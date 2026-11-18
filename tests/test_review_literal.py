"""Lesson 60 (the owner on #559): the written review asked «Your friend suggests a taxi. Say you'll go by bus instead.» for «Við förum með
strætó.». In the lesson the scene carries the gap between the instruction and the answer; the next morning, one question at a time, nothing does.
A situation in the written review says the item's literal meaning after it, unless the instruction already holds the meaning's words."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.prompts import Prompts
from audiolesson.review_wording import literal_prompt, reword_review, with_literal

ROOT = Path(__file__).resolve().parent.parent


class Item:
    def __init__(self, meaning, situation=None):
        self.meaning, self.situation, self.situations, self.partner_cue_situation = meaning, situation, [], ""


class Cur:
    def __init__(self, **items):
        self.by_id = items


class ReviewLiteralTests(unittest.TestCase):
    def setUp(self):
        self.en = Prompts.load("en")

    def test_a_situation_that_does_not_say_the_meaning_gets_it(self):
        bus = Item("We'll go by bus.")
        self.assertEqual(with_literal("Your friend suggests a taxi. Say you'll go by bus instead.", bus, self.en),
                         "Your friend suggests a taxi. Say you'll go by bus instead.\nLiterally: We'll go by bus.")
        self.assertEqual(with_literal("Greet the shopkeeper.", Item("Good day."), self.en), "Greet the shopkeeper.\nLiterally: Good day.")

    def test_a_situation_that_already_says_it_is_kept(self):
        for situation, meaning in [("Say let's go by bus instead: literally, we'll go by bus.", "We'll go by bus."),
                                   ("Ask where the toilet is.", "Where is the toilet?")]:
            self.assertEqual(with_literal(situation, Item(meaning), self.en), situation)

    def test_the_plan_question_gets_it_behind_the_speakers_form_and_other_prompts_are_kept(self):
        cur = Cur(bus=Item("We'll go by bus.", "Say you'll go by bus instead."), x=Item("Thanks.", "Thank her."))
        q = {"items": ["bus"], "prompt": "As a woman: Say you'll go by bus instead.", "answer": "Við förum með strætó."}
        self.assertEqual(literal_prompt(q, cur, self.en), "As a woman: Say you'll go by bus instead.\nLiterally: We'll go by bus.")
        other = {"items": ["bus"], "prompt": "How do you say: We'll go by bus.", "answer": "Við förum með strætó."}
        self.assertEqual(literal_prompt(other, cur, self.en), other["prompt"])
        shared = {"items": ["bus", "x"], "prompt": "Say you'll go by bus instead.", "answer": "…"}
        self.assertEqual(literal_prompt(shared, cur, self.en), shared["prompt"])
        self.assertEqual(reword_review([q], self.en, "is")[0]["prompt"], q["prompt"], "without the curriculum nothing is added")

    def test_the_course_asks_the_bus_with_its_literal_meaning(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        it = cur.by_id["vid_forum_med_straeto"]
        q = {"items": [it.id], "prompt": it.situation, "answer": it.target}
        self.assertIn(it.meaning, reword_review([q], self.en, cur.target_lang, cur)[0]["prompt"])


if __name__ == "__main__":
    unittest.main()
