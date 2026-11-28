"""A cue with a context sentence names the word as it is in that sentence (the owner, 2026-11-28, on a Japanese lesson 2): «「スキールをください。」と
言うときの「スキール、アイスランドの乳製品」は、何と言いますか？» said the word's description inside a cue whose context already says what it is.
``Item.cue_meaning`` is the in-sentence form there («スキール», «skyr»); the introduction still says the whole meaning."""
import unittest

from audiolesson.content import load_curriculum
from audiolesson.exercises import meaning_prompt
from audiolesson.prompts import Prompts
from tests.audiolesson_common import ROOT


class CueMeaningTests(unittest.TestCase):
    def test_a_context_cue_says_the_word_as_in_its_sentence(self):
        for lang, word, whole in (("en", "skyr", "skyr, the Icelandic dairy"), ("ja", "スキール", "スキール、アイスランドの乳製品")):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            skyr = cur.by_id["skyr"]
            self.assertEqual((skyr.cue_meaning, skyr.spoken_meaning), (word, whole), lang)
            for _ in range(6):
                cue = meaning_prompt(Prompts.load(lang), lang, "is", skyr.cue_meaning, skyr.context)
                self.assertNotIn(whole, cue, lang)
                self.assertIn(word, cue, lang)

    def test_without_a_context_the_cue_keeps_the_whole_meaning(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        plain = next(i for i in cur.items if not i.context and i.meaning_forms.get("in_sentence"))
        self.assertEqual(plain.cue_meaning, plain.spoken_meaning)


if __name__ == "__main__":
    unittest.main()
