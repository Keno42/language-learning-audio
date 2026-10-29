"""#427 (lesson 40): conversational contexts and cue–answer pairs. «Is it normal to ask someone's age straight away, or to say you're single
and live alone?»; «here with your family?» answered by «I'm married»; «Velkomin!» said to the learner's line in a man's voice; a catch task
opening on small talk's closing line with nothing before it."""
import unittest
from pathlib import Path

import tests.test_audiolesson as course
from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.themes import load_themes

ROOT = Path(__file__).resolve().parent.parent


class Lesson40ContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        cls.themes = load_themes(ROOT / "curricula" / "is-en", cls.cur, load_cando(ROOT / "curricula" / "is-en", cls.cur))

    def test_the_married_cues_ask_whether_you_are_married(self):
        gift = self.cur.by_id["eg_er_gift"]
        self.assertNotIn("family", gift.situations[0] if gift.situations else gift.situation)
        self.assertIn("married", gift.situation)
        cue_setups = [i.partner_cue_setup for i in self.cur.items if i.partner_cue_after == "eg_er_gift"]
        self.assertTrue(cue_setups and all("married" in c and "family" not in c for c in cue_setups), cue_setups)

    def test_no_welcome_agrees_with_one_learner(self):
        """«Velkomin» agrees with a woman or a group; said to the learner alone it may meet a man's voice. A table for two («Gott kvöld.
        Velkomin!») is a group and keeps it."""
        kynning = next(d for d in self.cur.dialogues if d.id == "kynning")
        self.assertNotIn("Velkomin", " ".join(t.partner or "" for t in kynning.turns))
        self.assertFalse([i.id for i in self.cur.items if "Velkomin" in (i.partner_cue or "") and "þú" in (i.partner_cue or "")])

    def test_small_talk_four_opens_its_questions(self):
        level = next(t for t in self.themes if t.id == "smalltalk").levels[3]
        self.assertEqual(level.turns[0].who, "partner")
        self.assertIn("afmæli", level.turns[0].say, "her birthday opens the age")
        said = " ".join(t.say for t in level.turns if t.who == "partner")
        self.assertNotIn("einhleyp", said, "she no longer volunteers that she is single and lives alone")

    def test_every_listening_task_names_its_scene_the_lessons_own_included(self):
        named = 0
        for _, _, sc in course.ListeningTaskTests._course(20):
            for e in sc.exercises:
                if e.kind not in ("pick_out", "catch_unknown"):
                    continue
                first = next(s for s in sc.segments if s.exercise == e.index and s.type in ("narrate", "speak", "answer"))
                self.assertEqual(first.type, "narrate", (sc.lesson_number, e.label, first.text))
                named += 1
        self.assertGreater(named, 5)


if __name__ == "__main__":
    unittest.main()
