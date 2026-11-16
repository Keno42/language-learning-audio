"""#439 step 3. Lesson 52: «Getting used to the changing endings, «nafninu», «bókun», is hard»; «Á nafninu Yuki.» came with no word on its form and was
not recalled the next day. Lesson 54: «what case is ~daginn?». A new phrase or chunk whose noun is in a form other than its basic word, the noun
having no item of its own, names the form against the basic word and says which form it is, once a lesson for the same reason."""
import dataclasses
import unittest
from pathlib import Path

from audiolesson.content import CurriculumError, load_curriculum, validate
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
DAYS = ("a_manudaginn", "a_thridjudaginn", "a_midvikudaginn", "a_fimmtudaginn", "a_fostudaginn", "a_laugardaginn", "a_sunnudaginn")


class WordFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def builder(self, lang="en"):
        cur = self.cur if lang == "en" else load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
        learner = LearnerState("is", lang, "A1")
        for i in cur.items:
            if i.order < cur.by_id["a_manudaginn"].order:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, last_outcome="recalled", due="2026-12-01")
        return cur, Builder(cur, Prompts.load(lang), Timing(level="A1"), learner)

    def said(self, sc, ex):
        return [g.text for g in sc.segments if g.exercise == ex.index and g.type != "pause"]

    def test_a_new_phrase_names_its_noun_against_the_basic_word_before_the_first_retrieval(self):
        cur, b = self.builder()
        sc = Script(1, "t", "is", "en")
        said = self.said(sc, b.intro(sc, cur.by_id["a_nafninu_yuki"]))
        at = said.index("is a form of")
        self.assertEqual(said[at - 1 : at + 2], ["nafninu", "is a form of", "nafn"])
        self.assertIn('The ending adds "the".', said)
        self.assertTrue(any("dative" in t for t in said))
        self.assertLess(at, len(said) - 2, "then the first retrieval")
        self.assertEqual(said[-1], "Á nafninu Yuki.")

    def test_the_days_share_their_reason_once_a_lesson_and_each_names_its_own_word(self):
        """Lesson 54 taught three days; the reason said three times would be the remark of lesson 31 (an instruction narrated nine times)."""
        cur, b = self.builder()
        sc = Script(1, "t", "is", "en")
        heard = []
        for day in ("a_fimmtudaginn", "a_fostudaginn"):
            heard.append(self.said(sc, b.intro(sc, cur.by_id[day])))
            b.in_lesson.add(day)
        self.assertIn("fimmtudagur", heard[0])
        self.assertIn("föstudagur", heard[1])
        self.assertTrue(any("accusative" in t for t in heard[0]))
        self.assertFalse(any("accusative" in t for t in heard[1]), "the same reason is said once a lesson")

    def test_every_day_has_its_basic_word_in_both_languages(self):
        for lang in ("en", "ja"):
            cur, b = self.builder(lang)
            for day in DAYS:
                item = cur.by_id[day]
                self.assertTrue(item.form_base.endswith("dagur") and item.form_word.endswith("daginn") and item.form_reason, (lang, day))
            sc = Script(1, "t", "is", lang)
            said = self.said(sc, b.intro(sc, cur.by_id["a_sunnudaginn"]))
            self.assertIn("sunnudagur", said, lang)

    def test_the_fields_are_checked(self):
        def with_item(**changes):
            return dataclasses.replace(self.cur, items=[dataclasses.replace(i, **changes) if i.id == "a_nafninu_yuki" else i for i in self.cur.items])

        for changes in ({"form_word": "nafni"}, {"form_base": ""}, {"form_base": "nafninu"}):
            with self.subTest(changes=changes), self.assertRaises(CurriculumError):
                validate(with_item(**changes))
        noun_form = next(i for i in self.cur.items if i.noun)
        bad = dataclasses.replace(self.cur, items=[dataclasses.replace(i, form_base="x") if i.id == noun_form.id else i for i in self.cur.items])
        with self.assertRaises(CurriculumError):
            validate(bad)


if __name__ == "__main__":
    unittest.main()
