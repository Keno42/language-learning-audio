"""#439 (lesson 45): 19 of 48 due reviews were asked and the rest carried over, while today's new sentences came back four or five times and the load
was «light». When the reviews due cannot fit beside today's new items, each new item gives up its second rung (1/10 of the lesson) to them; when they
fit, every rung stays."""
import dataclasses
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class ReviewsStarvedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day = LearnerState("is", "en", "A1"), date(2026, 9, 1)
        for _ in range(14):
            sc = Planner(cls.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=sc.lesson_number, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        cls.learner, cls.day = learner, day

    def build(self, learner, **kw):
        cfg = PlanConfig(minutes=30, seed=1, new_target=8.0, **kw)
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=self.day).build()

    def overdue(self):
        """The course's learner with every item met due today: more reviews than a lesson holds."""
        import copy

        learner = copy.deepcopy(self.learner)
        for st in learner.items.values():
            if st.stage != "intro":
                st.due = self.day.isoformat()
        return learner

    def test_new_items_give_a_rung_to_reviews_that_cannot_fit(self):
        starved = self.build(self.overdue())
        kept = self.build(self.overdue(), starved_skip_rung=None)
        self.assertTrue(starved.meta["reviews_starved"])
        self.assertFalse(kept.meta["reviews_starved"])
        def new_practice(sc):
            new = set(sc.meta["new_items"])
            closing = next((e.index for e in sc.exercises if e.kind == "closing" or e.label == "final review"), len(sc.exercises))
            return sum(1 for e in sc.exercises[:closing] if e.kind == "recall" and e.item_ids and e.item_ids[0] in new)

        self.assertLess(new_practice(starved), new_practice(kept), "today's items are asked less often before the closing")

    def test_every_rung_stays_when_the_reviews_fit(self):
        import copy

        sc = self.build(copy.deepcopy(self.learner))
        self.assertFalse(sc.meta["reviews_starved"])


if __name__ == "__main__":
    unittest.main()
