"""#270 step 3: a new form of a noun is named against the form the learner already has."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


def builder(cur, met=()):
    learner = LearnerState("is", "en", "A1")
    for i in met:
        learner.items[i] = ItemState(stage="meaning", successes=2, recalled=1)
    return Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)


class FormContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_basic_form_is_the_authored_base_else_a_met_form_of_the_noun(self):
        by = self.cur.by_id
        self.assertEqual(builder(self.cur).basic_form_of(by["koku"]), "kaka", "the authored basic word needs no item")
        self.assertIsNone(builder(self.cur).basic_form_of(by["bil"]), "«bíll» not met: nothing to name it against")
        self.assertEqual(builder(self.cur, ["bill"]).basic_form_of(by["bil"]), "bíll")
        self.assertEqual(builder(self.cur, ["hotelid"]).basic_form_of(by["hotelinu"]), "hótelið")
        self.assertIsNone(builder(self.cur, ["bill"]).basic_form_of(by["bill"]), "a form is not its own contrast")
        self.assertIsNone(builder(self.cur, ["bill"]).basic_form_of(by["hus"]), "a noun with one form has no contrast")

    def test_the_contrast_is_said_once_in_the_introduction_frame(self):
        b = builder(self.cur, ["bill"])
        sc = Script(1, "t", "is", "en")
        ex = sc.new_exercise("intro", "intro", ["bil"], "x")
        b._form_contrast(sc, ex, self.cur.by_id["bil"], "native_a")
        said = [(g.type, g.text) for g in sc.segments if g.type in ("narrate", "speak")]
        self.assertEqual(said, [("narrate", Prompts.load("en").get("form_of_base")), ("speak", "bíll")])
        sc2 = Script(1, "t", "is", "en")
        ex2 = sc2.new_exercise("intro", "intro", ["bil"], "x")
        builder(self.cur)._form_contrast(sc2, ex2, self.cur.by_id["bil"], "native_a")
        self.assertEqual(sc2.segments, [], "nothing met: nothing said")


if __name__ == "__main__":
    unittest.main()
