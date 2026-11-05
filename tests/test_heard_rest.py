"""#483: another learner, on 15-minute lessons, heard the supermarket's first level again in 19 of 20 lessons. A level heard again as spare time
(#218 b1) was drawn at random among every level already played, each lesson anew. It now rests: a level played or heard is not heard again
within ``heard_rest_lessons`` lessons, and the one heard longest ago comes first."""
import unittest
from datetime import timedelta

from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing
from tests import test_audiolesson as base


class HeardRestTests(unittest.TestCase):
    def test_on_short_lessons_no_level_is_heard_again_within_its_rest(self):
        cur, extra = base.SpareTimeTests._cfg()
        learner = LearnerState("is", "en", "A1")
        day, heard_any, last = base.TODAY, 0, {}
        for n in range(1, 15):
            cfg = PlanConfig(minutes=15, seed=1, new_target=4.0, **extra)
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=day).build()
            theme = sc.meta.get("theme") or {}
            own = f"{theme.get('id')}:{theme.get('level')}"
            for key in sc.meta["heard_themes"]:
                if key == own:
                    continue  # the lesson's own scene, heard again after its plays (#238), is this lesson's level, not a rerun
                heard_any += 1
                if key in last:
                    self.assertGreaterEqual(sc.lesson_number - last[key], cfg.heard_rest_lessons, (key, sc.lesson_number, last[key]))
            apply_to_learner(sc, learner, day)
            last.update({k: sc.lesson_number for k in sc.meta["heard_themes"]})
            if theme.get("plays"):
                last[own] = sc.lesson_number
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertGreater(heard_any, 3, "the course heard levels again: the check ran")
        self.assertTrue(learner.levels_last, "the levels heard are recorded")

    def test_the_record_survives_learner_json(self):
        import tempfile
        from pathlib import Path

        learner = LearnerState("is", "en", "A1")
        learner.levels_last = {"supermarket:1": 12, "cafe:2": 14}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "learner.json"
            learner.save(path)
            self.assertEqual(LearnerState.load(path).levels_last, {"supermarket:1": 12, "cafe:2": 14})
        self.assertNotIn("levels_last", LearnerState("is", "en", "A1").to_dict(), "no key until a level is recorded")


if __name__ == "__main__":
    unittest.main()
