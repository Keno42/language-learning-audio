"""Lesson 60: the written review asked «Your friend suggests a taxi. Say you'll go by bus instead.» for «Við förum með strætó.», and the learner
could not tell the answer from the cue. The English «you» does not tell «ég» from «við», and the course holds both («Ég fer á morgun.», «Við förum
á morgun.»). A cue whose answer opens with «Við» names the group; one whose answer opens with «Þú» is said to the person, not about them."""
import unittest
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import Curriculum, load_curriculum, subject_unnamed
from audiolesson.themes import load_themes

ROOT = Path(__file__).resolve().parent.parent


def _pairs(rows):
    return [(str(n), answer, cue) for n, (answer, cue) in enumerate(rows)]


class CueNamesTheSubjectTests(unittest.TestCase):
    def setUp(self):
        self.empty = Curriculum.__new__(Curriculum)
        self.empty.items, self.empty.dialogues = [], []

    def test_a_we_answer_with_a_you_cue_is_flagged(self):
        flagged = subject_unnamed(self.empty, _pairs([
            ("Við förum með strætó.", "Your friend suggests a taxi. Say you'll go by bus instead."),
            ("Við förum á morgun.", "The host asks how long you're staying. Say you're leaving tomorrow."),
            ("Við göngum upp.", "Your friend eyes the chairlift. Say you'll walk up."),
            ("Þú mátt það.", "Your guest asks if he may open the window. Say he may."),
        ]))
        self.assertEqual(len(flagged), 4, flagged)

    def test_a_cue_that_names_the_group_or_the_person_passes(self):
        ok = _pairs([
            ("Við förum með strætó.", "Your friend suggests a taxi. Say you'll both go by bus instead."),
            ("Við erum gift.", "Someone asks if you two are a couple. Say you're married."),
            ("Við erum fjögur.", "Say there are four of you."),
            ("Við erum fjögur.", "The host asks how many you are. Say four."),
            ("Við sjáum til.", "Anna asks if you'll go hiking Sunday. Say we'll see."),
            ("Þú mátt það.", "Your guest asks if he may open the window. Tell him he may."),
            ("Ég fer á morgun.", "Say you're leaving tomorrow."),
        ])
        self.assertEqual(subject_unnamed(self.empty, ok), [])

    def test_the_curriculum_names_every_subject(self):
        path = ROOT / "curricula" / "is-en"
        cur = load_curriculum(path)
        themes = load_themes(path, cur, load_cando(path))
        more = [(f"{t.id}:{n}", turn.say, turn.cue) for t in themes for n, lv in enumerate(t.levels, 1) for turn in lv.turns if turn.who == "you"]
        self.assertEqual(subject_unnamed(cur, more), [])
        self.assertIn("both", cur.by_id["vid_forum_med_straeto"].situation)


if __name__ == "__main__":
    unittest.main()
