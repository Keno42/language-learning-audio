"""#444 (lesson 42, 02:59): the learner reported «lögreglustöðin» hard to *hear*, and the lesson said «This word is hard to say.» and played the slow
pronunciation model. The reason of a «sooner» report now reaches the learner state: ``hear`` owes listening support (the word heard, found in a sentence the
learner has, the sentence once more), ``say`` the slow model of #337; without reasons (an older bot, the CLI alone) every «sooner» owes the slow model, as before."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent
WORD = "logreglustodin"  # «lögreglustöðin», one word: found in «Hvar er lögreglustöðin?»
LINE = "vegurinn_er_lokadur"  # a line of three words


class HearSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def learner(self, reasons):
        l = LearnerState("is", "en", "A1")
        for i in ("hvar_er_place", WORD, LINE, "er_vegurinn_opinn"):
            if i in self.cur.by_id:
                l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                       due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=1)).isoformat())
        extra = {} if reasons is None else {"sooner_reasons": reasons}
        l.report([], [], TODAY - timedelta(days=1), sooner=[WORD, LINE], **extra)
        l.lessons_completed = 20
        return l

    def test_the_reason_decides_what_is_owed(self):
        for reasons, slow, hear in ((None, True, False), (["say"], True, False), (["hear"], False, True), (["say", "hear"], True, True), (["scene"], False, False)):
            st = self.learner(reasons).items[WORD]
            self.assertEqual((bool(st.slow_owed), bool(st.hear_owed)), (slow, hear), reasons)
            self.assertTrue(st.reported_hard, "every «sooner» is still a report that it is hard (#326)")
        with self.assertRaises(ValueError):
            LearnerState("is", "en", "A1").report([], [], TODAY, sooner=[WORD], sooner_reasons=["loud"])

    def test_a_word_hard_to_hear_is_heard_found_in_a_sentence_and_heard_again(self):
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        ex = b.hear_support_exercise(sc, self.cur.by_id[WORD], "Hvar er lögreglustöðin?")
        self.assertEqual((ex.kind, ex.stage), ("model", "hear"))
        text = sc.transcript()
        self.assertNotIn("hard to say", text)
        self.assertIn("hard to catch", text)
        spoken = [(g.type, g.text) for g in sc.segments if g.type in ("speak", "answer")]
        self.assertEqual(spoken, [("speak", "lögreglustöðin"), ("speak", "Hvar er lögreglustöðin?"), ("answer", "lögreglustöðin"), ("speak", "Hvar er lögreglustöðin?")])

    def test_a_line_hard_to_hear_is_heard_then_word_by_word_then_at_natural_speed(self):
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        b.hear_support_exercise(sc, self.cur.by_id[LINE], None)
        self.assertFalse([g for g in sc.segments if g.type == "answer"], "listening only: nothing for the learner to say")
        self.assertGreaterEqual(sum(g.text == self.cur.by_id[LINE].target for g in sc.segments if g.type == "speak"), 2)

    def test_the_next_lesson_listens_instead_of_modelling_and_the_debt_is_cleared(self):
        l = self.learner(["hear"])
        sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY).build()
        self.assertEqual(sorted(sc.meta["hear_supports_reported"]), sorted([WORD, LINE]))
        self.assertEqual(sc.meta["slow_models_reported"], [])
        self.assertEqual(len([e for e in sc.exercises if e.kind == "model" and e.stage == "hear"]), 2)
        self.assertNotIn("hard to say", sc.transcript())
        from audiolesson.cli import _plan

        self.assertEqual(sorted(_plan(sc, self.cur)["hear_supports_reported"]), sorted([WORD, LINE]), "review of #447: plan.json lists them too")
        self.assertEqual(_plan(sc, self.cur)["slow_models_reported"], [])
        apply_to_learner(sc, l, TODAY)
        self.assertEqual((l.items[WORD].hear_owed, l.items[LINE].hear_owed), ("", ""))

    def test_the_cli_passes_the_reasons(self):
        import tempfile

        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "learner.json"
            l = LearnerState("is", "en", "A1")
            l.items[WORD] = ItemState(stage="meaning", interval_days=10, due=(TODAY + timedelta(days=10)).isoformat())
            l.save(path)
            self.assertEqual(main(["report", "-l", str(path), "--sooner", WORD, "--sooner-reasons", "hear", "--date", TODAY.isoformat()]), 0)
            st = LearnerState.load(path).items[WORD]
            self.assertEqual((st.hear_owed, st.slow_owed), (TODAY.isoformat(), ""))

    def test_without_reasons_the_slow_model_as_before(self):
        sc = Planner(self.cur, self.learner(None), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY).build()
        self.assertEqual(sc.meta["hear_supports_reported"], [])
        self.assertIn(LINE, sc.meta["slow_models_reported"])


if __name__ == "__main__":
    unittest.main()
