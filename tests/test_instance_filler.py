"""#311: a phrase that is a known pattern with a new word teaches the word, in other frames."""
import copy
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum, unlinked_instances
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class LinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_no_phrase_of_the_curriculum_is_an_unlinked_pattern_instance(self):
        self.assertEqual(unlinked_instances(self.cur), [])

    def test_an_unlinked_one_is_found(self):
        cur = copy.deepcopy(self.cur)
        item = cur.by_id["eg_tharf_ulpu"]
        item.instance_of, item.instance_fill = "", {}
        self.assertEqual(unlinked_instances(cur), [("eg_tharf_ulpu", "eg_tharf", "thing", "ulpu", "")])

    def test_ulpu_is_linked_to_its_pattern(self):
        item = self.cur.by_id["eg_tharf_ulpu"]
        self.assertEqual((item.instance_of, item.instance_fill), ("eg_tharf", {"thing": "ulpu"}))


class ParallelsTests(unittest.TestCase):
    def test_no_lesson_gets_more_than_a_few_parallels_of_one_pattern(self):
        """#316 review (§3, §9 "A pattern is not a lesson's whole supply": about ten is a ceiling, not a target): the thirty links hand a passed phrase's practice to
        its pattern's other instances (#192), which must not make a run of one pattern with random fillers."""
        from collections import defaultdict
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day = LearnerState("is", "en", "A1"), date(2026, 9, 1)
        worst = 0
        for _ in range(70):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
            apply_to_learner(sc, learner, day)
            by = defaultdict(set)
            for e in sc.exercises:
                if e.kind == "generative":
                    by[e.item_ids[0]].add(e.label)
            worst = max(worst, max((len(v) for v in by.values()), default=0))
            day += timedelta(days=1)
        self.assertLessEqual(worst, 10)


class IntroductionTests(unittest.TestCase):
    def lesson_with(self, item_id, upto=80):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day = LearnerState("is", "en", "A1"), date(2026, 9, 1)
        for _ in range(upto):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
            apply_to_learner(sc, learner, day)
            if item_id in sc.meta["new_items"]:
                return sc
            day += timedelta(days=1)
        self.fail(f"{item_id} was not introduced in {upto} lessons")

    def test_the_new_word_is_taught_as_a_word_and_met_in_other_frames(self):
        sc = self.lesson_with("eg_tharf_ulpu")
        self.assertIn("ulpu", sc.meta["new_items"], "the word is a new item of the lesson")
        self.assertIn("eg_tharf_ulpu", sc.meta["pattern_instances"], "the phrase is covered as a sentence of its pattern")
        spoken = {g.text for g in sc.segments if g.type in ("speak", "answer") and "úlpu" in (g.text or "")}
        others = spoken - {"Ég þarf úlpu.", "úlpu", "úlpu."}
        self.assertGreaterEqual(len(others), 2, f"úlpu is met in at least two other frames: {others}")

    def test_a_phrase_whose_word_was_taught_inside_it_today_is_not_introduced_again_as_new(self):
        """Lesson 26 of the replay (#316 review): «reikninginn» is taught inside «Get ég fengið reikninginn?», which then came again as «Something new»."""
        sc = self.lesson_with("get_eg_fengid_reikninginn")
        mine = [e for e in sc.exercises if "get_eg_fengid_reikninginn" in e.item_ids]
        self.assertEqual([e.kind for e in mine if e.kind == "intro"], [], "the phrase has no introduction of its own")
        self.assertFalse(any(e.kind == "embed" for e in mine), "#333: the word was taught inside this very phrase, so the sentence is not played again as «a sentence from a pattern you know»")
        self.assertEqual(sum(1 for g in sc.segments if g.type == "narrate" and (g.text or "").startswith("Something new") and "bill" in (g.text or "")), 0)
        self.assertIn("get_eg_fengid_reikninginn", sc.meta["pattern_instances"])

    def test_the_phrase_is_not_asked_as_the_same_sentence_more_than_three_times(self):
        sc = self.lesson_with("eg_tharf_ulpu")
        asked = [e for e in sc.exercises if any(g.type == "answer" and (g.text or "").strip() == "Ég þarf úlpu." for g in sc.segments if g.exercise == e.index)]
        self.assertLessEqual(len(asked), 3)
        self.assertNotIn("eg_tharf_ulpu", sc.meta["repeated_new_sentences"])


if __name__ == "__main__":
    unittest.main()
