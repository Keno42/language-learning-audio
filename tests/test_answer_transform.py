"""Draft of lesson 52: «Listen to how the sentence changes. Hvað kostar kaffi? becomes Það kostar þúsund krónur.», for coffee, tea, beer and «this»,
asked five times with the same answer. A transform whose results answer its sources (``Item.answers``) is introduced as a question and its answer, and
its instruction names the answer each time («Answer: It costs six hundred krónur.»), so its prices can vary."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class AnswerTransformTests(unittest.TestCase):
    def test_a_question_and_its_answer_not_becomes(self):
        for lang, intro, link in (("en", "Listen: a question, and its answer.", "The answer:"), ("ja", "質問と、その答えを聞いてください。", "答え：")):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            item = cur.by_id["numbers_price_transform"]
            b = Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
            sc = Script(1, "t", "is", lang)
            b.intro(sc, item)
            narrated = [g.text for g in sc.segments if g.type == "narrate"]
            self.assertEqual(narrated[:2], [intro, link], lang)
            self.assertNotIn(Prompts.load(lang).get("transform_becomes"), narrated)
            answer = [g.text for g in sc.segments if g.type == "answer"][0]
            asked = next(t for t in narrated if t.startswith(("Answer:", "答えてください")))
            exm = next(e for e in item.examples if e.result == answer)
            self.assertIn(exm.result_meaning.rstrip("。."), asked, "the instruction names the price the answer says")

    def test_each_ask_names_its_price_never_same_change(self):
        """Review of #506: after two full instructions the third ask in a row said «Same change:» and expected a price it never named."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        item = cur.by_id["numbers_price_transform"]
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        for exm in item.examples:
            b._transform_prompt(sc, sc.new_exercise("recall", "meaning", [item.id], "x"), item, exm)
        asked = [g.text for g in sc.segments if g.type == "narrate"]
        self.assertEqual(asked, [f"Answer: {e.result_meaning}" for e in item.examples])

    def test_the_prices_vary(self):
        item = load_curriculum(ROOT / "curricula" / "is-en").by_id["numbers_price_transform"]
        self.assertEqual(len({e.result for e in item.examples}), len(item.examples))
        self.assertFalse(any("þúsund" in e.result for e in item.examples), "the draft's «þúsund krónur» five times")

    def test_another_transform_still_says_becomes(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "t", "is", "en")
        b.intro(sc, cur.by_id["kynning_transform_hann_hun"])
        self.assertIn("becomes", [g.text for g in sc.segments if g.type == "narrate"])


if __name__ == "__main__":
    unittest.main()
