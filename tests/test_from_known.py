"""Lesson 51 (the owner: «fimm þúsund krónur / tíu… が新出フレーズ扱いになるのは違和感がある»): two prices whose every word the learner had were announced
«Something new.» and «A new expression.» and asked four times each. A plain number made only of known words is asked as a use of them, the model after it,
and once more later; the closing, which goes back over what was new, leaves it out."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


class FromKnownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_it_is_asked_as_a_use_of_known_words_not_named_new(self):
        item = self.cur.by_id["tvo_thusund_kronur"]
        for lang, frame in (("en", "Made of words you know."), ("ja", "知っている言葉だけでできています。")):
            b = Builder(self.cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
            b.plain.add(item.id)
            b.from_known.add(item.id)
            sc = Script(1, "t", "is", lang)
            ex = b.intro(sc, item)
            self.assertEqual(ex.kind, "intro")
            narrated = [g.text for g in sc.segments if g.type == "narrate"]
            self.assertEqual(narrated[0], frame)
            self.assertFalse(any(t.startswith(("Something new", "A new expression", "新しい表現")) for t in narrated), narrated)
            self.assertEqual([g.type for g in sc.segments if g.type in ("speak", "answer")], ["answer"], "asked first, the model after it, nothing before")

    def test_a_lesson_asks_it_twice_and_the_closing_leaves_it_out(self):
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id["tvo_thusund_kronur"].order and i.id != "fimmtan_hundrud_kronur":
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        learner.lessons_completed = 30
        sc = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1, priority=["tvo_thusund_kronur"]), today=TODAY).build()
        intro = next((e for e in sc.exercises if e.kind == "intro" and "tvo_thusund_kronur" in e.item_ids), None)
        self.assertIsNotNone(intro, "the price asked for by name comes in")
        self.assertTrue(intro.label.startswith("from known words"), intro.label)
        self.assertLessEqual(len(sc.meta["exposures"]["tvo_thusund_kronur"]), 2, sc.meta["exposures"]["tvo_thusund_kronur"])

    def test_a_number_with_a_new_word_is_introduced_as_before(self):
        learner = LearnerState("is", "en", "A1")
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), learner)
        b.plain.add("sextan")
        sc = Script(1, "t", "is", "en")
        b.intro(sc, self.cur.by_id["sextan"])
        self.assertTrue(sc.segments[0].text.startswith("Something new"))


if __name__ == "__main__":
    unittest.main()
