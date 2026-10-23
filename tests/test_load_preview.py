"""CURRENT-STATUS «Now» 3: the feedback form says what a load answer will change. Another learner: «変わらなかったから最近フィードバック
してなかった»; a single «light» raises the target only after another «light» (with at most 25% of new items failed and a small backlog), and
«heavy» only blocks a rise (LEARNING-DESIGN §9 "Pace"). ``LearnerState.load_preview`` gives the next lesson's target for each answer, from
``suggest_target`` run on copies, so the bot can show it beside the choice. The states below show where the answers differ and where they
do not: most often they do not."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cli import main
from audiolesson.learner import NEW_TARGET_MAX, ItemState, LearnerState

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 3, 10)  # the day of the next lesson; lessons 1–3 were on the three days before


def learner(failed=0, loads=(None, None), due=0, rate=9.0, reported_last=False):
    """Three lessons of ten new items each. Lessons 1 and 2 are reviewed, with ``failed`` of their new items failed, and rated
    ``loads``; lesson 3, the latest, is not reviewed yet (its form comes first) unless ``reported_last``. ``due``: other items due."""
    l = LearnerState("is", "en", "A1")
    l.new_target, l.pace, l.lessons_completed = rate, 6, 3
    left = failed
    for n in (1, 2, 3):
        day = TODAY - timedelta(days=4 - n)
        ids = [f"i{n}_{k}" for k in range(10)]
        for i in ids:
            ok = not (n < 3 and left > 0)
            left -= not ok
            l.items[i] = ItemState(stage="meaning", interval_days=1 if n == 3 else 3, last_practiced=day.isoformat(), introduced_lesson=n,
                                   due=(day + timedelta(days=1) if n == 3 else TODAY + timedelta(days=2)).isoformat(),
                                   history=[{"lesson": n, "stages": ["intro", "meaning"], "ok": ok}])
        l.lessons.append({"number": n, "date": day.isoformat(), "new_items": ids, **({"load": loads[n - 1]} if n < 3 and loads[n - 1] else {})})
        if n < 3 or reported_last:
            l.reported.append(n)
    for k in range(due):
        l.items[f"old{k}"] = ItemState(stage="meaning", interval_days=7, due=(TODAY - timedelta(days=1)).isoformat())
    return l


def rates(l, minutes=30):
    p = l.load_preview(minutes, TODAY)
    return {load: p[load]["rate"] for load in p}


class LoadPreviewTests(unittest.TestCase):
    def test_the_learner_is_unchanged(self):
        l = learner()
        before = json.dumps(l.to_dict(), sort_keys=True)
        l.load_preview(30, TODAY)
        self.assertEqual(json.dumps(l.to_dict(), sort_keys=True), before)

    def test_the_latest_lesson_is_presumed_recalled_until_its_review(self):
        """The form comes before the morning review, and the pace waits for that review (H2): without the presumption every answer
        would hold. A latest lesson already reviewed keeps its outcomes."""
        l = learner()
        self.assertIn("no feedback for the last lesson", l.suggest_target(30, TODAY)[1])
        self.assertEqual(rates(l), {"light": 10.0, "right": 10.0, "heavy": 9.0})
        self.assertIn("0/30 new items failed", l.load_preview(30, TODAY)["right"]["why"])
        reviewed = learner(reported_last=True)
        for i in reviewed.lessons[-1]["new_items"][:5]:
            reviewed.items[i].history[-1]["ok"] = False
        self.assertEqual(rates(reviewed), {"light": 9.0, "right": 9.0, "heavy": 9.0}, "5 of 30 failed in the review (17%): none is presumed")

    def test_a_clean_window_rises_on_light_or_right_and_heavy_holds(self):
        for failed in (0, 3):  # 0% and 10% of the window
            self.assertEqual(rates(learner(failed)), {"light": 10.0, "right": 10.0, "heavy": 9.0}, failed)

    def test_in_the_hold_band_only_a_second_light_changes_anything(self):
        """6 of 30 failed (20%): «light» raises the target only when the lesson rated before was «light» too; after «right», or no
        rating, the three answers give the same target. This is the «変わらなかった» of the other learner."""
        self.assertEqual(rates(learner(6, (None, "light"))), {"light": 10.0, "right": 9.0, "heavy": 9.0})
        for loads in ((None, None), (None, "right"), ("light", "right")):
            self.assertEqual(rates(learner(6, loads)), {"light": 9.0, "right": 9.0, "heavy": 9.0}, loads)

    def test_the_same_target_whatever_the_answer(self):
        cases = {
            "a heavy lesson in the window": (learner(0, ("heavy", "right")), 9.0),
            "a backlog over half the review slots": (learner(0, due=45), 9.0),
            "a backlog over 80% of the review slots": (learner(0, due=70), 8.0),
            "over a quarter failed": (learner(9, (None, "light")), 8.0),
            "at the ceiling": (learner(0, rate=NEW_TARGET_MAX), NEW_TARGET_MAX),
        }
        for name, (l, expected) in cases.items():
            self.assertEqual(rates(l), dict.fromkeys(("light", "right", "heavy"), expected), name)

    def test_a_lesson_of_m_minutes_plans_its_share(self):
        """#242: the rate is per 30 minutes and its rules run at 30; a 15-minute lesson plans half of it, a very short one at least 1."""
        p = learner().load_preview(15, TODAY)
        self.assertEqual({k: (v["rate"], v["target"]) for k, v in p.items()}, {"light": (10.0, 5.0), "right": (10.0, 5.0), "heavy": (9.0, 4.5)})
        self.assertEqual(learner(rate=4.0, due=70).load_preview(3, TODAY)["right"]["target"], 1.0)

    def test_the_command_prints_what_generate_then_plans(self):
        """End to end on the small French course: lesson 2's form previewed, then each answer given and the presumed review reported
        through the CLI, and the next lesson generated: its planned target is the one the preview gave."""
        cur = str(ROOT / "curricula" / "fr-en-a1.toml")
        day = date(2099, 1, 1)
        with tempfile.TemporaryDirectory() as td:
            path, out = Path(td) / "l.json", Path(td) / "out"

            def run(*args):
                with contextlib.redirect_stdout(io.StringIO()) as buf:
                    self.assertEqual(main(list(args)), 0, args)
                return buf.getvalue()

            run("generate", "-c", cur, "-l", str(path), "-o", str(out), "--no-audio", "-m", "15", "--date", day.isoformat())
            new = LearnerState.load(path).lessons[-1]["new_items"]
            run("report", "-l", str(path), "--recalled", ",".join(new), "--gaps", ",".join(f"{i}=1" for i in new), "--date", (day + timedelta(days=1)).isoformat())
            run("generate", "-c", cur, "-l", str(path), "-o", str(out), "--no-audio", "-m", "15", "--date", (day + timedelta(days=1)).isoformat())
            preview = json.loads(run("load-preview", "-l", str(path), "-m", "15"))
            self.assertEqual((preview["next_lesson"], preview["date"], preview["minutes"]), (3, (day + timedelta(days=2)).isoformat(), 15.0),
                             "the date defaults to the day after the latest lesson")
            self.assertEqual(list(preview["answers"]), ["light", "right", "heavy"])
            self.assertNotEqual(preview["answers"]["right"]["rate"], preview["answers"]["heavy"]["rate"], "a state where the answers differ")
            new = LearnerState.load(path).lessons[-1]["new_items"]
            for load, answer in preview["answers"].items():
                given = Path(td) / f"{load}.json"
                shutil.copy(path, given)
                review_day = (day + timedelta(days=2)).isoformat()
                run("report", "-l", str(given), "--load", load, "--date", review_day)
                run("report", "-l", str(given), "--recalled", ",".join(new), "--gaps", ",".join(f"{i}=1" for i in new), "--date", review_day)
                lesson = Path(td) / load
                run("generate", "-c", cur, "-l", str(given), "-o", str(lesson), "--no-audio", "-m", "15", "--date", review_day)
                plan = json.loads(next(lesson.glob("*.plan.json")).read_text())
                self.assertAlmostEqual(plan["new_components"]["target"], answer["target"], msg=load)
                self.assertEqual(LearnerState.load(given).new_target, answer["rate"], load)


if __name__ == "__main__":
    unittest.main()
