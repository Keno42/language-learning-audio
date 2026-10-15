"""#337: a phrase's hard words are modelled slowly and split at its introduction; a word reported hard gets the model again before its next practice."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import CurriculumError, curriculum_from_dict, load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.sounds import hard_words_of
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


class HardWordAgainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def builder(self):
        return Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))

    def test_the_words_of_the_learners_remark_have_authored_syllables(self):
        got = {i: hard_words_of(self.cur.by_id[i]) for i in ("vegurinn_er_lokadur", "get_eg_fengid_reikninginn", "er_vegurinn_opinn", "reikninginn")}
        self.assertEqual(got["vegurinn_er_lokadur"], [("vegurinn", ["veg", "ur", "inn"]), ("lokaður", ["lok", "að", "ur"])])
        self.assertEqual(got["get_eg_fengid_reikninginn"], [("reikninginn", ["reik", "ning", "inn"])])
        self.assertEqual(got["reikninginn"], [("reikninginn", ["reik", "ning", "inn"])])

    def test_a_phrase_names_its_hard_words_and_the_introduction_models_them_after_the_phrase(self):
        b = self.builder()
        sc = Script(1, "t", "is", "en")
        b.intro(sc, self.cur.by_id["vegurinn_er_lokadur"])
        slow = [g.text for g in sc.segments if g.type == "speak" and g.rate < 1]
        self.assertTrue({"veg", "inn", "lok", "að"} <= set(slow))
        said = [g.text for g in sc.segments if g.type == "speak" and g.rate == 1.0]
        self.assertIn("vegurinn", said)
        self.assertIn("lokaður", said)

    def test_a_phrase_with_nothing_authored_is_introduced_as_before(self):
        b = self.builder()
        sc = Script(1, "t", "is", "en")
        b.intro(sc, self.cur.by_id["er_thetta_saeti_laust"])
        self.assertNotIn("in parts", sc.transcript())

    def test_a_reported_item_without_authored_syllables_takes_the_word_with_most_hard_sounds(self):
        item = self.cur.by_id["er_thetta_saeti_laust"]
        self.assertEqual(hard_words_of(item), [], "not reported, nothing authored: no hard word")
        self.assertEqual(hard_words_of(item, reported=True), [("þetta", None)], "reported: «þetta» holds the old «tt» rule")

    def test_the_slow_exercise_says_the_phrase_then_its_words_in_pieces(self):
        b = self.builder()
        sc = Script(1, "t", "is", "en")
        ex = b.slow_word_exercise(sc, self.cur.by_id["get_eg_fengid_reikninginn"])
        self.assertEqual((ex.kind, ex.stage), ("model", "slow"))
        slow = [g.text for g in sc.segments if g.type == "speak" and g.rate < 1]
        self.assertEqual(slow, ["reik", "ning", "inn"])
        plain = next(i for i in self.cur.items if i.kind == "phrase" and not hard_words_of(i, reported=True))
        self.assertIsNone(b.slow_word_exercise(sc, plain), "nothing to model")

    def test_a_phrase_reported_hard_gets_the_model_once_before_its_first_practice(self):
        l = LearnerState("is", "en", "A1")
        for i in ("vegurinn_er_lokadur", "er_vegurinn_opinn"):
            l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=3, last_outcome="recalled",
                                   due=TODAY.isoformat(), last_practiced=(TODAY - timedelta(days=3)).isoformat())
        l.report([], [], TODAY, sooner=["vegurinn_er_lokadur"])
        l.lessons_completed = 20
        sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY).build()
        self.assertEqual(sc.meta["slow_models_reported"], ["vegurinn_er_lokadur"])
        models = [e for e in sc.exercises if e.kind == "model" and e.stage == "slow"]
        self.assertEqual(len(models), 1)
        first = min((e.start for e in sc.exercises if "vegurinn_er_lokadur" in e.item_ids and e.kind in ("recall", "generative", "connect")), default=None)
        if first is not None:
            self.assertLessEqual(models[0].start, first)

    def test_word_syllables_are_checked(self):
        base = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}}
        def make(extra):
            return curriculum_from_dict({**base, "items": [{"id": "a", "kind": "phrase", "target": "Vegurinn er lokaður.", "meaning": "The road is closed.", **extra}]})
        make({"word_syllables": {"vegurinn": ["veg", "ur", "inn"]}})
        for bad in ({"vegurinn": ["veg", "urinn", "x"]}, {"vegurinn": ["vegurinn"]}, {"nope": ["no", "pe"]}):
            with self.assertRaises(CurriculumError, msg=str(bad)):
                make({"word_syllables": bad})


if __name__ == "__main__":
    unittest.main()
