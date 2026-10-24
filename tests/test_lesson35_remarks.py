"""Lesson 35's remarks. «To finish, let's go back over today's new material.», then three of the six new items: the announcement says «some of»
when the closing leaves new items out (each said as often as a lesson allows). «latte needs no slow split»: a loanword or a name said much as in
English or Japanese is ``sounds_familiar``, outside the letter rules of the slow, split model (and «Tókýó» would have been split in lesson 37)."""
import unittest
from dataclasses import replace
from pathlib import Path

from datetime import timedelta

from audiolesson.content import CurriculumError, load_curriculum, validate
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing
from audiolesson.sounds import hard_sounds
from tests.test_audiolesson import TODAY, course

ROOT = Path(__file__).resolve().parent.parent


class ClosingAnnouncementTests(unittest.TestCase):
    def test_the_announcement_says_some_exactly_when_the_closing_leaves_new_items_out(self):
        prompts = Prompts.load("en")
        whole, some = prompts.get("final_block"), prompts.get("final_block_some")
        _, scripts = course(12, 30)
        said = set()
        for sc in scripts:
            ann = [e for e in sc.exercises if e.label == "final review"]
            if not ann:
                continue
            text = next(s.text for s in sc.segments if s.exercise == ann[0].index and s.type == "narrate")
            left = sc.meta["closing_left"]
            self.assertEqual(text, some if left else whole, left)
            asked = {i for e in sc.exercises[ann[0].index + 1 :] for i in e.item_ids}
            self.assertEqual(sorted(i for i in sc.meta["new_items"] if i not in asked), sorted(left))
            said.add(text)
        self.assertEqual(said, {whole, some}, "the simulated course has both kinds of closing")

    def test_a_phrase_taught_inside_a_sentence_counts_as_new_material(self):
        """Review of #407: «Ég tala ekki íslensku.» taught as a sentence of its pattern (`embedded`) keeps no closing recall (#192); the closing
        asked «Ég tala íslensku.» and the announcement still said «today's new material»."""
        cur = load_curriculum(ROOT / "curricula/is-en", known_lang="en")
        learner, day, found = LearnerState("is", "en", "A1"), TODAY, []
        for _ in range(20):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=day).build()
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
            ann = [e for e in sc.exercises if e.label == "final review"]
            asked = {i for e in sc.exercises[ann[0].index + 1 :] for i in e.item_ids} if ann else set()
            found += [i for i in sc.meta["embedded_items"] if i not in asked and ann]
            for i in sc.meta["embedded_items"]:
                if ann and i not in asked:
                    self.assertIn(i, sc.meta["closing_left"])
        self.assertTrue(found, "the course has a phrase taught inside a sentence and left out of the closing")


class FamiliarSoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula/is-en", known_lang="en")

    def test_a_loanword_or_a_name_gets_no_slow_split(self):
        for word in ("latte", "tokyo_dat"):
            self.assertTrue(self.cur.by_id[word].sounds_familiar)
            self.assertEqual(hard_sounds(self.cur.by_id[word]), [], word)
        self.assertEqual(hard_sounds(self.cur.by_id["kvittun"]), ["tt"], "an Icelandic word keeps its rule")

    def test_a_familiar_word_has_no_syllables(self):
        cur = load_curriculum(ROOT / "curricula/is-en", known_lang="en")
        latte = cur.by_id["latte"]
        cur.items[cur.items.index(latte)] = cur.by_id["latte"] = replace(latte, syllables=["lat", "te"])
        with self.assertRaisesRegex(CurriculumError, "sounds_familiar"):
            validate(cur)


if __name__ == "__main__":
    unittest.main()
