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

    def test_a_provider_given_on_the_command_line_says_every_speaker(self):
        """«--provider stub»: no speaker keeps a provider of its own, so the instructions are the stub's too (native_b's voice), and a
        stub render needs no OpenAI key."""
        from audiolesson.render.tts import get_provider

        profile = load_profile(ROOT / "profiles" / "edge-is-en.toml", "stub")
        self.assertEqual(profile.provider, "stub")
        self.assertNotIn("command", profile.speakers, "its voice («cedar») is the realtime provider's own")
        stub = get_provider("stub")
        self.assertEqual(profile.voice_for("command", "is", stub, 0).voice, "is-IS-GunnarNeural")
        sc = Script(1, "t", "is", "en")
        sc.segments = [Segment("speak", "command", "Endurtaktu.", "is", 1.0, 1.0)]
        with tempfile.TemporaryDirectory() as td, mock.patch.dict("os.environ", {}, clear=True), \
                contextlib.redirect_stderr(io.StringIO()) as err, mock.patch.object(renderer, "to_mp3", lambda *a: False):
            renderer.render_script(sc, profile, Path(td) / "out.wav", Path(td) / "cache", progress=False)
        self.assertNotIn("cannot run", err.getvalue())
        self.assertNotIn("said in the profile's voice", err.getvalue())

    def user_args(self, td, **given):
        """``generate --user yuki`` with ``given`` on the command line, the rest from the user's settings.json (``cli._apply_user``)."""
        import argparse

        from audiolesson import cli

        ns = argparse.Namespace(cmd="generate", user="yuki", root=td, learner=None, out=None, curriculum=None, known=None, profile=None,
                                provider=None, minutes=None, level=None)
        for k, v in given.items():
            setattr(ns, k, v)
        cli._apply_user(ns)
        return ns

    def test_a_remembered_service_keeps_the_instructions_voice(self):
        """Review of #576: a learner with «"provider": "edge"» saved from an earlier run, generating without --provider, keeps the
        ``command`` speaker's realtime voice (and its warning when that cannot run); edge replaces the profile's provider only."""
        import json

        from audiolesson import cli

        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "yuki").mkdir()
            (Path(td) / "yuki" / "settings.json").write_text(json.dumps({"curriculum": "curricula/is-en", "profile": str(ROOT / "profiles" / "edge-is-en.toml"),
                                                                        "provider": "edge"}))
            remembered = self.user_args(td)
            self.assertEqual(remembered.provider, "edge", "restored from settings.json")
            got = cli._profile(remembered)
            self.assertEqual((got.provider, got.speakers["command"].provider), ("edge", "openai-realtime"))

    def test_a_stub_run_and_the_next_that_remembers_it_call_no_service(self):
        """Review of #576: «--provider stub» is saved for the user; the next run, with no --provider and an OpenAI key present, is a stub
        render too: no speaker keeps a provider of its own, and nothing calls the realtime model."""
        from audiolesson import cli

        with tempfile.TemporaryDirectory() as td:
            first = self.user_args(td, curriculum="curricula/is-en", profile=str(ROOT / "profiles" / "edge-is-en.toml"), provider="stub")
            cli._save_user_settings(first)
            second = self.user_args(td)
            self.assertEqual(second.provider, "stub", "remembered")
            for run in (first, second):
                profile = cli._profile(run)
                self.assertNotIn("command", profile.speakers)
                sc = Script(1, "t", "is", "en")
                sc.segments = [Segment("speak", "command", "Endurtaktu.", "is", 1.0, 1.0)]
                with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
                        mock.patch.object(OpenAIRealtimeProvider, "_once", side_effect=AssertionError("a stub render called OpenAI")), \
                        mock.patch.object(OpenAIRealtimeProvider, "check", return_value=None), \
                        contextlib.redirect_stderr(io.StringIO()) as err, mock.patch.object(renderer, "to_mp3", lambda *a: False):
                    renderer.render_script(sc, profile, Path(td) / "out.wav", Path(td) / "cache", progress=False)
                self.assertNotIn("said in the profile's voice", err.getvalue())

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
        # the profile's voice says the instruction too, as the length its own voice's clip is checked against (``OWN_VOICE_MIN_SHARE``)
        self.assertEqual(sorted(main.asked), [("Endurtaktu.", "B"), ("Góðan daginn.", "A"), ("Takk.", "B")])
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


class Lengths(Voice):
    """A provider whose clips last ``lengths`` seconds in turn, the last one repeated."""

    def __init__(self, name: str, level: int, lengths: list[float]):
        super().__init__(name, level)
        self.lengths = lengths

    def synthesize(self, text, lang, voice, rate=1.0):
        self.asked.append((text, voice))
        return tone(self.level, self.lengths[min(len(self.asked), len(self.lengths)) - 1])


