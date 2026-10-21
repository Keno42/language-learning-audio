"""#270 step 3: a new form of a noun is named against the form the learner already has."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


def builder(cur, met=()):
    learner = LearnerState("is", "en", "A1")
    for i in met:
        learner.items[i] = ItemState(stage="meaning", successes=2, recalled=1)
    return Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)


class FormContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_basic_form_is_the_authored_base_or_a_met_nominative_and_another_met_form_is_only_known(self):
        by = self.cur.by_id
        self.assertEqual(builder(self.cur).basic_form_of(by["koku"]), ("kaka", "basic"), "the authored basic word needs no item")
        self.assertIsNone(builder(self.cur).basic_form_of(by["bil"]), "«bíll» not met: nothing to name it against")
        self.assertEqual(builder(self.cur, ["bill"]).basic_form_of(by["bil"]), ("bíll", "basic"), "a met nominative is the basic word")
        self.assertEqual(builder(self.cur, ["hotelid"]).basic_form_of(by["hotelinu"]), ("hótelið", "known"), "a met nom_def is a known form, not the basic word «hótel»")
        self.assertIsNone(builder(self.cur, ["bill"]).basic_form_of(by["bill"]), "a form is not its own contrast")
        self.assertIsNone(builder(self.cur, ["bill"]).basic_form_of(by["hus"]), "a noun with one form has no contrast")

    def test_the_contrast_is_said_once_in_the_introduction_frame(self):
        prompts = Prompts.load("en")
        for met, item, word, key in ((["bill"], "bil", "bíll", "form_of_base"), (["hotelid"], "hotelinu", "hótelið", "form_known_as")):
            b = builder(self.cur, met)
            sc = Script(1, "t", "is", "en")
            ex = sc.new_exercise("intro", "intro", [item], "x")
            b._form_contrast(sc, ex, self.cur.by_id[item], "native_a")
            said = [(g.type, g.text) for g in sc.segments if g.type in ("narrate", "speak")]
            self.assertEqual(said, [("narrate", prompts.get(key)), ("speak", word)], item)
        self.assertNotIn("basic word", prompts.get("form_known_as"))
        sc2 = Script(1, "t", "is", "en")
        ex2 = sc2.new_exercise("intro", "intro", ["bil"], "x")
        builder(self.cur)._form_contrast(sc2, ex2, self.cur.by_id["bil"], "native_a")
        self.assertEqual(sc2.segments, [], "nothing met: nothing said")


class FormInItsFrameTests(unittest.TestCase):
    """#270, first step (lesson 36, then lesson 31, on the lesson-30 replay): a form of a known noun («bankanum» of «bankinn») was introduced alone,
    «Here is another form of it: To the bank.», and asked bare, before the frame that needs it. It is introduced in that frame, named against the
    form the learner knows, with why the form changes there, once."""

    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        cls.cur_ja = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")

    def said(self, sc, ex):
        return [(g.type, g.text) for g in sc.segments if g.exercise == ex.index and g.type in ("narrate", "speak", "answer")]

    def test_a_form_of_a_met_noun_is_introduced_in_its_frame_with_the_known_form_and_the_reason(self):
        b = builder(self.cur, ["bankinn", "eg_er_ad_koma"])  # «Ég er að» known: «leita» is the one new word of the frame
        sc = Script(31, "t", "is", "en")
        ex = b.intro(sc, self.cur.by_id["bankanum"])
        said = self.said(sc, ex)
        self.assertIn(("speak", "Ég er að leita að bankanum."), said, "the sentence of the frame that asks the form")
        self.assertIn(("narrate", "You know it as:"), said)
        self.assertIn(("speak", "bankinn"), said)
        self.assertIn(("speak", "leita að"), said, "the reason names the words that decide")
        self.assertNotIn(("narrate", Prompts.load("en").get("variant_known")), said, "not the near-form introduction")
        self.assertEqual([t for k, t in said if k == "answer"], ["Ég er að leita að bankanum."], "the first retrieval asks the sentence, not the bare form")
        self.assertEqual(b.wholes_taught["bankanum"]["answer"], "Ég er að leita að bankanum.", "its later practice and the review ask the sentence")
        self.assertFalse(any("bank" in t.lower() and t.lower().startswith("to ") for k, t in said if k == "narrate"), "no «To the bank.» standing in for the reason")

    def test_the_reason_comes_in_the_learners_language(self):
        b = Builder(self.cur_ja, Prompts.load("ja"), Timing(level="A1"), builder(self.cur_ja, ["bankinn", "eg_er_ad_koma"]).learner)
        sc = Script(31, "t", "is", "ja")
        ex = b.intro(sc, self.cur_ja.by_id["bankanum"])
        said = self.said(sc, ex)
        self.assertIn(("speak", "leita að"), said)
        self.assertTrue(any(k == "narrate" and "この形" in t for k, t in said), said)

    def test_the_reason_is_said_once_a_lesson_per_frame(self):
        b = builder(self.cur, ["bankinn", "hotelid"])
        frame = self.cur.by_id["eg_er_ad_leita_ad"]
        sc = Script(31, "t", "is", "en")
        first = sc.new_exercise("intro", "intro", ["bankanum"], "x")
        b._form_contrast(sc, first, self.cur.by_id["bankanum"], "native_a", frame)
        second = sc.new_exercise("intro", "intro", ["hotelinu"], "y")
        b._form_contrast(sc, second, self.cur.by_id["hotelinu"], "native_a", frame)
        self.assertIn(("speak", "leita að"), self.said(sc, first))
        self.assertEqual(self.said(sc, second), [("narrate", "You know it as:"), ("speak", "hótelið")], "the contrast again, the reason not")

    def test_a_form_taken_out_of_a_worked_example_is_named_against_the_known_form_too(self):
        b = builder(self.cur, ["bankinn"])
        b.modeled_wholes["bankanum"] = {"through": "eg_er_ad_leita_ad", "answer": "Ég er að leita að bankanum.", "meaning": "I'm looking for the bank.", "gender": None}
        sc = Script(31, "t", "is", "en")
        ex = b.intro(sc, self.cur.by_id["bankanum"])
        said = self.said(sc, ex)
        self.assertEqual(said[0], ("narrate", Prompts.load("en").get("embed_known")), "taken out of the sentence just heard")
        self.assertIn(("speak", "bankinn"), said)
        self.assertIn(("speak", "leita að"), said)

    def test_a_near_form_that_is_no_noun_keeps_its_introduction(self):
        b = builder(self.cur, ["tveir"])
        sc = Script(31, "t", "is", "en")
        ex = b.intro(sc, self.cur.by_id["tvaer"])
        self.assertEqual(self.said(sc, ex)[0], ("narrate", Prompts.load("en").get("variant_known")))

    def test_a_form_taught_today_is_the_one_it_is_named_against(self):
        """Review of #368: «bankinn» introduced earlier in this lesson, then «bankanum»: the contrast and the reason are said too."""
        b = builder(self.cur, ["eg_er_ad_koma"])
        b.in_lesson.add("bankinn")
        sc = Script(31, "t", "is", "en")
        ex = b.intro(sc, self.cur.by_id["bankanum"])
        said = self.said(sc, ex)
        self.assertIn(("speak", "Ég er að leita að bankanum."), said)
        self.assertIn(("narrate", "You know it as:"), said)
        self.assertIn(("speak", "bankinn"), said)
        self.assertIn(("speak", "leita að"), said)

    def test_form_reason_goes_on_a_frame(self):
        from audiolesson.content import CurriculumError, curriculum_from_dict
        items = [{"id": "x", "kind": "phrase", "target": "Já.", "meaning": "Yes.", "form_reason": "Why."}]
        with self.assertRaises(CurriculumError):
            curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})


