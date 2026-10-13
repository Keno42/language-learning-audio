"""#302: the «Slowly.» model is word by word at natural speed (as #261's reply), never stretched sounds."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class SlowModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def intro(self, item_id):
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        b.intro(sc, self.cur.by_id[item_id])
        return sc

    def test_a_line_of_several_words_is_said_slowly_word_by_word_at_natural_speed(self):
        item = next(i for i in self.cur.items if i.kind == "phrase" and i.difficulty >= 2 and i.word_count >= 3 and not i.is_hard() and not i.noun)
        sc = self.intro(item.id)
        spaced = [g for g in sc.segments if g.role == "spaced"]
        self.assertGreaterEqual(len(spaced), item.word_count)
        self.assertTrue(all(g.rate == 1.0 for g in spaced), "natural speed")
        self.assertEqual(" ".join(g.text for g in spaced[: item.word_count]), item.target)
        gaps = [g for g in sc.segments if g.role == "word_gap"]
        self.assertTrue(gaps and all(g.duration == Timing().intro_word_gap and g.floor == g.duration for g in gaps))
        self.assertIn("(word by word)", sc.transcript())

    def test_no_introduction_of_a_line_of_several_words_has_a_stretched_segment(self):
        for item in self.cur.items:
            if item.kind != "phrase" or item.word_count < 2 or item.noun:
                continue
            sc = self.intro(item.id)
            stretched = [g.text for g in sc.segments if g.type == "speak" and g.rate < 1 and len(g.text.split()) > 1]
            self.assertEqual(stretched, [], item.id)

    def test_the_repeat_pause_after_a_spaced_model_adds_the_gaps(self):
        """#302 review: the learner repeats word by word, so the pause is the natural one plus (words − 1) gaps."""
        item = next(i for i in self.cur.items if i.kind == "phrase" and i.difficulty >= 2 and i.word_count >= 3 and not i.is_hard() and not i.noun)
        sc = self.intro(item.id)
        timing = Timing(level="A1")
        natural = timing.repeat_pause(item.target, "is")
        gaps = (item.word_count - 1) * timing.intro_word_gap
        slow_at = max(i for i, g in enumerate(sc.segments) if g.role == "spaced")
        after = next(g for g in sc.segments[slow_at:] if g.type == "pause" and g.role == "repeat")
        self.assertAlmostEqual(after.duration, natural + gaps, places=2)
        self.assertGreaterEqual(after.floor, timing.min_pause + gaps)

    def test_a_hard_word_keeps_its_syllable_split(self):
        sc = self.intro("jokull")
        self.assertEqual([g.text for g in sc.segments if g.type == "speak" and g.rate < 1], ["jö", "kull"])


if __name__ == "__main__":
    unittest.main()
