"""An aside written for a background (``Note.audience``) reaches only a learner who has it.

The English asides were written for the course's first learner, a Japanese speaker taught in English: «Treat it like a Japanese bath»,
««Jæja» does the work of several Japanese words». To an English speaker they say nothing. A learner with ``--background ja``, or taught in
Japanese, hears them as written; any other learner hears the same point with no comparison (``text_plain``), or nothing.
"""
import re
import unittest
from dataclasses import replace
from pathlib import Path

from audiolesson.content import NOTE_TARGET_RE, CurriculumError, for_background, load_curriculum

ROOT = Path(__file__).resolve().parent.parent


def assumes_japan(text: str) -> bool:
    return "«ja:" in text or bool(re.search(r"\bJapan", NOTE_TARGET_RE.sub("", text)))


class NoteAudienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_a_learner_without_the_background_hears_no_comparison_with_japan(self):
        plain = for_background(self.cur, "")
        self.assertEqual([n.id for n in plain.notes if assumes_japan(n.text)], [])
        self.assertEqual({n.id for n in plain.notes}, {n.id for n in self.cur.notes}, "every aside written for Japan has a plain text")
        by_id = {n.id: n for n in plain.notes}
        self.assertNotIn("omiyage", by_id["afmaeli"].text)
        self.assertIn("«Mig langar í kaffi» is literally 'me longs for coffee'.", by_id["mig_langar_idiom"].text, "the point stays")

    def test_a_learner_with_it_hears_the_asides_as_written(self):
        self.assertEqual(for_background(self.cur, "ja").notes, self.cur.notes)

    def test_a_learner_taught_in_japanese_has_it(self):
        ja = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")
        self.assertEqual(for_background(ja, "").notes, ja.notes)

    def test_an_aside_with_no_plain_text_is_not_played_without_the_background(self):
        note = next(n for n in self.cur.notes if n.audience)
        cur = replace(self.cur, notes=[replace(note, text_plain="")])
        self.assertEqual(for_background(cur, "").notes, [])
        self.assertEqual(len(for_background(cur, "ja").notes), 1)

    def test_validate_wants_an_audience_on_an_aside_that_assumes_japan(self):
        from audiolesson.content import validate
        note = next(n for n in self.cur.notes if n.id == "thjorfe")
        for bad in (replace(note, audience="", text_plain=""), replace(note, text_plain="Tipping is like in Japan.")):
            with self.assertRaises(CurriculumError):
                validate(replace(self.cur, notes=[bad]))


if __name__ == "__main__":
    unittest.main()
