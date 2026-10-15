"""#294: an item selected for the target and left untaught still lets the second half start."""
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from audiolesson.cando import load_cando
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
            return chosen[:-1] if len(calls) == 1 and len(chosen) > 1 else chosen  # charged by select_new, never queued: the two counters disagree

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

    def test_a_normal_lesson_does_not_use_the_guard(self):
        sc = self.lesson(drop_last_selected=False)
        self.assertTrue(sc.meta["target_delivered"])
        self.assertFalse(sc.meta["rotation_guard"])


if __name__ == "__main__":
    unittest.main()
