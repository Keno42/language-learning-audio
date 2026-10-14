"""#327 part 1: the day's new material is a group of one scene (topic), and the scene played matches it where a theme exists."""
import unittest
from datetime import date
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import curriculum_from_dict, load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.themes import Theme, load_themes, scenario_order
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
IS_EN = Path(__file__).resolve().parent.parent / "curricula" / "is-en"


def cur():
    topics = {"a": ["social"], "b": ["cafe"], "c": ["social"], "d": ["social"], "e": ["cafe"], "f": ["cafe"]}
    items = [{"id": k, "kind": "phrase", "target": f"Lína {k}.", "meaning": f"Line {k}.", "topics": t} for k, t in topics.items()]
    return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})


def planner(learner=None, themes=(), **kw):
    learner = learner or LearnerState("is", "en", "A1")
    cfg = PlanConfig(minutes=10, new_items=3, max_new_items=3, seed=1, themes=list(themes), **kw)
    return Planner(cur(), learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)


def cafe_theme():
    return Theme(id="cafe", scenario="A4", title="Café", topics=["cafe"], levels=[])  # no levels: all of them are played


def just_played():
    l = LearnerState("is", "en", "A1")
    l.themes_done["cafe"] = 1
    l.themes_last["cafe"] = 6  # the lesson before: not to be played again yet
    l.lessons_completed = 6
    return l


class SceneGroupTests(unittest.TestCase):
    def ids(self, p, n=3):
        return [i.id for i in p.select_new(n)]

    def test_with_no_scene_to_play_the_first_items_topic_is_the_group(self):
        p = planner(just_played(), themes=[cafe_theme()], theme_scenarios=["A4"])
        self.assertEqual(self.ids(p, 4), ["a", "c", "d", "b"], "the social lines go ahead of the café line, but only two thirds of the places (3 of 4)")
        self.assertEqual(p.day_topic, "social")

    def test_a_scene_that_can_be_played_takes_the_group_even_when_the_first_item_is_elsewhere(self):
        l = LearnerState("is", "en", "A1")
        l.themes_done["cafe"] = 1
        l.themes_last["cafe"] = 1  # rested: next lesson is far past it
        l.lessons_completed = 6
        p = planner(l, themes=[cafe_theme()], theme_scenarios=["A4"])
        self.assertEqual(self.ids(p), ["b", "e", "a"], "two of three places for the scene, the third in the course order")
        self.assertEqual(p.day_topic, "cafe")

    def test_a_scene_just_played_does_not_take_the_group(self):
        l = LearnerState("is", "en", "A1")
        l.themes_done["cafe"] = 1
        l.lessons_completed = 6
        l.themes_last["cafe"] = 6  # the lesson before
        p = planner(l, themes=[cafe_theme()], theme_scenarios=["A4"])
        self.assertEqual(self.ids(p, 4), ["a", "c", "d", "b"])

    def test_the_trip_order_still_goes_first(self):
        l = LearnerState("is", "en", "A1")
        l.themes_done["cafe"] = 1
        l.themes_last["cafe"] = 1
        l.lessons_completed = 6
        p = planner(l, themes=[cafe_theme()], theme_scenarios=["A4"], priority=["d"])
        self.assertEqual(self.ids(p), ["d", "b", "e"])

    def test_a_first_course_keeps_the_course_order(self):
        self.assertEqual(self.ids(planner()), ["a", "b", "c"])
        self.assertEqual(self.ids(planner(just_played())), ["a", "b", "c"], "no themes configured")
        with_levels = Theme(id="cafe", scenario="A4", title="Café", topics=["cafe"], levels=[{"goal": "g", "turns": []}, {"goal": "h", "turns": []}])
        p = planner(just_played(), themes=[with_levels], theme_scenarios=["A4"])
        self.assertFalse(p.themes_exhausted())
        self.assertEqual(self.ids(p), ["a", "b", "c"], "a theme still has a level to play: the course order and the theme decide")

    def test_the_topic_is_set_once_a_lesson(self):
        p = planner(just_played(), themes=[cafe_theme()], theme_scenarios=["A4"])
        p.select_new(1)
        self.assertEqual(p.day_topic, "social")
        self.assertEqual([i.id for i in p.select_new(3, exclude={"a"})], ["c", "d", "b"], "the same topic in the next arc")


class ThemeMatchTests(unittest.TestCase):
    def setUp(self):
        self.cur = load_curriculum(IS_EN)
        scen = load_cando(IS_EN)
        self.themes = load_themes(IS_EN, self.cur, scen)
        self.order = scenario_order(scen)

    def planner(self, last: dict[str, int]):
        l = LearnerState("is", "en", "A1")
        for t in self.themes:
            l.themes_done[t.id] = len(t.levels)  # every level played: the lesson replays one
            l.themes_last[t.id] = last[t.id]
        l.lessons_completed = 20
        cfg = PlanConfig(minutes=10, new_items=3, seed=1, themes=self.themes, theme_scenarios=self.order)
        return Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)

    def test_the_replayed_scene_is_the_days_topic_when_a_theme_has_it(self):
        last = {t.id: 10 for t in self.themes}
        last["cafe"] = 18  # rested two lessons: not by the old rule (3), by the match rule (2)
        p = self.planner(last)
        p.day_topic = "cafe"
        self.assertEqual(p.pick_theme()[0].id, "cafe")

    def test_without_a_match_the_rule_is_unchanged(self):
        last = {t.id: 10 for t in self.themes}
        last["cafe"] = 18
        p = self.planner(last)
        self.assertNotEqual(p.pick_theme()[0].id, "cafe")
        p.day_topic = "work"  # no theme plays it
        self.assertNotEqual(p.pick_theme()[0].id, "cafe")


if __name__ == "__main__":
    unittest.main()
