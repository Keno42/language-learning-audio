"""#528 step 2, the noun by its frame (the owner, 2026-11-12: «I want to feel a coach who makes me choose the right case and the right verb form»).
A noun the learner has in two forms or more is said in the sentence each form was taught in, the case named, then each sentence is asked from its
meaning: the form is said as the choice its frame makes («Hvar er bankinn?» / «Ég er að leita að bankanum.»)."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing
from audiolesson.transitions import mode

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent
WHOLES = {
    "bankinn": {"through": "hvar_er", "answer": "Hvar er bankinn?", "meaning": "Where is the bank?"},
    "bankanum": {"through": "eg_er_ad_leita_ad", "answer": "Ég er að leita að bankanum.", "meaning": "I'm looking for the bank."},
    "fisk": {"through": "eg_elska", "answer": "Ég elska fisk.", "meaning": "I love fish."},
}


def known(**extra) -> ItemState:
    return ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                     due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat(), **extra)


class NounChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "curricula" / "is-en"
        cls.cur = load_curriculum(path)
        scenarios = load_cando(path, cls.cur)
        cls.themes = load_themes(path, cls.cur, scenarios)
        cls.order = scenario_order(scenarios)

    def planner(self, learner: LearnerState) -> Planner:
        cfg = PlanConfig(minutes=30, seed=1, new_target=8, themes=self.themes, theme_scenarios=self.order)
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)

    def learner(self, wholes=WHOLES, stop="bankanum") -> LearnerState:
        """A learner who knows the course up to ``stop`` (the bank's dative among it), with the sentences ``wholes`` names."""
        learner = LearnerState("is", "en", "A1")
        upto = self.cur.by_id[stop].order
        for it in self.cur.items:
            if it.order <= upto:
                learner.items[it.id] = known()
        learner.learned_wholes = {k: dict(v) for k, v in wholes.items()}
        learner.lessons_completed = 40
        return learner

    def test_a_noun_met_in_two_forms_is_a_choice_and_one_in_one_form_waits(self):
        nouns = {lines[0][0].noun: lines for lines in self.planner(self.learner()).noun_choice_candidates()}
        self.assertIn("banki", nouns)
        bank = nouns["banki"]
        self.assertEqual([(it.id, case) for it, case, *_ in bank], [("bankinn", "nom"), ("bankanum", "dat")], "the nominative first")
        self.assertEqual([sentence for _, _, sentence, _, _ in bank], ["Hvar er bankinn?", "Ég er að leita að bankanum."])
        self.assertEqual(bank[1][4].id, "eg_er_ad_leita_ad", "the frame the form was taught in")
        self.assertNotIn("fiskur", nouns, "«fisk» alone: «fiski» has no sentence yet")

    def test_a_failing_form_or_one_with_no_sentence_leaves_the_noun_out(self):
        learner = self.learner()
        learner.items["bankanum"].last_outcome = "not_recalled"
        self.assertTrue(learner.is_open("bankanum"))
        self.assertNotIn("banki", {lines[0][0].noun for lines in self.planner(learner).noun_choice_candidates()})
        learner = self.learner({k: v for k, v in WHOLES.items() if k != "bankinn"})
        self.assertNotIn("banki", {lines[0][0].noun for lines in self.planner(learner).noun_choice_candidates()})

    def test_each_sentence_is_heard_with_its_case_then_asked_from_its_meaning(self):
        planner = self.planner(self.learner())
        b = planner.builder
        bank = next(lines for lines in planner.noun_choice_candidates() if lines[0][0].noun == "banki")
        sc = Script(41, "t", "is", "en")
        ex = b.noun_choice(sc, bank)
        self.assertEqual(mode(ex), "form", "the form work's way back follows it (lesson 55)")
        said = [g.text for g in sc.segments if g.exercise == ex.index and g.type in ("speak", "narrate", "answer")]
        self.assertEqual(said[0], "One noun, different forms: its form follows the words around it.")
        joined = " ".join(said)
        for word, case in (("bankinn", "nominative"), ("bankanum", "dative")):
            self.assertIn(word, said)
            self.assertIn(f", in the {case}.", joined)
        self.assertIn("leita að", said, "the frame's reason: «This form comes after «leita að».»")
        answers = [g.text for g in sc.segments if g.exercise == ex.index and g.type == "answer"]
        self.assertEqual(answers, ["Ég er að leita að bankanum.", "Hvar er bankinn?"], "each asked, in another order")
        again = b.noun_choice(sc, bank)
        self.assertEqual(" ".join(g.text for g in sc.segments if g.exercise == again.index and g.text).count("leita að"), 2,
                         "the reason once a lesson per frame: the second time only the sentence and its answer say «leita að»")

    def test_a_lesson_sets_one_noun_choice_once_the_learner_has_one(self):
        sc = self.planner(self.learner()).build()
        self.assertLessEqual(len(sc.meta["noun_choices"]), 1)
        played = [e for e in sc.exercises if e.stage == "noun_choice"]
        self.assertEqual(len(played), len(sc.meta["noun_choices"]))
        none = self.planner(self.learner({})).build()
        self.assertEqual(none.meta["noun_choices"], [], "no noun in two forms with their sentences: no choice")


if __name__ == "__main__":
    unittest.main()
