"""#439 step 1b (the owner after lesson 49): the forms of 1–4, which change with the gender and case of the noun they count, lacked practice to use
them right. The learner had each form through one frame («tvo» for tickets, «tvö» for prices, «eina» for a hot dog) and no exercise asked for the form
a noun chooses. Once a lesson, one number's known lines of different genders are heard side by side, the reason named once, and each is asked again."""
import dataclasses
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import CurriculumError, _check_counts, load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.numbers import ChoiceLine, agrees, choice_lines, number_in, pick_choice, value_of
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


class NumberChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_forms_of_one_to_four(self):
        self.assertEqual(number_in("Tvo miða, takk."), ("Tvo", 2, "miða"))
        self.assertEqual(number_in("Það kostar þrjú þúsund krónur."), ("þrjú", 3, "þúsund"))
        self.assertIsNone(number_in("Ég er fimm ára."))
        self.assertEqual((value_of("eina"), value_of("fjögur"), value_of("fimm")), (1, 4, None))
        self.assertTrue(agrees("tvo", 2, "masc") and agrees("tvær", 2, "fem") and agrees("tvö", 2, "neut"))
        self.assertFalse(agrees("tvo", 2, "neut"), "«Tvo kaffi» counts «bolla», not «kaffi»")

    def test_a_line_names_a_noun_its_number_agrees_with(self):
        _check_counts(self.cur, self.cur.by_id["eg_a_tvo_born"])  # «tvö» with «barn», neuter
        _check_counts(self.cur, self.cur.by_id["count_mida_takk"])  # «tvo», «þrjá», «fjóra» with «miði», masculine
        with self.assertRaises(CurriculumError):
            _check_counts(self.cur, dataclasses.replace(self.cur.by_id["tvo_kaffi"], counts="kaffi"))
        with self.assertRaises(CurriculumError):
            _check_counts(self.cur, dataclasses.replace(self.cur.by_id["eg_a_tvo_born"], counts="no_such_noun"))
        with self.assertRaises(CurriculumError):
            _check_counts(self.cur, dataclasses.replace(self.cur.by_id["count_mida_takk"], counts="pylsa"))

    def test_lines_are_grouped_by_number_and_gender_and_one_number_is_picked(self):
        groups = choice_lines([
            ("Tvo miða, takk.", "Two tickets, please.", "masc", ["count_mida_takk", "tvo_acc"], None),
            ("Ég á tvö börn.", "I have two children.", "neut", ["eg_a_tvo_born"], None),
            ("Tvo kaffi, takk.", "Two coffees, please.", "neut", ["tvo_kaffi"], None),  # does not agree: left out
            ("Þrjá miða, takk.", "Three tickets, please.", "masc", ["thrja_mida"], None),
        ])
        self.assertEqual(sorted(groups), [2, 3])
        self.assertEqual([line.sentence for line in groups[2]["neut"]], ["Ég á tvö börn."])
        picked = pick_choice(groups, turn=0)
        self.assertEqual([(line.form, line.gender) for line in picked], [("Tvo", "masc"), ("tvö", "neut")], "only 2 has two genders")

    def test_the_exercise_names_why_and_asks_each_again(self):
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        lines = [ChoiceLine("Tvo miða, takk.", "Two tickets, please.", 2, "Tvo", "miða", "masc", ("count_mida_takk", "tvo_acc")),
                 ChoiceLine("Ég á tvö börn.", "I have two children.", 2, "tvö", "börn", "neut", ("eg_a_tvo_born",))]
        ex = b.number_choice(sc, lines)
        self.assertEqual((ex.kind, ex.stage), ("model", "choice"))
        text = sc.transcript()
        self.assertIn("is masculine, so:", text)
        self.assertIn("is neuter, so:", text)
        answers = [g.text for g in sc.segments if g.type == "answer"]
        self.assertEqual(answers, ["Ég á tvö börn.", "Tvo miða, takk."], "asked again in another order")
        spoken = [g.text for g in sc.segments if g.type == "speak"]
        self.assertIn("tvo", spoken, "the form is named lower case, as said in the sentence")

    def test_a_lesson_plays_one_choice_once_two_genders_of_a_number_are_known(self):
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id["tvaer"].order:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        learner.lessons_completed = 30
        sc = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY).build()
        choices = [e for e in sc.exercises if e.stage == "choice"]
        self.assertEqual(len(choices), 1, sc.meta["number_choices"])
        self.assertEqual(sc.meta["number_choices"], [choices[0].label])
        heard = [g.text for g in sc.segments if g.exercise == choices[0].index and g.type == "answer"]
        found = [number_in(t) for t in heard]
        self.assertEqual(len({value for _, value, _ in found}), 1, f"one number: {heard}")
        self.assertGreaterEqual(len(heard), 2)

    def test_no_choice_while_a_number_is_known_in_one_gender_only(self):
        learner = LearnerState("is", "en", "A1")
        for i in ("count_mida_takk", "tvo_acc", "midi", "mida", "takk"):
            if i in self.cur.by_id:
                learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                             due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        p = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY)
        self.assertEqual(pick_choice(choice_lines(p.number_choice_candidates()), 1), [])

    def test_a_form_that_is_not_the_nominative_names_its_case(self):
        """Lesson 50 as drafted: «miða is masculine, so: þrjá» left out why not «þrír». A form that is not the nominative names the case and the
        nominative it comes from; a form that is also the nominative («tvö», «einn») names the gender only."""
        groups = choice_lines([("Þrjá miða, takk.", "Three tickets, please.", "masc", ["thrja_mida"], None),
                               ("Það kostar þrjú þúsund krónur.", "It costs three thousand krónur.", "neut", ["thad_kostar_big"], None)])
        lines = pick_choice(groups, 0)
        self.assertEqual([(line.case, line.nominative) for line in lines], [("acc", "þrír"), ("nom", "þrjú")])
        for lang, case_words in (("en", "in the accusative here:"), ("ja", "ここでは対格なので、")):
            b = Builder(self.cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
            sc = Script(1, "t", "is", lang)
            b.number_choice(sc, lines)
            narrated = [g.text for g in sc.segments if g.type == "narrate"]
            spoken = [g.text for g in sc.segments if g.type == "speak"]
            self.assertTrue(any(case_words in t for t in narrated), (lang, narrated))
            self.assertEqual(spoken[spoken.index("miða") + 1 : spoken.index("miða") + 3], ["þrír", "þrjá"], lang)
            self.assertEqual(sum(case_words in t for t in narrated), 1, f"{lang}: «þrjú» before «þúsund» is also the nominative: no case")

    def _met(self, ids):
        learner = LearnerState("is", "en", "A1")
        for i in ids:
            learner.items[i] = ItemState(stage="meaning", durable_successes=1, successes=3, recalled=1, interval_days=3, last_outcome="recalled",
                                         due=(TODAY + timedelta(days=3)).isoformat(), last_practiced=(TODAY - timedelta(days=1)).isoformat())
        return learner

    def test_a_line_that_adds_a_missing_gender_is_brought_forward(self):
        """Lesson 50 still set «tvo» (masculine) against «tvö» (neuter): the feminine forms of 2–4 had not come. A line not met yet that gives a known
        number its missing gender («fyrir tvær nætur») goes after the theme's items in the order of new material."""
        learner = self._met(["count_mida_takk", "tvo_acc", "midi", "mida", "thad_kostar_big", "tvo", "thusund", "kronur"])
        p = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        self.assertEqual(p.choice_wants(), ["fyrir_tvaer_naetur"])
        _check_counts(self.cur, self.cur.by_id["fyrir_tvaer_naetur"])  # a vocab item of two words or more may carry counts
        learner.items["fyrir_tvaer_naetur"] = learner.items["tvo"]
        learner.learned_wholes["fyrir_tvaer_naetur"] = {"through": "x", "answer": "Ég vil herbergi fyrir tvær nætur.", "meaning": "I'd like a room for two nights."}
        p = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        self.assertNotIn("fyrir_tvaer_naetur", p.choice_wants())
        lines = pick_choice(choice_lines(p.number_choice_candidates()), 0)
        two = [line for line in lines if line.value == 2] or pick_choice({2: choice_lines(p.number_choice_candidates())[2]}, 0)
        self.assertEqual([line.gender for line in two], ["masc", "fem", "neut"])
        self.assertIn("Ég vil herbergi fyrir tvær nætur.", [line.sentence for line in two], "a part is said in the sentence it was taught in")


if __name__ == "__main__":
    unittest.main()
