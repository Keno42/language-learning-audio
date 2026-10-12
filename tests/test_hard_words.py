"""#212 (H13): a hard-to-say word is heard slowed and split by syllable once, at its introduction."""
import unittest
from pathlib import Path

import tomllib

from audiolesson.content import CurriculumError, curriculum_from_dict, load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.sounds import DECK_RULES, hard_sounds
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class HardWordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_deck_rules_are_cards_of_the_reading_deck(self):
        deck = tomllib.loads((ROOT / "curricula" / "is-en" / "reading" / "deck.toml").read_text(encoding="utf-8"))
        graphemes = {g for card in deck.get("cards", []) for g in card.get("graphemes", [])}
        for rule in DECK_RULES:
            self.assertIn(rule, graphemes, "one source of truth with the letters rules")

    def test_the_signal_is_a_small_share_of_the_vocabulary(self):
        vocab = [i for i in self.cur.items if i.kind == "vocab"]
        flagged = [i for i in vocab if hard_sounds(i)]
        self.assertTrue(flagged)
        self.assertLess(len(flagged) / len(vocab), 0.12, "too coarse: most new words would be flagged")
        for i in ("jokull", "eldfjall", "haett"):
            self.assertTrue(hard_sounds(self.cur.by_id[i]), i)
        self.assertEqual(hard_sounds(self.cur.by_id["takk"]) if "takk" in self.cur.by_id else [], [])

    def test_every_flagged_word_has_authored_syllables(self):
        self.assertEqual([i.id for i in self.cur.items if hard_sounds(i) and not i.syllables], [])

    def test_the_introduction_of_a_flagged_word_is_split_slowly_then_natural(self):
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        item = self.cur.by_id["jokull"]
        b.intro(sc, item)
        slow = [g.text for g in sc.segments if g.type == "speak" and g.rate < 1]
        self.assertEqual([t for t in slow if t in ("jö", "kull")], ["jö", "kull"])
        self.assertIn("Slowly, in parts. Repeat each part.", sc.transcript())
        said = [g.text for g in sc.segments if g.type == "speak" and g.rate == 1.0]
        self.assertEqual(said[-1], "jökull", "natural speed after the parts")

    def test_a_word_with_no_hard_sound_is_introduced_as_before(self):
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        item = next(i for i in self.cur.items if i.kind == "vocab" and i.word_count == 1 and not hard_sounds(i) and not i.is_hard() and i.difficulty < 2)
        b.intro(sc, item)
        self.assertNotIn("in parts", sc.transcript())

    def test_syllables_must_join_to_the_target(self):
        raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": "a", "kind": "vocab", "target": "jökull", "meaning": "glacier", "syllables": ["jö", "kul"]}]}
        with self.assertRaisesRegex(CurriculumError, "syllables"):
            curriculum_from_dict(raw)


if __name__ == "__main__":
    unittest.main()
