"""#563 (lessons 61 and 62: «the conversation's male voice and the instructions' voice are the same, so the switch is hard to hear»; the
owner, 2026-11-20: OpenAI's realtime voice for them). The instructions in the target language are the ``command`` speaker's: a profile gives
it a provider of its own, a line that provider cannot say as written is said in native_b's voice, and its loudness matches the lesson's."""
import array
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from audiolesson.exercises import COMMAND_VOICE
from audiolesson.render import renderer
from audiolesson.render.audio import AudioClip, loudness
from audiolesson.render.renderer import load_profile
from audiolesson.render.tts import OpenAIRealtimeProvider, Provider, RealtimeMismatch
from audiolesson.script import Script, Segment

ROOT = Path(__file__).resolve().parent.parent


def tone(level: int, seconds: float = 0.5, rate: int = 24000) -> AudioClip:
    n = int(seconds * rate)
    return AudioClip(array.array("h", (level if k % 2 else -level for k in range(n))).tobytes(), rate)


class Voice(Provider):
    """A provider that answers every line with a tone at ``level``, and records what it was asked."""

    parallel = False

    def __init__(self, name: str, level: int, fails: bool = False):
        self.name, self.level, self.fails, self.asked = name, level, fails, []

    def synthesize(self, text, lang, voice, rate=1.0):
        self.asked.append((text, voice))
        if self.fails:
            raise RealtimeMismatch(f"did not say {text!r}")
        return tone(self.level)


class CommandVoiceTests(unittest.TestCase):
    def test_the_instructions_are_a_speaker_of_their_own(self):
        self.assertEqual(COMMAND_VOICE, "command")
        for name in ("edge-is-en.toml", "edge-is-ja.toml"):
            sv = load_profile(ROOT / "profiles" / name).speakers["command"]
            self.assertEqual((sv.provider, sv.voice), ("openai-realtime", "cedar"), name)
        self.assertNotIn("command", load_profile(ROOT / "profiles" / "edge-fr-en.toml").speakers, "a profile may leave it out")
        sc = Script(1, "t", "is", "en")
        sc.add(Segment("speak", "command", "Endurtaktu.", "is", 1.0, 1.0))
        self.assertIn("**Instruction:** Endurtaktu.", sc.transcript())

    def render(self, main, other, profile_text):
        sc = Script(1, "t", "is", "en")
        sc.segments = [Segment("speak", "native_a", "Góðan daginn.", "is", 1.0, 1.0), Segment("speak", "command", "Endurtaktu.", "is", 1.0, 1.0),
                       Segment("speak", "native_b", "Takk.", "is", 1.0, 1.0)]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "p.toml"
            path.write_text(profile_text, encoding="utf-8")
            profile = load_profile(path)
            providers = {main.name: main, other.name: other}
            with mock.patch.object(renderer, "get_provider", lambda name: providers[name]), mock.patch.object(renderer, "to_mp3", lambda *a: False), \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                cues = renderer.render_script(sc, profile, Path(td) / "out.wav", Path(td) / "cache", progress=False)
                mix = renderer.read_wav(Path(td) / "out.wav")
        return cues, mix, err.getvalue()

    PROFILE = '''provider = "main"
[speakers]
native_a = { voice = "A" }
native_b = { voice = "B" }
command = { provider = "realtime", voice = "cedar" }
'''

    def test_a_speaker_s_own_provider_says_its_lines_at_the_lesson_s_loudness(self):
        main, realtime = Voice("main", 8000), Voice("realtime", 2000)
        cues, mix, _ = self.render(main, realtime, self.PROFILE)
        self.assertEqual(realtime.asked, [("Endurtaktu.", "cedar")], "only the instruction, in its own voice")
        self.assertEqual(sorted(main.asked), [("Góðan daginn.", "A"), ("Takk.", "B")])
        # the instruction's clip is brought from 2000 to the native voices' 8000
        start = next(c for c in cues["segments"] if c["text"] == "Endurtaktu.")["t"]
        rate = mix.rate
        clip = AudioClip(mix.pcm[int(start * rate) * 2:int((start + 0.4) * rate) * 2], rate)
        self.assertAlmostEqual(loudness(clip), 8000, delta=50)

    def test_a_line_the_own_provider_cannot_say_is_said_in_the_stand_in_s_voice(self):
        main, realtime = Voice("main", 8000), Voice("realtime", 2000, fails=True)
        _, _, err = self.render(main, realtime, self.PROFILE)
        self.assertIn(("Endurtaktu.", "B"), main.asked, "native_b's voice, as before #563")
        self.assertIn("could not say 'Endurtaktu.'", err)

    def test_without_its_provider_the_speaker_takes_native_b_s_voice(self):
        main = Voice("main", 8000)

        class Missing(Voice):
            def check(self):
                return "OPENAI_API_KEY is not set"

        missing = Missing("realtime", 2000)
        _, _, err = self.render(main, missing, self.PROFILE)
        self.assertEqual(missing.asked, [])
        self.assertIn(("Endurtaktu.", "B"), main.asked)
        self.assertIn("cannot run (OPENAI_API_KEY is not set)", err)
        main2 = Voice("main", 8000)
        self.render(main2, Voice("realtime", 1), 'provider = "main"\n[speakers]\nnative_a = { voice = "A" }\nnative_b = { voice = "B" }\n')
        self.assertIn(("Endurtaktu.", "B"), main2.asked, "a profile with no command speaker: native_b's voice")


