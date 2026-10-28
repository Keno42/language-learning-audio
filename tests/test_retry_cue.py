"""#423: a sentence the learner reported hard opened with «This one was hard. Slowly, then at natural speed. First the whole.» and played the Icelandic at once:
no meaning, nothing asked. It now asks for the sentence from its meaning, leaves time to answer, gives the model, then the slow and natural-speed practice."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
KNOWN = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled")


class RetryCueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def builder(self, cur=None, lang="en", known=()):
        cur = cur or self.cur
        b = Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
        for i in known:
            b.learner.items[i] = KNOWN
        return b

    def played(self, b, item_id):
        sc = Script(1, "t", "is", b.kl)
        ex = b.slow_word_exercise(sc, b.cur.by_id[item_id])
        return ex, [s for s in sc.segments if s.exercise == ex.index]

    def assert_retry(self, segs, cue, sentence):
        """The cue, an answer pause, the model as the answer, then the existing practice: «Slowly.», word by word, a repeat, «And at natural speed.», the
        sentence, a repeat."""
        self.assertEqual((segs[0].type, segs[0].text), ("narrate", cue))
        self.assertEqual((segs[1].type, segs[1].role), ("pause", "answer"))
        self.assertEqual((segs[2].type, segs[2].text, segs[2].speaker), ("answer", sentence, "native_a"))
        rest = [(s.type, s.text) for s in segs[3:] if s.type != "pause" and s.role != "spaced"]
        self.assertEqual(rest, [("narrate", "Slowly."), ("narrate", "And at natural speed."), ("speak", sentence)])
        self.assertEqual([s.text for s in segs if s.role == "spaced"], sentence.split())
        self.assertEqual([s.role for s in segs if s.type == "pause"].count("answer"), 1, "one answer pause, before the first model")
        self.assertFalse([s for s in segs if s.text and "This one was hard" in s.text])

    def test_a_phrase_is_asked_from_its_meaning_before_the_model(self):
        _, segs = self.played(self.builder(), "vid_erum_fjogur")
        self.assert_retry(segs, "Let's try to say this sentence in Icelandic again: There are four of us.", "Við erum fjögur.")

    def test_a_pattern_gives_the_meaning_of_the_sentence_it_models(self):
        b = self.builder(known=["fara_heim"])
        ex, segs = self.played(b, "eg_nenni_ekki")
        item = self.cur.by_id["eg_nenni_ekki"]
        sentence, meaning = self.cur.resolve_slots(item, b.worked_example_fills(item))
        self.assertEqual(ex.label, f"slow: {sentence}")
        self.assertEqual(sentence, "Ég nenni ekki að fara heim.")
        self.assert_retry(segs, f"Let's try to say this sentence in Icelandic again: {b._m(meaning)}", sentence)
        self.assertNotIn("{", segs[0].text)

    def test_a_gendered_sentence_names_the_form_the_model_says(self):
        b = self.builder(known=["eg_er_state", "glod"])
        _, segs = self.played(b, "eg_er_state")
        self.assertTrue(segs[0].text.startswith("As a woman:"), segs[0].text)
        self.assertEqual(segs[2].text, "Ég er glöð.")
        self.assertEqual(b._gender_uses, {}, "no gender turn taken")

    def test_the_cue_follows_the_configured_languages(self):
        ja = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")
        b = self.builder(ja, "ja")
        _, segs = self.played(b, "vid_erum_fjogur")
        self.assertEqual(ja.by_id["vid_erum_fjogur"].spoken_meaning, "四人です。")
        self.assertEqual(segs[0].text, "この文を、もう一度アイスランド語で言ってみましょう。「四人です」", "the meaning as the other Japanese cues quote it")
        self.assertEqual((segs[1].role, segs[2].text), ("answer", "Við erum fjögur."))

    def test_a_single_word_keeps_its_word_model(self):
        _, segs = self.played(self.builder(), "reikninginn")
        self.assertEqual(segs[0].text, "This word is hard to say.")
        self.assertNotIn("answer", [s.role for s in segs if s.type == "pause"])
        self.assertEqual([s.text for s in segs if s.type == "speak" and s.rate < 1], ["reik", "ning", "inn"])


if __name__ == "__main__":
    unittest.main()
