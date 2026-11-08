"""#439 step 2 (the owner after lessons 44/45: «Ég er …», «Ég er ekki …», «Ertu …» teach no gender): the learner had a gendered word's two forms only as
the speaker's own («As a man: Say you're hungry.»). Once a lesson, a gendered line they know is said of him and of her («Hann er svangur.», «Hún er
svöng.»), whom each is said of named once, and each asked again."""
import dataclasses
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import CurriculumError, _check_said_of, load_curriculum, said_of_words
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent


def _known(learner, ids, open_=False):
    for i in ids:
        learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30,
                                     last_outcome="not_recalled" if open_ else "recalled", due=(TODAY + timedelta(days=60)).isoformat(),
                                     last_practiced=(TODAY - timedelta(days=5)).isoformat())


class SaidOfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_the_words_a_gendered_line_changes(self):
        self.assertEqual(said_of_words(self.cur.by_id["eg_er_svong"]), ("svangur", "svöng"))
        self.assertEqual(said_of_words(self.cur.by_id["eg_er_sein"]), ("seinn", "sein"))

    def test_the_load_check(self):
        item = self.cur.by_id["eg_er_svong"]
        _check_said_of(item)
        for bad in ({"m": "Hún er svangur.", "f": "Hún er svöng."},  # the line for him starts with «Hann»
                    {"m": "Hann er svöng.", "f": "Hún er svöng."},  # and says his form
                    {"m": "Hann er svangur."}):  # both lines
            with self.assertRaises(CurriculumError, msg=bad):
                _check_said_of(dataclasses.replace(item, said_of=bad))
        with self.assertRaises(CurriculumError):
            _check_said_of(dataclasses.replace(self.cur.by_id["tvo_kaffi"], said_of=item.said_of, said_of_meaning=item.said_of_meaning))

    def test_the_exercise_names_whom_and_asks_each_again(self):
        for lang, intro, man in (("en", "it follows the person it is said of", "Said of a man:"), ("ja", "誰のことを言うかで", "男性のことなので")):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            b = Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
            sc = Script(1, "t", "is", lang)
            ex = b.said_of_choice(sc, cur.by_id["eg_er_svong"])
            self.assertEqual((ex.kind, ex.stage), ("model", "said_of"))
            narrated = " ".join(g.text for g in sc.segments if g.type == "narrate")
            self.assertIn(intro, narrated)
            self.assertIn(man, narrated)
            spoken = [g.text for g in sc.segments if g.type == "speak"]
            self.assertEqual(spoken, ["Hann er svangur.", "svangur", "Hún er svöng.", "svöng"], lang)
            self.assertEqual({g.speaker for g in sc.segments if g.type in ("speak", "answer")}, {"native_a"}, "one voice: the speaker is not what changes")
            answers = [g.text for g in sc.segments if g.type == "answer"]
            self.assertEqual(answers, ["Hún er svöng.", "Hann er svangur."], "asked again in the other order")
            prompts = [g.text for g in sc.segments if g.type == "narrate"][-2:]
            self.assertTrue(all(m.rstrip("。.") in " ".join(prompts) for m in cur.by_id["eg_er_svong"].said_of_meaning.values()), (lang, prompts))

    def test_a_lesson_plays_one_once_a_gendered_line_is_known(self):
        learner = LearnerState("is", "en", "A1")
        _known(learner, [i.id for i in self.cur.items if i.order < self.cur.by_id["tvaer"].order])
        learner.lessons_completed = 30
        sc = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_items=2, new_target=2.0), today=TODAY).build()
        said = [e for e in sc.exercises if e.stage == "said_of"]
        self.assertEqual(len(said), 1)
        self.assertEqual(sc.meta["said_of_choices"], [said[0].label])
        self.assertTrue(self.cur.by_id[said[0].item_ids[0]].said_of)

    def test_none_while_the_line_is_unmet_or_failing(self):
        learner = LearnerState("is", "en", "A1")
        p = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY)
        self.assertEqual(p.said_of_candidates(), [])
        _known(learner, ["eg_er_svong"], open_=True)
        p = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY)
        self.assertEqual(p.said_of_candidates(), [], "a failing line is practised as itself first")
        _known(learner, ["eg_er_svong"])
        p = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY)
        self.assertEqual([i.id for i in p.said_of_candidates()], ["eg_er_svong"])


if __name__ == "__main__":
    unittest.main()
