"""#294: an item selected for the target and left untaught still lets the second half start, and its charge is given back."""
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from audiolesson.cando import load_cando
from audiolesson.cli import _plan
from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 9, 1)


def planner(cur, learner, extra, day):
    return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0, **extra), today=day)


class RotationGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "curricula" / "is-en"
        cls.cur = load_curriculum(path)
        scenarios = load_cando(path, cls.cur)
        cls.extra = dict(themes=load_themes(path, cls.cur, scenarios), theme_scenarios=scenario_order(scenarios, ()))
        cls.learner = LearnerState("is", "en", "A1")
        day = TODAY
        for _ in range(24):
            apply_to_learner(planner(cls.cur, cls.learner, cls.extra, day).build(), cls.learner, day)
            day += timedelta(days=1)
        cls.day = day

    def lesson(self, drop_last_selected):
        import copy
        learner = copy.deepcopy(self.learner)
        p = planner(self.cur, learner, self.extra, self.day)
        if not drop_last_selected:
            return p.build()
        real = Planner.select_new
        calls = []

        def select_new(self_, *a, **kw):
            chosen = real(self_, *a, **kw)
            calls.append(len(chosen))
            # charged by select_new, never queued: the two counters disagree. Only the first is kept, so the target is far from delivered whatever the
            # selection costs and however the planner counts what it taught
            return chosen[:1] if len(calls) == 1 and len(chosen) > 1 else chosen

        with mock.patch.object(Planner, "select_new", select_new):
            return p.build()

    def test_an_untaught_charged_item_leaves_the_target_undelivered_but_the_second_half_runs(self):
        sc = self.lesson(drop_last_selected=True)
        self.assertFalse(sc.meta["target_delivered"], "the two counters disagree, as in the L30 replay")
        self.assertTrue(sc.meta["rotation_guard"], "the guard started the rotation")
        listening = [e.kind for e in sc.exercises if e.kind in ("pick_out", "catch_unknown")]
        # #339: a word is caught once, ever, and the pick-outs rotate: after 24 lessons the pool of listening work is small, and the second half is the rest of the
        # rotation (scene heard again, today's expressions). It must still run: some listening work, and a lesson of its full length.
        self.assertGreaterEqual(len(listening), 1, "the second half has listening work")
        self.assertGreaterEqual(sc.total_duration / 60, 27.0, "and the lesson is not cut short")

    def test_what_was_charged_and_not_taught_is_given_back(self):
        sc = self.lesson(drop_last_selected=True)
        nc, back, taught = sc.meta["new_components"], sc.meta.get("charge_given_back"), set(sc.meta["new_items"])
        self.assertTrue(back, "the items charged at their selection and never taught are named")
        self.assertFalse(set(back) & taught, "only items the lesson did not teach")
        self.assertLessEqual(set(nc["by_item"]), taught, "new_components counts what the lesson taught")
        self.assertEqual(nc["total"], round(sum(nc["by_item"].values()), 2))
        self.assertLess(nc["total"], nc["target"], "«X of a target Y» says the target was not taught, as target_delivered does")
        self.assertEqual(_plan(sc, self.cur)["new_components"], nc, "plan.json says the same")

    def test_a_taught_item_that_shared_words_with_an_untaught_one_costs_what_it_brought(self):
        """Review of #404: «Ég er svöng.» charged first (ég, er, svöng, svangur: 4), «Ég er þyrst.» after it (þyrst, þyrstur: 2, «ég er» counted
        as known). When only the second is taught, its words «ég» and «er» are new after all: giving back the first's 4 left 2 where the
        lesson taught 4. The taught items are charged again from what the learner knew when the lesson began."""
        from audiolesson.timing import Timing
        cur = load_curriculum(Path(__file__).resolve().parent.parent / "curricula" / "is-en")
        p = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_target=8))
        first, second = cur.by_id["eg_er_svong"], cur.by_id["eg_er_thyrst"]
        self.assertEqual((p._charge(first), p._charge(second)), (4.0, 2.0))
        back = p._give_back_untaught({second.id})
        self.assertEqual(back, {first.id: 4.0})
        self.assertEqual((p.components_total, p.component_by_item), (4.0, {second.id: 4.0}))
        self.assertEqual(p._give_back_untaught({second.id}), {}, "nothing more to give back: the total stays")
        self.assertEqual(p.components_total, 4.0)

    def test_a_normal_lesson_does_not_use_the_guard(self):
        # premise changed (#339's pick-out values): which simulated lesson delivers its target depends on the course's path (the 25th now
        # runs out at 7.5 of 8), so the normal lesson is the first of the next few that delivers it
        import copy
        learner, day = copy.deepcopy(self.learner), self.day
        for _ in range(5):
            sc = planner(self.cur, learner, self.extra, day).build()
            if sc.meta["target_delivered"]:
                break
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        self.assertTrue(sc.meta["target_delivered"], "one of five lessons delivers its target")
        self.assertFalse(sc.meta["rotation_guard"])
        self.assertNotIn("charge_given_back", sc.meta, "everything charged was taught: nothing to give back")


if __name__ == "__main__":
    unittest.main()
