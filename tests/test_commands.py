"""#429, the long run's first step (the owner, 2026-11-09: «when in the hell the questions become Icelandic?»): every instruction was in the learner's
language. A pilot teaches two instructions in Icelandic, «Endurtaktu.» (repeat) and «Hlustaðu.» (listen), one a lesson from the tenth lesson on, as
material; then each is said in an Icelandic voice in every exercise that says it, with the learner's own after it in the lesson that teaches it and
the next (the owner after lesson 56: no complaint, which comes only in a lesson's feedback, is understanding), and again after a failure."""
import unittest
from dataclasses import replace
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

    def themed_lesson(self, taught_in: int = 20, completed: int = 40):
        """A themed lesson of a learner who knows the course up to «Ég er að leita að …» and was taught every instruction in lesson ``taught_in``."""
        from audiolesson.cando import load_cando
        from audiolesson.themes import load_themes, scenario_order

        learner = LearnerState("is", "en", "A1")
        upto = self.cur.by_id["eg_er_ad_leita_ad"].order
        for i in self.cur.items:
            if i.order <= upto:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
            if i.command:
                learner.items[i.id] = ItemState(stage="meaning", successes=2, recalled=2, last_outcome="recalled", due=(TODAY + timedelta(days=30)).isoformat(),
                                                introduced_lesson=taught_in)
        learner.lessons_completed = completed
        path = ROOT / "curricula" / "is-en"
        scenarios = load_cando(path, self.cur)
        cfg = PlanConfig(minutes=30, seed=1, new_target=8, themes=load_themes(path, self.cur, scenarios), theme_scenarios=scenario_order(scenarios))
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build(), learner

    def test_the_next_lines_are_said_in_icelandic_once_taught(self):
        """Lesson 57 (all four taught: «no new Icelandic instruction came; without about one each lesson the switch will not progress»): #429
        step 1, the lines said most after them. «Og á eðlilegum hraða.» where a slow model said «And at natural speed.», «Svarið:» before a
        pick-out's answer, and the ways back «Aftur að tala.» and «Samtalinu er lokið.», written on the finished script, each still the last
        line of its task (``unmarked_turns``)."""
        from audiolesson.listening_tasks import ListeningTask, _build
        from audiolesson.transitions import unmarked_turns

        en = Prompts.load("en")
        sc, learner = self.themed_lesson()
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

    def test_a_conversation_opens_in_icelandic_once_taught(self):
        """#429 step 3: «Now a short conversation.» is the next line of #429's list by how often a lesson says it (lesson 57: 4 times). Once
        «Nú kemur stutt samtal.» is taught a conversation opens with it: with the English after it in the lesson that teaches it and the
        next, then alone, a beat before the scene's setting. «Now another short conversation.» and «Now part of a conversation.» are not
        it, and stay as they were."""
        from audiolesson.transitions import unmarked_turns

        en = Prompts.load("en")
        start, others = en.get("dialogue_start"), {en.get("dialogue_start_another"), en.get("dialogue_start_part")}
        item = next(i for i in self.cur.items if i.command == "dialogue_start")
        self.assertEqual(item.target, "Nú kemur stutt samtal.")

        def openings(sc):
            """Each conversation the lesson opens with the line: the segments from the line to the scene's setting, pauses by their role."""
            out = []
            for e in (e for e in sc.exercises if e.kind == "dialogue"):
                segs = [g for g in sc.segments if g.exercise == e.index]
                k = next((k for k, g in enumerate(segs) if g.text in (start, item.target)), None)
                if k is not None:
                    self.assertEqual(k, 0, f"{e.label}: the conversation's first line")
                    out.append([(g.type, g.role if g.type == "pause" else g.text, g.speaker) for g in segs[: k + 4]])
            return out

        alone, _ = self.themed_lesson()  # taught twenty lessons ago
        opened = openings(alone)
        self.assertGreater(len(opened), 1, "the lesson opens conversations")
        for segs in opened:
            self.assertEqual(segs[:2], [("speak", item.target, COMMAND_VOICE), ("pause", "beat", None)], "in Icelandic alone, then a beat")
            self.assertEqual((segs[2][0], segs[2][2]), ("narrate", "instructor"), "then the setting, in the learner's language")
        self.assertFalse(any(g.text == start for g in alone.segments), "never «Now a short conversation.» once taught, twenty lessons ago")
        self.assertEqual(unmarked_turns(alone, en), [], "a conversation that opens in Icelandic still opens with its own line")

        supported, _ = self.themed_lesson(taught_in=40)  # taught in the lesson before
        opened = openings(supported)
        self.assertGreater(len(opened), 1)
        for segs in opened:
            self.assertEqual([s for s in segs if s[0] != "pause"][:2], [("speak", item.target, COMMAND_VOICE), ("narrate", start, "instructor")],
                             "the lesson after the one that teaches it: the English after it")
        self.assertFalse(any(g.text == start and g.role != "command_support" for g in supported.segments))

        for sc in (alone, supported):
            self.assertFalse(any(g.type != "narrate" for g in sc.segments if g.text in others), "the other openings stay in the learner's language")

        learner = LearnerState("is", "en", "A1")
        learner.lessons_completed = 40
        untaught = Builder(self.cur, en, Timing(level="A1"), learner)
        self.assertIsNone(untaught.command_segments("dialogue_start", 0), "not taught: the line as it was")

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

    def test_a_variant_introduction_still_says_repeat_before_its_sentence_is_repeated(self):
        """Review of #551: «In another sentence. Listen, then repeat.» became «In another sentence.» «Hlustaðu.», and ``_intro_variant``
        (unlike ``embed`` and ``pattern_instance``) says no repeat before the sentence comes again for the learner to repeat. It says
        «Endurtaktu.» there once the line is split; before, the line as it was, with nothing added."""
        item = self.cur.by_id["god"]

        def said(taught):
            learner = LearnerState("is", "en", "A1")
            learner.lessons_completed = 60
            for i in self.cur.items:
                if i.order < item.order or (taught and i.command):
                    learner.items[i.id] = ItemState(stage="meaning", successes=6, recalled=3, last_outcome="recalled", introduced_lesson=20)
            sc = Script(1, "t", "is", "en")
            builder(self.cur, learner=learner)._intro_variant(sc, item, self.cur.by_id[item.variant_of])
            return [g.text for g in sc.segments if g.type != "pause"]

        lines = said(True)
        sentence = lines.index("Hlustaðu.") + 1
        self.assertEqual(lines[sentence + 2 : sentence + 4], ["Endurtaktu.", lines[sentence]], "repeat, then the sentence to repeat")
        plain = said(False)
        self.assertIn(Prompts.load("en").get("embed_sentence"), plain, "not taught: «In another sentence. Listen, then repeat.» as before")
        self.assertNotIn("Repeat.", plain[plain.index(Prompts.load("en").get("embed_sentence")):], "and nothing added")

    def test_a_cue_s_frame_is_said_in_icelandic_once_taught(self):
        """#429 step 4 (lesson 59: «Say: …» 40 times and «How do you say: …» 18 times, the English lines left; the authored phrases run out in
        lesson 62): the cue's frame between its lead and what to say, «Segðu:» and «Hvernig segir maður:»; what to say stays in the learner's
        language. Not in the exercise that asks for the frame's own phrase, whose cue would say the answer."""
        def framed(lang, text, taught=("segdu_command", "hvernig_segir_madur_command"), asked=()):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            learner = LearnerState("is", lang, "A1")
            learner.lessons_completed = 60
            for i in taught:
                learner.items[i] = ItemState(stage="meaning", successes=2, recalled=2, last_outcome="recalled", introduced_lesson=50)
            b = builder(cur, lang, learner)
            sc = Script(1, "t", "is", lang)
            b._narr(sc, sc.new_exercise("recall", "meaning", list(asked), "x"), text)
            out = [(g.type, g.text) for g in sc.segments]
            return None if out == [("narrate", text)] else out

        self.assertEqual(framed("en", "Now something you haven't heard yet. Say: I'm looking for the bank."),
                         [("narrate", "Now something you haven't heard yet."), ("speak", "Segðu:"), ("narrate", "I'm looking for the bank.")])
        self.assertEqual(framed("en", "In Icelandic, say: It's minus eight degrees."), [("speak", "Segðu:"), ("narrate", "It's minus eight degrees.")])
        self.assertEqual(framed("en", "How do you say: Where is the gate?"), [("speak", "Hvernig segir maður:"), ("narrate", "Where is the gate?")])
        self.assertEqual(framed("ja", "アイスランド語で「門はどこですか」と言ってください。"), [("speak", "Segðu:"), ("narrate", "「門はどこですか」")])
        self.assertEqual(framed("ja", "「門はどこですか」は、何と言いますか？"), [("speak", "Hvernig segir maður:"), ("narrate", "「門はどこですか」")])
        self.assertIsNone(framed("en", "Complete the sentence to say: I have one bag."), "a cloze's frame is not «Say:»")
        self.assertIsNone(framed("en", "Say: Hi.", taught=()), "not taught: the cue as it was")
        self.assertIsNone(framed("en", "Say: Say, before what to say.", asked=("segdu_command",)), "«Segðu:» would say the answer")
        self.assertEqual(framed("en", "How do you say: Say, before what to say.", asked=("segdu_command",))[0], ("speak", "Hvernig segir maður:"),
                         "another frame gives nothing away")

    def test_a_framed_cue_keeps_its_claim_about_the_sentence(self):
        """Review of #557: once «Segðu:» had played, «Now something you haven't heard yet.» «Segðu:» «I need a taxi.» failed the novelty check,
        the instruction taken for the sentence the claim points at. An instruction said in Icelandic is not a line of the lesson."""
        from audiolesson.claims import unkept_claims

        learner = LearnerState("is", "en", "A1")
        learner.lessons_completed = 60
        learner.items["segdu_command"] = ItemState(stage="meaning", successes=2, recalled=2, last_outcome="recalled", introduced_lesson=50)
        b = builder(self.cur, learner=learner)
        en = Prompts.load("en")
        sc = Script(1, "t", "is", "en")
        for sentence, meaning in (("Ég þarf hjálp.", "I need help."), ("Ég þarf leigubíl.", "I need a taxi.")):
            ex = sc.new_exercise("generative", "recombine", [], sentence)
            b._narr(sc, ex, en.get("recombine_new", meaning=meaning))
            b._answer_pause(sc, ex, sentence, None, generative=True)
            b._answer(sc, ex, sentence)
        self.assertEqual([g.text for g in sc.segments if g.role == "command"], ["Segðu:", "Segðu:"])
        self.assertEqual(unkept_claims(sc, en), [], "each sentence is new; «Segðu:» was heard before, and is no sentence")

    def test_a_cloze_and_a_new_item_say_their_frame_in_icelandic_once_taught(self):
        """#429 step 5 (lessons 63–67 on the replay of lesson 60's export, «Segðu:» and «Hvernig segir maður:» taught: a cloze's «Complete the
        sentence to say: …» 5–13 times a lesson and a new item's «Something new. …» 2–6, the most frequent English instructions left): the frame
        in Icelandic once taught, «Kláraðu setninguna:» and «Eitthvað nýtt.», and what to say still in the learner's language."""
        def framed(lang, text, taught=("klaradu_setninguna_command", "eitthvad_nytt_command"), asked=(), kind="recall"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            learner = LearnerState("is", lang, "A1")
            learner.lessons_completed = 66
            for i in taught:
                learner.items[i] = ItemState(stage="meaning", successes=2, recalled=2, last_outcome="recalled", introduced_lesson=60)
            b = builder(cur, lang, learner)
            sc = Script(1, "t", "is", lang)
            b._narr(sc, sc.new_exercise(kind, "cloze", list(asked), "x"), text)
            out = [(g.type, g.text) for g in sc.segments]
            return None if out == [("narrate", text)] else out

        self.assertEqual(framed("en", "Complete the sentence to say: I'm doing well."), [("speak", "Kláraðu setninguna:"), ("narrate", "I'm doing well.")])
        self.assertEqual(framed("en", "As a woman: Complete the sentence to say: I'm tired."),
                         [("narrate", "As a woman:"), ("speak", "Kláraðu setninguna:"), ("narrate", "I'm tired.")], "the speaker's form stays first")
        self.assertEqual(framed("en", "Something new. Nice to see you.", kind="intro"), [("speak", "Eitthvað nýtt."), ("narrate", "Nice to see you.")])
        self.assertEqual(framed("ja", "「元気です」と言うように、文を完成させてください。"), [("speak", "Kláraðu setninguna:"), ("narrate", "「元気です」")])
        self.assertEqual(framed("ja", "新しい表現です。「会えてうれしいです」。", kind="intro"), [("speak", "Eitthvað nýtt."), ("narrate", "「会えてうれしいです」。")])
        self.assertIsNone(framed("en", "Complete the sentence to say: I'm doing well.", taught=()), "not taught: the cue as it was")
        self.assertIsNone(framed("en", "Something new. Nice to see you.", taught=("klaradu_setninguna_command",), kind="intro"), "each frame by its own phrase")
        self.assertIsNone(framed("en", "Complete the sentence to say: Complete the sentence, before what to say.", asked=("klaradu_setninguna_command",)),
                          "«Kláraðu setninguna:» would say the answer")

    def test_a_cloze_and_a_new_item_in_the_lesson(self):
        """#429 step 5, as a lesson says them: the new item's model and the cloze's fragment follow the Icelandic frame and its meaning; the English
        frame after it in the lesson that teaches it and the next, gone from the third."""
        def lesson(introduced):
            learner = LearnerState("is", "en", "A1")
            learner.lessons_completed = 66
            for i in ("klaradu_setninguna_command", "eitthvad_nytt_command"):
                learner.items[i] = ItemState(stage="meaning", successes=2, recalled=2, last_outcome="recalled", introduced_lesson=introduced)
            b = builder(self.cur, learner=learner)
            sc = Script(67, "t", "is", "en")
            b.intro(sc, self.cur.by_id["gaman_ad_sja_thig"])
            b.recall(sc, self.cur.by_id["eg_hef_thad_gott"], "cloze")
            return [(g.type, g.text) for g in sc.segments if g.type != "pause"]

        alone = lesson(60)
        self.assertEqual(alone[:3], [("speak", "Eitthvað nýtt."), ("narrate", "Nice to see you."), ("speak", "Gaman að sjá þig.")])
        cloze = alone.index(("speak", "Kláraðu setninguna:"))
        self.assertEqual(alone[cloze + 1:cloze + 3], [("narrate", "I'm doing well."), ("speak", "Ég hef það…")])
        self.assertNotIn(("narrate", "Something new."), alone, "from the third lesson, the Icelandic alone")
        self.assertFalse(any(t and t.startswith("Complete the sentence") for _, t in alone))
        supported = lesson(66)
        self.assertEqual(supported[:3], [("speak", "Eitthvað nýtt."), ("narrate", "Something new."), ("narrate", "Nice to see you.")])
        cloze = supported.index(("speak", "Kláraðu setninguna:"))
        self.assertEqual(supported[cloze + 1:cloze + 3], [("narrate", "Complete the sentence:"), ("narrate", "I'm doing well.")],
                         "the lesson after the one that teaches it: the English after it")

    def test_the_form_work_says_its_own_lines_in_icelandic_once_taught(self):
        """#429 step 6 (lessons 63–69 on the replay of lesson 62's export, the frames of steps 4 and 5 taught: «Now say each one.» 26 times in
        eight lessons and «That's the end of the form work.» 15, the most frequent English instructions left with «A quick aside.» and «Back to
        the lesson.»): the form work's turn to the learner, «Segðu hverja setningu.», and its way back, «Æfingunni er lokið.», as «Samtalinu er
        lokið.» ends a conversation; each still the last line of its block (``unmarked_turns``), never the English once taught."""
        from audiolesson.transitions import unmarked_turns

        en = Prompts.load("en")
        say = next(i for i in self.cur.items if i.command == "number_choice_say")
        back = next(i for i in self.cur.items if i.command == "form_back")
        self.assertEqual((say.target, back.target), ("Segðu hverja setningu.", "Æfingunni er lokið."))
        for lesson in range(40, 46):  # the form work takes turns by lesson number
            sc, _ = self.themed_lesson(completed=lesson)
            blocks = [e for e in sc.exercises if e.stage in ("choice", "noun_choice", "said_of", "subjects")]
            if not blocks:
                continue
            texts = [g.text for g in sc.segments]
            self.assertNotIn(en.get("number_choice_say"), texts, f"lesson {lesson + 1}: never «Now say each one.» once taught")
            self.assertNotIn(en.get("form_back"), texts, f"lesson {lesson + 1}: never «That's the end of the form work.» once taught")
            said = [g for g in sc.segments if g.text == say.target]
            self.assertTrue(said and all(g.speaker == COMMAND_VOICE for g in said))
            self.assertEqual(unmarked_turns(sc, en), [], "a way back in Icelandic is still the block's last line")
            break
        else:
            self.fail("no themed lesson played the form work")

        def block(introduced):
            learner = LearnerState("is", "en", "A1")
            learner.lessons_completed = 68
            learner.items[say.id] = ItemState(stage="meaning", successes=2, recalled=2, last_outcome="recalled", introduced_lesson=introduced)
            b = builder(self.cur, learner=learner)
            sc = Script(69, "t", "is", "en")
            b._instruct(sc, sc.new_exercise("model", "choice", [], "x"), "number_choice_say")
            return [(g.type, g.text) for g in sc.segments if g.type != "pause"]

        self.assertEqual(block(60), [("speak", "Segðu hverja setningu.")], "from the third lesson, the Icelandic alone")
        self.assertEqual(block(68), [("speak", "Segðu hverja setningu."), ("narrate", "Now say each one.")], "the English after it the lesson after")

    def test_an_aside_says_its_own_lines_in_icelandic_once_taught(self):
        """#429 step 7 (lessons 64–71 on the replay of lesson 64's export, the form work's lines taught in lessons 67 and 68: «A quick aside.» and
        «Back to the lesson.» 19 times each in eight lessons, the most frequent English instructions left that an authored phrase can say): an
        aside opens on «Smá útúrdúr.» and ends on «Aftur að efninu.», with the English after each in the lesson that teaches it and the next,
        alone from the third; the end is still the aside's last line (``unmarked_turns``). A milestone keeps its own lines in English."""
        from audiolesson.content import Note
        from audiolesson.transitions import unmarked_turns

        en = Prompts.load("en")
        start = next(i for i in self.cur.items if i.command == "aside")
        end = next(i for i in self.cur.items if i.command == "aside_end")
        self.assertEqual((start.target, end.target), ("Smá útúrdúr.", "Aftur að efninu."))

        def aside(introduced, milestone=False):
            learner = LearnerState("is", "en", "A1")
            learner.lessons_completed = 70
            for i in (start, end):
                if introduced is not None:
                    learner.items[i.id] = ItemState(stage="meaning", successes=2, recalled=2, last_outcome="recalled", introduced_lesson=introduced)
            b = builder(self.cur, learner=learner)
            sc = Script(71, "t", "is", "en")
            b.note(sc, Note(id="n", text="Some cultural fact.", milestone=milestone))
            return sc, [(g.type, g.text) for g in sc.segments if g.type != "pause"]

        sc, alone = aside(60)
        self.assertEqual(alone, [("speak", "Smá útúrdúr."), ("narrate", "Some cultural fact."), ("speak", "Aftur að efninu.")],
                         "from the third lesson, the Icelandic alone")
        self.assertTrue(all(g.speaker == COMMAND_VOICE for g in sc.segments if g.type == "speak"))
        self.assertEqual(unmarked_turns(sc, en), [], "«Aftur að efninu.» is the aside's end line")
        # review of #580: another instruction in its place is no end line
        wrong = [(k, g) for k, g in enumerate(sc.segments) if g.text == "Aftur að efninu."]
        k, g = wrong[-1]
        sc.segments[k] = replace(g, text="Endurtaktu.", role="command")
        self.assertEqual(unmarked_turns(sc, en), ["note: n: no end line"], "an aside that ends on «Endurtaktu.» has no end line")
        _, supported = aside(70)
        self.assertEqual(supported, [("speak", "Smá útúrdúr."), ("narrate", en.get("aside")), ("narrate", "Some cultural fact."),
                                     ("speak", "Aftur að efninu."), ("narrate", en.get("aside_end"))], "the lesson after: the English after each")
        _, before = aside(None)
        self.assertEqual(before, [("narrate", en.get("aside")), ("narrate", "Some cultural fact."), ("narrate", en.get("aside_end"))],
                         "before it is taught, as always")
        _, milestone = aside(60, milestone=True)
        self.assertEqual(milestone, [("narrate", en.get("milestone_intro")), ("narrate", "Some cultural fact."), ("narrate", en.get("milestone_end"))])

    def test_the_commands_come_one_a_lesson_in_their_order(self):
        order = [i.id for i in self.cur.items if i.command]
        self.assertEqual(order, ["endurtaktu", "hlustadu", "haegt_command", "hlustadu_aftur", "edlilegum_hrada_command", "svarid_command",
                                 "aftur_ad_tala_command", "samtalinu_lokid_command", "stutt_samtal_command", "segdu_command", "hvernig_segir_madur_command",
                                 "klaradu_setninguna_command", "eitthvad_nytt_command", "segdu_hverja_setningu_command", "aefingunni_lokid_command",
                                 "sma_utudur_command", "aftur_ad_efninu_command"],
                         "lesson 54's then lesson 57's, by how often the lessons say them")
        learner = LearnerState("is", "en", "A1")
        for i in ("endurtaktu", "hlustadu"):
            learner.items[i] = ItemState(stage="meaning", successes=2, recalled=1, last_outcome="recalled", due=(TODAY + timedelta(days=3)).isoformat())
        learner.lessons_completed = 54
        planner = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        self.assertEqual(planner.next_command().id, "haegt_command")


if __name__ == "__main__":
    unittest.main()
