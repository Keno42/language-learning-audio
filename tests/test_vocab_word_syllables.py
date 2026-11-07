"""#439 step 4 (lesson 49): «í fyrramálið» was asked for in syllables, and the model only said «í» and «fyrramálið» apart. A phrase could name its hard
words' splits (``word_syllables``, #337), a vocab item of two words could not. It now can, «fyrramálið» has its split, and ``validate`` lists the long
words inside items of two words or more that have none, since a split is authored, never guessed."""
import dataclasses
import unittest
from pathlib import Path

from audiolesson.content import CurriculumError, load_curriculum, validate
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.sounds import hard_words_of, unsplit_long_words
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
PIECES = ["fyrr", "a", "mál", "ið"]


class VocabWordSyllablesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_a_vocab_item_of_two_words_names_its_hard_word(self):
        item = self.cur.by_id["i_fyrramalid"]
        self.assertEqual(hard_words_of(item), [("fyrramálið", PIECES)])
        self.assertEqual(hard_words_of(item, reported=True), [("fyrramálið", PIECES)])

    def test_the_model_of_a_reported_item_says_the_pieces_slowly(self):
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        whole = {"through": "eg_fer", "answer": "Ég fer í fyrramálið.", "meaning": "I'm leaving tomorrow morning."}
        b.slow_word_exercise(sc, self.cur.by_id["i_fyrramalid"], whole)
        slow = [g.text for g in sc.segments if g.type == "speak" and g.rate < 1]
        self.assertEqual(slow, PIECES)
        self.assertEqual([g.text for g in sc.segments if g.type == "speak"][-1], "fyrramálið", "then the word at natural speed")

    def test_word_syllables_go_on_an_item_of_two_words_or_more(self):
        one_word = dataclasses.replace(self.cur.by_id["thusund"], word_syllables={"þúsund": ["þús", "und"]})
        cur = dataclasses.replace(self.cur, items=[one_word if i.id == "thusund" else i for i in self.cur.items])
        with self.assertRaises(CurriculumError):
            validate(cur)

    def test_validate_lists_the_long_words_with_no_split(self):
        listed = unsplit_long_words(self.cur)
        self.assertNotIn(("i_fyrramalid", "fyrramálið"), listed)
        self.assertTrue(listed, "the authoring list: the words still to split")
        self.assertTrue(all(len(w) > 4 for _, w in listed))


if __name__ == "__main__":
    unittest.main()
