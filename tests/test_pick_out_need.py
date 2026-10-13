"""#303: a pick-out names what to listen for before the line."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.listening_tasks import ListeningTask, _build
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("price", "time", "count", "place", "duration")


def build(lang, task):
    cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
    b = Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
    sc = Script(1, "t", "is", lang)
    _build(b, sc, task)
    return sc


class PickOutNeedTests(unittest.TestCase):
    def test_the_need_comes_after_the_scene_and_before_the_line_in_both_languages(self):
        for lang in ("en", "ja"):
            for kind in KINDS:
                task = ListeningTask("pick_out", "x", "At a museum.", "Safnið lokar klukkan fimm.", "klukkan fimm", "five", f"pick_out_{kind}")
                spoken = [g.text for g in build(lang, task).segments if g.type in ("narrate", "speak")]
                line = spoken.index("Safnið lokar klukkan fimm.")
                self.assertEqual(spoken[0], "At a museum.")
                self.assertGreater(line, 1, f"{lang}/{kind}: the need stands before the line")
                self.assertIn(Prompts.load(lang).get(f"pick_out_need_{kind}"), spoken[:line])

    def test_a_line_with_several_pieces_names_the_one_asked_for(self):
        task = ListeningTask("pick_out", "x", "", "Safnið opnar klukkan tíu og lokar klukkan fimm.", "klukkan fimm", "five", "pick_out_time", ask="When does it close?", pieces=2)
        spoken = [g.text for g in build("en", task).segments if g.type in ("narrate", "speak")]
        self.assertEqual(spoken[0], "You want to know: When does it close? Listen.")
        self.assertEqual(spoken[1], task.line)

    def test_the_question_is_not_asked_after_the_line(self):
        task = ListeningTask("pick_out", "x", "", "Það kostar fimm.", "fimm", "five", "pick_out_price")
        spoken = [g.text for g in build("en", task).segments if g.type in ("narrate", "speak")]
        self.assertNotIn("How much is it?", spoken)


if __name__ == "__main__":
    unittest.main()
