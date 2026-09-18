"""Structural guarantees of a generated lesson. Run: python -m unittest -v"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import CurriculumError, curriculum_from_dict, load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.render import load_profile, render_script
from audiolesson.render.audio import read_wav
from audiolesson.script import Script
from audiolesson.stages import ladder_for
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
CURRICULUM = ROOT / "curricula" / "fr-en-a1.toml"
TODAY = date(2026, 9, 18)


def build(learner: LearnerState, minutes: float = 15, today: date = TODAY, **cfg) -> Script:
    cur = load_curriculum(CURRICULUM)
    prompts = Prompts.load(cur.known_lang)
    planner = Planner(cur, learner, prompts, Timing(level="A1"), PlanConfig(minutes=minutes, seed=1, **cfg), today=today)
    return planner.build()


def fresh() -> LearnerState:
    return LearnerState("fr", "en", "A1")


def course(n_lessons: int, minutes: float = 15) -> tuple[LearnerState, list[Script]]:
    learner = fresh()
    scripts = []
    day = TODAY
    for _ in range(n_lessons):
        sc = build(learner, minutes, today=day)
        apply_to_learner(sc, learner, day)
        scripts.append(sc)
        day += timedelta(days=2)
    return learner, scripts


class CurriculumTests(unittest.TestCase):
    def test_sample_curriculum_loads(self):
        cur = load_curriculum(CURRICULUM)
        self.assertGreater(len(cur.items), 30)
        self.assertGreaterEqual(len(cur.dialogues), 3)

    def test_validation_catches_bad_references(self):
        raw = {
            "curriculum": {"name": "x", "target_lang": "fr", "known_lang": "en"},
            "items": [{"id": "a", "kind": "phrase", "target": "A.", "meaning": "A.", "prereqs": ["missing"]}],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)

    def test_construction_needs_slot_tag(self):
        raw = {
            "curriculum": {"name": "x", "target_lang": "fr", "known_lang": "en"},
            "items": [{"id": "c", "kind": "construction", "target": "Je veux {x}.", "meaning": "I want {x}."}],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)

    def test_backward_chunks_grow_from_the_end(self):
        cur = load_curriculum(CURRICULUM)
        it = cur.item("je_ne_comprends_pas")
        chunks = it.backward_chunks()
        self.assertEqual(chunks[-1], it.target)
        for a, b in zip(chunks, chunks[1:]):
            self.assertTrue(b.rstrip(".?! ").endswith(a.rstrip(".?! ")), (a, b))


class LessonStructureTests(unittest.TestCase):
    def setUp(self):
        self.script = build(fresh())

    def test_every_answer_pause_precedes_its_answer(self):
        """Recall before answer: after each answer-pause the next spoken thing is the model answer."""
        segs = self.script.segments
        for i, s in enumerate(segs):
            if s.type == "pause" and s.role == "answer":
                nxt = next(x for x in segs[i + 1 :] if x.type != "pause")
                self.assertEqual(nxt.type, "answer", f"segment {i}: pause not followed by answer but {nxt}")

    def test_no_answer_is_spoken_right_before_its_own_prompt_pause(self):
        """The model answer must not be played immediately before the learner is asked to produce it
        (that would be imitation, not recall) — except inside an introduction, where repeat pauses are used."""
        segs = self.script.segments
        for i, s in enumerate(segs):
            if s.type == "pause" and s.role == "answer":
                ex = self.script.exercises[s.exercise]
                if ex.kind == "intro":
                    continue
                answer = next(x for x in segs[i + 1 :] if x.type != "pause")
                prev_speech = next((x for x in reversed(segs[:i]) if x.type in ("speak", "answer")), None)
                if prev_speech is not None and prev_speech.exercise == s.exercise:
                    self.assertNotEqual(prev_speech.text, answer.text, f"segment {i} reveals the answer before the pause")

    def test_learner_speaks_a_lot(self):
        s = self.script.summary()
        self.assertGreater(s["active_ratio"], 0.4)
        self.assertGreater(s["prompts"], 30)

    def test_length_close_to_requested(self):
        self.assertAlmostEqual(self.script.total_duration / 60, 15, delta=2.5)

    def test_new_items_are_reactivated_at_expanding_gaps(self):
        exposures = self.script.meta["exposures"]
        for item_id in self.script.meta["new_items"]:
            stages = exposures[item_id]
            self.assertGreaterEqual(len(stages), 3, item_id)  # intro + reactivations + closing
            self.assertEqual(stages[0], "intro")
            positions = [e.index for e in self.script.exercises if e.item_ids and e.item_ids[0] == item_id]
            gaps = [b - a for a, b in zip(positions, positions[1:])]
            self.assertTrue(all(g >= 1 for g in gaps), positions)
            self.assertLess(gaps[0], gaps[-1] + 1, f"{item_id}: gaps should widen {gaps}")

    def test_no_item_twice_in_a_row(self):
        prev: list[str] = []
        for ex in self.script.exercises:
            if ex.kind in ("opening", "closing"):
                continue
            if prev and ex.item_ids:
                self.assertNotEqual(prev[0], ex.item_ids[0], f"{ex.index}: same item twice in a row")
            prev = ex.item_ids

    def test_lesson_ends_with_todays_material(self):
        last = [e for e in self.script.exercises if e.kind == "recall"][-1]
        self.assertIn(last.item_ids[0], self.script.meta["new_items"])

    def test_stages_get_harder_within_lesson(self):
        cur = load_curriculum(CURRICULUM)
        for item_id, stages in self.script.meta["exposures"].items():
            it = cur.item(item_id)
            ladder = self.script.meta["ladders"][item_id]
            idx = [ladder.index(s) for s in stages if s in ladder]
            self.assertEqual(idx, sorted(idx), f"{item_id}: {stages}")

    def test_hard_phrase_is_built_backwards(self):
        text = self.script.transcript()
        self.assertIn("build it up from the end", text)
        self.assertIn("**Speaker A:** plaît", text)

    def test_script_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.json"
            self.script.save(p)
            back = Script.load(p)
            self.assertEqual(len(back.segments), len(self.script.segments))
            self.assertAlmostEqual(back.total_duration, self.script.total_duration, places=3)


class CourseTests(unittest.TestCase):
    def test_lessons_form_a_sequence(self):
        learner, scripts = course(6)
        self.assertEqual(learner.lessons_completed, 6)
        seen = set()
        for sc in scripts:
            for i in sc.meta["new_items"]:
                self.assertNotIn(i, seen, "item introduced twice")
                seen.add(i)
        later = scripts[3]
        self.assertGreater(len(later.meta["reviewed_items"]), 3)
        self.assertTrue(any(sc.meta["dialogues"] for sc in scripts[2:]), "dialogues should appear once material is known")

    def test_generative_recombination_appears(self):
        _, scripts = course(4)
        kinds = {e.kind for sc in scripts for e in sc.exercises}
        self.assertIn("generative", kinds)
        gen_labels = [e.label for sc in scripts for e in sc.exercises if e.kind == "generative"]
        self.assertTrue(any("Je voudrais un thé" in l or "Je voudrais de l'eau" in l for l in gen_labels), gen_labels)

    def test_prerequisites_respected(self):
        cur = load_curriculum(CURRICULUM)
        learner, scripts = course(8)
        intro_lesson = {}
        for sc in scripts:
            for i in sc.meta["new_items"]:
                intro_lesson[i] = sc.lesson_number
        for i, n in intro_lesson.items():
            for p in cur.item(i).prereqs:
                self.assertLessEqual(intro_lesson.get(p, 999), n, f"{i} introduced before prereq {p}")

    def test_failed_report_brings_item_back(self):
        learner, scripts = course(2)
        item = scripts[0].meta["new_items"][0]
        before = learner.items[item].due
        learner.report([item], [], TODAY + timedelta(days=3), 2)
        self.assertLess(learner.items[item].due, before)
        self.assertEqual(learner.items[item].failures, 1)
        nxt = build(learner, today=TODAY + timedelta(days=4))
        self.assertIn(item, nxt.meta["reviewed_items"])

    def test_topics_are_preferred(self):
        sc = build(fresh(), topics=["directions"])
        cur = load_curriculum(CURRICULUM)
        on_topic = [i for i in sc.meta["new_items"] if "directions" in cur.item(i).topics]
        self.assertGreaterEqual(len(on_topic), len(sc.meta["new_items"]) // 2)

    def test_learner_state_roundtrip(self):
        learner, _ = course(2)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "l.json"
            learner.save(p)
            back = LearnerState.load(p)
            self.assertEqual(back.to_dict(), learner.to_dict())


class JapaneseInstructorTests(unittest.TestCase):
    def test_fr_ja_curriculum_builds_a_lesson_in_japanese(self):
        cur = load_curriculum(ROOT / "curricula" / "fr-ja-a1.toml")
        en = load_curriculum(CURRICULUM)
        self.assertEqual([i.id for i in cur.items], [i.id for i in en.items], "derived curriculum must keep ids in sync")
        learner = LearnerState("fr", "ja", "A1")
        sc = Planner(cur, learner, Prompts.load("ja"), Timing(level="A1"), PlanConfig(minutes=5, seed=1), today=TODAY).build()
        narr = [s.text for s in sc.segments if s.type == "narrate"]
        self.assertTrue(all(any(ord(ch) > 0x3000 for ch in n) for n in narr), "every instructor line should be Japanese")
        self.assertNotIn("。」", "".join(narr))
        answers = [s.text for s in sc.segments if s.type == "answer"]
        self.assertTrue(answers and all(ord(a[0]) < 0x3000 for a in answers), "answers stay in French")

    def test_alternatives_are_sometimes_spoken(self):
        learner, scripts = course(8)
        alts = [s for sc in scripts for s in sc.segments if s.role == "alternative"]
        self.assertTrue(alts, "an alternative answer should be spoken at least once over a course")
        for sc in scripts:
            for i, s in enumerate(sc.segments):
                if s.role == "alternative":
                    self.assertEqual(sc.segments[i - 1].type, "narrate")


class TimingTests(unittest.TestCase):
    def test_pause_grows_with_length_and_level(self):
        t = Timing(level="A2")
        self.assertLess(t.answer_pause("Oui.", "fr"), t.answer_pause("Je voudrais un café avec du lait.", "fr"))
        self.assertLess(Timing(level="B1").answer_pause("Où est la gare ?", "fr"), Timing(level="A0").answer_pause("Où est la gare ?", "fr"))

    def test_french_question_mark_is_not_a_word(self):
        t = Timing()
        self.assertEqual(t.answer_pause("Où est la gare ?", "fr"), t.answer_pause("Où est la gare.", "fr"))

    def test_ladder_skips_unavailable_stages(self):
        self.assertNotIn("situation", ladder_for("phrase", has_situation=False, in_dialogue=False, recombinable=False, word_count=3))
        self.assertNotIn("cloze", ladder_for("phrase", has_situation=True, in_dialogue=False, recombinable=False, word_count=1))


class RenderTests(unittest.TestCase):
    def test_stub_render_matches_script_pauses_exactly(self):
        sc = build(fresh(), minutes=2)
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(None, "stub")
            prof.mp3 = False
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
            clip = read_wav(Path(td) / "l.wav")
            self.assertAlmostEqual(clip.seconds, cues["duration_s"], delta=0.2)
            pauses = [c for c in cues["segments"] if c["type"] == "pause" and c["role"] == "answer"]
            script_pauses = [s.duration for s in sc.segments if s.type == "pause" and s.role == "answer"]
            self.assertEqual([p["dur"] for p in pauses], [round(x, 2) for x in script_pauses])

    def test_pause_multiplier_scales_only_learner_pauses(self):
        sc = build(fresh(), minutes=2)
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(None, "stub")
            prof.mp3 = False
            prof.pause_multiplier = 2.0
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
            answers = [c["dur"] for c in cues["segments"] if c["type"] == "pause" and c["role"] == "answer"]
            expected = [round(s.duration * 2, 2) for s in sc.segments if s.type == "pause" and s.role == "answer"]
            self.assertEqual(answers, expected)

    @unittest.skipUnless(os.system("espeak-ng --version >/dev/null 2>&1") == 0, "espeak-ng not installed")
    def test_espeak_render(self):
        sc = build(fresh(), minutes=3)
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(ROOT / "profiles" / "espeak.toml")
            prof.mp3 = False
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
            self.assertGreater(cues["duration_s"], 60)


class CliTests(unittest.TestCase):
    def test_generate_report_status(self):
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            learner = Path(td) / "learner.json"
            rc = main(["generate", "-c", str(CURRICULUM), "-l", str(learner), "-o", td, "-m", "3", "--no-audio", "--date", "2026-09-18"])
            self.assertEqual(rc, 0)
            self.assertTrue((Path(td) / "lesson-001.script.json").exists())
            self.assertTrue((Path(td) / "lesson-001.transcript.md").exists())
            plan = json.loads((Path(td) / "lesson-001.plan.json").read_text())
            first = plan["new_items"][0]["id"]
            self.assertEqual(main(["report", "-l", str(learner), "--failed", first, "--date", "2026-09-19"]), 0)
            self.assertEqual(main(["status", "-l", str(learner), "-c", str(CURRICULUM)]), 0)
            rc = main(["generate", "-c", str(CURRICULUM), "-l", str(learner), "-o", td, "-m", "3", "--provider", "stub", "--date", "2026-09-20"])
            self.assertEqual(rc, 0)
            self.assertTrue((Path(td) / "lesson-002.wav").exists())


if __name__ == "__main__":
    unittest.main()
