"""The theme levels' content (#327): what a level asks the learner to say."""
import unittest
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.themes import load_themes

ROOT = Path(__file__).resolve().parent.parent


class ThemeLevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "curricula" / "is-en"
        cls.cur = load_curriculum(path)
        cls.themes = {t.id: t for t in load_themes(path, cls.cur, load_cando(path))}

    def test_no_learner_line_needs_a_gendered_item(self):
        """A learner's line is literal: one form, in the learner's voice, never announced. A line whose words follow the speaker's gender
        («Ég er týnd.» / «Ég er týndur.») would ask one form without saying which, the confusion #375 removed from the review."""
        for t in self.themes.values():
            for n, level in enumerate(t.levels):
                for turn in level.turns:
                    if turn.who == "you":
                        gendered = [i for i in turn.items if self.cur.by_id[i].target_m]
                        self.assertEqual(gendered, [], f"{t.id}:{n + 1}: {turn.say}")

    def test_the_towns_third_level_is_the_way_itself(self):
        """After lesson 38 of the lesson-33 replay the day's new items were the way (left or right, how far, the map) and no level said
        them: the town's third level does."""
        level = self.themes["town"].levels[2]
        said = {i for turn in level.turns if turn.who == "you" for i in turn.items}
        self.assertLessEqual({"til_haegri", "hvad_er_langt_thangad", "geturdu_synt_mer_a_kortinu"}, said)
        probes = [p for turn in level.turns if turn.who == "partner" for line in turn.lines() for p in line.probes]
        self.assertTrue(any(p["kind"] == "duration" for p in probes), "how long it takes is picked out of the partner's answer")


if __name__ == "__main__":
    unittest.main()
