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
from audiolesson.stages import ladder_for, stage_index
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
CURRICULUM = ROOT / "curricula" / "fr-en-a1.toml"
TODAY = date(2026, 9, 18)


def build(learner: LearnerState, minutes: float = 15, today: date = TODAY, **cfg) -> Script:
    cur = load_curriculum(CURRICULUM)
    prompts = Prompts.load(cur.known_lang)
    planner = Planner(cur, learner, prompts, Timing(level="A1"), PlanConfig(minutes=minutes, seed=1, **cfg), today=today)
    return planner.build()


_LADDERS: dict[str, list[str]] = {}


def learner_ladder(item_id: str) -> list[str]:
    """Ladder of an item in the sample curriculum, as the planner computes it."""
    if not _LADDERS:
        cur = load_curriculum(CURRICULUM)
        planner = Planner(cur, fresh(), Prompts.load("en"), Timing(), PlanConfig(), today=TODAY)
        _LADDERS.update({i.id: planner.ladder(i) for i in cur.items})
    return _LADDERS[item_id]


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

    def test_directory_curriculum_loads_and_is_large(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertGreater(len(cur.items), 900)
        self.assertGreater(len(cur.dialogues), 25)
        # every construction has at least two possible fills, so recombination is always possible
        for c in cur.items:
            if c.kind == "construction":
                for slot, tag in c.slots.items():
                    self.assertGreaterEqual(len(cur.items_with_tag(tag)), 2, f"{c.id}.{slot}")

    def test_notes_follow_related_items_and_are_rationed(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertGreaterEqual(len(cur.notes), 40)
        learner = LearnerState("is", "en", "A1")
        learner.feedback_mode = "auto"
        day = TODAY
        heard: list[str] = []
        for _ in range(12):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=2), today=day).build()
            notes = [e for e in sc.exercises if e.kind == "note"]
            self.assertLessEqual(len(notes), 2)
            for e in notes:
                note = cur.note_by_id[e.label.split(": ")[1]]
                self.assertNotIn(note.id, heard, "no note repeats while unheard notes remain")
                heard.append(note.id)
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        self.assertGreater(len(heard), 4)
        self.assertEqual(sum(learner.notes_heard.values()), len(heard))

    def test_full_course_over_the_icelandic_set(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        learner.feedback_mode = "auto"
        day = TODAY
        for _ in range(30):
            pace, _why = learner.suggest_pace(30, day)
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=pace, seed=1), today=day).build()
            apply_to_learner(sc, learner, day)
            learner.pace = pace
            day += timedelta(days=1)
        self.assertGreaterEqual(sc.total_duration / 60, 27)
        self.assertLessEqual(len(sc.meta["dialogues"]), 3)
        self.assertGreater(len(learner.items), 150)

    def test_backward_chunks_grow_from_the_end(self):
        cur = load_curriculum(CURRICULUM)
        it = cur.item("je_ne_comprends_pas")
        chunks = it.backward_chunks()
        self.assertEqual(chunks[-1], it.target)
        for a, b in zip(chunks, chunks[1:]):
            self.assertTrue(b.rstrip(".?! ").endswith(a.rstrip(".?! ")), (a, b))


class LessonStructureTests(unittest.TestCase):
    def setUp(self):
        self.script = build(fresh(), new_items=8)  # a full first lesson (the default pace would make it short)

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

    def test_first_lesson_at_default_pace_is_short_not_padded(self):
        sc = build(fresh())  # 15 min, pace 3: at most 5 new items, nothing to review → ends early
        self.assertLessEqual(len(sc.meta["new_items"]), 5)
        self.assertLess(sc.total_duration / 60, 12)

    def test_later_lessons_fill_the_requested_time(self):
        _, scripts = course(8, minutes=30)
        minutes = [round(sc.total_duration / 60, 1) for sc in scripts]
        # once there is enough material the requested length is reached; the sample curriculum
        # (47 items) is exhausted around lesson 7, after which review-only lessons end early
        self.assertGreaterEqual(max(minutes), 24, minutes)
        self.assertLess(minutes[0], minutes[4], minutes)

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

    def test_dialogues_get_longer_each_time(self):
        _, scripts = course(10)
        seen: dict[str, list[int]] = {}
        for sc in scripts:
            for e in sc.exercises:
                if e.kind == "dialogue":
                    dlg_id = e.label.split(":")[1].split("(")[0].strip()
                    n_turns = sum(1 for s in sc.segments if s.exercise == e.index and s.type == "pause" and s.role == "answer")
                    seen.setdefault(dlg_id, []).append(n_turns)
        self.assertTrue(seen)
        for dlg_id, lengths in seen.items():
            self.assertEqual(lengths, sorted(lengths), f"{dlg_id}: {lengths}")
            if len(lengths) >= 3:
                self.assertGreater(lengths[-1], lengths[0], f"{dlg_id}: {lengths}")

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

    def test_review_never_lowers_a_stage(self):
        learner, _ = course(8)
        for item_id, st in learner.items.items():
            top_seen = max(
                (stage_index(l, s) for h in st.history for s in h["stages"] for l in [learner_ladder(item_id)] if s in l),
                default=0,
            )
            self.assertEqual(stage_index(learner_ladder(item_id), st.stage), top_seen, item_id)

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


