"""#548 step 2 (the owner, 2026-11-20: the «why» of a form goes to the Discord bot as text, not into the audio): the anchor frames a native teacher
gave the owner («Hér er bankinn / um bankann / frá bankanum / til bankans»), and, for a phrase whose word takes another form, the frame whose noun
takes the same one (``Item.like``). The plan carries both for the day's new items; the lessons say nothing of them."""
import dataclasses
import unittest
from pathlib import Path

from audiolesson.cli import _case_frames
from audiolesson.content import CASE_FRAMES, CurriculumError, load_curriculum, validate

ROOT = Path(__file__).resolve().parent.parent
IS_EN = ROOT / "curricula" / "is-en"


class CaseFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(IS_EN)

    def test_the_anchor_frames_are_one_noun_with_the_small_word_changed(self):
        anchors = self.cur.case_anchors
        self.assertEqual([f["frame"] for f in anchors["frames"]], ["", *CASE_FRAMES])
        self.assertEqual([f["line"] for f in anchors["frames"]], ["Hér er bankinn.", "um bankann", "frá bankanum", "til bankans"])
        ja = load_curriculum(IS_EN, known_lang="ja").case_anchors
        self.assertEqual(ja["frames"][2]["meaning"], "銀行から")
        for text in (anchors["lead"], ja["lead"]):
            self.assertFalse([t for t in ("accusative", "dative", "genitive", "対格", "与格", "属格") if t in text], "no grammatical term")

    def test_a_phrase_points_its_form_to_a_frame(self):
        self.assertEqual(self.cur.by_id["get_eg_fengid_reikninginn"].like, {"reikninginn": "um"})
        self.assertEqual(self.cur.by_id["eg_er_med_ofnaemi_fyrir_hnetum"].like, {"hnetum": "frá"})
        self.assertEqual(self.cur.by_id["hvad_heitir_thetta_a_islensku"].like, {"íslensku": "frá"}, "«á íslensku»: the frá form, not tala's")
        self.assertEqual(self.cur.by_id["eg_tala_sma_islensku"].like, {"íslensku": "um"})
        self.assertEqual(self.cur.by_id["eg_spila_fotbolta"].like, {"fótbolta": "um"}, "review of #598: spila's object is accusative, as «um bankann»")
        self.assertGreaterEqual(sum(1 for i in self.cur.items if i.like), 25)

    def test_a_like_names_a_word_of_the_target_and_a_frame(self):
        it = self.cur.by_id["get_eg_fengid_reikninginn"]
        for bad in ({"bankann": "um"}, {"reikninginn": "fyrir"}):
            cur = dataclasses.replace(self.cur, items=[dataclasses.replace(it, like=bad) if i.id == it.id else i for i in self.cur.items])
            with self.assertRaises(CurriculumError):
                validate(cur)

    def test_the_plan_carries_the_day_s_forms_and_the_anchors(self):
        out = _case_frames(self.cur, ["get_eg_fengid_reikninginn", "takk", "get_eg_fengid_reikninginn"])
        self.assertEqual(out["anchors"], self.cur.case_anchors)
        self.assertEqual(list(out["items"]), ["get_eg_fengid_reikninginn"])
        self.assertEqual(out["items"]["get_eg_fengid_reikninginn"]["like"], {"reikninginn": "um"})
        self.assertEqual(_case_frames(self.cur, ["takk"]), {}, "no form of the day: nothing for the card")


if __name__ == "__main__":
    unittest.main()
