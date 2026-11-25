"""#599, lesson 67: the catch task asked what «fætinum» means while the woman lay hurt on the ice. In a scene where the learner would act first, a
level marked ``urgent`` gives no partner line to a catch task (the second half's or an introduction's); its lines can still be pick-outs."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner, catchable_lines
from audiolesson.prompts import Prompts
from audiolesson.themes import Level, Theme, Turn, load_themes
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
IS_EN = Path(__file__).resolve().parent.parent / "curricula" / "is-en"


def level(urgent: bool) -> Level:
    return Level(goal="g", partner_speaker="native_a", urgent=urgent, turns=[
        Turn(who="you", say="Er allt í lagi?", cue="Ask if she's all right.", items=["er_allt_i_lagi"]),
        Turn(who="partner", say="Nei. Mér er illt í fætinum.", meaning="No. My leg hurts.", word_glosses={"fætinum": {"en": "leg", "ja": "足"}}),
    ])


class UrgentLevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(IS_EN)
        cls.themes = load_themes(IS_EN, cls.cur, load_cando(IS_EN))

    def test_an_urgent_level_gives_no_line_to_a_catch(self):
        self.assertEqual(catchable_lines(level(urgent=True)), [])
        self.assertEqual([ln.say for _, _, ln in catchable_lines(level(urgent=False))], ["Nei. Mér er illt í fætinum."])

    def test_nor_to_a_catch_introduction(self):
        from audiolesson.content import Item

        word = Item(id="faetinum_test", kind="vocab", target="fætinum", meaning="leg")
        learner = LearnerState("is", "en", "A1")
        learner.items["hvad_thydir_thetta"] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7,
                                                        last_outcome="recalled", due=(TODAY + timedelta(days=5)).isoformat())
        known = {"nei", "mér", "er", "illt", "í"}

        def task(urgent: bool):
            theme = Theme(scene_line="On the icy path, a woman slips and falls.", id="fall_test", scenario="A1", title="A fall", levels=[level(urgent)])
            planner = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"),
                              PlanConfig(minutes=30, themes=[theme], theme_scenarios=["A1"]), today=TODAY)
            return planner.catch_intro_task(word, known, set())

        calm = task(urgent=False)
        self.assertIsNotNone(calm, "the line qualifies when the level is not urgent (a test that passes with no catch proves nothing)")
        self.assertTrue(calm.source.startswith("theme:fall_test:"), calm.source)
        hurt = task(urgent=True)
        self.assertTrue(hurt is None or not hurt.source.startswith("theme:fall_test:"), hurt and hurt.source)

    def test_the_accidents_first_level_is_urgent_and_its_clinic_is_not(self):
        accident = next(t for t in self.themes if t.id == "accident")
        self.assertEqual([lv.urgent for lv in accident.levels], [True, False])


if __name__ == "__main__":
    unittest.main()
