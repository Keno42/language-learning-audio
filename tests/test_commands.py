"""#429, the long run's first step (the owner, 2026-11-09: «when in the hell the questions become Icelandic?»): every instruction was in the learner's
language. A pilot teaches two instructions in Icelandic, «Endurtaktu.» (repeat) and «Hlustaðu.» (listen), one a lesson from the tenth lesson on, as
material; then each is said in an Icelandic voice in every exercise that says it, with the learner's own after it until their review has recalled
it twice, and again after a failure."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import CurriculumError, load_curriculum, validate
from audiolesson.exercises import COMMAND_VOICE, Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


def builder(cur, lang="en", learner=None):
    return Builder(cur, Prompts.load(lang), Timing(level="A1"), learner or LearnerState("is", lang, "A1"))


class CommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def instruct(self, learner=None, in_lesson=()):
        b = builder(self.cur, learner=learner)
        b.in_lesson.update(in_lesson)
        sc = Script(1, "t", "is", "en")
        b._instruct(sc, sc.new_exercise("recall", "meaning", [], "x"), "repeat")
        return [(g.type, g.speaker, g.text) for g in sc.segments if g.type != "pause"]

    def test_the_instruction_follows_what_the_learner_has(self):
        self.assertEqual(self.instruct(), [("narrate", "instructor", "Repeat.")], "not taught: the learner's own")
        self.assertEqual(self.instruct(in_lesson=["endurtaktu"]), [("speak", COMMAND_VOICE, "Endurtaktu."), ("narrate", "instructor", "Repeat.")],
                         "taught: in Icelandic, the English after it")
        learner = LearnerState("is", "en", "A1")
        learner.items["endurtaktu"] = ItemState(stage="meaning", recalled=2, last_outcome="recalled")
        self.assertEqual(self.instruct(learner), [("speak", COMMAND_VOICE, "Endurtaktu.")], "recalled twice in the review: Icelandic alone")
        learner.items["endurtaktu"] = ItemState(stage="meaning", recalled=2, failures=1, last_outcome="not_recalled")
        self.assertEqual(len(self.instruct(learner)), 2, "a failure brings the English back")

    def test_it_is_taught_as_material(self):
        for lang, intro in (("en", "From now on, this instruction is in Icelandic:"), ("ja", "これからは、この指示をアイスランド語で言います：")):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            b = builder(cur, lang)
            sc = Script(1, "t", "is", lang)
            ex = b.intro(sc, cur.by_id["endurtaktu"])
            self.assertEqual(ex.kind, "intro")
            narrated = [g.text for g in sc.segments if g.type == "narrate"]
            self.assertEqual(narrated[0], intro)
            self.assertIn({"en": "It means: Repeat.", "ja": "意味は「繰り返してください」です。"}[lang], narrated)
            self.assertEqual([g.text for g in sc.segments if g.type == "answer"], ["Endurtaktu."], "a first retrieval, which the review asks too")

    def test_a_command_names_an_instruction_the_lessons_say(self):
        import dataclasses
        bad = dataclasses.replace(self.cur, items=[dataclasses.replace(i, command="slowly") if i.id == "endurtaktu" else i for i in self.cur.items])
        with self.assertRaises(CurriculumError):
            validate(bad)

    def lesson(self, completed: int):
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id["tvaer"].order:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        learner.lessons_completed = completed
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY).build()

    def test_one_a_lesson_first_from_the_tenth_lesson_then_heard(self):
        sc = self.lesson(30)
        intros = [e for e in sc.exercises if e.kind == "intro" and e.label.startswith("new instruction")]
        self.assertEqual([e.label for e in intros], ["new instruction: Endurtaktu."], "one a lesson, in course order")
        first_intro = min(e.index for e in sc.exercises if e.kind == "intro")
        self.assertEqual(intros[0].index, first_intro, "first, ahead of the day's new material")
        after = [g for g in sc.segments if g.exercise is not None and g.exercise > intros[0].index]
        self.assertTrue(any(g.role == "command" and g.text == "Endurtaktu." for g in after), "then heard where «Repeat.» was said")
        self.assertFalse(any(g.type == "narrate" and g.text == "Repeat." and g.role != "command_support" for g in after), "never «Repeat.» alone")
        self.assertFalse(any(e.label.startswith("new instruction") for e in self.lesson(5).exercises), "not before the tenth lesson")


if __name__ == "__main__":
    unittest.main()
