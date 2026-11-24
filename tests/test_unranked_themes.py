"""#579 (the owner, 2026-11-24: «do as recommended»): lessons 65 and 66 taught eight and six illness and emergency lines of the pharmacy and the
accident (Tier C, C4), none of them in the scene the lesson played: a theme only a trip profile's boost ranks never played, while the course
order taught its lines for everyone. A theme no profile ranks now plays when the learner can say its next level, as a ranked one does, after
every ranked scenario at the same level; it never decides which new material comes (``theme_target``)."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.themes import Level, Theme, Turn
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent
LINES = ["hjalp", "hringdu_a_sjukrabil"]


class UnrankedThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        level = Level(goal="g", partner_speaker="native_c",
                      turns=[Turn(who="you", say=cls.cur.by_id[i].target, cue="Call for help.", items=[i]) for i in LINES])
        cls.theme = Theme(scene_line="Someone has fallen.", id="accident_test", scenario="C4", title="Accident", levels=[level])

    def _planner(self, met: bool, **cfg) -> Planner:
        learner = LearnerState("is", "en", "A1")
        if met:
            for i in LINES:
                learner.items[i] = ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2,
                                             last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=1)).isoformat())
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"),
                       PlanConfig(minutes=30, themes=[self.theme], theme_scenarios=["A1"], **cfg), today=TODAY)

    def test_an_unranked_level_plays_once_its_lines_are_met(self):
        pick = self._planner(met=True).pick_theme()
        self.assertIsNotNone(pick)
        self.assertEqual((pick[0].id, pick[1]), ("accident_test", 0))

    def test_and_in_the_lesson_that_teaches_its_lines(self):
        pick = self._planner(met=False).pick_theme(coming=set(LINES))
        self.assertEqual(pick[0].id, "accident_test", "a level plays in the lesson that teaches its lines (#365)")

    def test_not_before_its_lines_come(self):
        self.assertIsNone(self._planner(met=False).pick_theme(), "lines never taught: no scene to play")

    def test_it_never_chooses_the_new_material(self):
        planner = self._planner(met=False)
        self.assertIsNone(planner.theme_target())
        self.assertEqual(planner.theme_wants(), [])

    def test_the_old_rule_is_a_setting(self):
        self.assertIsNone(self._planner(met=True, play_unranked=False).pick_theme())


if __name__ == "__main__":
    unittest.main()