class ShortOwnVoiceTests(unittest.TestCase):
    """The owner's dry-run lesson 63: the realtime voice said «Hlustaðu.» as «staðu» (0.40 s; Gunnar's clip 0.64 s), its transcript said
    «Hlustaðu.». A clip of the instructions' own voice under ``OWN_VOICE_MIN_SHARE`` of the same line in the profile's voice is synthesized
    again, then said in the profile's voice; the whole clips measured ran 0.86 to 1.59 of Gunnar's."""

    def render(self, main, realtime, cache: Path):
        sc = Script(1, "t", "is", "en")
        sc.segments = [Segment("speak", "native_a", "Góðan daginn.", "is", 1.0, 1.0), Segment("speak", "command", "Hlustaðu.", "is", 1.0, 1.0)]
        path = cache.parent / "p.toml"
        path.write_text(CommandVoiceTests.PROFILE, encoding="utf-8")
        providers = {main.name: main, realtime.name: realtime}
        with mock.patch.object(renderer, "get_provider", lambda name: providers[name]), mock.patch.object(renderer, "to_mp3", lambda *a: False), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            renderer.render_script(sc, load_profile(path), cache.parent / "out.wav", cache, progress=False)
        return err.getvalue()

    def test_the_share_sits_between_the_cut_clip_and_the_shortest_whole_one(self):
        self.assertTrue(0.40 / 0.64 < renderer.OWN_VOICE_MIN_SHARE < 0.47 / 0.55)

    def test_a_clip_too_short_against_the_profile_s_voice_is_synthesized_again(self):
        with tempfile.TemporaryDirectory() as td:
            main, realtime = Voice("main", 8000), Lengths("realtime", 2000, [0.3, 0.6])
            err = self.render(main, realtime, Path(td) / "cache")
            self.assertEqual(realtime.asked, [("Hlustaðu.", "cedar")] * 2, "0.3 s against 0.5 s: asked again")
            self.assertNotIn("could not say", err)
            again = Lengths("realtime", 2000, [0.6])
            self.render(Voice("main", 8000), again, Path(td) / "cache")
            self.assertEqual(again.asked, [], "the whole one was cached")

    def test_a_clip_short_twice_is_said_in_the_profile_s_voice_and_not_cached(self):
        with tempfile.TemporaryDirectory() as td:
            main, realtime = Voice("main", 8000), Lengths("realtime", 2000, [0.3])
            err = self.render(main, realtime, Path(td) / "cache")
            self.assertEqual(len(realtime.asked), 2)
            self.assertIn(("Hlustaðu.", "B"), main.asked, "native_b's voice")
            self.assertIn("could not say 'Hlustaðu.'", err)
            later = Lengths("realtime", 2000, [0.6])
            self.render(Voice("main", 8000), later, Path(td) / "cache")
            self.assertEqual(len(later.asked), 1, "nothing short was cached: the next render asks again")

    def test_a_short_clip_already_cached_is_synthesized_again(self):
        with tempfile.TemporaryDirectory() as td:
            cache = Path(td) / "cache"
            self.render(Voice("main", 8000), Lengths("realtime", 2000, [0.3, 0.3]), cache)  # leaves nothing cached
            # a short clip cached before this check existed
            realtime = Lengths("realtime", 2000, [0.6])
            key = renderer._cache_path(realtime, cache, "Hlustaðu.", "is", "cedar", 1.0, True)
            renderer.write_wav(tone(2000, 0.3), key)
            err = self.render(Voice("main", 8000), realtime, cache)
            self.assertEqual(len(realtime.asked), 1)
            self.assertIn("too short against the profile's voice", err)
            self.assertAlmostEqual(renderer.read_wav(key).seconds, 0.6, places=2)
            self.assertAlmostEqual(renderer.read_wav(key.with_name(key.name + ".bad")).seconds, 0.3, places=2, msg="put aside, as by hand")

    def test_a_short_cached_clip_is_not_found_again_by_a_render_that_cannot_check_it(self):
        """Review of #578: a cached «staðu» found short, whose replacements came back short too, stayed on disk; a later render whose
        reference (the profile's voice) failed took every clip as long enough, and played it. It is put aside when found, and a render
        that cannot check says so."""

        class NoReference(Voice):
            def synthesize(self, text, lang, voice, rate=1.0):
                if text == "Hlustaðu.":
                    raise RuntimeError("edge is unavailable")
                return super().synthesize(text, lang, voice, rate)

        with tempfile.TemporaryDirectory() as td:
            cache = Path(td) / "cache"
            cache.mkdir()
            key = renderer._cache_path(Lengths("realtime", 2000, [0.3]), cache, "Hlustaðu.", "is", "cedar", 1.0, True)
            renderer.write_wav(tone(2000, 0.3), key)  # cached before the check existed
            err = self.render(Voice("main", 8000), Lengths("realtime", 2000, [0.3]), cache)
            self.assertIn("put aside", err)
            self.assertFalse(key.exists(), "short, and its replacements short: nothing left under its key")
            no_ref = NoReference("main", 8000)
            renderer._cache_path(no_ref, cache, "Hlustaðu.", "is", "B", 1.0, True).unlink()  # the reference not cached, and edge down
            later = Lengths("realtime", 2000, [0.6])
            err = self.render(no_ref, later, cache)
            self.assertEqual(len(later.asked), 1, "the short clip is not found again: the line is asked anew")
            # the form the bot reads (site_update_notifier ``lesson.voice_fallbacks``): one line, at its start
            self.assertRegex(err, r"(?m)^warning: realtime could not check 'Hlustaðu\.' against the profile's voice \(.*\); used unchecked$")

    def test_a_clip_as_short_as_the_shortest_whole_one_is_kept(self):
        with tempfile.TemporaryDirectory() as td:
            realtime = Lengths("realtime", 2000, [0.43])  # 0.86 of 0.5 s, as «Hægt.»
            err = self.render(Voice("main", 8000), realtime, Path(td) / "cache")
            self.assertEqual(len(realtime.asked), 1)
            self.assertNotIn("could not say", err)


