"""#287: «Use it in a sentence.» / «Use the pattern again.» are said only when the exercise just before practised the same item or pattern."""
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
TODAY = date(2026, 3, 1)


class RecombineWordingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def first_narration(self, sc, ex):
        return next(g.text for g in sc.segments if g.type == "narrate" and g.exercise == ex.index)

    def test_a_vocab_recombine_after_something_else_names_nothing_it_cannot_keep(self):
        from audiolesson.content import curriculum_from_dict
        from audiolesson.learner import ItemState

        cur = curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "tvo", "kind": "vocab", "target": "tvo", "meaning": "two", "tags": ["c"]},
                {"id": "thrja", "kind": "vocab", "target": "þrjá", "meaning": "three", "tags": ["c"]},
                {"id": "fjora", "kind": "vocab", "target": "fjóra", "meaning": "four", "tags": ["c"]},
                {"id": "pat", "kind": "construction", "target": "{count} miða, takk.", "meaning": "{count} tickets, please.", "slots": {"count": "c"}, "example": {"count": "tvo"}},
                {"id": "pat2", "kind": "construction", "target": "Ég vil {count} miða.", "meaning": "I want {count} tickets.", "slots": {"count": "c"}, "example": {"count": "tvo"}},
                {"id": "hae", "kind": "phrase", "target": "Halló.", "meaning": "Hello."},
            ],
        })
        for lang, plain, linked in (("en", "In a sentence.", "Use it in a sentence."), ("ja", "文で言ってください。", "文の中で使ってください。")):
            learner = LearnerState("is", lang, "A1")
            for i in ("tvo", "thrja", "fjora", "pat", "pat2", "hae"):
                learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3, due=(TODAY + timedelta(days=5)).isoformat(), last_practiced=(TODAY - timedelta(days=2)).isoformat())
            b = Builder(cur, Prompts.load(lang), Timing(level="A1"), learner)
            sc = Script(1, "t", "is", lang)
            b.recall(sc, cur.by_id["hae"], "meaning")  # something else just before
            item = cur.by_id["thrja"]
            ex = b.recall(sc, item, "recombine")
            self.assertEqual(ex.kind, "generative")
            self.assertTrue(self.first_narration(sc, ex).startswith(plain), (lang, self.first_narration(sc, ex)))
            again = b.recall(sc, item, "recombine")
            self.assertEqual(again.kind, "generative")
            self.assertTrue(self.first_narration(sc, again).startswith(linked), (lang, "right after an exercise that practised the item"))

    def test_no_lesson_of_a_course_promises_a_link_it_does_not_keep(self):
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        checked = 0
        for n in range(1, 13):
            sc = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_target=8, seed=1), today=day).build()
            self.assertEqual(sc.meta["unkept_links"], [], n)
            checked += sum(1 for e in sc.exercises if e.kind == "generative" and e.stage == "recombine")
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertGreaterEqual(checked, 5)  # the check is on `unkept_links`; the floor only says the course had recombines at all, whatever the order of a lesson


if __name__ == "__main__":
    unittest.main()


class ApplyInASentenceTests(unittest.TestCase):
    """#287 step 2: the first reactivation of today's new part applies it in a sentence where a known pattern takes it."""

    def test_a_new_part_with_a_known_pattern_is_first_reactivated_as_a_recombine(self):
        from audiolesson.content import curriculum_from_dict
        from audiolesson.learner import ItemState

        cur = curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "tvo", "kind": "vocab", "target": "tvo", "meaning": "two", "tags": ["c"]},
                {"id": "thrja", "kind": "vocab", "target": "þrjá", "meaning": "three", "tags": ["c"]},
                {"id": "fjora", "kind": "vocab", "target": "fjóra", "meaning": "four", "tags": ["c"]},
                {"id": "pat", "kind": "construction", "target": "{count} miða, takk.", "meaning": "{count} tickets, please.", "slots": {"count": "c"}, "example": {"count": "tvo"}},
                {"id": "pat2", "kind": "construction", "target": "Ég vil {count} miða.", "meaning": "I want {count} tickets.", "slots": {"count": "c"}, "example": {"count": "tvo"}},
                *({"id": f"r{n}", "kind": "phrase", "target": f"Rifja {n}.", "meaning": f"Review {n}."} for n in range(10)),
            ],
        })
        learner = LearnerState("is", "en", "A1")
        for i in ("tvo", "pat", "pat2", *(f"r{n}" for n in range(10))):
            due = TODAY - timedelta(days=1) if i.startswith("r") else TODAY + timedelta(days=5)
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3, due=due.isoformat(), last_practiced=(TODAY - timedelta(days=8)).isoformat())
        learner.lessons_completed = 4
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, new_items=1, max_new_items=1, priority=["thrja"], seed=3), today=TODAY).build()
        self.assertIn("thrja", sc.meta["new_items"])
        self.assertEqual(sc.meta["apply_in_sentence_parts"].count("thrja"), 1, "at most one per new part")
        self.assertTrue(any(e.kind == "generative" and e.item_ids[0] == "thrja" for e in sc.exercises), "applied in a sentence")
        # right after the part's own retrieval, so «Use it in a sentence.» is true (#291 review)
        k = next(i for i, e in enumerate(sc.exercises) if e.kind == "generative" and e.item_ids[0] == "thrja")
        self.assertIn("thrja", sc.exercises[k - 1].item_ids)
        said = next(g.text for g in sc.segments if g.type == "narrate" and g.exercise == k)
        self.assertTrue(said.startswith("Use it in a sentence."), said)
