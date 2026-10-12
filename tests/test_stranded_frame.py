"""#270 admission: a known noun whose only frame is unmet brings that frame forward."""
import unittest
from datetime import date, timedelta

from audiolesson.content import curriculum_from_dict
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)


def cur():
    items = [
        {"id": "sturtan", "kind": "vocab", "target": "sturtan", "meaning": "the shower", "tags": ["nom_noun"], "noun": "sturta", "form": "nom_def", "gender": "fem"},
        {"id": "klosettid", "kind": "vocab", "target": "klósettið", "meaning": "the toilet", "tags": ["nom_noun"], "noun": "klosett", "form": "nom_def", "gender": "neut"},
        {"id": "virkar", "kind": "construction", "target": "{thing} virkar ekki.", "meaning": "{thing} doesn't work.", "slots": {"thing": "nom_noun"}, "example": {"thing": "sturtan"}, "prereqs": ["sturtan"]},
    ]
    items += [{"id": f"w{n}", "kind": "phrase", "target": f"Ný lína {n}.", "meaning": f"New line {n}."} for n in range(6)]
    return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})


def learner(met=("sturtan", "klosettid")):
    l = LearnerState("is", "en", "A1")
    for i in met:
        l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3, due=(TODAY + timedelta(days=5)).isoformat(), last_practiced=(TODAY - timedelta(days=2)).isoformat())
    l.lessons_completed = 4
    return l


class StrandedFrameTests(unittest.TestCase):
    def planner(self, l, **kw):
        return Planner(cur(), l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, new_items=2, max_new_items=2, seed=3, **kw), today=TODAY)

    def test_the_frame_of_a_known_noun_comes_first(self):
        p = self.planner(learner())
        self.assertEqual(p.stranded_frame(lambda c: True).id, "virkar")
        chosen = p.select_new(2)
        self.assertEqual(chosen[0].id, "virkar")
        self.assertEqual(p.stranded_placed, ["virkar"])

    def test_nothing_is_brought_forward_when_the_frame_is_met_or_the_noun_is_not(self):
        self.assertIsNone(self.planner(learner(met=("sturtan", "klosettid", "virkar"))).stranded_frame(lambda c: True))
        self.assertIsNone(self.planner(learner(met=("klosettid",))).stranded_frame(lambda c: True), "the noun itself is not known yet")

    def test_a_lesson_teaches_it_and_reports_it(self):
        sc = self.planner(learner()).build()
        self.assertIn("virkar", sc.meta["new_items"])
        self.assertEqual(sc.meta["stranded_frames"], ["virkar"])


if __name__ == "__main__":
    unittest.main()
