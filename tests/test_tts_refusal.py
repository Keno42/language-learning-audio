"""#296: a refusal of the speech service (HTTP 403 at the handshake) is one shared state: the workers wait together, one probes, they resume or fail together."""
import contextlib
import io
import threading
import unittest
from pathlib import Path
from unittest import mock

from audiolesson.render.tts import EdgeProvider, SpeechRefused


class Refused(Exception):
    status = 403


def provider(budget=15.0):
    p = EdgeProvider()
    p.MINUTE = 0.0
    p.refusal_budget_min = budget
    return p


def run_workers(p, attempts, n=4, sleeps=None):
    """``n`` workers each call ``p._retrying(attempt)``; returns (results, stderr). ``sleeps`` collects the waits."""
    results = [None] * n
    err = io.StringIO()
    sleeps = sleeps if sleeps is not None else []

    def work(i):
        try:
            results[i] = p._retrying(lambda: attempts(i))
        except Exception as exc:  # noqa: BLE001
            results[i] = exc

    with mock.patch("audiolesson.render.tts.time.sleep", side_effect=sleeps.append), contextlib.redirect_stderr(err):
        threads = [threading.Thread(target=work, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
    return results, err.getvalue()


class SchedulingTests(unittest.TestCase):
    def test_the_probes_are_one_two_four_eight_minutes_up_to_the_budget(self):
        self.assertEqual(provider(15)._schedule(), [1.0, 2.0, 4.0, 8.0])
        self.assertEqual(provider(5)._schedule(), [1.0, 2.0, 2.0])
        self.assertEqual(provider(1)._schedule(), [1.0])

    def test_only_a_403_status_is_a_refusal(self):
        self.assertTrue(EdgeProvider._refused(Refused()))
        self.assertFalse(EdgeProvider._refused(ValueError("403")))
        self.assertFalse(EdgeProvider._refused(type("E", (Exception,), {"status": 500})()))


class WorkersWaitTogetherTests(unittest.TestCase):
    def test_a_short_refusal_costs_waiting_not_a_failed_lesson(self):
        sleeps = []
        lock = threading.Lock()
        calls = {"n": 0}

        def attempts(i):
            with lock:
                calls["n"] += 1
            if len(sleeps) < 2:  # the service refuses until the first prober has waited twice
                raise Refused("403")
            return f"clip{i}"

        p = provider()
        results, err = run_workers(p, attempts, sleeps=sleeps)
        self.assertEqual(results, ["clip0", "clip1", "clip2", "clip3"])
        waits = [l for l in err.splitlines() if "service refusing (403)" in l]
        self.assertEqual(len(waits), 2, "waiting 1 and 2 min: the second probe got through")
        self.assertIn("waiting 1 min (1/4)", waits[0])
        self.assertIn("waiting 2 min (2/4)", waits[1])

    def test_one_worker_probes_at_a_time(self):
        sleeps = []
        active = {"now": 0, "max": 0}
        lock = threading.Lock()

        def attempts(i):
            if not sleeps:  # refused until someone has waited once
                raise Refused("403")
            with lock:
                active["now"] += 1
            try:
                return "ok"
            finally:
                with lock:
                    active["now"] -= 1

        results, err = run_workers(provider(), attempts, sleeps=sleeps)
        self.assertEqual(results, ["ok"] * 4)
        self.assertEqual(len(sleeps), 1, "one worker waited for all of them")
        self.assertEqual(len([l for l in err.splitlines() if "waiting" in l]), 1)

    def test_when_the_budget_is_spent_every_worker_fails_at_once_with_one_clear_line(self):
        calls = {"n": 0}
        lock = threading.Lock()

        def attempts(i):
            with lock:
                calls["n"] += 1
            raise Refused("403")

        p = provider(budget=3)
        results, err = run_workers(p, attempts)
        self.assertTrue(all(isinstance(r, SpeechRefused) for r in results), results)
        self.assertEqual({str(r) for r in results}, {"speech service refused (403) for 3 min; cached clips kept"})
        probes = len(p._schedule())
        self.assertEqual(calls["n"], 4 + probes, "the four first tries, then only the prober's probes")
        lines = [l for l in err.splitlines() if l.startswith("edge-tts:")]
        self.assertEqual(len(lines), probes, "one waiting line per probe, said as it happens")

    def test_another_error_keeps_the_per_clip_retries(self):
        class EdgeTTSException(Exception):
            pass

        class NoAudioReceived(EdgeTTSException):
            pass

        seen = []

        def attempt():
            seen.append(1)
            if len(seen) == 1:
                raise NoAudioReceived("no audio")
            return "ok"

        waits = []
        with mock.patch("audiolesson.render.tts.time.sleep", side_effect=waits.append), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(provider()._retrying(attempt), "ok")
        self.assertEqual(waits, [5.0])


class CacheKeptTests(unittest.TestCase):
    def test_clips_synthesized_before_the_refusal_stay_in_the_cache(self):
        import tempfile

        from audiolesson.render.audio import silence
        from audiolesson.render.renderer import _cache_path, _cached

        class Fake(EdgeProvider):
            name = "fake"

            def synthesize(self, text, lang, voice, rate=1.0):
                if text == "b":
                    raise SpeechRefused("speech service refused (403) for 15 min; cached clips kept")
                return silence(0.2)

        with tempfile.TemporaryDirectory() as td:
            cache = Path(td)
            p = Fake()
            _cached(p, cache, "a", "is", "v", 1.0, True)
            with self.assertRaises(SpeechRefused):
                _cached(p, cache, "b", "is", "v", 1.0, True)
            self.assertTrue(_cache_path(p, cache, "a", "is", "v", 1.0, True).exists())
            self.assertFalse(_cache_path(p, cache, "b", "is", "v", 1.0, True).exists())


if __name__ == "__main__":
    unittest.main()
