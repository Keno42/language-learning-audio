"""#278: a scene is named by a spoken scene line, never by the theme's written `setting`."""
import unittest
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import CurriculumError, load_curriculum
from audiolesson.themes import Theme, _check, level_dialogue, load_themes

ROOT = Path(__file__).resolve().parent.parent


class SceneLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "curricula" / "is-en"
        cls.cur = load_curriculum(path)
        cls.themes = load_themes(path, cls.cur, load_cando(path))

    def test_every_theme_has_a_scene_line_in_both_languages(self):
        for t in self.themes:
            self.assertTrue(t.scene_line and t.scene_line_ja, t.id)
            self.assertNotEqual(t.scene_line, t.setting, t.id)

    def test_a_dialogue_names_its_scene_by_the_scene_line(self):
        for t in self.themes:
            for lang in ("en", "ja"):
                for n in range(len(t.levels)):
                    d = level_dialogue(t, n, lang)
                    self.assertEqual(d.setting, t.scene_line_ja if lang == "ja" else t.scene_line)
                    self.assertNotIn(d.setting, (t.setting, t.setting_ja))

    def test_a_theme_without_a_scene_line_fails_validation(self):
        t = self.themes[0]
        bare = Theme(id=t.id, scenario=t.scenario, title=t.title, setting=t.setting, levels=t.levels)
        with self.assertRaisesRegex(CurriculumError, "scene_line"):
            _check(bare)

    def test_no_narration_of_a_lesson_reads_a_setting_aloud(self):
        from tests.test_audiolesson import ListeningTaskTests
        settings = {s for t in self.themes for s in (t.setting, t.setting_ja) if s}
        spoken = 0
        for _, _, sc in ListeningTaskTests._course(12):
            for g in sc.segments:
                if g.type == "narrate" and g.text:
                    spoken += 1
                    self.assertNotIn(g.text.strip(), settings)
        self.assertGreater(spoken, 100)


if __name__ == "__main__":
    unittest.main()
