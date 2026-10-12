"""#273, the spacing half: the same sentence is not asked twice within a minute where another exercise can come, and a situation is not narrated again right after."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import curriculum_from_dict, load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class SituationRotationTests(unittest.TestCase):
    def test_a_situation_is_not_narrated_again_while_another_variant_has_room(self):
        cur = curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a", "kind": "phrase", "target": "Halló.", "meaning": "Hello.", "situations": ["Greet the driver.", "Greet the neighbour."]},
                {"id": "b", "kind": "phrase", "target": "Takk.", "meaning": "Thanks.", "situations": ["Greet the driver.", "Thank the cashier."]},
            ],
        })
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        first = b._situation(cur.by_id["a"])
        second = b._situation(cur.by_id["b"])
        self.assertNotEqual(first, second)


class SpacingOverACourseTests(unittest.TestCase):
    def test_a_sentence_is_rarely_asked_twice_within_a_minute_once_the_course_has_material(self):
        """#273 review: the first version deferred a timed recall by a minute but step 5's fallbacks pulled the same entry straight back. Pinned on the
        real curriculum's lessons 17–22 (a simulated course, seed 1): the row stays well under the ~40 it counted before the fallbacks respected the spacing."""
        from audiolesson.planner import PlanConfig, Planner, apply_to_learner

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = date(2026, 3, 1)
        late = 0
        for n in range(1, 23):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_target=8, seed=1), today=day).build()
            if n >= 17:
                late += sc.meta["asked_again_within_spacing"]
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertLessEqual(late, 40)


if __name__ == "__main__":
    unittest.main()
