"""#429, the long run's first step (the owner, 2026-11-09: «when in the hell the questions become Icelandic?»): every instruction was in the learner's
language. A pilot teaches two instructions in Icelandic, «Endurtaktu.» (repeat) and «Hlustaðu.» (listen), one a lesson from the tenth lesson on, as
material; then each is said in an Icelandic voice in every exercise that says it, with the learner's own after it in the lesson that teaches it and
the next (the owner after lesson 56: no complaint, which comes only in a lesson's feedback, is understanding), and again after a failure."""
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
        learner.lessons_completed = 11
        learner.items["endurtaktu"] = ItemState(stage="meaning", recalled=0, last_outcome="recalled", introduced_lesson=10)
        self.assertEqual(self.instruct(learner), [("speak", COMMAND_VOICE, "Endurtaktu.")], "the third lesson from the one that taught it: Icelandic alone")
        learner.items["endurtaktu"] = ItemState(stage="meaning", recalled=2, failures=1, last_outcome="not_recalled", introduced_lesson=10)
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
        bad = dataclasses.replace(self.cur, items=[dataclasses.replace(i, command="build_up") if i.id == "endurtaktu" else i for i in self.cur.items])
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
        learner.lessons_completed = 56
        for i, taught in (("haegt_command", 56), ("hlustadu_aftur", 55)):
            learner.items[i] = ItemState(stage="meaning", successes=2, recalled=0, last_outcome="recalled", due=(TODAY + timedelta(days=3)).isoformat(),
                                         introduced_lesson=taught)
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), learner)
        sc = Script(1, "t", "is", "en")
        ex = sc.new_exercise("intro", "intro", [], "t")
        b._instruct(sc, ex, "slowly")
        self.assertEqual([(g.type, g.text, g.role) for g in sc.segments], [("speak", "Hægt.", "command"), ("narrate", "Slowly.", "command_support")])
        sc = Script(1, "t", "is", "en")
        ex = sc.new_exercise("intro", "intro", [], "t")
        b._instruct(sc, ex, "pick_out_again", frame=True)
        self.assertEqual([(g.type, g.text) for g in sc.segments[:1]], [("speak", "Hlustaðu aftur.")])
        self.assertEqual([g.type for g in sc.segments], ["speak", "pause"], "taught two lessons before: the English has faded, a beat before the line")
        fresh = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        ex = sc.new_exercise("intro", "intro", [], "t")
        fresh._instruct(sc, ex, "pick_out_again", frame=True)
        self.assertEqual([(g.type, g.text, g.role) for g in sc.segments if g.type != "pause"], [("narrate", "Listen again.", "frame")], "not taught: as before")
        self.assertEqual(sc.segments[-1].type, "pause")

    def test_the_english_goes_from_the_third_lesson_after_the_one_that_teaches_it(self):
        """The owner after lesson 56 («the instructions in both languages never end»; «no complaint should be treated as understood … the third
        lesson, because there is no feedback given during a lesson»): «Hlustaðu aftur.», taught in lesson 56, has its English in lessons 56 and
        57 and is said alone from lesson 58, whatever the written review has recalled. Lesson 56 had said «Endurtaktu. / Repeat.» seven times,
        four lessons after lesson 52 taught it: the fade waited for two recalls in the review."""
        self.assertEqual(len(self.instruct(in_lesson=["endurtaktu"])), 2, "the lesson that teaches it")
        for lesson, said in ((53, 2), (54, 1), (60, 1)):
            learner = LearnerState("is", "en", "A1")
            learner.lessons_completed = lesson - 1
            learner.items["endurtaktu"] = ItemState(stage="meaning", successes=2, recalled=0, last_outcome="recalled", introduced_lesson=52)
            self.assertEqual(len(self.instruct(learner)), said, f"lesson {lesson}, taught in 52")

    def test_the_next_lines_are_said_in_icelandic_once_taught(self):
        """Lesson 57 (all four taught: «no new Icelandic instruction came; without about one each lesson the switch will not progress»): #429
        step 1, the lines said most after them. «Og á eðlilegum hraða.» where a slow model said «And at natural speed.», «Svarið:» before a
        pick-out's answer, and the ways back «Aftur að tala.» and «Samtalinu er lokið.», written on the finished script, each still the last
        line of its task (``unmarked_turns``)."""
        from audiolesson.cando import load_cando
        from audiolesson.listening_tasks import ListeningTask, _build
        from audiolesson.themes import load_themes, scenario_order
        from audiolesson.transitions import unmarked_turns

        en = Prompts.load("en")
        learner = LearnerState("is", "en", "A1")
        upto = self.cur.by_id["eg_er_ad_leita_ad"].order
        for i in self.cur.items:
            if i.order <= upto:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
            if i.command:
                learner.items[i.id] = ItemState(stage="meaning", successes=2, recalled=2, last_outcome="recalled", due=(TODAY + timedelta(days=30)).isoformat(),
                                                introduced_lesson=20)
        learner.lessons_completed = 40
        path = ROOT / "curricula" / "is-en"
        scenarios = load_cando(path, self.cur)
        cfg = PlanConfig(minutes=30, seed=1, new_target=8, themes=load_themes(path, self.cur, scenarios), theme_scenarios=scenario_order(scenarios))
        sc = Planner(self.cur, learner, en, Timing(level="A1"), cfg, today=TODAY).build()
        for key in ("natural", "listening_back", "conversation_back"):
            item = next(i for i in self.cur.items if i.command == key)
            self.assertTrue(any(g.speaker == COMMAND_VOICE and g.text == item.target for g in sc.segments), key)
            self.assertFalse(any(g.type == "narrate" and g.text == en.get(key) for g in sc.segments), f"never «{en.get(key)}» once taught, twenty lessons ago")
        self.assertEqual(unmarked_turns(sc, en), [], "a way back in Icelandic is still the task's last line")
        # #429 step 2 (lesson 56): no line says a taught instruction inside its English («… Listen, then repeat.», «… Repeat each part.»)
        whole = {en.get(k) for k in ("build_up", "split_slowly", "slow_word_break_down", "note_pieces", "embed_sentence", "instance_sentence",
                                     "instance_form_question", "instance_form_negative")}
        self.assertFalse([g.text for g in sc.segments if g.type == "narrate" and g.text in whole])
        self.assertTrue(any(g.text == en.get("build_up_lead") for g in sc.segments), "the lesson builds a sentence up, its lead in English")
        b = Builder(self.cur, en, Timing(level="A1"), learner)
        pick = Script(1, "t", "is", "en")
        _build(b, pick, ListeningTask("pick_out", "x", "", "Safnið lokar klukkan fimm.", "klukkan fimm", "Five o'clock.", "pick_out_time"))
        answer = next(k for k, g in enumerate(pick.segments) if g.type == "answer")
        self.assertEqual([(g.type, g.text) for g in pick.segments[answer - 2 : answer + 1]], [("speak", "Svarið:"), ("pause", None), ("answer", "klukkan fimm")],
                         "«Svarið:» alone, a beat before the answer")
        intro = Script(1, "t", "is", "en")
        builder(self.cur).intro(intro, self.cur.by_id["svarid_command"])
        self.assertIn("It means: The answer.", [g.text for g in intro.segments], "not «The answer:.»")

    def test_a_line_that_ends_on_an_instruction_says_it_as_a_line_of_its_own(self):
        """#429 step 2, lesson 56: «"Repeat" was learned in Icelandic, but some instructions still say it only in English» («A sentence from a
        pattern you know. Listen, then repeat.», «Let's build it up from the end. Repeat each part.»). Once taught, the lead is said in English
        and the instruction in Icelandic; before, the line as it was."""
        def said(learner, whole_key, key, frame):
            b = builder(self.cur, learner=learner)
            sc = Script(1, "t", "is", "en")
            b._lead_instruct(sc, sc.new_exercise("model", "intro", [], "x"), whole_key, key, frame=frame)
            return [(g.type, g.text) for g in sc.segments]

        en = Prompts.load("en")
        self.assertEqual(said(None, "build_up", "repeat", False), [("narrate", en.get("build_up"))], "not taught: as before")
        self.assertEqual(said(None, "instance_sentence", "listen", True), [("narrate", en.get("instance_sentence")), ("pause", None)])
        learner = LearnerState("is", "en", "A1")
        learner.lessons_completed = 60
        for i in ("endurtaktu", "hlustadu"):
            learner.items[i] = ItemState(stage="meaning", successes=2, recalled=2, last_outcome="recalled", introduced_lesson=52)
        self.assertEqual(said(learner, "build_up", "repeat", False), [("narrate", "Let's build it up from the end."), ("speak", "Endurtaktu."), ("pause", None)])
        self.assertEqual(said(learner, "instance_sentence", "listen", True), [("narrate", "A sentence from a pattern you know."), ("speak", "Hlustaðu."),
                                                                               ("pause", None)], "a framing line keeps its beat")

    def test_the_commands_come_one_a_lesson_in_their_order(self):
        order = [i.id for i in self.cur.items if i.command]
        self.assertEqual(order, ["endurtaktu", "hlustadu", "haegt_command", "hlustadu_aftur", "edlilegum_hrada_command", "svarid_command",
                                 "aftur_ad_tala_command", "samtalinu_lokid_command"], "lesson 54's then lesson 57's, by how often the lessons say them")
        learner = LearnerState("is", "en", "A1")
        for i in ("endurtaktu", "hlustadu"):
            learner.items[i] = ItemState(stage="meaning", successes=2, recalled=1, last_outcome="recalled", due=(TODAY + timedelta(days=3)).isoformat())
        learner.lessons_completed = 54
        planner = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        self.assertEqual(planner.next_command().id, "haegt_command")


if __name__ == "__main__":
    unittest.main()
