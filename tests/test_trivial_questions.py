"""#277: a part is asked through the sentence it was taught in, and a question whose cue is its own answer is never asked."""
import unittest
from datetime import date
from pathlib import Path

from audiolesson.content import curriculum_from_dict, load_curriculum
from audiolesson.exercises import cue_is_answer
from audiolesson.planner import PlanConfig, Planner
from audiolesson.learner import ItemState, LearnerState
from audiolesson.prompts import Prompts
from audiolesson.review_wholes import refine_review
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 3, 1)


def _cur():
    return curriculum_from_dict({
        "curriculum": {"name": "t", "target_lang": "is", "known_lang": "en"},
        "items": [
            {"id": "akureyri", "kind": "vocab", "target": "Akureyri", "meaning": "Akureyri"},
            {"id": "lundi", "kind": "vocab", "target": "lundi", "meaning": "a puffin"},
            {"id": "thetta_lundi", "kind": "phrase", "target": "Þetta er lundi.", "meaning": "This is a puffin."},
        ],
    })


class TrivialQuestionTests(unittest.TestCase):
    def test_a_cue_that_is_its_answer_is_trivial(self):
        cur = _cur()
        self.assertTrue(cue_is_answer(cur.by_id["akureyri"]))
        self.assertFalse(cue_is_answer(cur.by_id["lundi"]))

    def test_the_review_drops_a_trivial_question_that_has_no_whole(self):
        cur = _cur()
        prompts = Prompts.load("en")
        review = [
            {"items": ["akureyri"], "prompt": "Akureyri", "answer": "Akureyri", "stage": "meaning"},
            {"items": ["lundi"], "prompt": "a puffin", "answer": "lundi", "stage": "meaning"},
        ]
        out, report = refine_review(review, cur, {"akureyri", "lundi", "thetta_lundi"}, prompts)
        self.assertEqual([q["items"] for q in out], [["lundi"]])
        self.assertEqual([(r["kind"], r["items"]) for r in report], [("trivial", ["akureyri"]), ("through_whole", ["lundi"])])
        self.assertEqual(out[0]["answer"], "Þetta er lundi.", "a part with a whole is asked through it")

    def test_the_lesson_asks_no_trivial_question_on_the_course(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        for i in cur.items[:60]:
            learner.items[i.id] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=1, new_items=3), today=TODAY).build()
        self.assertEqual(sc.meta["trivial_questions"], [])


if __name__ == "__main__":
    unittest.main()
