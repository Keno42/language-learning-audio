"""Lesson 29: «Þrjá miða, takk.» was asked twice in a row. A word's practice («þrjá» in its pattern) said it, and the pattern's own recall right after
fell back to its authored example, the same sentence: no filler of the slot was known yet («tvo» and «þrjá» met, not learned)."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder, _norm_utterance
from audiolesson.learner import ItemState, LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class PatternRecallFallbackTests(unittest.TestCase):
    def builder(self, met=("tvo_acc", "thrja_acc")):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        learner.items["mida"] = ItemState(stage="meaning", durable_successes=3, successes=8, interval_days=7, recalled=3)
        for i in ("count_mida_takk", *met):  # met in earlier lessons and recalled, not learned yet (one success after a gap)
            learner.items[i] = ItemState(stage="meaning", durable_successes=1, successes=3, interval_days=2, recalled=1, last_outcome="recalled")
        return cur, Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)

    def test_with_no_known_filler_the_recall_takes_a_met_one_not_the_sentence_just_said(self):
        cur, b = self.builder()
        c = cur.by_id["count_mida_takk"]
        self.assertIsNone(b.generate(c), "no filler of the slot is known: the case of lesson 29")
        b.recent_answers = [_norm_utterance("Þrjá miða, takk.")]
        ex = b.recall(Script(1, "t", "is", "en"), c, "meaning")
        self.assertEqual(ex.label.split(": ", 1)[1], "Tvo miða, takk.")  # asked from its scene (lesson 31's verdicts) or its meaning

    def test_with_no_filler_met_the_authored_example_stays(self):
        cur, b = self.builder(met=())
        ex = b.recall(Script(1, "t", "is", "en"), cur.by_id["count_mida_takk"], "meaning")
        self.assertEqual(ex.label.split(": ", 1)[1], "Þrjá miða, takk.")


if __name__ == "__main__":
    unittest.main()
