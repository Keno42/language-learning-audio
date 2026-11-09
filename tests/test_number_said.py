"""#451 step 3b (the owner after lesson 52: «mínus þrjár gráður» far too often, always three). The sentence was said nine times in the lesson that
taught it, every time with «þrjár»: its value was fixed in a line the learner says, and its pattern, which would vary it, came only once the sentence
was known. A fixed phrase whose one filler is a number is taught whole (§9 "Parts against utterances"); after its introduction, cloze and hint, its
recalls ask its pattern's sentence with the number the learner has said least. A phrase with no number keeps its own recalls."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent
SENTENCE = "thad_eru_minus_thrjar_gradur"


class NumberSaidTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "curricula" / "is-en"
        cls.cur = load_curriculum(path)
        scenarios = load_cando(path, cls.cur)
        cls.themes = [t for t in load_themes(path, cls.cur, scenarios) if t.id == "weather"]
        cls.order = scenario_order(scenarios)

    def lesson(self):
        """A learner who knows everything before the sentence in the course (the numbers 5–12 among it) and whose next scene is weather 2."""
        learner = LearnerState("is", "en", "A1")
        stop = self.cur.by_id[SENTENCE].order
        for it in self.cur.items:
            if it.order < stop and it.id not in ("gradur", "thad_eru_minus_count_gradur"):
                learner.items[it.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                 due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        learner.lessons_completed = 40
        learner.themes_done = {"weather": 1}
        cfg = PlanConfig(minutes=30, seed=1, new_target=8, themes=self.themes, theme_scenarios=self.order)
        planner = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)
        return planner, planner.build()

    def test_a_number_sentence_is_practised_over_its_patterns_values(self):
        """The sentence's recall after its lesson (here: in it, once the lesson is built) asks another temperature, from its meaning, and records the practice
        as the sentence's. On the replay of the lesson-52 export the pattern is not taught yet when the sentence is, so every recall took this path."""
        planner, sc = self.lesson()
        item = self.cur.by_id[SENTENCE]
        said = []
        for _ in range(4):
            ex = planner.builder.recall(sc, item, "situation")
            said.append(ex.label)
            self.assertEqual(ex.item_ids[0], SENTENCE, "the practice is the sentence's")
            self.assertNotIn("thad_eru_minus_count_gradur", ex.item_ids, "the pattern is not met through it")
        self.assertTrue(all("gráður" in s and "þrjár" not in s for s in said), said)
        self.assertEqual(len(set(said)), len(said), f"each time another number: {said}")
        cloze = planner.builder.recall(sc, item, "cloze")
        self.assertIn("þrjár", cloze.label, "the cloze and the hint keep the sentence as taught")

    def test_only_a_phrase_whose_filler_is_a_number_takes_its_patterns_values(self):
        planner, _ = self.lesson()
        b = planner.builder
        self.assertEqual(b.number_pattern(self.cur.by_id[SENTENCE]).id, "thad_eru_minus_count_gradur")
        for it in self.cur.items:
            if it.kind == "phrase" and it.instance_of and it.id != SENTENCE and b.number_pattern(it) is not None:
                fill = self.cur.by_id[next(iter(it.instance_fill.values()))]
                self.assertTrue(fill.tags or fill.target.split()[0].lower() in ("einn", "tvo", "þrjá"), (it.id, fill.id))
        self.assertIsNone(b.number_pattern(self.cur.by_id["eg_er_med_bokun"]), "a phrase with no number")


if __name__ == "__main__":
    unittest.main()