class RetakeTests(unittest.TestCase):
    """#563, lesson 64 («Samtalinu er lokið.» stayed high in tension): one take of an instruction is cached and replayed. A line the profile
    names in its speaker's ``retake`` is said again as that take, under a key of its own; the other lines, and take 0, keep their clips."""

    PROFILE = CommandVoiceTests.PROFILE.replace('command = { provider = "realtime", voice = "cedar" }',
                                                'command = { provider = "realtime", voice = "cedar", retake = { "Samtalinu er lokið." = 1 } }')

    def test_the_icelandic_profiles_retake_the_line_the_learner_heard_high(self):
        for name in ("edge-is-en.toml", "edge-is-ja.toml"):
            self.assertEqual(load_profile(ROOT / "profiles" / name).speakers["command"].retake, {"Samtalinu er lokið.": 1}, name)

    def test_a_take_is_its_own_clip_and_take_0_keeps_the_old_key(self):
        from audiolesson.render.renderer import _cache_path

        realtime = OpenAIRealtimeProvider()
        path = lambda take: _cache_path(realtime, Path("/c"), "Samtalinu er lokið.", "is", "cedar", 1.0, True, take)  # noqa: E731
        self.assertEqual(path(0), _cache_path(realtime, Path("/c"), "Samtalinu er lokið.", "is", "cedar", 1.0, True), "no take: the key as before")
        self.assertEqual(len({path(0), path(1), path(2)}), 3)

    def test_a_render_says_a_retaken_line_anew_and_keeps_the_others(self):
        sc = Script(1, "t", "is", "en")
        sc.segments = [Segment("speak", "native_a", "Góðan daginn.", "is", 1.0, 1.0), Segment("speak", "command", "Samtalinu er lokið.", "is", 1.0, 1.0),
                       Segment("speak", "command", "Endurtaktu.", "is", 1.0, 1.0)]
        with tempfile.TemporaryDirectory() as td:
            cache = Path(td) / "cache"
            for text, profile_text in (("first", CommandVoiceTests.PROFILE), ("retake", self.PROFILE)):
                path = Path(td) / f"{text}.toml"
                path.write_text(profile_text, encoding="utf-8")
                main, realtime = Voice("main", 8000), Voice("realtime", 2000)
                with mock.patch.object(renderer, "get_provider", {"main": main, "realtime": realtime}.get), \
                        mock.patch.object(renderer, "to_mp3", lambda *a: False), contextlib.redirect_stderr(io.StringIO()):
                    renderer.render_script(sc, load_profile(path), Path(td) / "out.wav", cache, progress=False)
                if text == "first":
                    self.assertEqual(sorted(realtime.asked), [("Endurtaktu.", "cedar"), ("Samtalinu er lokið.", "cedar")])
                else:
                    self.assertEqual(realtime.asked, [("Samtalinu er lokið.", "cedar")], "only the retaken line is said again")
            # the same profile once more: the retake is cached
            again = Voice("realtime", 2000)
            with mock.patch.object(renderer, "get_provider", {"main": Voice("main", 8000), "realtime": again}.get), \
                    mock.patch.object(renderer, "to_mp3", lambda *a: False), contextlib.redirect_stderr(io.StringIO()):
                renderer.render_script(sc, load_profile(Path(td) / "retake.toml"), Path(td) / "out.wav", cache, progress=False)
            self.assertEqual(again.asked, [])


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
