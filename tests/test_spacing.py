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


if __name__ == "__main__":
    unittest.main()
