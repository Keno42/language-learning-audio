"""#428 (the owner, 2026-11-25: a lesson-configure option): the learner's own name and age in the lines they say about themselves; a partner's
line, a note and the other number exercises are left as they are."""
import unittest
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.own import PERSONA_NAME, age_item, age_value, personalize, valid_name
from audiolesson.themes import load_themes

IS_EN = Path(__file__).resolve().parent.parent / "curricula" / "is-en"


class OwnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(IS_EN)
        cls.themes = load_themes(IS_EN, cls.cur, load_cando(IS_EN, cls.cur))

    def you_lines(self, themes):
        return [(t.id, turn) for t in themes for lv in t.levels for turn in lv.turns if turn.who == "you"]

    def test_the_persona_s_name_is_only_in_the_learner_s_own_lines(self):
        """The data rule the option relies on: «Yuki» is the learner's, never a partner's or a note's, so replacing it changes no one else."""
        for t in self.themes:
            for lv in t.levels:
                for turn in lv.turns:
                    if turn.who == "partner":
                        self.assertNotIn(PERSONA_NAME, turn.say + str(turn.variants), t.id)
        for n in self.cur.notes:
            self.assertNotIn(PERSONA_NAME, n.text, n.id)
        for d in self.cur.dialogues:
            for turn in d.turns:
                self.assertNotIn(PERSONA_NAME, (turn.partner or "") + (turn.opener or ""), d.id)

    def test_the_name_goes_into_every_line_of_the_learner_s_that_held_the_persona_s(self):
        cur, themes, applied = personalize(self.cur, self.themes, name="Kenji")
        self.assertEqual(applied, {"name": True, "age": False})
        self.assertEqual(cur.by_id["eg_heiti"].target, "Ég heiti Kenji.")
        self.assertIn("Kenji", cur.by_id["eg_heiti"].situation)
        self.assertEqual(cur.by_id["a_nafninu_yuki"].target, "Á nafninu Kenji.", "the id stays, so the learner's history carries over")
        said = [turn.say for _, turn in self.you_lines(themes)]
        self.assertIn("Hæ! Ég heiti Kenji. Hvað heitir þú?", said)
        self.assertFalse([s for s in said if PERSONA_NAME in s])
        self.assertFalse([i.id for i in cur.items if PERSONA_NAME in i.target])
        self.assertEqual(self.cur.by_id["eg_heiti"].target, "Ég heiti Yuki.", "the loaded course is not changed in place")

    def test_the_age_is_the_learner_s_when_the_course_can_teach_it(self):
        _, themes, applied = personalize(self.cur, self.themes, age=25)
        self.assertTrue(applied["age"])
        turn = next(turn for _, turn in self.you_lines(themes) if "eg_er_ara" in turn.items)
        self.assertEqual((turn.say, turn.items, turn.cue), ("Ég er tuttugu og fimm ára.", ["eg_er_ara", "tuttugu_og_fimm"], "Say you're 25."))
        partner = [turn.say for t in themes for lv in t.levels for turn in lv.turns if turn.who == "partner" and "ára" in turn.say]
        self.assertIn("Takk! Ég er þrjátíu ára. En þú?", partner, "her age is hers")
        self.assertIsNone(age_item(self.cur, 47))
        _, same, applied = personalize(self.cur, self.themes, age=47)
        self.assertFalse(applied["age"], "an age the course has no item for: the persona's stays")
        self.assertEqual([turn.say for _, turn in self.you_lines(same)], [turn.say for _, turn in self.you_lines(self.themes)])

    def test_every_age_filler_has_its_value_in_either_known_language(self):
        """Review of #608: the value was read from the English meaning, which a Japanese-glossed course replaces («25»): --own-age 25 was dropped."""
        ja = load_curriculum(IS_EN, known_lang="ja")
        for cur in (self.cur, ja):
            values = {i.id: age_value(i) for i in cur.items_with_tag("age")}
            self.assertNotIn(None, values.values(), values)
            self.assertEqual(age_item(cur, 25).id, "tuttugu_og_fimm")
        themes = load_themes(IS_EN, ja, load_cando(IS_EN, ja))
        _, mine, applied = personalize(ja, themes, age=25)
        self.assertTrue(applied["age"])
        turn = next(turn for _, turn in self.you_lines(mine) if "eg_er_ara" in turn.items)
        self.assertEqual((turn.say, turn.cue_ja), ("Ég er tuttugu og fimm ára.", "25歳だと言ってください。"))

    def test_a_name_is_one_word_of_letters(self):
        self.assertTrue(valid_name("Kenji") and valid_name("Ástríður") and valid_name("Mary-Ann"))
        for bad in ("", "Ken 2", "K3n", "{name}", "a" * 30, "健二"):
            self.assertFalse(valid_name(bad), bad)
        with self.assertRaises(ValueError):
            personalize(self.cur, self.themes, name="Ken 2")


if __name__ == "__main__":
    unittest.main()
