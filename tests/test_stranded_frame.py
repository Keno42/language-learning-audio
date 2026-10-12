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

    def test_it_takes_the_place_left_over_behind_the_days_own_items_and_brings_no_new_noun(self):
        """#293 review: first, the frame pushed the day's own line out of lesson 24 and pulled a second new noun with it."""
        extra = {"id": "ljosid", "kind": "vocab", "target": "ljósið", "meaning": "the light", "tags": ["nom_noun"], "noun": "ljos", "form": "nom_def", "gender": "neut"}
        raw = cur()
        items = [i for i in raw.items] + [curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": [extra]}).items[0]]
        raw.items[:] = items
        raw.by_id[extra["id"]] = items[-1]
        p = Planner(raw, learner(), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, new_items=2, max_new_items=2, seed=3, priority=["w0", "w1"]), today=TODAY)
        self.assertEqual([i.id for i in p.select_new(2)], ["w0", "w1"], "the day's items keep both places")
        p = Planner(raw, learner(), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, new_items=3, max_new_items=3, seed=3, priority=["w0", "w1"]), today=TODAY)
        chosen = [i.id for i in p.select_new(3)]
        self.assertEqual(chosen[:2], ["w0", "w1"])
        self.assertIn("virkar", chosen)
        self.assertNotIn("ljosid", chosen, "the met nouns «sturtan» and «klósettið» fill it: no new noun comes with it")

    def test_nothing_is_brought_forward_when_the_frame_is_met_or_the_noun_is_not(self):
        self.assertIsNone(self.planner(learner(met=("sturtan", "klosettid", "virkar"))).stranded_frame(lambda c: True))
        self.assertIsNone(self.planner(learner(met=("klosettid",))).stranded_frame(lambda c: True), "the noun itself is not known yet")

    def test_a_lesson_teaches_it_and_reports_it(self):
        sc = self.planner(learner()).build()
        self.assertIn("virkar", sc.meta["new_items"])
        self.assertEqual(sc.meta["stranded_frames"], ["virkar"])


if __name__ == "__main__":
    unittest.main()
