"""#445 (lesson 42, 27:50: «Sjáumst núna!» / «See you now!» had no setting): «Sjáumst {time}!» is judged sentence by sentence. «núna» is dropped (one says
«see you» on parting, never with «now»), and every other time it takes has a scene, used as the cue."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum, scene_sheet

ROOT = Path(__file__).resolve().parent.parent


class SjaumstTests(unittest.TestCase):
    def test_now_is_dropped_and_every_other_time_has_a_scene(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        c = cur.by_id["sjaumst_time"]
        self.assertIn("nuna", c.exclude_fills)
        self.assertEqual(scene_sheet(cur, ["sjaumst_time"]), [], "no sentence of the pattern left unjudged")
        self.assertIn("a_morgun", c.fill_scenes)


if __name__ == "__main__":
    unittest.main()
