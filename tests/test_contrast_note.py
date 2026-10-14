"""#198: «heiti potturinn» / «heitur pottur»: a grammar note for the contrast, once both forms are met, outranking the cultural aside."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import load_curriculum, notes_cutting_sentences
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 9, 1)
PAIR = ("heiti_potturinn", "er_heitur_pottur_herna")


def planner(cur, met):
    learner = LearnerState("is", "en", "A1")
    for i in met:
        learner.items[i] = ItemState(stage="meaning", successes=2, recalled=1, due=(TODAY + timedelta(days=2)).isoformat(), last_practiced=TODAY.isoformat())
    learner.lessons_completed = 14
    return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY)


class ContrastNoteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_note_is_data_in_both_languages_and_says_its_sentences_whole(self):
        for lang in ("en", "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            note = cur.note_by_id["definite_weak_adjective"]
            self.assertTrue(note.contrast)
            self.assertEqual(set(note.items), set(PAIR))
            self.assertNotIn(note.id, notes_cutting_sentences(cur), lang)

    def test_it_waits_until_both_forms_are_met(self):
        for met in ((), ("heiti_potturinn",), ("er_heitur_pottur_herna",)):
            pick = planner(self.cur, met)._pick_note(list(PAIR))
            self.assertNotEqual(getattr(pick, "id", None), "definite_weak_adjective", met)

    def test_with_both_met_it_outranks_the_cultural_aside_on_the_same_items(self):
        for seed in range(8):  # the choice among equals is random: the contrast wins every time
            p = planner(self.cur, PAIR)
            p.rng.seed(seed)
            self.assertEqual(p._pick_note(list(PAIR)).id, "definite_weak_adjective")

    def test_once_heard_the_cultural_aside_is_still_available(self):
        p = planner(self.cur, PAIR)
        p.learner.notes_heard["definite_weak_adjective"] = 1
        p.learner.notes_last_heard["definite_weak_adjective"] = p.learner.next_lesson_number()
        self.assertEqual(p._pick_note(list(PAIR)).id, "heiti_potturinn")


if __name__ == "__main__":
    unittest.main()
