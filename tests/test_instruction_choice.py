"""#429 (owner, 2026-11-14): replacing the lessons' instructions with Icelandic ones is the learner's choice, asked once by the bot around the
tenth lesson: «gradual» or «off». Not answered yet («pending»), a learner who has met no instruction phrase hears none; one who has goes on."""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import for_instructions, load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent
COMMANDS = ["endurtaktu", "hlustadu", "haegt_command", "hlustadu_aftur"]


class InstructionChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def learner(self, met=()):
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id["tvaer"].order and not i.command:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        for i in met:
            learner.items[i] = ItemState(stage="meaning", successes=2, recalled=1, last_outcome="recalled", introduced_lesson=20, due=TODAY.isoformat())
        learner.lessons_completed = 30
        return learner

    def build(self, learner, mode):
        cur, resolved, withdrawn = for_instructions(self.cur, learner, mode)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY).build()
        return sc, resolved, withdrawn

    def test_the_modes_resolve(self):
        self.assertEqual(for_instructions(self.cur, self.learner(), "pending")[1:], ("off", COMMANDS), "not answered, none met: none")
        self.assertEqual(for_instructions(self.cur, self.learner(["endurtaktu"]), "pending")[1:], ("gradual", []), "not answered, already started: go on")
        self.assertEqual(for_instructions(self.cur, self.learner(), "gradual")[1:], ("gradual", []))
        cur, mode, withdrawn = for_instructions(self.cur, self.learner(["endurtaktu"]), "off")
        self.assertEqual((mode, withdrawn), ("off", COMMANDS))
        self.assertFalse(any(i.command for i in cur.items))
        with self.assertRaises(ValueError):
            for_instructions(self.cur, self.learner(), "sometimes")

    def test_off_teaches_none_says_none_and_asks_none(self):
        """«off» chosen after two instructions were taught: the lesson says every instruction in English, teaches no new one, and neither its
        review nor its recalls ask the two phrases (their cards are withdrawn from the written review)."""
        sc, _, withdrawn = self.build(self.learner(["endurtaktu", "hlustadu"]), "off")
        self.assertFalse(any(g.role in ("command", "command_support") for g in sc.segments), "no instruction in Icelandic")
        self.assertFalse(any(e.label.startswith("new instruction") for e in sc.exercises), "none taught")
        self.assertFalse(set(COMMANDS) & {i for e in sc.exercises for i in e.item_ids}, "none asked")
        self.assertFalse(set(COMMANDS) & {i for q in sc.review_questions() for i in q.get("items", [])}, "none in the review")
        self.assertIn("Repeat.", [g.text for g in sc.segments if g.type == "narrate"])
        self.assertEqual(withdrawn, COMMANDS)

    def test_gradual_goes_on_as_before(self):
        sc, _, _ = self.build(self.learner(), "gradual")
        self.assertEqual([e.label for e in sc.exercises if e.label.startswith("new instruction")], ["new instruction: Endurtaktu."])

    def test_generate_writes_the_choice_and_the_withdrawn_items_to_the_plan(self):
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as d:
            learner = self.learner(["endurtaktu"])
            path = Path(d) / "learner.json"
            learner.save(path)
            rc = main(["generate", "-c", str(ROOT / "curricula" / "is-en"), "-l", str(path), "-o", d, "-m", "5", "--no-audio",
                       "--instructions", "off", "--date", TODAY.isoformat()])
            self.assertEqual(rc, 0)
            plan = json.loads(next(Path(d).glob("*.plan.json")).read_text(encoding="utf-8"))
            self.assertEqual((plan["instructions"], plan["withdrawn_items"]), ("off", COMMANDS))


if __name__ == "__main__":
    unittest.main()