class RealtimeTests(unittest.TestCase):
    def test_a_line_is_kept_only_when_the_model_said_it_as_written(self):
        p = OpenAIRealtimeProvider()
        pcm = tone(5000).pcm
        with mock.patch.object(p, "_once", side_effect=[(pcm, "Endurtaktu, gjörðu svo vel."), (pcm, "endurtaktu")]) as once:
            clip = p.synthesize("Endurtaktu.", "is", "cedar")
        self.assertEqual(once.call_count, 2, "an added word: asked again")
        self.assertEqual(clip.pcm, pcm)
        with mock.patch.object(p, "_once", return_value=(pcm, "Endurtaktu núna.")), self.assertRaises(RealtimeMismatch):
            p.synthesize("Endurtaktu.", "is", "cedar")

    def test_another_model_or_prompt_is_another_clip(self):
        """Review of #575: the cache key holds the realtime model and a fingerprint of its instructions, so changing either makes new
        clips; a provider with no tag keeps the key it always had."""
        from audiolesson.render import tts
        from audiolesson.render.renderer import _cache_path

        cache = Path("/c")
        path = lambda p: _cache_path(p, cache, "Endurtaktu.", "is", "cedar", 1.0, True)  # noqa: E731
        base = path(OpenAIRealtimeProvider())
        other_model = OpenAIRealtimeProvider()
        other_model.MODEL = "gpt-realtime-other"
        self.assertNotEqual(path(other_model), base)
        with mock.patch.object(tts, "REALTIME_INSTRUCTIONS", tts.REALTIME_INSTRUCTIONS + "\nSpeak a little slower."):
            self.assertNotEqual(path(OpenAIRealtimeProvider()), base)
        self.assertEqual(path(OpenAIRealtimeProvider()), base, "the same model and prompt: the cached clip")
        import hashlib

        edge = tts.get_provider("edge")
        self.assertEqual(_cache_path(edge, cache, "Takk.", "is", "v", 1.0, True).name,
                         hashlib.sha1("edge|v|1.000|is|True|Takk.".encode()).hexdigest() + ".wav", "an edge clip's key is unchanged")

    def test_it_needs_a_key(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(OpenAIRealtimeProvider().check(), "OPENAI_API_KEY is not set")


if __name__ == "__main__":
    unittest.main()
