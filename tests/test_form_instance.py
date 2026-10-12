"""#280: a phrase that is a form of a pattern («Er þetta hættulegt?» of «Er þetta {adj}?») is introduced lightly as that form."""
import unittest
from datetime import date

from audiolesson.content import CurriculumError, curriculum_from_dict
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)


def raw(form="question", target="Er þetta hættulegt?"):
    return {
        "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
        "items": [
            {"id": "haett", "kind": "vocab", "target": "hættulegt", "meaning": "dangerous", "tags": ["adj"]},
            {"id": "pat", "kind": "construction", "target": "Þetta er {adj}.", "meaning": "This is {adj}.", "question": "Er þetta {adj}?", "question_meaning": "Is this {adj}?",
             "slots": {"adj": "adj"}, "example": {"adj": "haett"}, "prereqs": ["haett"]},
            {"id": "ph", "kind": "phrase", "target": target, "meaning": "Is this dangerous?", "prereqs": ["pat"],
             "instance_of": "pat", "instance_fill": {"adj": "haett"}, "instance_form": form},
        ],
    }


class FormInstanceTests(unittest.TestCase):
    def test_a_form_that_does_not_make_the_phrase_fails_validation(self):
        with self.assertRaisesRegex(CurriculumError, "question form"):
            curriculum_from_dict(raw(target="Er þetta gott?"))
        with self.assertRaisesRegex(CurriculumError, "instance_form"):
            curriculum_from_dict(raw(form="negative"))

    def test_the_form_costs_as_a_form_and_comes_in_lightly_after_the_plain_sentence(self):
        cur = curriculum_from_dict(raw())
        planner = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, new_items=2, max_new_items=3, priority=["pat", "ph"], seed=3), today=TODAY)
        self.assertEqual(planner.component_cost(cur.by_id["ph"]), planner.cfg.form_weight)
        sc = planner.build()
        self.assertIn("ph", sc.meta["new_items"])
        self.assertEqual(sc.meta["pattern_instances"], ["ph"], "one light exercise, no ladder")
        mine = [e for e in sc.exercises if "ph" in e.item_ids]
        self.assertEqual([e.kind for e in mine], ["embed"])
        self.assertIn("As a question", sc.transcript())
        order = [e.label for e in sc.exercises if e.kind in ("intro", "embed")]
        self.assertLess(next(i for i, l in enumerate(order) if "Þetta er" in l), order.index("pattern: Er þetta hættulegt?"))


if __name__ == "__main__":
    unittest.main()


class PartsTogetherTests(unittest.TestCase):
    """#280: new parts of one line the learner knows are taken out of it in one exercise."""

    def test_two_parts_of_one_known_line_share_an_exercise(self):
        from audiolesson.learner import ItemState
        from datetime import timedelta
        cur = curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "thusund", "kind": "vocab", "target": "þúsund", "meaning": "thousand", "tags": ["n"]},
                {"id": "kronur", "kind": "vocab", "target": "krónur", "meaning": "krónur", "tags": ["n"]},
                {"id": "thusund_kronur", "kind": "vocab", "target": "þúsund krónur", "meaning": "a thousand krónur", "tags": ["n"]},
            ],
        })
        learner = LearnerState("is", "en", "A1")
        learner.items["thusund_kronur"] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3,
                                                    due=(TODAY + timedelta(days=5)).isoformat(), last_practiced=(TODAY - timedelta(days=2)).isoformat())
        learner.lessons_completed = 4
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, new_items=2, max_new_items=2, priority=["thusund", "kronur"], seed=3), today=TODAY).build()
        intros = [e for e in sc.exercises if e.kind == "intro"]
        self.assertEqual([sorted(e.item_ids) for e in intros], [["kronur", "thusund"]], "one exercise for both parts")
        self.assertIn("And this one:", sc.transcript())
        self.assertEqual(sorted(sc.meta["new_items"]), ["kronur", "thusund"])
        self.assertEqual({sc.meta["wholes_taught"][i]["answer"] for i in ("kronur", "thusund")}, {"þúsund krónur"})
