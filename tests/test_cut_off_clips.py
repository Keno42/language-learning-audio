"""#462 (lesson 43): «Ask where she lives.» was cached as a valid WAV of 0.57 s, about half the sentence, and played cut off three times. A
clip of a line of several words far shorter than its estimate is synthesized once more, and not cached while it stays short; a tool lists
the cached clips that look cut off."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from audiolesson.render.audio import AudioClip, write_wav
from audiolesson.render.renderer import _cache_path, _cached, load_profile, looks_cut_off
from audiolesson.render.tts import Provider
from audiolesson.script import Script, Segment

RATE = 24000
LINE = "Ask where she lives."


def clip(seconds: float) -> AudioClip:
    return AudioClip(b"\x10\x27" * int(seconds * RATE), RATE)  # a constant loud sample: nothing trimmed


class Service(Provider):
    """A speech service that answers with the given lengths in turn."""

    name = "edge"
    parallel = True

    def __init__(self, *lengths: float):
        self.lengths, self.calls = list(lengths), 0

    def synthesize(self, text, lang, voice, rate=1.0):
        self.calls += 1
        return clip(self.lengths.pop(0) if len(self.lengths) > 1 else self.lengths[0])


class CutOffTests(unittest.TestCase):
    def test_lesson_43s_clip_looks_cut_off_and_a_whole_one_does_not(self):
        self.assertTrue(looks_cut_off(clip(0.574), LINE, "en"), "the cached clip: 27,594 bytes at 24 kHz")
        self.assertFalse(looks_cut_off(clip(1.2), LINE, "en"))
        self.assertFalse(looks_cut_off(clip(0.3), "Já, takk.", "is"), "two words: the estimate's floor, left out")

    def test_a_cut_off_clip_is_synthesized_again_and_the_whole_one_cached(self):
        with tempfile.TemporaryDirectory() as td:
            service = Service(0.57, 1.2)
            got = _cached(service, Path(td), LINE, "en", "en-US-AriaNeural", 1.0, True)
            self.assertEqual((service.calls, round(got.seconds, 2)), (2, 1.2))
            self.assertTrue(_cache_path(service, Path(td), LINE, "en", "en-US-AriaNeural", 1.0, True).exists())

    def test_a_clip_cut_off_twice_is_used_once_and_not_cached(self):
        with tempfile.TemporaryDirectory() as td:
            service = Service(0.57)
            with contextlib.redirect_stderr(io.StringIO()) as err:
                _cached(service, Path(td), LINE, "en", "en-US-AriaNeural", 1.0, True)
            self.assertEqual(service.calls, 2)
            self.assertIn("cut off", err.getvalue())
            self.assertFalse(_cache_path(service, Path(td), LINE, "en", "en-US-AriaNeural", 1.0, True).exists(), "the next render asks again")

    def test_a_render_asks_once_for_a_line_said_three_times(self):
        """Review of #466: a clip left out of the cache was asked again at every line that said it (8 requests for 3 lines, warm-up
        included). One render keeps it in memory: two requests (the first and the retry), one warning; the next render asks again."""
        from unittest import mock

        from audiolesson.render import renderer

        service = Service(0.57)
        service.check = lambda: None
        sc = Script(43, "t", "is", "en")
        sc.segments = [Segment("narrate", "instructor", LINE, "en", 1.0, 2.0) for _ in range(3)]
        profile = load_profile(str(Path(__file__).resolve().parent.parent / "profiles" / "edge-is-en.toml"))
        profile.fallback = ""
        with tempfile.TemporaryDirectory() as td, mock.patch.object(renderer, "get_provider", lambda name: service), \
                contextlib.redirect_stderr(io.StringIO()) as err, mock.patch.object(renderer, "to_mp3", lambda *a: False):
            renderer.render_script(sc, profile, Path(td) / "out.wav", Path(td) / "cache", progress=False)
            self.assertEqual(service.calls, 2)
            self.assertEqual(err.getvalue().count("cut off twice"), 1)
            self.assertFalse(any((Path(td) / "cache").glob("*.wav")), "still not cached")

    def test_a_local_engine_is_taken_as_it_speaks(self):
        with tempfile.TemporaryDirectory() as td:
            local = Service(0.57)
            local.name, local.parallel = "espeak", False
            _cached(local, Path(td), LINE, "en", "v", 1.0, True)
            self.assertEqual(local.calls, 1)

    def test_the_tool_lists_the_cut_off_clip_first(self):
        import tools.cut_off_clips as tool

        with tempfile.TemporaryDirectory() as td:
            cache, sc = Path(td), Script(43, "t", "is", "en")
            sc.segments = [Segment("narrate", "instructor", LINE, "en", 1.0, 2.0), Segment("narrate", "instructor", "Say you live in Osaka.", "en", 1.0, 2.3)]
            sc.save(cache / "lesson.script.json")
            profile = Path(__file__).resolve().parent.parent / "profiles" / "edge-is-en.toml"
            edge = Service(1.0)
            for text, seconds in ((LINE, 0.57), ("Say you live in Osaka.", 1.4)):
                write_wav(clip(seconds), _cache_path(edge, cache, text, "en", "en-US-AriaNeural", 1.0, load_profile(str(profile)).trim))
            rows = tool.rows([cache / "lesson.script.json"], cache, str(profile))
            self.assertEqual([(r["text"], r["cut_off"]) for r in rows], [(LINE, True), ("Say you live in Osaka.", False)])

    def test_the_tools_list_shows_every_flagged_clip_whatever_its_top(self):
        """Review of #466: «Hi.» (one word, never flagged) sorts ahead of a cut-off line; with --top 1 the cut-off line was not shown."""
        import tools.cut_off_clips as tool

        with tempfile.TemporaryDirectory() as td:
            cache, sc = Path(td), Script(43, "t", "is", "en")
            sc.segments = [Segment("narrate", "instructor", LINE, "en", 1.0, 2.0), Segment("narrate", "instructor", "Hi.", "en", 1.0, 1.0)]
            sc.save(cache / "lesson.script.json")
            profile = str(Path(__file__).resolve().parent.parent / "profiles" / "edge-is-en.toml")
            edge = Service(1.0)
            for text, seconds in ((LINE, 0.57), ("Hi.", 0.1)):
                write_wav(clip(seconds), _cache_path(edge, cache, text, "en", "en-US-AriaNeural", 1.0, load_profile(profile).trim))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = tool.main(["--cache", str(cache), "--profile", profile, "--top", "1", str(cache / "lesson.script.json")])
            lines = out.getvalue().splitlines()
            self.assertEqual(code, 1)
            self.assertTrue(lines[1].startswith("CUT ") and LINE in lines[1], lines)


if __name__ == "__main__":
    unittest.main()
