"""Lesson 67: a line whose words differ from its meaning says them aloud (the `form-why` family).

«Segðu hverja setningu.» was taught as «Now say each one.» and «Hann er hérna.» as «The pain is here.»; the learner asked for the literal
words. Six items had them in `pronunciation_notes` only, which the transcript prints and no lesson says. Every item whose note says
«literally» has an aside (`[[notes]]` in `90-notes.toml`) that names it, so the literal words are heard in the lesson (owner, after lesson 29:
idioms said literally), and the asides added for it use no grammatical term (owner, 2026-11-16).
"""

import re
import unittest

from audiolesson.content import load_curriculum

TERMS = re.compile(r"\b(nominative|accusative|dative|genitive|masculine|feminine|neuter|case|subject|object|verb|noun|pronoun|gender)\b", re.I)
LITERAL_NOTES = ("hann_er_herna_literal", "segdu_hverja_setningu_literal", "eg_er_med_literal", "ofnaemi_fyrir_literal", "half_atta_literal")


class LiteralAsideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum("curricula/is-en")

    def test_every_literal_transcript_note_is_said_in_an_aside(self):
        spoken = {i for n in self.cur.notes for i in n.items}
        missing = [it.id for it in self.cur.items if "literally" in (it.pronunciation_notes or "").lower() and it.id not in spoken]
        self.assertEqual(missing, [], "a literal meaning only in the transcript is never heard")

    def test_the_remarked_lines_say_their_literal_words(self):
        notes = {n.id: n for n in self.cur.notes}
        self.assertIn("'he is here'", notes["hann_er_herna_literal"].text)
        self.assertIn("'say each sentence'", notes["segdu_hverja_setningu_literal"].text)

    def test_no_grammatical_term(self):
        notes = {n.id: n for n in self.cur.notes}
        for nid in LITERAL_NOTES:
            self.assertIsNone(TERMS.search(notes[nid].text), nid)


if __name__ == "__main__":
    unittest.main()
