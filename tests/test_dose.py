"""#518 (the owner, 2026-11-12): every new item starts on less practice, and the reviews say which kinds need more. «It cannot be judged before the
lesson is taken and the review tried, so use a feedback loop.» Three doses: light (an instruction, a plain number, a phrase made of known words: one
timed recall), middle (the default: the timed recalls, the hinted one given to the due reviews when they cannot fit, #478) and heavy (every recall,
whatever the reviews), for an item with a trait whose new items the next-day review found weak."""
import re
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

    def lesson(self, weak: bool):
        """A lesson for a learner who knows the course up to «tvær», every item due today: more reviews than a lesson holds. ``weak``: ten of
        their sentences of five words or more were not recalled the day after the lesson that taught them."""
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id["tvaer"].order:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=TODAY.isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        if weak:
            for i in [i for i in self.long if i.id in learner.items][:10]:
                learner.items[i.id].introduced_lesson = 20
                learner.items[i.id].history = [{"lesson": 20, "stages": ["intro"], "ok": True, "outcome": "not_recalled"}]
        learner.lessons_completed = 30
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY).build()

    @staticmethod
    def recalls(sc, item_id: str) -> list[str]:
        """The stages of the item's own recalls, in the lesson's order."""
        return [e.stage for e in sc.exercises if e.kind == "recall" and e.item_ids[:1] == [item_id]]

    @staticmethod
    def rungs(sc, item_id: str) -> list[str]:
        """``recalls``, with a recall from the meaning that the scene check's line cues read as ``meaning``: ``Builder.sentence_cue`` and
        ``_recall_construction`` label it «situation» when the sentence they pick has a scene line («Ég elska súpu.»; «Ég elska ís.» has none),
        but its cue is the scene line and the meaning (``scene_say``), never the item's own situation. A recall from the item's own situation
        stays «situation»."""
        template = Prompts.load("en").data["scene_say"]
        cued = re.compile(".*".join(re.escape(p) for p in re.split(r"\{[^}]*\}", template)))
        def rung(e) -> str:
            said = [g.text or "" for g in sc.segments if g.exercise == e.index and g.type == "narrate"]
            return "meaning" if e.stage == "situation" and any(cued.search(t) for t in said) else e.stage
        return [rung(e) for e in sc.exercises if e.kind == "recall" and e.item_ids[:1] == [item_id]]

    def hinted(self, sc, item_id: str) -> bool:
        """Whether a sentence's recall at about three minutes was asked: the rung a lesson gives to reviews that cannot fit (a sentence's
        ladder goes cloze, hinted, meaning)."""
        return "hinted" in self.recalls(sc, item_id)

    def test_a_heavy_item_keeps_the_recall_a_full_lesson_takes_from_the_others(self):
        """Lessons 46, 53 and 56-58 could not fit their due reviews, and every new item gave them its hinted recall (#478), a kind that fails
        the next day as much as one that does not. The loop gives it back to the kind the reviews find weak."""
        fine, weak = self.lesson(weak=False), self.lesson(weak=True)
        self.assertTrue(fine.meta["reviews_starved"] and weak.meta["reviews_starved"])
        # the same choice of new material, but for the dose: what was chosen and not taught for lack of time («not_introduced») counts as
        # chosen, since a second more or less in a lesson (lesson 62's opening line of a contrast) decides whether the last item fits
        chosen = lambda sc: set(sc.meta["new_items"]) | set(sc.meta.get("not_introduced", []))
        self.assertEqual(chosen(fine), chosen(weak), "the same lesson, but for the dose")
        long_new = [i for i in weak.meta["new_items"] if self.cur.by_id[i].kind == "phrase" and self.cur.by_id[i].word_count >= 5 and weak.meta["doses"][i] != "light"]
        self.assertTrue(long_new, "the lesson teaches a sentence of five words or more")
        self.assertEqual(weak.meta["trait_rates"]["five words or more"], [1.0, 10])
        for i in long_new:
            self.assertEqual((fine.meta["doses"][i], self.hinted(fine, i)), ("middle", False), i)
            self.assertEqual((weak.meta["doses"][i], self.hinted(weak, i)), ("heavy", True), i)
        others = [i for i, d in weak.meta["doses"].items() if d == "middle" and i in fine.meta["new_items"] and i in weak.meta["new_items"]]
        self.assertTrue(others, "a kind the reviews do not find weak stays on the default")
        for i in others:
            self.assertEqual(self.rungs(weak, i), self.rungs(fine, i), f"{i}: and is asked as in the other lesson, its recall given to the reviews")

    def test_plan_json_holds_the_doses_and_the_trait_rates(self):
        """Review of #529: the description promised both fields in plan.json; ``_plan`` exported neither."""
        from audiolesson.cli import _plan

        sc = self.lesson(weak=True)
        plan = _plan(sc, self.cur)
        self.assertEqual((plan["doses"], plan["trait_rates"]), (sc.meta["doses"], sc.meta["trait_rates"]))
        self.assertEqual(set(plan["doses"].values()), {"light", "middle", "heavy"} & set(plan["doses"].values()))
        self.assertTrue(set(plan["doses"]) <= set(sc.meta["new_items"]))
        self.assertIn("heavy", plan["doses"].values())


if __name__ == "__main__":
    unittest.main()
