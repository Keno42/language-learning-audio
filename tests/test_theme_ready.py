"""#327: on the replay of the lesson-36 export, lesson 40 taught two of small talk 4's three lines («Hvað ertu gömul?», «Ég er tuttugu ára.»)
and «Ég er gift.» the next day. All but a quarter of three turns is three, so the level waited and the café's fourth level was played
again over today's lines. A level of three or more learner turns may play with one of them heard (`theme_heard_one`)."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 3, 1)
COMING = {"hvad_ertu_gomul", "eg_er_ara", "tuttugu_ara"}  # small talk 4's first two turns, taught today
LATER = {"eg_er_gift"}  # its third, taught tomorrow


class ThemeHeardOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", cls.cur)
        cls.themes = load_themes(ROOT / "curricula" / "is-en", cls.cur, scenarios)
        cls.order = scenario_order(scenarios)

    def learner(self):
        """Every level played but small talk's fourth; every item known but its three lines' own."""
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.by_id:
            if i not in COMING | LATER:
                learner.items[i] = ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2,
                                             last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=1)).isoformat())
        for t in self.themes:
            learner.themes_done[t.id] = len(t.levels) - (1 if t.id == "smalltalk" else 0)
            learner.themes_last[t.id] = 1
        return learner

    def pick(self, **cfg):
        planner = Planner(self.cur, self.learner(), Prompts.load("en"), Timing(level="A1"),
                          PlanConfig(minutes=30, new_items=0, themes=self.themes, theme_scenarios=self.order, **cfg), today=TODAY)
        return planner.pick_theme(COMING)

    def test_a_level_of_three_plays_with_its_one_untaught_turn_heard(self):
        theme, level, heard = self.pick()
        self.assertEqual((theme.id, level), ("smalltalk", 3), "small talk 4, whose lines this lesson teaches")
        you = [t for t in theme.levels[level].turns if t.who == "you"]
        # the turns not met yet: today's two are asked once taught (`play_theme`); the one whose line comes tomorrow stays heard
        self.assertEqual([you[k].say for k in sorted(heard) if not set(you[k].items) & COMING], ["Ég er gift."])

    def test_without_the_allowance_the_level_waits_for_a_replay(self):
        theme, level, _ = self.pick(theme_heard_one=99)
        self.assertNotEqual(theme.id, "smalltalk", "the old rule: all but a quarter of three is three, so another theme is played again")


if __name__ == "__main__":
    unittest.main()
