"""#410: the replay plans each later lesson as `generate` would. Production works out the pace and the target rate (`plan_pace`) and stores
them once the lesson is built (`keep_pace`), so the next lesson's rules start from them; the replay recomputed them every lesson and stored
nothing, so the lesson whose new items fall outside the played exchange read 40 on the replay of the lesson-36 export and 41 in production."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from audiolesson.content import load_curriculum
from audiolesson.learner import NEW_TARGET_MINUTES, LearnerState, lesson_target
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class PlanPaceTests(unittest.TestCase):
    def test_plan_pace_is_what_generate_works_out_and_keep_pace_stores_it(self):
        learner = LearnerState("is", "en", "A1")
        day = date(2026, 1, 1)
        items, _, rate, _ = learner.plan_pace(30, day)
        self.assertEqual(rate, LearnerState("is", "en", "A1").suggest_target(NEW_TARGET_MINUTES, day)[0])
        learner.keep_pace(items, rate)
        self.assertEqual((learner.pace, learner.new_target), (items, rate))
        learner.keep_pace(None, None)
        self.assertEqual((learner.pace, learner.new_target), (items, rate), "None leaves each as it is")


class ReplayStoresThePaceTests(unittest.TestCase):
    def test_the_replay_stores_what_each_lesson_was_planned_from(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang="en")
        learner = LearnerState(cur.target_lang, cur.known_lang, "A1")
        day = date(2026, 1, 1)
        for _ in range(3):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, new_items=4), today=day).build()
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        planned, kept = [], []
        real_plan, real_keep = LearnerState.plan_pace, LearnerState.keep_pace

        def plan(self, minutes, today):
            out = real_plan(self, minutes, today)
            planned.append((out[0], out[2]))
            return out

        def keep(self, items, rate):
            kept.append((items, rate))
            return real_keep(self, items, rate)

        with tempfile.TemporaryDirectory() as td:
            export = Path(td) / "lesson-004"
            export.mkdir()
            learner.save(export / "learner.before.json")
            manifest = {"lesson": 4, "created_at": f"{day.isoformat()}T08:00:00+09:00", "revisions": {"lla": "test"},
                        "generate_args": ["generate", "--curriculum", "curricula/is-en", "--known", "en", "--minutes", "20"]}
            (export / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            spec = importlib.util.spec_from_file_location("replay_lesson", ROOT / "tools" / "replay_lesson.py")
            tool = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tool)
            out = io.StringIO()
            with mock.patch.object(LearnerState, "plan_pace", plan), mock.patch.object(LearnerState, "keep_pace", keep), contextlib.redirect_stdout(out):
                self.assertEqual(tool.main([str(export), "--lessons", "3", "--curriculum", str(ROOT / "curricula" / "is-en")]), 0)
        self.assertEqual(len(planned), 3)
        self.assertEqual(kept, planned, "each lesson stores the pace and rate it was planned from")
        row = next(line for line in out.getvalue().splitlines() if line.startswith("| target, weighted components (#410"))
        self.assertEqual([c.strip() for c in row.split("|")[2:-1]], [f"{lesson_target(r, 20):g}" for _, r in planned])


if __name__ == "__main__":
    unittest.main()
