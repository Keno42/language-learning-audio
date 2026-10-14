"""#270 step 1, the other half: each scene's frames and the case each asks, read from the scene data."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum

ROOT = Path(__file__).resolve().parent.parent


class SceneFramesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from audiolesson.cando import load_cando
        from audiolesson.themes import load_themes
        path = ROOT / "curricula" / "is-en"
        cls.cur = load_curriculum(path)
        cls.themes = load_themes(path, cls.cur, load_cando(path, cls.cur))

    def test_every_scene_turn_that_says_a_noun_names_its_frame_and_case(self):
        from audiolesson.nouns import scene_frames
        rows = scene_frames(self.cur, self.themes)
        self.assertTrue(rows)
        by_say = {r["say"]: r for r in rows}
        r = by_say["Ég ætla að fá súpu."]
        self.assertEqual((r["frames"], r["nouns"]), ([{"construction": "eg_aetla_ad_fa", "slot": "thing", "case": "acc"}], [{"item": "supu", "noun": "supa", "form": "acc"}]))
        self.assertEqual(by_say["Vatn, takk."]["frames"], [], "a bare answer has no frame")
        self.assertEqual(by_say["Get ég fengið matseðilinn?"]["nouns"][0]["form"], "acc_def", "the article form of the accusative")

    def test_a_form_standing_for_another_case_is_listed_not_an_error(self):
        from audiolesson.nouns import scene_frames, scene_report, scene_syncretisms
        notes = scene_syncretisms(scene_frames(self.cur, self.themes))
        self.assertTrue(any("eldfjall" in n and "the same word" in n for n in notes), notes)
        self.assertIn("Mig langar að sjá eldfjall.", scene_report(self.cur, self.themes))


if __name__ == "__main__":
    unittest.main()
