"""#281: the one definition of a word and of a normalised line."""
import unittest

from audiolesson import exercises, listening_tasks, planner, review_wholes
from audiolesson.text import WORD, norm_utterance, words


class TextTests(unittest.TestCase):
    def test_a_word_is_a_run_of_letters(self):
        self.assertEqual(words("Klukkan 5, takk!"), ["Klukkan", "takk"])
        self.assertEqual(words("Ég þarf úlpu_2.", lower=True), ["ég", "þarf", "úlpu"])
        self.assertEqual(WORD.findall("a-b"), ["a", "b"])

    def test_a_line_is_normalised_without_case_and_trailing_punctuation(self):
        self.assertEqual(norm_utterance("  Takk fyrir!  "), "takk fyrir")
        self.assertEqual(norm_utterance("Hvað?…"), "hvað")

    def test_every_module_uses_the_same_definitions(self):
        self.assertIs(exercises._norm_utterance, norm_utterance)
        for module, name in ((listening_tasks, "WORD"), (planner, "_WORD_RE"), (review_wholes, "_WORD"), (exercises, "_FILL_WORD_RE")):
            self.assertIs(getattr(module, name), WORD, f"{module.__name__}.{name}")


if __name__ == "__main__":
    unittest.main()
