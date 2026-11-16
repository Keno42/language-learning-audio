"""#427 (lesson 40): conversational contexts and cue–answer pairs. «Is it normal to ask someone's age straight away, or to say you're single
and live alone?»; «here with your family?» answered by «I'm married»; «Velkomin!» said to the learner's line in a man's voice; a catch task
opening on small talk's closing line with nothing before it."""
import re
import unittest
from datetime import date, timedelta
from pathlib import Path

import tests.test_audiolesson as course
from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.themes import level_dialogue, load_themes, scenario_order
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class Lesson40ContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", cls.cur)
        cls.themes = load_themes(ROOT / "curricula" / "is-en", cls.cur, scenarios)
        cls.order = scenario_order(scenarios)

    def test_the_married_cues_ask_whether_you_are_married(self):
        gift = self.cur.by_id["eg_er_gift"]
        self.assertNotIn("family", gift.situations[0] if gift.situations else gift.situation)
        self.assertIn("married", gift.situation)
        cue_setups = [i.partner_cue_setup for i in self.cur.items if i.partner_cue_after == "eg_er_gift"]
        self.assertTrue(cue_setups and all("married" in c and "family" not in c for c in cue_setups), cue_setups)

    def test_no_welcome_agrees_with_one_learner(self):
        """«Velkomin» agrees with a woman or a group; said to the learner alone it may meet a man's voice. A table for two («Gott kvöld.
        Velkomin!») is a group and keeps it."""
        kynning = next(d for d in self.cur.dialogues if d.id == "kynning")
        self.assertNotIn("Velkomin", " ".join(t.partner or "" for t in kynning.turns))
        self.assertFalse([i.id for i in self.cur.items if "Velkomin" in (i.partner_cue or "") and "þú" in (i.partner_cue or "")])

    def test_small_talk_four_opens_its_questions(self):
        level = next(t for t in self.themes if t.id == "smalltalk").levels[3]
        self.assertEqual(level.turns[0].who, "partner")
        self.assertIn("afmæli", level.turns[0].say, "her birthday opens the age")
        said = " ".join(t.say for t in level.turns if t.who == "partner")
        self.assertNotIn("einhleyp", said, "she no longer volunteers that she is single and lives alone")

    def test_every_listening_task_names_its_scene_the_lessons_own_included(self):
        named = 0
        # 22 lessons, not 20: the hotel and bus scenes (#451 step 2c) push the second levels, which bring most listening, two lessons later
        for _, _, sc in course.ListeningTaskTests._course(22):
            for e in sc.exercises:
                if e.kind not in ("pick_out", "catch_unknown"):
                    continue
                first = next(s for s in sc.segments if s.exercise == e.index and s.type in ("narrate", "speak", "answer"))
                self.assertEqual(first.type, "narrate", (sc.lesson_number, e.label, first.text))
                named += 1
        self.assertGreater(named, 5)

    def test_each_question_of_small_talk_four_has_its_reason(self):
        """Lesson 42, after #433: «still odd to talk about marriage and age with another customer at a café, out of the blue». The level is a
        coffee with the friend made in the lounge, said by its own scene line; her birthday leads to the age, and her remark on your ring to
        «Ég er gift.»: «En þú?» follows only her age, the one thing it asks back."""
        theme = next(t for t in self.themes if t.id == "smalltalk")
        level = theme.levels[3]
        self.assertIn("Anna", level.scene_line)
        self.assertEqual(level_dialogue(theme, 3).setting, level.scene_line, "the level's scene, not «Someone sits down next to you»")
        self.assertEqual(level_dialogue(theme, 0).setting, theme.scene_line, "the other levels keep the theme's")
        k = next(k for k, t in enumerate(level.turns) if "eg_er_gift" in t.items)
        self.assertIn("hring", level.turns[k - 1].say, "her remark on the ring leads to whether you're married")
        asked_back = [line.say for t in level.turns if t.who == "partner" for line in t.lines() if "En þú?" in line.say]
        self.assertEqual(asked_back, [
            "Takk! Ég er þrjátíu ára. En þú?", "Takk! Þrjátíu ára í dag. En þú?",
            "Takk! Ég er tuttugu og sex ára. En þú?", "Takk! Ég er fjörutíu ára. En þú?",  # #534: her age has other values; each is still her age
        ])
        a = next(k for k, t in enumerate(level.turns) if "hvad_ertu_gomul" in t.items)
        self.assertIn("afmæli", level.turns[a - 1].say, "her birthday leads to the age")

    def known(self, *ids):
        today = date(2026, 3, 1)
        l = LearnerState("is", "en", "A1")
        for i in ids:
            l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, interval_days=7, recalled=3, last_outcome="recalled",
                                   due=(today + timedelta(days=5)).isoformat(), last_practiced=(today - timedelta(days=2)).isoformat())
        l.lessons_completed = 8
        return l, today

    def planner(self, learner, today):
        cfg = PlanConfig(minutes=30, new_target=8, themes=self.themes, theme_scenarios=self.order)
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=today)

    def test_a_scene_line_cut_from_the_middle_opens_on_the_line_its_partner_answers(self):
        """Review of #433 (lesson 40's learner): a hard «Ég vinn hjá litlu fyrirtæki.» was played from «Nú já! Hvar vinnur þú?», whose «Oh, I
        see!» answered nothing. The learner's line before it leads in, voiced when known, heard with its meaning when not; it is never asked."""
        l, today = self.known("eg_vinn_hja", "eg_er_i_vinnuferd")
        dlg, turn_items, key, asked, lead = self.planner(l, today).scene_line_of(self.cur.by_id["eg_vinn_hja"], set())
        self.assertEqual(dlg.id, "theme:smalltalk:3")
        self.assertEqual([t.expect_text for t in dlg.turns], ["Ég er í vinnuferð.", "Ég vinn hjá litlu fyrirtæki."])
        self.assertTrue(dlg.turns[0].partner.startswith("Nú já!"), "the partner's line answers the lead-in")
        self.assertEqual(turn_items, {0: ["eg_er_i_vinnuferd"], 1: ["eg_vinn_hja"]})
        self.assertEqual(lead, {0: True}, "known: voiced")
        sc = Script(title="t", lesson_number=1, known_lang="en", target_lang="is")
        p = self.planner(l, today)
        ex = p.builder.dialogue(sc, dlg, translate=True, turn_items=turn_items, heard_turns=frozenset({0}), lead_turns=frozenset({0}))
        self.assertEqual(ex.item_ids, ["eg_vinn_hja"], "the lead-in is never practice")
        texts = [s.text for s in sc.segments if s.exercise == ex.index and s.type != "pause"]
        self.assertLess(texts.index("Ég er í vinnuferð."), texts.index("Nú já! Hvar vinnur þú?"))
        self.assertNotIn(Prompts.load("en").get("dialogue_voiced_note"), texts, "not a set reply: no note")
        self.assertNotIn(Prompts.load("en").get("listening_line"), texts[: texts.index("Ég er í vinnuferð.")], "voiced: no «Here you would say:»")
        new, today = self.known("eg_vinn_hja")
        _, _, _, _, lead = self.planner(new, today).scene_line_of(self.cur.by_id["eg_vinn_hja"], set())
        self.assertEqual(lead, {0: False}, "never met: heard with its meaning")

    def test_a_scene_line_that_opens_its_level_has_no_lead_in(self):
        l, today = self.known("hvad_ertu_gomul")
        dlg, turn_items, _, _, lead = self.planner(l, today).scene_line_of(self.cur.by_id["hvad_ertu_gomul"], set())
        self.assertEqual((lead, list(turn_items)), ({}, [0]))
        self.assertTrue(dlg.turns[0].opener.startswith("Ég á afmæli"))

    def test_small_talk_fours_partner_lines_use_taught_words(self):
        """The owner, on «Maðurinn minn kemur í kvöld. Ég hef verið gift í tíu ár.»: «maðurinn», «minn» and «verið» are taught by no item
        before the level. Every word of her lines (a glossed word aside) is in an item no later than the level's own items."""
        level = next(t for t in self.themes if t.id == "smalltalk").levels[3]
        last = max(self.cur.by_id[i].order for t in level.turns for i in t.items)
        words = lambda text: {w.lower() for w in re.findall(r"[^\W\d_]+", text)}
        taught = set().union(*(words(i.target) | words(i.target_m or "") for i in self.cur.items if i.order <= last))
        for t in level.turns:
            if t.who != "partner":
                continue
            for line in t.lines():
                self.assertFalse(words(line.say) - taught - {w.lower() for w in line.word_glosses}, line.say)

    def test_a_scene_line_cut_from_a_level_keeps_the_levels_own_scene(self):
        """Review of #458: ``scene_line_of`` rebuilt the level from its goal and speaker only, so an excerpt of small talk 4 or 5 still said «Someone sits
        down next to you and says hello.» The excerpt keeps the level's own scene line, in both languages."""
        for lang in ("en", "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            themes = load_themes(ROOT / "curricula" / "is-en", cur, load_cando(ROOT / "curricula" / "is-en", cur))
            smalltalk = next(t for t in themes if t.id == "smalltalk")
            for item_id, n in (("eg_er_gift", 3), ("eg_hef_verid_her_adur", 4)):
                l, today = self.known(item_id, "eg_er_ara", "tuttugu_ara", "takk", "ja")
                p = Planner(cur, l, Prompts.load(lang), Timing(level="A1"),
                            PlanConfig(minutes=30, new_target=8, themes=themes, theme_scenarios=self.order), today=today)
                dlg, *_ = p.scene_line_of(cur.by_id[item_id], set())
                level = smalltalk.levels[n]
                self.assertEqual(dlg.id, f"theme:smalltalk:{n + 1}", (lang, item_id))
                self.assertEqual(dlg.setting, level.scene_line_ja if lang == "ja" else level.scene_line, (lang, item_id))

    def test_a_lead_in_can_be_the_levels_first_line(self):
        """Review of #433: «Já, ég er frá Akureyri. En þú?» answers the learner's opening «Ert þú íslensk?»; without it «Yes» answers a
        question never heard."""
        l, today = self.known("eg_er_japonsk", "ert_thu_islensk")
        dlg, turn_items, _, _, lead = self.planner(l, today).scene_line_of(self.cur.by_id["eg_er_japonsk"], set())
        self.assertEqual(dlg.id, "theme:smalltalk:3")
        self.assertEqual(dlg.turns[0].expect_text, "Ert þú íslensk?")
        self.assertTrue(dlg.turns[0].partner.startswith("Já, ég er frá Akureyri"))
        self.assertEqual((lead, turn_items[1]), ({0: False}, ["eg_er_japonsk"]), "it opens the exchange: heard with its cue, not voiced (lesson 53)")

    def test_a_reaction_to_a_line_no_one_said_opens_no_exchange(self):
        """Lesson 53: the exchange cut from the clothes shop's third level for «Áttu þetta í öðrum lit?» opened with «Æ, leiðinlegt.», an answer
        to «Þetta er of lítið.», which was not in it. The partner's line before the lead-in opens the exchange only when it asks something or is the
        level's first line; otherwise the lead-in opens it, heard with its cue (the model voice said it with no word before it)."""
        l, today = self.known("attu_thetta_i_odrum_lit", "attu_thetta_i_staerra")
        dlg, turn_items, _, _, lead = self.planner(l, today).scene_line_of(self.cur.by_id["attu_thetta_i_odrum_lit"], set())
        self.assertEqual(dlg.id, "theme:clothes:3")
        self.assertEqual([t.expect_text for t in dlg.turns], ["Áttu þetta í stærra?", "Áttu þetta í öðrum lit?"])
        self.assertIsNone(dlg.turns[0].opener)
        self.assertEqual(lead, {0: False})
        self.assertFalse(dlg.part, "it ends where its level ends")
        sc = Script(title="t", lesson_number=1, known_lang="en", target_lang="is")
        p = self.planner(l, today)
        p.builder.close_conversations = True
        p.builder.dialogue(sc, dlg, translate=True, turn_items=turn_items, heard_turns=frozenset({0}), lead_turns=frozenset())
        texts = [s.text for s in sc.segments if s.type != "pause"]
        en = Prompts.load("en")
        self.assertEqual(texts[0], en.get("dialogue_start"))
        self.assertLess(texts.index(en.get("listening_line")), texts.index("Áttu þetta í stærra?"))
        self.assertEqual(texts[-1], en.get("conversation_back"))

    def test_an_exchange_that_stops_before_its_level_ends_is_announced_and_closed_as_a_part(self):
        """Lesson 53: «That's the end of the conversation.» after the room number, with the key still to ask for."""
        l, today = self.known("attu_thetta_i_staerra", "thetta_er_of_litid")
        for lang in ("en", "ja"):
            p = Planner(self.cur, l, Prompts.load(lang), Timing(level="A1"), PlanConfig(minutes=30, new_target=8, themes=self.themes, theme_scenarios=self.order), today=today)
            dlg, turn_items, _, _, lead = p.scene_line_of(self.cur.by_id["attu_thetta_i_staerra"], set())
            self.assertTrue(dlg.part)
            sc = Script(title="t", lesson_number=1, known_lang=lang, target_lang="is")
            p.builder.close_conversations = True
            p.builder.dialogue(sc, dlg, translate=True, turn_items=turn_items, heard_turns=frozenset(lead), lead_turns=frozenset(k for k, v in lead.items() if v))
            texts = [s.text for s in sc.segments if s.type != "pause"]
            self.assertEqual((texts[0], texts[-1]), (Prompts.load(lang).get("dialogue_start_part"), Prompts.load(lang).get("conversation_part_back")), lang)
            self.assertEqual([s.role for s in sc.segments if s.type != "pause"][-1], "conversation_back", "the same way back, kept or dropped by what follows")

    def test_no_line_is_cut_from_a_level_the_lesson_has_played(self):
        """Lesson 53: the hotel desk was heard three times (its two plays and an exchange cut from it for «Á nafninu Yuki.») and the clothes shop's
        third level twice (one exchange for each of two hard items). The level the lesson plays, and a level a line was cut from, give no other."""
        l, today = self.known("attu_thetta_i_odrum_lit", "attu_thetta_i_staerra")
        p = self.planner(l, today)
        self.assertIsNotNone(p.scene_line_of(self.cur.by_id["attu_thetta_i_odrum_lit"], set()))
        self.assertIsNone(p.scene_line_of(self.cur.by_id["attu_thetta_i_odrum_lit"], set(), {"clothes:3"}))


if __name__ == "__main__":
    unittest.main()
