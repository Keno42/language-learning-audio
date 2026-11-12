"""H9, lesson 54: the pace's backlog counted every item due by its date. 15 of lesson 54's 72 had been asked by the learner's own review that
morning (the lesson does not ask them again, #238) and one was gone from the course, so the lesson could ask 56: the count the pace reads."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


def due(**changes) -> ItemState:
    return ItemState(**{"stage": "meaning", "successes": 4, "durable_successes": 1, "recalled": 1, "last_outcome": "recalled",
                        "due": (TODAY - timedelta(days=1)).isoformat(), "last_practiced": (TODAY - timedelta(days=4)).isoformat(), **changes})


class DueAskableTests(unittest.TestCase):
    def learner(self) -> LearnerState:
        learner = LearnerState("is", "en", "A1")
        learner.items["takk"] = due()
        learner.items["godan_daginn"] = due(last_reviewed=TODAY.isoformat(), last_outcome="hesitated")  # asked this morning, still due
        learner.items["gone_from_the_course"] = due()
        learner.items["bless"] = due(due=(TODAY + timedelta(days=9)).isoformat())  # not due
        return learner

    def test_an_item_the_review_asked_today_or_gone_from_the_course_is_not_counted(self):
        learner = self.learner()
        self.assertEqual(learner.due_count(TODAY), 2, "without the course: due and not asked today")
        self.assertEqual(learner.due_count(TODAY, frozenset({"takk", "godan_daginn", "bless"})), 1)
        self.assertEqual(learner.due_count(TODAY + timedelta(days=1), frozenset({"takk", "godan_daginn", "bless"})), 2, "the next day it can be asked again")

    def test_the_backlog_rule_reads_what_the_lesson_can_ask(self):
        """The backlog slows a lesson when the due items exceed about four fifths of its review slots. Seventy due by date, forty of them asked
        by the review that morning: the lesson can ask thirty, and the target holds."""
        learner = LearnerState("is", "en", "A1")
        learner.lessons_completed = 30
        learner.new_target = 8.0
        course = frozenset(f"i{k}" for k in range(70))
        for k in range(70):
            learner.items[f"i{k}"] = due(last_reviewed=TODAY.isoformat() if k < 40 else "")
        target, why = learner.suggest_target(30, TODAY, course)
        self.assertEqual(target, 8.0, why)
        self.assertNotIn("review slots", why)
        for k in range(70):
            learner.items[f"i{k}"].last_reviewed = ""
        target, why = learner.suggest_target(30, TODAY, course)
        self.assertEqual(target, 7.0)
        self.assertIn("70 items due", why)

    def rising(self, lessons):
        """A learner at a target of 7 whose latest new items were all recalled, with 50 items due (a backlog over half the review slots)."""
        learner = LearnerState("is", "en", "A1")
        learner.new_target = 7.0
        learner.lessons_completed = len(lessons)
        learner.lessons = lessons
        learner.reported = [le["number"] for le in lessons]
        for le in lessons:
            for i in le["new_items"]:
                learner.items[i] = ItemState(stage="meaning", successes=3, recalled=1, last_outcome="recalled", introduced_lesson=le["number"],
                                             due=(TODAY + timedelta(days=20)).isoformat(), history=[{"lesson": le["number"], "stages": ["intro"], "ok": True, "outcome": "recalled"}])
        for k in range(50):
            learner.items[f"d{k}"] = due()
        return learner

    def lesson(self, n, **record):
        return {"number": n, "date": (TODAY - timedelta(days=4 - n)).isoformat(), "new_items": [f"n{n}_{k}" for k in range(8)], **record}

    def test_a_rise_reads_whether_the_last_lessons_due_reviews_fitted(self):
        """The owner, 2026-11-12. Lesson 54 was «light» at a target of 7 and fitted 54 of its 56 due reviews; a rise waited for the due items to
        fall under half the review slots, which about fifty due a day never do. What the last lesson did decides: its reviews fitted."""
        fitted = self.rising([self.lesson(1), self.lesson(2), self.lesson(3, due_at_start=56, due_not_fitted=2)])
        target, why = fitted.suggest_target(30, TODAY)
        self.assertEqual(target, 8.0, why)
        self.assertIn("the last lesson's due reviews fitted", why)
        left = self.rising([self.lesson(1), self.lesson(2), self.lesson(3, due_at_start=56, due_not_fitted=9)])
        self.assertEqual(left.suggest_target(30, TODAY)[0], 7.0, "nine of 56 left: more than a tenth, no rise (and under a quarter, no fall)")
        old = self.rising([self.lesson(1), self.lesson(2), self.lesson(3)])
        self.assertEqual(old.suggest_target(30, TODAY)[0], 7.0, "no record of what fitted: the estimate stands, and 50 due is over half the slots")

    def test_a_lesson_records_what_it_could_ask_and_each_unfitted_item_once(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        early = [i.id for i in cur.items if i.kind == "phrase"][:12]
        for k, i in enumerate(early):
            learner.items[i] = due(last_reviewed=TODAY.isoformat() if k < 4 else "")
        learner.items["gone_from_the_course"] = due()
        learner.lessons_completed = 20
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY).build()
        self.assertEqual((sc.meta["due_at_start"], sc.meta["due_by_date"]), (8, 13))
        self.assertEqual(len(sc.meta["due_not_fitted"]), len(set(sc.meta["due_not_fitted"])))
        # review of #526: the description promised both counts in plan.json; ``_plan`` exported neither
        from audiolesson.cli import _plan

        plan = _plan(sc, cur)
        self.assertEqual((plan["due_at_start"], plan["due_by_date"]), (8, 13))
        self.assertEqual(plan["due_not_fitted"], sc.meta["due_not_fitted"])


if __name__ == "__main__":
    unittest.main()
