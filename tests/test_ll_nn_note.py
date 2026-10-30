"""#443 (lesson 42, 14:26): the aside on double «ll» called its sound pre-aspiration, said it came wherever «ll» or «nn» is written, and gave
«allt» as an example. A native «ll» is pre-stopped («fjall» ≈ fjatl) except before «t» («allt»: a plain breathy «l»); «nn» takes the stop only
after a long vowel or a diphthong («seinn», not «inn»); pre-aspiration is the breath before «pp», «tt», «kk» («takk»)."""
import re
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum

ROOT = Path(__file__).resolve().parent.parent


class LlNnNoteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.note = next(n for n in load_curriculum(ROOT / "curricula" / "is-en").notes if n.id == "tvo_l")
        cls.note_ja = next(n for n in load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja").notes if n.id == "tvo_l")

    def test_the_rule_and_its_exceptions(self):
        text = self.note.text
        self.assertNotIn("pre-aspirated", text)
        self.assertNotIn("wherever", text, "not every «ll» or «nn»")
        for word in ("fjall", "allt", "seinn", "inn", "takk"):
            self.assertIn(f"«{word}»", text)
        self.assertIn("pre-aspiration", text.split("«takk»", 1)[1], "pre-aspiration is named for «takk» only")
        self.assertRegex(text, r"Before a 't' there is no stop[^.]*«allt»")

    def test_the_japanese_says_the_same(self):
        text = self.note_ja.text
        for word in ("fjall", "allt", "seinn", "inn", "takk"):
            self.assertIn(f"«{word}»", text)
        self.assertEqual(text.count("前気音化"), 1)
        self.assertLess(text.index("«takk»"), text.index("前気音化"))


if __name__ == "__main__":
    unittest.main()
