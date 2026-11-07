"""#439 step 1a (lesson 49): «sextán», «tvö þúsund krónur» and «þrjú þúsund krónur» were introduced as words, with a slow word-by-word model, four timed
recalls and «use it in another sentence». The owner: a plain number needs no word's practice; the forms of 1–4, which change with the noun, need more
(step 1b). A plain number is now introduced plainly (heard, repeated once, said once), asked once more after a gap, and never moved to new sentences."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.numbers import plain_number
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent
PRICES = ("tvo_thusund_kronur", "fimmtan_hundrud_kronur")


class PlainNumberTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_a_plain_number_is_one_whose_form_never_changes(self):
        for i in ("sextan", "fimmtiu", "tvo_thusund_kronur", "fimm_hundrud_kronur", "tuttugu_og_fimm", "hundrad"):
            self.assertTrue(plain_number(self.cur.by_id[i], self.cur), i)
        # the forms of 1–4: a gender of its own, a form of another, the base of a form, or one of the words by name; and anything that is no number
        for i in ("einn", "tveir", "fjorir", "eitt", "tvo", "tvaer", "fjorar", "thusund", "ein", "dyrt"):
            self.assertFalse(plain_number(self.cur.by_id[i], self.cur), i)

    def test_a_plain_number_is_not_moved_to_new_sentences(self):
        p = Planner(self.cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY)
        for i in ("sextan", "fimmtiu", "tvo_thusund_kronur"):
            self.assertNotIn("recombine", p.ladder(self.cur.by_id[i]), i)
        self.assertIn("recombine", p.ladder(self.cur.by_id["tvo"]), "«tvö», a form of 1–4, keeps its ladder (step 1b practises it)")

    def test_the_introduction_has_no_slow_model(self):
        item = self.cur.by_id["tvo_thusund_kronur"]
        for plain in (False, True):
            b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
            if plain:
                b.plain.add(item.id)
            sc = Script(1, "t", "is", "en")
            b.intro(sc, item)
            self.assertEqual("Slowly." in sc.transcript(), not plain, f"plain={plain}")
            if plain:
                self.assertEqual([g.type for g in sc.segments if g.type in ("speak", "answer")], ["speak", "speak", "answer"], "heard, repeated once, said once")

    def test_a_lesson_introduces_a_price_plainly_and_asks_it_once_more(self):
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id["tvo_thusund_kronur"].order and i.id != "fimmtan_hundrud_kronur":
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        learner.lessons_completed = 30
        sc = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1, topics=["money"]), today=TODAY).build()
        exposures = sc.meta["exposures"]
        introduced = [i for i in PRICES if i in exposures]
        self.assertTrue(introduced, "the money topic brings a price in")
        for i in introduced:
            self.assertEqual(exposures[i][0], "intro")
            self.assertNotIn("recombine", exposures[i], i)
            self.assertLessEqual(len(exposures[i]), 3, f"{i}: the introduction, one timed recall and the closing's ({exposures[i]})")
            intro = next(e for e in sc.exercises if e.kind == "intro" and i in e.item_ids)
            self.assertFalse(any(g.text == "Slowly." for g in sc.segments if g.exercise == intro.index), i)

    def test_an_age_number_is_never_asked_in_a_new_sentence_later_in_the_lesson(self):
        """Review of #492 on lesson 49's replay: «sextán» was asked again in the second half as «It costs sixteen thousand krónur.» and «Are you
        sixteen years old?», through the second half's practice of today's items and a sentence practice that asked for a recombination directly."""
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id["sextan"].order:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        learner.lessons_completed = 30
        for seed in (1, 2, 3):
            sc = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=seed), today=TODAY).build()
            stages = sc.meta["exposures"].get("sextan")
            self.assertTrue(stages, "the course order brings «sextán» in")
            self.assertEqual(stages, ["intro", "meaning", "meaning"], f"seed {seed}: the introduction, one timed recall and the closing's")
            self.assertFalse([e.label for e in sc.exercises if e.kind == "generative" and "sextan" in e.item_ids], f"seed {seed}")
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), learner)
        self.assertEqual(b.recombine_status(self.cur.by_id["sextan"]), "impossible", "no path moves a plain number to a new sentence")


if __name__ == "__main__":
    unittest.main()
