"""#451 step 2d, review of #512: «mínus» and «gráður» were drilled bare (lesson 55 on the replay: «mínus» at 0:12, «gráður» at 3:31, the sentence at
4:20, both asked alone again in the closing). §9 "Parts against utterances": a part is introduced inside the expression that holds it. The
temperature is a whole sentence the learner says first («Það eru mínus þrjár gráður.»); the pattern of other temperatures comes after it."""
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


class TemperatureWholeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "curricula" / "is-en"
        cls.cur = load_curriculum(path)
        scenarios = load_cando(path, cls.cur)
        cls.themes = [t for t in load_themes(path, cls.cur, scenarios) if t.id == "weather"]
        cls.order = scenario_order(scenarios)

    def test_the_pattern_comes_after_the_sentence_and_no_word_stands_alone(self):
        pattern = self.cur.by_id["thad_eru_minus_count_gradur"]
        self.assertEqual(pattern.prereqs, [SENTENCE], "the pattern is derived from the sentence the learner says")
        self.assertEqual(self.cur.by_id[SENTENCE].instance_of, pattern.id)
        self.assertNotIn("minus", self.cur.by_id, "«mínus» has no item of its own: it is a word of the sentence")
        level = self.themes[0].levels[1]
        said = next(t for t in level.turns if t.who == "you" and "gráður" in t.say)
        self.assertEqual(said.items, [SENTENCE], "the scene asks the whole sentence")

    def test_a_lesson_introduces_the_sentence_whole_and_never_asks_its_words_alone(self):
        learner = LearnerState("is", "en", "A1")
        stop = self.cur.by_id[SENTENCE].order
        for it in self.cur.items:
            if it.order < stop and it.id not in ("gradur", "thad_eru_minus_count_gradur"):
                learner.items[it.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                 due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        learner.lessons_completed = 40
        learner.themes_done = {"weather": 1}
        cfg = PlanConfig(minutes=30, seed=1, new_target=8, themes=self.themes, theme_scenarios=self.order)
        sc = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        labels = [e.label for e in sc.exercises]
        self.assertIn("new: Það eru mínus þrjár gráður.", labels, labels)
        bare = [e.label for e in sc.exercises if e.label.split(": ", 1)[-1].split(" (")[0].strip(".").lower() in ("mínus", "gráður")]
        self.assertEqual(bare, [], "neither word is introduced or asked alone, the closing included")
        asked = {g.text.strip(".").lower() for g in sc.segments if g.type == "answer"}
        self.assertFalse(asked & {"mínus", "gráður"}, "no answer is a bare word of the sentence")


if __name__ == "__main__":
    unittest.main()
