"""#451 step 3: a number word rests between lessons. After lesson 51 the owner asked for far fewer «þúsund», «fimm» and «tíu»: on the replay of the
lesson-52 export, «átta» was the answer of five of one lesson's sixteen pick-outs, and the clothes shop's two price turns gave «þúsund» in four lessons of
five. A pick-out whose answer's number words were heard less (in this lesson, and in the two before) comes first; the number choice takes a gender's
lines in turn («Ég á tvö börn.» beside «Það kostar tvö þúsund krónur.»)."""
import copy
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.numbers import ChoiceLine, number_words, pick_choice
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
IS_EN = Path(__file__).resolve().parent.parent / "curricula" / "is-en"


def line(sentence: str, value: int, gender: str) -> ChoiceLine:
    return ChoiceLine(sentence, sentence, value, "x", "y", gender, ())


class NumberWordsTests(unittest.TestCase):
    def test_the_number_words_of_a_line(self):
        self.assertEqual(number_words("Það kostar tvö þúsund og fimm hundruð krónur."), ["tvö", "þúsund", "fimm", "hundruð"])
        self.assertEqual(number_words("Klukkan hálf ellefu, og þú getur farið eftir tíu mínútur."), ["ellefu", "tíu"])
        self.assertEqual(number_words("Þarna til vinstri."), [])

    def test_the_choice_takes_a_genders_lines_in_turn(self):
        groups = {
            2: {"masc": [line("Tvo miða, takk.", 2, "masc")], "neut": [line("Það kostar tvö þúsund krónur.", 2, "neut"), line("Ég á tvö börn.", 2, "neut")]},
            3: {"masc": [line("Þrjá miða, takk.", 3, "masc")], "neut": [line("Það kostar þrjú þúsund krónur.", 3, "neut")]},
        }
        # the numbers take turns by lesson (2, 3, 2, 3, …); each time 2 comes round, its neuter is the next of its lines
        neuter_of_two = [pick_choice(groups, turn)[-1].sentence for turn in (0, 2, 4, 6)]
        self.assertEqual(neuter_of_two, ["Það kostar tvö þúsund krónur.", "Ég á tvö börn.", "Það kostar tvö þúsund krónur.", "Ég á tvö börn."])
        self.assertEqual([c.sentence for c in pick_choice(groups, 1)], ["Þrjá miða, takk.", "Það kostar þrjú þúsund krónur."])


class FormGenderTests(unittest.TestCase):
    """#451 step 3c (the owner: the same load, a second purpose): a number heard for its information also practises the form of 1–4 its noun's gender asks."""

    def test_the_gender_a_form_of_one_to_four_shows(self):
        from audiolesson.numbers import form_genders

        self.assertEqual(form_genders("Nei, það tekur bara tvær mínútur að ganga."), ["fem"])
        self.assertEqual(form_genders("Tvo fullorðna og tvö börn, takk."), ["masc", "neut"])
        self.assertEqual(form_genders("Það kostar fimm hundruð krónur."), [], "«fimm» has one form")
        self.assertEqual(form_genders("með tveimur"), [], "a form all genders share says nothing")
        # review of #517: not a choice of form, so not practice of it
        self.assertEqual(form_genders("Síminn minn er átta, sex, sjö, tveir, þrír, níu, einn."), [], "a phone number's counting forms")
        self.assertEqual(form_genders("Það kostar tvö þúsund krónur."), [], "a form fixed by «þúsund»")
        self.assertEqual(form_genders("Klukkan tvö, eða korter í fjögur."), [], "an hour")
        self.assertEqual(form_genders("Góðan daginn. Herbergi fyrir tvo?"), ["masc"])

    def test_the_towns_walking_times_have_feminine_values_beside_the_round_ones(self):
        """Adding, not replacing: on a course from the start the town comes before «tvær» and «þrjár» are known, and a turn whose values cannot be asked
        sends the pick-outs back to turns heard lately (#339's measure rose from 41 to 50 of about 155 over 60 simulated lessons when they replaced «fimm»)."""
        from audiolesson.numbers import form_genders

        cur = load_curriculum(IS_EN)
        town = next(t for t in load_themes(IS_EN, cur, load_cando(IS_EN)) if t.id == "town")
        for n in (0, 1):
            answers = [p["answer"] for turn in town.levels[n].turns if turn.who == "partner" for ln in [*turn.lines(), *turn.listen_lines()] for p in ln.probes]
            self.assertTrue(any("fem" in form_genders(a) for a in answers), f"town {n + 1}: {answers}")
            self.assertTrue(any(a.split()[-2:-1] and a.split()[-2] in ("fimm", "tíu") for a in answers), f"town {n + 1} keeps a round value")


class NumberRestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(IS_EN)
        scen = load_cando(IS_EN)
        cls.themes = load_themes(IS_EN, cls.cur, scen)
        cls.order = scenario_order(scen)

    def build(self, learner, day):
        cfg = PlanConfig(minutes=30, new_target=8, themes=self.themes, theme_scenarios=self.order)
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=day).build()

    def test_a_number_word_heard_lately_comes_after_the_others(self):
        """The same lesson built twice from one learner state with every number word rested, the second time with the words of its first numeric pick-out
        logged as heard in the lesson before: the second build asks them later, or not at all."""
        l, day = LearnerState("is", "en", "A1"), TODAY
        checked = moved = 0
        for k in range(1, 31):
            sc = self.build(l, day)
            if k >= 20:
                fresh = copy.deepcopy(l)
                fresh.listening_log = {key: at for key, at in l.listening_log.items() if not key.startswith("number:")}
                plain = self.build(fresh, day)
                first = next((number_words(a) for a in self.answers(plain) if number_words(a)), [])
                if first:
                    for w in first:
                        fresh.listening_log[f"number:{w}"] = l.next_lesson_number() - 1
                    again = self.build(fresh, day)
                    at = lambda s: next((i for i, a in enumerate(self.answers(s)) if set(number_words(a)) & set(first)), len(self.answers(s)))
                    self.assertGreaterEqual(at(again), at(plain), f"lesson {k}: {first} heard lately, asked sooner")
                    moved += at(again) > at(plain)
                    checked += 1
            apply_to_learner(sc, l, day)
            l.report([], [], day + timedelta(days=1), lesson_number=k, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertGreater(checked, 3, "lessons with numeric pick-outs (a test over none proves nothing)")
        self.assertGreater(moved, 0, "and in some the words heard lately waited for others")
        self.assertTrue(any(key.startswith("number:") for key in l.listening_log), "the words are logged for the lessons after")

    @staticmethod
    def answers(sc) -> list[str]:
        """The pick-outs' answers in the order the lesson asks them."""
        out = []
        for e in sc.exercises:
            if e.kind == "pick_out":
                said = [g.text for g in sc.segments if g.exercise == e.index and g.type == "answer" and g.text]
                if said:
                    out.append(said[0])
        return out


if __name__ == "__main__":
    unittest.main()
