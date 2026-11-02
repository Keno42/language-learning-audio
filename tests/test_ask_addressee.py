"""Lesson 44: «Ask if she's Icelandic.» was a review question whose answer is «Ert þú íslensk?». With no one named after «ask», «she» reads as a
third person («Er hún íslensk?»). An instruction to ask a person names them («Ask her if …», «Ask the receptionist if …»), or names who the question
is about («Ask what the girl is called.»)."""
import unittest
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import ask_without_addressee, cue_texts, load_curriculum
from audiolesson.themes import load_themes

ROOT = Path(__file__).resolve().parent.parent


class AskNamesTheAddresseeTests(unittest.TestCase):
    def test_a_question_about_a_person_needs_someone_after_ask(self):
        flagged = [t for _, t in ask_without_addressee([(str(n), t) for n, t in enumerate([
            "Ask if she's Icelandic.",
            "Ask where she lives.",
            "Your friend was ill. Ask how she feels.",
            "Ask what her name is.",
            "At the stall. Ask whether they take cards.",
            "Say no, and ask if she has something for a headache.",
        ])])]
        self.assertEqual(len(flagged), 6, flagged)

    def test_a_named_addressee_or_a_question_about_no_person_passes(self):
        ok = [
            "Ask her if she's Icelandic.",
            "Ask the receptionist if she speaks English.",
            "Ask Anna what he's called.",
            "Ask what the girl is called.",
            "Ask where the bus stop is.",
            "Ask if you may pay by card.",
            "Your friend says she found a great café. Ask where.",
            "Ask how much it costs.",
        ]
        self.assertEqual(ask_without_addressee([(str(n), t) for n, t in enumerate(ok)]), [])

    def test_the_curriculum_names_every_addressee(self):
        path = ROOT / "curricula" / "is-en"
        cur = load_curriculum(path)
        themes = load_themes(path, cur, load_cando(path))
        theme_cues = [(f"{t.id}:{n}", turn.cue) for t in themes for n, lv in enumerate(t.levels, 1) for turn in lv.turns if turn.who == "you"]
        self.assertEqual(ask_without_addressee(cue_texts(cur) + theme_cues), [])
        self.assertIn("Ask her if she's Icelandic.", cur.by_id["ert_thu_islensk"].situation)


if __name__ == "__main__":
    unittest.main()
