"""Lesson 46 as generated from the lesson-45 export: «hinum megin við götuna» and «við hliðina á bankanum», reported hard to say, were tried again
as «Let's try to say this sentence … again: Across the street.» with the part alone as the answer, said word by word, and the two models came back to
back. A part with its sentence is tried as that sentence, then built up from its end; two slow models are not played in a row."""
import copy
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class PartRetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_a_part_is_tried_as_its_sentence_then_built_up(self):
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        whole = {"through": "thad_er_direction", "answer": "Það er hinum megin við götuna.", "meaning": "It's across the street."}
        ex = b.slow_word_exercise(sc, self.cur.by_id["hinum_megin_vid_gotuna"], whole)
        segs = [g for g in sc.segments if g.exercise == ex.index]
        self.assertEqual(segs[0].text, "Let's try to say this sentence in Icelandic again: It's across the street.")
        self.assertEqual([g.text for g in segs if g.type == "answer"], ["Það er hinum megin við götuna."], "the sentence is asked, not the part alone")
        tx = sc.transcript()
        at = 0
        for line in ("These words are in it:", "Let's build it up from the end.", "**Speaker A:** götuna", "við · götuna", "megin · við · götuna", "hinum · megin · við · götuna"):
            at = tx.index(line, at)  # each after the one before
        self.assertEqual([g.text for g in segs if g.type == "speak"][-1], "Það er hinum megin við götuna.", "and the sentence at natural speed")

    def test_without_its_sentence_a_part_keeps_the_line_retry(self):
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        ex = b.slow_word_exercise(sc, self.cur.by_id["hinum_megin_vid_gotuna"])
        self.assertEqual([g.text for g in sc.segments if g.exercise == ex.index and g.type == "answer"], ["hinum megin við götuna"])

    def test_two_slow_models_are_not_played_in_a_row(self):
        learner, day = LearnerState("is", "en", "A1"), date(2026, 9, 1)
        found = None
        for _ in range(40):
            sc = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=sc.lesson_number, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
            if {"hinum_megin_vid_gotuna", "vid_hlidina_a_bankanum"} <= set(learner.items):
                found = learner
                break
        self.assertIsNotNone(found)
        owed = copy.deepcopy(found)
        for i in ("hinum_megin_vid_gotuna", "vid_hlidina_a_bankanum"):
            owed.items[i].slow_owed = (day - timedelta(days=1)).isoformat()
        sc = Planner(self.cur, owed, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
        slow = [e for e in sc.exercises if e.kind == "model" and e.stage == "slow"]
        self.assertEqual(len(slow), 2, [e.label for e in slow])
        self.assertTrue(all(e.label.endswith(f"({self.cur.by_id[e.item_ids[0]].target})") for e in slow), "each tried as its sentence")
        spoken = [e for e in sc.exercises if any(g.exercise == e.index and g.duration > 0 for g in sc.segments)]
        for a, c in zip(spoken, spoken[1:]):
            self.assertFalse(a.kind == "model" and c.kind == "model", (a.label, c.label))


if __name__ == "__main__":
    unittest.main()
