"""#416: a familiar fixed conversation must not keep returning just because its rest is over."""
import unittest
from dataclasses import replace
from datetime import date, timedelta

from audiolesson.content import curriculum_from_dict
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)


class FamiliarDialogueTests(unittest.TestCase):
    def planner(self, turns=4, plays=6, **cfg):
        cur = curriculum_from_dict({
            "curriculum": {"name": "test", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "hello", "kind": "phrase", "target": "Góðan daginn.", "meaning": "Hello."},
                {"id": "thanks", "kind": "phrase", "target": "Takk.", "meaning": "Thanks."},
            ],
            "dialogues": [{
                "id": "familiar", "setting": "At the counter.", "requires": ["thanks"],
                "turns": [{"cue": "Greet her.", "expect": "hello"} for _ in range(turns - 1)]
                         + [{"cue": "Thank her.", "expect_text": "Takk.", "expect_meaning": "Thanks."}],
            }],
        })
        learner = LearnerState("is", "en", "A1", lessons_completed=20)
        for i in cur.by_id:
            learner.items[i] = ItemState(stage="dialogue", successes=8, durable_successes=3, recalled=2,
                                         last_outcome="recalled", due=(TODAY + timedelta(days=10)).isoformat())
        learner.dialogues_done["familiar"] = plays
        # Rest is already over: familiarity, rather than the rest gate, must stop the return.
        learner.lessons = [{"number": 10, "dialogues": ["familiar"]}]
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, **cfg), today=TODAY)

    def test_four_complete_plays_stop_a_learned_script_and_leave_other_scenes_available(self):
        p = self.planner()
        self.assertIsNone(p.eligible_dialogue())
        self.assertIsNone(p.eligible_dialogue(prefer_item=p.cur.by_id["hello"]))
        self.assertIsNone(p.listening_dialogue())
        p.cur.dialogues.append(replace(p.cur.dialogues[0], id="another_scene"))
        self.assertEqual(p.eligible_dialogue().id, "another_scene")

    def test_partial_encounters_do_not_count_as_complete_plays(self):
        # Four turns: encounters 1 and 2 give only 2 and 3 turns; encounters 3–6 give the full script.
        for plays in (0, 1, 2, 3, 4, 5):
            with self.subTest(plays=plays):
                self.assertIsNotNone(self.planner(plays=plays).eligible_dialogue())
        self.assertIsNone(self.planner(plays=6).eligible_dialogue())
        # A longer dialogue is still growing after four encounters.
        self.assertIsNotNone(self.planner(turns=8, plays=4).eligible_dialogue())

    def test_short_scripts_count_from_the_first_complete_encounter(self):
        self.assertIsNotNone(self.planner(turns=2, plays=3).eligible_dialogue())
        self.assertIsNone(self.planner(turns=2, plays=4).eligible_dialogue())
        self.assertIsNotNone(self.planner(turns=4, plays=4, dialogue_first_turns=1).eligible_dialogue())

    def test_failed_hesitated_and_reported_hard_items_keep_their_scene(self):
        for change in ({"last_outcome": "not_recalled"}, {"last_outcome": "hesitated"}, {"reported_hard": TODAY.isoformat()}):
            with self.subTest(change=change):
                p = self.planner()
                p.learner.items["hello"] = replace(p.learner.items["hello"], **change)
                self.assertEqual(p.eligible_dialogue().id, "familiar")

    def test_new_or_embedded_material_keeps_its_scene(self):
        for where in ("intro", "embedded"):
            with self.subTest(where=where):
                p = self.planner()
                if where == "intro":
                    p.builder.in_lesson.add("hello")
                else:
                    p.embedded.append("hello")
                self.assertEqual(p.eligible_dialogue().id, "familiar")

    def test_a_literal_turns_required_item_must_also_be_learned(self):
        p = self.planner()
        p.learner.items["thanks"].durable_successes = 1
        self.assertFalse(p._dialogue_familiar(p.cur.dialogues[0]))
        # A met, not-yet-learned item can still put the scene on the listening route.
        self.assertEqual(p.listening_dialogue()[0].id, "familiar")

    def test_a_due_item_does_not_force_the_whole_familiar_script_back(self):
        p = self.planner()
        p.learner.items["hello"].due = TODAY.isoformat()
        self.assertIsNone(p.eligible_dialogue())
        self.assertIn("hello", [i.id for i in p.select_reviews()])

    def test_zero_disables_the_limit_for_comparisons(self):
        self.assertIsNotNone(self.planner(dialogue_full_play_limit=0).eligible_dialogue())


if __name__ == "__main__":
    unittest.main()
