"""Lesson 31: «asking for the same thing more politely» was asked 8 times, its instruction narrated 9 times (G12). The instruction is narrated
in full under the cap of any situation (twice a lesson), then «Same change:» while the transform asked last had it."""
import random
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import SITUATION_FULL_MAX, Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
POLITE = "politeness_get_eg_fengid"


class TransformInstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.curricula = {lang: load_curriculum(ROOT / "curricula/is-en", known_lang=lang) for lang in ("en", "ja")}

    def lesson(self, lang="en", seed=0):
        cur = self.curricula[lang]
        return cur, Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"), random.Random(seed)), Script(31, "t", "is", lang)

    @staticmethod
    def cues(sc):
        """(text, role) of each transform cue: the narration right before the source sentence."""
        return [(a.text, a.role) for a, b in zip(sc.segments, sc.segments[1:]) if b.type == "speak" and b.role == "source" and a.type == "narrate"]

    def test_the_instruction_is_said_in_full_twice_then_the_short_form(self):
        for lang in ("en", "ja"):
            with self.subTest(lang=lang):
                cur, b, sc = self.lesson(lang)
                item = cur.by_id[POLITE]
                b._intro_transform(sc, item)
                for _ in range(7):
                    b.recall(sc, item, "meaning")
                cues = self.cues(sc)
                self.assertEqual(len(cues), 8)
                self.assertEqual(cues[:SITUATION_FULL_MAX], [(item.instruction, None)] * SITUATION_FULL_MAX)
                short = Prompts.load(lang).get("transform_same")
                self.assertNotEqual(short, item.instruction)
                self.assertEqual(cues[SITUATION_FULL_MAX:], [(short, "short_instruction")] * (8 - SITUATION_FULL_MAX))

    def test_after_another_transform_the_instruction_is_said_in_full_again(self):
        cur, b, sc = self.lesson()
        polite, opposite = cur.by_id[POLITE], cur.by_id["adjective_opposites"]
        for item in (polite, polite, polite, opposite, polite, polite):
            b.recall(sc, item, "meaning")
        short = Prompts.load("en").get("transform_same")
        self.assertEqual(
            [t for t, _ in self.cues(sc)],
            [polite.instruction, polite.instruction, short, opposite.instruction, polite.instruction, short],
        )

    def test_the_short_form_names_the_speakers_form_like_the_instruction(self):
        cur, b, sc = self.lesson()
        past = cur.by_id["transform_var"]
        exm = next(e for e in past.examples if e.result_m)
        for _ in range(4):
            b._transform_prompt(sc, sc.new_exercise("recall", "meaning", [past.id]), past, exm)
        self.assertEqual(
            [t for t, _ in self.cues(sc)],
            ["As a woman: " + past.instruction, "As a man: " + past.instruction, "As a woman: Same change:", "As a man: Same change:"],
        )

    def test_the_instruction_does_not_push_a_situation_out_of_the_recent_ones(self):
        """#273's last ``SITUATION_RECENT`` are situations a cue could pick instead: an instruction counts against its own cap only."""
        cur, b, sc = self.lesson()
        b._narrated("Greet the driver.")
        for item in (cur.by_id[POLITE], cur.by_id[POLITE], cur.by_id["adjective_opposites"]):
            b.recall(sc, item, "meaning")
        self.assertEqual(len(self.cues(sc)), 3)
        self.assertEqual(b.situation_rank("Greet the driver."), 1)
        self.assertIsNone(b.situation_rank(cur.by_id[POLITE].instruction))

    def test_the_written_review_asks_with_the_instruction_in_full(self):
        for lang in ("en", "ja"):
            with self.subTest(lang=lang):
                cur, b, sc = self.lesson(lang)
                item = cur.by_id[POLITE]
                b._intro_transform(sc, item)
                for _ in range(5):
                    b.recall(sc, item, "meaning")
                qs = [q for q in sc.review_questions() if item.id in q["items"]]
                self.assertEqual(len(qs), 1)
                prompt, answer = qs[0]["prompt"], qs[0]["answer"]
                self.assertTrue(prompt.startswith(item.instruction + "\n"), prompt)
                source = prompt.split("\n", 1)[1]
                self.assertIn((source, answer), {(e.source, e.result) for e in item.examples})


if __name__ == "__main__":
    unittest.main()
