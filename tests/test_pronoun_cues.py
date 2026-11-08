"""Lesson 51: «Your neighbour complains about the snow. Say you think it's beautiful.» asked for «Mér finnst snjórinn fallegur.», which «Mér finnst það
fallegt.» answers as well. A situation's instruction names what its answer names; ``validate`` lists one that says «it» for it (``pronoun_cues``)."""
import dataclasses
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum, pronoun_cues

ROOT = Path(__file__).resolve().parent.parent


class PronounCueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_course_names_what_its_answers_name(self):
        self.assertEqual(pronoun_cues(self.cur), [])

    def test_an_instruction_that_says_it_for_the_thing_is_listed(self):
        snow = self.cur.by_id["mer_finnst_snjorinn_fallegur"]
        old = dataclasses.replace(snow, situation="Your neighbour complains about the snow. Say you think it's beautiful.", partner_cue_situation="")
        cur = dataclasses.replace(self.cur, items=[old])
        self.assertEqual([(i, w) for i, _, w in pronoun_cues(cur)], [("mer_finnst_snjorinn_fallegur", ["snow"])])

    def test_it_that_the_answer_says_too_is_not(self):
        # «Mér finnst það gott.»: the answer says «það» as the instruction says «it»
        self.assertNotIn("mer_finnst_thad_gott", [i for i, _, _ in pronoun_cues(self.cur)])


if __name__ == "__main__":
    unittest.main()
