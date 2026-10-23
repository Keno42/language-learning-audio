"""G17: lesson 31 asked «asking for the same thing more politely» 8 times from its 5 authored pairs. Once every pair had come, any could come
again, the one just asked included. The pair asked is the one said least this lesson, and of those the one said longest ago."""
import random
import unittest
from collections import Counter
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
POLITE = "politeness_get_eg_fengid"


class TransformRotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_every_pair_comes_before_one_comes_again_and_never_twice_in_a_row(self):
        item = self.cur.by_id[POLITE]
        for seed in range(20):
            with self.subTest(seed=seed):
                b = Planner(self.cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30)).builder
                b.rng = random.Random(seed)
                sc = Script(1, "t", "is", "en")
                b._intro_transform(sc, item)
                for _ in range(7):
                    b.recall(sc, item, "meaning")
                asked = [s.text for s in sc.segments if s.type == "speak" and s.role == "source"]
                shown = [e.source for e in item.examples[:2]]  # the introduction's two pairs, heard source and result
                said = Counter(asked + shown)
                self.assertEqual(set(said), {e.source for e in item.examples})
                self.assertLessEqual(max(said.values()) - min(said.values()), 1, said)
                self.assertTrue(all(x != y for x, y in zip(asked, asked[1:])), asked)
                self.assertEqual(len(set(asked[:3])), 3, "the three pairs the introduction did not show come first")


if __name__ == "__main__":
    unittest.main()
