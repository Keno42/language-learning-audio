"""#312: the written review asks in its own words."""
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from audiolesson.content import load_curriculum
from audiolesson.prompts import Prompts
from audiolesson.review_wording import LESSON_CUE_KEYS, lesson_cue_count, lesson_cue_meaning, reword_review

ROOT = Path(__file__).resolve().parent.parent


def cues(prompts):
    out = []
    for key in LESSON_CUE_KEYS:
        val = prompts.data[key]
        out += [t.format(meaning="the meaning") for t in (val if isinstance(val, list) else [val])]
    return out


class WordingTests(unittest.TestCase):
    def test_no_review_prompt_keeps_a_lesson_cue_in_any_language(self):
        for lang in ("en", "ja"):
            prompts = Prompts.load(lang)
            review = [{"items": ["a"], "prompt": c, "answer": "x"} for c in cues(prompts)]
            self.assertTrue(review)
            self.assertEqual(lesson_cue_count(review, prompts), len(review), f"{lang}: they are all lesson cues before")
            out = reword_review(review, prompts, "is")
            self.assertEqual(lesson_cue_count(out, prompts), 0, lang)
            self.assertTrue(all("the meaning" in q["prompt"] for q in out), "the meaning is kept")
            self.assertEqual(len({q["prompt"] for q in out}), 1, "all in the one review form")

    def test_the_english_form_is_how_do_you_say(self):
        prompts = Prompts.load("en")
        out = reword_review([{"items": ["a"], "prompt": "Put it together yourself. Say: I want coffee.", "answer": "x"}], prompts, "is")
        self.assertEqual(out[0]["prompt"], "How do you say: I want coffee.")

    def test_a_situation_and_the_plain_meaning_cue_are_kept(self):
        prompts = Prompts.load("en")
        review = [{"items": ["a"], "prompt": "You're at a cafe and want a coffee.", "answer": "x"}, {"items": ["b"], "prompt": "How do you say: thank you", "answer": "y"}, {"items": ["c"], "prompt": "Say: hello", "answer": "z"}]
        self.assertEqual(reword_review(review, prompts, "is"), review)
        self.assertIsNone(lesson_cue_meaning("Say: hello", prompts))

    def test_the_input_is_not_changed(self):
        prompts = Prompts.load("en")
        review = [{"items": ["a"], "prompt": "Your turn. Say: hi", "answer": "x"}]
        reword_review(review, prompts, "is")
        self.assertEqual(review[0]["prompt"], "Your turn. Say: hi")


class CommandTests(unittest.TestCase):
    def test_refine_review_rewords_the_queues_old_questions(self):
        from audiolesson import cli
        stdin = io.StringIO(json.dumps({"review": [{"items": ["takk"], "prompt": "In a sentence. Say: thank you", "answer": "Takk fyrir."}]}))
        out = io.StringIO()
        with mock.patch("sys.stdin", stdin), redirect_stdout(out):
            cli.main(["refine-review", str(ROOT / "curricula" / "is-en"), "-l", "/nonexistent/learner.json"])
        prompts = [q["prompt"] for q in json.loads(out.getvalue())["review"]]
        self.assertTrue(prompts and all("In a sentence" not in p for p in prompts), prompts)

    def test_a_plan_has_no_lesson_cue_in_its_review(self):
        import tempfile
        from datetime import date
        from audiolesson.learner import LearnerState
        from audiolesson.planner import PlanConfig, Planner, apply_to_learner
        from audiolesson.timing import Timing
        from audiolesson.cli import _plan
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day = LearnerState("is", "en", "A1"), date(2026, 9, 1)
        prompts = Prompts.load("en")
        for _ in range(8):
            sc = Planner(cur, learner, prompts, Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=day).build()
            apply_to_learner(sc, learner, day)
            day = date.fromordinal(day.toordinal() + 1)
        plan = _plan(sc, cur)
        self.assertEqual(plan["review_lesson_cues"], 0)
        self.assertEqual(lesson_cue_count(plan["review"], prompts), 0)


if __name__ == "__main__":
    unittest.main()
