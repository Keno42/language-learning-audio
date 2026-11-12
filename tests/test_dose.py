"""#518 (the owner, 2026-11-12): every new item starts on less practice, and the reviews say which kinds need more. «It cannot be judged before the
lesson is taken and the review tried, so use a feedback loop.» Three doses: light (made of known words, a plain number), middle (the default: two
timed recalls and at most six says), heavy (all four and nine), for an item with a trait whose new items the next-day review found weak."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


class DoseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        cls.long = [i for i in cls.cur.items if i.kind == "phrase" and i.word_count >= 5 and not i.command]

    def planner(self, outcomes: dict[str, str], **cfg):
        """A learner whose items in ``outcomes`` were new in lesson 10 and got that outcome the next day."""
        learner = LearnerState("is", "en", "A1")
        for item_id, outcome in outcomes.items():
            learner.items[item_id] = ItemState(stage="meaning", successes=4, durable_successes=1, recalled=1 if outcome == "recalled" else 0,
                                               last_outcome=outcome, introduced_lesson=10, due=(TODAY + timedelta(days=30)).isoformat(),
                                               history=[{"lesson": 10, "stages": ["intro"], "ok": True, "outcome": outcome}])
        learner.lessons_completed = 20
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, **cfg), today=TODAY)

    def test_a_new_item_is_middle_until_the_reviews_find_its_kind_weak(self):
        new = self.long[-1]
        had = [i.id for i in self.long[:10]]
        fine = self.planner({i: "recalled" for i in had})
        self.assertEqual(fine.dose(new), "middle")
        self.assertEqual(fine.trait_rates()["five words or more"], (0.0, 10))
        weak = self.planner({i: ("not_recalled" if k < 3 else "recalled") for k, i in enumerate(had)})
        self.assertEqual(weak.trait_rates()["five words or more"], (0.3, 10))
        self.assertEqual(weak.dose(new), "heavy", "three of ten failed the next day: sentences of five words get their practice back")
        short = next(i for i in self.cur.items if i.kind == "phrase" and i.word_count == 2 and i.difficulty <= 2 and not i.command and i.id not in had)
        self.assertEqual(weak.dose(short), "middle", "a kind the reviews do not find weak stays on the default")

    def test_a_hesitation_counts_half_and_a_few_samples_decide_nothing(self):
        had = [i.id for i in self.long[:10]]
        half = self.planner({i: ("hesitated" if k < 4 else "recalled") for k, i in enumerate(had)})
        self.assertEqual(half.trait_rates()["five words or more"], (0.2, 10))
        self.assertEqual(half.dose(self.long[-1]), "middle", "at the threshold, not over it")
        few = self.planner({i: "not_recalled" for i in had[:5]})
        self.assertEqual(few.dose(self.long[-1]), "middle", "five samples are under dose_min_samples")

    def test_the_rates_are_read_from_the_latest_items(self):
        had = [i.id for i in self.long[:12]]
        p = self.planner({i: "not_recalled" for i in had}, dose_window=4)
        for k, i in enumerate(had):
            p.learner.items[i].introduced_lesson = 10 + k
            p.learner.items[i].history[0]["lesson"] = 10 + k
            if k >= 8:
                p.learner.items[i].history[0]["outcome"] = "recalled"
        self.assertEqual(p.trait_rates()["five words or more"], (0.0, 4), "the four latest, all recalled")

    def test_an_instruction_a_plain_number_and_a_phrase_of_known_words_are_light(self):
        p = self.planner({})
        self.assertEqual(p.dose(self.cur.by_id["endurtaktu"]), "light")
        self.assertEqual(p.dose(self.cur.by_id["sextan"]), "light")

    def test_a_lesson_says_a_middle_item_less_often(self):
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id["tvaer"].order:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        learner.lessons_completed = 30

        def says(**cfg):
            sc = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, **cfg), today=TODAY).build()
            new = [self.cur.by_id[i] for i in sc.meta["new_items"]]
            out = {}
            for it in new:
                if it.kind == "phrase" and sc.meta["doses"].get(it.id) in ("middle", "heavy"):
                    out[it.id] = sum(1 for g in sc.segments if g.type == "answer" and g.text == it.target)
            return sc, out

        sc, middle = says()
        self.assertTrue(middle, "the lesson teaches a phrase on the default dose")
        self.assertTrue(all(v == "middle" for k, v in sc.meta["doses"].items() if k in middle))
        self.assertIn("trait_rates", sc.meta)
        # review of #529: the description promised both fields in plan.json; ``_plan`` exported neither
        from audiolesson.cli import _plan

        plan = _plan(sc, self.cur)
        self.assertEqual((plan["doses"], plan["trait_rates"]), (sc.meta["doses"], sc.meta["trait_rates"]))
        self.assertTrue(plan["doses"])
        sc2, before = says(dose_ceiling={})  # no ceiling: the old dose
        both = sorted(set(middle) & set(before))
        self.assertTrue(both)
        self.assertLess(sum(middle[i] for i in both), sum(before[i] for i in both), (middle, before))
        # its own recalls stop at six; a play of its scene or its pattern's sentence may say it once more
        self.assertLessEqual(max(middle.values()), 7, middle)


if __name__ == "__main__":
    unittest.main()
