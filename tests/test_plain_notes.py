"""The owner (2026-11-25, the principle «no grammatical terms in lessons»): an aside says what changes with words the learner knows, never a
grammatical term («dative», «masculine», «verb»; «与格», «男性名詞», «動詞»). The explanation with terms belongs in the bot's written text, not the
audio (2026-11-20). Checked over every note's spoken text and lead lines, in both languages."""
import re
import tomllib
import unittest
from pathlib import Path

NOTES = Path(__file__).resolve().parent.parent / "curricula" / "is-en" / "90-notes.toml"
EN = re.compile(r"\b(dative|accusative|genitive|nominative|masculine|feminine|neuter|plural|singular|verbs?|nouns?|adjectives?|case|infinitive|"
                r"subject|object|conjugat\w*|declen\w*|pronouns?|prepositions?|tense|imperative|articles?|genders?|grammatical)\b", re.I)
JA = re.compile(r"男性|女性名詞|中性|与格|対格|属格|主格|不定詞|形容詞|代名詞|動詞|名詞|主語|人称|格")


class PlainNotesTests(unittest.TestCase):
    def test_no_note_says_a_grammatical_term(self):
        notes = [n for v in tomllib.loads(NOTES.read_text(encoding="utf-8")).values() if isinstance(v, list) for n in v]
        self.assertTrue(notes)
        found = []
        for n in notes:
            for field, value in n.items():
                if not field.startswith(("text", "parts_lead", "lead")):
                    continue
                for line in value if isinstance(value, list) else [value]:
                    if isinstance(line, str) and (hit := (JA if field.endswith("_ja") else EN).findall(line)):
                        found.append((n.get("id"), field, hit))
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
