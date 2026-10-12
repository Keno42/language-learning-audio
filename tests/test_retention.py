"""#220: ease learns from a recall confirmed after a long gap; the confirmed recall rate is read by gap."""
import unittest
from datetime import date, timedelta

from audiolesson.learner import ItemState, LearnerState, retention_report

TODAY = date(2026, 3, 1)


def learner(**kw):
    l = LearnerState("is", "en", "A1")
    base = dict(stage="meaning", ease=2.3, interval_days=7.0, due=(TODAY - timedelta(days=1)).isoformat(), last_practiced=(TODAY - timedelta(days=14)).isoformat(),
                successes=3, durable_successes=2, recalled=2, last_outcome="recalled")
    base.update(kw)
    l.items["a"] = ItemState(**base)
    l.items["b"] = ItemState(**base)
    return l


class LongGapTests(unittest.TestCase):
    def test_a_recall_confirmed_after_a_week_raises_the_ease_and_extends_the_interval(self):
        l = learner()
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 14})
        st = l.items["a"]
        self.assertAlmostEqual(st.ease, 2.4)
        self.assertGreaterEqual(st.interval_days, 14 * 2.4 - 0.1, "at least the gap bridged, times the ease")
        self.assertGreaterEqual(date.fromisoformat(st.due), TODAY + timedelta(days=int(st.interval_days)))

    def test_a_short_gap_or_no_gap_changes_nothing_but_the_count(self):
        l = learner()
        l.report([], [], TODAY, recalled=["a", "b"], gaps={"a": 3})
        self.assertEqual((l.items["a"].ease, l.items["a"].interval_days), (2.3, 7.0))
        self.assertEqual((l.items["b"].ease, l.items["b"].interval_days), (2.3, 7.0), "no gap: as before")

    def test_a_failure_at_any_gap_lowers_the_ease_as_before(self):
        l = learner()
        l.report(["a"], [], TODAY, gaps={"a": 21})
        self.assertAlmostEqual(l.items["a"].ease, 2.1)
        self.assertEqual(l.items["a"].interval_days, 1)

    def test_the_ease_never_passes_its_ceiling(self):
        l = learner(ease=2.98)
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 30})
        self.assertEqual(l.items["a"].ease, 3.0)


class RetentionCountTests(unittest.TestCase):
    def test_outcomes_are_counted_by_the_longest_bucket_the_gap_reached(self):
        l = learner()
        l.items["c"] = ItemState(**{**l.items["a"].__dict__})
        l.items["d"] = ItemState(**{**l.items["a"].__dict__})
        l.report(["d"], [], TODAY, recalled=["a", "b"], hesitated=["c"], gaps={"a": 3, "b": 8, "c": 14, "d": 15})
        self.assertEqual(l.retention, {"3": [1, 1], "7": [1, 1], "14": [0, 2]})
        report = retention_report(l)
        self.assertEqual(report["3+ days"], "1/1 (100%)")
        self.assertEqual(report["14+ days"], "0/2 (0%)")

    def test_it_is_saved_and_loaded_and_an_old_file_reads_empty(self):
        import tempfile
        from pathlib import Path

        l = learner()
        l.report([], [], TODAY, recalled=["a"], gaps={"a": 10})
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "learner.json"
            l.save(path)
            self.assertEqual(LearnerState.load(path).retention, {"7": [1, 1]})
            fresh = LearnerState("is", "en", "A1")
            fresh.save(path)
            self.assertEqual(LearnerState.load(path).retention, {})
            self.assertEqual(retention_report(fresh)["7+ days"], "–")

    def test_the_cli_reads_gaps(self):
        from audiolesson.cli import _gaps

        self.assertEqual(_gaps("a=14, b=7,bad,c=x"), {"a": 14, "b": 7})


if __name__ == "__main__":
    unittest.main()
