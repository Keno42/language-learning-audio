"""#528 step 1. The owner, 2026-11-12: more numbers, colours and words is a memory game; «I want to feel a coach who makes me choose the right verb
form». Of 256 sentences of the course that open with a subject pronoun, 207 say «ég». A sentence the learner says with «ég» is said with other
subjects, the verb's form named, and each asked: the verb is practised as the subject's choice."""
import dataclasses
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import SUBJECTS, CurriculumError, _check_subjects, load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
ROOT = Path(__file__).resolve().parent.parent
VERBS = ("eg_fer", "eg_kem", "eg_vil", "eg_tharf", "eg_aetla_ad", "eg_tala", "eg_by_i", "eg_er_i_frii")


class SubjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")

    def test_eight_sentences_have_their_other_subjects_in_both_languages(self):
        for lang in ("en", "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            for item_id in VERBS:
                item = cur.by_id[item_id]
                self.assertEqual(sorted(item.subjects), ["she", "we", "you"], item_id)
                self.assertTrue(all(item.subjects_meaning[k] for k in item.subjects), (lang, item_id))
                _check_subjects(item)
        self.assertEqual(self.cur.by_id["eg_fer"].subject_verbs, {"i": "fer", "we": "förum", "she": "fer", "you": "ferð"})

    def test_the_fields_are_checked(self):
        item = self.cur.by_id["eg_fer"]
        for bad in (
            {"subjects": {"we": item.subjects["we"]}},  # one subject is no choice
            {"subjects": {**item.subjects, "we": "Hún förum á morgun."}},  # the line opens with its pronoun
            {"subject_verbs": {**item.subject_verbs, "we": "fara"}},  # the verb form is in its line
            {"subjects_base": "Við förum á morgun."},  # the base is the «ég» sentence
            {"subjects_meaning": {"we": "x"}},
        ):
            with self.subTest(bad=bad), self.assertRaises(CurriculumError):
                _check_subjects(dataclasses.replace(item, **bad))
        with self.assertRaises(CurriculumError):
            _check_subjects(dataclasses.replace(self.cur.by_id["kaffi"], subjects=item.subjects, subjects_meaning=item.subjects_meaning,
                                                subject_verbs=item.subject_verbs, subjects_base=item.subjects_base))

    def test_the_exercise_sets_the_sentences_side_by_side_names_the_verb_and_asks_each(self):
        for lang, stays in (("en", "The verb stays"), ("ja", "のままです")):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            b = Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
            sc = Script(1, "t", "is", lang)
            ex = b.subject_choice(sc, cur.by_id["eg_fer"], ["we", "she"])
            self.assertEqual((ex.kind, ex.stage, ex.item_ids), ("model", "subjects", ["eg_fer"]))
            spoken = [g.text for g in sc.segments if g.type == "speak"]
            self.assertEqual(spoken[0], "Ég fer á morgun.", "the sentence the learner says comes first")
            self.assertIn("Við förum á morgun.", spoken)
            self.assertIn("förum", spoken, "the verb's form is named")
            narrated = " ".join(g.text for g in sc.segments if g.type == "narrate")
            self.assertIn(stays, narrated, "«Hún fer»: the form does not change, and the lesson says so")
            self.assertEqual([g.text for g in sc.segments if g.type == "answer"], ["Hún fer á morgun.", "Við förum á morgun."], "each asked, in the other order")
            self.assertEqual(sum(1 for g in sc.segments if g.type == "pause" and g.role == "answer"), 2)

    def lesson(self, completed: int, known_until: str = "tvaer", themes: bool = False):
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id[known_until].order and not i.command:
                learner.items[i.id] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=30, last_outcome="recalled",
                                                due=(TODAY + timedelta(days=60)).isoformat(), last_practiced=(TODAY - timedelta(days=5)).isoformat())
        learner.lessons_completed = completed
        cfg = PlanConfig(minutes=30, seed=1)
        if themes:  # as `generate` plans: a theme's exchange, whose goal is said after the opening
            from audiolesson.cando import load_cando
            from audiolesson.themes import load_themes, scenario_order

            scenarios = load_cando(ROOT / "curricula" / "is-en", self.cur)
            cfg = PlanConfig(minutes=30, seed=1, themes=load_themes(ROOT / "curricula" / "is-en", self.cur, scenarios), theme_scenarios=scenario_order(scenarios, ()))
        return Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)

    def test_a_lesson_plays_one_and_the_sentences_and_subjects_take_turns(self):
        seen = []
        for completed in (30, 31, 32):
            planner = self.lesson(completed)
            cands = planner.subject_candidates()
            self.assertTrue(cands, "the learner says sentences the course holds with other subjects")
            sc = planner.build()
            played = [e for e in sc.exercises if e.stage == "subjects"]
            self.assertEqual(len(played), 1, completed)
            self.assertEqual(sc.meta["subject_choices"], [played[0].label])
            # review of #531: a spare today's-items turn played it at 6:35, before its scheduled time (13:30 of 30 minutes)
            self.assertGreaterEqual(played[0].start, PlanConfig().subject_choice_at * 30 * 60, completed)
            seen.append(played[0].label)
        self.assertEqual(len(set(seen)), 3, seen)

    def test_the_goal_names_the_form_work_and_the_closing_asks_it_once_more(self):
        """#528 step 3 (the owner: «a coach who applies the right load»): the intent is said, not only practised. The goal exercise ends on the
        day's form work, and the last question before the lesson's closing words is one of the choice's sentences, the one whose verb changes."""
        planner = self.lesson(30, themes=True)
        sc = planner.build()
        (choice,) = [e for e in sc.exercises if e.stage == "subjects"]
        goal = next(e for e in sc.exercises if e.label == "lesson goal")
        said = [g.text for g in sc.segments if g.exercise == goal.index and g.type == "narrate"]
        self.assertEqual(said[-2:], ["Today's form work:", "One sentence you know, said of someone else."], said)
        self.assertEqual(sc.segments[max(k for k, g in enumerate(sc.segments) if g.exercise == goal.index)].type, "pause", "the goal still ends on its gap")
        (again,) = [e for e in sc.exercises if e.stage == "subjects_again"]
        self.assertGreater(again.index, choice.index)
        self.assertEqual(sc.exercises[again.index + 1].kind, "closing")
        item = self.cur.by_id[again.item_ids[0]]
        sentence = again.label.removeprefix("subjects: ")
        self.assertIn(sentence, choice.label)
        key = next(k for k, v in item.subjects.items() if v == sentence)
        changing = [k for k, v in item.subjects.items() if v in choice.label and item.subject_verbs[k].lower() != item.subject_verbs["i"].lower()]
        self.assertTrue(not changing or key in changing, (sentence, changing))
        answers = [g.text for g in sc.segments if g.exercise == again.index and g.type == "answer"]
        self.assertEqual(answers, [sentence])

    def test_a_lesson_with_no_subject_choice_says_no_form_work(self):
        fresh = Planner(self.cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        sc = fresh.build()
        self.assertEqual([e for e in sc.exercises if e.stage in ("subjects", "subjects_again")], [])
        self.assertFalse(any(g.text and "form work" in g.text for g in sc.segments if g.type == "narrate"))

    def test_a_spare_turn_never_plays_it_before_its_scheduled_time(self):
        """Review of #531: the today's-items turn of spare time played the subject choice with no look at the clock (6:35 in the reviewer's lesson;
        here, with a small target of new material, 13:10 and 13:04 of a 13:30 schedule). The turn waits for the time the main loop waits for."""
        for completed in (30, 31):
            planner = self.lesson(completed)
            planner.cfg = dataclasses.replace(planner.cfg, new_items=1, new_target=2.0)
            sc = planner.build()
            (played,) = [e for e in sc.exercises if e.stage == "subjects"]
            self.assertGreaterEqual(played.start, planner.cfg.subject_choice_at * 30 * 60, completed)

    def test_only_a_sentence_the_learner_says_is_set(self):
        planner = self.lesson(30)
        met = {i.id for i, _ in planner.subject_candidates()}
        self.assertTrue(met <= set(VERBS))
        open_one = sorted(met)[0]
        planner.learner.items[open_one].last_outcome = "not_recalled"
        self.assertNotIn(open_one, {i.id for i, _ in planner.subject_candidates()}, "a sentence that is failing is not varied")
        fresh = Planner(self.cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        self.assertEqual(fresh.subject_candidates(), [])
        self.assertEqual(sorted(SUBJECTS), ["he", "she", "they", "we", "you"])


if __name__ == "__main__":
    unittest.main()
