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


class SpokenNoteTests(unittest.TestCase):
    """The review of #323: the pieces are spoken, a lone «.» is not narrated, and the wording survives TTS."""

    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def script(self, note):
        from audiolesson.exercises import Builder
        from audiolesson.script import Script

        prompts = Prompts.load("en")
        sc = Script(1, "Lesson 1", self.cur.target_lang, self.cur.known_lang)
        Builder(self.cur, prompts, Timing(level="A1"), LearnerState("is", "en", "A1")).note(sc, note)
        return sc, prompts

    def test_the_endings_are_said_piece_by_piece_slowly(self):
        sc, prompts = self.script(self.cur.note_by_id["definite_weak_adjective"])
        i = next(k for k, s in enumerate(sc.segments) if s.text == prompts.get("note_pieces"))
        spoken = [s for s in sc.segments[i:] if s.type == "speak"]
        self.assertEqual([s.text for s in spoken], ["ur", "pottur", "inn", "urinn", "potturinn", "heitur", "heiti"])
        self.assertTrue(all(s.rate < 1.0 for s in spoken), "slowly and carefully")
        idx = [k for k, s in enumerate(sc.segments) if s.type == "speak" and s.text in ("ur", "pottur", "inn", "urinn", "potturinn", "heitur", "heiti")]
        self.assertTrue(all(sc.segments[k + 1].type == "pause" for k in idx[:-1]), "a gap after each piece")

    def test_no_lone_full_stop_is_narrated_in_any_note(self):
        for note in self.cur.notes:
            sc, _ = self.script(note)
            lone = [s.text for s in sc.segments if s.type == "narrate" and s.text and not any(ch.isalnum() for ch in s.text)]
            self.assertEqual(lone, [], note.id)

    def test_the_fragment_that_ends_a_sentence_leaves_a_beat_not_a_narration(self):
        from audiolesson.content import Note

        sc, _ = self.script(Note(id="n", text="Start from «pottur». With the ending, it is «potturinn». Done.", items=[]))
        self.assertNotIn(".", [s.text for s in sc.segments if s.type == "narrate"])

    def test_the_note_names_no_word_in_quotation_marks_for_speech(self):
        for lang in ("en", "ja"):
            note = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang).note_by_id["definite_weak_adjective"]
            self.assertNotIn('"', note.text)
            self.assertNotIn("word for the", note.text)


if __name__ == "__main__":
    unittest.main()
