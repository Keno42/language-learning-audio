"""Lesson 35's remarks. «To finish, let's go back over today's new material.», then three of the six new items: the announcement says «some of»
when the closing leaves new items out (each said as often as a lesson allows). «latte needs no slow split»: a loanword or a name said much as in
English or Japanese is ``sounds_familiar``, outside the letter rules of the slow, split model (and «Tókýó» would have been split in lesson 37)."""
import unittest
from dataclasses import replace
from pathlib import Path

from audiolesson.content import CurriculumError, load_curriculum, validate
from audiolesson.prompts import Prompts
from audiolesson.sounds import hard_sounds
from tests.test_audiolesson import course

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
            new = [i for i in sc.meta["new_items"] if i not in sc.meta["embedded_items"]]
            self.assertEqual(sorted(i for i in new if i not in asked), sorted(left))
            said.add(text)
        self.assertEqual(said, {whole, some}, "the simulated course has both kinds of closing")


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