class PacingTests(unittest.TestCase):
    def test_default_pace_is_about_one_per_five_minutes(self):
        learner = fresh()
        self.assertEqual(learner.suggest_pace(30, TODAY)[0], 6)
        self.assertEqual(learner.suggest_pace(15, TODAY)[0], 3)
        self.assertEqual(learner.suggest_pace(90, TODAY)[0], 10)

    def test_pace_never_rises_without_feedback(self):
        learner = fresh()
        day = TODAY
        for _ in range(6):
            pace, _why = learner.suggest_pace(30, day)
            sc = build(learner, 30, today=day, new_items=pace)
            apply_to_learner(sc, learner, day)
            learner.pace = pace
            day += timedelta(days=1)
        self.assertEqual(learner.pace, 6)
        self.assertIn("no feedback", learner.suggest_pace(30, day)[1])

    def test_pace_rises_on_clean_reports_and_falls_on_failures(self):
        learner = fresh()
        day = TODAY
        pace, _ = learner.suggest_pace(30, day)
        sc = build(learner, 30, today=day, new_items=pace)
        apply_to_learner(sc, learner, day)
        learner.pace = pace
        learner.report([], [], day)  # listened, all good
        day += timedelta(days=1)
        up, why = learner.suggest_pace(30, day)
        self.assertEqual(up, 7, why)
        sc = build(learner, 30, today=day, new_items=up)
        apply_to_learner(sc, learner, day)
        learner.pace = up
        new = sc.meta["new_items"]
        learner.report(new[: max(2, len(new) // 2)], [], day)  # half of them failed
        day += timedelta(days=1)
        down, why = learner.suggest_pace(30, day)
        self.assertEqual(down, 6, why)

    def test_backlog_slows_the_pace(self):
        learner, _ = course(6, minutes=30)
        # pretend a long break: everything is overdue
        late = TODAY + timedelta(days=60)
        learner.pace = 6
        pace, why = learner.suggest_pace(15, late)  # a short lesson cannot absorb the backlog
        self.assertEqual(pace, 5, why)
        self.assertIn("due", why)
        pace, why = learner.suggest_pace(60, late)  # a long one can
        self.assertEqual(pace, 6, why)

    def test_intervals_grow_with_elapsed_time_not_lesson_count(self):
        learner = fresh()
        day = TODAY
        for _ in range(40):  # daily lessons for 40 days on a small curriculum: everything gets reviewed constantly
            sc = build(learner, 30, today=day)
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        for item_id, st in learner.items.items():
            self.assertLessEqual(st.interval_days, 40 * 3, item_id)
            self.assertLessEqual(date.fromisoformat(st.due), day + timedelta(days=200), item_id)
        # something learned in the first lessons should by now be on a multi-week interval
        first = learner.lessons[0]["new_items"][0]
        self.assertGreaterEqual(learner.items[first].interval_days, 7)

    def test_auto_mode_steps_up_every_few_lessons_without_reports(self):
        learner = fresh()
        learner.feedback_mode = "auto"
        day = TODAY
        paces = []
        for _ in range(8):
            pace, why = learner.suggest_pace(30, day)
            paces.append(pace)
            sc = build(learner, 30, today=day, new_items=pace)
            apply_to_learner(sc, learner, day)
            learner.pace = pace
            day += timedelta(days=1)
        self.assertEqual(paces[:3], [6, 6, 6], paces)  # first step only after 3 completed lessons
        self.assertEqual(paces[3], 7, paces)
        self.assertEqual(paces[6], 8, paces)

    def test_auto_mode_still_slows_on_reported_failures(self):
        learner = fresh()
        learner.feedback_mode = "auto"
        day = TODAY
        pace, _ = learner.suggest_pace(30, day)
        sc = build(learner, 30, today=day, new_items=pace)
        apply_to_learner(sc, learner, day)
        learner.pace = pace
        new = sc.meta["new_items"]
        learner.report(new[: len(new) // 2], [], day)
        pace2, why = learner.suggest_pace(30, day + timedelta(days=1))
        self.assertEqual(pace2, 5, why)

    def test_report_defaults_to_latest_lesson(self):
        learner, scripts = course(2)
        changed = learner.report([], [], TODAY)
        self.assertEqual(changed["lesson"], 2)
        self.assertEqual(learner.reported, [2])


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
        sc = build(fresh(), minutes=5)
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(None, "stub")
            prof.mp3 = False
            prof.fit = False
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
            clip = read_wav(Path(td) / "l.wav")
            self.assertAlmostEqual(clip.seconds, cues["duration_s"], delta=0.2)
            pauses = [c for c in cues["segments"] if c["type"] == "pause" and c["role"] == "answer"]
            script_pauses = [s.duration for s in sc.segments if s.type == "pause" and s.role == "answer"]
            self.assertEqual([p["dur"] for p in pauses], [round(x, 2) for x in script_pauses])

    def test_pause_multiplier_scales_only_learner_pauses(self):
        sc = build(fresh(), minutes=5)
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(None, "stub")
            prof.mp3 = False
            prof.fit = False
            prof.pause_multiplier = 2.0
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
            answers = [c["dur"] for c in cues["segments"] if c["type"] == "pause" and c["role"] == "answer"]
            expected = [round(s.duration * 2, 2) for s in sc.segments if s.type == "pause" and s.role == "answer"]
            self.assertEqual(answers, expected)

    def test_fit_lands_on_the_requested_length(self):
        learner, scripts = course(6, minutes=15)  # by now there is enough material for a full lesson
        sc = scripts[-1]
        self.assertGreater(len([s for s in sc.segments if s.type == "pause" and s.role == "answer"]), 20)
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(None, "stub")
            prof.mp3 = False
            prof.fit_tolerance = 0.0
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
            self.assertEqual(cues["target_s"], 900)
            self.assertAlmostEqual(cues["duration_s"], 900, delta=1.0, msg=cues["fit_scale"])
            self.assertTrue(0.85 <= cues["fit_scale"] <= 1.25)
            # speech untouched, every pause scaled by the same factor
            answers = [c["dur"] for c in cues["segments"] if c["type"] == "pause" and c["role"] == "answer"]
            expected = [round(s.duration * cues["fit_scale"], 2) for s in sc.segments if s.type == "pause" and s.role == "answer"]
            for a, e in zip(answers, expected):
                self.assertAlmostEqual(a, e, delta=0.02)

    def test_fit_tolerance_leaves_pauses_alone_when_close(self):
        learner, scripts = course(6, minutes=15)
        sc = scripts[-1]
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(None, "stub")
            prof.mp3 = False
            prof.fit_tolerance = 600.0  # anything within ten minutes counts as on target
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
            self.assertEqual(cues["fit_scale"], 1.0)
            prof.fit_tolerance = 30.0
            cues2 = render_script(sc, prof, Path(td) / "m.wav", cache_dir=Path(td) / "c", progress=False)
            self.assertLessEqual(abs(cues2["duration_s"] - 900), 31.0, cues2["fit_scale"])

    def test_calibration_feeds_back_into_estimates(self):
        learner = fresh()
        learner.calibrate({"fr": 0.8, "en": 1.2})
        self.assertAlmostEqual(learner.speech_calibration["fr"], 0.86)  # 1 - 0.7 + 0.7 × 0.8
        learner.calibrate({"fr": 1.0})  # a spot-on render changes nothing
        self.assertAlmostEqual(learner.speech_calibration["fr"], 0.86)
        t = Timing(speech_ratio=learner.speech_calibration)
        self.assertAlmostEqual(t.speech_estimate("Bonjour.", "fr"), Timing().speech_estimate("Bonjour.", "fr") * 0.86, places=1)

    def test_short_lessons_still_introduce_something(self):
        sc = build(fresh(), minutes=2)
        self.assertGreaterEqual(len(sc.meta["new_items"]), 1)

    def test_parallel_warmup_gives_identical_output(self):
        from audiolesson.render.tts import StubProvider

        sc = build(fresh(), minutes=2)
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(None, "stub")
            prof.mp3 = False
            prof.fit = False
            seq = render_script(sc, prof, Path(td) / "a.wav", cache_dir=Path(td) / "ca", progress=False)
            StubProvider.parallel = True
            try:
                par = render_script(sc, prof, Path(td) / "b.wav", cache_dir=Path(td) / "cb", progress=False)
            finally:
                StubProvider.parallel = False
            self.assertEqual(seq["duration_s"], par["duration_s"])
            self.assertEqual(read_wav(Path(td) / "a.wav").pcm, read_wav(Path(td) / "b.wav").pcm)

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
