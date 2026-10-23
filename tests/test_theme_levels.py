"""The theme levels' content (#327): what a level asks the learner to say."""
import copy
import unittest
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import CurriculumError, load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.themes import check_gendered_lines, level_dialogue, load_themes
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class ThemeLevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "curricula" / "is-en"
        cls.cur = load_curriculum(path)
        cls.themes = {t.id: t for t in load_themes(path, cls.cur, load_cando(path))}

    def test_a_gendered_learner_line_has_its_mans_form(self):
        """A learner's line whose words follow the speaker's gender («Afsakið, ég er týnd.» / «…týndur.») carries its man's form, and only
        such a line does (owner, after #381: the line is said in the form of the learner's voice and the cue names it, as the review does, #375)."""
        check_gendered_lines(list(self.themes.values()), self.cur)  # the course as it is
        town = copy.deepcopy(self.themes["town"])
        lost = next(t for t in town.levels[2].turns if "eg_er_tynd" in t.items)
        lost.say_m = ""
        with self.assertRaisesRegex(CurriculumError, "needs its man's form"):
            check_gendered_lines([town], self.cur)
        thanks = next(t for t in town.levels[2].turns if t.items == ["takk_kaerlega"])
        lost.say_m, thanks.say_m = "Afsakið, ég er týndur.", "Takk."
        with self.assertRaisesRegex(CurriculumError, "no item of the line has a man's form"):
            check_gendered_lines([town], self.cur)

    def test_the_line_is_said_in_the_voice_opposite_the_partner_and_named(self):
        """The town's partner is a man: the learner says «Afsakið, ég er týnd.» in the woman's voice, «As a woman:». With a woman as the
        partner the same turn is «As a man:», «Afsakið, ég er týndur.», in the man's voice."""
        for partner, gender, line, voice in (("native_b", "woman", "Afsakið, ég er týnd.", "native_a"), ("native_a", "man", "Afsakið, ég er týndur.", "native_b")):
            town = copy.deepcopy(self.themes["town"])
            town.levels[2].partner_speaker = partner
            sc = Script(1, "t", self.cur.target_lang, self.cur.known_lang)
            builder = Planner(self.cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30)).builder
            ex = builder.dialogue(sc, level_dialogue(town, 2, "en"), translate=True)
            spoken = [(s.speaker, s.text) for s in sc.segments if s.exercise == ex.index and s.text]
            self.assertIn(("instructor", f"As a {gender}: Stop someone and say you're lost."), spoken)
            self.assertIn((voice, line), spoken)

    def test_asked_to_speak_more_slowly_the_partner_says_the_line_again_word_by_word(self):
        """#261 in a theme level (scenario A7's repair): after «Það tekur svona tíu mínútur.» the learner says «Fyrirgefðu, ég skil ekki.
        Gætirðu talað hægar?» and the passer-by says the line again, word by word. A theme's line is literal, so the request is read from
        the turn's items (`gaetirdu_talad_haegar`, `slows_partner`); before, only an authored dialogue's turn could ask it."""
        town = self.themes["town"]
        you = [t for t in town.levels[2].turns if t.who == "you"]
        ask = next(k for k, t in enumerate(you) if "gaetirdu_talad_haegar" in t.items)
        sc = Script(1, "t", self.cur.target_lang, self.cur.known_lang)
        builder = Planner(self.cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30)).builder
        ex = builder.dialogue(sc, level_dialogue(town, 2, "en"), translate=True, turn_items={k: t.items for k, t in enumerate(you)})
        segs = [s for s in sc.segments if s.exercise == ex.index]
        request = next(n for n, s in enumerate(segs) if s.text == "Fyrirgefðu, ég skil ekki. Gætirðu talað hægar?")
        spaced = [s.text for s in segs[request:] if s.role == "spaced"]
        self.assertEqual(" ".join(spaced).rstrip("."), "Það tekur svona tíu mínútur", "the line again, one word at a time")
        self.assertFalse(any(s.role == "spaced" for s in segs[:request]), "only the line after the request is slowed")

    def test_the_towns_third_level_is_the_way_itself(self):
        """After lesson 38 of the lesson-33 replay the day's new items were the way (left or right, how far, the map) and no level said
        them: the town's third level does."""
        level = self.themes["town"].levels[2]
        said = {i for turn in level.turns if turn.who == "you" for i in turn.items}
        self.assertLessEqual({"til_haegri", "hvad_er_langt_thangad", "geturdu_synt_mer_a_kortinu"}, said)
        probes = [p for turn in level.turns if turn.who == "partner" for line in turn.lines() for p in line.probes]
        self.assertTrue(any(p["kind"] == "duration" for p in probes), "how long it takes is picked out of the partner's answer")


    def test_small_talks_third_and_fourth_levels_say_the_lines_of_getting_to_know_someone(self):
        """After lesson 38 of the lesson-33 replay the day's new items were getting to know someone (nationality, work; age, married) and
        no level said them. Small talk's partner stays a woman, as the learner's questions to her are («Ert þú íslensk?», «Hvað ertu
        gömul?»): the learner's voice is then a man's, and the gendered lines are said «As a man:» in the man's form."""
        levels = self.themes["smalltalk"].levels
        said = [{i for turn in lv.turns if turn.who == "you" for i in turn.items} for lv in levels[2:4]]
        self.assertLessEqual({"ert_thu_islensk", "eg_er_japonsk", "eg_er_i_vinnuferd", "eg_vinn_hja"}, said[0])
        self.assertLessEqual({"hvad_ertu_gomul", "eg_er_ara", "eg_er_gift"}, said[1])
        self.assertEqual({lv.partner_speaker for lv in levels}, {"native_a"})
        dlg = level_dialogue(self.themes["smalltalk"], 2, "en")
        self.assertEqual(next(t.expect_text_m for t in dlg.turns if t.expect_text == "Ég er japönsk."), "Ég er japanskur.")

if __name__ == "__main__":
    unittest.main()
