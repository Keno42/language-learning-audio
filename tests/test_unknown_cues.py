import unittest
from pathlib import Path

from audiolesson.content import CurriculumError, load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.listening_cues import unknown_cue
from audiolesson.listening_tasks import append_task, catch_unknown, tokens
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.themes import Level, Theme, Turn, _check
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class UnknownCueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula/is-en")
        cls.repair = cls.cur.by_id["hvad_thydir_thetta"]

    def task(self, lang="en", **changes):
        args = dict(
            line="Auðvitað. Í dag er kjötsúpa.",
            glosses={"kjötsúpa": {"en": "lamb soup", "ja": "ラム肉のスープ"}},
            known_words={w.lower() for w in tokens("Auðvitað. Í dag er.")},
            known_lang=lang, repair=self.repair, repair_known=True,
            source="theme:cafe:2:3:1", scene="At the café.",
            line_meaning="Of course. Today there's lamb soup." if lang == "en" else "もちろん。今日はラム肉のスープです。",
        )
        args.update(changes)
        return catch_unknown(**args)

    def test_the_cue_names_the_missing_part_and_the_answer_is_one_question(self):
        for lang, context in (("en", "Of course. Today there's something."), ("ja", "もちろん。今日は何かです。")):
            with self.subTest(lang=lang):
                task = self.task(lang)
                self.assertEqual(task.cue, context)
                self.assertEqual(task.repair, "Hvað þýðir kjötsúpa?")
                b = Builder(self.cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
                sc = Script(22, "catch", "is", lang)
                append_task(b, sc, task, 120)
                cue = next(g.text for g in sc.segments if g.type == "narrate" and context in g.text)
                self.assertNotIn("kjötsúpa", cue)
                self.assertNotIn(task.meaning, cue)
                self.assertEqual([g.text for g in sc.segments if g.type == "answer"], ["Hvað þýðir kjötsúpa?"])
                self.assertEqual([g.text for g in sc.segments if g.type == "speak"], [task.line, task.line])
                self.assertEqual(sc.review_questions(), [])
                self.assertEqual(b.learner.items, {})

    def test_an_authored_pointer_handles_a_different_translation(self):
        gloss = {"en": "a moment", "ja": "少しの間", "pointer": {"en": "the word used when asking you to wait", "ja": "待つように言った部分"}}
        task = self.task(line="Já, augnablik.", known_words={"já"}, glosses={"augnablik": gloss}, line_meaning="Yes, one moment.")
        self.assertEqual((task.prompt_key, task.cue), ("catch_unknown_pointer", gloss["pointer"]["en"]))
        self.assertEqual(task.repair, "Hvað þýðir augnablik?")

    def test_no_context_means_no_generic_guess_the_word_prompt(self):
        self.assertIsNone(self.task(line_meaning="Of course. The special is ready."))
        self.assertIsNone(self.task(line_meaning=""))

    def test_a_known_repair_and_exactly_one_unknown_word_are_still_required(self):
        self.assertIsNone(self.task(repair_known=False))
        self.assertIsNone(self.task(known_words={"í", "dag", "er"}))
        self.assertIsNone(self.task(line="Auðvitað. Í dag er kjötsúpa, kjötsúpa."))
        self.assertIsNone(self.task(known_words={w.lower() for w in tokens("Auðvitað. Í dag er kjötsúpa.")}))

    def test_a_partial_or_ambiguous_translation_needs_an_authored_pointer(self):
        self.assertIsNone(unknown_cue("Cancel it.", {"en": "can"}, "en"))
        self.assertIsNone(unknown_cue("Soup with soup.", {"en": "soup"}, "en"))

    def test_validate_checks_canonical_variant_and_listening_lines_in_both_languages(self):
        def check(line, location):
            partner = Turn("partner", "Já.", meaning="Yes.", meaning_ja="はい。")
            if location == "canonical":
                partner = Turn("partner", **line)
            else:
                getattr(partner, location).append(line)
            theme = Theme("x", "A3", "X", levels=[Level("g", turns=[partner, Turn("you", "Takk.", cue="Thank them.", items=["takk"])])])
            _check(theme)
        for location in ("canonical", "variants", "listen"):
            for lang in ("en", "ja"):
                with self.subTest(location=location, lang=lang):
                    gloss = {"en": "lamb soup", "ja": "ラム肉のスープ"}
                    line = dict(say="Í dag er kjötsúpa.", meaning="Today there's lamb soup.", meaning_ja="今日はラム肉のスープです。", word_glosses={"kjötsúpa": gloss})
                    if location == "listen":
                        line["probes"] = [{"kind": "time", "answer": "Í dag", "meanings": {"en": "today", "ja": "今日"}}]
                    check(line, location)
                    line["meaning" if lang == "en" else "meaning_ja"] = "Different translation."
                    with self.assertRaises(CurriculumError):
                        check(line, location)
                    gloss["pointer"] = {"en": "what is available today", "ja": "今日あると言っていたもの"}
                    check(line, location)
