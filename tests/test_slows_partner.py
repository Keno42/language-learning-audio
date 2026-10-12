"""#261: after «Gætirðu talað hægar?» the partner's next line is spoken word by word with gaps, not stretched."""
import unittest
from pathlib import Path

from audiolesson.content import CurriculumError, curriculum_from_dict, load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


class SlowsPartnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def builder(self):
        return Builder(self.cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))

    def spaced(self, sc):
        return [g.text for g in sc.segments if g.type == "speak" and g.role == "spaced"]

    def test_only_the_item_with_the_flag_slows_the_partner(self):
        self.assertEqual([i.id for i in self.cur.items if i.slows_partner], ["gaetirdu_talad_haegar"])

    def test_the_dialogue_reply_after_the_request_is_word_spaced_and_nothing_else(self):
        dlg = next(d for d in self.cur.dialogues if any(t.expect == "gaetirdu_talad_haegar" for t in d.turns))
        for replay in (False, True):
            b = self.builder()
            sc = Script(2, "t", "is", "en")
            b.dialogue(sc, dlg, replay=replay)
            words = self.spaced(sc)
            reply = next(t.partner for t in dlg.turns if t.expect == "gaetirdu_talad_haegar").split()
            self.assertEqual(words[:len(reply)], reply, replay)
            self.assertEqual(len(words), len(reply) * (2 if replay else 1), "no other partner line changes")
            gaps = [g for g in sc.segments if g.role == "word_gap"]
            self.assertEqual(len(gaps), len(words) - (2 if replay else 1))
            self.assertTrue(all(g.duration == b.timing.word_gap for g in gaps))
            self.assertTrue(all(g.rate == 1.0 for g in sc.segments if g.role == "spaced"), "natural speed, not stretched")

    def test_the_transcript_shows_the_line_once_with_its_gaps_marked(self):
        dlg = next(d for d in self.cur.dialogues if any(t.expect == "gaetirdu_talad_haegar" for t in d.turns))
        b = self.builder()
        sc = Script(2, "t", "is", "en")
        b.dialogue(sc, dlg)
        self.assertIn("(word by word):** Fyrirgefðu. · Tölum · við · bara · íslensku.", sc.transcript())

    def test_connects_bridge_after_the_request_is_word_spaced(self):
        slower = self.cur.by_id["gaetirdu_talad_haegar"]
        again = self.cur.by_id["gaetirdu_endurtekid_thetta"]
        b = self.builder()
        sc = Script(2, "t", "is", "en")
        b.connect(sc, [slower, again])
        self.assertEqual(self.spaced(sc), "Auðvitað. Herbergið er númer tuttugu og þrjú.".split())

    def test_the_flag_is_for_a_phrase(self):
        raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": "a", "kind": "vocab", "target": "hægar", "meaning": "slower", "slows_partner": True}]}
        with self.assertRaisesRegex(CurriculumError, "slows_partner"):
            curriculum_from_dict(raw)


if __name__ == "__main__":
    unittest.main()
