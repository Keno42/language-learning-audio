"""#265, lesson 42 (09:18 in the draft, 06:54 on the lesson-41 replay): «og» was asked alone («How do you say: And.»), as no expression the learner has
holds it. «Takk og bless!», the everyday sign-off, holds it in words the learner knows: once met, a due review of «og» is asked as that line and credited
to «og», in the lesson and in the written review."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.review_wholes import whole_for
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


class OgHomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_written_review_asks_og_through_the_sign_off(self):
        whole = whole_for(self.cur, self.cur.by_id["og"], {"og", "takk", "bless", "takk_og_bless"}, Prompts.load("en"))
        self.assertEqual(whole["answer"], "Takk og bless!")
        self.assertIsNone(whole_for(self.cur, self.cur.by_id["og"], {"og", "takk", "bless"}, Prompts.load("en")), "before it, no sentence holds «og»")

    def test_a_due_review_of_og_is_the_sign_off_not_the_bare_word(self):
        l = LearnerState("is", "en", "A1")
        for i in ("takk", "bless", "takk_og_bless", "og"):
            due = TODAY if i == "og" else TODAY + timedelta(days=30)
            l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=10, last_outcome="recalled",
                                   due=due.isoformat(), last_practiced=(TODAY - timedelta(days=10)).isoformat())
        l.lessons_completed = 20
        sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY).build()
        asked = [e for e in sc.exercises if "og" in (e.item_ids or []) and e.kind in ("recall", "generative")]
        self.assertTrue(asked, "the due review is kept")
        self.assertTrue(all("Takk og bless!" in e.label for e in asked), [e.label for e in asked])


if __name__ == "__main__":
    unittest.main()
