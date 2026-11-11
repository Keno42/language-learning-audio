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

    def planner(self, *known, **changes):
        learner = LearnerState("is", "en", "A1")
        for i in known:
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                         due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        for i, change in changes.items():
            for k, v in change.items():
                setattr(learner.items[i], k, v)
        learner.lessons_completed = 30
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)

    def test_a_phrase_made_of_words_the_learner_says_is_a_use_of_them(self):
        """Lesson 54 («大人2枚、子供2枚の練習が厚すぎる»): «Tvo fullorðna og tvö börn, takk.», after «Tvo fullorðna, takk.», «Ég á tvö börn.» and «Kaffi
        og kaka», was introduced as new, built up from its end and said nine times (#518)."""
        ticket = self.cur.by_id["tvo_fullordna_og_tvo_born_takk"]
        had = [i.id for i in self.cur.items if i.order < ticket.order and i.kind in ("phrase", "vocab")]
        self.assertTrue(self.planner(*had).made_of_known_words(ticket))
        words = lambda i: {w.lower() for w in __import__("re").findall(r"[^\W\d_]+", self.cur.by_id[i].target)}
        without = [i for i in had if "börn" not in words(i)]
        self.assertFalse(self.planner(*without).made_of_known_words(ticket), "«börn» never met: the phrase is new")
        holder = next(i for i in had if "börn" in words(i))
        only = [i for i in had if "börn" not in words(i)] + [holder]
        self.assertTrue(self.planner(*only).made_of_known_words(ticket))
        failing = self.planner(*only, **{holder: {"last_outcome": "not_recalled", "recalled": 0}})
        if failing.learner.is_open(holder):
            self.assertFalse(failing.made_of_known_words(ticket), "a word only a failing item holds is not one the learner says")

    def test_an_instruction_keeps_its_own_path(self):
        everything = [i.id for i in self.cur.items if i.kind in ("phrase", "vocab", "construction")]
        self.assertFalse(self.planner(*everything).made_of_known_words(self.cur.by_id["endurtaktu"]))

    def test_a_number_with_a_new_word_is_introduced_as_before(self):
        learner = LearnerState("is", "en", "A1")
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), learner)
        b.plain.add("sextan")
        sc = Script(1, "t", "is", "en")
        b.intro(sc, self.cur.by_id["sextan"])
        self.assertTrue(sc.segments[0].text.startswith("Something new"))


if __name__ == "__main__":
    unittest.main()
