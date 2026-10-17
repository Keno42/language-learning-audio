"""site_update_notifier#151 review: the bot's form offers every learned item the lesson asked the learner to say, so plan.json describes every item an
exercise names. reviewed_items holds only the items picked for review; «Hæ.» asked in a connection (lesson 5) or «japönsku» in «Ég tala japönsku.»
(lesson 10) were not in it, and the form could not name them."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cli import _plan
from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
ASKED = ("recall", "connect", "generative")


class ExerciseItemsTests(unittest.TestCase):
    def test_every_item_an_exercise_names_is_described(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day = LearnerState("is", "en", "A1"), date(2026, 9, 1)
        outside = set()
        for _ in range(10):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
            plan = _plan(sc, cur)
            described = {d["id"]: d for d in plan["exercise_items"]}
            named = [i for e in plan["exercises"] for i in e["items"]]
            self.assertEqual(list(described), list(dict.fromkeys(named)), "each once, in the order first named")
            self.assertTrue(all(d["target"] for d in described.values()))
            new, reviewed = {d["id"] for d in plan["new_items"]}, {d["id"] for d in plan["reviewed_items"]}
            outside |= {i for e in plan["exercises"] if e["kind"] in ASKED for i in e["items"]} - new - reviewed
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        self.assertTrue(outside, "learned items asked outside reviewed_items exist: the field is what lets the form name them")


if __name__ == "__main__":
    unittest.main()
