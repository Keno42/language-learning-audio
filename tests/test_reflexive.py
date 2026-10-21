"""A reflexive fill («hvíla mig») goes only into a template whose subject is «ég» (lesson 31 on the replay of the lesson-30 export:
«Viltu hvíla mig?» and «Ætlarðu að hvíla mig?», "do you want to / are you going to rest me?")."""
import copy
import unittest
from pathlib import Path

from audiolesson.content import CurriculumError, load_curriculum, validate
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
ADDRESSED = ("Viltu hvíla mig", "Ætlarðu að hvíla mig", "Ertu að hvíla mig", "Finnst þér gaman að hvíla mig")


def builder(cur, known):
    """A learner who knows ``known`` and has heard the notes for the negative and question forms, both modelled for every known pattern."""
    learner = LearnerState("is", "en", "A1")
    for i in known:
        learner.items[i] = ItemState(stage="meaning", successes=3, recalled=2, durable_successes=2)
    learner.notes_heard = {"negation_ekki": 1, "question_verb_first": 1}
    b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
    b.forms_modelled = {f"{c}:{f}" for c in known if cur.by_id[c].kind == "construction" for f in ("negative", "question")}
    return b


class ReflexiveFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_data_marks_the_fill_and_the_templates_that_speak_to_the_other_person(self):
        by = self.cur.by_id
        self.assertTrue(by["hvila_mig"].reflexive)
        self.assertEqual(by["viltu"].addressee, ["plain"])
        for c in ("eg_vil", "eg_aetla_ad", "eg_er_ad_inf", "mer_finnst_gaman_ad"):
            self.assertEqual(by[c].addressee, ["question"], c)

    def test_a_template_that_speaks_to_the_other_person_takes_no_reflexive_fill(self):
        by = self.cur.by_id
        self.assertNotIn("hvila_mig", [i.id for i in self.cur.items_with_tag("inf", by["viltu"])], "«Viltu hvíla mig?»")
        self.assertIn("hvila_mig", [i.id for i in self.cur.items_with_tag("inf", by["eg_vil"])], "«Ég vil hvíla mig.» stays")
        fills = {"inf": by["hvila_mig"]}
        self.assertTrue(self.cur.fits_form(by["eg_aetla_ad"], fills, None))
        self.assertTrue(self.cur.fits_form(by["eg_aetla_ad"], fills, "negative"), "«Ég ætla ekki að hvíla mig.»")
        self.assertFalse(self.cur.fits_form(by["eg_aetla_ad"], fills, "question"), "«Ætlarðu að hvíla mig?»")
        self.assertTrue(self.cur.fits_form(by["eg_aetla_ad"], {"inf": by["versla"]}, "question"), "«Ætlarðu að versla?» stays")

    def test_generated_sentences_never_put_it_after_another_subject(self):
        """Every pattern with an infinitive slot, every form, with «hvíla mig» the only fill the learner knows: no sentence speaks to the other person
        with «mig»; the plain and negative sentences after «ég» are still made."""
        made: set[str] = set()
        for c in ("eg_vil", "eg_aetla_ad", "viltu", "eg_er_ad_inf", "mer_finnst_gaman_ad", "ma_eg_inf"):
            b = builder(self.cur, [c, "hvila_mig"])
            for form in (None, "negative", "question"):
                for _ in range(3):
                    gen = b.generate(self.cur.by_id[c], form=form, prefer_unused=False)
                    if gen is not None:
                        made.add(gen.target)
        self.assertFalse([t for t in made if t.startswith(ADDRESSED)], made)
        self.assertIn("Ég vil hvíla mig.", made)
        self.assertIn("Ég ætla ekki að hvíla mig.", made)

    def test_the_form_model_shows_a_fill_that_fits_the_form(self):
        """``model_form`` says the plain sentence, then the same fill in the form: «hvíla mig» is never the one shown as a question."""
        b = builder(self.cur, ["eg_aetla_ad", "hvila_mig", "versla"])
        for _ in range(5):
            sc = Script(1, "t", "is", "en")
            b.model_form(sc, self.cur.by_id["eg_aetla_ad"], "question")
            said = [g.text for g in sc.segments if g.type in ("speak", "answer")]
            self.assertTrue(said, "«versla» fits: there is a model")
            self.assertFalse([t for t in said if t.startswith(ADDRESSED)], said)
        alone = builder(self.cur, ["eg_aetla_ad", "hvila_mig"])
        self.assertIsNone(alone.model_form(Script(1, "t", "is", "en"), self.cur.by_id["eg_aetla_ad"], "question"), "no fill fits: no model")

    def test_validate_checks_the_two_fields(self):
        for item_id, field, value in (("eg_vil", "addressee", ["imperative"]), ("hvila_mig", "addressee", ["plain"]), ("eg_vil", "reflexive", True)):
            cur = copy.deepcopy(self.cur)
            setattr(cur.by_id[item_id], field, value)
            with self.assertRaises(CurriculumError, msg=(item_id, field)):
                validate(cur)


if __name__ == "__main__":
    unittest.main()
