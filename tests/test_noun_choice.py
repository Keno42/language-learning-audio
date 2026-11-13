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
STALE = {"hotelinu": {"through": "hvernig_kemst_eg_ad", "answer": "Hvernig kemst ég að hótelinu?", "meaning": "How do I get to the hotel?"}}


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

    def learner(self, stop="eg_er_ad_leita_ad", wholes=None) -> LearnerState:
        """A learner who knows the course up to ``stop`` (the bank and the hotel in two forms among it), with the stored sentences ``wholes``."""
        learner = LearnerState("is", "en", "A1")
        upto = self.cur.by_id[stop].order
        for it in self.cur.items:
            if it.order <= upto:
                learner.items[it.id] = known()
        learner.learned_wholes = {k: dict(v) for k, v in (wholes or {}).items()}
        learner.lessons_completed = 40
        return learner

    def nouns(self, learner) -> dict:
        return {lines[0][0].noun: lines for lines in self.planner(learner).noun_choice_candidates()}

    def test_a_noun_met_in_two_forms_is_a_choice_in_sentences_the_learner_knows(self):
        bank = self.nouns(self.learner())["banki"]
        self.assertEqual([(it.id, case) for it, case, *_ in bank], [("bankinn", "nom"), ("bankanum", "dat")], "the nominative first")
        self.assertEqual([sentence for _, _, sentence, _, _ in bank], ["Hvar er bankinn?", "Ég er að leita að bankanum."])
        self.assertEqual(bank[1][4].id, "eg_er_ad_leita_ad", "the frame that holds the form")
        self.assertEqual(bank[1][3], "How do you say: I'm looking for the bank.", "asked from its meaning, as the written review asks it")

    def test_a_stored_sentence_a_correction_replaced_does_not_come_back(self):
        """Review of #539: lesson 58 of the lesson-55 replay taught «Hvernig kemst ég að hótelinu?» again, a sentence #533 corrected
        («Hvernig kemst ég {dest}?»), because the rule copied ``learned_wholes``. The sentence is read from the current curriculum."""
        hotel = self.nouns(self.learner(wholes=STALE))["hotel"]
        said = [sentence for _, _, sentence, _, _ in hotel]
        self.assertNotIn(STALE["hotelinu"]["answer"], said)
        self.assertEqual(said, ["Hvar er hótelið?", "Ég er að leita að hótelinu."])

    def test_a_failing_form_or_one_no_known_sentence_holds_leaves_the_noun_out(self):
        learner = self.learner()
        learner.items["bankanum"].last_outcome = "not_recalled"
        self.assertTrue(learner.is_open("bankanum"))
        self.assertNotIn("banki", self.nouns(learner))
        learner = self.learner()
        for it in self.cur.items:  # every frame that would hold «bankanum»
            if it.id != "bankanum" and (any(t == "dat_place" for t in it.slots.values()) or "bankanum" in it.target):
                learner.items.pop(it.id, None)
        self.assertNotIn("banki", self.nouns(learner))

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

    def test_the_next_form_the_choice_could_set_comes_in_as_new_material(self):
        """#528 step 4: on the replay of lesson 55's export the noun choice had three nouns and nothing brought a fourth, since a close variant
        waits for a scene or a frame to pull it (#218 b1). A form not met, of another case than the forms the learner has of its noun, that a
        known pattern takes, is wanted: one a lesson, the earliest in the course, and the day's new items hold it."""
        learner = self.learner()
        places = ["flugvellinum", "sundlauginni", "safninu", "stoppistodinni"]
        for item_id in places:
            del learner.items[item_id]
        planner = self.planner(learner)
        self.assertEqual(planner.noun_choice_wants(), ["flugvellinum"], "the earliest in the course, one a lesson")
        self.assertNotIn("flugvellinum", [i.id for i in planner.select_new(6)], "the selection is as before: the form takes no item's place")
        self.assertIn("flugvellinum", planner.build().meta["new_items"], "the lesson adds it to its first batch of new items")
        learner.items["flugvollurinn"].last_outcome = "not_recalled"
        self.assertEqual(self.planner(learner).noun_choice_wants(), ["sundlauginni"], "a noun whose known form is failing gets no second form yet")
        learner.items.pop("eg_er_ad_leita_ad")
        self.assertNotIn(self.planner(learner).noun_choice_wants(), [[p] for p in places], "no known frame takes the dative: nothing to set it in")
        wanted = self.planner(self.learner(stop="eg_aetla_ad_fa")).noun_choice_wants()
        self.assertNotIn("kaffid", wanted, "«kaffið» beside «kaffi» is the same case: no choice of a case")

    def test_a_lesson_sets_one_noun_choice_once_the_learner_has_one(self):
        sc = self.planner(self.learner()).build()
        self.assertLessEqual(len(sc.meta["noun_choices"]), 1)
        played = [e for e in sc.exercises if e.stage == "noun_choice"]
        self.assertEqual(len(played), len(sc.meta["noun_choices"]))
        self.assertEqual(len(played), 1, "this learner has nouns in two forms, and the lesson a today's-items turn for one")
        from audiolesson.cli import _plan

        self.assertEqual(_plan(sc, self.cur)["noun_choices"], sc.meta["noun_choices"], "review of #539: plan.json keeps it")
        none = self.planner(self.learner(stop="takk")).build()
        self.assertEqual(none.meta["noun_choices"], [], "no noun in two forms with their sentences: no choice")


if __name__ == "__main__":
    unittest.main()
