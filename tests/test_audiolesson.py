"""Structural guarantees of a generated lesson. Run: python -m unittest -v"""

from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.content import CurriculumError, curriculum_from_dict, load_curriculum
from audiolesson.learner import ItemState, LearnerState
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
_WORD_RE = re.compile(r"[^\W\d]+", re.UNICODE)


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

    def test_split_note_span_recognizes_an_explicit_language_prefix(self):
        """Issue #49: a «...»-marked note span may open with "xx:" to name a language other
        than the target one — an embedded third-language example, e.g. a Japanese word
        inside an English note. A bare span (no prefix) still means "target language,"
        unchanged, and a colon that isn't a real 2-3 letter language code (e.g. inside a
        clock time) must not misfire as one."""
        from audiolesson.content import split_note_span

        self.assertEqual(split_note_span("Halló"), (None, "Halló", "Halló"))
        self.assertEqual(split_note_span("ja:onigiri"), ("ja", "onigiri", "onigiri"))
        self.assertEqual(split_note_span("ja: onigiri"), ("ja", "onigiri", "onigiri"))  # optional space after the colon
        self.assertEqual(split_note_span("ja:yare yare"), ("ja", "yare yare", "yare yare"))
        self.assertEqual(split_note_span("14:00"), (None, "14:00", "14:00"))  # digits, not a language code

    def test_split_note_span_separates_display_text_from_speech_text(self):
        """Owner review on PR #51: passing a romanized display form straight to the TTS
        provider is provider-fragile — some providers (e.g. OpenAIProvider) don't even use
        the language code to disambiguate it, they just read whatever text they're given.
        «xx:display|speech» lets a note keep a familiar romanization in the transcript while
        the provider receives native orthography — not Japanese-specific: the same split
        serves pinyin → Hanzi, Korean romanization → Hangul, Arabic transliteration, etc."""
        from audiolesson.content import split_note_span

        self.assertEqual(split_note_span("ja:sate|さて"), ("ja", "sate", "さて"))
        self.assertEqual(split_note_span("ja:onigiri|おにぎり"), ("ja", "onigiri", "おにぎり"))
        self.assertEqual(split_note_span("zh:pinyin|漢字"), ("zh", "pinyin", "漢字"))

    def test_note_with_unbalanced_guillemets_is_rejected(self):
        """A stray or missing «»  in a note is an authoring mistake — catch it at validation
        rather than have it silently mis-split at build time (issue #34 point 1)."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "notes": [{"id": "n", "text": "Say «halló to greet someone."}],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)

    def test_note_with_equal_but_malformed_guillemet_counts_is_rejected(self):
        """Owner review on #41: counting «/» separately passes malformed markup that happens
        to have one of each but isn't an actual matched pair — e.g. reversed order, or one
        real pair plus an unrelated stray open. Validation must actually run the matching
        regex, not just compare counts."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "notes": [{"id": "n", "text": "»uh oh« then «real»"}],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)

    def test_a_spent_arc_with_substantial_time_left_starts_a_new_one(self):
        """Issue #34, reframed by the owner from a real generated lesson: a 30-minute request
        that hits its per-lesson new-item cap early, then runs its review pool dry (including a
        second pass), used to just stop — a real Lesson 3 ended at ~15 minutes with 11 minutes
        of budget still unused and 985 of 993 curriculum items untouched, solely because every
        fallback tier (due reactivation, extra single item under the cap, repeat, note, second
        review pass) was independently exhausted. The new-item cap should bound one coherent
        arc, not the whole lesson: once arc 1's own reactivations are done and review is spent,
        with substantial time and more curriculum left, the planner should start a fresh small
        arc instead of ending far short."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": (
                [{"id": f"r{i}", "kind": "phrase", "target": f"Rifja {i}.", "meaning": f"Review {i}."} for i in range(6)]
                + [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(20)]
            ),
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(6):
            learner.items[f"r{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        cfg = PlanConfig(minutes=60, seed=1, new_items=2, dialogue_every=1000, drill_streak_limit=1000, note_chance=0.0)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)
        sc = planner.build()
        new_items = sc.meta["new_items"]
        self.assertGreater(len(new_items), cfg.resolved_max_new_items(), new_items)
        self.assertEqual(len(new_items), len(set(new_items)), "no item introduced twice")

    def test_a_spent_arc_does_not_start_a_new_one_on_a_genuinely_first_lesson(self):
        """The new-arc mechanism above must not defeat the deliberate, separately-tested
        guarantee that a first lesson with nothing to review ends short rather than being
        padded (``test_first_lesson_at_default_pace_is_short_not_padded``) — it is gated on
        ``reviews_used`` (this lesson actually reviewed something and ran that pool dry), which
        stays empty for a learner with no history at all."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(20)],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")  # no items known at all: a true first lesson
        cfg = PlanConfig(minutes=60, seed=1, new_items=2, dialogue_every=1000, drill_streak_limit=1000, note_chance=0.0)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)
        sc = planner.build()
        self.assertLessEqual(len(sc.meta["new_items"]), cfg.resolved_max_new_items())

    def test_a_new_arc_still_respects_prerequisite_order(self):
        """Regression for a real bug hit while building the new-arc mechanism above: the first
        cut's dedup fix (excluding items already sitting in ``new_queue``, to avoid selecting a
        duplicate across two arc-starting calls in the same lesson) made ``select_new`` treat a
        queued-but-not-yet-introduced item as satisfying another item's prerequisite too — since
        a fresh ``select_new`` call was allowed to run *while a previous arc's queue was still
        draining*, it could return an item whose prereq was only queued, not yet actually
        taught, and ``do_intro`` it immediately, jumping ahead. Caught by
        ``test_prerequisites_respected`` on the real curriculum; this is a minimal, fast
        reproduction: a chain of 20 items each requiring the previous one, with pace forced low
        enough that multiple arcs are needed to introduce them all."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": (
                [{"id": f"r{i}", "kind": "phrase", "target": f"Rifja {i}.", "meaning": f"Review {i}."} for i in range(6)]
                + [
                    {
                        "id": f"w{i}",
                        "kind": "phrase",
                        "target": f"Orð {i}.",
                        "meaning": f"Word {i}.",
                        "prereqs": ([f"w{i - 1}"] if i > 0 else []),
                    }
                    for i in range(20)
                ]
            ),
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(6):
            learner.items[f"r{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        cfg = PlanConfig(minutes=60, seed=1, new_items=2, dialogue_every=1000, drill_streak_limit=1000, note_chance=0.0)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)
        sc = planner.build()
        order = {iid: idx for idx, iid in enumerate(sc.meta["new_items"])}
        for i in range(1, 20):
            a, b = f"w{i - 1}", f"w{i}"
            if a in order and b in order:
                self.assertLess(order[a], order[b], f"{b} introduced before its prereq {a}")

    def test_a_freshly_introduced_items_own_dialogue_stage_is_not_skipped(self):
        """Issue #44 point 2: once an item's own reactivation schedule reaches its ladder's
        final "dialogue" stage, the old code only attempted it when ``since_dialogue >=
        dialogue_every // 2`` — a frequency-spacing gate meant to keep dialogues from
        clustering when several long-known review items cycle back to "dialogue" close
        together, not something that should apply to a freshly introduced item's own first
        (and only, since "dialogue" is always the ladder's last stage) attempt at connected
        use. With ``dialogue_every`` set unreachably high and ``drill_streak_limit`` disabled
        (isolating this from the streak-triggered dialogue pick, a different mechanism), the
        item's own schedule must still reach a real "dialogue" exercise rather than silently
        falling back to ``below_dialogue()`` forever — confirmed against the pre-fix code that
        this exact scenario produced no dialogue at all (``dialogues: []``)."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": (
                [{"id": "w0", "kind": "phrase", "target": "Orð eitt tvö.", "meaning": "Word one two."}]
                + [{"id": f"r{i}", "kind": "phrase", "target": f"Rifja {i}.", "meaning": f"Review {i}."} for i in range(10)]
            ),
            "dialogues": [
                {"id": "d1", "setting": "A test setting.", "requires": ["w0"], "turns": [{"cue": "Say it.", "expect": "w0"}]}
            ],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(10):
            learner.items[f"r{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        cfg = PlanConfig(minutes=30, seed=1, new_items=1, dialogue_every=1000, drill_streak_limit=1000)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)
        sc = planner.build()
        self.assertIn("d1", sc.meta["dialogues"])

    def test_a_long_drill_streak_pulls_an_eligible_dialogue_forward(self):
        """Issue #34 points 5-6: a long uninterrupted run of isolated recall exercises should
        pull an eligible dialogue forward rather than waiting for its usual periodic schedule
        (``dialogue_every``) — otherwise a well-stocked review lesson can run many consecutive
        "situation -> pause -> answer" drills before ever reaching a connected dialogue."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(10)],
            "dialogues": [
                {
                    "id": "d1",
                    "setting": "A test setting.",
                    "requires": ["w0", "w1"],
                    "turns": [{"cue": "Say word 0.", "expect": "w0"}],
                }
            ],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(10):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        # dialogue_every set far out of reach so only drill_streak_limit can pull d1 forward
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, dialogue_every=1000, drill_streak_limit=4), today=TODAY)
        sc = planner.build()
        kinds = [ex.kind for ex in sc.exercises if ex.kind != "opening"]
        self.assertEqual(kinds[:4], ["recall"] * 4, kinds)
        self.assertEqual(kinds[4], "dialogue", kinds)

    def test_high_drill_streak_pulls_a_note_forward_when_no_dialogue_fits(self):
        """Issue #34 point 6: a high drill streak should pull *something* connected/varied
        forward, not just a dialogue — when no dialogue is eligible either (here: none exist
        in the curriculum at all), a note breaks up the run instead of silently falling
        through to yet another isolated recall."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(10)],
            "notes": [{"id": "n1", "text": "A cultural fact."}],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(10):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        # note_chance=0 so the note can only come from the new streak fallback, not the
        # ordinary per-exercise random note roll — isolates which mechanism produced it.
        planner = Planner(
            cur,
            learner,
            Prompts.load("en"),
            Timing(level="A1"),
            PlanConfig(minutes=30, seed=1, dialogue_every=1000, drill_streak_limit=3, note_chance=0.0),
            today=TODAY,
        )
        sc = planner.build()
        kinds = [ex.kind for ex in sc.exercises if ex.kind != "opening"]
        self.assertEqual(kinds[:3], ["recall"] * 3, kinds)
        self.assertEqual(kinds[3], "note", kinds)

    def test_streak_relief_notes_are_bounded_not_unlimited(self):
        """Issue #44 point 1: a real generated lesson showed the streak-triggered note fallback
        (previous test) was itself gated by ``_note_budget_left()``, the ordinary per-lesson
        aside ration — as little as 1 note for a short lesson, easily spent by the very first
        unrelated aside roll long before the streak ever needed it, after which the streak kept
        climbing (confirmed to 15 unbroken recalls on the real curriculum) with no rescue at
        all. The fix must not simply remove that gate either — an unconditional bypass measured
        as high as 19 asides in one 30-minute lesson during `auto` pace escalation, turning
        rationing off entirely. `max_streak_relief_notes` is the middle ground: a small, bounded
        allowance spent only once the ordinary ration is exhausted.

        This curriculum forces the ordinary ration to exactly 1 (a 12-minute lesson) and gives
        the streak plenty of opportunities to retrigger (no dialogues, `drill_streak_limit=3`,
        30 review items). Exactly ration (1) + `max_streak_relief_notes` (2) = 3 notes should
        fire — not fewer (the relief mechanism must actually engage), and not more (it must stay
        bounded even though the streak keeps retriggering and more notes remain available)."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(30)],
            "notes": [{"id": f"n{i}", "text": f"Note {i}."} for i in range(10)],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(30):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        cfg = PlanConfig(minutes=12, seed=1, dialogue_every=1000, drill_streak_limit=3, max_streak_relief_notes=2)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)
        sc = planner.build()
        self.assertEqual(len(sc.meta["notes"]), 1 + cfg.max_streak_relief_notes, sc.meta["notes"])

    def test_streak_with_no_dialogue_and_no_notes_does_not_fall_through_to_more_recall(self):
        """Owner review on #46 (issue #44's own acceptance criteria): bounding the relief-note
        allowance (previous test) still left a silent fallthrough once *both* the ordinary
        note ration and the relief allowance ran out — the old code just fell back to another
        isolated recall, exactly what #44 rules out. With no dialogues and no notes in the
        curriculum at all, there is nothing on the note/dialogue side to rescue the streak, so
        the very next exercise after the streak trips must be something other than another
        isolated "recall" — here, the new recombination fallback (``do_connect``, kind
        "connect"), since plenty of already-known items with a situation cue exist."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}.", "situation": f"Situation {i}."}
                for i in range(10)
            ],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(10):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        planner = Planner(
            cur,
            learner,
            Prompts.load("en"),
            Timing(level="A1"),
            PlanConfig(minutes=30, seed=1, dialogue_every=1000, drill_streak_limit=3, note_chance=0.0),
            today=TODAY,
        )
        sc = planner.build()
        kinds = [ex.kind for ex in sc.exercises if ex.kind != "opening"]
        self.assertEqual(kinds[:3], ["recall"] * 3, kinds)
        self.assertNotEqual(kinds[3], "recall", f"{kinds}: silently fell through to another isolated recall")
        self.assertEqual(kinds[3], "connect", kinds)

    def test_connected_use_reaches_an_arc_whose_items_are_wired_into_no_dialogue(self):
        """Issue #44 point 2, owner review on #46: the earlier fix (previous test class,
        ``test_a_freshly_introduced_items_own_dialogue_stage_is_not_skipped``) only reaches an
        item's own "dialogue" ladder stage when that item is referenced by some authored
        dialogue's ``requires`` — an item never wired into any dialogue never gets a "dialogue"
        ladder stage at all, so that fix could never fire for it. Here the curriculum has *no*
        dialogues whatsoever, so a whole freshly introduced arc (``a0``, ``a1``) can never get
        connected use through the dialogue system, no matter how its reactivation schedule
        plays out. Plenty of other already-known review material exists too. The new
        recombination fallback (``do_connect``) doesn't depend on authored dialogue content —
        it must still give the arc's own material a connected-use moment, preferring it over
        the unrelated review items, once the drill streak trips."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": (
                [
                    {"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}.", "situation": f"Situation {i}."}
                    for i in range(10)
                ]
                + [
                    {"id": "a0", "kind": "phrase", "target": "Boga 0.", "meaning": "Arc 0.", "situation": "Arc situation 0."},
                    {"id": "a1", "kind": "phrase", "target": "Boga 1.", "meaning": "Arc 1.", "situation": "Arc situation 1."},
                ]
            ),
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(10):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        planner = Planner(
            cur,
            learner,
            Prompts.load("en"),
            Timing(level="A1"),
            PlanConfig(minutes=30, seed=1, new_items=2, dialogue_every=1000, drill_streak_limit=3, note_chance=0.0),
            today=TODAY,
        )
        sc = planner.build()
        self.assertNotIn("dialogue", [ex.kind for ex in sc.exercises], "no dialogue exists in this curriculum at all")
        connect_exercises = [ex for ex in sc.exercises if ex.kind == "connect"]
        self.assertTrue(connect_exercises, "no connected-use activity ever fired for the wired-nowhere arc")
        connected_items = {i for ex in connect_exercises for i in ex.item_ids}
        # both of the arc's own items, not just one of them alongside an unrelated review item —
        # "recombine the arc's own material" means the arc supplies both halves of the exchange
        # whenever it can (owner review round 2 on #46).
        self.assertTrue(
            {"a0", "a1"} <= connected_items,
            f"connected-use activity didn't recombine the arc's own two items together: {connected_items}",
        )

    def test_each_arc_gets_its_own_connected_use_moment_without_a_drill_streak(self):
        """Issue #44, owner review round 2 on #46: the first cut only ever reached
        ``do_connect()`` as a side effect of the drill-streak breaker, so an arc practiced at
        a normal pace — never running the streak past its limit — could finish, and the
        lesson could move on to a second arc or end, with no connected-use attempt at all.
        #44's own acceptance criteria don't make this conditional on a streak: once an arc's
        items have had initial practice, it gets a deliberate connected-use attempt before the
        lesson moves on. ``drill_streak_limit`` is set unreachably high here specifically to
        prove this doesn't depend on the streak breaker.

        Also checks the two arcs don't cross-contaminate: arc 2's connected-use moment must
        use arc 2's own two items, not reuse arc 1's (a risk with a shared ``introduced`` pool
        ordered by intro time, where an earlier arc's items would otherwise be found first)."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": (
                [
                    {"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}.", "situation": f"Situation {i}."}
                    for i in range(10)
                ]
                + [
                    {"id": "a0", "kind": "phrase", "target": "Boga 0.", "meaning": "Arc one, a.", "situation": "Arc one situation a."},
                    {"id": "a1", "kind": "phrase", "target": "Boga 1.", "meaning": "Arc one, b.", "situation": "Arc one situation b."},
                    {"id": "b0", "kind": "phrase", "target": "Boga 2.", "meaning": "Arc two, a.", "situation": "Arc two situation a."},
                    {"id": "b1", "kind": "phrase", "target": "Boga 3.", "meaning": "Arc two, b.", "situation": "Arc two situation b."},
                ]
            ),
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(10):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        planner = Planner(
            cur,
            learner,
            Prompts.load("en"),
            Timing(level="A1"),
            PlanConfig(minutes=30, seed=1, new_items=2, max_new_items=2, dialogue_every=1000, drill_streak_limit=1000, note_chance=0.0),
            today=TODAY,
        )
        sc = planner.build()
        drill_streaks = []
        streak = 0
        for ex in sc.exercises:
            if ex.kind == "recall":
                streak += 1
                drill_streaks.append(streak)
            else:
                streak = 0
        self.assertLess(max(drill_streaks, default=0), 1000, "the streak breaker must never have tripped in this test")
        connect_exercises = [ex for ex in sc.exercises if ex.kind == "connect"]
        self.assertGreaterEqual(len(connect_exercises), 2, f"expected a connected-use moment per arc: {[ex.item_ids for ex in connect_exercises]}")
        arc1 = next((ex for ex in connect_exercises if set(ex.item_ids) & {"a0", "a1"}), None)
        arc2 = next((ex for ex in connect_exercises if set(ex.item_ids) & {"b0", "b1"}), None)
        self.assertIsNotNone(arc1, f"arc 1 never got its own connected-use moment: {[ex.item_ids for ex in connect_exercises]}")
        self.assertIsNotNone(arc2, f"arc 2 never got its own connected-use moment: {[ex.item_ids for ex in connect_exercises]}")
        self.assertEqual(set(arc1.item_ids), {"a0", "a1"}, f"arc 1's connected use pulled in material outside the arc: {arc1.item_ids}")
        self.assertEqual(set(arc2.item_ids), {"b0", "b1"}, f"arc 2's connected use pulled in material outside the arc: {arc2.item_ids}")

    def test_connect_never_skips_a_multi_word_items_own_stage_progression(self):
        """Owner review round 3 on #46: ``do_connect()`` recorded *any* has-situation candidate
        at stage ``"situation"`` regardless of how far it had actually climbed its own ladder —
        harmless for a short item, whose ladder goes straight from ``meaning`` to ``situation``,
        but a multi-word item's ladder also has ``cloze``/``hinted`` in between. Since
        ``record_lesson()`` never lowers a stage once raised (only ``max()``s across what a
        lesson recorded), sweeping such an item into a connect() exercise could jump its
        persisted stage straight to ``situation``, permanently skipping stages it never
        actually practised.

        ``hard0`` is a known multi-word item stuck at ``hinted`` — several stages short of
        ``situation`` — alongside plenty of fully-progressed short items, so every connect()
        this lesson has an alternative pairing that doesn't need ``hard0`` at all. Confirmed
        against the pre-fix code that ``hard0`` got swept into a connect() exercise (and its
        stage jumped straight to ``situation``) despite never having done ``cloze``/``meaning``
        in this lesson or any before it.

        The second half checks the general guarantee, not just this one item: no item's
        recorded stage sequence this lesson, starting from wherever it stood before the
        lesson, ever skips a ladder stage — stronger than the existing
        ``test_stages_get_harder_within_lesson``, which only checks the sequence doesn't go
        *backward*, not that it doesn't jump *ahead*."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": (
                [
                    {
                        "id": "hard0",
                        "kind": "phrase",
                        "target": "Þetta er erfitt orð.",
                        "meaning": "This is a hard word.",
                        "situation": "A hard-word situation.",
                    }
                ]
                + [
                    {"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}.", "situation": f"Situation {i}."}
                    for i in range(10)
                ]
            ),
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        learner.items["hard0"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="hinted")
        for i in range(10):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="situation")
        planner = Planner(
            cur,
            learner,
            Prompts.load("en"),
            Timing(level="A1"),
            PlanConfig(minutes=30, seed=1, dialogue_every=1000, drill_streak_limit=3, note_chance=0.0),
            today=TODAY,
        )
        sc = planner.build()
        connect_items = {i for ex in sc.exercises if ex.kind == "connect" for i in ex.item_ids}
        self.assertNotIn("hard0", connect_items, "a not-yet-ready multi-word item was swept into a connect() exercise")

        ladders = sc.meta["ladders"]
        for item_id, stages in sc.meta["exposures"].items():
            ladder = ladders[item_id]
            pre_stage = learner.items[item_id].stage if item_id in learner.items and learner.items[item_id].stage in ladder else ladder[0]
            seq = [stage_index(ladder, pre_stage)] + [ladder.index(s) for s in stages if s in ladder]
            gaps = [b - a for a, b in zip(seq, seq[1:])]
            self.assertTrue(all(g <= 1 for g in gaps), f"{item_id}: stage sequence skipped a ladder stage: {seq} ({ladder})")

    def test_connect_uses_the_partner_cue_only_for_its_authored_predecessor(self):
        """Issue #48, owner review round 3 on PR #52: ``partner_cue`` alone only guarantees
        the line is good context *for B* — it says nothing about whether it followed
        naturally from whichever A the planner happened to recombine it with. Two cases,
        tested directly against ``Builder.connect()`` for full control over which item
        lands in the "first" slot (round 2's version routed through the whole planner,
        which doesn't guarantee that): a compatible pairing (``b.partner_cue_after ==
        a.id``) must use the cue; an incompatible one (the very same ``b``, paired after a
        *different* item) must not — falling back to the ordinary English bridge instead,
        exactly as if no ``partner_cue`` had ever been authored."""
        from audiolesson.exercises import Builder

        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a", "kind": "phrase", "target": "A.", "meaning": "A.", "situation": "Situation A."},
                {"id": "c", "kind": "phrase", "target": "C.", "meaning": "C.", "situation": "Situation C."},
                {
                    "id": "b",
                    "kind": "phrase",
                    "target": "B.",
                    "meaning": "B.",
                    "situation": "Situation B.",
                    "partner_cue": "Bridge line.",
                    "partner_cue_after": "a",
                    "partner_cue_setup": "Scene: say A.", "partner_cue_meaning": "Bridge meaning.", "partner_cue_situation": "Scene: say B.",
                },
            ],
        }
        cur = curriculum_from_dict(raw)
        prompts = Prompts.load("en")
        b = Builder(cur, prompts, Timing(level="A1"), fresh())

        sc_compatible = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.connect(sc_compatible, [cur.by_id["a"], cur.by_id["b"]])
        speaks = [(s.speaker, s.text) for s in sc_compatible.segments if s.type == "speak"]
        self.assertIn(("native_b", "Bridge line."), speaks, "a -> b is exactly what partner_cue_after names; the cue must be used")

        sc_incompatible = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.connect(sc_incompatible, [cur.by_id["c"], cur.by_id["b"]])
        narrations = [s.text for s in sc_incompatible.segments if s.type == "narrate"]
        speaks2 = [(s.speaker, s.text) for s in sc_incompatible.segments if s.type == "speak"]
        self.assertNotIn(("native_b", "Bridge line."), speaks2, "c -> b is not what the cue was written for; it must not be used")
        self.assertIn(prompts.get("connect_next"), narrations, "falls back to the ordinary English bridge")

    def test_connect_resolves_a_construction_instead_of_speaking_its_raw_template(self):
        """A construction can have a ``situation`` (e.g. ``einn_tvo_thrjar``, issue #29 cluster
        A) just like any phrase, and ``_connect_pair`` (planner.py) picks connect() candidates
        by ``has_situation`` alone — it doesn't filter by kind. ``recall()`` always resolves a
        construction's slots before speaking it (``_recall_construction``); connect() must do
        the same rather than speaking ``item.target`` verbatim, which for a construction is an
        unfilled template like "{n} widgets." — not a sentence a partner or learner ever says."""
        from audiolesson.exercises import Builder

        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a", "kind": "phrase", "target": "A.", "meaning": "A.", "situation": "Situation A."},
                {"id": "two", "kind": "vocab", "target": "tveir", "meaning": "two", "tags": ["cnt"]},
                {
                    "id": "b",
                    "kind": "construction",
                    "target": "{n} widgets.",
                    "meaning": "{n} widgets.",
                    "situation": "Situation B.",
                    "slots": {"n": "cnt"},
                    "example": {"n": "two"},
                },
            ],
        }
        cur = curriculum_from_dict(raw)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.connect(sc, [cur.by_id["a"], cur.by_id["b"]])
        answers = [s.text for s in sc.segments if s.type == "answer"]
        self.assertNotIn("{n} widgets.", answers)
        self.assertIn("Tveir widgets.", answers)  # a sentence opening with a slot is capitalised

    def _talar_thu_builder(self, seed: int):
        """A Builder on the real is-en course whose learner knows every ``acc_language`` fill,
        so unconstrained generation for «Talar þú {language}?» has seven languages to pick."""
        import random

        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        for it in cur.items_with_tag("acc_language") + [cur.by_id["talar_thu"], cur.by_id["ha"]]:
            learner.items[it.id] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="situation")
        return cur, Builder(cur, Prompts.load("en"), Timing(level="A1"), learner, random.Random(seed))

    def test_construction_situation_practice_uses_the_fill_its_situation_names(self):
        """Issue #57: «Talar þú {language}?»'s situation says "Ask if she speaks English." — a
        situation-stage recall must answer «Talar þú ensku?», whatever the generator would
        otherwise pick. Other stages keep generating other languages (the non-goal: this must
        not collapse into always using the worked example)."""
        answers, free = set(), set()
        for seed in range(12):
            cur, b = self._talar_thu_builder(seed)
            sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
            b.recall(sc, cur.by_id["talar_thu"], "situation")
            b.recall(sc, cur.by_id["talar_thu"], "meaning")
            b.recall(sc, cur.by_id["talar_thu"], "recombine")
            situation_ex, *others = sc.exercises
            self.assertIn("English", " ".join(s.text for s in sc.segments if s.exercise == situation_ex.index and s.type == "narrate"))
            answers |= {s.text for s in sc.segments if s.exercise == situation_ex.index and s.type == "answer"}
            free |= {s.text for ex in others for s in sc.segments if s.exercise == ex.index and s.type == "answer"}
        self.assertEqual(answers, {"Talar þú ensku?"})
        self.assertGreater(len(free), 2, f"non-situation practice must still vary the fill: {free}")

    def test_connect_uses_the_fill_a_construction_situation_names(self):
        """Issue #57, the real Lesson 4 failure: inside connect(), "You're not sure the
        receptionist understands you. Ask if she speaks English." was answered «Talar þú
        íslensku?» — connect() narrates the construction's situation, so it must honour the
        same binding."""
        seen = set()
        for seed in range(12):
            cur, b = self._talar_thu_builder(seed)
            sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
            b.connect(sc, [cur.by_id["ha"], cur.by_id["talar_thu"]])
            seen |= {s.text for s in sc.segments if s.type == "answer" and s.text.startswith("Talar")}
        self.assertEqual(seen, {"Talar þú ensku?"})

    def test_construction_situations_that_name_a_fill_are_bound(self):
        """Issue #57 authoring guard: if a construction's situation mentions one of its slot
        fills by meaning ("English", "two"), that slot must be bound with ``situation_fill`` —
        otherwise the generator can answer the named situation with a different fill."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for c in cur.items:
            if c.kind != "construction" or not c.has_situation:
                continue
            text = " ".join(c.situations or [c.situation]).lower()
            for slot, tag in c.slots.items():
                for fill in cur.items_with_tag(tag):
                    word = re.sub(r"\s*\(.*\)", "", fill.meaning).strip().lower()
                    if word and re.search(r"\b" + re.escape(word) + r"\b", text):
                        self.assertIn(slot, c.situation_fill, f"{c.id}: situation names {word!r} but slot {slot!r} is unbound")

    def test_meaning_forms_render_a_fill_in_the_form_a_construction_asks_for(self):
        """Issue #29 pilot 3: Icelandic uses the same bare infinitive after «er að», «má», «vil»,
        but English/Japanese glosses don't — "I'm {inf:ing}." needs "going home", not "go home".
        ``{slot:form}`` renders the fill's ``meaning_forms[form]`` (glossed per language like
        ``meaning``), and validation insists every possible fill has that form."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "fara_heim", "kind": "vocab", "target": "fara heim", "meaning": "go home", "meaning_ja": "家に帰る",
                 "tags": ["inf"], "meaning_forms": {"ing": "going home"}, "meaning_forms_ja": {"te": "家に帰って"}},
                {"id": "sofa", "kind": "vocab", "target": "sofa", "meaning": "sleep", "meaning_ja": "寝る",
                 "tags": ["inf"], "meaning_forms": {"ing": "sleeping"}, "meaning_forms_ja": {"te": "寝て"}},
                {"id": "c", "kind": "construction", "target": "Ég er að {inf}.", "meaning": "I'm {inf:ing}.",
                 "meaning_ja": "今、{inf:te}いるところです。", "slots": {"inf": "inf"}},
            ],
        }
        cur = curriculum_from_dict(raw)
        self.assertEqual(cur.resolve_slots(cur.by_id["c"], {"inf": cur.by_id["sofa"]}), ("Ég er að sofa.", "I'm sleeping."))
        ja = curriculum_from_dict(raw, known_lang="ja")
        self.assertEqual(ja.resolve_slots(ja.by_id["c"], {"inf": ja.by_id["fara_heim"]})[1], "今、家に帰っているところです。")
        bad = json.loads(json.dumps(raw))
        del bad["items"][1]["meaning_forms"]
        with self.assertRaisesRegex(CurriculumError, "needs meaning_forms.ing"):
            curriculum_from_dict(bad)

    def test_real_aspect_and_modality_constructions_read_correctly_for_every_fill(self):
        """Issue #29 pilot 3 on the real course: «Ég er að {inf}.» and «Má ég {inf}?» over the
        whole "inf" pool resolve to well-formed glosses in both instructor languages — no raw
        placeholders, and the progressive always reads "I'm …ing"."""
        for lang in (None, "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            for cid in ("eg_er_ad_inf", "ma_eg_inf"):
                for fill in cur.items_with_tag(cur.by_id[cid].slots["inf"]):
                    target, meaning = cur.resolve_slots(cur.by_id[cid], {"inf": fill})
                    self.assertNotIn("{", target + meaning, (cid, fill.id))
                    if cid == "eg_er_ad_inf" and lang is None:
                        self.assertRegex(meaning, r"^I'm \w+ing\b", fill.id)

    def _lesson_introducing(self, item_id: str) -> tuple[Script, "Curriculum"]:
        """A real is-en lesson for a learner who has learned everything before ``item_id``."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        limit = cur.by_id[item_id].order
        for it in cur.items:
            if it.order < limit:
                learner.items[it.id] = ItemState(due=(TODAY + timedelta(days=30)).isoformat(), successes=3, durable_successes=3, stage="situation")
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY).build(), cur

    def test_modality_milestone_names_the_family_before_ma_eg_becomes_productive(self):
        """Issue #29 pilot 3 (modality), generalising godur_gender: when «Má ég {inf}?» is
        introduced, the modal_infinitive milestone has already named want / have to / may +
        infinitive and immediately contrasted the familiar «Ég vil fara heim» / «Ég verð að
        fara heim» — then the construction generates verbs beyond its worked example."""
        sc, cur = self._lesson_introducing("ma_eg_inf")
        labels = [ex.label for ex in sc.exercises]
        self.assertIn("ma_eg_inf", sc.meta["new_items"])
        note = labels.index("note: modal_infinitive")
        self.assertLess(note, labels.index("new pattern: Má ég {inf}?"))
        self.assertEqual(labels[note + 1 : note + 3], ["situation: Ég vil fara heim.", "situation: Ég verð að fara heim."])
        novel = {l for ex, l in zip(sc.exercises, labels) if "ma_eg_inf" in ex.item_ids and ex.kind != "intro"} - {"situation: Má ég fara heim?"}
        self.assertTrue(novel, labels)

    def test_progressive_only_generates_activity_verbs(self):
        """Issue #63 and the owner's review on PR #64: «vera að» + infinitive is for dynamic
        verbs, not states — «ég sit» for "I'm sitting", and «sofa» too: «er að sofa» is not
        generally accepted (icelandicgrammar.com gives «sefur»). So the progressive draws on its
        own ``progressive_inf`` pool, a subset of "inf" without «sofa», while the modal
        constructions keep the general pool («Má ég sofa?» is fine). Adding a verb to
        ``progressive_inf`` fails here until someone has checked its progressive is natural."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        audited_dynamic = {
            "fara_heim", "borda", "fara_i_sund", "fara_ut", "hvila_mig", "versla", "kaupa_mida",
            "hringja_heim", "fara_a_safnid", "drekka_kaffi", "boka_ferd", "vinna_verb", "laera",
        }
        progressive = cur.by_id["eg_er_ad_inf"].slots["inf"]
        self.assertEqual(progressive, "progressive_inf")
        self.assertEqual({i.id for i in cur.items_with_tag(progressive)}, audited_dynamic)
        general = {i.id for i in cur.items_with_tag("inf")}
        self.assertTrue(audited_dynamic <= general)
        self.assertIn("sofa", general - audited_dynamic)
        for cid in ("ma_eg_inf", "eg_vil", "eg_verd_ad"):
            self.assertEqual(cur.by_id[cid].slots["inf"], "inf", cid)
        generated = {cur.resolve_slots(cur.by_id["eg_er_ad_inf"], {"inf": f})[0] for f in cur.items_with_tag(progressive)}
        self.assertNotIn("Ég er að sofa.", generated)
        self.assertEqual(cur.resolve_slots(cur.by_id["ma_eg_inf"], {"inf": cur.by_id["sofa"]})[0], "Má ég sofa?")
        note = cur.note_by_id["vera_ad_progressive"]
        self.assertNotIn("Any verb", note.text)
        self.assertIn("activity verbs", note.text)
        self.assertIn("«Ég sef»", note.text)

    def test_aspect_milestone_names_the_progressive_before_eg_er_ad_inf(self):
        """Issue #29 pilot 3 (aspect): the vera_ad_progressive milestone names «er að» +
        infinitive from «Ég er að koma!» / «Ég er að fara» / «Ég er að læra …» before the
        productive «Ég er að {inf}.» is introduced."""
        sc, cur = self._lesson_introducing("eg_er_ad_inf")
        labels = [ex.label for ex in sc.exercises]
        self.assertIn("eg_er_ad_inf", sc.meta["new_items"])
        self.assertLess(labels.index("note: vera_ad_progressive"), labels.index("new pattern: Ég er að {inf}."))

    def test_dialogue_turn_can_expect_a_construction_with_a_bound_fill(self):
        """Issue #48: a dialogue turn may expect a construction, with the fill its cue names
        bound by ``expect_fill`` — the learner generates the line from known parts inside a real
        exchange. The fill is a required item (the dialogue waits for it), the spoken line is
        resolved, and bad bindings are rejected."""
        from audiolesson.exercises import Builder

        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "fimm", "kind": "vocab", "target": "fimm", "meaning": "five", "tags": ["cnt"]},
                {"id": "sex", "kind": "vocab", "target": "sex", "meaning": "six", "tags": ["cnt"]},
                {"id": "kaffi", "kind": "vocab", "target": "kaffi", "meaning": "coffee", "tags": ["drink"]},
                {"id": "ok", "kind": "phrase", "target": "Allt í lagi.", "meaning": "OK."},
                {"id": "kostar", "kind": "construction", "target": "Það kostar {count} þúsund krónur.",
                 "meaning": "It costs {count} thousand krónur.", "slots": {"count": "cnt"}, "example": {"count": "sex"}},
            ],
            "dialogues": [
                {"id": "d", "setting": "A stall.", "turns": [
                    {"opener": "Hvað kostar þetta?", "cue": "Say five thousand.", "expect": "kostar", "expect_fill": {"count": "fimm"}, "partner": "Of dýrt."},
                    {"cue": "Agree.", "expect": "ok"},
                ]},
            ],
        }
        cur = curriculum_from_dict(raw)
        self.assertIn("fimm", cur.dialogue_by_id["d"].required_items)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), fresh())
        sc = Script(1, "L", cur.target_lang, cur.known_lang)
        b.dialogue(sc, cur.dialogue_by_id["d"])
        self.assertEqual([s.text for s in sc.segments if s.type == "answer"], ["Það kostar fimm þúsund krónur.", "Allt í lagi."])
        for turn_patch, msg in (
            ({"expect": "ok", "expect_fill": {"count": "fimm"}}, "needs a construction"),
            ({"expect_fill": {"n": "fimm"}}, "unknown slot"),
            ({"expect_fill": {"count": "kaffi"}}, "not a valid fill"),
        ):
            bad = json.loads(json.dumps(raw))
            bad["dialogues"][0]["turns"][0].update(turn_patch)
            with self.assertRaisesRegex(CurriculumError, msg):
                curriculum_from_dict(bad)

    def test_a_construction_turn_must_bind_every_slot(self):
        """Owner review on PR #61: with a multi-slot construction, a slot left out of
        ``expect_fill`` silently fell back to the worked-example fill — which is not a required
        item, so a dialogue whose other parts were learned became eligible and spoke a part the
        learner had never durably learned (#27's gate bypassed). The same held for a construction
        turn with no ``expect_fill`` at all. Every slot of a construction turn must now be bound,
        so each spoken part is in ``required_items``."""
        def raw(fill):
            turn = {"cue": "Order two coffees.", "expect": "order"}
            if fill is not None:
                turn["expect_fill"] = fill
            return {
                "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
                "items": [
                    {"id": "tvo", "kind": "vocab", "target": "tvo", "meaning": "two", "tags": ["cnt"]},
                    {"id": "thrju", "kind": "vocab", "target": "þrjú", "meaning": "three", "tags": ["cnt"]},
                    {"id": "kaffi", "kind": "vocab", "target": "kaffi", "meaning": "coffee", "tags": ["drink"]},
                    {"id": "te", "kind": "vocab", "target": "te", "meaning": "tea", "tags": ["drink"]},
                    {"id": "order", "kind": "construction", "target": "{n} {drink}, takk.", "meaning": "{n} {drink}, please.",
                     "slots": {"n": "cnt", "drink": "drink"}, "example": {"n": "thrju", "drink": "te"}},
                ],
                "dialogues": [{"id": "d", "setting": "A café.", "turns": [turn]}],
            }

        for fill, msg in (({"n": "tvo"}, "must bind every slot"), (None, "must bind every slot")):
            with self.assertRaisesRegex(CurriculumError, msg):
                curriculum_from_dict(raw(fill))
        cur = curriculum_from_dict(raw({"n": "tvo", "drink": "kaffi"}))
        self.assertTrue({"order", "tvo", "kaffi"} <= set(cur.dialogue_by_id["d"].required_items))

        # the gate itself: with the construction and «kaffi» durable but «tvo» only met, the
        # dialogue that would speak «tvo kaffi, takk.» is not eligible
        learner = LearnerState("is", "en", "A1")
        for i in ("order", "kaffi"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="situation")
        learner.items["tvo"] = ItemState(due=TODAY.isoformat(), successes=1, durable_successes=0, stage="meaning")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, seed=1), today=TODAY)
        self.assertIsNone(planner.eligible_dialogue())

    def test_real_market_stall_dialogue_generates_the_price(self):
        """Issue #48: session 26's number constructions were only ever safe inside connect(),
        never used in a partner-driven transaction. «solubas» puts the learner behind a stall:
        with the instructor lane stripped, the target-language turns are one haggle, and the
        price is generated from ``thad_kostar_big`` + the known count word, not recalled."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "L", cur.target_lang, cur.known_lang)
        b.dialogue(sc, cur.dialogue_by_id["solubas"])
        lane = [(s.speaker, s.text) for s in sc.segments if s.type in ("speak", "answer")]
        self.assertEqual(
            lane,
            [
                ("native_b", "Góðan daginn. Hvað kostar þetta?"),
                ("native_a", "Það kostar fimm þúsund krónur."),
                ("native_b", "Fimm þúsund? Það er of dýrt. Fjögur þúsund?"),
                ("native_a", "Allt í lagi."),
                ("native_b", "Frábært. Má ég borga með korti?"),
                ("native_a", "Ekkert mál."),
                ("native_b", "Takk fyrir! Bless."),
            ],
        )
        self.assertIn("fimm", cur.dialogue_by_id["solubas"].required_items)

    def test_no_dialogue_speaks_a_raw_construction_template(self):
        """Issue #48 guard: every dialogue on the real course, played in full, speaks only
        resolved target-language lines — never a ``{slot}`` placeholder."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        for d in cur.dialogues:
            sc = Script(1, "L", cur.target_lang, cur.known_lang)
            b.dialogue(sc, d, replay=True)
            spoken = [s.text for s in sc.segments if s.type in ("speak", "answer")]
            self.assertFalse([t for t in spoken if "{" in t], d.id)

    @staticmethod
    def _german_situation_curriculum():
        return curriculum_from_dict(
            {
                "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
                "items": [
                    {"id": "ensku", "kind": "vocab", "target": "ensku", "meaning": "English", "tags": ["lang"]},
                    {"id": "islensku", "kind": "vocab", "target": "íslensku", "meaning": "Icelandic", "tags": ["lang"]},
                    {"id": "thysku", "kind": "vocab", "target": "þýsku", "meaning": "German", "tags": ["lang"]},
                    {
                        "id": "talar",
                        "kind": "construction",
                        "target": "Talar þú {language}?",
                        "meaning": "Do you speak {language}?",
                        "slots": {"language": "lang"},
                        "prereqs": ["ensku"],
                        "situation": "Ask if she speaks German.",
                        "situation_fill": {"language": "thysku"},
                    },
                ]
                + [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}.", "situation": f"Situation {i}."} for i in range(8)],
            }
        )

    def test_a_situation_fill_the_learner_lacks_is_never_generated(self):
        """Owner review on PR #58: ``fixed`` fills skipped ``generate()``'s own invariant —
        constructions are only generated from parts the learner has (known, or introduced this
        lesson). "Ask if she speaks German." bound to þýsku must not force «Talar þú þýsku?»
        before þýsku is known: the situation stage drops to ``meaning`` and generates from known
        fills; once þýsku is known, the situation and its bound fill are used."""
        import random

        from audiolesson.exercises import Builder

        cur = self._german_situation_curriculum()
        learner = LearnerState("is", "en", "A1")
        for i in ("ensku", "islensku", "talar"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="situation")
        for seed in range(8):
            b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner, random.Random(seed))
            sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
            ex = b.recall(sc, cur.by_id["talar"], "situation")
            self.assertEqual(ex.stage, "meaning")
            answers = [s.text for s in sc.segments if s.type == "answer"]
            self.assertTrue(answers and all("þýsku" not in a for a in answers), answers)
            with self.assertRaises(ValueError):
                b.connect(Script(1, "L", cur.target_lang, cur.known_lang), [cur.by_id["ensku"], cur.by_id["talar"]])
        learner.items["thysku"] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="meaning")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner, random.Random(0))
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        self.assertEqual(b.recall(sc, cur.by_id["talar"], "situation").stage, "situation")
        self.assertEqual([s.text for s in sc.segments if s.type == "answer"], ["Talar þú þýsku?"])

    def test_connect_never_pairs_a_construction_whose_situation_fill_is_unknown(self):
        """Owner review on PR #58, planner side: with þýsku unknown, a streak-heavy lesson full
        of connect() exercises must never pick the German-bound construction."""
        cur = self._german_situation_curriculum()
        learner = LearnerState("is", "en", "A1")
        for i in ["ensku", "islensku", "talar"] + [f"w{i}" for i in range(8)]:
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="situation")
        cfg = PlanConfig(minutes=30, seed=1, new_items=0, max_new_items=0, dialogue_every=1000, drill_streak_limit=2, note_chance=0.0)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        connects = [ex.item_ids for ex in sc.exercises if ex.kind == "connect"]
        self.assertTrue(connects)
        self.assertFalse(any("talar" in ids for ids in connects), connects)
        self.assertNotIn("Talar þú þýsku?", [s.text for s in sc.segments if s.type == "answer"])

    def test_situation_fill_validation(self):
        """Issue #57: a situation binding must name a real slot of the construction and an item
        that is a valid fill for it (carries the slot's tag)."""
        base = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "en", "kind": "vocab", "target": "ensku", "meaning": "English", "tags": ["lang"]},
                {"id": "is_", "kind": "vocab", "target": "íslensku", "meaning": "Icelandic", "tags": ["lang"]},
                {"id": "kaffi", "kind": "vocab", "target": "kaffi", "meaning": "coffee", "tags": ["drink"]},
                {
                    "id": "c",
                    "kind": "construction",
                    "target": "Talar þú {language}?",
                    "meaning": "Do you speak {language}?",
                    "slots": {"language": "lang"},
                    "situation": "Ask if she speaks English.",
                    "situation_fill": {"language": "en"},
                },
            ],
        }
        curriculum_from_dict(base)  # valid
        for bad, msg in (({"lingo": "en"}, "unknown slot"), ({"language": "kaffi"}, "not a valid fill"), ({"language": "nope"}, "unknown item")):
            raw = json.loads(json.dumps(base))
            raw["items"][3]["situation_fill"] = bad
            with self.assertRaisesRegex(CurriculumError, msg):
                curriculum_from_dict(raw)

    def test_cloze_names_the_meaning_before_the_partial_phrase(self):
        """Issue #59: "Complete the sentence." + «Ég skil…» didn't say whether «Ég skil.» (itself a
        complete, known utterance) or «Ég skil ekki.» was wanted. The cloze prompt now states the
        target meaning first, in both instructor languages, then the partial phrase; the answer,
        the partial and the pauses are unchanged."""
        from audiolesson.exercises import Builder

        expected = {
            ("en", "eg_skil_ekki"): ("Complete the sentence to say: I don't understand.", "Ég skil…"),
            ("en", "gott_ad_heyra"): ("Complete the sentence to say: Good to hear.", "Gott að…"),
            ("ja", "eg_skil_ekki"): ("「わかりません」と言うように、文を完成させてください。", "Ég skil…"),
            ("ja", "gott_ad_heyra"): ("「それはよかった」と言うように、文を完成させてください。", "Gott að…"),
        }
        for (lang, item_id), (narration, partial) in expected.items():
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=None if lang == "en" else lang)
            b = Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
            sc = Script(1, "L", cur.target_lang, lang)
            b.recall(sc, cur.by_id[item_id], "cloze")
            lane = [(s.type, s.text) for s in sc.segments if s.type in ("narrate", "speak", "answer")]
            self.assertEqual(lane[:2], [("narrate", narration), ("speak", partial)], (lang, item_id))
            self.assertIn(("answer", cur.by_id[item_id].target), lane)

    def test_every_cloze_prompt_carries_its_items_meaning(self):
        """Issue #59 regression guard, course-wide: no cloze exercise on the real course narrates
        a bare "Complete the sentence." — each one contains its target item's meaning."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        clozed = 0
        for it in cur.items:
            if it.kind != "phrase" or it.word_count < 3:
                continue
            sc = Script(1, "L", cur.target_lang, cur.known_lang)
            ex = b.recall(sc, it, "cloze")
            narration = " ".join(s.text for s in sc.segments if s.exercise == ex.index and s.type == "narrate")
            self.assertIn(it.meaning.strip().rstrip("."), narration, it.id)
            clozed += 1
        self.assertGreater(clozed, 100)

    def test_bridge_is_one_scene_across_both_lanes(self):
        """Owner comment on #48 (a real Lesson 4): «Góðan daginn» was cued as greeting *bakery
        staff*, then the partner said «Má ég setjast hérna?» and B's cue was about someone at
        *your table* — the target-language turns fit, the instructor's world didn't. A bridge now
        plays as one authored scene: its own setup for A, what the partner said (early
        encounters), and B's cue naming the partner's move; the standalone bakery situation is
        never narrated inside the exchange."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "L", cur.target_lang, cur.known_lang)
        b.connect(sc, [cur.by_id["godan_daginn"], cur.by_id["endilega"]])
        narr = [s.text for s in sc.segments if s.type == "narrate"]
        lane = [s.text for s in sc.segments if s.type in ("speak", "answer")]
        self.assertEqual(lane, ["Góðan daginn.", "Góðan daginn. Má ég setjast hérna?", "Endilega."])
        self.assertEqual(
            narr[1:],
            [
                "You're sitting at a shared table in a café. A woman comes over and greets you. Greet her back: good day.",
                "Good day. May I sit here?",
                "She asked if she may sit here. Tell her: by all means.",
            ],
        )
        self.assertFalse([n for n in narr if "bakery" in n], "the failure shape: A's standalone bakery scene inside the bridge")

    def test_bridge_gloss_fades_after_early_encounters(self):
        """Owner comment on #48: early partner input with untaught words gets its communicative
        move explained; later encounters may drop that support. The partner line is glossed on
        the learner's first two hearings of a bridge (LearnerState.bridges_heard, counted by
        apply_to_learner), not after — the scene cues stay, since they keep the task checkable."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        gloss = cur.by_id["endilega"].partner_cue_meaning

        def narrated() -> list[str]:
            b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
            sc = Script(1, "L", cur.target_lang, cur.known_lang)
            b.connect(sc, [cur.by_id["godan_daginn"], cur.by_id["endilega"]])
            return [s.text for s in sc.segments if s.type == "narrate"]

        self.assertIn(gloss, narrated())
        learner.bridges_heard["endilega"] = 2
        later = narrated()
        self.assertNotIn(gloss, later)
        self.assertIn(cur.by_id["endilega"].partner_cue_situation, later)

        # the planner records played bridges so the fade actually happens across lessons
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a", "kind": "phrase", "target": "A.", "meaning": "A.", "situation": "Situation A."},
                {"id": "b", "kind": "phrase", "target": "B.", "meaning": "B.", "situation": "Situation B.", "partner_cue": "Bridge.",
                 "partner_cue_after": "a", "partner_cue_setup": "Scene A.", "partner_cue_meaning": "Gloss.", "partner_cue_situation": "Scene B."},
            ] + [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(6)],
        }
        syn = curriculum_from_dict(raw)
        ls = LearnerState("is", "en", "A1")
        for i in ["a", "b"] + [f"w{i}" for i in range(6)]:
            ls.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="situation")
        sc = Planner(syn, ls, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, seed=1, new_items=0, max_new_items=0, dialogue_every=1000, drill_streak_limit=2, note_chance=0.0), today=TODAY).build()
        self.assertIn("b", sc.meta["bridges"])
        apply_to_learner(sc, ls, TODAY)
        self.assertEqual(ls.bridges_heard["b"], sc.meta["bridges"].count("b"))

    def test_bridge_scene_fields_are_validated(self):
        """A partner_cue bridge needs its whole scene (setup, meaning, situation); scene fields
        without a partner_cue are an authoring mistake too."""
        base = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a", "kind": "phrase", "target": "A.", "meaning": "A.", "situation": "Situation A."},
                {"id": "b", "kind": "phrase", "target": "B.", "meaning": "B.", "situation": "Situation B.", "partner_cue": "Bridge.",
                 "partner_cue_after": "a", "partner_cue_setup": "Scene A.", "partner_cue_meaning": "Gloss.", "partner_cue_situation": "Scene B."},
            ],
        }
        curriculum_from_dict(base)
        missing = json.loads(json.dumps(base))
        del missing["items"][1]["partner_cue_situation"]
        with self.assertRaisesRegex(CurriculumError, "whole scene"):
            curriculum_from_dict(missing)
        orphan = json.loads(json.dumps(base))
        orphan["items"][0]["partner_cue_setup"] = "Stray."
        with self.assertRaisesRegex(CurriculumError, "without a partner_cue"):
            curriculum_from_dict(orphan)

    def test_generated_sentence_prompts_carry_no_recall_disambiguators(self):
        """Issue #29 audit finding: a fill's gloss can carry a disambiguator meant for isolated
        recall ("English (the language)", "the hotel (after 'to' / 'for')", "work (to work)"),
        and constructions pasted it into sentence prompts — "Say: Do you speak English (the
        language)?" in most simulated lessons. A fill's ``in_sentence`` form is used instead.
        Every construction × fill, in both instructor languages, now resolves without a
        parenthetical, except the audited few where it tells the learner which word to produce
        (vinur vs vinkona; bróðir/systir covering older and younger). Isolated recall keeps the
        disambiguator."""
        informative = {None: {"vinur_minn", "vinkona_min"}, "ja": {"vinur_minn", "vinkona_min", "brodir_minn", "systir_min"}}
        for lang in (None, "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            for c in cur.items:
                if c.kind != "construction":
                    continue
                for slot, tag in c.slots.items():
                    for fill in cur.items_with_tag(tag):
                        if fill.id in informative[lang]:
                            continue
                        fills = cur.example_fill(c)
                        fills[slot] = fill
                        meaning = cur.resolve_slots(c, fills)[1]
                        # a construction's own authored annotation ("(feminine count word)") is
                        # deliberate guidance; only what the fills bring in is checked
                        for own in re.findall(r"[（(][^）)]*[）)]", c.meaning):
                            meaning = meaning.replace(own, "")
                        self.assertNotRegex(meaning, r"[（(]", (lang, c.id, fill.id))
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertEqual(cur.by_id["ensku"].meaning, "English (the language)")

    def test_eigdu_transfers_godur_gender_to_a_new_frame(self):
        """Issue #29 (owner comment on Lesson 3: grammar noticed but not transferred): «Eigðu
        góðan dag» was one more fixed string. ``eigdu_godur`` applies godur_gender's accusative
        agreement in the «Eigðu …» wish frame to the three nouns whose genders that note names,
        generating «Eigðu góða nótt.» / «Eigðu gott kvöld.» (never authored), in both instructor
        languages; and a learner who has learned everything before it gets the fills and the
        pattern in the same lesson, not several lessons of isolated «dag»/«nótt» drills."""
        expected = {
            None: {"dag_acc": ("Eigðu góðan dag.", "Have a good day."), "nott_acc": ("Eigðu góða nótt.", "Have a good night."),
                   "kvold_acc": ("Eigðu gott kvöld.", "Have a good evening.")},
            "ja": {"dag_acc": ("Eigðu góðan dag.", "良い一日を。"), "nott_acc": ("Eigðu góða nótt.", "良い夜を。"),
                   "kvold_acc": ("Eigðu gott kvöld.", "良い夕べを。")},
        }
        for lang, rows in expected.items():
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            for fill_id, pair in rows.items():
                self.assertEqual(cur.resolve_slots(cur.by_id["eigdu_godur"], {"time": cur.by_id[fill_id]}), pair)
            self.assertIn("eigdu_godur", cur.note_by_id["godur_gender"].transfer_items)
        sc, cur = self._lesson_introducing("dag_acc")
        new = sc.meta["new_items"]
        self.assertIn("eigdu_godur", new, new)
        generated = {ex.label.split(": ", 1)[1] for ex in sc.exercises if "eigdu_godur" in ex.item_ids and ex.kind != "intro"}
        self.assertTrue(generated - {"Eigðu góðan dag."}, generated)

    def test_recombination_connect_does_not_imply_one_scene(self):
        """Issue #69: a recombination-only connect pairs two independent situations — the owner's
        example is a street sign («Hvað þýðir þetta?») and a fish on a menu («Hvað heitir þetta á
        íslensku?»). The transition used to be "And then —", implying the second followed from
        the first. It is now neutral in both instructor languages; the exercise stays
        ``recombine`` and authored exchanges keep their own scene cues."""
        from audiolesson.exercises import Builder

        for lang, banned in ((None, "And then"), ("ja", "そして")):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            prompts = Prompts.load(lang or "en")
            b = Builder(cur, prompts, Timing(level="A1"), LearnerState("is", lang or "en", "A1"))
            sc = Script(1, "L", cur.target_lang, lang or "en")
            ex = b.connect(sc, [cur.by_id["hvad_thydir_thetta"], cur.by_id["hvad_heitir_thetta_a_islensku"]])
            self.assertEqual(ex.stage, "recombine")
            narr = [s.text for s in sc.segments if s.type == "narrate"]
            self.assertIn(prompts.get("connect_next"), narr)
            self.assertFalse([n for n in narr if banned in n], narr)

    def test_recombine_claims_novelty_only_for_a_sentence_never_presented(self):
        """Issue #68, the real Lesson 5 sequence: «Talar þú {language}?»'s intro presents
        «Talar þú ensku?» and a second fill («Talar þú íslensku?»); a later recombine that lands
        on one of those again used to say "Now something you haven't heard yet". The novelty
        claim now needs the exact sentence never to have been presented — this lesson, an
        earlier lesson (persisted), or as a met item's own target — and reuse stays allowed
        with neutral wording."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        prompts = Prompts.load("en")
        novelty = prompts.get("recombine_new", meaning="").split(".")[0]  # "Now something you haven't heard yet"

        def learner_with(fills):
            ls = LearnerState("is", "en", "A1")
            for i in fills:
                ls.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="meaning")
            return ls

        def recombine_after_intro(ls):
            b = Builder(cur, prompts, Timing(level="A1"), ls)
            b.in_lesson.add("talar_thu")
            sc = Script(1, "L", cur.target_lang, cur.known_lang)
            b.intro(sc, cur.by_id["talar_thu"])
            intro_answers = {s.text for s in sc.segments if s.type in ("speak", "answer")}
            ex = b.recall(sc, cur.by_id["talar_thu"], "recombine")
            narr = " ".join(s.text for s in sc.segments if s.exercise == ex.index and s.type == "narrate")
            answer = [s.text for s in sc.segments if s.exercise == ex.index and s.type == "answer"][0]
            return b, intro_answers, narr, answer

        # only two languages known: the intro uses both, so the recombine must repeat one
        _, heard, narr, answer = recombine_after_intro(learner_with(["ensku", "islensku"]))
        self.assertIn(answer, heard)
        self.assertNotIn(novelty, narr, "a repeated sentence was presented as new")

        # a third known language: the recombine finds an unheard sentence and may say so
        b, heard, narr, answer = recombine_after_intro(learner_with(["ensku", "islensku", "japonsku"]))
        self.assertNotIn(answer, heard)
        self.assertIn(novelty, narr)

        # ...and once presented, it stays heard in later lessons (persisted via the planner meta)
        ls = learner_with(["ensku"])
        ls.heard_utterances.add("talar þú japönsku")
        self.assertFalse(Builder(cur, prompts, Timing(level="A1"), ls).is_new_utterance("Talar þú japönsku?"))

    def test_heard_utterances_persist_across_lessons(self):
        """Issue #68: what a lesson presented is recorded in the learner state, and survives a
        save/load round trip, so a later lesson doesn't call it new."""
        import tempfile

        learner, scripts = course(2)
        self.assertTrue(learner.heard_utterances)
        self.assertTrue(set(scripts[0].meta["heard_utterances"]) <= learner.heard_utterances)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            learner.save(path)
            self.assertEqual(LearnerState.load(path).heard_utterances, learner.heard_utterances)

    def test_connect_plays_the_owners_real_curriculum_worked_example(self):
        """Issue #48: the real authored pair from the owner's own review — with the
        instructor scaffolding stripped away, the target-language turns alone should form
        one coherent exchange: "Gætirðu talað hægar?" -> "Auðvitað. Herbergið er númer
        tuttugu og þrjú." -> "Gætirðu endurtekið þetta?"."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        first = cur.by_id["gaetirdu_talad_haegar"]
        second = cur.by_id["gaetirdu_endurtekid_thetta"]
        self.assertEqual(second.partner_cue_after, first.id)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.connect(sc, [first, second])
        turns = [(s.speaker, s.text) for s in sc.segments if s.type in ("answer", "speak")]
        self.assertEqual(
            turns,
            [
                ("native_a", "Gætirðu talað hægar?"),
                ("native_b", "Auðvitað. Herbergið er númer tuttugu og þrjú."),
                ("native_a", "Gætirðu endurtekið þetta?"),
            ],
        )

    def test_connect_falls_back_to_the_english_bridge_without_an_authored_partner_cue(self):
        """No item in this curriculum authors a ``partner_cue`` — connect() must not break;
        it falls back to the original English "And then —" bridge, unchanged. This is the
        common case (most items have no authored bridge at all), and matches the small
        fr-en-a1 sample curriculum most other tests build lessons from."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}.", "situation": f"Situation {i}."}
                for i in range(10)
            ],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(10):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        planner = Planner(
            cur,
            learner,
            Prompts.load("en"),
            Timing(level="A1"),
            PlanConfig(minutes=30, seed=1, dialogue_every=1000, drill_streak_limit=3, note_chance=0.0),
            today=TODAY,
        )
        sc = planner.build()
        ex = next(ex for ex in sc.exercises if ex.kind == "connect")
        segs = [s for s in sc.segments if s.exercise == ex.index]
        self.assertFalse(any(s.speaker == "native_b" for s in segs), "no discourse item exists to speak a partner line")
        prompts = Prompts.load("en")
        narrations = [s.text for s in segs if s.type == "narrate"]
        self.assertIn(prompts.get("connect_next"), narrations)

    def _real_streak_lesson(self, known: list[str]) -> Script:
        """A real is-en lesson whose drill streak keeps tripping with nothing but connect() to
        break it: no dialogue, no notes, only ``known`` items ready for "situation", padded with
        known words that have no situation cue (review material connect() can't use)."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        padding = ["ja", "nei", "lika", "islensku", "ensku", "japonsku", "thysku", "fronsku", "donsku", "vegabref"]
        for i in known + padding:
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="situation")
        cfg = PlanConfig(minutes=20, seed=1, new_items=0, max_new_items=0, dialogue_every=1000, drill_streak_limit=3, max_notes=0, max_streak_relief_notes=0)
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()

    def test_connect_does_not_replay_the_real_lesson_4_pair(self):
        """Issue #55: a real Lesson 4 played ``connect: ha+eg_skil`` ("Ha?" → "Ég skil.") over
        and over — every time the drill streak tripped, ``_connect_pair`` picked the first
        eligible same-topic pair again, with no history of what it had already played. With
        only those two items known, the pair may be played once; after that the streak breaker
        has nothing unused left and must stop the lesson rather than loop back to it."""
        sc = self._real_streak_lesson(["ha", "eg_skil"])
        pairs = [frozenset(ex.item_ids) for ex in sc.exercises if ex.kind == "connect"]
        self.assertEqual(pairs, [frozenset({"ha", "eg_skil"})], "the same fallback pair must not be replayed")
        streak = longest = 0
        for ex in sc.exercises:
            streak = streak + 1 if ex.kind == "recall" else 0
            longest = max(longest, streak)
        self.assertLessEqual(longest, 3, "exhausted pairs must not let the streak run on unbounded either")

    def test_connect_varies_its_pairs_while_unused_ones_exist(self):
        """Issue #55: the same streak-heavy lesson with more clarifying items known must use a
        different pair every time, and not just the same item with a new partner each time."""
        known = ["ha", "eg_skil", "eg_skil_ekki", "gaetirdu_talad_haegar", "hvad_thydir_thetta", "takk", "godan_daginn", "bless"]
        sc = self._real_streak_lesson(known)
        pairs = [frozenset(ex.item_ids) for ex in sc.exercises if ex.kind == "connect"]
        self.assertGreaterEqual(len(pairs), 3, pairs)
        self.assertEqual(len(pairs), len(set(pairs)), f"a connect pair was replayed: {pairs}")
        # the first few spread across different items before any one item is paired again
        first = [i for p in pairs[:3] for i in p]
        self.assertEqual(len(first), len(set(first)), f"the first pairs reused an item while fresh ones remained: {pairs[:3]}")

    def test_connect_prefers_an_authored_partner_cue_pair(self):
        """Issue #55: where both are available, an authored ``partner_cue`` pair (a coherent
        target-language exchange, issue #48) beats a generic same-topic fallback pair — even
        though the generic pair comes first in curriculum order — and plays in its authored
        order, since the cue only fits after its named predecessor."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}.", "situation": f"Situation {i}.", "topics": ["t"]}
                for i in range(4)
            ]
            + [
                {"id": "a", "kind": "phrase", "target": "A.", "meaning": "A.", "situation": "Situation A.", "topics": ["t"]},
                {
                    "id": "b",
                    "kind": "phrase",
                    "target": "B.",
                    "meaning": "B.",
                    "situation": "Situation B.",
                    "topics": ["t"],
                    "partner_cue": "Bridge line.",
                    "partner_cue_after": "a",
                    "partner_cue_setup": "Scene: say A.", "partner_cue_meaning": "Bridge meaning.", "partner_cue_situation": "Scene: say B.",
                },
            ],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for it in cur.items:
            learner.items[it.id] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="situation")
        cfg = PlanConfig(minutes=20, seed=1, dialogue_every=1000, drill_streak_limit=3, note_chance=0.0)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        connects = [ex for ex in sc.exercises if ex.kind == "connect"]
        self.assertTrue(connects)
        self.assertEqual(connects[0].item_ids, ["a", "b"], [ex.item_ids for ex in connects])
        pairs = [frozenset(ex.item_ids) for ex in connects]
        self.assertEqual(len(pairs), len(set(pairs)), pairs)

    def test_per_arc_connected_use_is_never_satisfied_by_one_unrelated_pair(self):
        """Issue #55: an arc too small to pair with itself widens to other known material — but
        the per-arc guarantee is about *that arc's* material, so the widened pair must include
        one of its own items. Before, a same-topic pair of unrelated review items (``w0``+``w1``)
        outranked the arc's own item and was replayed for every arc, "satisfying" each one's
        connected use without ever touching what it taught."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}.", "situation": f"Situation {i}.", "topics": ["rev"]}
                for i in range(6)
            ]
            + [
                {"id": "a0", "kind": "phrase", "target": "Boga 0.", "meaning": "Arc one.", "situation": "Arc one situation.", "topics": ["p"]},
                {"id": "b0", "kind": "phrase", "target": "Boga 1.", "meaning": "Arc two.", "situation": "Arc two situation.", "topics": ["q"]},
            ],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(6):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="situation")
        cfg = PlanConfig(minutes=30, seed=1, new_items=1, max_new_items=1, dialogue_every=1000, drill_streak_limit=1000, note_chance=0.0)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        connects = [ex.item_ids for ex in sc.exercises if ex.kind == "connect"]
        self.assertEqual(set(sc.meta["new_items"]), {"a0", "b0"}, "both arcs must have been taught for this test to mean anything")
        self.assertTrue(any("a0" in ids for ids in connects), connects)
        self.assertTrue(any("b0" in ids for ids in connects), connects)
        for ids in connects:
            self.assertTrue({"a0", "b0"} & set(ids), f"an arc's connected use played only unrelated review items: {ids}")

    def test_connect_is_labelled_exchange_only_with_an_authored_bridge(self):
        """Issue #48: a connect() without a compatible target-language bridge is recombination
        practice, not evidence of conversation — the exercise says which one it was, and the
        lesson's ``partner_exchanges`` only counts the former (plus dialogues)."""
        from audiolesson.exercises import Builder

        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a", "kind": "phrase", "target": "A.", "meaning": "A.", "situation": "Situation A."},
                {"id": "c", "kind": "phrase", "target": "C.", "meaning": "C.", "situation": "Situation C."},
                {"id": "b", "kind": "phrase", "target": "B.", "meaning": "B.", "situation": "Situation B.", "partner_cue": "Bridge.", "partner_cue_after": "a",
                 "partner_cue_setup": "Scene: say A.", "partner_cue_meaning": "Bridge meaning.", "partner_cue_situation": "Scene: say B."},
            ],
        }
        cur = curriculum_from_dict(raw)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        self.assertEqual(b.connect(sc, [cur.by_id["a"], cur.by_id["b"]]).stage, "exchange")
        self.assertEqual(b.connect(sc, [cur.by_id["c"], cur.by_id["b"]]).stage, "recombine")

    def test_every_authored_partner_cue_is_playable(self):
        """Issue #48 content guard: connect() only pairs items with a situation cue, so a
        ``partner_cue`` whose item or predecessor has none could never be heard."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        authored = [it for it in cur.items if it.partner_cue]
        self.assertGreaterEqual(len(authored), 10)
        for it in authored:
            self.assertTrue(it.has_situation and cur.by_id[it.partner_cue_after].has_situation, it.id)

    def test_fixed_phrase_families_become_constructions(self):
        """Issue #29 audit, category 2: «Hvenær fer …?» and «… virkar ekki» were three fixed
        strings each. Each is now one construction over a noun pool, no fixed phrase duplicates
        a sentence it generates, and what used those phrases (a dialogue turn, a bridge) speaks
        the construction with the fill it names."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for con_id, tag, fills, frame in (("hvenaer_fer", "departs", {"strætó", "flugid", "ferjan"}, r"^Hvenær fer \w+\?$"),
                                          ("virkar_ekki", "breaks", {"sturtan", "ljosid", "netid"}, r"^\w+ virkar ekki\.$")):
            self.assertEqual(cur.by_id[con_id].slots, {next(iter(cur.by_id[con_id].slots)): tag})
            self.assertEqual({i.id for i in cur.items_with_tag(tag)}, fills)
            self.assertFalse([i.id for i in cur.items if i.kind == "phrase" and re.match(frame, i.target)], con_id)
        ljos = cur.resolve_slots(cur.by_id["virkar_ekki"], {"thing": cur.by_id["ljosid"]})
        self.assertEqual(ljos, ("Ljósið virkar ekki.", "The light doesn't work."))

        dlg = cur.dialogue_by_id["flugvollur"]
        self.assertIn("flugid", dlg.required_items)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), fresh())
        sc = Script(1, "L", cur.target_lang, cur.known_lang)
        b.dialogue(sc, dlg)
        self.assertIn("Hvenær fer flugið?", [s.text for s in sc.segments if s.type == "answer"])

        b.in_lesson.update({"strætó"})
        sc = Script(1, "L", cur.target_lang, cur.known_lang)
        b.connect(sc, [cur.by_id["hvenaer_fer"], cur.by_id["hvad_kostar_i_straeto"]])
        self.assertEqual([s.text for s in sc.segments if s.type in ("speak", "answer")],
                         ["Hvenær fer strætó?", "Eftir tíu mínútur.", "Hvað kostar í strætó?"])

    def test_dative_feeling_is_a_construction_paired_with_its_question(self):
        """Issue #29 (case): «Mér líður …» was four unrelated fixed phrases, and «Hvernig líður
        þér?» was taught ~870 items later. The adverbs are now a pool for one construction, the
        question sits right after it, and «Hvernig líður þér?» → «… En þér?» → «Mér líður vel.»
        is one bridge."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        con = cur.by_id["mer_lidur"]
        self.assertEqual({i.id for i in cur.items_with_tag("how_feel")}, {"vel", "illa", "betur", "agaetlega"})
        self.assertFalse([i.id for i in cur.items if i.kind == "phrase" and i.target.startswith("Mér líður") and i.id != "mer_lidur_illa"],
                         "the construction generates these; only the dialogue's «Mér líður illa.» stays a phrase")
        self.assertLess(abs(cur.by_id["hvernig_lidur_ther"].order - con.order), 15)
        for lang, expected in (("en", "I feel alright."), ("ja", "気分はまあまあです。")):
            c = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            self.assertEqual(c.resolve_slots(c.by_id["mer_lidur"], {"how": c.by_id["agaetlega"]}), ("Mér líður ágætlega.", expected))
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        b.in_lesson.add("vel")
        sc = Script(1, "L", cur.target_lang, cur.known_lang)
        ex = b.connect(sc, [cur.by_id["hvernig_lidur_ther"], con])
        self.assertEqual(ex.stage, "exchange")
        self.assertEqual([s.text for s in sc.segments if s.type in ("speak", "answer")],
                         ["Hvernig líður þér?", "Mér líður betur, takk. En þér?", "Mér líður vel."])
        self.assertIn("mer_lidur", cur.note_by_id["mer_ther"].transfer_items)

    def test_partner_bridges_reach_beyond_the_first_modules(self):
        """Issue #48: with bridges only in modules 01–03, a simulated course had no partner
        exchange outside dialogues from about lesson 30 on. Modules 04–13 each author some, and
        one of them plays as a single scene in both instructor languages."""
        from audiolesson.exercises import Builder

        modules = sorted((ROOT / "curricula" / "is-en").glob("[0-9][0-9]-*.toml"))
        for f in modules[3:13]:
            self.assertTrue("partner_cue = " in f.read_text(encoding="utf-8"), f"{f.name} authors no partner bridge")
        for lang, setup in (("en", "You slipped on the ice on a walk with a friend. Tell her you fell."),
                            ("ja", "友達と散歩中、氷で滑りました。転んだと言ってください。")):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            b = Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
            sc = Script(1, "L", cur.target_lang, cur.known_lang)
            ex = b.connect(sc, [cur.by_id["eg_datt"], cur.by_id["eg_er_i_lagi"]])
            self.assertEqual(ex.stage, "exchange")
            self.assertEqual([s.text for s in sc.segments if s.type in ("speak", "answer")], ["Ég datt.", "Æ! Er allt í lagi?", "Ég er í lagi."])
            narr = [s.text for s in sc.segments if s.type == "narrate"]
            self.assertIn(setup, narr)
            self.assertIn(cur.by_id["eg_er_i_lagi"].partner_cue_situation, narr)
            self.assertNotIn(cur.by_id["eg_er_i_lagi"].situation, narr, "B's standalone scene stays out of the bridge")

    def test_early_real_lessons_contain_a_partner_exchange(self):
        """Issue #48: a real Lesson 4 was all instructor → learner retrieval — its only
        "connected" moments were ``Ha?`` → [English "And then —"] → ``Ég skil.``, and the first
        authored dialogue isn't reachable until its items are learned. With authored bridges
        among the first modules' items (and #55's ranking preferring them), every lesson from
        the second on has at least one partner target-language exchange, and the Lesson 4
        pair itself now plays as one: "Ha?" → partner repeats → "Ég skil."."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for n in range(1, 7):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20), today=day).build()
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
            if n >= 2:
                self.assertGreaterEqual(sc.meta["partner_exchanges"], 1, f"lesson {n} had no partner interaction")
        from audiolesson.exercises import Builder

        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.connect(sc, [cur.by_id["ha"], cur.by_id["eg_skil"]])
        turns = [(s.speaker, s.text) for s in sc.segments if s.type in ("answer", "speak")]
        self.assertEqual([t[0] for t in turns], ["native_a", "native_b", "native_a"], turns)

    def test_dialogue_requirements_need_durable_evidence_or_this_lesson(self):
        """Issue #27's durable gate, kept under #48 (owner review on PR #56): an item met in an
        earlier lesson but with no durable evidence yet (``durable_successes == 0``) must not
        satisfy a dialogue's requirements — only ``knows()`` (durable) or the same-lesson
        exception (introduced earlier in *this* lesson, #25) may. A first cut of #48 widened
        this to ``has_met``, quietly undoing #27; early partner interaction comes from authored
        connect() exchanges instead, which unlock nothing."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a", "kind": "phrase", "target": "Halló.", "meaning": "Hello."},
                {"id": "b", "kind": "phrase", "target": "Bless.", "meaning": "Bye."},
            ],
            "dialogues": [
                {
                    "id": "d",
                    "setting": "A short chat.",
                    "requires": ["a", "b"],
                    "turns": [{"cue": "Say hello.", "expect": "a", "partner": "Halló."}, {"cue": "Say bye.", "expect": "b"}],
                }
            ],
        }
        cur = curriculum_from_dict(raw)

        def planner_with(durable: int) -> Planner:
            learner = LearnerState("is", "en", "A1")
            for i in ("a", "b"):
                learner.items[i] = ItemState(due=TODAY.isoformat(), successes=1, durable_successes=durable, stage="meaning")
            return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, seed=1), today=TODAY)

        self.assertIsNone(planner_with(0).eligible_dialogue(), "met but not durable must not unlock a dialogue")
        self.assertIsNotNone(planner_with(2).eligible_dialogue())
        same_lesson = planner_with(0)
        same_lesson.builder.in_lesson.update({"a", "b"})
        self.assertIsNotNone(same_lesson.eligible_dialogue(), "items introduced this lesson may count (#25)")

    @staticmethod
    def _filler_family(extra_after: int = 3) -> dict:
        """Six slot fillers, then their construction (prereq: the second filler), then a few
        unrelated phrases — the shape of the real ``acc_language`` block → ``talar_thu``."""
        return {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": f"f{i}", "kind": "vocab", "target": f"fyll{i}", "meaning": f"filler {i}", "tags": ["lang"]} for i in range(6)]
            + [
                {
                    "id": "pat",
                    "kind": "construction",
                    "target": "Talar þú {x}?",
                    "meaning": "Do you speak {x}?",
                    "slots": {"x": "lang"},
                    "example": {"x": "f1"},
                    "prereqs": ["f1"],
                }
            ]
            + [{"id": f"p{i}", "kind": "phrase", "target": f"Setning {i}.", "meaning": f"Phrase {i}."} for i in range(extra_after)],
        }

    def _select(self, raw: dict, learner: LearnerState, count: int) -> list[str]:
        cur = curriculum_from_dict(raw)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY)
        return [i.id for i in planner.select_new(count)]

    def test_an_arc_reaches_the_construction_its_fillers_unlock(self):
        """Issue #29 (owner comment on a real Lesson 4): an arc of six language fillers ended
        right before «Talar þú {language}?», so every filler was only ever an isolated
        flashcard. The arc should be the smallest set that creates the capability: two
        fillers, then the construction — the other four wait (they are neither chosen before
        the pattern nor piled on after it in the same arc)."""
        chosen = self._select(self._filler_family(), LearnerState("is", "en", "A1"), 6)
        self.assertEqual(chosen[:3], ["f0", "f1", "pat"], chosen)
        self.assertFalse({"f2", "f3", "f4", "f5"} & set(chosen), chosen)

    def test_an_arc_boundary_does_not_fall_between_fillers_and_their_construction(self):
        """Issue #29: when ``count`` runs out right after the second filler, the construction it
        just made teachable comes along (one over ``count``); when it runs out after a single
        filler, that lone filler is left for the next arc instead of ending this one."""
        raw = self._filler_family()
        raw["items"] = [{"id": f"q{i}", "kind": "phrase", "target": f"Fyrst {i}.", "meaning": f"First {i}."} for i in range(3)] + raw["items"]
        self.assertEqual(self._select(raw, LearnerState("is", "en", "A1"), 5), ["q0", "q1", "q2", "f0", "f1", "pat"])
        self.assertEqual(self._select(raw, LearnerState("is", "en", "A1"), 4), ["q0", "q1", "q2"])

    def test_fillers_wait_for_their_construction_then_come_back_as_transfer(self):
        """Issue #29: while the construction is met but not yet learned, more fillers are held
        (not another homogeneous block); once it's learned they return — at most two per arc,
        so the construction gives each one a transfer opportunity instead of a new block."""
        raw = self._filler_family(extra_after=6)
        learner = LearnerState("is", "en", "A1")
        for i in ("f0", "f1", "pat"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=1, durable_successes=0, stage="meaning")
        self.assertEqual(self._select(raw, learner, 4), ["p0", "p1", "p2", "p3"])
        for i in ("f0", "f1", "pat"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        chosen = self._select(raw, learner, 4)
        self.assertEqual(sum(1 for i in chosen if i.startswith("f")), 2, chosen)
        self.assertEqual(chosen[:2], ["f2", "f3"], chosen)

    def test_a_held_filler_is_never_starved(self):
        """Issue #29's holds must not strand material: across a simulated course on the small
        synthetic family, every filler is eventually introduced."""
        cur = curriculum_from_dict(self._filler_family(extra_after=6))
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for _ in range(12):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, seed=1), today=day).build()
            apply_to_learner(sc, learner, day)
            day += timedelta(days=2)
        self.assertEqual({i.id for i in cur.items} - set(learner.items), set())

    def test_real_language_family_reaches_talar_thu_in_the_same_lesson(self):
        """Issue #29, the owner's own Lesson 4 example on the real is-en course: with everything
        before the language block learned, the lesson that introduces the first languages also
        introduces «Talar þú {language}?» and generates a sentence with it that was never an
        authored item — parts → construction → novel generation — without first drilling the
        whole block of six languages as isolated words."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        first = cur.by_id["islensku"].order
        for it in cur.items:
            if it.order < first:
                learner.items[it.id] = ItemState(due=(TODAY + timedelta(days=30)).isoformat(), successes=3, durable_successes=3, stage="situation")
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY).build()
        new = sc.meta["new_items"]
        self.assertIn("talar_thu", new, new)
        languages = [i for i in new if "acc_language" in cur.by_id[i].tags]
        self.assertLessEqual(len(languages[: new.index("talar_thu")]), 2, new)
        # every non-intro exercise on the pattern resolves it from known parts; at least one must
        # use a fill other than the worked example the intro modelled
        generated = [ex.label for ex in sc.exercises if ex.kind in ("recall", "generative") and "talar_thu" in ex.item_ids]
        example = cur.resolve_slots(cur.by_id["talar_thu"], cur.example_fill(cur.by_id["talar_thu"]))[0]
        self.assertTrue(any(example not in label for label in generated), f"no novel Talar þú sentence: {generated}")

    def test_high_drill_streak_wins_over_a_due_reactivation_too(self):
        """Owner review on #41: the streak breaker used to run *after* step 1 (a due
        scheduled reactivation), guarded by ``if not acted``, so a due reactivation could
        still win and continue the very run the streak check exists to interrupt — the
        streak's own trigger condition never got a chance to act that turn. It must run
        before any branch that would emit another isolated recall, including step 1, not
        only the ordinary review path (step 4) the earlier tests above cover.

        One new item is introduced immediately (``new_items=1``), scheduling a reactivation
        a few exercises later; with ``drill_streak_limit=2``, the reactivation's due turn
        coincides with the streak already being at the limit. The note must win that turn."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": (
                [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(10)]
                + [{"id": "n0", "kind": "phrase", "target": "Nýtt.", "meaning": "New."}]
            ),
            "notes": [{"id": "n1", "text": "A cultural fact."}],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(10):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        planner = Planner(
            cur,
            learner,
            Prompts.load("en"),
            Timing(level="A1"),
            PlanConfig(minutes=30, seed=1, new_items=1, dialogue_every=1000, drill_streak_limit=2, note_chance=0.0),
            today=TODAY,
        )
        sc = planner.build()
        kinds = [ex.kind for ex in sc.exercises if ex.kind != "opening"]
        self.assertEqual(kinds[0], "intro", kinds)
        self.assertEqual(kinds[1:3], ["recall"] * 2, kinds)
        self.assertEqual(kinds[3], "note", f"{kinds}: a due reactivation must not win over the streak breaker")

    def test_trailing_drill_streak_resets_across_a_multi_exercise_iteration(self):
        """Owner review follow-up on #40: a single ``build()`` loop iteration can append
        several exercises at once — a milestone note plus its discrimination recalls, via
        ``_maybe_note``/``do_discriminate`` — so the trailing drill streak must reflect the
        actual exercise sequence, not the previous streak plus one just because the
        iteration's *last* exercise happens to be a recall. Five recalls, then a note, then
        two more recalls: the note resets the streak, so the trailing count is 2, not 6."""
        cur = load_curriculum(CURRICULUM)
        planner = Planner(cur, LearnerState("fr", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=1))
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        for kind in ("recall", "recall", "recall", "recall", "recall", "note", "recall", "recall"):
            sc.new_exercise(kind, None, [], kind)
        self.assertEqual(planner._trailing_drill_streak(sc), 2)

    def test_early_icelandic_lessons_mix_full_sentences_with_greetings(self):
        """Issue #12: the first few lessons were nothing but one- and two-word greetings to
        memorize. Guard against sliding back to that: among the first 10 items introduced,
        several should be genuine multi-word sentences, not just single words."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        first_ten = [it for it in cur.items if it.order < 10]
        self.assertEqual(len(first_ten), 10)
        full_sentences = [it for it in first_ten if it.word_count >= 3]
        self.assertGreaterEqual(len(full_sentences), 3, first_ten)

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
        """Ordinary cultural asides are rationed to ~1 per 12 minutes; milestones (issue #34
        point 3 added a second: ``three_kinds_of_sorry`` alongside ``godur_gender``) are
        curriculum events, not filler, so they neither draw on that ration nor shrink it for
        the asides that do — a lesson where both happen to fire can rack up more than 2 notes
        total without that being a rationing failure. Issue #44 point 1 added a third, small
        exemption: once the ordinary ration is spent, up to ``max_streak_relief_notes`` (2 by
        default) more asides may fire specifically to break up a drill streak with no eligible
        dialogue — bounded, not unlimited, so the ceiling here is the ration plus that
        allowance, not the ration alone."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertGreaterEqual(len(cur.notes), 40)
        learner = LearnerState("is", "en", "A1")
        learner.feedback_mode = "auto"
        day = TODAY
        heard: list[str] = []
        cfg_for_ceiling = PlanConfig(minutes=30)
        for _ in range(12):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=2), today=day).build()
            notes = [e for e in sc.exercises if e.kind == "note"]
            asides = [e for e in notes if not cur.note_by_id[e.label.split(": ")[1]].milestone]
            self.assertLessEqual(len(asides), 2 + cfg_for_ceiling.max_streak_relief_notes)
            for e in notes:
                note = cur.note_by_id[e.label.split(": ")[1]]
                if not note.milestone:
                    self.assertNotIn(note.id, heard, "no aside repeats while unheard asides remain")
                heard.append(note.id)
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        self.assertGreater(len(heard), 4)
        self.assertEqual(sum(learner.notes_heard.values()), len(heard))

    def test_note_waits_for_the_expression_it_recommends(self):
        """Issue #66, the real Lesson 5 case: the «enska» note advises "Saying «ég er að læra
        íslensku» usually makes them switch back" and is triggered by ``talar_thu`` — which comes
        before ``eg_er_ad_laera`` teaches that expression. ``Note.requires`` holds it back until
        each required item is learned or introduced earlier in the same lesson; a note that only
        *illustrates* a word («tölva» in «islenska») needs no requirement."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertEqual(cur.note_by_id["enska"].requires, ["eg_er_ad_laera"])
        self.assertFalse(cur.note_by_id["islenska"].requires)
        learner = LearnerState("is", "en", "A1")
        for i in ("talar_thu", "eg_tala_sma_islensku", "ensku", "islensku"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="meaning")
        for seed in range(6):
            planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=seed), today=TODAY)
            self.assertNotEqual(getattr(planner._pick_note(["talar_thu"]), "id", None), "enska")
            planner.builder.in_lesson.add("eg_er_ad_laera")  # introduced earlier this lesson
            self.assertEqual(planner._pick_note(["talar_thu"]).id, "enska")
        learner.items["eg_er_ad_laera"] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="meaning")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=0), today=TODAY)
        self.assertEqual(planner._pick_note(["talar_thu"]).id, "enska")

        # across a simulated course, «enska» never plays before eg_er_ad_laera is available
        ls = LearnerState("is", "en", "A1")
        day = TODAY
        for _ in range(20):
            sc = Planner(cur, ls, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20), today=day).build()
            labels = [e.label for e in sc.exercises]
            if "note: enska" in labels:
                intro = next((k for k, e in enumerate(sc.exercises) if e.kind == "intro" and "eg_er_ad_laera" in e.item_ids), None)
                self.assertTrue(ls.knows("eg_er_ad_laera") or (intro is not None and intro < labels.index("note: enska")), labels)
            apply_to_learner(sc, ls, day)
            day += timedelta(days=1)

        bad = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": "a", "kind": "phrase", "target": "A.", "meaning": "A."}],
               "notes": [{"id": "n", "text": "Say «A».", "items": ["a"], "requires": ["nope"]}]}
        with self.assertRaisesRegex(CurriculumError, "unknown item 'nope'"):
            curriculum_from_dict(bad)

    def test_milestone_note_never_fires_before_all_its_items_are_known(self):
        """Every milestone note (issue #29 pilot 2's góðan/góða/gott gender-agreement note,
        and issue #34 point 3's afsakið/fyrirgefðu/því miður contrast note) must never appear
        before every one of its own items has at least been exercised, unlike an ordinary
        cultural aside which only needs one related item to have just been practised.
        ``has_met`` alone lags a lesson behind (a newly introduced item isn't persisted to
        ``LearnerState`` until ``apply_to_learner()`` runs after the whole lesson is built), so
        the check here is against the state *after* applying the same lesson the note appeared
        in — which must already know all of that note's items."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        milestones = {n.id: n.items for n in cur.notes if n.milestone}
        self.assertGreaterEqual(len(milestones), 2)
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        fired: set[str] = set()
        # A fixed, fast pace (not auto-escalation, which stays too slow to reach a milestone
        # whose items sit as deep as order ~700 within a reasonable number of simulated
        # lessons — issue #29 owner review added "godur_gender_nominative", gated on items
        # spread across modules 1/7/17).
        for _ in range(80):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=10, seed=3), today=day).build()
            played = {e.label.split(": ")[1] for e in sc.exercises if e.kind == "note" and e.label.split(": ")[1] in milestones}
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
            for note_id in played:
                self.assertTrue(
                    all(learner.has_met(i) for i in milestones[note_id]),
                    f"{note_id} fired in a lesson that didn't end up knowing all its items",
                )
                fired.add(note_id)
            if fired == set(milestones):
                break
        self.assertEqual(fired, set(milestones), "not every milestone note fired across simulated lessons")

    def test_milestone_note_is_followed_by_contrastive_discrimination(self):
        """Issue #34 point 2: right after a milestone plays, the lesson must immediately
        switch between two *different* of its own already-known examples ("notice, name,
        discriminate") — reusing each item's own ``situation`` (all of both milestones' items
        have one) — never just one recall (that would be retrieval, not discrimination) and
        never zero (owner review on #38: a milestone that fires must complete its
        discrimination block even if the lesson runs slightly over its nominal time target).
        Checked for every milestone note in the curriculum, not just ``godur_gender``.

        A discrimination candidate may come from ``transfer_items`` too, not only the
        milestone's own gating ``items`` (issue #29, owner review: applying the pattern to
        new vocabulary once it's known, not just replaying the same fixed examples)."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        milestones = {n.id: set(n.items) | set(n.transfer_items) for n in cur.notes if n.milestone}
        self.assertGreaterEqual(len(milestones), 2)
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        checked: set[str] = set()
        # Fixed, fast pace, not auto-escalation -- see test_milestone_note_never_fires_...
        # above for why (a milestone's items can sit as deep as order ~700).
        for _ in range(80):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=10, seed=3), today=day).build()
            note_positions = [(i, e.label.split(": ")[1]) for i, e in enumerate(sc.exercises) if e.kind == "note" and e.label.split(": ")[1] in milestones]
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
            for note_idx, note_id in note_positions:
                gate_ids = milestones[note_id]
                self.assertGreater(len(sc.exercises), note_idx + 2, f"{note_id} wasn't followed by two discrimination exercises")
                first, second = sc.exercises[note_idx + 1], sc.exercises[note_idx + 2]
                for ex in (first, second):
                    self.assertEqual((ex.kind, ex.stage), ("recall", "situation"))
                    # a construction's recall also lists the fill it was generated with (support
                    # exposure); the practised item itself is always first
                    self.assertTrue(len(ex.item_ids) == 1 or cur.by_id[ex.item_ids[0]].kind == "construction", ex.item_ids)
                    self.assertIn(ex.item_ids[0], gate_ids)
                self.assertNotEqual(first.item_ids[0], second.item_ids[0])
                checked.add(note_id)
            if checked == set(milestones):
                break
        self.assertEqual(checked, set(milestones), "not every milestone note fired across simulated lessons")

    def _transfer_curriculum(self):
        """A synthetic milestone with transfer_items, isolated from any real-curriculum
        content decision (issue #29, owner review round 2: the first cut of this test used
        the real ``godur_gender`` note, which coupled the test's validity to a specific
        curriculum-content choice that turned out to need correcting — see
        ``test_...nominative`` below and docs/HANDOFF.md). This tests the *mechanism* only:
        whether ``transfer_items`` gates milestone firing, and whether ``do_discriminate``
        reaches for a known one."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a", "kind": "phrase", "target": "A.", "meaning": "A.", "situation": "Situation A."},
                {"id": "b", "kind": "phrase", "target": "B.", "meaning": "B.", "situation": "Situation B."},
                {"id": "c", "kind": "phrase", "target": "C.", "meaning": "C.", "situation": "Situation C."},
                {"id": "t", "kind": "phrase", "target": "T.", "meaning": "T.", "situation": "Situation T."},
            ],
            "notes": [
                {
                    "id": "milestone_with_transfer",
                    "milestone": True,
                    "items": ["a", "b", "c"],
                    "transfer_items": ["t"],
                    "text": "A milestone note.",
                }
            ],
        }
        return curriculum_from_dict(raw)

    def test_milestone_fires_without_any_of_its_transfer_items_being_known(self):
        """Issue #29, owner review: a milestone's ``transfer_items`` (extra discrimination
        material demonstrating the pattern applies to new vocabulary, not just its own gating
        examples) must never delay the milestone itself — it exists specifically to introduce
        that transfer material, so requiring it known first would be circular."""
        cur = self._transfer_curriculum()
        learner = LearnerState("is", "en", "A1")
        learner.items["a"] = ItemState(due=TODAY.isoformat())
        learner.items["b"] = ItemState(due=TODAY.isoformat())
        learner.items["c"] = ItemState(due=TODAY.isoformat())
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=5), today=TODAY)
        self.assertFalse(learner.has_met("t") or "t" in planner.exposures, "t shouldn't be known in this test")
        found = planner._eligible_milestone(["a"])
        self.assertIsNotNone(found)
        self.assertEqual(found.id, "milestone_with_transfer")

    def test_discrimination_prefers_a_known_transfer_item_over_replaying_the_same_examples(self):
        """Issue #29, owner review: once a milestone's transfer material is already known,
        the discrimination step that follows it should reach for that — applying the pattern
        to new vocabulary — rather than only ever switching between the milestone's own
        founding examples forever."""
        cur = self._transfer_curriculum()
        learner = LearnerState("is", "en", "A1")
        for iid in ("a", "b", "c", "t"):
            learner.items[iid] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="situation")
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, seed=1), today=TODAY).build()
        note_idx = next(i for i, ex in enumerate(sc.exercises) if ex.kind == "note" and ex.label == "note: milestone_with_transfer")
        first, second = sc.exercises[note_idx + 1], sc.exercises[note_idx + 2]
        discriminated = {first.item_ids[0], second.item_ids[0]}
        self.assertIn("t", discriminated, f"discrimination ignored a known transfer item: {discriminated}")

    def test_godur_gender_nominative_is_explicit_about_case_not_just_gender(self):
        """Issue #29, owner review round 2 (blocker): the first cut of a gender-transfer
        milestone paired «góður»/«góð»/«gott» (nominative) with «godur_gender»'s own
        «góðan»/«góða»/«gott» (accusative) as if only gender had changed — but Icelandic
        adjectives inflect for case too, and masculine/feminine forms differ between the two
        (BÍN: góður masc. nom., góðan masc. acc.; góð fem. nom., góða fem. acc.). Silently
        mixing them taught case and gender as one undifferentiated change, contradicting
        godur_gender's own "changes with the noun's grammatical gender" (said of examples
        that all share one case). Fixed by giving the nominative trio (matur masculine,
        hugmynd feminine, veður neuter) its own milestone, explicit that it's a different
        case from godur_gender's — not silently folded in as if it were the same paradigm
        slot with only gender varying."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        godur_gender = cur.note_by_id["godur_gender"]
        # transfer is allowed only within the same (accusative) case: e.g. eigdu_godur, whose
        # agreement forms are exactly godur_gender's góðan / góða / gott (issue #29 transfer)
        for tid in godur_gender.transfer_items:
            t = cur.by_id[tid]
            forms = {g: f.lower() for rule in t.agreement.values() for g, f in rule.items() if g != "from"}
            self.assertEqual(forms, {"masc": "góðan", "fem": "góða", "neut": "gott"}, f"{tid} pairs godur_gender with another case")
        nominative = cur.note_by_id["godur_gender_nominative"]
        self.assertEqual(set(nominative.items), {"godur_matur", "thad_er_god_hugmynd", "gott_vedur"})
        self.assertIn("nominative", nominative.text.lower())
        self.assertIn("accusative", nominative.text.lower())

    def _agreement_curriculum(self):
        """A synthetic gender-agreement construction, isolated from the real curriculum's own
        choice of adjective/nouns (same reasoning as ``_transfer_curriculum`` above): this tests
        the *mechanism* — that a construction's own wording, not just which item fills a slot,
        can depend on a filled item's ``gender`` — independent of which real Icelandic words
        happen to carry it."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "m", "kind": "vocab", "target": "m-noun", "meaning": "m-thing", "tags": ["gnoun"], "gender": "masc"},
                {"id": "f", "kind": "vocab", "target": "f-noun", "meaning": "f-thing", "tags": ["gnoun"], "gender": "fem"},
                {"id": "n", "kind": "vocab", "target": "n-noun", "meaning": "n-thing", "tags": ["gnoun"], "gender": "neut"},
                {
                    "id": "agree",
                    "kind": "construction",
                    "target": "{adj} {noun}.",
                    "meaning": "Good {noun}.",
                    "slots": {"noun": "gnoun"},
                    "agreement": {"adj": {"from": "noun", "masc": "GoodM", "fem": "GoodF", "neut": "GoodN"}},
                    "example": {"noun": "n"},
                },
            ],
        }
        return curriculum_from_dict(raw)

    def test_agreement_slot_derives_the_constructions_own_wording_from_the_filled_noun_gender(self):
        """Issue #29 owner review (final requirement): a genuine generate-from-parts pilot
        needs the construction's own wording (not just which noun it names) to change with an
        independently-known noun's gender — three surface strings from one authored template,
        never each written out as its own item. See ``Item.agreement``/``resolve_slots``."""
        cur = self._agreement_curriculum()
        agree = cur.by_id["agree"]
        cases = {"m": ("GoodM m-noun.", "Good m-thing."), "f": ("GoodF f-noun.", "Good f-thing."), "n": ("GoodN n-noun.", "Good n-thing.")}
        for noun_id, (target, meaning) in cases.items():
            got_target, got_meaning = cur.resolve_slots(agree, {"noun": cur.by_id[noun_id]})
            self.assertEqual((got_target, got_meaning), (target, meaning), noun_id)

    def test_agreement_requires_an_explicit_controlling_slot(self):
        """Owner review on PR #50, point 2: inferring the controller as "whichever fill happens
        to carry a gender" is ambiguous once a construction could have more than one gendered
        slot. `from` must name it explicitly, and validation must reject its absence."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "n", "kind": "vocab", "target": "n-noun", "meaning": "n-thing", "tags": ["gnoun"], "gender": "neut"},
                {
                    "id": "agree",
                    "kind": "construction",
                    "target": "{adj} {noun}.",
                    "meaning": "Good {noun}.",
                    "slots": {"noun": "gnoun"},
                    "agreement": {"adj": {"masc": "GoodM", "fem": "GoodF", "neut": "GoodN"}},  # no "from"
                    "example": {"noun": "n"},
                },
            ],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)

    def test_agreement_construction_requires_forms_for_every_gender_its_controller_can_produce(self):
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "m", "kind": "vocab", "target": "m-noun", "meaning": "m-thing", "tags": ["gnoun"], "gender": "masc"},
                {"id": "n", "kind": "vocab", "target": "n-noun", "meaning": "n-thing", "tags": ["gnoun"], "gender": "neut"},
                {
                    "id": "agree",
                    "kind": "construction",
                    "target": "{adj} {noun}.",
                    "meaning": "Good {noun}.",
                    "slots": {"noun": "gnoun"},
                    "agreement": {"adj": {"from": "noun", "masc": "GoodM"}},  # missing "neut", which "n" needs
                    "example": {"noun": "n"},
                },
            ],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)

    def test_agreement_construction_requires_every_controller_candidate_to_have_a_gender(self):
        """Owner review on PR #50, point 3: validation previously only required *some* tagged
        item to carry a gender, so an ungendered candidate could still slip through and hit
        `forms[None]` at runtime the day it happened to be picked. Every candidate for the
        controlling slot must be gendered, not just one of them."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "m", "kind": "vocab", "target": "m-noun", "meaning": "m-thing", "tags": ["gnoun"], "gender": "masc"},
                {"id": "u", "kind": "vocab", "target": "u-noun", "meaning": "u-thing", "tags": ["gnoun"]},  # no gender
                {
                    "id": "agree",
                    "kind": "construction",
                    "target": "{adj} {noun}.",
                    "meaning": "Good {noun}.",
                    "slots": {"noun": "gnoun"},
                    "agreement": {"adj": {"from": "noun", "masc": "GoodM", "fem": "GoodF", "neut": "GoodN"}},
                    "example": {"noun": "m"},
                },
            ],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)

    def test_item_gender_must_be_a_known_value(self):
        """Owner review on PR #50, point 3: a typo like gender = "masculine" should fail to
        load, not silently produce an item that can never satisfy any agreement rule."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": "n", "kind": "vocab", "target": "n-noun", "meaning": "n-thing", "gender": "masculine"}],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)

    def test_godur_noun_generates_the_owners_worked_example_without_authoring_the_phrases(self):
        """Issue #29 owner review (final requirement before closing #29): 'at least one
        grammar/construction pilot where the learner generates a novel combination rather than
        recalling a pre-authored phrase' — the owner's own worked example is a learner who
        already knows the góður/góð/gott gender distinction and that bíll/bók/hús are
        masc/fem/neut, producing 'Góður bíll.'/'Góð bók.'/'Gott hús.' as combinations that were
        never authored as their own phrase items. Proves both halves: the real ``godur_noun``
        construction really does generate exactly those three strings, AND none of the three
        exists anywhere in the curriculum as its own item target."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        construction = cur.by_id["godur_noun"]
        cases = {"bill": "Góður bíll.", "bok": "Góð bók.", "hus": "Gott hús."}
        targets = {it.target.strip().lower() for it in cur.items}
        for noun_id, expected in cases.items():
            target, _ = cur.resolve_slots(construction, {"noun": cur.by_id[noun_id]})
            self.assertEqual(target, expected)
            self.assertNotIn(expected.lower(), targets, f"{expected!r} must not also exist as its own pre-authored item")

    def test_gendered_nouns_note_actually_teaches_the_genders_godur_noun_relies_on(self):
        """Owner review on PR #50, point 1: `Item.gender` and `resolve_slots()` let the
        *system* resolve bíll/bók/hús's genders, but until this note existed nothing ever told
        the *learner* — the fact lived only in curriculum metadata, never in an exercise the
        learner actually hears. Checks both halves: the note names the three words and their
        genders, and godur_noun's own prereqs guarantee it has always fired first."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        note = cur.note_by_id["gendered_nouns_bill_bok_hus"]
        self.assertEqual(set(note.items), {"bill", "bok", "hus"})
        for word in ("bíll", "bók", "hús"):
            self.assertIn(word, note.text.lower())
        for word in ("masculine", "feminine", "neuter"):
            self.assertIn(word, note.text.lower())
        construction = cur.by_id["godur_noun"]
        self.assertTrue(set(note.items) <= set(construction.prereqs), "godur_noun must not be reachable before the learner is told these genders")

    def test_godur_noun_construction_is_reachable_once_its_prereqs_are_known(self):
        """The generative pilot must actually be usable, not just correct in isolation: once a
        learner has met godur_noun's prereqs (the gender-agreement concept plus all three
        gendered nouns, per the owner's own worked example), Builder.generate() -- the same
        machinery every other construction uses for genuinely novel recombination during a
        lesson -- must be able to produce a valid fill for it."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        construction = cur.by_id["godur_noun"]
        learner = LearnerState("is", "en", "A1")
        for iid in construction.prereqs:
            learner.items[iid] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="situation")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
        gen = b.generate(construction)
        self.assertIsNotNone(gen, "godur_noun could not be generated once its prereqs were known")
        valid = {"Gott hús.": "Good house.", "Góður bíll.": "Good car.", "Góð bók.": "Good book."}
        self.assertIn(gen.target, valid, gen.target)
        self.assertEqual(gen.meaning, valid[gen.target])

    def test_milestone_fires_before_a_construction_whose_own_example_fill_would_complete_it(self):
        """Owner review on PR #50 (the one remaining blocker): godur_noun's prereqs guarantee
        the gendered_nouns_bill_bok_hus note has *fired* before it — but only if firing was
        actually forced, not left to chance. Reproduced directly: when all of a milestone's
        gating items are already known *before* this lesson starts (so nothing about them is
        freshly touched), and the only new thing left to introduce is a construction whose own
        worked-example fill happens to be one of those same gating items, the construction's
        intro exercise (Builder._intro_construction plays its own example fill — see
        Curriculum.example_fill) is what would complete the milestone's "met or exposed" check —
        but the post-exercise _maybe_note check only runs *after* that intro finishes, so the
        milestone note used to fire one exercise too late, after the learner had already met the
        construction it was meant to prepare them for. Uses a synthetic curriculum, isolated
        from godur_noun's own specific prereqs/content, matching this file's convention for
        mechanism tests (see ``_transfer_curriculum``/``_agreement_curriculum`` above)."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "m", "kind": "vocab", "target": "m-noun", "meaning": "m-thing", "tags": ["gnoun"], "gender": "masc"},
                {"id": "f", "kind": "vocab", "target": "f-noun", "meaning": "f-thing", "tags": ["gnoun"], "gender": "fem"},
                {"id": "n", "kind": "vocab", "target": "n-noun", "meaning": "n-thing", "tags": ["gnoun"], "gender": "neut"},
                {
                    "id": "agree",
                    "kind": "construction",
                    "target": "{adj} {noun}.",
                    "meaning": "Good {noun}.",
                    "slots": {"noun": "gnoun"},
                    "agreement": {"adj": {"from": "noun", "masc": "GoodM", "fem": "GoodF", "neut": "GoodN"}},
                    "example": {"noun": "n"},  # "n" is both the construction's own worked example AND one of the note's gating items
                    "prereqs": ["m", "f", "n"],
                },
            ],
            "notes": [{"id": "gender_note", "milestone": True, "items": ["m", "f", "n"], "text": "m is masc, f is fem, n is neut."}],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for iid in ("m", "f", "n"):
            # all noun items already known ...
            learner.items[iid] = ItemState(due=TODAY.isoformat(), successes=5, durable_successes=5, stage="situation")
        self.assertEqual(learner.notes_heard.get("gender_note", 0), 0)  # ... and gender note unheard
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        sc = planner.build()  # next lesson must play note before godur_noun introduction
        note_idx = next(i for i, ex in enumerate(sc.exercises) if ex.kind == "note" and ex.label == "note: gender_note")
        intro_idx = next(i for i, ex in enumerate(sc.exercises) if ex.kind == "intro" and "agree" in ex.item_ids)
        self.assertLess(note_idx, intro_idx, "the construction was introduced before the milestone that names its own pattern had fired")

    def test_all_due_milestones_fire_before_an_intro_not_just_the_first_one_found(self):
        """Owner review follow-up on PR #50: godur_noun's own prereqs actually span *two*
        separate milestones (godur_gender_nominative's trio and
        gendered_nouns_bill_bok_hus's), but the previous fix's single
        ``_eligible_milestone(item.prereqs)`` call only ever returns the first one it finds —
        so if both are simultaneously due and unheard, only the first fires before the intro;
        the second still only fires reactively afterward, too late for the same reason the
        previous fix exists at all. ``do_intro`` must drain *every* currently-due milestone
        among an item's prereqs, not just one, before its own intro exercise plays. Reproduced
        with two independent milestone groups, both already eligible and unheard, gating a
        single construction: two milestones already known → its example fill would complete a
        third check, none of them already 'used up' by only checking once."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a1", "kind": "phrase", "target": "A1.", "meaning": "A1."},
                {"id": "a2", "kind": "phrase", "target": "A2.", "meaning": "A2."},
                {"id": "a3", "kind": "phrase", "target": "A3.", "meaning": "A3."},
                {"id": "m", "kind": "vocab", "target": "m-noun", "meaning": "m-thing", "tags": ["gnoun"], "gender": "masc"},
                {"id": "f", "kind": "vocab", "target": "f-noun", "meaning": "f-thing", "tags": ["gnoun"], "gender": "fem"},
                {"id": "n", "kind": "vocab", "target": "n-noun", "meaning": "n-thing", "tags": ["gnoun"], "gender": "neut"},
                {
                    "id": "agree",
                    "kind": "construction",
                    "target": "{adj} {noun}.",
                    "meaning": "Good {noun}.",
                    "slots": {"noun": "gnoun"},
                    "agreement": {"adj": {"from": "noun", "masc": "GoodM", "fem": "GoodF", "neut": "GoodN"}},
                    "example": {"noun": "n"},
                    "prereqs": ["a1", "a2", "a3", "m", "f", "n"],  # spans two unrelated milestone groups
                },
            ],
            "notes": [
                {"id": "group_a", "milestone": True, "items": ["a1", "a2", "a3"], "text": "group a."},
                {"id": "group_gender", "milestone": True, "items": ["m", "f", "n"], "text": "group gender."},
            ],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for iid in ("a1", "a2", "a3", "m", "f", "n"):  # both groups already known
            learner.items[iid] = ItemState(due=TODAY.isoformat(), successes=5, durable_successes=5, stage="situation")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        sc = planner.build()
        intro_idx = next(i for i, ex in enumerate(sc.exercises) if ex.kind == "intro" and "agree" in ex.item_ids)
        for note_id in ("group_a", "group_gender"):
            note_idx = next(i for i, ex in enumerate(sc.exercises) if ex.kind == "note" and ex.label == f"note: {note_id}")
            self.assertLess(note_idx, intro_idx, f"{note_id} was not drained before the construction's intro")

    def test_milestone_eligible_as_soon_as_its_last_item_is_exercised_this_lesson(self):
        """Owner review follow-up on #32: a milestone must not wait an extra lesson just
        because ``has_met`` doesn't count an item introduced earlier in the *same*, still
        in-progress lesson. ``Planner.exposures`` already tracks that, so checking it
        alongside ``has_met`` makes the note eligible the moment its last item is exercised,
        not on the next lesson that happens to touch one of the three again."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        note = cur.note_by_id["godur_gender"]
        a, b, c = note.items
        learner = LearnerState("is", "en", "A1")
        learner.items[a] = ItemState(due=TODAY.isoformat())
        learner.items[b] = ItemState(due=TODAY.isoformat())
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=5), today=TODAY)
        self.assertIsNone(planner._eligible_milestone([c]))  # c not met, not yet exercised this lesson
        planner.exposures[c] = ["intro"]  # c just introduced this lesson; not in LearnerState yet
        found = planner._eligible_milestone([c])
        self.assertIsNotNone(found)
        self.assertEqual(found.id, "godur_gender")

    def test_milestone_note_takes_priority_over_the_ordinary_note_budget(self):
        """Owner review follow-up on #32: a due milestone is a curriculum event, not an
        optional aside, so an exhausted note budget (or an earlier cultural aside using it
        up) must not be able to suppress it."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        note = cur.note_by_id["godur_gender"]
        learner = LearnerState("is", "en", "A1")
        for item_id in note.items:
            learner.items[item_id] = ItemState(due=TODAY.isoformat())
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=6, max_notes=0), today=TODAY)
        self.assertFalse(planner._note_budget_left())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        planner._maybe_note(sc, [note.items[-1]], remaining=100)
        self.assertEqual([e.label for e in sc.exercises], ["note: godur_gender"])

    def test_milestone_does_not_suppress_the_end_of_lesson_aside_fallback(self):
        """Owner review follow-up on #38 (pilot 4): the "at least one aside per lesson"
        fallback checked whether ``self.notes_played`` was empty, but that list includes
        milestones too — so a lesson where a milestone fired but no ordinary aside had played
        would wrongly skip the fallback, letting a milestone indirectly crowd out cultural
        asides. Unit-tests the extracted ``_aside_played()`` check directly (a full-lesson
        simulation isn't reliable here: the "nothing else fits" mid-lesson filler can also
        supply an aside independent of this fallback, which masked the bug in an earlier draft
        of this test that only asserted on simulated lesson output)."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=1), today=TODAY)
        self.assertFalse(planner._aside_played())
        planner.notes_played = ["godur_gender"]  # a milestone fired; no ordinary aside has
        self.assertFalse(planner._aside_played(), "a milestone alone must not count as an aside having played")
        planner.notes_played.append("tvo_l")  # an ordinary aside now has too
        self.assertTrue(planner._aside_played())

    def test_milestone_note_is_never_picked_as_unrelated_filler(self):
        """Unlike a cultural aside, a milestone note must not be handed out by ``_pick_note``
        as generic lesson filler — it only ever fires via ``_eligible_milestone``, right after
        one of its items was just exercised."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        note = cur.note_by_id["godur_gender"]
        learner = LearnerState("is", "en", "A1")
        for item_id in note.items:
            learner.items[item_id] = ItemState(due=TODAY.isoformat())
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=4), today=TODAY)
        for _ in range(200):
            picked = planner._pick_note(None)
            if picked is not None:
                self.assertNotEqual(picked.id, "godur_gender")

    def test_pick_note_unheard_check_ignores_ineligible_milestones(self):
        """Owner review follow-up on #32: an ineligible milestone note is permanently
        "unheard" from ``_pick_note``'s point of view, since it never picks one — so it must
        not count towards the "keep going while any note is unheard" restriction, or it
        would needlessly block repeats of ordinary notes that have all already been heard."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": "a", "kind": "phrase", "target": "A.", "meaning": "A."}],
            "notes": [
                {"id": "cultural", "items": ["a"], "text": "Fact."},
                {"id": "gate", "milestone": True, "items": ["a"], "text": "Pattern."},
            ],
        }
        cur = curriculum_from_dict(raw)  # item "a" is never met, so "gate" stays ineligible
        learner = LearnerState("is", "en", "A1")
        learner.notes_heard["cultural"] = 1
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=7), today=TODAY)
        self.assertIsNotNone(planner._pick_note(None))

    def test_icelandic_course_has_complete_japanese_glosses(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")
        self.assertEqual(cur.known_lang, "ja")
        self.assertEqual(cur.missing_glosses, [])
        self.assertIn("ja", cur.known_langs)
        # every gloss the Japanese learner hears is Japanese (digits and "ATM" are Japanese usage too)
        def ja(text: str) -> bool:
            return any(ord(ch) > 0x3000 for ch in text) or text.strip("0123456789 ") in ("", "ATM")

        for it in cur.items:
            self.assertTrue(ja(it.meaning), f"{it.id}: {it.meaning!r}")
            if it.situation:
                self.assertTrue(any(ord(ch) > 0x3000 for ch in it.situation), it.id)
            if it.kind == "construction":
                # an agreement slot (see Item.agreement) is never filled from an item's own
                # meaning -- it resolves from another slot's gender -- so it has no reason to
                # appear in the translated meaning the way a real fill-slot does.
                for slot in it.slot_names:
                    if slot in it.agreement:
                        continue
                    # ``{slot:form}`` (Item.meaning_forms, issue #29 pilot 3) renders the same slot
                    self.assertRegex(it.meaning, r"\{" + slot + r"(:\w+)?\}", f"{it.id}: slot missing from Japanese meaning")
        for d in cur.dialogues:
            self.assertTrue(any(ord(ch) > 0x3000 for ch in d.setting), d.id)
            for turn in d.turns:
                self.assertTrue(any(ord(ch) > 0x3000 for ch in turn.cue), d.id)
                if turn.expect_text:
                    self.assertTrue(turn.expect_meaning and any(ord(ch) > 0x3000 for ch in turn.expect_meaning), d.id)
        for n in cur.notes:
            self.assertTrue(any(ord(ch) > 0x3000 for ch in n.text), n.id)
        en = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertEqual([i.id for i in en.items], [i.id for i in cur.items])
        self.assertEqual([i.target for i in en.items], [i.target for i in cur.items])

    def test_unknown_gloss_language_reports_everything_missing(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang="zz")
        self.assertGreater(len(cur.missing_glosses), 1900)
        self.assertEqual(cur.items[0].meaning, load_curriculum(ROOT / "curricula" / "is-en").items[0].meaning)  # fallback

    def test_pronunciation_notes_reach_the_transcript(self):
        """CURRICULUM.md documents pronunciation_notes as 'for the transcript' — make sure that's true."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        hallo = cur.item("hallo")
        self.assertIn("aspirat", hallo.pronunciation_notes)  # matches "pre-aspirated"/"pre-aspiration" either way
        learner = LearnerState("is", "en", "A1")
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY).build()
        notes = {i.id: i.pronunciation_notes for i in cur.items if i.pronunciation_notes}
        self.assertIn("hallo", notes)
        text = sc.transcript(notes)
        self.assertIn(hallo.pronunciation_notes, text)
        self.assertEqual(text.count(hallo.pronunciation_notes), 1, "printed once, not on every later review of the item")
        # without the dict, behaviour is unchanged (no notes section, no crash)
        self.assertNotIn("pre-aspirated", sc.transcript())

    def test_japanese_instructor_lesson_from_the_icelandic_course(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")
        learner = LearnerState("is", "ja", "A1")
        learner.feedback_mode = "auto"
        day = TODAY
        for _ in range(5):
            sc = Planner(cur, learner, Prompts.load("ja"), Timing(level="A1"), PlanConfig(minutes=30, seed=3), today=day).build()
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        narr = [s.text for s in sc.segments if s.type == "narrate"]
        self.assertTrue(narr and all(any(ord(ch) > 0x3000 for ch in n) for n in narr), [n for n in narr if not any(ord(ch) > 0x3000 for ch in n)][:3])
        answers = [s.text for s in sc.segments if s.type == "answer"]
        self.assertTrue(answers and all(ord(a[0]) < 0x3000 for a in answers))

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

    def test_dialogue_lines_stay_within_taught_vocabulary(self):
        """Issue #22: dialogue partner lines used words the curriculum never otherwise teaches,
        which is exactly what made the spoken translation feel necessary rather than optional.
        Every word a partner/opener line speaks should appear somewhere in an item's target —
        proper names are the one thing this can't (and shouldn't) require."""
        proper_names = {"sóley"}
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        known: set[str] = set()
        for it in cur.items:
            known |= set(w.lower() for w in _WORD_RE.findall(it.target))
        for d in cur.dialogues:
            lines = [t.opener for t in d.turns if t.opener] + [t.partner for t in d.turns if t.partner]
            used = set(w.lower() for w in _WORD_RE.findall(" ".join(lines)))
            missing = used - known - proper_names
            self.assertFalse(missing, f"{d.id}: {sorted(missing)}")

    def test_dialogue_sequencing_report_is_advisory_not_gating(self):
        """Issue #25 (reframed): a dialogue can use a word taught very late without that word
        ever blocking eligibility -- the report only flags it as a sequencing signal for a
        human to act on. The worst offender moves as issue #29's ongoing audit fixes each one
        in turn (this used to be "nagranni"/"heyra", resequenced in the #29 triage's second
        pass); what matters here is the mechanism, not which dialogue currently tops the list."""
        from audiolesson.content import dialogue_sequencing_report

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        findings = dialogue_sequencing_report(cur)
        self.assertTrue(findings)
        worst = findings[0]
        self.assertGreater(worst["gap"], 700)
        # never gates: the flagged item isn't part of what actually decides eligibility
        dlg = cur.dialogue_by_id[worst["dialogue"]]
        self.assertNotIn(worst["item"], dlg.required_items)

    def test_backward_chunks_grow_from_the_end(self):
        cur = load_curriculum(CURRICULUM)
        it = cur.item("je_ne_comprends_pas")
        chunks = it.backward_chunks()
        self.assertEqual(chunks[-1], it.target)
        for a, b in zip(chunks, chunks[1:]):
            self.assertTrue(b.rstrip(".?! ").endswith(a.rstrip(".?! ")), (a, b))

    def test_long_single_word_is_hard_but_gets_no_synthetic_sub_word_chunks(self):
        """Issue #34 point 7: a long word is just as hard to hold in memory as a long phrase
        — ``is_hard()`` still flags it — but it no longer gets an automatic backward-build
        split. The previous vowel-run heuristic guessed syllable boundaries from spelling
        alone with no knowledge of Icelandic consonant clusters or gemination, and even a
        correct split can come out mispronounced when TTS synthesizes the fragment in
        isolation, with no context that it's part of a longer word — the system should prefer
        no chunking over a guess. Author-supplied ``chunks`` are still honored, for a word
        whose boundaries are actually verified."""
        from audiolesson.content import Item

        easy = Item(id="x", kind="vocab", target="strætó", meaning="bus")
        hard = Item(id="y", kind="vocab", target="flugvöllurinn", meaning="the airport")
        self.assertFalse(easy.is_hard())  # short, two-syllable word: no build-up needed
        self.assertTrue(hard.is_hard())
        self.assertEqual(hard.backward_chunks(), [hard.target])  # no automatic sub-word split
        verified = Item(
            id="z", kind="vocab", target="flugvöllurinn", meaning="the airport",
            chunks=["-inn", "-urinn", "flugvöllurinn"],
        )
        self.assertEqual(verified.backward_chunks(), ["-inn", "-urinn", "flugvöllurinn"])

    def test_situation_for_rotates_round_robin_on_exposures(self):
        """Issue #34 point 4: an item with several ``situations`` should rotate through them
        by exposure count, not always narrate the same one."""
        from audiolesson.content import Item

        item = Item(id="x", kind="phrase", target="T.", meaning="M.", situations=["A", "B", "C"])
        self.assertTrue(item.has_situation)
        self.assertEqual([item.situation_for(n) for n in range(5)], ["A", "B", "C", "A", "B"])

    def test_situation_for_falls_back_to_singular_situation(self):
        """An item authored the old way (a single ``situation``, no ``situations``) keeps
        narrating that one string regardless of exposure count; an item with neither has no
        situation stage at all."""
        from audiolesson.content import Item

        one = Item(id="x", kind="phrase", target="T.", meaning="M.", situation="only one")
        self.assertTrue(one.has_situation)
        self.assertEqual(one.situation_for(0), "only one")
        self.assertEqual(one.situation_for(5), "only one")
        none = Item(id="y", kind="phrase", target="T.", meaning="M.")
        self.assertFalse(none.has_situation)
        self.assertIsNone(none.situation_for(0))

    def test_situations_rotate_across_repeated_retrieval_of_the_same_item(self):
        """Issue #34 point 4's own example: ``velkomin``'s situation-stage narration used to
        replay "Friends arrive at your door. Welcome them in." on every spaced review. Now
        that it has several ``situations``, real simulated lessons should actually vary the
        wording across repeats, not just accept that they theoretically could — including
        when the *same* lesson recalls it more than once (owner review on #39: rotating only
        between lessons, via ``ItemState.exposures``, still replayed the identical cue for a
        second same-lesson recall, since ``exposures`` doesn't update until the lesson ends)."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        item = cur.by_id["velkomin"]
        self.assertGreaterEqual(len(item.situations), 2)
        learner = LearnerState("is", "en", "A1")
        learner.feedback_mode = "auto"
        day = TODAY
        seen: list[str] = []
        within_lesson_repeat_checked = False
        for _ in range(25):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=7), today=day).build()
            this_lesson: list[str] = []
            for i, ex in enumerate(sc.exercises):
                if ex.kind == "recall" and ex.stage == "situation" and ex.item_ids == ["velkomin"]:
                    text = next(s.text for s in sc.segments if s.exercise == i and s.type == "narrate")
                    this_lesson.append(text)
            for a, b in zip(this_lesson, this_lesson[1:]):
                self.assertNotEqual(a, b, "same lesson repeated the identical situation cue")
                within_lesson_repeat_checked = True
            seen.extend(this_lesson)
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        self.assertGreaterEqual(len(seen), 2, "velkomin's situation stage never recurred across 25 simulated lessons")
        self.assertGreater(len(set(seen)), 1, "situation wording never varied across repeats")
        self.assertTrue(all(t in item.situations for t in seen))
        self.assertTrue(within_lesson_repeat_checked, "velkomin's situation stage never recurred within a single lesson")

    def test_situation_varies_across_repeated_retrieval_within_one_lesson(self):
        """Owner review follow-up on #39: ``ItemState.exposures`` only updates once a whole
        lesson is applied (``record_lesson()``), so it alone can't distinguish a second
        situation recall in the same, still-being-built lesson from the first. Directly
        exercises ``Builder._situation()`` (via ``recall()``) three times in a row on the same
        ``Builder`` instance — simulating three situation recalls of one item within a single
        lesson build — and requires none of them to repeat, even before any lesson is applied."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        item = cur.by_id["velkomin"]
        self.assertGreaterEqual(len(item.situations), 3)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        seen = []
        for _ in range(3):
            sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
            ex = b.recall(sc, item, "situation")
            seen.append(next(s.text for s in sc.segments if s.exercise == ex.index and s.type == "narrate"))
        self.assertEqual(len(seen), len(set(seen)), seen)

    def test_connect_advances_the_situation_rotation(self):
        """Issue #77: connect() narrated an item's current cue without advancing it, so the
        next ordinary recall of the same item replayed exactly the cue the connect had just
        used, even though the item had another variant."""
        from audiolesson.exercises import Builder

        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a", "kind": "phrase", "target": "A.", "meaning": "A.", "situations": ["A one.", "A two."]},
                {"id": "b", "kind": "phrase", "target": "B.", "meaning": "B.", "situations": ["B one.", "B two."]},
            ],
        }
        cur = curriculum_from_dict(raw)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), fresh())
        sc = Script(1, "L", cur.target_lang, cur.known_lang)
        b.connect(sc, [cur.by_id["a"], cur.by_id["b"]])
        in_connect = {s.text for s in sc.segments if s.type == "narrate"}
        self.assertTrue({"A one.", "B one."} <= in_connect)
        for item_id, expected in (("a", "A two."), ("b", "B two.")):
            sc = Script(1, "L", cur.target_lang, cur.known_lang)
            ex = b.recall(sc, cur.by_id[item_id], "situation")
            self.assertEqual(next(s.text for s in sc.segments if s.exercise == ex.index and s.type == "narrate"), expected)

    def test_a_lesson_never_repeats_a_situation_while_a_variant_is_unused(self):
        """Issue #77: repeated review in one lesson rotates through an item's authored
        situations; an exact cue comes back only once every variant has been used. Checked on
        real simulated lessons in both instructor languages, and non-vacuously: items with
        variants do recur within a lesson."""
        for lang in ("en", "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            cue_item = {c: it for it in cur.items for c in ([it.situation] if it.situation else []) + list(it.situations)}
            learner = LearnerState("is", lang, "A1")
            day = TODAY
            rotated = 0
            for _ in range(12):
                sc = Planner(cur, learner, Prompts.load(lang), Timing(level="A1"), PlanConfig(minutes=30), today=day).build()
                used: dict[str, set[str]] = {}
                for seg in sc.segments:
                    if seg.type != "narrate" or seg.text not in cue_item:
                        continue
                    it = cue_item[seg.text]
                    variants = set(it.situations) or {it.situation}
                    seen = used.setdefault(it.id, set())
                    self.assertFalse(seg.text in seen and variants - seen, f"L{sc.lesson_number} {lang}: {it.id} repeated a cue with a variant unused")
                    if seen and seg.text not in seen:
                        rotated += 1
                    seen.add(seg.text)
                apply_to_learner(sc, learner, day)
                day += timedelta(days=1)
            self.assertGreater(rotated, 20, lang)

    def test_frequently_reviewed_phrases_have_situation_variants(self):
        """Issue #77: the functional phrases a real Lesson 6 replayed seven times verbatim now
        have several situations, and a bridge's own scene never reuses an item's standalone
        wording (it would count as the same prompt without advancing the rotation)."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for iid in ("augnablik", "biddu", "sjadu", "skilurdu", "eg_er_ekki_viss", "godan_daginn", "takk", "eigdu_godan_dag"):
            self.assertGreaterEqual(len(cur.by_id[iid].situations), 3, iid)
        for lang in ("en", "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            for b_item in (it for it in cur.items if it.partner_cue):
                a_item = cur.by_id[b_item.partner_cue_after]
                self.assertNotIn(b_item.partner_cue_setup, set(a_item.situations) or {a_item.situation}, (lang, b_item.id))
                self.assertNotIn(b_item.partner_cue_situation, set(b_item.situations) or {b_item.situation}, (lang, b_item.id))


class LessonStructureTests(unittest.TestCase):
    def setUp(self):
        self.script = build(fresh(), new_items=12)  # a full first lesson (the default pace would make it short)

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

    def test_intro_pauses_between_meaning_and_target_word(self):
        """First exposure to a new word: a beat separates the known-language meaning from the
        target-language word, so a listener doesn't hear them run together as one clip."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        item = next(i for i in cur.items if i.kind not in ("construction", "transform"))
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.intro(sc, item)
        narrate_idx = next(i for i, s in enumerate(sc.segments) if s.type == "narrate")
        speak_idx = next(i for i, s in enumerate(sc.segments) if s.type == "speak")
        self.assertEqual(sc.segments[narrate_idx + 1].type, "pause")
        self.assertEqual(sc.segments[speak_idx - 1].type, "pause")

    def test_situation_stage_does_not_ask_twice(self):
        """Issue #17: 'Say bye. What do you say?' told the learner what to say and then asked
        them what to say, back to back. situation is a self-contained instruction on its own
        (every one in this curriculum already ends with one), so nothing should follow it."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        item = next(i for i in cur.items if i.situation and i.kind not in ("construction", "transform"))
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.recall(sc, item, "situation")
        narrations = [s.text for s in sc.segments if s.type == "narrate"]
        self.assertEqual(narrations, [item.situation])

    def test_note_is_bookended_so_the_next_exercise_is_not_confused_for_part_of_it(self):
        """Issue #21: a cultural aside followed straight by an unrelated question read as if
        the aside was itself part of the exercise. It already announces its start ("A quick
        aside."); it must also announce its end."""
        from audiolesson.content import Note
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.note(sc, Note(id="n", text="Some cultural fact.", items=[]))
        narrations = [s.text for s in sc.segments if s.type == "narrate"]
        self.assertEqual(narrations, [prompts.get("aside"), "Some cultural fact.", prompts.get("aside_end")])
        end_idx = next(i for i, s in enumerate(sc.segments) if s.text == "Some cultural fact.")
        self.assertEqual(sc.segments[end_idx + 1].type, "pause")  # a beat before the "back to it" line

    def test_milestone_note_is_not_framed_as_a_cultural_aside(self):
        """Issue #29 pilot 2 review, extended by issue #34 point 1: an instructional milestone
        note names a pattern the learner is ready for, so it must not open OR close with the
        "quick aside" framing an optional cultural note uses — #34 explicitly calls out "Back
        to the lesson." as wrong here, since a milestone isn't a detour: "this *is* the
        lesson"."""
        from audiolesson.content import Note
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.note(sc, Note(id="n", text="A grammar pattern.", items=[], milestone=True))
        narrations = [s.text for s in sc.segments if s.type == "narrate"]
        self.assertEqual(narrations, [prompts.get("milestone_intro"), "A grammar pattern.", prompts.get("milestone_end")])
        self.assertNotEqual(prompts.get("milestone_intro"), prompts.get("aside"))
        self.assertNotEqual(prompts.get("milestone_end"), prompts.get("aside_end"))

    def test_note_text_speaks_guillemet_marked_phrases_in_the_target_voice(self):
        """Issue #34 point 1, deferred at pilot 2: a target-language phrase named inside a
        note should be heard spoken by the target-language voice, not read as instructor-
        language text. «...» inside ``Note.text`` marks that phrase; ``Builder.note()`` must
        split on it and hand the marked parts to ``_speak`` (target language) while the
        surrounding prose stays with ``_narr`` (instructor language)."""
        from audiolesson.content import Note
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.note(sc, Note(id="n", text="Say «halló» to greet someone, and «bless» to say goodbye.", items=[]))
        speaks = [s for s in sc.segments if s.type == "speak"]
        self.assertEqual([s.text for s in speaks], ["halló", "bless"])
        self.assertTrue(all(s.lang == cur.target_lang for s in speaks))
        narrations = [s.text for s in sc.segments if s.type == "narrate"]
        self.assertEqual(
            narrations,
            [prompts.get("aside"), "Say", "to greet someone, and", "to say goodbye.", prompts.get("aside_end")],
        )
        self.assertTrue(all(s.lang == cur.known_lang for s in sc.segments if s.type == "narrate"))

    def test_note_text_speaks_a_language_prefixed_span_in_that_language_not_the_target(self):
        """Issue #49: a note can legitimately mention a *third* language besides its own
        narration language and the course's target language — e.g. an English note about
        Icelandic naming a Japanese word. «ja:onigiri» must be spoken in Japanese, not the
        target-language voice bare «...» implies, while a plain «...» span is unaffected."""
        from audiolesson.content import Note
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.note(sc, Note(id="n", text="Say «bonjour», the way «ja:onigiri» is said in Japan.", items=[]))
        speaks = [s for s in sc.segments if s.type == "speak"]
        self.assertEqual([(s.text, s.lang) for s in speaks], [("bonjour", cur.target_lang), ("onigiri", "ja")])
        self.assertIsNone(speaks[1].speech_text)  # no "|" given, so text alone is what's spoken

    def test_note_text_with_display_speech_split_keeps_romanization_in_the_transcript(self):
        """Owner review on PR #51: «ja:sate|さて» must show "sate" in the transcript (what a
        reader recognizes) while the segment separately carries "さて" as what the TTS
        provider will actually receive — Segment.speech_text, not Segment.text."""
        from audiolesson.content import Note
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.note(sc, Note(id="n", text="It works like «ja:sate|さて».", items=[]))
        speak = next(s for s in sc.segments if s.type == "speak")
        self.assertEqual(speak.text, "sate")
        self.assertEqual(speak.speech_text, "さて")
        self.assertEqual(speak.lang, "ja")
        self.assertIn("sate", sc.transcript())
        self.assertNotIn("さて", sc.transcript())  # the transcript shows the romanization, not the kana

    def test_note_text_does_not_narrate_bare_punctuation_between_marked_phrases(self):
        """Owner review on #41: a note that marks a short list of phrases — like the real
        `godur_gender` milestone's "In «Góðan daginn», «Góða nótt», and «Gott kvöld», ..." —
        splits a bare "," between two «...» phrases into its own prose fragment, which the
        first cut of this mechanism handed to ``_narr`` as a standalone, meaningless
        punctuation-only TTS call. A fragment with real words (", and") must still narrate
        normally; only a fragment with no alphanumeric content becomes a pause instead."""
        from audiolesson.content import Note
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.note(sc, Note(id="n", text="In «A», «B», and «C», the pattern holds.", items=[]))
        narrations = [s.text for s in sc.segments if s.type == "narrate"]
        self.assertEqual(
            narrations,
            [prompts.get("aside"), "In", ", and", ", the pattern holds.", prompts.get("aside_end")],
        )
        self.assertTrue(all(any(ch.isalnum() for ch in t) for t in narrations), narrations)
        speaks = [s.text for s in sc.segments if s.type == "speak"]
        self.assertEqual(speaks, ["A", "B", "C"])
        a_idx = next(i for i, s in enumerate(sc.segments) if s.type == "speak" and s.text == "A")
        b_idx = next(i for i, s in enumerate(sc.segments) if s.type == "speak" and s.text == "B")
        self.assertEqual(sc.segments[a_idx + 1].type, "pause", "bare comma between A and B should become a beat")
        self.assertEqual(sc.segments[a_idx + 2], sc.segments[b_idx])

    def test_note_text_with_no_guillemets_is_narrated_as_one_piece(self):
        """A note with no «...» markup keeps behaving exactly as before this mechanism existed
        — one narrate segment for the whole text, not split into fragments."""
        from audiolesson.content import Note
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.note(sc, Note(id="n", text="Some cultural fact.", items=[]))
        narrations = [s.text for s in sc.segments if s.type == "narrate"]
        self.assertEqual(narrations, [prompts.get("aside"), "Some cultural fact.", prompts.get("aside_end")])
        self.assertFalse(any(s.type == "speak" for s in sc.segments))

    def test_hard_single_word_gets_slow_repetition_not_a_synthetic_backward_split(self):
        """Issue #34 point 7: a long single word has no verified sub-word boundary to build
        backward from (``backward_chunks()`` now returns just the one, unsplit word for it),
        so its intro must not be framed as "build it up from the end" — it should fall back
        to the same slow-then-natural whole-word repetition an easy multi-word phrase already
        gets, not silently skip extra practice for being hard."""
        from audiolesson.content import Item
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        item = Item(id="long_word", kind="vocab", target="flugvöllurinn", meaning="the airport", difficulty=3)
        self.assertTrue(item.is_hard())
        self.assertEqual(item.backward_chunks(), [item.target])
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.intro(sc, item)
        narrations = [s.text for s in sc.segments if s.type == "narrate"]
        self.assertNotIn(prompts.get("build_up"), narrations)
        self.assertIn(prompts.get("slowly"), narrations)
        self.assertIn(prompts.get("natural"), narrations)

    def test_dialogue_partner_line_and_its_translation_have_a_beat_between(self):
        """Issue #22: a native line and its known-language translation ran together with no
        margin, which is confusing since they're two different voices/languages back to back."""
        from audiolesson.content import Dialogue, DialogueTurn
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        turn = DialogueTurn(cue="Say hello.", expect_text="Bonjour.", opener="Bonjour !", opener_meaning="Hello!")
        b.dialogue(sc, Dialogue(id="d", setting="A scene.", turns=[turn]))
        opener_idx = next(i for i, s in enumerate(sc.segments) if s.type == "speak" and s.text == "Bonjour !")
        self.assertEqual(sc.segments[opener_idx + 1].type, "pause")

    def test_dialogue_scaffolding_fades_on_later_encounters(self):
        """Issue #26: a translation of the partner's line plus an explicit "say X" cue meant
        the learner never had to understand the partner to answer correctly. On a later
        encounter (assisted=False) both should drop once there's a partner line to react to —
        but a turn with nothing said yet (no opener, nothing before it) must keep its cue,
        since there would otherwise be no way to know what to say."""
        from audiolesson.content import Dialogue, DialogueTurn
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        prompts = Prompts.load(cur.known_lang)
        b = Builder(cur, prompts, Timing(level="A1"), fresh())
        turns = [
            DialogueTurn(cue="Ask how much.", expect_text="Combien ?", opener=None, partner="Avec lait ?", partner_meaning="With milk?"),
            DialogueTurn(cue="Say no thanks.", expect_text="Non, merci."),
        ]
        dlg = Dialogue(id="d", setting="A scene.", turns=turns)

        assisted = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.dialogue(assisted, dlg, assisted=True)
        narrations = [s.text for s in assisted.segments if s.type == "narrate"]
        self.assertIn("Ask how much.", narrations)
        self.assertIn("Say no thanks.", narrations)
        self.assertTrue(any("With milk?" in n for n in narrations))

        later = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.dialogue(later, dlg, assisted=False)
        narrations = [s.text for s in later.segments if s.type == "narrate"]
        self.assertIn("Ask how much.", narrations)  # turn 1: nothing said yet, cue stays
        self.assertNotIn("Say no thanks.", narrations)  # turn 2: partner just spoke, cue drops
        self.assertFalse(any("With milk?" in n for n in narrations))  # translation drops too

    def test_later_lessons_fill_the_requested_time(self):
        _, scripts = course(8, minutes=30)
        minutes = [round(sc.total_duration / 60, 1) for sc in scripts]
        # once there is enough material the requested length is approached; the sample
        # curriculum (47 items) is exhausted around lesson 7, after which review-only lessons
        # end early. Threshold lowered from 24 (issue #34 point 7): hard single words no
        # longer speak a synthetic backward-build split, which shortens their intro slightly.
        self.assertGreaterEqual(max(minutes), 23, minutes)
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
        # Issue #49: each backward-build chunk used to play at natural rate, the one part
        # of this ladder that never went through slow_rate despite existing specifically
        # so the learner can hear and imitate a hard phrase piece by piece — "(slow)" is
        # how the transcript marks a sub-1.0 rate segment (see Script.transcript()).
        self.assertIn("**Speaker A (slow):** plaît", text)

    def test_script_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.json"
            self.script.save(p)
            back = Script.load(p)
            self.assertEqual(len(back.segments), len(self.script.segments))
            self.assertAlmostEqual(back.total_duration, self.script.total_duration, places=3)


class CourseTests(unittest.TestCase):
    def test_lessons_form_a_sequence(self):
        # long enough that items reach durable_successes>=2 (a review on/after its own due
        # date, not just intra-lesson practice) before a dialogue needs them known
        learner, scripts = course(10)
        self.assertEqual(learner.lessons_completed, 10)
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
    def test_durable_successes_need_a_review_on_or_after_its_due_date(self):
        """Issue #27: several recalls minutes apart in one lesson (the intra-lesson
        reactivation ladder) are good practice but not evidence of retention across time.
        is_learned must not fire on same-lesson repeats alone."""
        learner = fresh()
        day = TODAY
        # intro + two same-lesson reactivations: successes go up, but nothing durable yet
        learner.record_lesson(1, {"x": ["intro", "hinted", "meaning"]}, day)
        st = learner.items["x"]
        self.assertEqual(st.successes, 2)
        self.assertEqual(st.durable_successes, 0)
        self.assertFalse(st.is_learned)

        # reactivated again before its due date: still no durable evidence
        early = date.fromisoformat(st.due) - timedelta(days=1)
        if early > day:
            learner.record_lesson(2, {"x": ["meaning"]}, early)
            self.assertEqual(learner.items["x"].durable_successes, 0)

        # a real review on/after the due date: this is durable evidence
        due = date.fromisoformat(st.due)
        learner.record_lesson(3, {"x": ["meaning"]}, due)
        self.assertEqual(learner.items["x"].durable_successes, 1)
        self.assertFalse(learner.items["x"].is_learned)  # one is not enough yet

        due2 = date.fromisoformat(learner.items["x"].due)
        learner.record_lesson(4, {"x": ["meaning"]}, due2)
        self.assertEqual(learner.items["x"].durable_successes, 2)
        self.assertTrue(learner.items["x"].is_learned)

        # explicit failure feedback demotes durable standing, not just the raw count
        learner.report(["x"], [], due2)
        self.assertEqual(learner.items["x"].durable_successes, 1)
        self.assertFalse(learner.items["x"].is_learned)

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


class PromptsTests(unittest.TestCase):
    def test_meaning_prompt_is_always_an_explicit_request_to_speak(self):
        """Issue #20: 'In Icelandic: Halló.' reads as a label, not an instruction. Every variant
        of the 'meaning' prompt must explicitly ask the learner to say something."""
        for lang, marker in (("en", "say"), ("ja", "言")):
            variants = Prompts.load(lang).data["meaning"]
            for v in variants:
                self.assertIn(marker, v.lower() if lang == "en" else v, v)

    def test_meaning_prompt_never_doubles_up_terminal_punctuation(self):
        """Issue #34 point 8: 'Say: Well then. in Icelandic.' — exercises.py's _m() guarantees
        every English meaning ends in its own terminal punctuation, so no variant of the
        'meaning' prompt may put more template text directly after {meaning}: it would always
        collide with that punctuation. (Japanese sidesteps this differently — _m() strips the
        meaning's trailing '。' for ja/zh/ko before it's embedded mid-sentence, which is exactly
        why that language's templates are allowed to continue after {meaning}.)"""
        for v in Prompts.load("en").data["meaning"]:
            self.assertTrue(v.endswith("{meaning}"), v)


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

    def test_hinted_stage_skipped_for_one_word_items(self):
        """Issue #14: 'it starts with takk' as a hint for guessing 'takk' isn't a hint, it's the
        answer. The first word of a one-word item is the whole item."""
        self.assertNotIn("hinted", ladder_for("phrase", has_situation=False, in_dialogue=False, recombinable=False, word_count=1))
        self.assertIn("hinted", ladder_for("phrase", has_situation=False, in_dialogue=False, recombinable=False, word_count=2))


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

    def test_third_language_segment_does_not_inherit_the_fixed_speaker_voice(self):
        """Issue #49: an embedded third-language segment (neither the lesson's known nor
        target language, e.g. a Japanese example inside English narration) must not
        inherit whichever fixed voice the profile configured for that speaker role in
        kl/tl — it needs a voice for its own language instead. Verified by giving the
        provider a lang-distinct ``default_voices`` and checking the profile's fixed
        English override never reaches the Japanese segment's actual synthesize() call."""
        from audiolesson.render.renderer import SpeakerVoice
        from audiolesson.render.tts import StubProvider
        from audiolesson.script import Segment

        sc = Script(1, "Lesson 1", "is", "en")
        ex = sc.new_exercise("note", None, [], "note: n")
        sc.add(Segment("narrate", "instructor", "onigiri", "ja", 1.0, 1.0, None, ex.index))

        heard: list[tuple[str, str]] = []
        original_synth = StubProvider.synthesize
        original_defaults = StubProvider.default_voices

        def spy_synth(self, text, lang, voice, rate=1.0):
            heard.append((lang, voice))
            return original_synth(self, text, lang, voice, rate)

        def lang_specific_defaults(self, lang):
            return [f"voice-for-{lang.split('-')[0].lower()}"]

        StubProvider.synthesize = spy_synth
        StubProvider.default_voices = lang_specific_defaults
        try:
            with tempfile.TemporaryDirectory() as td:
                prof = load_profile(None, "stub")
                prof.mp3 = False
                prof.speakers["instructor"] = SpeakerVoice(voice="fixed-english-voice")
                render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
        finally:
            StubProvider.synthesize = original_synth
            StubProvider.default_voices = original_defaults

        self.assertEqual(heard, [("ja", "voice-for-ja")])

    def test_speech_text_reaches_the_provider_not_the_romanized_display_text(self):
        """Owner review on PR #51: routing by ``lang`` (the test above) proves *a* Japanese
        voice gets picked, but #49 ultimately needs the TTS provider to receive text that
        unambiguously represents the intended Japanese utterance — some providers (e.g.
        OpenAIProvider) don't even look at ``lang``, they just read whatever ``text`` they're
        given. Pins the actual synthesize() call: native orthography, not the romanized
        transcript display, must be what's sent, regardless of the segment's own ``text``."""
        from audiolesson.render.tts import StubProvider
        from audiolesson.script import Segment

        sc = Script(1, "Lesson 1", "is", "en")
        ex = sc.new_exercise("note", None, [], "note: n")
        sc.add(Segment("narrate", "instructor", "onigiri", "ja", 1.0, 1.0, None, ex.index, speech_text="おにぎり"))

        heard: list[tuple[str, str]] = []
        original_synth = StubProvider.synthesize

        def spy_synth(self, text, lang, voice, rate=1.0):
            heard.append((text, lang))
            return original_synth(self, text, lang, voice, rate)

        StubProvider.synthesize = spy_synth
        try:
            with tempfile.TemporaryDirectory() as td:
                prof = load_profile(None, "stub")
                prof.mp3 = False
                render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
        finally:
            StubProvider.synthesize = original_synth

        self.assertEqual(heard, [("おにぎり", "ja")])

    def test_respell_table_is_scoped_to_its_language_and_word(self):
        from audiolesson.render.renderer import RESPELL_FOR_SPEECH, _respell

        self.assertIn("is", RESPELL_FOR_SPEECH)
        self.assertEqual(_respell("Halló.", "is"), "Haló.")
        self.assertEqual(_respell("Halló.", "is-IS"), "Haló.")  # region-tagged lang code
        self.assertEqual(_respell("Halló.", "en"), "Halló.")  # never touches another language
        self.assertEqual(_respell("Shall we?", "is"), "Shall we?")  # substring collision guarded elsewhere by lang, not here
        self.assertEqual(_respell("fjall", "is"), "fjall")  # only the one overridden word, not every 'll'

    def test_halló_reaches_the_tts_respelled_but_the_record_keeps_the_real_spelling(self):
        """The owner asked for 'halló' specifically not to get Icelandic ll pre-aspiration.
        Only the audio should change — transcript/cues keep the correct native spelling."""
        from audiolesson.script import Segment
        from audiolesson.render.tts import StubProvider

        sc = Script(1, "Lesson 1", "is", "en")
        ex = sc.new_exercise("intro", "intro", ["hallo"], "new: Halló.")
        sc.add(Segment("speak", "native_a", "Halló.", "is", 1.0, 1.0, None, ex.index))

        heard: list[str] = []
        original = StubProvider.synthesize

        def spy(self, text, lang, voice, rate=1.0):
            heard.append(text)
            return original(self, text, lang, voice, rate)

        StubProvider.synthesize = spy
        try:
            with tempfile.TemporaryDirectory() as td:
                prof = load_profile(None, "stub")
                prof.mp3 = False
                cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
        finally:
            StubProvider.synthesize = original

        self.assertIn("Haló.", heard)
        self.assertNotIn("Halló.", heard)  # the TTS never actually saw the geminate spelling
        self.assertEqual(cues["segments"][0]["text"], "Halló.")  # cues.json keeps the real word
        self.assertIn("Halló.", sc.transcript())  # transcript is built from the Segment, untouched by rendering

    def test_narration_slash_is_spoken_as_a_word_not_read_as_slash(self):
        from audiolesson.render.renderer import _speak_slashes

        self.assertEqual(_speak_slashes("Excuse me / Sorry.", "en"), "Excuse me or Sorry.")
        self.assertEqual(_speak_slashes("yes/no", "en"), "yes or no")
        self.assertEqual(_speak_slashes("もしもし。／ハロー。", "ja"), "もしもし。またはハロー。")
        self.assertEqual(_speak_slashes("地図／カード", "ja"), "地図またはカード")
        self.assertEqual(_speak_slashes("no slash here", "en"), "no slash here")
        self.assertEqual(_speak_slashes("A / B", "is"), "A / B")  # only known-language narration is fixed

    def test_narration_slash_reaches_the_tts_but_the_record_keeps_the_slash(self):
        """The written meaning keeps the '/' for a reader; only the spoken audio says 'or'."""
        from audiolesson.script import Segment
        from audiolesson.render.tts import StubProvider

        sc = Script(1, "Lesson 1", "is", "en")
        ex = sc.new_exercise("intro", "intro", ["hallo"], "new: Halló.")
        sc.add(Segment("speak", "instructor", "Excuse me / Sorry.", "en", 1.0, 1.0, None, ex.index))

        heard: list[str] = []
        original = StubProvider.synthesize

        def spy(self, text, lang, voice, rate=1.0):
            heard.append(text)
            return original(self, text, lang, voice, rate)

        StubProvider.synthesize = spy
        try:
            with tempfile.TemporaryDirectory() as td:
                prof = load_profile(None, "stub")
                prof.mp3 = False
                cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
        finally:
            StubProvider.synthesize = original

        self.assertIn("Excuse me or Sorry.", heard)
        self.assertNotIn("Excuse me / Sorry.", heard)
        self.assertEqual(cues["segments"][0]["text"], "Excuse me / Sorry.")
        self.assertIn("Excuse me / Sorry.", sc.transcript())


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

    def test_user_wrapper_remembers_settings_across_calls(self):
        """--user NAME is a thin wrapper: files land under <root>/NAME/, and the curriculum,
        --known, --minutes etc. from the first call don't need repeating on later ones."""
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "out"
            rc = main(["generate", "-u", "yuki", "--root", str(root), "-c", str(CURRICULUM), "-m", "3", "--no-audio", "--date", "2026-09-18"])
            self.assertEqual(rc, 0)
            user_dir = root / "yuki"
            self.assertTrue((user_dir / "lesson-001.script.json").exists())
            self.assertTrue((user_dir / "learner.json").exists())
            saved = json.loads((user_dir / "settings.json").read_text())
            self.assertEqual(saved["curriculum"], str(CURRICULUM))
            self.assertEqual(saved["minutes"], 3.0)

            # second call: only -u, everything else remembered; lesson numbering continues
            rc = main(["generate", "-u", "yuki", "--root", str(root), "--no-audio", "--date", "2026-09-19"])
            self.assertEqual(rc, 0)
            self.assertTrue((user_dir / "lesson-002.script.json").exists())

            self.assertEqual(main(["status", "-u", "yuki", "--root", str(root)]), 0)
            self.assertEqual(main(["report", "-u", "yuki", "--root", str(root)]), 0)

    def test_user_wrapper_rejects_path_like_names_and_conflicting_flags(self):
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "out"
            self.assertEqual(main(["generate", "-u", "../escape", "--root", str(root), "-c", str(CURRICULUM), "-m", "3", "--no-audio"]), 1)
            self.assertEqual(main(["generate", "-u", "a/b", "--root", str(root), "-c", str(CURRICULUM), "-m", "3", "--no-audio"]), 1)
            # --user together with --learner or --out is a conflict, not a silent override
            self.assertEqual(main(["generate", "-u", "a", "--root", str(root), "-c", str(CURRICULUM), "-m", "3", "-l", str(root / "x.json"), "--no-audio"]), 1)
            self.assertEqual(main(["generate", "-u", "a", "--root", str(root), "-c", str(CURRICULUM), "-m", "3", "-o", str(root / "x"), "--no-audio"]), 1)

    def test_without_user_or_learner_still_errors_clearly(self):
        from audiolesson.cli import main

        self.assertEqual(main(["generate", "-c", str(CURRICULUM), "-m", "3", "--no-audio"]), 1)
        self.assertEqual(main(["status"]), 1)
        self.assertEqual(main(["report"]), 1)


if __name__ == "__main__":
    unittest.main()
