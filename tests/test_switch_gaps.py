"""#301: a change of voice always has a gap."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum, notes_cutting_sentences
from audiolesson.script import Script, Segment

CUR = Path(__file__).resolve().parents[1] / "curricula" / "is-en"


def seg(kind, speaker, lang, text="x"):
    return Segment(kind, speaker, text, lang, 1.0, 1.0, None, 0)


class SeparateSwitchesTests(unittest.TestCase):
    def script(self, *segments):
        sc = Script(lesson_number=1, title="t", target_lang="is", known_lang="en")
        sc.segments = list(segments)
        return sc

    def test_a_change_of_voice_gets_the_long_gap_and_the_same_voice_the_short_one(self):
        sc = self.script(seg("narrate", "instructor", "en"), seg("speak", "native_a", "is"), seg("speak", "native_a", "is"), seg("narrate", "instructor", "en"))
        self.assertEqual(sc.touching_switches(), 2)
        self.assertEqual(sc.separate_switches(0.4, 0.25), 3)
        pauses = [(s.duration, s.role, s.floor) for s in sc.segments if s.type == "pause"]
        self.assertEqual(pauses, [(0.4, "switch", 0.4), (0.25, "switch", 0.25), (0.4, "switch", 0.4)])
        self.assertEqual(sc.touching_switches(), 0)

    def test_an_existing_pause_is_left_alone(self):
        sc = self.script(seg("narrate", "instructor", "en"), Segment("pause", None, None, None, 1.0, 0.8, "beat", 0), seg("speak", "native_a", "is"))
        self.assertEqual(sc.separate_switches(0.4, 0.25), 0)
        self.assertEqual(len(sc.segments), 3)

    def test_the_gap_belongs_to_the_exercise_and_survives_a_second_pass(self):
        sc = self.script(seg("narrate", "instructor", "en"), seg("answer", "native_a", "is"))
        sc.separate_switches(0.4, 0.25)
        self.assertEqual(sc.segments[1].exercise, 0)
        self.assertEqual(sc.separate_switches(0.4, 0.25), 0)


class NoteTests(unittest.TestCase):
    def test_the_modal_note_is_said_as_whole_sentences(self):
        self.assertNotIn("modal_infinitive", notes_cutting_sentences(load_curriculum(CUR)))
        self.assertNotIn("modal_infinitive", notes_cutting_sentences(load_curriculum(CUR, known_lang="ja")))

    def test_the_notes_that_still_cut_a_sentence_do_not_grow(self):
        self.assertLessEqual(len(notes_cutting_sentences(load_curriculum(CUR))), 25)


if __name__ == "__main__":
    unittest.main()
