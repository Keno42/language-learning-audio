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
        for _, _, sc in course.ListeningTaskTests._course(20):
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
        asked_back = [t.say for t in level.turns if t.who == "partner" and "En þú?" in t.say]
        self.assertEqual(asked_back, ["Takk! Ég er þrjátíu ára. En þú?"])
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

    def test_a_lead_in_can_be_the_levels_first_line(self):
        """Review of #433: «Já, ég er frá Akureyri. En þú?» answers the learner's opening «Ert þú íslensk?»; without it «Yes» answers a
        question never heard."""
        l, today = self.known("eg_er_japonsk", "ert_thu_islensk")
        dlg, turn_items, _, _, lead = self.planner(l, today).scene_line_of(self.cur.by_id["eg_er_japonsk"], set())
        self.assertEqual(dlg.id, "theme:smalltalk:3")
        self.assertEqual(dlg.turns[0].expect_text, "Ert þú íslensk?")
        self.assertTrue(dlg.turns[0].partner.startswith("Já, ég er frá Akureyri"))
        self.assertEqual((lead, turn_items[1]), ({0: True}, ["eg_er_japonsk"]))


if __name__ == "__main__":
    unittest.main()
