"""The trust check in the lessons (the owner, 2026-11-28; G10, #631): the planner says only lines none of whose pairs of neighbouring words is
missing from every Icelandic text (``PlanConfig.trusted``, on by default; ``generate --untrusted`` turns it off). An item, a pattern's
sentence, a theme level, a dialogue or a note with such a pair is passed over; a pair not looked up yet holds nothing back."""

from __future__ import annotations

import dataclasses
import random
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson import trust
from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes
from audiolesson.timing import Timing

IS = Path(__file__).resolve().parent.parent / "curricula" / "is-en"


def course(cur, lessons: int, trusted: bool = True, themes=(), scenarios=()) -> tuple[LearnerState, list]:
    learner, day, scripts = LearnerState("is", "en"), date(2026, 1, 5), []
    for _ in range(lessons):
        cfg = PlanConfig(minutes=30, trusted=trusted, themes=list(themes), theme_scenarios=list(scenarios))
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=day).build()
        apply_to_learner(sc, learner, day)
        day += timedelta(days=1)
        scripts.append(sc)
    return learner, scripts


def said(scripts) -> list[str]:
    return [s.text for sc in scripts for s in sc.segments if s.type in ("speak", "answer") and (s.lang or "").startswith("is") and s.text]


class TrustInLessonsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(IS)
        cls.scenarios = load_cando(IS, cls.cur)
        cls.themes = load_themes(IS, cls.cur, cls.scenarios)

    def table(self, pairs: dict[str, int]):
        return dataclasses.replace(self.cur, trust=trust.Trust(pairs=pairs))

    def planner(self, cur, trusted: bool = True) -> Planner:
        return Planner(cur, LearnerState("is", "en"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, trusted=trusted))

    def test_a_worked_example_takes_an_allowed_filling_or_none(self):
        """Review of #634: a worked example whose sentence the check refuses takes a filling the learner has that it allows; with none (every
        filler refused, or the part taken out next refused itself) there is no example, never the refused one."""
        from audiolesson.exercises import NoAllowedSentence

        pattern = self.cur.by_id["erud_thid_med"]  # «Eruð þið með {thing}?», example «mjólk»
        p = self.planner(self.table({"með mjólk": 0}))
        p.builder.in_lesson.update({"mjolk", "peysu"})
        self.assertEqual(p.builder.worked_example_fills(pattern)["thing"].id, "peysu", "the allowed one the learner has")
        p = self.planner(self.table({"með mjólk": 0, "með peysu": 0}))
        p.builder.in_lesson.update({"mjolk", "peysu"})
        self.assertIsNone(p.builder.worked_example_fills(pattern), "every filler the learner has is refused")
        p = self.planner(self.table({"með mjólk": 0}))
        p.builder.in_lesson.update({"mjolk", "peysu"})
        self.assertIsNone(p.builder.worked_example_fills(pattern, {"thing": self.cur.by_id["mjolk"]}), "the part taken out next is refused itself")
        with self.assertRaises(NoAllowedSentence):
            p2 = self.planner(self.table({"með mjólk": 0, "með peysu": 0}))
            p2.builder.in_lesson.update({"mjolk", "peysu"})
            from audiolesson.script import Script
            p2.builder.recall(Script(1, "t", "is", "en"), pattern, "meaning")

    def test_a_pattern_with_no_allowed_example_waits(self):
        """With every sentence of «Eruð þið með {thing}?» refused, the pattern is never introduced nor said: its turn goes to the next item."""
        fillers = [i for i in self.cur.items_with_tag(self.cur.by_id["erud_thid_med"].slots["thing"], self.cur.by_id["erud_thid_med"])]
        refused = self.table({f"með {i.target.split()[0].lower()}": 0 for i in fillers})
        from audiolesson.themes import scenario_order

        for trusted in (True, False):
            learner, scripts = course(refused, 3, trusted=trusted, themes=self.themes, scenarios=scenario_order(self.scenarios))
            said_it = [t for t in said(scripts) if t.startswith("Eruð þið með")]
            if trusted:
                self.assertEqual(said_it, [])
                self.assertNotIn("erud_thid_med", learner.items)
            else:
                self.assertTrue(said_it, "the course does teach it without the check")

    def test_a_pattern_never_makes_a_sentence_with_a_pair_no_text_has(self):
        pattern = self.cur.by_id["erud_thid_med"]  # «Eruð þið með {thing}?»
        for trusted, expect in ((True, set()), (False, {"poka"})):
            p = self.planner(self.table({"með poka": 0}), trusted)
            p.builder.in_lesson.update({"poka", "peysu", "ulpu"})
            p.builder.rng = random.Random(3)
            made = {p.builder.generate(pattern, prefer_unused=False).fills["thing"].id for _ in range(40)}
            self.assertEqual(made & {"poka"}, expect, trusted)

    def test_a_worked_example_takes_another_filler_when_its_sentence_has_such_a_pair(self):
        pattern = self.cur.by_id["erud_thid_med"]  # the authored example is «mjólk»
        p = self.planner(self.table({"með mjólk": 0}))
        p.builder.in_lesson.update({"mjolk", "poka"})
        self.assertEqual(p.builder.worked_example_fills(pattern)["thing"].id, "poka")
        p = self.planner(self.table({"með mjólk": 0}), trusted=False)
        p.builder.in_lesson.update({"mjolk", "poka"})
        self.assertEqual(p.builder.worked_example_fills(pattern)["thing"].id, "mjolk")

    def test_an_item_whose_line_has_such_a_pair_is_not_taught(self):
        cur = self.table({"góðan daginn": 0})
        for trusted in (True, False):
            learner, _ = course(cur, 3, trusted)
            self.assertEqual(learner.has_met("godan_daginn"), not trusted, trusted)

    def test_a_theme_level_with_such_a_line_is_passed_over(self):
        # supermarket 1 opens on «Afsakið, eruð þið með skyr?»: with «með skyr» in no text the scene goes on at its second level
        for pairs, played in (({}, True), ({"með skyr": 0}, False)):
            learner, _ = course(self.table(pairs), 4, themes=self.themes, scenarios=[s.id for s in self.scenarios])
            self.assertEqual("supermarket:1" in learner.levels_last, played, pairs)

    def test_the_setting_is_recorded_and_can_be_turned_off(self):
        for trusted in (True, False):
            _, scripts = course(self.table({}), 1, trusted)
            self.assertEqual(scripts[0].meta["config"]["trusted"], trusted)
        _, scripts = course(dataclasses.replace(self.cur, trust=None), 1)
        self.assertFalse(scripts[0].meta["config"]["trusted"])  # a course without the table says everything

    def test_the_lessons_say_no_line_the_courses_table_calls_unusual(self):
        if self.cur.trust is None:
            self.skipTest("curricula/is-en/trust/pairs.json is not built yet: python tools/attest_pairs.py curricula/is-en")
        _, scripts = course(self.cur, 20, themes=self.themes, scenarios=[s.id for s in self.scenarios])
        unusual = sorted({t for t in said(scripts) if not self.cur.trust.usual(t)})
        self.assertEqual(unusual, [])


if __name__ == "__main__":
    unittest.main()
