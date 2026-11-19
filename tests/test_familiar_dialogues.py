"""#416, lesson 53: a fixed conversation played whole twice did not return; its lines are practised one at a time. The owner, 2026-11-19 (a simple
dialogue played four or five times, «every time I was fed up»): once (``dialogue_full_play_limit`` 1), a script whose every line the learner can say
is played whole at once, and one whose scene a theme level has played (``Dialogue.superseded_by``) does not return."""
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

    def test_two_complete_plays_retire_a_script_and_leave_other_scenes_available(self):
        """Lesson 53 (the owner: retire the whole replay and keep single lines): «tynd», «kynning» and «veitingastadur» were played whole for the
        fifth, sixth and seventh time in the lesson's first thirteen minutes."""
        p = self.planner(plays=4)  # four turns: encounters 1 and 2 are partial, 3 and 4 complete
        self.assertIsNone(p.eligible_dialogue())
        self.assertIsNone(p.eligible_dialogue(prefer_item=p.cur.by_id["hello"]))
        self.assertIsNone(p.listening_dialogue())
        p.cur.dialogues.append(replace(p.cur.dialogues[0], id="another_scene"))
        self.assertEqual(p.eligible_dialogue().id, "another_scene")

    def test_partial_encounters_do_not_count_as_complete_plays(self):
        # Four turns, played before whole plays were recorded: encounters 1 and 2 gave only 2 and 3 turns; encounter 3 the full script.
        for plays in (0, 1, 2):
            with self.subTest(plays=plays):
                self.assertIsNotNone(self.planner(plays=plays).eligible_dialogue())
        self.assertIsNone(self.planner(plays=3).eligible_dialogue())
        self.assertIsNotNone(self.planner(plays=3, dialogue_full_play_limit=2).eligible_dialogue(), "#416's limit of two")
        # A longer dialogue is still growing after four encounters.
        self.assertIsNotNone(self.planner(turns=8, plays=4).eligible_dialogue())

    def test_short_scripts_count_from_the_first_complete_encounter(self):
        self.assertIsNone(self.planner(turns=2, plays=1).eligible_dialogue())
        self.assertIsNotNone(self.planner(turns=2, plays=1, dialogue_full_play_limit=2).eligible_dialogue())
        self.assertIsNotNone(self.planner(turns=4, plays=2, dialogue_first_turns=1).eligible_dialogue())

    def test_a_known_script_is_played_whole_at_once_and_counted_as_a_whole_play(self):
        """The owner, 2026-11-19: every line the learner can say, the script is not grown over four lessons."""
        from audiolesson.planner import apply_to_learner
        from audiolesson.script import Script

        p = self.planner(plays=0)
        d = p.cur.dialogues[0]
        sc = Script(1, "t", "is", "en")
        p._play_dialogue(sc, d)
        said = [g.text for g in sc.segments if g.type == "answer"]
        self.assertEqual(len(said), 4, "all four turns at the first encounter")
        self.assertEqual(p.dialogues_whole_played, {"familiar": 1})
        sc.meta = {"dialogues": ["familiar"], "dialogues_whole": dict(p.dialogues_whole_played), "new_items": [], "reviewed_items": []}
        learner = p.learner
        learner.dialogues_done.pop("familiar")
        learner.dialogues_done["familiar"] = 1
        learner.dialogues_whole.update(sc.meta["dialogues_whole"])
        self.assertTrue(p._dialogue_familiar(d), "one whole play: retired")

    def test_a_script_whose_scene_a_theme_level_played_does_not_return(self):
        p = self.planner(plays=0)
        p.cur.dialogues[0] = replace(p.cur.dialogues[0], superseded_by=["cafe:1"])
        self.assertIsNotNone(p.eligible_dialogue())
        p.learner.levels_last["cafe:1"] = 18
        self.assertIsNone(p.eligible_dialogue())

    def test_a_failed_hesitated_or_reported_hard_item_does_not_bring_the_whole_script_back(self):
        """Until lesson 53 such an item kept its script returning for good; it is practised as a line of its own."""
        for change in ({"last_outcome": "not_recalled"}, {"last_outcome": "hesitated"}, {"reported_hard": TODAY.isoformat()}):
            with self.subTest(change=change):
                p = self.planner()
                p.learner.items["hello"] = replace(p.learner.items["hello"], **change)
                self.assertIsNone(p.eligible_dialogue())
                self.assertIsNone(p.eligible_dialogue(prefer_item=p.cur.by_id["hello"]))

    def test_an_item_not_yet_learned_does_not_bring_the_whole_script_back(self):
        p = self.planner()
        p.learner.items["thanks"].durable_successes = 1
        self.assertTrue(p._dialogue_familiar(p.cur.dialogues[0]))
        self.assertIsNone(p.eligible_dialogue())

    def test_a_due_item_is_reviewed_as_a_line_of_its_own(self):
        p = self.planner()
        p.learner.items["hello"].due = TODAY.isoformat()
        self.assertIsNone(p.eligible_dialogue())
        self.assertIn("hello", [i.id for i in p.select_reviews()])

    def test_zero_disables_the_limit_for_comparisons(self):
        self.assertIsNotNone(self.planner(dialogue_full_play_limit=0).eligible_dialogue())

class SupersededByTests(unittest.TestCase):
    def test_every_superseding_level_exists(self):
        """Each `superseded_by` names a level of a theme of the course («pharmacy:1»), so a misspelt one does not keep a script playing."""
        from pathlib import Path

        from audiolesson.cando import load_cando
        from audiolesson.content import load_curriculum
        from audiolesson.themes import load_themes

        path = Path(__file__).resolve().parent.parent / "curricula" / "is-en"
        cur = load_curriculum(path)
        themes = load_themes(path, cur, load_cando(path, cur))
        levels = {f"{t.id}:{k}" for t in themes for k in range(1, len(t.levels) + 1)}
        named = {d.id: key for d in cur.dialogues for key in d.superseded_by}
        self.assertGreaterEqual(len(named), 14)
        self.assertEqual({d: k for d, k in named.items() if k not in levels}, {})


if __name__ == "__main__":
    unittest.main()
