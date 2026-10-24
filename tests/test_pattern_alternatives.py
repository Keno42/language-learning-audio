"""A pattern's sentence can have another acceptable answer: «It's twelve o'clock.» is «Klukkan er tólf.», and «Hún er tólf.» too (the
owner, 2026-10-23: «I wonder every time»). A construction's ``alternatives`` take its slots and are filled as the sentence just answered
was; past the hint stages one is sometimes offered («You could also say:»), as a fixed phrase's is."""
import random
import unittest
from dataclasses import replace
from pathlib import Path

from audiolesson.content import CurriculumError, load_curriculum, validate
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class Offers(random.Random):
    """Takes every «sometimes» branch: an alternative is offered whenever it may be."""

    def random(self):
        return 0.0


class PatternAlternativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula/is-en", known_lang="en")

    def test_the_clock_sentence_takes_hun_with_the_same_hour(self):
        cur = self.cur
        clock = cur.by_id["klukkan_er"]
        self.assertEqual(cur.resolve_alternatives(clock, {"hour": cur.by_id["tolf"]}), ["Hún er tólf."])
        self.assertEqual(cur.resolve_alternatives(clock, {"hour": cur.by_id["thrju"]}), ["Hún er þrjú."])

    def test_an_alternative_without_the_pattern_slots_is_refused(self):
        cur = load_curriculum(ROOT / "curricula/is-en", known_lang="en")
        clock = cur.by_id["klukkan_er"]
        cur.items[cur.items.index(clock)] = cur.by_id["klukkan_er"] = replace(clock, alternatives=["Hún er tólf."])
        with self.assertRaisesRegex(CurriculumError, "an alternative uses the item's slots"):
            validate(cur)

    def builder(self):
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"), Offers(0))
        b.in_lesson.update({"klukkan_er", "thrju", "fimm", "sex", "sjo", "atta"})
        return b

    def offered(self, sc):
        """(answer, alternative) for each alternative offered, after checking it is framed and said in the answer's voice."""
        segs, pairs = sc.segments, []
        for k, s in enumerate(segs):
            if s.role == "alternative":
                answer = next(a for a in reversed(segs[:k]) if a.type == "answer")
                self.assertEqual(next(a for a in reversed(segs[:k]) if a.type != "pause").text, "You could also say:")
                self.assertEqual(s.speaker, answer.speaker, "the same voice says the other answer")
                pairs.append((answer.text, s.text))
        return pairs

    def test_the_offered_alternative_is_the_sentence_just_answered(self):
        clock = self.cur.by_id["klukkan_er"]
        for stage in ("meaning", "situation"):
            sc = Script(1, "t", "is", "en")
            self.builder().recall(sc, clock, stage)
            (pair,) = self.offered(sc)
            self.assertEqual(pair[1], pair[0].replace("Klukkan er ", "Hún er "), stage)
            self.assertNotEqual(pair[0], pair[1])

    def test_a_made_sentence_offers_it_once_a_lesson_with_its_own_hour(self):
        b, sc = self.builder(), Script(1, "t", "is", "en")
        for _ in range(3):
            self.assertIsNotNone(b._recombine(sc, self.cur.by_id["klukkan_er"], met_fills=True))
        (pair,) = self.offered(sc)
        self.assertEqual(pair[1], pair[0].replace("Klukkan er ", "Hún er "))
        self.assertNotEqual(pair[0], "Klukkan er þrjú.", "a made sentence, not the example")

    def test_no_alternative_while_the_sentence_is_hinted(self):
        sc = Script(1, "t", "is", "en")
        self.builder().recall(sc, self.cur.by_id["klukkan_er"], "hinted")
        self.assertFalse([s for s in sc.segments if s.role == "alternative"])


if __name__ == "__main__":
    unittest.main()
