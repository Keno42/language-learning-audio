"""#339: a word is caught once (across lessons); some new words are introduced through the catch; pick-outs rotate across lessons."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
IS_EN = Path(__file__).resolve().parent.parent / "curricula" / "is-en"


class CatchOnceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(IS_EN)
        scen = load_cando(IS_EN)
        cls.themes = load_themes(IS_EN, cls.cur, scen)
        cls.order = scenario_order(scen)

    def cfg(self):
        return PlanConfig(minutes=30, new_target=8, themes=self.themes, theme_scenarios=self.order)

    def test_the_learner_state_keeps_the_caught_words_and_the_listening_log(self):
        import tempfile

        l = LearnerState("is", "en", "A1")
        l.caught_words = ["sestu"]
        l.listening_log = {"line|answer": 7}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "l.json"
            l.save(path)
            back = LearnerState.load(path)
            self.assertEqual((back.caught_words, back.listening_log), (["sestu"], {"line|answer": 7}))
            LearnerState("is", "en", "A1").save(path)
            self.assertEqual(LearnerState.load(path).caught_words, [], "an old file reads empty")

    def test_a_course_catches_no_word_twice_and_records_what_it_caught(self):
        l = LearnerState("is", "en", "A1")
        day = TODAY
        seen: list[str] = []
        for n in range(1, 24):
            sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
            m = sc.meta
            self.assertEqual(m["caught_before"], 0, f"lesson {n}")
            seen += m["caught_words"]
            apply_to_learner(sc, l, day)
            l.report([], [], day + timedelta(days=1), lesson_number=n, recalled=m["new_items"])
            day += timedelta(days=1)
        self.assertEqual(len(seen), len(set(seen)), seen)
        self.assertEqual(set(seen), set(l.caught_words))

    def test_a_word_caught_before_is_not_a_catch_word_again(self):
        l = LearnerState("is", "en", "A1")
        day = TODAY
        for n in range(1, 24):
            sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
            apply_to_learner(sc, l, day)
            l.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        l.caught_words = sorted(set(l.caught_words) | {"sestu", "kjötsúpa", "þarftu"})
        sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
        self.assertFalse({"sestu", "kjötsúpa", "þarftu"} & set(sc.meta["caught_words"]))

    def test_a_new_word_that_a_line_holds_as_its_only_unknown_is_introduced_through_the_catch(self):
        l = LearnerState("is", "en", "A1")
        for i in ("hvad_thydir_thetta", "hvad_kostar_thetta"):
            if i in self.cur.by_id:
                l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled", due=(TODAY + timedelta(days=5)).isoformat())
        p = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=TODAY)
        task = p.catch_intro_task(self.cur.by_id["thusund"], {"tvö", "krónur", "takk"}, set())
        self.assertIsNotNone(task)
        self.assertEqual((task.answer.lower(), task.meaning), ("þúsund", self.cur.by_id["thusund"].meaning))
        again = p.catch_intro_task(self.cur.by_id["thusund"], {"tvö", "krónur", "takk"}, {task.line})
        self.assertTrue(again is None or again.line != task.line, "each line once a lesson")
        l.caught_words = ["þúsund"]
        self.assertIsNone(p.catch_intro_task(self.cur.by_id["thusund"], {"tvö", "krónur", "takk"}, set()), "caught once, never again")

    def test_a_hard_to_say_word_keeps_its_plain_introduction_with_the_slow_split_model(self):
        """Review of #344: the slow, split model (#212) lives in the plain introduction; a catch must not take it from «eldfjall» and the like."""
        from unittest import mock

        from audiolesson.sounds import hard_sounds

        asked: list[str] = []
        real = Planner.catch_intro_task

        def spy(self_, item, known, used):
            asked.append(item.id)
            return real(self_, item, known, used)

        l = LearnerState("is", "en", "A1")
        day = TODAY
        with mock.patch.object(Planner, "catch_intro_task", spy):
            for n in range(1, 31):
                sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
                apply_to_learner(sc, l, day)
                l.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
                day += timedelta(days=1)
        self.assertTrue(asked, "the catch was considered for some words")
        self.assertEqual([i for i in asked if hard_sounds(self.cur.by_id[i])], [], "never for a hard-to-say word")


if __name__ == "__main__":
    unittest.main()
