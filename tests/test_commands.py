"""#429, the long run's first step (the owner, 2026-11-09: «when in the hell the questions become Icelandic?»): every instruction was in the learner's
language. A pilot teaches two instructions in Icelandic, «Endurtaktu.» (repeat) and «Hlustaðu.» (listen), one a lesson from the tenth lesson on, as
material; then each is said in an Icelandic voice in every exercise that says it, with the learner's own after it for its first two hearings
after it is taught (the owner after lesson 56: «no complaint should be treated as understood»), and again after a failure."""
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
        learner.items["endurtaktu"] = ItemState(stage="meaning", recalled=0, last_outcome="recalled")
        learner.commands_heard = {"endurtaktu": 2}
        self.assertEqual(self.instruct(learner), [("speak", COMMAND_VOICE, "Endurtaktu.")], "heard twice as the instruction: Icelandic alone")
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
        bad = dataclasses.replace(self.cur, items=[dataclasses.replace(i, command="natural") if i.id == "endurtaktu" else i for i in self.cur.items])
        with self.assertRaises(CurriculumError):
            validate(bad)

    def lesson(self, completed: int):
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id["tvaer"].order:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        learner.lessons_completed = completed
        self.planner = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        return self.planner.build()

    def test_one_a_lesson_first_from_the_tenth_lesson_then_heard(self):
        sc = self.lesson(30)
        intros = [e for e in sc.exercises if e.kind == "intro" and e.label.startswith("new instruction")]
        self.assertEqual([e.label for e in intros], ["new instruction: Endurtaktu."], "one a lesson, in course order")
        first_intro = min(e.index for e in sc.exercises if e.kind == "intro")
        self.assertEqual(intros[0].index, first_intro, "first, ahead of the day's new material")
        after = [g for g in sc.segments if g.exercise is not None and g.exercise > intros[0].index]
        self.assertTrue(any(g.role == "command" and g.text == "Endurtaktu." for g in after), "then heard where «Repeat.» was said")
        self.assertFalse(any(g.type == "narrate" and g.text == "Repeat." and g.role != "command_support" for g in after), "never «Repeat.» alone")
        # review of #507: charged at 0, so the caps that read the charged costs (``arc_size``, the new-item cap) do not count it as 1
        self.assertEqual(self.planner.component_by_item.get("endurtaktu"), 0.0)
        self.assertFalse(any(e.label.startswith("new instruction") for e in self.lesson(5).exercises), "not before the tenth lesson")

    def test_slowly_and_listen_again_are_said_in_icelandic_once_taught(self):
        """Lesson 54 («アイスランド語の指示文が増えなかった»): #429's second step. «Hægt.» where «Slowly.» was, joined to its line; «Hlustaðu aftur.» where a
        pick-out said «Listen again.», a framing line, so a beat follows it with the English after it or without."""
        learner = LearnerState("is", "en", "A1")
        for i in ("haegt_command", "hlustadu_aftur"):
            learner.items[i] = ItemState(stage="meaning", successes=2, recalled=0, last_outcome="recalled", due=(TODAY + timedelta(days=3)).isoformat())
        learner.commands_heard = {"haegt_command": 1, "hlustadu_aftur": 2}
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), learner)
        sc = Script(1, "t", "is", "en")
        ex = sc.new_exercise("intro", "intro", [], "t")
        b._instruct(sc, ex, "slowly")
        self.assertEqual([(g.type, g.text, g.role) for g in sc.segments], [("speak", "Hægt.", "command"), ("narrate", "Slowly.", "command_support")])
        sc = Script(1, "t", "is", "en")
        ex = sc.new_exercise("intro", "intro", [], "t")
        b._instruct(sc, ex, "pick_out_again", frame=True)
        self.assertEqual([(g.type, g.text) for g in sc.segments[:1]], [("speak", "Hlustaðu aftur.")])
        self.assertEqual([g.type for g in sc.segments], ["speak", "pause"], "heard twice: the English has faded, a beat before the line")
        fresh = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        ex = sc.new_exercise("intro", "intro", [], "t")
        fresh._instruct(sc, ex, "pick_out_again", frame=True)
        self.assertEqual([(g.type, g.text, g.role) for g in sc.segments if g.type != "pause"], [("narrate", "Listen again.", "frame")], "not taught: as before")
        self.assertEqual(sc.segments[-1].type, "pause")

    def test_the_english_fades_at_the_third_hearing_after_the_instruction_is_taught(self):
        """The owner after lesson 56 («the instructions in both languages never end»; «no complaint should be treated as understood»): the
        English follows the first two hearings after the introduction, in that lesson and the ones after, then never, failures aside. Lesson 56
        had said «Endurtaktu. / Repeat.» seven times, four lessons after it was taught: the fade waited for two recalls in the written review."""
        def hearings(b):
            sc = Script(1, "t", "is", "en")
            out = []
            for _ in range(4):
                ex = sc.new_exercise("recall", "meaning", [], "x")
                b._instruct(sc, ex, "repeat")
                out.append(sum(1 for g in sc.segments if g.exercise == ex.index and g.type != "pause"))
            return out

        b = builder(self.cur)
        b.in_lesson.add("endurtaktu")  # taught in this lesson
        self.assertEqual(hearings(b), [2, 2, 1, 1], "the lesson that teaches it: English twice, then Icelandic alone")
        learner = LearnerState("is", "en", "A1")
        learner.items["endurtaktu"] = ItemState(stage="meaning", successes=2, recalled=0, last_outcome="recalled")
        learner.commands_heard = {"endurtaktu": 1}
        self.assertEqual(hearings(builder(self.cur, learner=learner)), [2, 1, 1, 1], "the count goes on across lessons")
        learner.commands_heard = {}
        self.assertEqual(hearings(builder(self.cur, learner=learner)), [1, 1, 1, 1], "taught before the count began: heard enough already")

    def test_the_finished_script_keeps_the_english_on_the_first_two_hearings_only(self):
        """The way in («Listen.») is written on the finished script, so it can come before instructions the build decided earlier: the last pass
        reads them in the order heard."""
        from audiolesson.script import Segment

        b = builder(self.cur)
        b.in_lesson.add("hlustadu")
        sc = Script(1, "t", "is", "en")
        for _ in range(3):
            ex = sc.new_exercise("recall", "meaning", [], "x")
            sc.add(Segment("speak", COMMAND_VOICE, "Hlustaðu.", "is", 1.0, 0.5, "command", ex.index))
            sc.add(Segment("narrate", "instructor", "Listen.", "en", 1.0, 0.5, "command_support", ex.index))
        b.settle_command_support(sc)
        self.assertEqual([g.text for g in sc.segments if g.type != "pause"], ["Hlustaðu.", "Listen.", "Hlustaðu.", "Listen.", "Hlustaðu."])
        self.assertEqual(sc.segments[-1].type, "pause", "a beat where the English was")

    def test_a_lesson_records_the_hearings_for_the_next(self):
        from audiolesson.planner import apply_to_learner

        sc = self.lesson(30)
        said = sum(1 for g in sc.segments if g.role == "command" and g.text == "Endurtaktu.")
        self.assertEqual(sc.meta["commands_heard"], {"endurtaktu": said})
        self.assertEqual(sum(1 for g in sc.segments if g.role == "command_support" and g.text == "Repeat."), min(said, 2))
        learner = self.planner.learner
        apply_to_learner(sc, learner, TODAY)
        self.assertEqual(learner.commands_heard["endurtaktu"], said)

    def test_the_commands_come_one_a_lesson_in_their_order(self):
        order = [i.id for i in self.cur.items if i.command]
        self.assertEqual(order, ["endurtaktu", "hlustadu", "haegt_command", "hlustadu_aftur"])
        learner = LearnerState("is", "en", "A1")
        for i in ("endurtaktu", "hlustadu"):
            learner.items[i] = ItemState(stage="meaning", successes=2, recalled=1, last_outcome="recalled", due=(TODAY + timedelta(days=3)).isoformat())
        learner.lessons_completed = 54
        planner = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        self.assertEqual(planner.next_command().id, "haegt_command")


if __name__ == "__main__":
    unittest.main()
