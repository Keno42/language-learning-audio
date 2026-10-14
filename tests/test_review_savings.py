"""#220: the lesson time a 言えた at the review would save, by older item."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cli import SAVINGS_STAGES, _plan, review_savings
from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class SavingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day = LearnerState("is", "en", "A1"), date(2026, 9, 1)
        for _ in range(14):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
            if _ == 13:
                cls.sc, cls.cur = sc, cur
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)

    def test_only_same_form_recalls_of_older_items_count(self):
        savings = review_savings(self.sc)
        self.assertTrue(savings)
        skip = set(self.sc.meta["new_items"]) | set(self.sc.meta.get("embedded_items", [])) | set(self.sc.meta.get("open_items", [])) | set(self.sc.meta.get("open_not_fitted", []))
        self.assertFalse(set(savings) & skip, "a new or open item is not a saving: its practice stays")
        for item, seconds in savings.items():
            asked = [e for e in self.sc.exercises if e.kind == "recall" and e.stage in SAVINGS_STAGES and e.item_ids[:1] == [item]]
            self.assertTrue(asked, item)
            self.assertAlmostEqual(seconds, sum(e.duration for e in asked), delta=0.1 * len(asked), msg=item)

    def test_recombine_runs_are_not_savings(self):
        recombine_only = {e.item_ids[0] for e in self.sc.exercises if e.stage == "recombine" and e.item_ids}
        asked_same_form = {e.item_ids[0] for e in self.sc.exercises if e.kind == "recall" and e.stage in SAVINGS_STAGES and e.item_ids}
        self.assertFalse((recombine_only - asked_same_form) & set(review_savings(self.sc)))

    def test_it_is_ordered_most_first_and_in_the_plan(self):
        values = list(review_savings(self.sc).values())
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertEqual(_plan(self.sc, self.cur)["review_savings"], review_savings(self.sc))


if __name__ == "__main__":
    unittest.main()