class FrameFirstForAFormTests(unittest.TestCase):
    """Review of #368: the frame is new too and two of its words are new, so the form has no home yet (``whole_home``): the frame queued for this
    lesson comes first, its worked example made of the form, and the form is taken out of that sentence, named against the known form."""

    def cur(self):
        from audiolesson.content import curriculum_from_dict
        items = [
            {"id": "bankinn", "kind": "vocab", "target": "bankinn", "meaning": "the bank", "noun": "banki", "form": "nom_def", "gender": "masc", "tags": ["nom_place"]},
            {"id": "bankanum", "kind": "vocab", "target": "bankanum", "meaning": "the bank", "meaning_spoken": "to the bank", "noun": "banki", "form": "dat_def", "gender": "masc",
             "variant_of": "bankinn", "tags": ["dat_place"]},
            {"id": "leita", "kind": "construction", "target": "Ég er að leita að {place}.", "meaning": "I'm looking for {place}.", "slots": {"place": "dat_place"},
             "example": {"place": "bankanum"}, "prereqs": ["bankanum"], "form_reason": "This form comes after «leita að»."},
        ]
        return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})

    def test_the_frame_comes_first_and_the_form_is_taken_out_of_it(self):
        from datetime import date
        from audiolesson.planner import PlanConfig, Planner
        cur = self.cur()
        learner = LearnerState("is", "en", "A1")
        learner.items["bankinn"] = ItemState(stage="meaning", successes=2, recalled=1, due="2026-03-20")
        learner.lessons_completed = 6
        p = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=8, new_items=2, max_new_items=2, seed=1), today=date(2026, 3, 1))
        self.assertIsNone(p.builder.whole_home(cur.by_id["bankanum"]), "«ég», «er», «að», «leita» are new: no home yet")
        self.assertEqual(p.frame_first(cur.by_id["bankanum"], [cur.by_id["leita"]]), (cur.by_id["leita"], "place"))
        sc = p.build()
        intros = [e for e in sc.exercises if e.kind == "intro"]
        self.assertEqual([e.item_ids[0] for e in intros[:2]], ["leita", "bankanum"], "the pattern first, then the form out of its worked example")
        form = intros[1]
        said = [(g.type, g.text) for g in sc.segments if g.exercise == form.index and g.type in ("narrate", "speak", "answer")]
        self.assertEqual(said[0], ("narrate", Prompts.load("en").get("embed_known")))
        self.assertIn(("speak", "bankinn"), said)
        self.assertIn(("speak", "leita að"), said)
        self.assertEqual([t for k, t in said if k == "answer"], ["Ég er að leita að bankanum."], "the sentence is asked, not the bare form")
        narrated = [g.text for g in sc.segments if g.type == "narrate"]
        self.assertFalse(any(t.startswith("Here is another form of it") for t in narrated), "no near-form introduction")


if __name__ == "__main__":
    unittest.main()
