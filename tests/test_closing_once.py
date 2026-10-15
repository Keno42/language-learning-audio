"""The closing asks each sentence once (lesson 27 of the replay: «Í miðbæinn, takk.» and «Ljósið virkar ekki.» each twice in a minute)."""
import collections
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class ClosingOnce(unittest.TestCase):
    def test_no_sentence_is_asked_twice_in_the_closing(self):
        """A new item the closing has just made the learner say, as the holder, the pattern or the filler of another new item's sentence («Hvenær?» in
        «Hvenær leggjum við af stað?»), is not asked again. Before the fix lessons 3 and 7 of this course asked one sentence twice."""
        from audiolesson.cando import load_cando
        from audiolesson.themes import load_themes, scenario_order

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        scen = load_cando(ROOT / "curricula" / "is-en")
        themes, order = load_themes(ROOT / "curricula" / "is-en", cur, scen), scenario_order(scen)
        l, day = LearnerState("is", "en", "A1"), date(2026, 3, 1)
        for k in range(1, 8):
            sc = Planner(cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_target=8, themes=themes, theme_scenarios=order), today=day).build()
            start = next(i for i, e in enumerate(sc.exercises) if e.kind == "closing")
            asked = collections.Counter(e.label.split(": ", 1)[-1] for e in sc.exercises[start + 1 :] if e.kind == "recall")
            self.assertEqual([s for s, n in asked.items() if n > 1], [], f"lesson {k}")
            apply_to_learner(sc, l, day)
            l.report([], [], day + timedelta(days=1), lesson_number=k, recalled=sc.meta["new_items"])
            day += timedelta(days=1)


    def test_a_negated_sentence_is_not_the_recall_of_its_affirmative(self):
        """Review of #349: «Ég skil ekki.» holds the words of «Ég skil.» but says the opposite; both keep their own closing recall."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        sc = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, priority=["eg_skil", "eg_skil_ekki"]), today=date(2026, 3, 1)).build()
        self.assertLessEqual({"eg_skil", "eg_skil_ekki"}, set(sc.meta["new_items"]))
        start = next(i for i, e in enumerate(sc.exercises) if e.kind == "closing")
        asked = {e.label.split(": ", 1)[-1]: e.item_ids for e in sc.exercises[start + 1 :] if e.kind == "recall"}
        self.assertIn("Ég skil.", asked)
        self.assertNotIn("eg_skil", asked.get("Ég skil ekki.", []), "the negative answer is not credited to the affirmative phrase")


if __name__ == "__main__":
    unittest.main()
