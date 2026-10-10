"""Structural guarantees of a generated lesson. Run: python -m unittest -v"""

from __future__ import annotations

import copy
import json
import os
import random
import re
import tempfile
import unittest
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from audiolesson.exercises import SITUATION_FULL_MAX, _norm_utterance
from audiolesson.content import NOTE_TARGET_RE, CurriculumError, curriculum_from_dict, load_curriculum, unmarked_japanese
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.render import load_profile, render_script
from audiolesson.render.audio import read_wav
from audiolesson.script import Script, Segment
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
    def test_learner_notes_are_not_authoring_comments(self):
        """Lesson 18 review: «ein»'s note told the learner about small_count tags and a
        construction's unit pool. pronunciation_notes are printed in the transcript, so they
        must not name ids, tags or fields; authoring rationale belongs in a TOML comment."""
        internal = re.compile(r"\b[a-z]+_[a-z_]+\b|\btags?\b|target text|issue #|#\d")
        for it in load_curriculum(ROOT / "curricula" / "is-en").items:
            self.assertIsNone(internal.search(it.pronunciation_notes or ""), f"{it.id}: {it.pronunciation_notes}")

    def test_number_prompts_are_spoken_naturally(self):
        """Lesson 18 review: "Say: Two (feminine; krónur)." is read out by the TTS as is. The
        disambiguator for 1-4's three forms is a phrase a person would say."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for i in ("einn", "eitt", "ein", "tveir", "tvo", "tvaer"):
            self.assertFalse(re.search(r"[();]", cur.by_id[i].meaning), cur.by_id[i].meaning)
        self.assertEqual(cur.by_id["tvaer"].meaning, "two, as in counting krónur")
        self.assertEqual(load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja").by_id["eitt"].meaning, "時刻を言うときの1")

    def test_no_two_items_share_a_recall_prompt(self):
        """Lesson 8 feedback: «einn», «eitt» and «ein» were all prompted "Say: One." — the
        learner can't know which form is asked for. Every item's meaning, in every language it
        is glossed in, must tell it apart from the others (a disambiguator such as "one
        (neuter; clock times)" or 「鍵（〜を）」 is fine; ``meaning_forms.in_sentence`` keeps
        sentence prompts plain)."""
        for path in (ROOT / "curricula" / "is-en", CURRICULUM):
            for lang in load_curriculum(path).known_langs:
                cur = load_curriculum(path, known_lang=lang)
                seen: dict[str, str] = {}
                for it in cur.items:
                    if "{" in it.target:
                        continue  # a construction is prompted through a filled example
                    key = it.meaning.strip().rstrip(".!?。").lower()
                    self.assertNotIn(key, seen, f"{path.name} [{lang}]: {it.id} and {seen.get(key)} are both prompted {it.meaning!r}")
                    seen[key] = it.id

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

    def test_an_infinitive_is_named_with_to(self):
        """Owner: «Say: Buy a ticket.» → «kaupa miða» asks for the imperative («Kauptu miða.»)
        and answers with the infinitive. Said alone, an infinitive filler is «to buy a ticket»;
        in a sentence the fill still comes from ``meaning`` («I want to buy a ticket»)."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": "k", "kind": "vocab", "target": "kaupa miða", "meaning": "buy a ticket", "tags": ["inf"]}],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)
        raw["items"][0]["meaning_spoken"] = "to buy a ticket"
        curriculum_from_dict(raw)
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        item = cur.by_id["kaupa_mida"]
        self.assertEqual(item.spoken_meaning, "to buy a ticket")
        self.assertEqual(cur.resolve_slots(cur.by_id["eg_vil"], {"inf": item})[1], "I want to buy a ticket.")

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

    def test_the_scan_finds_the_romanized_japanese_the_notes_had_and_nothing_now(self):
        """#219: the romanized Japanese that lessons 14, 17 and 18 had the English voice read."""
        before = (
            "the sentō: cheap. 'atsui desu ne' and 'senjitsu wa arigatō gozaimashita' and 'gochisōsama' and 'itadakimasu', "
            "close to gochisousama and ojama shimashita in one."
        )
        self.assertEqual(
            set(unmarked_japanese(before)),
            {"sentō", "atsui", "desu", "senjitsu", "arigatō", "gozaimashita", "gochisōsama", "itadakimasu", "gochisousama", "ojama", "shimashita"},
        )
        cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang="en")
        self.assertEqual([(n.id, w) for n in cur.notes for w in unmarked_japanese(n.text)], [])

    def test_a_note_with_unmarked_japanese_fails_validate_and_marked_passes(self):
        def raw(text):
            return {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "notes": [{"id": "n", "text": text}]}

        with self.assertRaisesRegex(CurriculumError, "romanized Japanese outside"):
            curriculum_from_dict(raw("Said like 'atsui desu ne' in Japan."))
        curriculum_from_dict(raw("Said like «ja:atsui desu ne|暑いですね» in Japan."))
        with self.assertRaisesRegex(CurriculumError, "genkan"):  # plain morae: the mark heuristic misses it, the denylist does not
            curriculum_from_dict(raw("There is no genkan step."))
        curriculum_from_dict(raw("There is no «ja:genkan|玄関» step."))
        curriculum_from_dict(raw("A sushi bar, a machine, Chinese food and some fun."))  # the allowlist

    def test_unmarked_japanese_in_an_items_situation_or_a_themes_cue_fails(self):
        from audiolesson.themes import Level, Theme, Turn, _check

        item = {"id": "a", "kind": "phrase", "target": "Halló", "meaning": "Hello.", "situation": "Say it as you would 'gochisōsama'."}
        with self.assertRaisesRegex(CurriculumError, "romanized Japanese"):
            curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": [item]})
        # every English field of an item is read, the list the glossing uses
        for field_name in ("meaning", "context", "partner_cue_setup"):
            with self.assertRaisesRegex(CurriculumError, field_name):
                curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": [{**item, "situation": "", field_name: "like a gochisōsama"}]})
        theme = Theme(id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[
            Turn(who="you", say="Takk.", cue="Say 'gochisōsama' in Icelandic.", items=["takk"])])])
        with self.assertRaisesRegex(CurriculumError, "romanized Japanese"):
            _check(theme)

    def test_unmarked_japanese_in_a_dialogue_or_an_example_fails(self):
        """The same English fields the glossing names: a dialogue's setting and turns, an item's transform examples."""
        head = {"name": "x", "target_lang": "is", "known_lang": "en"}
        item = {"id": "w0", "kind": "vocab", "target": "Halló", "meaning": "Hello."}
        for turn_field, value in (("cue", "Say gochisōsama."), ("partner_meaning", "Yes, arigatō."), ("expect_meaning", "After the onsen.")):
            dlg = {"id": "d1", "setting": "A setting.", "requires": ["w0"], "turns": [{"cue": "Say it.", "expect": "w0", turn_field: value}]}
            with self.assertRaisesRegex(CurriculumError, turn_field):
                curriculum_from_dict({"curriculum": head, "items": [item], "dialogues": [dlg]})
        dlg = {"id": "d1", "setting": "After the onsen.", "requires": ["w0"], "turns": [{"cue": "Say it.", "expect": "w0"}]}
        with self.assertRaisesRegex(CurriculumError, "setting"):
            curriculum_from_dict({"curriculum": head, "items": [item], "dialogues": [dlg]})
        tr = {"id": "t0", "kind": "transform", "target": "x", "meaning": "m", "instruction": "Do it:",
              "examples": [{"source": "a", "source_meaning": "like gochisōsama", "result": "b", "result_meaning": "B."}]}
        with self.assertRaisesRegex(CurriculumError, "source_meaning"):
            curriculum_from_dict({"curriculum": head, "items": [tr]})

    def test_a_note_with_a_marked_japanese_span_is_spoken_in_japanese(self):
        from audiolesson.exercises import Builder
        from audiolesson.prompts import Prompts
        from audiolesson.timing import Timing

        cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang="en")
        sc = Script(1, "t", cur.target_lang, cur.known_lang)
        Builder(cur, Prompts.load("en"), Timing(level="A1"), fresh()).note(sc, next(n for n in cur.notes if n.id == "vedur_smalltalk"))
        ja = [s for s in sc.segments if s.type == "speak" and s.lang == "ja"]
        self.assertTrue(any(s.speech_text == "暑いですね" for s in ja), [(s.text, s.speech_text) for s in ja])

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
        # the lesson-wide note total is tested on its own below; give it room here
        cfg = PlanConfig(minutes=12, seed=1, dialogue_every=1000, drill_streak_limit=3, max_streak_relief_notes=2, max_notes_total=10)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY)
        sc = planner.build()
        self.assertEqual(len(sc.meta["notes"]), 1 + cfg.max_streak_relief_notes, sc.meta["notes"])

    def _note_lesson(self, minutes, milestones=0, **cfg):
        """A lesson over 40 known phrases with 20 plain notes and ``milestones`` milestone
        notes (one per item w0, w1, …, so each fires right after its item is practised)."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(40)],
            "notes": [{"id": f"n{i}", "text": f"Note {i}."} for i in range(20)]
            + [{"id": f"m{i}", "text": f"Pattern {i}.", "items": [f"w{i}"], "milestone": True} for i in range(milestones)],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in range(40):
            learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        cfg = PlanConfig(minutes=minutes, seed=1, dialogue_every=1000, drill_streak_limit=3, note_chance=1.0, **cfg)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        played = sc.meta["notes"]
        return [n for n in played if n.startswith("m")], [n for n in played if n.startswith("n")]

    def test_asides_stop_at_the_lesson_total(self):
        """Lesson 8 feedback: six notes in 28 minutes. max_notes_total defaults to one per 10
        minutes, at least 2; with every note chance on, asides fill it and stop."""
        for minutes, total in ((30, 3), (12, 2)):
            milestones, asides = self._note_lesson(minutes)
            self.assertEqual((milestones, len(asides)), ([], total), minutes)

    def test_streak_relief_asides_count_toward_the_total(self):
        """Relief asides (#44) break a drill streak only while the total has room: with one
        ordinary aside and two relief asides available, a total of 2 lets through one relief."""
        _, asides = self._note_lesson(12, max_notes=1, max_streak_relief_notes=2, max_notes_total=2)
        self.assertEqual(len(asides), 2)
        _, roomy = self._note_lesson(12, max_notes=1, max_streak_relief_notes=2, max_notes_total=10)
        self.assertEqual(len(roomy), 3, "the relief allowance itself is unchanged when the total has room")

    def test_milestones_play_past_the_total_but_asides_do_not(self):
        """The total is not a strict cap: milestones keep their own cap (max_reactive_milestones)
        and are never blocked, because they name a pattern right where it is practised. Once
        they fill the total, no aside plays; past it, milestones still do."""
        milestones, asides = self._note_lesson(30, milestones=1)
        self.assertEqual((len(milestones), len(asides)), (1, 2), "one milestone + asides up to the total of 3")
        milestones, asides = self._note_lesson(30, milestones=4, max_reactive_milestones=4)
        self.assertEqual(len(milestones), 4, "four milestones exceed the total of 3 and all play")
        self.assertEqual(asides, [], "no aside once milestones have used the total")

    def test_notes_heard_before_last_heard_was_recorded_rest_the_full_gap(self):
        """Lesson 8 feedback: asides heard in lessons made before notes_last_heard existed came
        back as if never rested. Loading such a file dates them to the latest lesson."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "l.json"
            old = LearnerState("is", "en", "A1", lessons_completed=7)
            old.notes_heard = {"nofn": 1, "kindur": 1}
            old.save(path)
            raw = json.loads(path.read_text())
            raw.pop("notes_last_heard")
            path.write_text(json.dumps(raw))
            loaded = LearnerState.load(path)
            self.assertEqual(loaded.notes_last_heard, {"nofn": 7, "kindur": 7})
            cur = load_curriculum(ROOT / "curricula" / "is-en")
            planner = Planner(cur, loaded, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
            played = planner.build().meta["notes"]
            self.assertTrue(played, "other asides still play")
            self.assertFalse(set(played) & {"nofn", "kindur"}, played)
            fresh_state = LearnerState("is", "en", "A1", lessons_completed=7)
            fresh_state.notes_heard = {"nofn": 1, "kindur": 1}  # no last-heard record in memory either
            self.assertIsNone(fresh_state.notes_last_heard.get("nofn"), "only loading backfills")

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
                    {"id": "a0", "kind": "phrase", "target": "Boga núll hér.", "meaning": "Arc one, a.", "situation": "Arc one situation a."},
                    {"id": "a1", "kind": "phrase", "target": "Boga einn hér.", "meaning": "Arc one, b.", "situation": "Arc one situation b."},
                    {"id": "b0", "kind": "phrase", "target": "Boga tveir hér.", "meaning": "Arc two, a.", "situation": "Arc two situation a."},
                    {"id": "b1", "kind": "phrase", "target": "Boga þrír hér.", "meaning": "Arc two, b.", "situation": "Arc two situation b."},
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
            # extra_arc_share=1: the second arc takes two items too, so each arc can pair with itself.
            # premise changed (#192): max_sentence_hard=0 (the hard cap off): twelve fixed phrases fill a 30-minute lesson here, so the new ones
            # reach the cap and are left out of scenes; the test is about the arcs' connect moments, not identical counts
            PlanConfig(minutes=30, seed=1, new_items=2, max_new_items=2, extra_arc_share=1.0, dialogue_every=1000, drill_streak_limit=1000, note_chance=0.0, max_sentence_hard=0),
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
                {"id": "fara_heim", "kind": "vocab", "target": "fara heim", "meaning": "go home", "meaning_spoken": "to go home", "meaning_ja": "家に帰る",
                 "tags": ["inf"], "meaning_forms": {"ing": "going home"}, "meaning_forms_ja": {"te": "家に帰って"}},
                {"id": "sofa", "kind": "vocab", "target": "sofa", "meaning": "sleep", "meaning_spoken": "to sleep", "meaning_ja": "寝る",
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
            # #29 families: their progressive is already authored as a phrase in the course
            # («Ég er að elda.», «Ég er að senda tölvupóst.»)
            "elda", "senda_tolvupost",
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

    def test_tense_and_person_milestones_name_the_rule_before_its_drill(self):
        """Issue #29 tense / person pilot: var_past names «er → var» from three known «var»
        phrases before transform_var drills it, and vid_um names the «við … -um» ending before
        transform_vid_form — each followed by two of its own phrases' situations. Likewise the
        «Ég á …» family: eiga_have names «eiga» and the gendered count (einn bróður / tvö börn)
        right before «Ég á tvær systur.» brings the feminine one."""
        for drill, note in (("transform_var", "var_past"), ("transform_vid_form", "vid_um"), ("eg_a_tvaer_systur", "eiga_have")):
            sc, cur = self._lesson_introducing(drill)
            labels = [ex.label for ex in sc.exercises]
            self.assertIn(drill, sc.meta["new_items"], drill)
            at = labels.index(f"note: {note}")
            first_drill = next(i for i, ex in enumerate(sc.exercises) if drill in ex.item_ids)
            self.assertLess(at, first_drill, labels)
            gate = set(cur.note_by_id[note].items) | set(cur.note_by_id[note].transfer_items)
            for ex in sc.exercises[at + 1 : at + 3]:
                self.assertEqual((ex.kind, ex.stage), ("recall", "situation"), labels)
                self.assertIn(ex.item_ids[0], gate)

    def test_past_drills_only_ask_for_forms_already_taught(self):
        """Issue #29 tense pilot: the pilot generalizes only «er → var»; other past-tense
        patterns (weak «borða → borðaði» included) stay phrase-first until they are introduced
        explicitly. So a past drill never asks for a past the learner hasn't met as a phrase:
        transform_var changes only «er» → «var», and every transform_past result verb is in a
        phrase introduced before the drill."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        tv = cur.by_id["transform_var"]
        for ex in tv.examples:
            for src, res in ((ex.source, ex.result), (ex.source_m or ex.source, ex.result_m or ex.result)):
                self.assertTrue(res.startswith(src[:-1].replace(" er ", " var ", 1)), (src, res))
                self.assertTrue(res.endswith(" í gær."), res)
        past = cur.by_id["transform_past"]
        earlier = [it.target for it in cur.items if it.order < past.order and it.kind == "phrase"]
        for ex in past.examples:
            verb = ex.result.split()[1]
            self.assertTrue(any(f" {verb} " in f" {t} " for t in earlier), verb)
        self.assertLess(cur.by_id["eg_keypti_peysu"].order, past.order)

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
            self.assertIn(it.spoken_meaning.strip().rstrip(".").lower(), narration.lower(), it.id)  # prompts capitalise the gloss (#83)
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
                        # a construction's own authored annotation is
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

    def test_unrelated_pair_is_framed_as_mixed_review_not_connection(self):
        """Issue #78, the real Lesson 6 pair: «Augnablik.» (ask the cashier for a moment) and
        «Bíddu.» (tell a friend to hang on) have no relation a learner can notice, but were
        announced with "Let's put a couple of things together." An unrelated pair is now framed
        as mixed review in both instructor languages; an authored exchange keeps its framing."""
        from audiolesson.exercises import Builder

        for lang, connected in (("en", ("together", "And then")), ("ja", ("つなげ", "そして"))):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            prompts = Prompts.load(lang)
            b = Builder(cur, prompts, Timing(level="A1"), LearnerState("is", lang, "A1"))
            sc = Script(1, "L", cur.target_lang, lang)
            ex = b.connect(sc, [cur.by_id["augnablik"], cur.by_id["biddu"]])
            narr = [s.text for s in sc.segments if s.type == "narrate"]
            self.assertEqual(ex.stage, "recombine")
            self.assertTrue(ex.label.startswith("mixed review"), ex.label)
            self.assertEqual(narr[0], prompts.get("mixed_review_intro"))
            self.assertFalse([n for n in narr if any(w in n for w in connected)], narr)

            sc = Script(1, "L", cur.target_lang, lang)
            ex = b.connect(sc, [cur.by_id["godan_daginn"], cur.by_id["endilega"]])
            self.assertEqual(ex.stage, "exchange")
            self.assertEqual(next(s.text for s in sc.segments if s.type == "narrate"), prompts.get("connect_intro"))

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
        # the partner speaks in the bridge's own voice (lesson 8 feedback: match the narration's
        # he/she), the learner's model answers in the other
        partner = second.partner_cue_speaker
        learner = "native_b" if partner == "native_a" else "native_a"
        self.assertEqual(
            turns,
            [
                (learner, "Gætirðu talað hægar?"),
                (partner, "Auðvitað. Herbergið er númer tuttugu og þrjú."),
                (learner, "Gætirðu endurtekið þetta?"),
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
        padding = ["kaffi", "te", "vatn", "islensku", "ensku", "japonsku", "thysku", "fronsku", "donsku", "vegabref"]
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
                {"id": "a0", "kind": "phrase", "target": "Boga núll hér.", "meaning": "Arc one.", "situation": "Arc one situation.", "topics": ["p"]},
                {"id": "b0", "kind": "phrase", "target": "Boga einn hér.", "meaning": "Arc two.", "situation": "Arc two situation.", "topics": ["q"]},
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
        partner = cur.by_id["eg_skil"].partner_cue_speaker  # the voice the narration's he/she implies
        learner = "native_b" if partner == "native_a" else "native_a"
        self.assertEqual([t[0] for t in turns], [learner, partner, learner], turns)

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
        last_heard: dict[str, int] = {}
        cfg_for_ceiling = PlanConfig(minutes=30)
        for _ in range(12):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=2), today=day).build()
            notes = [e for e in sc.exercises if e.kind == "note"]
            asides = [e for e in notes if not cur.note_by_id[e.label.split(": ")[1]].milestone]
            self.assertLessEqual(len(asides), 2 + cfg_for_ceiling.max_streak_relief_notes)
            for e in notes:
                note = cur.note_by_id[e.label.split(": ")[1]]
                if not note.milestone and note.id in last_heard:
                    # issue #81: a heard aside may come back, but only after the repeat gap
                    self.assertGreaterEqual(sc.lesson_number - last_heard[note.id], cfg_for_ceiling.note_repeat_gap, note.id)
                heard.append(note.id)
                last_heard[note.id] = sc.lesson_number
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
        # premise changed (#192): the course grew by nine items (the ticket and party patterns), so the deepest milestone now needs
        # 81-82 simulated lessons at this pace, not 80 or fewer; the budget is 85
        for _ in range(85):
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
            # the next day's review: a real learner says the embedded parts and pattern sentences back (#149, #192), so they are met
            learner.report([], [], day, recalled=list(learner.embedded))
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
        # premise changed (#192): the course grew by nine items (the ticket and party patterns), so the deepest milestone now needs
        # 81-82 simulated lessons at this pace, not 80 or fewer; the budget is 85
        for _ in range(85):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=10, seed=3), today=day).build()
            note_positions = [(i, e.label.split(": ")[1]) for i, e in enumerate(sc.exercises) if e.kind == "note" and e.label.split(": ")[1] in milestones]
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
            for note_idx, note_id in note_positions:
                gate_ids = milestones[note_id]
                self.assertGreater(len(sc.exercises), note_idx + 2, f"{note_id} wasn't followed by two discrimination exercises")
                first, second = sc.exercises[note_idx + 1], sc.exercises[note_idx + 2]
                for ex in (first, second):
                    # a situation narrated in full twice already this lesson (#170, G12) is recalled from its short
                    # meaning cue instead; otherwise the item's own situation
                    item = cur.by_id[ex.item_ids[0]]
                    texts = {t for t in ([item.situation] if item.situation else []) + list(item.situations)}
                    told = sum(1 for sg in sc.segments if sg.type == "narrate" and sg.text in texts and sg.exercise is not None and sg.exercise < ex.index)
                    allowed = {("recall", "situation")} | ({("recall", "meaning")} if told >= SITUATION_FULL_MAX else set())
                    self.assertIn((ex.kind, ex.stage), allowed, (note_id, ex.item_ids, told))
                    # a construction's recall also lists the fill it was generated with (support
                    # exposure); the practised item itself is always first
                    self.assertTrue(len(ex.item_ids) == 1 or cur.by_id[ex.item_ids[0]].kind == "construction", ex.item_ids)
                    self.assertIn(ex.item_ids[0], gate_ids)
                self.assertNotEqual(first.item_ids[0], second.item_ids[0])
                checked.add(note_id)
            # the next day's review: a real learner says the embedded parts and pattern sentences back (#149, #192), so they are met
            learner.report([], [], day, recalled=list(learner.embedded))
            if checked == set(milestones):
                break
        self.assertEqual(checked, set(milestones), "not every milestone note fired across simulated lessons")

    def _transfer_curriculum(self):
        """A synthetic milestone with transfer_items, isolated from any real-curriculum
        content decision (issue #29, owner review round 2: the first cut of this test used
        the real ``godur_gender`` note, which coupled the test's validity to a specific
        curriculum-content choice that turned out to need correcting — see
        ``test_...nominative`` below and docs/history/sessions.md). This tests the *mechanism* only:
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

    def test_filler_asides_stay_in_context_and_keep_coming(self):
        """Issue #81: filler used any unheard note, so asides about material far ahead (families,
        cashless shops) played in the first lessons and were then used up. One note waiting on
        its ``requires`` also blocked every repeat, so no aside played from L12 on. Filler now
        takes a note about met material first, then one about material within
        ``note_lookahead``; distant material waits for its moment, a waiting note doesn't block
        repeats, and a heard note comes back only after ``note_repeat_gap`` lessons."""
        items = [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(300)]
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": items,
            "notes": [
                {"id": "far", "items": ["w250"], "text": "About something far ahead."},
                {"id": "waiting", "items": ["w0"], "requires": ["w299"], "text": "Recommends w299."},
                {"id": "heard", "items": ["w0"], "text": "Heard before."},
            ],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        learner.items["w0"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning")
        learner.lessons_completed = 29  # the next lesson is L30
        learner.notes_heard["heard"] = 1
        learner.notes_last_heard["heard"] = 25
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=1), today=TODAY)
        self.assertIsNone(planner._pick_note(None), "far is out of context, heard is resting, waiting is unavailable")
        learner.notes_last_heard["heard"] = 30 - PlanConfig().note_repeat_gap
        self.assertEqual(planner._pick_note(None).id, "heard", "a waiting note no longer blocks a rested repeat")
        with tempfile.TemporaryDirectory() as td:
            learner.save(Path(td) / "l.json")
            self.assertEqual(LearnerState.load(Path(td) / "l.json").notes_last_heard, learner.notes_last_heard)

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        late_asides = 0
        for _ in range(40):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30), today=day).build()
            reached = max((cur.by_id[i].order for i in list(learner.items) + list(sc.meta["exposures"]) if i in cur.by_id), default=0)
            for n in sc.meta["notes"]:
                note = cur.note_by_id[n]
                if note.milestone:
                    continue
                self.assertTrue(
                    not note.items or any(cur.by_id[i].order <= reached + PlanConfig().note_lookahead for i in note.items),
                    f"L{sc.lesson_number}: {n} is about material far ahead",
                )
                if sc.lesson_number > 20:
                    late_asides += 1
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        self.assertGreaterEqual(late_asides, 10, "asides must keep coming after the first lessons")

    def test_milestone_contrast_keeps_two_recalls_when_situations_run_short(self):
        """Issue #84: contrast practice after a milestone took only examples whose situation was
        usable, so a milestone with one such example got a single recall, silently (modal_infinitive
        and vera_ad_progressive are real cases: their other examples are constructions bound to a
        fill). The shortfall is now made up from meaning-stage recalls of the other examples."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "a", "kind": "phrase", "target": "A a a.", "meaning": "A.", "situation": "Say A."},
                {"id": "b", "kind": "phrase", "target": "B b b.", "meaning": "B."},
                {"id": "c", "kind": "phrase", "target": "C c c.", "meaning": "C."},
            ] + [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(6)],
            "notes": [{"id": "m", "milestone": True, "items": ["a", "b", "c"], "text": "A, B and C share a pattern."}],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        # a is the most overdue, so it comes first and triggers the milestone; the fillers are due
        # next, and b and c aren't due, so only the contrast practice can recall them right after
        later, earlier = (TODAY + timedelta(days=20)).isoformat(), (TODAY - timedelta(days=9)).isoformat()
        for i, due in [("a", earlier), ("b", later), ("c", later)] + [(f"w{i}", TODAY.isoformat()) for i in range(6)]:
            learner.items[i] = ItemState(due=due, interval_days=10, successes=2, durable_successes=2, stage="meaning")
        cfg = PlanConfig(minutes=10, seed=3, drill_streak_limit=100)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        at = next(i for i, e in enumerate(sc.exercises) if e.kind == "note" and e.label == "note: m")
        trigger = sc.exercises[at - 1].item_ids[0]
        after = sc.exercises[at + 1 : at + 3]
        self.assertEqual([e.kind for e in after], ["recall", "recall"])
        self.assertEqual({e.item_ids[0] for e in after}, {"a", "b", "c"} - {trigger})
        for e in after:
            self.assertEqual(e.stage, "situation" if e.item_ids[0] == "a" else "meaning")

    def test_pronunciation_features_are_named_early_and_spread_out(self):
        """Issue #82: sounds that surprise a Japanese listener (no added final vowel and first-
        syllable stress, þ / ð, hv = kv, á / æ / ó) are each named once, aloud, as milestones
        over early phrases that contain them. So that they don't crowd one lesson, at most
        ``max_reactive_milestones`` milestones fire after their item per lesson; the rest wait."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        pron = {n.id: n for n in cur.notes if n.id.startswith("pron_")}
        self.assertEqual(set(pron), {"pron_stress_final", "pron_th", "pron_hv", "pron_vowels"})
        for note in pron.values():
            self.assertTrue(note.milestone)
            self.assertLess(max(cur.by_id[i].order for i in note.items), 100, note.id)
            # every example spoken in the target voice is one of the note's own (met) items
            spoken = {t.rstrip(".!?") for t in NOTE_TARGET_RE.findall(note.text)}
            self.assertTrue(spoken <= {cur.by_id[i].target.rstrip(".!?") for i in note.items}, (note.id, spoken))
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        fired: set[str] = set()
        cap = PlanConfig().max_reactive_milestones
        for _ in range(15):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30), today=day).build()
            milestones = [e.label.split(": ")[1] for e in sc.exercises if e.kind == "note" and cur.note_by_id[e.label.split(": ")[1]].milestone]
            self.assertLessEqual(len(milestones), cap, (sc.lesson_number, milestones))
            fired |= set(milestones)
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        self.assertTrue(set(pron) <= fired, set(pron) - fired)

    def test_early_fills_get_their_frame_right_after_them(self):
        """Issue #80: the numbers moved to module 02 (#29 cluster A) but their frames stayed in
        modules 06 and 08, and «vegabréf» / «poka» waited for module 09's clothes, so they were
        drilled as bare words for weeks. Each frame now sits right after the last thing it needs:
        the clock after the numbers, the price after «Hvað kostar þetta?», «Ég þarf …» after
        «poka»."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for con_id in ("klukkan_er", "thad_kostar_big", "eg_tharf"):
            con = cur.by_id[con_id]
            needed = max(cur.by_id[p].order for p in con.prereqs)
            self.assertLessEqual(con.order - needed, 3, con_id)
        self.assertLess(cur.by_id["hvad_er_klukkan"].order, cur.by_id["klukkan_er"].order)
        self.assertLess(cur.by_id["eg_tharf"].order - cur.by_id["vegabref"].order, 100)

    def test_each_gendered_set_of_one_to_four_arrives_with_its_frame(self):
        """Issue #80, owner direction: not all twelve forms of 1-4 as bare words ahead of any
        use. Each form is *produced* in a context right after its set (review on PR #118:
        checked on the surfaces the learner actually says, not on an item standing nearby) —
        the counting forms by counting and the emergency number, the neuter by the clock, the
        feminine by krónur. Once the three frames are met a milestone ties them to góður/góð/gott."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        o = {i.id: i.order for i in cur.items}

        def surfaces(item) -> set[str]:
            if item.kind != "construction":
                return {w.lower() for w in _WORD_RE.findall(item.target)}
            out: set[str] = set()
            for slot, tag in item.slots.items():
                for fill in cur.items_with_tag(tag):
                    fills = cur.example_fill(item)
                    fills[slot] = fill
                    out |= {w.lower() for w in _WORD_RE.findall(cur.resolve_slots(item, fills)[0])}
            return out

        sets = [
            ["einn", "tveir", "thrir", "fjorir"],
            ["eitt", "tvo", "thrju", "fjogur"],
            ["ein", "tvaer", "thrjar", "fjorar"],
        ]
        for forms in sets:
            last = max(o[f] for f in forms)
            contexts = [i for i in cur.items if i.kind != "vocab" and last < i.order <= last + 3]
            said = set().union(*(surfaces(i) for i in contexts))
            for f in forms:
                self.assertIn(cur.by_id[f].target.lower(), said, f"{f}: never produced right after its set ({[i.id for i in contexts]})")
        self.assertLess(o["klukkan_er"], o["ein"], "the feminine set comes after the clock, not interleaved")
        note = cur.note_by_id["tolur_kyn"]
        self.assertTrue(note.milestone)
        self.assertEqual(set(note.items), {"einn_einn_tveir", "klukkan_er", "einn_tvo_thrjar"})
        self.assertIn("«góður»", note.text)
        self.assertTrue(all(cur.by_id[i].has_situation for i in note.items), "the contrast recalls use situations")

    def test_first_lesson_never_opens_with_three_introductions_in_a_row(self):
        """Issue #86: with nothing to review yet, lesson 1 opened o-i-i-i: three new items back to
        back before the first retrieval, because pulling a reactivation forward skipped both
        recently touched items. After two introductions in a row the earlier one is recalled
        instead. Lesson length and new-item count are unchanged."""
        for path in (ROOT / "curricula" / "is-en", CURRICULUM):
            cur = load_curriculum(path)
            for minutes in (15, 30):
                learner = LearnerState(cur.target_lang, "en", "A1")
                day = TODAY
                for _ in range(5):
                    sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=minutes), today=day).build()
                    kinds = "".join("i" if e.kind == "intro" else "-" for e in sc.exercises)
                    self.assertNotIn("iii", kinds, (path.name, minutes, sc.lesson_number))
                    apply_to_learner(sc, learner, day)
                    day += timedelta(days=1)

    def test_a_dialogue_is_announced_before_anyone_speaks(self):
        """Issue #85: a dialogue opened with its setting and then, often, a partner line in a new
        voice; nothing marked the switch from drills to a conversation. Every dialogue now opens
        with ``dialogue_start`` in both instructor languages, before the setting and before the
        first partner line."""
        from audiolesson.exercises import Builder

        for lang in ("en", "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            prompts = Prompts.load(lang)
            dlg = cur.dialogue_by_id["tungumal"]
            for translate in (True, False):
                b = Builder(cur, prompts, Timing(level="A1"), LearnerState("is", lang, "A1"))
                sc = Script(1, "L", cur.target_lang, lang)
                b.dialogue(sc, dlg, translate=translate)
                segs = [(s.type, s.text) for s in sc.segments if s.type != "pause"]
                self.assertEqual(segs[0], ("narrate", prompts.get("dialogue_start")), (lang, translate))
                self.assertEqual(segs[1], ("narrate", dlg.setting))

    def test_instructor_prompts_capitalise_glosses_and_carry_no_usage_notes(self):
        """Issue #83, from a real Lesson 6: "Something new. a passport." pasted a lowercase vocab
        gloss after a full stop, and "In Icelandic, say: Enjoy your meal. (also the reply to
        thanks for food)." read a usage note aloud inside the prompt. Glosses are capitalised
        where a template puts them, and a parenthetical after the sentence is only allowed when
        it tells the learner which form to produce (who is addressed, what is shown)."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), fresh())
        sc = Script(1, "L", cur.target_lang, cur.known_lang)
        b.intro(sc, cur.by_id["vegabref"])
        self.assertIn("Something new. A passport.", [s.text for s in sc.segments if s.type == "narrate"])
        informative = {
            "a_thetta_hotel_takk", "eg_er_a_bil", "einn_tvo_thrjar", "ert_thu_islensk", "ertu_buin", "ertu_state",
            "farid_varlega_a_isnum", "gerdu_thig_heimakomna", "ha", "hvad_ertu_gomul", "hvar_er_thetta", "hvers_vegna",
            "takk_fyrir_sidast",
        }
        trailing = {it.id for it in cur.items if re.search(r"[.?!]\s*\(", it.meaning)}
        self.assertEqual(trailing - informative, set(), "a usage note belongs in a situation or a note, not the spoken gloss")

    def test_near_synonyms_are_contrasted_and_every_situation_asks_for_something(self):
        """Issue #79: early lessons teach near-synonym clusters side by side («Ha?» / «Hvað
        sagðirðu?» / «Gætirðu endurtekið þetta?»; don't know / don't understand / not sure; bye /
        see you) without saying which fits when. Each cluster now has a milestone that names
        the difference. Every situation also ends in something to do, so a prompt never leaves
        the learner guessing whether an answer is wanted; the instruction-verb check is a
        heuristic, so extend its vocabulary rather than weakening it."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        clusters = {
            "say_it_again": {"ha", "hvad_sagdirdu", "gaetirdu_endurtekid_thetta"},
            "dont_know": {"eg_veit_ekki", "eg_skil_ekki", "eg_er_ekki_viss"},
            "goodbyes": {"bless", "sjaumst", "sjaumst_seinna"},
        }
        for note_id, members in clusters.items():
            note = cur.note_by_id[note_id]
            self.assertTrue(note.milestone)
            self.assertEqual(set(note.items), members)
            self.assertTrue(all(cur.by_id[i].has_situation for i in members), note_id)
        instruction = re.compile(
            r"\b(say|ask|tell|greet|thank|wish|answer|apologi[sz]e|congratulate|agree|welcome|warn|shout|remark|"
            r"complain|reassure|explain|point|order|call|introduce|offer|suggest|check|signal|turn|return|get|"
            r"comment|repeat|whisper|text|react|start|summari[sz]e|mention|protest|refuse|accept|decline|admit|correct|confirm|count)\b",
            re.IGNORECASE,
        )
        for it in cur.items:
            for text in ([it.situation] if it.situation else []) + list(it.situations):
                self.assertRegex(text, instruction, it.id)

        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), fresh())
        sc = Script(1, "L", cur.target_lang, cur.known_lang)
        ex = b.connect(sc, [cur.by_id["allt_gott"], cur.by_id["en_thu"]])
        self.assertEqual(ex.stage, "exchange")
        self.assertEqual([s.text for s in sc.segments if s.type in ("speak", "answer")], ["Allt gott, takk.", "Gott að heyra.", "En þú?"])

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

    def test_part_before_whole_report_and_the_hvenaer_fix(self):
        """G13 (lesson 13 feedback): «Hvenær?» came as a new item after «Hvenær leggjum við af
        stað?». The report is advisory; the phrase now lists the word as a prerequisite."""
        from audiolesson.content import part_before_whole_report

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertIn("hvenaer", cur.by_id["hvenaer_leggjum_vid_af_stad"].prereqs)
        found = {(f["whole"], f["part"]) for f in part_before_whole_report(cur)}
        self.assertNotIn(("hvenaer_leggjum_vid_af_stad", "hvenaer"), found)
        small = curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "whole", "kind": "phrase", "target": "Hvenær kemur þú?", "meaning": "When do you come?"},
                {"id": "part", "kind": "phrase", "target": "Hvenær?", "meaning": "When?"},
            ],
        })
        self.assertEqual([(f["whole"], f["part"]) for f in part_before_whole_report(small)], [("whole", "part")])
        small.by_id["whole"].prereqs.append("part")
        self.assertEqual(part_before_whole_report(small), [])

    def test_a_phrase_waits_for_its_part_and_comes_after_it(self):
        cur = curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "whole", "kind": "phrase", "target": "Hvenær kemur þú?", "meaning": "When do you come?", "prereqs": ["part"]},
                {"id": "other", "kind": "phrase", "target": "Takk fyrir.", "meaning": "Thanks."},
                {"id": "part", "kind": "phrase", "target": "Hvenær?", "meaning": "When?"},
            ],
        })
        learner = LearnerState("is", "en", "A1")
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, new_items=3, priority=["whole"]), today=TODAY).build()
        order = sc.meta["new_items"]
        self.assertLess(order.index("part"), order.index("whole"))

    def test_frame_gap_report_flags_bare_words(self):
        """Issue #80: a vocab item climbs past ``meaning`` only in a frame (a construction with
        a slot for one of its tags) or a dialogue that requires it. The report lists words whose
        first such context comes more than ``span`` items later, and words with none."""
        from audiolesson.content import frame_gap_report

        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "kaffi", "kind": "vocab", "target": "kaffi", "meaning": "coffee", "tags": ["drink"]},
                {"id": "te", "kind": "vocab", "target": "te", "meaning": "tea", "tags": ["drink"]},
                {"id": "vatn", "kind": "vocab", "target": "vatn", "meaning": "water", "tags": ["drink"]},
                {"id": "lone", "kind": "vocab", "target": "einn", "meaning": "one"},
                {"id": "talk", "kind": "vocab", "target": "tala", "meaning": "speak"},
                {"id": "hi", "kind": "phrase", "target": "Hæ.", "meaning": "Hi."},
            ]
            + [{"id": f"p{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(8)]
            + [{"id": "c", "kind": "construction", "target": "{d}, takk.", "meaning": "{d}, please.", "slots": {"d": "drink"}}],
            "dialogues": [
                {"id": "d1", "setting": "A test setting.", "turns": [{"cue": "Greet.", "expect": "hi"}, {"cue": "Say 'speak'.", "expect": "talk"}]}
            ],
        }
        cur = curriculum_from_dict(raw)
        report = frame_gap_report(cur, span=5)
        late = {f["item"]: f for f in report["late"]}
        self.assertEqual(set(late), {"kaffi", "te", "vatn"}, report)
        self.assertEqual(late["kaffi"]["context"], "c")
        self.assertEqual(late["kaffi"]["gap"], cur.by_id["c"].order - cur.by_id["kaffi"].order)
        self.assertEqual([f["item"] for f in report["none"]], ["lone"], "a dialogue turn is a context too; phrases aren't reported")
        self.assertEqual(frame_gap_report(cur, span=100)["late"], [])

        # the real course, after #80: no word waits far for its first frame, and those with none
        # at all are function words and number parts used inside phrases
        report = frame_gap_report(load_curriculum(ROOT / "curricula" / "is-en"))
        self.assertEqual(report["late"], [])
        self.assertLessEqual(len(report["none"]), 34)  # 26 plus the eight colours, which wait for a scene that uses them (#158)

    def test_a_filler_recombines_into_a_frame_met_in_an_earlier_lesson(self):
        """Issue #80: a filler could only recombine into a construction already *learned* (or
        introduced this lesson), while the construction's own review recombined with that very
        filler as soon as it was met. «vatn» was drilled as "say: water" while «Ég ætla að fá
        {thing}», met the lesson before, waited to be learned. A frame met in an earlier lesson
        now serves too — unless its last report was a failure."""
        from audiolesson.exercises import Builder

        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "kaffi", "kind": "vocab", "target": "kaffi", "meaning": "coffee", "tags": ["drink"]},
                {"id": "vatn", "kind": "vocab", "target": "vatn", "meaning": "water", "tags": ["drink"]},
                {"id": "fa", "kind": "construction", "target": "Ég ætla að fá {d}.", "meaning": "I'll have {d}.", "slots": {"d": "drink"}},
            ],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in ("kaffi", "vatn"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=2, stage="meaning")
        learner.items["fa"] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=0, stage="hinted")
        self.assertFalse(learner.knows("fa"), "met and practised, not yet learned")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
        gen = b.generate_with(cur.by_id["vatn"])
        self.assertIsNotNone(gen)
        self.assertEqual(gen.target, "Ég ætla að fá vatn.")
        learner.items["fa"].last_outcome = "not_recalled"
        self.assertIsNone(Builder(cur, Prompts.load("en"), Timing(level="A1"), learner).generate_with(cur.by_id["vatn"]))
        learner.items["fa"] = ItemState(stage="intro")
        self.assertIsNone(Builder(cur, Prompts.load("en"), Timing(level="A1"), learner).generate_with(cur.by_id["vatn"]), "only met at intro")

    def test_nouns_with_no_other_frame_are_named_by_pointing(self):
        """Issue #80: people, furniture, work, nature and animal nouns were drilled only as bare
        words. «Þetta er {thing}.» names each ("That's a waterfall."), «þetta» staying neuter
        whatever the noun; bíll/bók/hús keep their bare form for «Góður bíll.»."""
        for lang, expect in ((None, [("Þetta er foss.", "That's a waterfall."), ("Þetta er bíll.", "That's a car."), ("Þetta er maður.", "That's a man.")]),
                             ("ja", [("Þetta er foss.", "あれは滝です。"), ("Þetta er bíll.", "あれは車です。"), ("Þetta er heitur hver.", "あれは温泉です。")])):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            frame = cur.by_id["thetta_er_noun"]
            for target, meaning in expect:
                fill = next(i for i in cur.items_with_tag("nom_noun") if target.startswith(f"Þetta er {i.target}."))
                self.assertEqual(cur.resolve_slots(frame, {"thing": fill}), (target, meaning))
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertEqual(cur.resolve_slots(cur.by_id["godur_noun"], {"noun": cur.by_id["bill"]}), ("Góður bíll.", "Good car."))
        self.assertLess(cur.by_id["thetta_er_noun"].order, cur.by_id["bill"].order)
        self.assertEqual(cur.resolve_slots(cur.by_id["eg_er_ara"], {"age": cur.by_id["sautjan"]})[0], "Ég er sautján ára.")
        for i in ("hvar", "af_hverju", "kannski", "i_gaer"):
            self.assertEqual((cur.by_id[i].kind, cur.by_id[i].has_situation), ("phrase", True), i)

    def test_takk_fyrir_and_the_grown_inf_pool_generate(self):
        """Issue #29 families: «Takk fyrir {thing}.» is a pattern right after «Ég þarf hjálp.»,
        not only three fixed phrases hundreds of items later; the «Má ég …?» phrases' verb
        phrases fill every «… {inf}» pattern, in both instructor languages."""
        for lang, expect in (
            (None, {("takk_fyrir", "hjalpina"): ("Takk fyrir hjálpina.", "Thanks for the help."),
                    ("eg_vil", "taka_mynd"): ("Ég vil taka mynd.", "I want to take a photo."),
                    ("ma_eg_inf", "opna_gluggann"): ("Má ég opna gluggann?", "May I open the window?")}),
            ("ja", {("takk_fyrir", "hjalpina"): ("Takk fyrir hjálpina.", "手伝ってくれてありがとう。"),
                    ("ma_eg_inf", "hringja"): ("Má ég hringja?", "電話してもいいですか？")}),
        ):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            for (cid, fid), resolved in expect.items():
                c = cur.by_id[cid]
                self.assertEqual(cur.resolve_slots(c, {next(iter(c.slots)): cur.by_id[fid]}), resolved)
        # food and drink thank the way Japanese does: the generated «Takk fyrir matinn.» is cued as
        # the fixed phrase is, ごちそうさま, not a literal 食事をありがとう
        ja = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")
        c = ja.by_id["takk_fyrir"]
        self.assertEqual(ja.resolve_slots(c, {"thing": ja.by_id["matinn"]})[1], ja.by_id["takk_fyrir_matinn"].meaning)
        self.assertEqual(ja.resolve_slots(c, {"thing": ja.by_id["kaffid"]})[1], "コーヒー、ごちそうさまでした。")
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        # «Verði þér að góðu» both wishes a good meal and answers «Takk fyrir matinn»
        reply = cur.by_id["verdi_ther_ad_godu"]
        self.assertEqual((reply.partner_cue, reply.partner_cue_after), ("Takk fyrir matinn!", "gjordu_svo_vel"))
        self.assertLess(cur.by_id["takk_fyrir"].order - cur.by_id["eg_tharf_hjalp"].order, 10)
        self.assertLess(cur.by_id["takk_fyrir"].order, cur.by_id["takk_fyrir_dvolina"].order)
        for fill in ("borga_med_korti", "opna_gluggann", "loka_hurdinni", "hringja", "taka_mynd"):
            self.assertIn("inf", cur.by_id[fill].tags)

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
            # every narration of the item's cue counts, connect() included: since #77 it advances
            # the rotation too, so only consecutive narrations can be compared
            this_lesson = [s.text for s in sc.segments if s.type == "narrate" and s.text in item.situations]
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

    def test_only_the_translation_fades_on_later_encounters_the_cue_stays(self):
        """Issue #26, narrowed by #210: the translation of the partner's line fades (the learner has to understand it),
        but the cue, the intent, plays in every encounter, so the learner always knows what they are to say and where
        they are. No turn drops it: the partner's line never decides the reply (#230 review)."""
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
        narrations = lambda translate, **kw: [s.text for s in self._play(b, dlg, translate=translate, **kw).segments if s.type == "narrate"]

        first = narrations(True)
        self.assertIn("Ask how much.", first)
        self.assertIn("Say no thanks.", first)
        self.assertTrue(any("With milk?" in n for n in first))
        later = narrations(False)
        self.assertIn("Ask how much.", later)
        self.assertIn("Say no thanks.", later, "the cue stays after the partner has spoken")
        self.assertFalse(any("With milk?" in n for n in later), "only the translation drops")
        # a meaning comes the first time its turn is heard
        self.assertTrue(any("With milk?" in n for n in narrations(frozenset({0}))))
        self.assertFalse(any("With milk?" in n for n in narrations(frozenset({1}))))

    @staticmethod
    def _play(builder, dlg, **kw):
        sc = Script(1, "Lesson 1", "is", "en")
        builder.dialogue(sc, dlg, **kw)
        return sc

    def test_a_scene_line_plays_in_every_encounter(self):
        from audiolesson.content import Dialogue, DialogueTurn
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        b = Builder(cur, Prompts.load(cur.known_lang), Timing(level="A1"), fresh())
        dlg = Dialogue(id="d", setting="A scene.", turns=[
            DialogueTurn(cue="Ask.", expect_text="Hæ.", partner="Viltu poka?", partner_meaning="A bag?", partner_scene="At the till."),
            DialogueTurn(cue="Answer.", expect_text="Já.", opener="Gjörðu svo vel.", opener_meaning="Here you go.", scene="Outside."),
        ])
        for translate in (True, False):
            segs = [(s.type, s.text) for s in self._play(b, dlg, translate=translate).segments if s.type in ("narrate", "speak")]
            texts = [t for _, t in segs]
            self.assertLess(texts.index("At the till."), texts.index("Viltu poka?"))
            self.assertLess(texts.index("Outside."), texts.index("Gjörðu svo vel."), "before the opener")

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
        """Stages climb; once an item has recombined with no fresh sentence left, it may be
        recalled again at ``meaning`` (repeating is fine, dropping it is not), which the
        learner update never counts as a demotion."""
        for item_id, stages in self.script.meta["exposures"].items():
            ladder = self.script.meta["ladders"][item_id]
            top = -1
            climbing = []
            for s in stages:
                if s not in ladder:
                    continue
                i = ladder.index(s)
                if s == "meaning" and i < top:
                    continue  # a repeat after the item's hardest stage today
                climbing.append(i)
                top = max(top, i)
            self.assertEqual(climbing, sorted(climbing), f"{item_id}: {stages}")

    def test_hard_phrase_is_built_backwards(self):
        text = self.script.transcript()
        self.assertIn("build it up from the end", text)
        # Issue #49: each backward-build chunk used to play at natural rate, the one part
        # of this ladder that never went through slow_rate despite existing specifically
        # so the learner can hear and imitate a hard phrase piece by piece — "(slow)" is
        # how the transcript marks a sub-1.0 rate segment (see Script.transcript()).
        self.assertIn("**Speaker A (slow):** plaît", text)
        # the learner's model answers read as "You", whichever voice models them; every
        # "**You:**" line is an answer and every answer is one
        answers = [seg.text for seg in self.script.segments if seg.type == "answer"]
        you = [line.removeprefix("**You:** ") for line in text.splitlines() if line.startswith("**You:** ")]
        self.assertEqual(you, answers)

    def test_script_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.json"
            self.script.save(p)
            back = Script.load(p)
            self.assertEqual(len(back.segments), len(self.script.segments))
            self.assertAlmostEqual(back.total_duration, self.script.total_duration, places=3)


class PartnerVoiceTests(unittest.TestCase):
    """The partner speaks in the voice the narration implies; the learner's model answers
    take the other one, so the two sides of an exchange never sound alike."""

    def exchange(self, speaker):
        from audiolesson.exercises import Builder

        bridge = {"id": "b", "kind": "phrase", "target": "B.", "meaning": "B.", "situation": "S b.",
                  "partner_cue": "Hæ!", "partner_cue_after": "a", "partner_cue_setup": "A woman greets you.",
                  "partner_cue_meaning": "Hi!", "partner_cue_situation": "She said hi. Answer."}
        if speaker:
            bridge["partner_cue_speaker"] = speaker
        raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": "a", "kind": "phrase", "target": "A.", "meaning": "A.", "situation": "S a."}, bridge]}
        cur = curriculum_from_dict(raw)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), fresh())
        sc = Script(1, "t", "is", "en")
        b.connect(sc, [cur.by_id["a"], cur.by_id["b"]])
        partner = {s.speaker for s in sc.segments if s.type == "speak"}
        learner = {s.speaker for s in sc.segments if s.type == "answer"}
        return partner, learner

    def test_partner_voices_match_the_narrations_he_or_she(self):
        """Lesson 8 feedback: "A woman comes over and greets you" was answered in the male
        voice (native_b spoke every partner line). Every profile voices native_a female and
        native_b male, so a bridge or dialogue whose narration only says she/woman/… must use
        native_a, and one that only says he/man/… native_b. Narration naming both (the partner
        and someone they talk about) is left to the author."""
        female = re.compile(r"\b(she|her|hers|herself|woman|girl|lady|mother|mum|aunt|grandmother|sister|daughter|wife|waitress|anna)\b", re.I)
        male = re.compile(r"\b(he|him|his|himself|man|boy|guy|father|dad|uncle|grandfather|brother|son|husband|waiter)\b", re.I)

        def expected(text: str) -> str | None:
            f, m = bool(female.search(text)), bool(male.search(text))
            return "native_a" if f and not m else "native_b" if m and not f else None

        for path in (ROOT / "curricula" / "is-en", CURRICULUM):
            cur = load_curriculum(path)
            for it in cur.items:
                if it.partner_cue and (want := expected(it.partner_cue_setup + " " + it.partner_cue_situation)):
                    self.assertEqual(it.partner_cue_speaker, want, f"{path.name}: bridge {it.id}")
            for d in cur.dialogues:
                if want := expected(" ".join([d.setting] + [t.cue for t in d.turns])):
                    self.assertEqual(d.partner_speaker, want, f"{path.name}: dialogue {d.id}")

    def test_a_female_partner_gets_the_female_voice_and_the_learner_the_other(self):
        self.assertEqual(self.exchange("native_a"), ({"native_a"}, {"native_b"}))

    def test_default_partner_is_unchanged(self):
        self.assertEqual(self.exchange(None), ({"native_b"}, {"native_a"}))

    def test_dialogue_learner_lines_take_the_other_voice(self):
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        dlg = next(d for d in cur.dialogues if d.partner_speaker == "native_a")
        learner = LearnerState("is", "en", "A1")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
        sc = Script(1, "t", "is", "en")
        b.dialogue(sc, dlg)
        self.assertEqual({s.speaker for s in sc.segments if s.type == "answer"}, {"native_b"})
        self.assertIn("native_a", {s.speaker for s in sc.segments if s.type == "speak"})

    def test_an_unknown_speaker_is_rejected(self):
        raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": "a", "kind": "phrase", "target": "A.", "meaning": "A."},
                         {"id": "b", "kind": "phrase", "target": "B.", "meaning": "B.", "partner_cue": "Hæ!",
                          "partner_cue_after": "a", "partner_cue_speaker": "native_c"}]}
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)


class SpeakerGenderTests(unittest.TestCase):
    """#112 review: practise both the woman's and the man's form when the words follow the
    speaker's gender («Ég er sein.» / «Ég er seinn.»), and say which one is asked for, each
    time — in the matching voice."""

    def builder(self, lang="en"):
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
        return cur, Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))

    @staticmethod
    def turns(sc, index=None):
        return [(s.type, s.speaker, s.text) for s in sc.segments if s.type != "pause" and (index is None or s.exercise == index)]

    def test_recalls_alternate_forms_announced_in_the_matching_voice(self):
        cur, b = self.builder()
        it = cur.by_id["eg_er_sein"]
        sc = Script(1, "t", "is", "en")
        for _ in range(4):
            b.recall(sc, it, "meaning")
        pairs = [(n[2].split(":")[0], a[1], a[2]) for n, a in zip(*[iter([t for t in self.turns(sc) if t[0] in ("narrate", "answer")])] * 2)]
        woman, man = ("As a woman", "native_a", "Ég er sein."), ("As a man", "native_b", "Ég er seinn.")
        self.assertEqual(pairs, [woman, man, woman, man])

    def test_the_introduction_presents_both_forms(self):
        cur, b = self.builder("ja")
        sc = Script(1, "t", "is", "ja")
        b.intro(sc, cur.by_id["eg_er_sein"])
        turns = self.turns(sc)
        self.assertIn(("narrate", "instructor", "男性はこう言います。"), turns)
        self.assertIn(("speak", "native_b", "Ég er seinn."), turns)
        self.assertTrue(turns[-2][2].startswith("女性として："), turns[-2])

    def test_words_that_do_not_change_are_not_announced(self):
        cur, b = self.builder()
        sc = Script(1, "t", "is", "en")
        b.recall(sc, cur.by_id["eg_er_ekki_viss"], "meaning")
        narration = [t[2] for t in self.turns(sc) if t[0] == "narrate"]
        self.assertFalse(any("As a" in n for n in narration), narration)
        self.assertEqual({t[1] for t in self.turns(sc) if t[0] == "answer"}, {"native_a"})

    def test_in_an_exchange_the_learner_takes_the_voice_opposite_the_partner(self):
        """Opposite voices keep the two sides apart; a gendered answer then takes that voice's
        form and is announced (a woman partner, so the learner answers as a man)."""
        from audiolesson.content import curriculum_from_dict

        raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": "hae", "kind": "phrase", "target": "Hæ.", "meaning": "Hi.", "situation": "S."},
                         {"id": "sein", "kind": "phrase", "target": "Ég er sein.", "target_m": "Ég er seinn.",
                          "meaning": "I'm late.", "situation": "S2.", "partner_cue": "Hvar ertu?", "partner_cue_after": "hae",
                          "partner_cue_setup": "Your friend calls. Greet her.", "partner_cue_meaning": "Where are you?",
                          "partner_cue_situation": "She asks where you are. Say you're late.",
                          "partner_cue_speaker": "native_a"}]}
        from audiolesson.exercises import Builder

        cur2 = curriculum_from_dict(raw)
        b2 = Builder(cur2, Prompts.load("en"), Timing(level="A1"), fresh())
        sc = Script(1, "t", "is", "en")
        b2.connect(sc, [cur2.by_id["hae"], cur2.by_id["sein"]])
        turns = self.turns(sc)
        self.assertIn(("speak", "native_a", "Hvar ertu?"), turns)
        self.assertEqual([t[1:] for t in turns if t[0] == "answer"], [("native_b", "Hæ."), ("native_b", "Ég er seinn.")])
        self.assertIn(("narrate", "instructor", "As a man: She asks where you are. Say you're late."), turns)

    def test_the_review_question_carries_the_announcement(self):
        cur, b = self.builder()
        sc = Script(1, "t", "is", "en")
        b.recall(sc, cur.by_id["eg_er_sein"], "situation")
        (q,) = sc.review_questions()
        self.assertTrue(q["prompt"].startswith("As a woman: "), q)
        self.assertEqual(q["answer"], "Ég er sein.")

    def test_notes_no_longer_hide_the_mans_form(self):
        """#112/#113: a man's form lives in data (target_m), never only in a note."""
        for it in load_curriculum(ROOT / "curricula" / "is-en").items:
            self.assertNotIn("masculine: ", it.pronunciation_notes or "", f"{it.id}: move the man's form to target_m")

    # ---- #113: constructions, transforms and dialogue lines ------------------

    def state_builder(self):
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        for f in cur.items_with_tag("state_f") + [cur.by_id["eg_er_state"]]:
            learner.items[f.id] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="meaning")
        return cur, Builder(cur, Prompts.load("en"), Timing(level="A1"), learner, random.Random(3))

    def test_a_filled_construction_alternates_forms_when_its_fill_has_a_mans_form(self):
        cur, b = self.state_builder()
        mans = {f.target: f.target_m for f in cur.items_with_tag("state_f") if f.target_m}
        sc = Script(1, "t", "is", "en")
        for _ in range(12):
            b.recall(sc, cur.by_id["eg_er_state"], "meaning")
        seen = set()
        for ex in sc.exercises:
            narr = next(s.text for s in sc.segments if s.exercise == ex.index and s.type == "narrate")
            ans = next(s for s in sc.segments if s.exercise == ex.index and s.type == "answer")
            word = ans.text.rstrip(".").split()[-1]
            if word == "einmana":
                self.assertFalse(narr.startswith("As a"), "a fill with one form for both is not announced")
                continue
            gender = "m" if narr.startswith("As a man:") else "f" if narr.startswith("As a woman:") else None
            self.assertIsNotNone(gender, narr)
            self.assertEqual(ans.speaker, {"f": "native_a", "m": "native_b"}[gender])
            self.assertIn(word, mans.values() if gender == "m" else mans.keys(), (narr, ans.text))
            seen.add(gender)
        self.assertEqual(seen, {"f", "m"}, "both forms get practised")

    def test_resolve_slots_takes_the_fills_mans_form(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        c, glod, einmana = cur.by_id["eg_er_state"], cur.by_id["glod"], cur.by_id["einmana"]
        self.assertEqual(cur.resolve_slots(c, {"state": glod})[0], "Ég er glöð.")
        self.assertEqual(cur.resolve_slots(c, {"state": glod}, "m")[0], "Ég er glaður.")
        self.assertEqual(cur.resolve_slots(c, {"state": einmana}, "m")[0], "Ég er einmana.")

    def test_a_fill_without_a_mans_form_is_not_announced(self):
        from audiolesson.exercises import Builder

        raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": "lonely", "kind": "vocab", "target": "einmana", "meaning": "lonely", "tags": ["st"]},
                         {"id": "c", "kind": "construction", "target": "Ég er {s}.", "meaning": "I'm {s}.",
                          "slots": {"s": "st"}, "example": {"s": "lonely"}}]}
        cur = curriculum_from_dict(raw)
        learner = fresh()
        learner.items["lonely"] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="meaning")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
        sc = Script(1, "t", "is", "en")
        b.recall(sc, cur.by_id["c"], "meaning")
        self.assertFalse(any(s.text.startswith("As a") for s in sc.segments if s.type == "narrate"))

    def test_transform_examples_use_the_mans_form(self):
        cur, b = self.state_builder()
        past = cur.by_id["transform_var"]
        exm = next(e for e in past.examples if e.result_m)
        sc = Script(1, "t", "is", "en")
        for _ in range(2):
            b._transform_prompt(sc, sc.new_exercise("recall", "meaning", [past.id]), past, exm)
        turns = [(s.type, s.speaker, s.text) for s in sc.segments if s.type != "pause"]
        self.assertIn(("narrate", "instructor", "As a man: " + past.instruction), turns)
        self.assertIn(("speak", "native_b", "Ég er þreyttur."), turns)
        self.assertIn(("answer", "native_b", "Ég var þreyttur í gær."), turns)
        self.assertIn(("answer", "native_a", "Ég var þreytt í gær."), turns)
        # only the source changes: «Hún er glöð.» is about her, so no announcement
        hun = cur.by_id["transform_feelings_hun"]
        exm = hun.examples[0]
        sc = Script(1, "t", "is", "en")
        for _ in range(2):
            b._transform_prompt(sc, sc.new_exercise("recall", "meaning", [hun.id]), hun, exm)
        turns = [(s.type, s.speaker, s.text) for s in sc.segments if s.type != "pause"]
        self.assertIn(("speak", "native_b", "Ég er glaður."), turns)
        self.assertEqual({t for t in turns if t[0] == "answer"}, {("answer", "native_a", "Hún er glöð.")})
        self.assertFalse(any(t[2].startswith("As a") for t in turns if t[0] == "narrate"))

    def test_a_second_person_result_keeps_its_source_ungendered(self):
        """PR #114 review: «Þú ert þreytt.» agrees with the person addressed, whom the exercise
        never names. A man's source («Ég er þreyttur.») next to it would be an unexplained
        mismatch, and source_m/result_m can't model speaker and listener separately, so a
        result addressed to "þú" gets no man's source until the listener is specified."""
        for it in load_curriculum(ROOT / "curricula" / "is-en").items:
            for e in it.examples:
                if re.match(r"(?i)þú\b", e.result):
                    self.assertFalse(e.source_m or e.result_m, f"{it.id}: {e.source} → {e.result}")

    def test_a_dialogue_line_takes_the_mans_form_opposite_a_woman(self):
        cur, b = self.builder()
        dlg = next(d for d in cur.dialogues if any(t.expect_text_m for t in d.turns))
        self.assertEqual(dlg.partner_speaker, "native_a")
        sc = Script(1, "t", "is", "en")
        b.dialogue(sc, dlg)
        turns = [(s.type, s.speaker, s.text) for s in sc.segments if s.type != "pause"]
        self.assertIn(("answer", "native_b", "Afsakið, ég er týndur."), turns)
        self.assertIn(("narrate", "instructor", "As a man: Excuse yourself and say you're lost."), turns)

    def test_review_questions_carry_the_announcement_for_a_gendered_construction(self):
        cur, b = self.state_builder()
        sc = Script(1, "t", "is", "en")
        for _ in range(6):
            b.recall(sc, cur.by_id["eg_er_state"], "meaning")
        questions = sc.review_questions()
        gendered = [q for q in questions if not q["answer"].endswith("einmana.")]
        self.assertTrue(gendered)
        for q in gendered:
            self.assertTrue(q["prompt"].startswith(("As a woman: ", "As a man: ")), q)


class RecombineNoveltyTests(unittest.TestCase):
    """Issue #105: recombination only asks for a sentence not yet heard in this lesson."""

    def builder(self, seed=0):
        import random

        from audiolesson.exercises import Builder

        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "fara", "kind": "vocab", "target": "fara", "meaning": "to go", "tags": ["inf"]},
                {"id": "sofa", "kind": "vocab", "target": "sofa", "meaning": "to sleep", "tags": ["inf"]},
                {"id": "vil", "kind": "construction", "target": "Ég vil {inf}.", "meaning": "I want {inf}.",
                 "slots": {"inf": "inf"}, "example": {"inf": "fara"}},
            ],
        }
        cur = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        for i in ("fara", "sofa", "vil"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="meaning")
        return cur, Builder(cur, Prompts.load("en"), Timing(level="A1"), learner, random.Random(seed))

    @staticmethod
    def answers(sc):
        return [s.text for s in sc.segments if s.type == "answer"]

    def test_a_heard_fill_is_replaced_by_the_other(self):
        for seed in range(6):
            cur, b = self.builder(seed)
            b.heard.add("ég vil fara")
            sc = Script(1, "t", "is", "en")
            b.recall(sc, cur.by_id["vil"], "recombine")
            self.assertEqual(sc.exercises[0].kind, "generative")
            self.assertEqual(self.answers(sc), ["Ég vil sofa."])

    def test_nothing_new_left_means_no_recombine_exercise(self):
        cur, b = self.builder()
        b.heard |= {"ég vil fara", "ég vil sofa"}
        for item_id in ("vil", "sofa"):  # the construction, and a word placed into it
            self.assertEqual(b.recombine_status(cur.by_id[item_id]), "heard")
            sc = Script(1, "t", "is", "en")
            b.recall(sc, cur.by_id[item_id], "recombine")
            self.assertNotEqual(sc.exercises[0].kind, "generative")
            narration = " ".join(s.text for s in sc.segments if s.type == "narrate")
            self.assertNotIn("in a sentence", narration)

    def test_status_has_no_side_effects(self):
        cur, b = self.builder()
        state = b.rng.getstate()
        self.assertEqual(b.recombine_status(cur.by_id["vil"]), "novel")
        self.assertEqual(b.rng.getstate(), state)
        self.assertEqual(b.used_combos, set())

    def test_no_lesson_recombines_a_line_it_already_presented(self):
        _, scripts = course(8)
        seen_generative = 0
        for sc in scripts:
            heard = set()
            for ex in sc.exercises:
                segs = [s for s in sc.segments if s.exercise == ex.index]
                if ex.kind == "generative":
                    seen_generative += 1
                    answer = next(s.text for s in segs if s.type == "answer")
                    self.assertNotIn(answer.strip().rstrip(".?!…").lower(), heard, f"lesson {sc.lesson_number}: {ex.label}")
                for s in segs:
                    if s.type in ("speak", "answer") and s.lang == sc.target_lang and s.role not in ("partial", "hint"):
                        heard.add(s.text.strip().rstrip(".?!…").strip().lower())
        self.assertGreater(seen_generative, 0, "recombination still happens when something new is possible")


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
                    if dlg_id in sc.meta.get("dialogues_listened", []):
                        continue  # played as listening (#149 step 3): its own mechanism, not a step of this series
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

    def test_confirmed_outcomes_schedule_the_next_lesson_differently(self):
        """Issue #119: the same item history, reported as recalled, hesitated or not recalled,
        gives three different schedules — and an unreported item keeps the presumed-success
        schedule without counting as confirmed."""
        outcomes = {}
        for outcome in ("recalled", "hesitated", "failed", None):
            learner, scripts = course(6)
            # an item the last lesson practised, on a schedule that grew
            item = next(i for i in scripts[-1].meta["exposures"] if learner.items[i].interval_days > 5)
            st = learner.items[item]
            self.assertGreater(st.interval_days, 1, "a schedule that grew, to tell the outcomes apart")
            day = TODAY + timedelta(days=11)  # the day after the last lesson (course(): every 2 days)
            lists = {"failed": [], "hesitated": [], "recalled": []}
            if outcome:
                lists[outcome] = [item]
            learner.report(lists["failed"], [], day, 6, hesitated=lists["hesitated"], recalled=lists["recalled"])
            outcomes[outcome] = (st.due, st.interval_days, st.recalled, st.hesitated, st.failures, st.last_outcome)
        recalled, hesitated, failed, unreported = (outcomes[k] for k in ("recalled", "hesitated", "failed", None))
        self.assertEqual(failed[0], (TODAY + timedelta(days=12)).isoformat(), "not recalled: tomorrow")
        self.assertLess(failed[0], hesitated[0])
        self.assertLess(hesitated[0], recalled[0], "hesitated: sooner than a clean recall")
        self.assertEqual(recalled[:2], unreported[:2], "recalled keeps the presumed schedule")
        self.assertEqual([o[2:] for o in (recalled, hesitated, failed)], [(1, 0, 0, "recalled"), (0, 1, 0, "hesitated"), (0, 0, 1, "not_recalled")])
        self.assertEqual(unreported[2:], (0, 0, 0, ""), "no feedback: nothing confirmed")

    def test_appearances_without_feedback_confirm_nothing(self):
        learner, _ = course(8)
        practised = [st for st in learner.items.values() if st.successes >= 3]
        self.assertTrue(practised)
        self.assertTrue(all(st.recalled == st.hesitated == st.failures == 0 and not st.last_outcome for st in practised))

    def test_an_item_in_two_reported_lists_takes_the_weaker_outcome(self):
        learner, scripts = course(2)
        a, b = scripts[0].meta["new_items"][:2]
        changed = learner.report([a], [], TODAY + timedelta(days=3), 2, hesitated=[a, b], recalled=[a, b])
        self.assertEqual((changed["failed"], changed["hesitated"], changed["recalled"]), ([a], [b], []))
        self.assertEqual(learner.items[a].history[-1]["outcome"], "not_recalled")

    def test_older_learner_files_load_without_confirmed_counts(self):
        """Migration: a learner.json from before #119 keeps its exposures, history and reported
        failures; the confirmed recalled/hesitated counts start at zero."""
        learner, _ = course(2)
        raw = learner.to_dict()
        for st in raw["items"].values():
            for key in ("recalled", "hesitated", "last_outcome"):
                del st[key]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "l.json"
            p.write_text(json.dumps(raw), encoding="utf-8")
            back = LearnerState.load(p)
        for item_id, st in back.items.items():
            self.assertEqual((st.recalled, st.hesitated, st.last_outcome), (0, 0, ""))
            self.assertEqual((st.exposures, st.history), (learner.items[item_id].exposures, learner.items[item_id].history))

    def test_a_dialogue_heard_in_full_rests_before_it_plays_again(self):
        """Simulated lessons 7-12: «nagranni» was the only dialogue eligible, and played in
        full in every lesson. Once heard in full it now rests dialogue_rest_lessons lessons;
        one still growing a turn per encounter comes back next lesson."""
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(3)],
            "dialogues": [
                {"id": "short", "setting": "A.", "turns": [{"cue": "Say it.", "expect": "w0"}, {"cue": "Say it.", "expect": "w1"}]},
                {"id": "long", "setting": "B.", "turns": [{"cue": "Say it.", "expect": f"w{i}"} for i in range(3)]},
            ],
        }
        cur = curriculum_from_dict(raw)

        def eligible(done: dict[str, int], played: dict[int, list[str]], last: int) -> set[str]:
            learner = LearnerState("is", "en", "A1")
            for i in range(3):
                learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="meaning")
            learner.dialogues_done = dict(done)
            learner.lessons = [{"number": n, "dialogues": played.get(n, [])} for n in range(1, last + 1)]
            learner.lessons_completed = last
            out = set()
            for _ in range(2):
                planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
                planner.dialogues_played = sorted(out)  # ask again without what it already gave
                d = planner.eligible_dialogue()
                if d is None:
                    break
                out.add(d.id)
            return out

        both = {"short": 1, "long": 1}  # short (2 turns) was heard in full; long (3) got 2 of 3
        self.assertEqual(eligible(both, {4: ["short", "long"]}, 4), {"long"}, "the full one rests, the growing one continues")
        self.assertEqual(eligible(both, {1: ["short", "long"]}, 3), {"long"})
        self.assertEqual(eligible(both, {1: ["short", "long"]}, 4), {"short", "long"}, "rested three lessons")
        self.assertEqual(eligible({"short": 3}, {}, 4), {"short", "long"}, "no record of when: never held back")

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


class PrematureReviewTests(unittest.TestCase):
    """Issue #94: spare time used to go to items that were not due, least premature first, so
    the same well-known phrases came back in every lesson whatever their interval. Not-due
    items now wait while due reviews and new material fill the lesson."""

    @staticmethod
    def _curriculum(due: int, not_due: int, new: int):
        return curriculum_from_dict(
            {
                "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
                "items": [{"id": f"d{i}", "kind": "phrase", "target": f"Due {i}.", "meaning": f"Due {i}."} for i in range(due)]
                + [{"id": f"n{i}", "kind": "phrase", "target": f"Known {i}.", "meaning": f"Known {i}."} for i in range(not_due)]
                + [{"id": f"w{i}", "kind": "phrase", "target": f"Orð {i}.", "meaning": f"Word {i}."} for i in range(new)],
            }
        )

    @staticmethod
    def _state(due_in: int, practised_ago: int, interval: float) -> ItemState:
        return ItemState(
            due=(TODAY + timedelta(days=due_in)).isoformat(),
            last_practiced=(TODAY - timedelta(days=practised_ago)).isoformat(),
            interval_days=interval,
            successes=4,
            durable_successes=3,
            stage="meaning",
        )

    def test_not_due_items_wait_while_due_reviews_and_new_material_fill_the_lesson(self):
        cur = self._curriculum(due=20, not_due=6, new=30)
        learner = LearnerState("is", "en", "A1")
        for i in range(20):
            learner.items[f"d{i}"] = self._state(due_in=0, practised_ago=7, interval=7)
        for i in range(6):
            learner.items[f"n{i}"] = self._state(due_in=40, practised_ago=4, interval=44)
        cfg = PlanConfig(minutes=15, seed=1, new_items=3, drill_streak_limit=1000, dialogue_every=1000, note_chance=0.0)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        first: dict[str, int] = {}
        for e in sc.exercises:
            for i in e.item_ids:
                first.setdefault(i, e.index)
        new = sc.meta["new_items"]
        self.assertGreater(len(new), 3, "spare time went to a second batch of new items")
        self.assertLessEqual(len(new), 3 + cfg.resolved_extra_arc_items() + 1)  # + a pulled-in filler at most
        not_due = [first[f"n{i}"] for i in range(6) if f"n{i}" in first]
        if not_due:
            self.assertGreater(min(not_due), max(first[f"d{i}"] for i in range(20)), "a not-due item before a due one")
            self.assertGreater(min(not_due), first[new[3]], "a not-due item before the second batch of new items")

        # on a tighter budget the due reviews and new items fill it all: nothing waits early
        cfg = PlanConfig(minutes=6, seed=1, new_items=3, drill_streak_limit=1000, dialogue_every=1000, note_chance=0.0)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        self.assertFalse({f"n{i}" for i in range(6)} & {i for e in sc.exercises for i in e.item_ids})
        self.assertEqual(sc.meta["reviewed_early"], [])

    def test_early_reviews_take_the_longest_rested_first(self):
        """With nothing due and nothing new, the lesson fills with not-due items: first those
        rested at least half their interval, the longest ago first; one practised yesterday
        only after all of them."""
        cur = self._curriculum(due=1, not_due=8, new=0)
        learner = LearnerState("is", "en", "A1")
        for i in range(7):
            learner.items[f"n{i}"] = self._state(due_in=3, practised_ago=20 - i, interval=20)  # n0 the longest ago
        learner.items["n7"] = self._state(due_in=19, practised_ago=1, interval=20)  # just practised
        learner.items["d0"] = self._state(due_in=0, practised_ago=3, interval=3)  # one due item: a lesson to fill
        cfg = PlanConfig(minutes=10, seed=1, new_items=0, dialogue_every=1000, note_chance=0.0)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=TODAY).build()
        order = list(dict.fromkeys(e.item_ids[0] for e in sc.exercises if e.kind == "recall"))
        self.assertEqual(order[0], "d0", "the due item first")
        rested = [i for i in order if i in {f"n{k}" for k in range(7)}]
        self.assertEqual(rested, sorted(rested, key=lambda i: int(i[1:])), "the longest rested first")
        if "n7" in order:
            self.assertEqual(set(rested), {f"n{k}" for k in range(7)}, "yesterday's item only after every rested one")
            self.assertGreater(order.index("n7"), max(order.index(i) for i in rested))

    def test_early_words_are_said_in_a_sentence_within_two_lessons(self):
        """Issue #80's acceptance criterion: «vegabréf» is used in a sentence within its first
        two lessons — and so are «frábært» and «fimm hundruð krónur», the other words that
        waited longest for a frame; «já», «nei» and «Ég líka.» answer situations."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        words = {"vegabref": "vegabréf", "frabaert": "frábært", "fimm_hundrud_kronur": "fimm hundruð krónur"}
        introduced: dict[str, int] = {}
        in_sentence: dict[str, int] = {}
        answered_situations: set[str] = set()
        for _ in range(14):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_items=6), today=day).build()
            for item_id in sc.meta["new_items"]:
                introduced.setdefault(item_id, sc.lesson_number)
            for seg in sc.segments:
                if seg.type != "answer" or not seg.text:
                    continue
                for item_id, word in words.items():
                    if word in seg.text.lower() and seg.text.lower().strip(" .!?") != word:
                        in_sentence.setdefault(item_id, sc.lesson_number)
            for ex in sc.exercises:
                if ex.stage == "situation" and ex.item_ids and ex.item_ids[0] in ("ja", "nei", "eg_lika"):
                    answered_situations.add(ex.item_ids[0])
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        for item_id in words:
            self.assertIn(item_id, introduced)
            self.assertIn(item_id, in_sentence, f"{item_id} never said in a sentence")
            self.assertLessEqual(in_sentence[item_id] - introduced[item_id], 1, item_id)
        self.assertEqual(answered_situations, {"ja", "nei", "eg_lika"})

    def test_an_item_removed_from_the_curriculum_is_ignored(self):
        """#123 review: «lika» left the curriculum («Ég líka.» is eg_lika). An older learner
        file still has it; lessons build and never practise it."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertNotIn("lika", cur.by_id)
        learner = LearnerState("is", "en", "A1")
        for i in ("godan_daginn", "takk", "lika"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=2, stage="meaning")
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=1), today=TODAY).build()
        self.assertNotIn("lika", {i for e in sc.exercises for i in e.item_ids})
        self.assertIn("takk", sc.meta["reviewed_items"])

    def test_a_later_arc_never_takes_a_lesson_past_the_new_item_ceiling(self):
        """Simulated lessons 1-12: pace 10 plus half again was 15 new items in 30 minutes.
        While a lesson has other work, a later arc stops at about one new item per 3
        minutes; only the last resort (nothing else left to do) may go past it."""
        self.assertEqual(PlanConfig(minutes=30, new_items=6).resolved_extra_arc_items(), 3)
        self.assertEqual(PlanConfig(minutes=30, new_items=8).resolved_extra_arc_items(), 2)
        self.assertEqual(PlanConfig(minutes=30, new_items=10).resolved_extra_arc_items(), 0)
        self.assertEqual(PlanConfig(minutes=30, new_items=10).resolved_extra_arc_items(capped=False), 5)
        self.assertEqual(PlanConfig(minutes=15, new_items=3).resolved_extra_arc_items(), 2)

    def test_a_course_stops_repeating_well_known_items(self):
        """#94's acceptance criterion on the real course: no item with an interval of a week or
        more is drilled (recalled, or in a connect exercise) in more than half the lessons
        within its interval. Dialogues and fills of a pattern may still use it. Lessons stay
        on length and the new items per lesson near the pace."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        drilled: dict[str, dict[int, float]] = {}
        n_lessons = 25
        for _ in range(n_lessons):
            interval = {i: st.interval_days for i, st in learner.items.items()}
            cfg = PlanConfig(minutes=30, seed=1, new_items=6)
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=day).build()
            for e in sc.exercises:
                heads = e.item_ids if e.kind == "connect" else e.item_ids[:1] if e.kind in ("recall", "generative") else []
                for i in heads:
                    if i in interval:
                        drilled.setdefault(i, {})[sc.lesson_number] = interval[i]
            if sc.lesson_number >= 5:
                self.assertGreater(sc.total_duration, 26 * 60, sc.lesson_number)
            if sc.lesson_number >= 11:
                self.assertLessEqual(len(sc.meta["new_items"]), 6 + cfg.resolved_extra_arc_items() + 3, sc.lesson_number)
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        over = []
        for item, lessons in drilled.items():
            for n, ivl in lessons.items():
                window = range(n + 1, min(n_lessons, n + int(ivl) - 1) + 1)
                if ivl >= 7 and n > 10 and len(window) >= 4:
                    hits = sum(1 for k in window if k in lessons)
                    if hits / len(window) > 0.5:
                        over.append((item, n, ivl, hits, len(window)))
        self.assertLessEqual(len({o[0] for o in over}), 2, over)


class StableItemTests(unittest.TestCase):
    """Issue #151: já, nei and hæ, reported as recalled, came back in every lesson and
    several times per lesson: the planner filled spare time with them, and early practice
    never moved their schedule. Stable items now wait for their date, and the spare time
    goes to substitution drills over known patterns and to today's new items."""

    PHRASES = [f"Orð {n}." for n in ("eitt", "tvö", "þrjú", "fjögur", "fimm", "sex")]

    # the phrases have no situations, so nothing could break a drill streak: let it run
    def _curriculum(self, with_pattern: bool = False):
        items = [{"id": "w0", "kind": "phrase", "target": "Nýtt orð hér.", "meaning": "A new word here."}]
        items += [{"id": f"s{n}", "kind": "phrase", "target": t, "meaning": f"Stable {n}."} for n, t in enumerate(self.PHRASES)]
        items += [{"id": f"u{n}", "kind": "phrase", "target": t.replace("Orð", "Annað"), "meaning": f"Unsure {n}."} for n, t in enumerate(self.PHRASES)]
        if with_pattern:
            for v, en in (("fara heim", "go home"), ("sofa", "sleep"), ("borða", "eat"), ("versla", "shop"), ("fara út", "go out")):
                items.append({"id": v.replace(" ", "_").replace("ð", "d"), "kind": "vocab", "target": v, "meaning": en, "meaning_spoken": "to " + en, "tags": ["inf"]})
            items.append({"id": "eg_vil", "kind": "construction", "target": "Ég vil {inf}.", "meaning": "I want to {inf}.", "slots": {"inf": "inf"}})
        return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})

    @staticmethod
    def _state(durable: int, successes: int, due_in: int, stage: str = "meaning", **kw) -> ItemState:
        return ItemState(stage=stage, durable_successes=durable, successes=successes, interval_days=7.2,
                         due=(TODAY + timedelta(days=due_in)).isoformat(),
                         last_practiced=(TODAY - timedelta(days=7)).isoformat(), **kw)

    def _learner(self, cur) -> LearnerState:
        learner = LearnerState("is", "en", "A1")
        for n in range(len(self.PHRASES)):
            learner.items[f"s{n}"] = self._state(2, 17, due_in=3, last_outcome="recalled")
            learner.items[f"u{n}"] = self._state(1, 4, due_in=3)
        learner.items["u0"].due = TODAY.isoformat()  # one due review, so the lesson has reviews
        return learner

    def test_stable_means_spaced_recalls_many_recalls_and_no_recent_trouble(self):
        cur = self._curriculum()
        learner = self._learner(cur)
        learner.items["s1"].history = [{"lesson": 1, "stages": ["situation"], "ok": True, "outcome": "hesitated"}]
        learner.items["s2"].last_outcome = ""
        learner.items["s2"].durable_successes = 1
        learner.items["s3"].successes = 5
        learner.items["s4"].stage = "hinted"
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=TODAY)
        stable = {i for i in learner.items if planner._stable(cur.by_id[i])}
        self.assertEqual(stable, {"s0", "s5"}, "hesitated lately / one spaced recall and no report / few recalls / hinted")

    def test_fillers_leave_stable_items_alone_until_they_are_due(self):
        cur = self._curriculum()
        learner = self._learner(cur)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, new_items=1, drill_streak_limit=1000), today=TODAY).build()
        used = {i for e in sc.exercises if e.kind in ("recall", "connect", "generative") for i in e.item_ids}
        self.assertFalse(used & {f"s{n}" for n in range(6)}, "stable, not due: not even rested ones fill")
        self.assertTrue(used & {f"u{n}" for n in range(1, 6)}, "rested items that aren't stable still fill early")

    def test_a_stable_due_item_is_reviewed_once(self):
        cur = self._curriculum()
        learner = self._learner(cur)
        learner.items["s0"].due = TODAY.isoformat()
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, new_items=1, drill_streak_limit=1000), today=TODAY).build()
        self.assertEqual(sum(1 for e in sc.exercises if "s0" in e.item_ids), 1, "no second pass, no extra touch")
        self.assertGreater(sum(1 for e in sc.exercises if "u0" in e.item_ids), 1, "an item still being learned gets its second pass")

    def test_spare_time_goes_to_substitution_runs_in_one_frame(self):
        """A known pattern with its other words, one frame at a time («Ég vil sofa.» →
        «Ég vil borða.»), the words met before but not necessarily learned."""
        cur = self._curriculum(with_pattern=True)
        learner = self._learner(cur)
        learner.items["eg_vil"] = self._state(1, 6, due_in=3, stage="recombine")
        for v in ("fara_heim", "sofa", "borda", "versla", "fara_ut"):
            learner.items[v] = self._state(1, 4, due_in=3)
            learner.items[v].last_practiced = (TODAY - timedelta(days=1)).isoformat()  # not rested: no review of their own
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, new_items=1, drill_streak_limit=1000), today=TODAY).build()
        drills = [k for k, e in enumerate(sc.exercises) if e.kind == "generative" and e.item_ids[0] == "eg_vil"]
        self.assertEqual(len(drills), PlanConfig().substitutions_per_construction)
        self.assertTrue(any(b - a == 1 for a, b in zip(drills, drills[1:])), f"a run in one frame: {drills}")
        lines = [e.label for k, e in enumerate(sc.exercises) if k in drills]
        self.assertEqual(len(set(lines)), len(lines), lines)

    def test_a_course_keeps_stable_items_for_their_due_date(self):
        """The real course, 12 lessons: a stable item that isn't due is never drilled on its
        own (a connect exchange with one of today's new items, or a milestone's contrast
        right after its note, may still use it), and a stable due item at most twice."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for _ in range(12):
            planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=5), today=day)
            sc = planner.build()
            stable = {i for i in learner.items if planner._stable(cur.by_id[i])}
            due = {i for i in stable if learner.review_priority(i, day) >= 1.0}
            new = set(sc.meta["new_items"])
            for k, e in enumerate(sc.exercises):
                if e.kind == "recall" and e.item_ids[0] in stable - due:
                    self.assertIn("note", [x.kind for x in sc.exercises[max(0, k - 2):k]], (sc.lesson_number, e.label))
                if e.kind == "connect" and set(e.item_ids) & (stable - due):
                    self.assertTrue(set(e.item_ids) & (new | due), (sc.lesson_number, e.item_ids))
            for i in due:
                self.assertLessEqual(sum(1 for e in sc.exercises if e.kind in ("recall", "connect") and i in e.item_ids), 2, i)
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)


class OpenItemTests(unittest.TestCase):
    """Issue #149 step 1a (G11): a failed item stays open until a later confirmed recall;
    presumed success neither closes it nor lengthens its interval, and every lesson practises it."""

    def _setup(self, failed_at_start: bool = True):
        helper = StableItemTests()
        cur = helper._curriculum()
        learner = helper._learner(cur)
        learner.items["s0"] = helper._state(0, 3, due_in=-1, stage="cloze", failures=2, last_outcome="not_recalled")
        learner.items["s0"].history = [{"lesson": 9, "stages": ["meaning"], "ok": False, "outcome": "not_recalled"}]
        learner.items["s1"] = helper._state(0, 3, due_in=3, failures=1)  # a failure from before last_outcome existed
        return cur, learner

    def _build(self, cur, learner, **cfg):
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, new_items=1, drill_streak_limit=1000, **cfg), today=TODAY).build()

    def test_open_means_no_confirmed_recall_since_the_failure(self):
        _, learner = self._setup()
        self.assertEqual(set(learner.open_items()), {"s0", "s1"})
        learner.items["s0"].last_outcome = "recalled"
        learner.items["s1"].recalled = 1
        self.assertEqual(learner.open_items(), [])

    def test_each_open_item_is_practised_at_least_four_times_spread_over_the_lesson(self):
        cur, learner = self._setup()
        sc = self._build(cur, learner)
        self.assertEqual(sc.meta["open_items"], ["s0", "s1"])
        total = len(sc.exercises)
        for i in ("s0", "s1"):
            spots = [k for k, e in enumerate(sc.exercises) if e.kind in ("recall", "connect", "generative") and i in e.item_ids]
            self.assertGreaterEqual(len(spots), 4, (i, spots))
            self.assertGreater(spots[-1], total / 2, (i, spots, total))

    def test_presumed_success_does_not_close_or_lengthen_an_open_item(self):
        cur, learner = self._setup()
        sc = self._build(cur, learner)
        before = learner.items["s0"].ease
        apply_to_learner(sc, learner, TODAY)
        st = learner.items["s0"]
        self.assertTrue(learner.is_open("s0"))
        self.assertEqual((st.durable_successes, st.interval_days, st.ease), (0, 1, before))
        self.assertEqual(st.due, (TODAY + timedelta(days=1)).isoformat())

    def test_a_confirmed_recall_closes_it(self):
        cur, learner = self._setup()
        apply_to_learner(self._build(cur, learner), learner, TODAY)
        learner.report([], [], TODAY, recalled=["s0"])
        self.assertFalse(learner.is_open("s0"))
        sc = self._build(cur, learner)
        self.assertNotIn("s0", sc.meta["open_items"])

    def test_more_open_items_than_the_cap_wait_their_turn(self):
        cur, learner = self._setup()
        sc = self._build(cur, learner, max_open_items=1)
        self.assertEqual(len(sc.meta["open_items"]), 1)
        self.assertEqual(len(sc.meta["open_not_fitted"]), 1)

    def test_a_course_spreads_open_practice_over_the_lesson_and_rotates_a_backlog(self):
        """The real curriculum, 30-minute lessons, two new items failed in lessons 3, 4, 6 and
        7: no gap over 8 minutes between an open item's practices, some in the last third, and
        the old failures come round instead of waiting behind the newest."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        waited: dict[str, int] = {}
        for n in range(1, 11):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=5), today=day).build()
            for i in sc.meta["open_items"]:
                spots = [e.start for e in sc.exercises if e.kind in ("recall", "connect", "generative") and i in e.item_ids]
                self.assertGreaterEqual(len(spots), 4, (n, i))
                self.assertGreater(spots[-1], 0.6 * sc.total_duration, (n, i, spots))
                gaps = [b - a for a, b in zip(spots, spots[1:])]
                self.assertLess(max(gaps), 8 * 60, (n, i, [round(x / 60, 1) for x in spots]))
            for i in sc.meta["open_not_fitted"]:
                waited[i] = waited.get(i, 0) + 1
            apply_to_learner(sc, learner, day)
            if n in (3, 4, 6, 7):
                learner.report(sc.meta["new_items"][:2], [], day + timedelta(days=1), lesson_number=n)
            day += timedelta(days=1)
        self.assertTrue(waited, "the backlog should exceed the cap in this course")
        self.assertLessEqual(max(waited.values()), 3, f"every open item comes round: {waited}")

    def test_open_practice_never_ends_a_lesson_early(self):
        """Owner's review of #162: five open practices placed together made a drill streak
        that ended lesson 14 at 15.5 of 30 minutes. The real curriculum, pace 5, two new items
        failed in lessons 3, 4, 6, 7 and 12 (only new items confirmed afterwards): from lesson
        9 on every lesson runs at least 25 of its 30 minutes (the daily dose, §9), and open
        practices never run five in a row."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for n in range(1, 17):
            cfg = PlanConfig(minutes=30, new_items=5)
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=day).build()
            if n >= 9:
                self.assertGreaterEqual(sc.total_duration, 25 * 60, n)
            open_ids = set(sc.meta["open_items"])
            run = 0
            for e in sc.exercises:
                run = run + 1 if e.kind == "recall" and e.item_ids and e.item_ids[0] in open_ids else 0
                self.assertLess(run, 5, (n, e.index))
            apply_to_learner(sc, learner, day)
            new = sc.meta["new_items"]
            failed = new[:2] if n in (3, 4, 6, 7, 12) else []
            learner.report(failed, [], day + timedelta(days=1), lesson_number=n, recalled=[i for i in new if i not in failed])
            day += timedelta(days=1)

    def test_unconfirmed_practice_does_not_raise_an_open_items_stage(self):
        cur, learner = self._setup()
        before = learner.items["s0"].stage
        apply_to_learner(self._build(cur, learner), learner, TODAY)
        self.assertEqual(learner.items["s0"].stage, before)
        self.assertEqual(learner.items["s0"].open_practiced, learner.lessons_completed)



class EmbeddedPartTests(unittest.TestCase):
    """#149 (lesson 13 feedback): a part of a phrase the learner can say shouldn't come back as a
    single word. It is heard inside an easy sentence; the review decides if it counts as learned."""

    def _cur(self, with_frame=True):
        items = [
            {"id": "er_opid", "kind": "phrase", "target": "Er opið?", "meaning": "Is it open?"},
            {"id": "gott", "kind": "vocab", "target": "gott", "meaning": "good", "tags": ["adj"]},
            {"id": "kalt", "kind": "vocab", "target": "kalt", "meaning": "cold", "tags": ["adj"]},
            {"id": "opid", "kind": "vocab", "target": "opið", "meaning": "open", "tags": ["adj"]},
        ]
        if with_frame:
            items.append({"id": "thetta_er", "kind": "construction", "target": "Þetta er {adj}.", "meaning": "This is {adj}.",
                          "slots": {"adj": "adj"}, "example": {"adj": "gott"}})
        return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})

    def _learner(self, whole_met=True, frame=True):
        learner = LearnerState("is", "en", "A1")
        known = dict(stage="meaning", durable_successes=2, successes=8, interval_days=7, due=(TODAY + timedelta(days=5)).isoformat(),
                     last_practiced=(TODAY - timedelta(days=2)).isoformat())
        for i in ["gott", "kalt"] + (["thetta_er"] if frame else []):
            learner.items[i] = ItemState(**known)
        if whole_met:
            learner.items["er_opid"] = ItemState(**known)
        return learner

    def _plan(self, cur, learner, **cfg):
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"),
                       PlanConfig(minutes=10, new_items=1, max_new_items=1, priority=["opid"], seed=3, **cfg), today=TODAY).build()

    def test_a_part_of_a_met_phrase_is_heard_in_a_sentence_not_introduced(self):
        cur = self._cur()
        sc = self._plan(cur, self._learner())
        self.assertEqual(sc.meta["embedded_items"], ["opid"])
        self.assertIn("opid", sc.meta["new_items"])
        self.assertEqual([e.kind for e in sc.exercises if "opid" in e.item_ids and e.kind in ("intro", "embed")], ["embed"])
        text = sc.transcript()
        self.assertIn("Þetta er opið.", text)
        block = text.split("embed:")[1].split("##")[0]
        self.assertNotIn("Something new", block)
        self.assertIn("You know this:", block)
        self.assertIn("Er opið?", block, "it names the phrase it is taken out of")
        self.assertNotIn("opid", sc.meta["exposures"], "nothing is recorded for it: the review decides")

    def test_without_a_phrase_that_holds_it_or_a_pattern_to_put_it_in_it_is_introduced(self):
        for kw in (dict(whole_met=False), dict(frame=False)):
            cur = self._cur(with_frame=kw.get("frame", True))
            sc = self._plan(cur, self._learner(**kw))
            self.assertEqual(sc.meta["embedded_items"], [], kw)
            self.assertIn("opid", sc.meta["exposures"], kw)

    def test_no_item_is_taught_twice_in_a_lesson_over_a_simulated_course(self):
        """#217 as a property: over a real-curriculum course, ``new_items`` never repeats an id, an item is not both embedded and
        introduced, and nothing is introduced twice."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for _ in range(30):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=8, seed=3), today=day).build()
            new = sc.meta["new_items"]
            self.assertEqual(len(new), len(set(new)), (sc.lesson_number, new))
            intros = [e.item_ids[0] for e in sc.exercises if e.kind == "intro"]
            self.assertEqual(len(intros), len(set(intros)), (sc.lesson_number, intros))
            self.assertFalse(set(intros) & set(sc.meta["embedded_items"]), (sc.lesson_number, "embedded and introduced"))
            self.assertEqual(sc.meta["intro_skipped"], [], (sc.lesson_number, "the guard fired: a selection chose an item already taught"))
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)

    def test_an_item_queued_twice_is_taught_once(self):
        """#217 (lesson 19, «miða»): an item embedded in a sentence and then reaching ``do_intro`` again from a queue was introduced
        as new nine minutes later, and ``new_items`` listed it twice (the bot's feedback form broke on the duplicate)."""
        from unittest import mock

        cur = self._cur()
        opid = cur.by_id["opid"]
        calls = []

        def select_new(self, count, exclude=None, cheap=False):
            calls.append(1)
            return [opid, opid] if len(calls) == 1 else []  # the first selection queues it twice; later ones honour ``exclude``

        with mock.patch.object(Planner, "select_new", select_new):
            sc = Planner(cur, self._learner(), Prompts.load("en"), Timing(level="A1"),
                         PlanConfig(minutes=10, new_items=2, max_new_items=2, seed=3), today=TODAY).build()  # fmt: skip
        self.assertEqual(sc.meta["new_items"], ["opid"], "once")
        self.assertEqual(sc.meta["embedded_items"], ["opid"])
        self.assertEqual(sc.meta["intro_skipped"], ["opid"], "the guard reports that it fired")
        self.assertEqual([e.kind for e in sc.exercises if "opid" in e.item_ids and e.kind in ("intro", "embed")], ["embed"],
                         "heard inside the sentence, not introduced again")  # fmt: skip

    def test_the_review_asks_the_sentence(self):
        cur = self._cur()
        sc = self._plan(cur, self._learner())
        qs = [q for q in sc.review_questions() if q["items"] == ["opid"]]
        self.assertEqual([(q["prompt"], q["answer"]) for q in qs], [("This is open.", "Þetta er opið.")])

    def test_said_back_it_counts_as_its_first_recall(self):
        cur = self._cur()
        learner = self._learner()
        sc = self._plan(cur, learner)
        apply_to_learner(sc, learner, TODAY)
        self.assertEqual(learner.embedded, {"opid": learner.lessons_completed})
        self.assertFalse(learner.has_met("opid"))
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, new_items=1, priority=["opid"]), today=TODAY)
        self.assertNotIn("opid", [i.id for i in planner.select_new(3)], "pending: not introduced meanwhile")
        learner.report([], [], TODAY + timedelta(days=1), recalled=["opid"])
        self.assertTrue(learner.has_met("opid"))
        self.assertEqual(learner.embedded, {})
        st = learner.items["opid"]
        self.assertEqual((st.durable_successes, st.interval_days), (1, 3))
        self.assertFalse(learner.knows("opid"), "§9: known after two recalls on or after a due date, like any item")

    def test_not_said_back_it_is_introduced_the_usual_way_next_time(self):
        cur = self._cur()
        learner = self._learner()
        apply_to_learner(self._plan(cur, learner), learner, TODAY)
        learner.report(["opid"], [], TODAY + timedelta(days=1))
        self.assertFalse(learner.has_met("opid"))
        self.assertEqual(learner.embed_failed, ["opid"])
        again = self._plan(cur, learner)
        self.assertEqual(again.meta["embedded_items"], [])
        self.assertIn("opid", again.meta["exposures"])

    def test_the_state_round_trips(self):
        learner = self._learner()
        learner.embedded["opid"] = 4
        learner.embed_failed.append("mida")
        import tempfile, os

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "l.json")
            learner.save(path)
            back = LearnerState.load(path)
        self.assertEqual((back.embedded, back.embed_failed), ({"opid": 4}, ["mida"]))


class ScaffoldFadeTests(unittest.TestCase):
    """G12 (lesson 13 feedback): the instructor kept narrating in English what the learner
    already knows. When the partner's line is known it is the cue, in Icelandic; and a
    situation never re-states what the learner has just said."""

    def _cur(self):
        return curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "q", "kind": "phrase", "target": "Hvaðan ert þú?", "meaning": "Where are you from?"},
                {"id": "a", "kind": "phrase", "target": "Ég er frá Japan.", "meaning": "I'm from Japan.",
                 "prompt_by": "q", "situation": "Someone asks where you're from. Tell them you're from Japan."},
            ],
        })

    def _recall(self, learner_items=(), introduced=()):
        cur = self._cur()
        learner = LearnerState("is", "en", "A1")
        for i in learner_items:
            learner.items[i] = ItemState(stage="situation", durable_successes=2, successes=6, interval_days=7, due=TODAY.isoformat())
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10), today=TODAY)
        planner.builder.in_lesson.update(introduced)
        sc = Script(1, "t", "is", "en")
        ex = planner.builder.recall(sc, cur.by_id["a"], "situation")
        return sc, ex

    def test_a_known_partner_line_is_the_cue_with_no_english(self):
        sc, ex = self._recall(learner_items=["q"])
        said = [(s.type, s.speaker, s.text) for s in sc.segments if s.exercise == ex.index and s.type in ("narrate", "speak", "answer")]
        self.assertIn(("speak", "native_b", "Hvaðan ert þú?"), said)
        self.assertEqual([t for t in said if t[0] == "narrate"], [("narrate", "instructor", "Reply.")])
        self.assertEqual(said[-1], ("answer", "native_a", "Ég er frá Japan."))
        self.assertNotIn("Someone asks", sc.transcript())

    def test_a_line_introduced_earlier_in_the_lesson_comes_with_its_meaning_once(self):
        """Not known yet (H2): the line is the cue, then what it means, but no authored scene."""
        sc, _ = self._recall(introduced=["q"])
        text = sc.transcript()
        self.assertNotIn("Someone asks", text)
        self.assertIn("Hvaðan ert þú?", text)
        self.assertIn("Where are you from?", text)
        more = Script(1, "t", "is", "en")
        planner = Planner(self._cur(), LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10), today=TODAY)
        planner.builder.in_lesson.add("q")
        for _ in range(4):
            planner.builder.recall(more, planner.cur.by_id["a"], "situation")
        self.assertEqual(more.transcript().count("Where are you from?"), 2, "glossed on the first two hearings only")

    def test_an_open_prompt_line_is_not_a_bare_cue(self):
        """#149: a line the learner reported not being able to say comes with its meaning."""
        cur = self._cur()
        learner = LearnerState("is", "en", "A1")
        learner.items["q"] = ItemState(stage="situation", durable_successes=2, successes=6, failures=1, interval_days=1,
                                      due=TODAY.isoformat(), last_outcome="not_recalled")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10), today=TODAY)
        sc = Script(1, "t", "is", "en")
        planner.builder.recall(sc, cur.by_id["a"], "situation")
        self.assertIn("Where are you from?", sc.transcript())

    def test_an_unknown_partner_line_keeps_the_english_situation(self):
        sc, _ = self._recall()
        self.assertIn("Someone asks where you're from", sc.transcript())
        self.assertNotIn("Hvaðan ert þú?", sc.transcript())

    def test_reply_frames_a_cue_unless_the_exercise_before_was_one(self):
        cur = self._cur()
        learner = LearnerState("is", "en", "A1")
        learner.items["q"] = ItemState(stage="situation", durable_successes=2, successes=6, interval_days=7, due=TODAY.isoformat())
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10), today=TODAY)
        sc = Script(1, "t", "is", "en")
        planner.builder.recall(sc, cur.by_id["a"], "situation")
        planner.builder.recall(sc, cur.by_id["a"], "situation")  # straight after a cue: no frame
        self.assertEqual(sc.transcript().count("Reply."), 1)
        planner.builder.recall(sc, cur.by_id["q"], "meaning")  # an English-cued recall in between
        planner.builder.recall(sc, cur.by_id["a"], "situation")
        self.assertEqual(sc.transcript().count("Reply."), 2)

    def test_the_review_question_for_a_partner_line_cue_is_the_line(self):
        sc, ex = self._recall(learner_items=["q"])
        ex.item_ids = ["a"]
        questions = sc.review_questions()
        self.assertEqual([(q["prompt"], q["answer"]) for q in questions], [("Hvaðan ert þú?", "Ég er frá Japan.")])

    def test_prompt_by_must_name_another_phrase(self):
        base = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}}
        for bad in ("a", "nothing"):
            raw = {**base, "items": [{"id": "a", "kind": "phrase", "target": "Já.", "meaning": "Yes.", "prompt_by": bad}]}
            with self.assertRaises(CurriculumError):
                curriculum_from_dict(raw)

    def test_no_authored_situation_restates_what_the_learner_said(self):
        """«You've said you're from Japan. Ask where she is from.» (lesson 13): the learner
        said it a moment ago. The four questions that carried such a recap are now the task
        alone, in both languages."""
        import re

        recap = re.compile(r"^You(?:'ve| have) (?:said you|told \w+ you|answered|introduced yourself)\b")
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for it in cur.items:
            for text in ([it.situation] if it.situation else []) + list(it.situations):
                self.assertIsNone(recap.match(text), (it.id, text))
        ja = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")
        for item_id in ("hvad_heitir_thu", "hvadan_ert_thu", "hvar_byrd_thu", "hvad_gerir_thu"):
            self.assertEqual(ja.by_id[item_id].situation.count("。"), 1, item_id)


class ListeningDialogueTests(unittest.TestCase):
    """#149 step 3 (lesson 13: 23.6 of 30 minutes, the last 5 repeating today's items): with
    nothing else left, a dialogue lacking one or two required items is played as listening."""

    def _cur(self, missing_count=1):
        known = [{"id": f"k{i}", "kind": "phrase", "target": f"Þekkt {i}.", "meaning": f"Known {i}."} for i in range(8)]
        unknown = [{"id": f"u{i}", "kind": "phrase", "target": f"Nýtt {i}.", "meaning": f"New {i}."} for i in range(3)]
        turns = [
            {"cue": "Say known 0.", "expect": "k0", "partner": "Gott.", "partner_meaning": "Good."},
            {"cue": "Say new 0.", "expect": "u0", "partner": "Já.", "partner_meaning": "Yes."},
            {"cue": "Say known 1.", "expect": "k1"},
        ]
        requires = ["k0", "k1"] + [f"u{i}" for i in range(missing_count)]
        return curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": known + unknown,
            "dialogues": [{"id": "d1", "setting": "A test setting.", "requires": requires, "turns": turns}],
        })

    def _learner(self, cur, lessons=()):
        learner = LearnerState("is", "en", "A1")
        for i in range(8):
            learner.items[f"k{i}"] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7,
                                              due=(TODAY + timedelta(days=5)).isoformat(), last_practiced=(TODAY - timedelta(days=2)).isoformat())
        learner.lessons = list(lessons)
        learner.lessons_completed = max((l["number"] for l in lessons), default=0)
        return learner

    def _planner(self, cur, learner, **cfg):
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, new_items=0, max_new_items=0, **cfg), today=TODAY)

    def test_one_or_two_missing_items_make_a_listening_dialogue(self):
        cur = self._cur(missing_count=1)
        found = self._planner(cur, self._learner(cur)).listening_dialogue()
        self.assertEqual((found[0].id, found[1]), ("d1", {"u0"}))
        cur3 = self._cur(missing_count=3)
        self.assertIsNone(self._planner(cur3, self._learner(cur3)).listening_dialogue())
        done = self._cur(missing_count=1)
        learner = self._learner(done)
        learner.items["u0"] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, due=TODAY.isoformat())
        self.assertIsNone(self._planner(done, learner).listening_dialogue(), "nothing missing: it is an ordinary dialogue")

    def test_the_missing_turn_is_heard_not_asked_for(self):
        cur = self._cur()
        planner = self._planner(cur, self._learner(cur))
        sc = Script(1, "t", "is", "en")
        planner._play_listening(sc, cur.dialogues[0], {"u0"})
        text = sc.transcript()
        self.assertIn("You don't need to remember them", text)
        self.assertIn("Here you would say:", text)
        self.assertIn("Nýtt 0.", text)
        self.assertIn("New 0.", text)
        pauses = [s for s in sc.segments if s.type == "pause" and s.role == "answer"]
        self.assertEqual(len(pauses), 2, "the two known turns are asked; the unknown one is not")

    def test_a_heard_construction_turn_says_its_filled_meaning(self):
        """The real dialogue 'solubas' lacks a construction turn: its meaning was narrated with
        the slot still in it («It costs {count} thousand krónur.»)."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        dlg = cur.dialogues_by_id["solubas"] if hasattr(cur, "dialogues_by_id") else next(d for d in cur.dialogues if d.id == "solubas")
        learner = LearnerState("is", "en", "A1")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=TODAY)
        sc = Script(1, "t", "is", "en")
        planner._play_listening(sc, dlg, {i for i in dlg.required_items})
        self.assertNotIn("{", sc.transcript())

    def test_heard_items_are_not_recorded_or_asked(self):
        cur = self._cur()
        learner = self._learner(cur)
        planner = self._planner(cur, learner)
        sc = Script(1, "t", "is", "en")
        planner._play_listening(sc, cur.dialogues[0], {"u0"})
        sc.meta = {"exposures": planner.exposures, "ladders": {}, "dialogues_listened": ["d1"], "new_items": []}
        apply_to_learner(sc, learner, TODAY)
        self.assertNotIn("u0", learner.items)
        self.assertIn("k0", learner.items)
        self.assertEqual(learner.lessons[-1]["dialogues_listened"], ["d1"])
        self.assertNotIn("u0", {i for q in sc.review_questions() for i in q["items"]})

    def test_a_listened_dialogue_rests(self):
        cur = self._cur()
        recent = [{"number": 4, "dialogues_listened": ["d1"]}]
        self.assertIsNone(self._planner(cur, self._learner(cur, recent)).listening_dialogue())
        old = [{"number": 4, "dialogues_listened": ["d1"]}, {"number": 11}]
        self.assertIsNotNone(self._planner(cur, self._learner(cur, old)).listening_dialogue())

    def test_a_lesson_with_nothing_else_left_ends_on_listening_not_short(self):
        cur = self._cur()
        learner = self._learner(cur)
        sc = self._planner(cur, learner).build()
        self.assertEqual(sc.meta["dialogues_listened"], ["d1"])


class SemanticSetTests(unittest.TestCase):
    """#149 step 2 (H5): at most ``max_set_items`` new items of one semantic set a lesson."""

    def setUp(self):
        self.cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.nature = [i for i in self.cur.items if "nature_nom" in i.tags and i.kind != "construction"]
        self.assertGreaterEqual(len(self.nature), 5)
        first = min(i.order for i in self.nature)
        self.learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < first and "nature_nom" not in i.tags:
                self.learner.items[i.id] = ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning",
                                                     recalled=2, last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=1)).isoformat())

    def _planner(self, **cfg):
        return Planner(self.cur, self.learner, Prompts.load("en"), Timing(level="A1"),
                       PlanConfig(minutes=30, new_items=8, seed=1, priority=[i.id for i in self.nature], **cfg), today=TODAY)

    def _of_set(self, ids):
        return [i for i in ids if "nature_nom" in self.cur.by_id[i].tags]

    def test_a_lesson_takes_at_most_three_of_a_set_and_the_pool_goes_on(self):
        ids = [i.id for i in self._planner().select_new(8)]
        self.assertEqual(len(self._of_set(ids)), 3)
        self.assertGreaterEqual(len(ids), 8, "the pace is unchanged: other items fill the places")

    def test_the_limit_counts_the_lessons_earlier_arcs(self):
        earlier = {i.id for i in self.nature[:2]}
        ids = [i.id for i in self._planner().select_new(8, exclude=earlier)]
        self.assertEqual(len(self._of_set(ids)), 1, "two already in the lesson: one more")

    def test_the_items_a_theme_level_wants_are_a_scene_and_exempt(self):
        from audiolesson.themes import Level, Theme, Turn

        scene = ["sjor", "nordurljos", "midnætursol"]  # no slot tag: only the set limit applies to them
        level = Level(goal="g", partner_speaker="native_c", turns=[Turn(who="you", say="Takk.", cue="Thank him.", items=scene)])
        theme = Theme(id="nature_test", scenario="A1", title="Nature", levels=[level])
        with_theme = self._planner(themes=[theme], theme_scenarios=["A1"], max_set_items=2)
        self.assertEqual(sorted(i for i in with_theme.theme_wants() if i in scene), sorted(scene))
        ids = [i.id for i in with_theme.select_new(8)]
        self.assertTrue(all(i in ids for i in scene), "a level that needs three of a set gets all three, over a limit of two")
        # the same items without a theme: the limit holds
        without = [i.id for i in self._planner(max_set_items=2).select_new(8)]
        self.assertEqual(len(self._of_set(without)), 2)

    def test_the_adjectives_are_one_set_whatever_their_gender(self):
        """The owner, after #204: adjectives arrive as a block too («vont», «dýrt», «ódýrt», «fallegt», «ljótt», «stórt» stand
        together in the course), and «góður» / «góð» / «gott» are one set across their gender tags."""
        adjectives = [i for i in self.cur.items if {"adj_neut", "adj_masc", "adj_fem"} & set(i.tags) and i.kind != "construction"]
        first = min(i.order for i in adjectives)
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < first and i not in adjectives:
                learner.items[i.id] = ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning",
                                                recalled=2, last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=1)).isoformat())
        def pick(sets):
            planner = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"),
                              PlanConfig(minutes=30, new_items=8, seed=1, priority=[i.id for i in adjectives], semantic_sets=sets), today=TODAY)
            return [i.id for i in planner.select_new(8)]

        adj_ids = {a.id for a in adjectives}
        ids = pick(PlanConfig().semantic_sets)
        # the fillers a chosen construction's slot pulls in come with their pattern, not as a set (#204)
        slot_tags = {t for i in ids if self.cur.by_id[i].kind == "construction" for t in self.cur.by_id[i].slots.values()}
        alone = [i for i in ids if i in adj_ids and not slot_tags & set(self.cur.by_id[i].tags)]
        self.assertLessEqual(len(alone), 3, ids)
        self.assertGreaterEqual(len(ids), 8, "the pace is unchanged: other items fill the places")
        without = pick(tuple(s for s in PlanConfig().semantic_sets if "adj" not in s))
        self.assertGreater(sum(1 for i in without if i in adj_ids), sum(1 for i in ids if i in adj_ids), "without the set, more come together")

    def test_the_limit_is_a_setting(self):
        """On the colours: the nature words come with «Þetta er {thing}.» since #215 (their frame is not a set), and the colours are the set a lesson would
        otherwise take together."""
        colours = [i for i in self.cur.items if "colour" in i.tags and i.kind != "construction"]
        first = min(i.order for i in colours)
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < first and "colour" not in i.tags:
                learner.items[i.id] = ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning",
                                                recalled=2, last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=1)).isoformat())

        def pick(**cfg):
            planner = Planner(self.cur, learner, Prompts.load("en"), Timing(level="A1"),
                              PlanConfig(minutes=30, new_items=8, seed=1, priority=[i.id for i in colours], **cfg), today=TODAY)
            return [i.id for i in planner.select_new(8) if "colour" in self.cur.by_id[i.id].tags]

        self.assertEqual(len(pick(max_set_items=5)), 5)
        self.assertEqual(len(pick()), 3)
        self.assertGreater(len(pick(semantic_sets=())), 3)


class EdgeRetryTests(unittest.TestCase):
    """#77: one clip that edge-tts answers with «no audio» (or a dropped connection) is retried after a wait instead of failing the
    whole lesson; any other error fails at once, and an error that keeps coming fails after the retries, as before."""

    @staticmethod
    def _provider():
        from audiolesson.render.tts import EdgeProvider

        return EdgeProvider()

    def _run(self, errors, final="ok"):
        import contextlib
        import io
        from unittest import mock

        calls, waits = [], []
        queue = list(errors)

        def attempt():
            calls.append(1)
            if queue:
                raise queue.pop(0)
            return final

        err = io.StringIO()
        with mock.patch("audiolesson.render.tts.time.sleep", side_effect=waits.append), contextlib.redirect_stderr(err):
            try:
                result = self._provider()._retrying(attempt)
            except Exception as exc:
                result = exc
        return result, len(calls), waits, err.getvalue()

    def test_a_clip_that_fails_once_is_retried_and_the_lesson_goes_on(self):
        class EdgeTTSException(Exception):
            pass

        class NoAudioReceived(EdgeTTSException):
            pass

        result, calls, waits, err = self._run([NoAudioReceived("No audio was received.")])
        self.assertEqual((result, calls, waits), ("ok", 2, [5.0]))
        self.assertIn("retrying in 5 s (1/3)", err)

    def test_the_whole_edge_tts_family_and_a_dropped_connection_are_retried(self):
        """Decided by family: WebSocketError (a socket error frame) and UnexpectedResponse (a cut-off frame) are as transient
        as NoAudioReceived, without naming each (#77 review)."""

        class EdgeTTSException(Exception):
            pass

        class WebSocketError(EdgeTTSException):
            pass

        class UnexpectedResponse(EdgeTTSException):
            pass

        for errors in ([WebSocketError("socket")], [UnexpectedResponse("short frame")], [ConnectionResetError("reset"), TimeoutError()]):
            result, calls, waits, _ = self._run(errors)
            self.assertEqual((result, calls), ("ok", len(errors) + 1), errors)
            self.assertEqual(waits, [5.0, 20.0][: len(errors)])

    def test_an_error_that_keeps_coming_fails_after_the_retries_with_its_own_error(self):
        class EdgeTTSException(Exception):
            pass

        class NoAudioReceived(EdgeTTSException):
            pass

        errors = [NoAudioReceived(f"try {k}") for k in range(4)]
        result, calls, waits, _ = self._run(errors)
        self.assertIs(result, errors[-1])
        self.assertEqual((calls, waits), (4, [5.0, 20.0, 60.0]))

    def test_a_malformed_argument_fails_at_once(self):
        for exc in (ValueError("Invalid voice 'x'"), TypeError("bad rate"), KeyError("k")):
            result, calls, waits, _ = self._run([exc])
            self.assertIs(result, exc)
            self.assertEqual((calls, waits), (1, []), exc)


class SoonerRequestTests(unittest.TestCase):
    """#222: the feedback form's «not enough / don't remember» is a request about the schedule, not an outcome. ``report(sooner=…)``
    moves ``due`` to at most half the interval and changes nothing else; ``report(hesitated=…)`` stays the next-day outcome."""

    @staticmethod
    def _learner(interval=6.0, due_in=6):
        learner = LearnerState("is", "en", "A1")
        learner.items["a"] = ItemState(stage="meaning", successes=3, durable_successes=2, recalled=2, ease=2.3, interval_days=interval,
                                       due=(TODAY + timedelta(days=due_in)).isoformat(), last_practiced=TODAY.isoformat(), last_outcome="recalled",
                                       history=[{"lesson": 1, "stages": ["meaning"], "ok": True, "outcome": "recalled"}])
        learner.lessons = [{"number": 1, "new_items": ["a"]}]
        learner.lessons_completed = 1
        return learner

    def test_the_due_date_moves_to_half_the_interval_and_nothing_else_changes(self):
        learner = self._learner()
        before = copy.deepcopy(learner.items["a"])
        changed = learner.report([], [], TODAY, 1, sooner=["a"])
        st = learner.items["a"]
        self.assertEqual(st.due, (TODAY + timedelta(days=3)).isoformat())
        self.assertEqual(changed["sooner"], ["a"])
        before.due = st.due
        self.assertEqual(st, before, "no hesitation, failure, recall, ease, interval or history entry")
        self.assertEqual(st.interval_days, 6.0, "the next success grows it from where it was")

    def test_it_does_not_mark_the_lesson_reported_so_the_pace_still_waits_for_the_review(self):
        learner = self._learner()
        self.assertIsNone(learner.recall_rate())
        learner.report([], [], TODAY, 1, sooner=["a"])
        self.assertEqual(learner.reported, [])
        self.assertIsNone(learner.recall_rate())
        learner.report([], [], TODAY, sooner=["a"])  # no lesson given: the same
        self.assertEqual(learner.reported, [])

    def test_a_due_date_already_sooner_is_not_moved_later(self):
        learner = self._learner(interval=6.0, due_in=1)
        learner.report([], [], TODAY, sooner=["a"])
        self.assertEqual(learner.items["a"].due, (TODAY + timedelta(days=1)).isoformat())

    def test_an_embedded_or_tried_item_is_left_to_its_review_and_an_unknown_one_is_listed(self):
        learner = self._learner()
        learner.embedded["e"] = 1
        learner.tried["t"] = 1
        changed = learner.report([], [], TODAY, sooner=["e", "t", "zzz"])
        self.assertEqual((changed["sooner_skipped"], changed["unknown"]), (["e", "t"], ["zzz"]))
        self.assertEqual((learner.embedded, learner.embed_failed), ({"e": 1}, []), "not consumed as failed")
        self.assertIn("t", learner.tried)

    def test_hesitated_stays_a_next_day_outcome(self):
        learner = self._learner()
        learner.report([], [], TODAY, 1, hesitated=["a"])
        self.assertEqual(learner.reported, [1])
        self.assertEqual(learner.items["a"].hesitated, 1)

    def test_the_cli_takes_sooner_alone(self):
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "learner.json"
            self._learner().save(path)
            self.assertEqual(main(["report", "-l", str(path), "--sooner", "a", "--date", TODAY.isoformat()]), 0)
            loaded = LearnerState.load(path)
            self.assertEqual(loaded.items["a"].due, (TODAY + timedelta(days=3)).isoformat())
            self.assertEqual(loaded.reported, [])


class HardSentenceCapTests(unittest.TestCase):
    """#192 (owner: «never ten identical»): a fixed phrase is said at most ``max_sentence_hard`` times in a lesson, while the
    caps are on. Its practice is dropped when no other sentence holds it; a new item keeps one place for its closing recall."""

    @staticmethod
    def _plan(hard):
        from audiolesson.exercises import _norm_utterance

        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": [
            {"id": "ph", "kind": "phrase", "target": "Þetta er allt.", "meaning": "That's all.", "situation": "You're done at the till. Say that's all."},
            {"id": "ph2", "kind": "phrase", "target": "Takk fyrir.", "meaning": "Thanks.", "situation": "Thank the clerk."},
        ]})
        planner = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"),
                          PlanConfig(minutes=10, new_items=2, max_sentence_hard=hard, seed=1), today=TODAY)
        sc = planner.build()
        return planner, sc, {k: v for k, v in planner.builder.said.items()}

    def test_a_fixed_phrase_is_said_no_more_than_the_cap(self):
        _, sc, said = self._plan(6)
        self.assertLessEqual(max(said.values()), 6, said)
        self.assertFalse(sc.meta["bare_cap_lapsed"])
        for i in sc.meta["new_items"]:  # each new item still gets its closing recall
            closing = next(e.index for e in sc.exercises if e.kind == "closing" and e.label == "final review")
            self.assertTrue(any(e.index > closing and i in e.item_ids for e in sc.exercises), i)

    def test_without_the_cap_the_same_lesson_says_a_line_more_often(self):
        _, _, said = self._plan(0)
        self.assertGreater(max(said.values()), 6, said)


    def test_the_time_the_cap_frees_is_not_given_to_bare_words_past_their_own_cap(self):
        """#206 review: the two caps conflict whenever both bind. A recall the hard cap keeps out is not made up for by
        saying short words alone past the bare cap: the lesson ends a little short instead. A hard cap of 5 binds in
        most lessons of the real course, so the bare cap would lapse without it."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for n in range(1, 15):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_items=6, max_sentence_hard=5), today=day).build()
            if n >= 6:  # the first lessons have little to practise and lapse the bare cap whatever the hard cap is
                # the rule, not one path's outcome: the cap lapses only when the lesson would otherwise end more than
                # hard_cap_short_max short (a few seconds of beats, #241, moved lesson 9 of this course just past it)
                if sc.meta["bare_cap_lapsed"]:
                    self.assertGreaterEqual(sc.meta["bare_cap_lapsed_short_s"], PlanConfig().hard_cap_short_max, sc.lesson_number)
                self.assertGreaterEqual(sc.total_duration, 30 * 60 - 240, sc.lesson_number)
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)


class SpareTimeTests(unittest.TestCase):
    """#238 (Now 1, lesson 20): the time after the target serves the scene and the ear; what the learner's own review asked this morning
    is not asked again in the audio; a generated sentence in spare time is a parallel of a target expression of the scene."""

    @staticmethod
    def _cfg():
        from audiolesson.cando import load_cando
        from audiolesson.themes import load_themes, scenario_order
        path = ROOT / "curricula" / "is-en"
        cur = load_curriculum(path)
        scenarios = load_cando(path, cur)
        themes = load_themes(path, cur, scenarios)
        return cur, dict(themes=themes, theme_scenarios=scenario_order(scenarios, ()))

    @classmethod
    def _course_to(cls, n: int):
        cur, extra = cls._cfg()
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for k in range(1, n + 1):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0, **extra), today=day).build()
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        return cur, learner, day, extra

    def test_a_report_marks_the_day_the_review_asked_an_item(self):
        learner = LearnerState("is", "en", "A1")
        learner.items["a"] = ItemState(stage="meaning", due=TODAY.isoformat())
        learner.items["b"] = ItemState(stage="meaning", due=TODAY.isoformat())
        learner.items["c"] = ItemState(stage="meaning", due=TODAY.isoformat())
        learner.report(["a"], [], TODAY, hesitated=["b"], recalled=[])
        self.assertEqual((learner.items["a"].last_reviewed, learner.items["b"].last_reviewed, learner.items["c"].last_reviewed), (TODAY.isoformat(), TODAY.isoformat(), ""))
        learner.report([], [], TODAY + timedelta(days=1), sooner=["c"])
        self.assertEqual(learner.items["c"].last_reviewed, "", "the feedback form's «sooner» is not a review")

    def test_what_the_review_asked_this_morning_is_not_reviewed_or_used_as_filler_in_the_audio(self):
        cur, learner, day, extra = self._course_to(9)
        due = [i for i, st in learner.items.items() if st.due and st.due <= day.isoformat()]
        self.assertGreater(len(due), 5)
        base = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0, **extra), today=day)
        asked = set(base.build().meta["reviewed_items"])
        reviewed = sorted(asked)[:6]
        self.assertTrue(reviewed)
        for i in reviewed:
            learner.items[i].last_reviewed = day.isoformat()
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0, **extra), today=day).build()
        open_ids = set(learner.open_items())
        again = (set(sc.meta["reviewed_items"]) | set(sc.meta["reviewed_early"])) & set(reviewed) - open_ids
        self.assertFalse(again, again)
        self.assertFalse(set(sc.meta["asked_after_review"]) - open_ids - {x for e in sc.exercises if e.kind == "note" for x in e.item_ids}, sc.meta["asked_after_review"])

    def test_the_scene_names_the_patterns_spare_time_may_make_parallels_of(self):
        cur, learner, day, extra = self._course_to(9)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0, **extra), today=day)
        theme = next(t for t in extra["themes"] if t.id == "cafe")
        pick = (theme, 0, set())
        scene = planner.scene_constructions(pick)
        self.assertEqual(scene, {"eg_aetla_ad_fa"}, "the learner's turns use one pattern and two phrases")
        self.assertIsNone(planner.scene_constructions(None), "no theme (a first lesson): nothing is restricted")

    def test_the_lesson_reports_when_the_target_was_reached_and_how_much_after_it_served_neither(self):
        cur, learner, day, extra = self._course_to(10)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0, **extra), today=day).build()
        m = sc.meta
        self.assertGreater(m["target_reached_at"], 0)
        self.assertLess(m["target_reached_at"], sc.total_duration)
        self.assertGreaterEqual(m["spare_unserved_s"], 0)
        self.assertLess(m["spare_unserved_s"], sc.total_duration - m["target_reached_at"])
        self.assertIsInstance(m["asked_after_review"], list)

    def test_the_last_resort_is_a_parallel_outside_the_scene_only_when_nothing_else_is_left(self):
        """Spare time tries the scene's parallels first; a pattern outside the scene comes only at the very end (rather than bare words again)."""
        cur, learner, day, extra = self._course_to(12)
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0, **extra), today=day).build()
        self.assertGreaterEqual(sc.total_duration, 24 * 60)
        self.assertFalse(sc.meta["bare_cap_lapsed"])

    def test_a_run_of_generated_sentences_is_cut_at_three_while_there_is_something_to_hear(self):
        """Review of #247: lesson 20 had 20 generated sentences in a row, lesson 22 had 17. With a theme level to hear again, a listening
        dialogue or one of today's lines left, a fourth generated sentence does not follow three."""
        cur, extra = self._cfg()
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        checked = 0
        for n in range(1, 13):
            cfg = PlanConfig(minutes=30, seed=1, new_target=8.0, **extra)
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=day).build()
            if len(sc.meta["heard_themes"]) < cfg.heard_theme_plays:  # the ear still had something left
                self.assertLessEqual(sc.meta["longest_generated_run"], cfg.generated_run_max, sc.lesson_number)
                checked += 1
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertGreaterEqual(checked, 6)

    def test_the_not_due_fillers_start_with_the_scene(self):
        cur, learner, day, extra = self._course_to(9)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0, **extra), today=day)
        plain = [i.id for i in planner.select_early_reviews(set(), rested_only=False)]
        self.assertGreater(len(plain), 5)
        last = plain[-1]
        first = [i.id for i in planner.select_early_reviews(set(), rested_only=False, prefer=frozenset({last}))]
        self.assertEqual(first[0], last)
        self.assertEqual(sorted(first), sorted(plain))


class PartsLiveInsideTheirWholeTests(unittest.TestCase):
    """#239 (lesson 20 and 21): a part is introduced inside the target expression that holds it, the review asks each expression once and a part only
    through its whole, and a pattern whose example is known is not announced as new."""

    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        cls.en = Prompts.load("en")

    def _builder(self, met=()):
        from audiolesson.exercises import Builder
        learner = LearnerState("is", "en", "A1")
        for i in met:
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3)
        return Builder(self.cur, self.en, Timing(level="A1"), learner)

    # -- the lesson: a part inside its whole

    def test_hjalpina_is_introduced_inside_takk_fyrir_hjalpina(self):
        """Lesson 20: «hjálpina» 'for help' was introduced and drilled as a word. The gloss only makes sense inside «Takk fyrir {thing}.»"""
        b = self._builder(met=["takk"])
        home = b.whole_home(self.cur.by_id["hjalpina"])
        self.assertEqual((home[0].id, {k: v.id for k, v in home[1].items()}), ("takk_fyrir", {"thing": "hjalpina"}))
        sc = Script(1, "t", "is", "en")
        ex = b.intro(sc, self.cur.by_id["hjalpina"])
        self.assertEqual((ex.kind, ex.item_ids, ex.label), ("intro", ["hjalpina"], "new: Takk fyrir hjálpina. (hjálpina)"))
        speech = [g.text for g in sc.segments if g.type in ("speak", "answer")]
        self.assertEqual(speech[0], "Takk fyrir hjálpina.", "the whole comes first")
        self.assertLess(speech.index("Takk fyrir hjálpina."), speech.index("hjálpina"), "the part is said alone afterwards, never first")
        self.assertIn("A new expression. Thanks for the help.", sc.transcript())
        self.assertEqual(speech[-1], "Takk fyrir hjálpina.", "the first retrieval asks the whole")
        # the next day's question asks the sentence
        self.assertEqual([(q["items"], q["answer"]) for q in sc.review_questions()], [(["hjalpina"], "Takk fyrir hjálpina.")])

    def test_a_part_without_an_authored_home_or_with_a_strange_frame_is_introduced_as_before(self):
        b = self._builder()
        self.assertIsNone(b.whole_home(self.cur.by_id["kaffihusid"]), "no construction names it")
        thusund = self._builder(met=[])
        self.assertIsNone(thusund.whole_home(self.cur.by_id["tvo"]), "«Það kostar … þúsund krónur.» has two words they have never met")
        self.assertIsNone(self._builder().whole_home(self.cur.by_id["takk_fyrir"]), "only a part has a whole")
        b = self._builder(met=["takk"])
        b.heard.add(_norm_utterance("Takk fyrir hjálpina."))
        self.assertIsNone(b.whole_home(self.cur.by_id["hjalpina"]), "the sentence was already heard whole")

    def test_a_pattern_whose_example_is_known_is_not_announced_as_new(self):
        """Lesson 20: «Eigðu {adj} {time}.» was introduced as "new pattern" with «Eigðu góðan dag.», which the learner already knew."""
        b = self._builder(met=["eigdu_godan_dag", "godan_daginn", "goda_nott", "gott_kvold", "dag_acc"])
        sc = Script(1, "t", "is", "en")
        b.intro(sc, self.cur.by_id["eigdu_godur"])
        text = sc.transcript()
        self.assertIn("You know this:", text)
        self.assertIn("It is a pattern: you can say it with other words.", text)
        self.assertNotIn("Here is a useful pattern", text)
        # a pattern whose example is not known is still introduced as before
        fresh = self._builder(met=["hjalpina"])
        sc = Script(1, "t", "is", "en")
        fresh.intro(sc, self.cur.by_id["takk_fyrir"])
        self.assertIn("Here is a useful pattern", sc.transcript())
        # and in the lesson where the part came in with its whole, the pattern is that sentence with other words
        both = self._builder(met=["takk"])
        sc = Script(1, "t", "is", "en")
        both.intro(sc, self.cur.by_id["hjalpina"])
        both.in_lesson.add("hjalpina")
        both.intro(sc, self.cur.by_id["takk_fyrir"])
        self.assertEqual(sc.transcript().count("Here is a useful pattern"), 0)

    # -- the review: each expression once, a part through its whole

    def _prompts(self):
        return Prompts.load("en")

    def test_a_bare_part_is_asked_through_the_whole_the_learner_knows(self):
        from audiolesson.review_wholes import refine_review
        met = {"takk", "takk_fyrir", "hjalpina"}
        review = [{"items": ["hjalpina"], "prompt": "for the help", "answer": "hjálpina", "stage": "meaning"}]
        out, report = refine_review(review, self.cur, met, self._prompts())
        self.assertEqual([(q["items"], q["answer"], q["through"]) for q in out], [(["hjalpina"], "Takk fyrir hjálpina.", "takk_fyrir")])
        self.assertIn("Thanks for the help.", out[0]["prompt"])
        self.assertEqual([r["kind"] for r in report], ["through_whole"])
        # the whole is not known yet: the part stays bare, the fallback when no sentence exists
        out, report = refine_review(review, self.cur, {"hjalpina"}, self._prompts())
        self.assertEqual(([q["answer"] for q in out], report), (["hjálpina"], []))

    def test_the_refine_review_subcommand_refines_a_list_of_questions(self):
        """For the bot's queue (site_update_notifier#96): the same rules as `plan.json` `review`, from JSON on stdin; what the learner has met comes from the learner file."""
        import contextlib
        import io
        import sys
        from audiolesson.cli import main
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "l.json"
            learner = LearnerState("is", "en", "A1")
            for i in ("takk", "takk_fyrir", "hjalpina", "matinn"):
                learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3)
            learner.save(path)
            payload = {"review": [
                {"items": ["matinn"], "prompt": "for the meal", "answer": "matinn"},
                {"items": ["eigdu_godan_dag"], "prompt": "p", "answer": "Eigðu góðan dag."},
                {"items": ["eigdu_godur"], "prompt": "q", "answer": "Eigðu góðan dag."},
            ]}
            out = io.StringIO()
            old_stdin = sys.stdin
            sys.stdin = io.StringIO(json.dumps(payload))
            try:
                with contextlib.redirect_stdout(out):
                    self.assertEqual(main(["refine-review", str(ROOT / "curricula" / "is-en"), "-l", str(path)]), 0)
            finally:
                sys.stdin = old_stdin
            result = json.loads(out.getvalue())
        self.assertEqual([(q["items"], q["answer"]) for q in result["review"]], [(["matinn"], "Takk fyrir matinn."), (["eigdu_godan_dag", "eigdu_godur"], "Eigðu góðan dag.")])
        self.assertEqual(sorted(r["kind"] for r in result["refined"]), ["same_answer", "through_whole"])

    def test_a_part_inside_a_longer_form_is_asked_through_that_phrase(self):
        """#257 review: «norðurljós» counts as housed by «Ég vil sjá norðurljósin.»; the review must then ask that sentence, not the bare word."""
        from audiolesson.review_wholes import refine_review
        review = [{"items": ["nordurljos"], "prompt": "northern lights", "answer": "norðurljós", "stage": "meaning"}]
        out, report = refine_review(review, self.cur, {"nordurljos", "eg_vil_sja_nordurljosin"}, self._prompts())
        self.assertEqual([(q["answer"], q["through"]) for q in out], [("Ég vil sjá norðurljósin.", "eg_vil_sja_nordurljosin")])
        self.assertEqual([r["kind"] for r in report], ["through_whole"])

    def test_a_part_is_never_asked_beside_the_whole_that_holds_it(self):
        from audiolesson.review_wholes import parts_outside_their_whole, refine_review
        review = [
            {"items": ["tvo_fullordna"], "prompt": "two adults", "answer": "tvo fullorðna", "stage": "meaning"},
            {"items": ["partei_takk"], "prompt": "Two adults, please.", "answer": "Tvo fullorðna, takk.", "stage": "situation"},
        ]
        self.assertEqual(parts_outside_their_whole(review, self.cur), 1)
        out, report = refine_review(review, self.cur, {"tvo_fullordna", "partei_takk"}, self._prompts())
        self.assertEqual([(q["items"], q["answer"]) for q in out], [(["partei_takk", "tvo_fullordna"], "Tvo fullorðna, takk.")])
        self.assertEqual([r["kind"] for r in report], ["beside_whole"])
        self.assertEqual(parts_outside_their_whole(out, self.cur), 0)

    def test_no_two_questions_share_an_answer(self):
        from audiolesson.review_wholes import parts_outside_their_whole, refine_review
        review = [
            {"items": ["eigdu_godan_dag"], "prompt": "Wish him a good day.", "answer": "Eigðu góðan dag.", "stage": "situation"},
            {"items": ["eigdu_godur"], "prompt": "Have a good day.", "answer": "Eigðu góðan dag.", "stage": "recombine"},
            {"items": ["x"], "prompt": "p", "answer": "Eigðu góðan dag.", "stage": "meaning", "bonus": True},
        ]
        self.assertEqual(parts_outside_their_whole(review, self.cur), 1)
        out, report = refine_review(review, self.cur, set(), self._prompts())
        self.assertEqual([(q["items"], bool(q.get("bonus"))) for q in out], [(["eigdu_godan_dag", "eigdu_godur"], False), (["x"], True)])
        self.assertEqual([r["kind"] for r in report], ["same_answer"])

    def test_a_part_with_no_home_at_all_comes_out_of_the_review(self):
        from audiolesson.review_wholes import has_home, refine_review
        self.assertTrue(has_home(self.cur, self.cur.by_id["hundrad"]), "«Hundrað krónur, takk.» (#215)")
        self.assertTrue(has_home(self.cur, self.cur.by_id["nordurljos"]), "«Ég vil sjá norðurljósin.» holds it in a longer form")
        self.assertTrue(has_home(self.cur, self.cur.by_id["hjalpina"]))
        raw = ExcludeFillsTests._raw()
        raw["items"].append({"id": "orphan", "kind": "vocab", "target": "munaðarlaus", "meaning": "an orphan"})
        cur = curriculum_from_dict(raw)
        self.assertFalse(has_home(cur, cur.by_id["orphan"]))
        review = [{"items": ["orphan"], "prompt": "an orphan", "answer": "munaðarlaus", "stage": "meaning"}]
        out, report = refine_review(review, cur, {"orphan"}, self._prompts())
        self.assertEqual((out, [r["kind"] for r in report]), ([], ["no_home"]))

    def test_the_sentence_a_part_came_in_with_is_what_the_review_asks(self):
        """The first lesson of the bot's end-to-end test: «peysu» comes in inside «Áttu peysu?», a sentence taught whole, so the next-day question is the sentence even
        though the pattern itself is not introduced yet."""
        from audiolesson.cli import _plan
        learner = LearnerState("is", "en", "A1")
        sc = Planner(self.cur, learner, self.en, Timing(level="A1"), PlanConfig(minutes=5, new_items=3, priority=["afsakid", "peysu", "vegabref"]), today=TODAY).build()
        self.assertIn("new: Áttu peysu? (peysu)", [e.label for e in sc.exercises])
        plan = _plan(sc, self.cur)
        answers = {i: q["answer"] for q in plan["review"] for i in q["items"]}
        self.assertEqual(answers["peysu"], "Áttu peysu?", "the part is asked in its sentence")
        self.assertEqual(answers["vegabref"], "Áttu vegabréf?", "and another part through the pattern it was just taught whole in")
        self.assertEqual(Counter(q["answer"] for q in plan["review"]).most_common(1)[0][1], 1)
        self.assertIn("peysu", sc.meta["met_items"])
        self.assertIn("attu", sc.meta["met_items"], "taught whole today")

    def test_every_part_has_a_home(self):
        """#215's data side: the 18 vocab items with no frame or phrase now have one («Þetta er blár bíll.», «Hundrað krónur, takk.», «Það er margt fólk hér.»), or are gone
        («tuttugu og einn»: no scene needs it). The course is pinned at 0 here; `validate` lists them as an advisory because the sample curricula have a few («oui», «non»)."""
        from audiolesson.review_wholes import has_home
        self.assertEqual([i.id for i in self.cur.items if i.kind == "vocab" and not has_home(self.cur, i)], [])

    def test_a_colour_takes_the_form_of_its_noun(self):
        """The colours' home (#215): «Þetta er {colour} {noun}.» with the colour in the form of its noun's gender (#158)."""
        c = self.cur.by_id["litur_noun"]
        said = {self.cur.resolve_slots(c, {"colour": self.cur.by_id["blar"], "noun": self.cur.by_id[n]})[0] for n in ("bill", "bok", "hus")}
        self.assertEqual(said, {"Þetta er blár bíll.", "Þetta er blá bók.", "Þetta er blátt hús."})
        self.assertEqual(self.cur.resolve_slots(c, {"colour": self.cur.by_id["raudur"], "noun": self.cur.by_id["bok"]})[1], "This is a red book.")

    def test_the_plan_carries_the_refined_review_and_the_lessons_row_reads_zero(self):
        from audiolesson.cli import _plan
        from audiolesson.review_wholes import parts_outside_their_whole
        lessons = list(ListeningTaskTests._course(21))
        changed = 0
        for cur, _, sc in lessons:
            plan = _plan(sc, cur)
            self.assertEqual(parts_outside_their_whole(plan["review"], cur), 0, f"lesson {sc.lesson_number}")
            changed += len(plan["review_refined"])
            answers = [q["answer"].casefold() for q in plan["review"] if not q.get("bonus")]
            self.assertEqual(len(answers), len(set(answers)), f"lesson {sc.lesson_number}: one answer asked twice")
        self.assertGreater(changed, 10, "the review has something to refine on a real course")
        # lesson 20's case on the real path: the part comes in with its whole
        labels = [e.label for _, _, sc in lessons for e in sc.exercises if e.kind == "intro"]
        self.assertIn("new: Takk fyrir hjálpina. (hjálpina)", labels)
        self.assertNotIn("new: hjálpina", labels)


class ListeningTaskTests(unittest.TestCase):
    """#248: the second half's listening exercises (pick out information, catch an unknown word) and their rotation."""

    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        cls.en = Prompts.load("en")

    def _builder(self, known=()):
        from audiolesson.exercises import Builder
        learner = LearnerState("is", "en", "A1")
        for i in known:
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3)
        return Builder(self.cur, self.en, Timing(level="A1"), learner)

    def _gen(self, cid, **fills):
        from audiolesson.exercises import Generated
        c = self.cur.by_id[cid]
        f = {slot: self.cur.by_id[i] for slot, i in fills.items()}
        target, meaning = self.cur.resolve_slots(c, f)
        return Generated(c, f, target, meaning)

    def _known(self, *lines):
        from audiolesson.listening_tasks import tokens
        return {w.lower() for line in lines for w in tokens(line)}

    # -- the curriculum's side

    def test_a_probe_names_its_slots_and_both_languages(self):
        raw = ExcludeFillsTests._raw()
        raw["items"][2]["information_probes"] = [{"kind": "price", "answer": "{thing}", "meanings": {"en": "{thing}", "ja": "{thing}"}}]
        curriculum_from_dict(raw)  # a good probe loads
        for bad in (
            {"kind": "weather", "answer": "{thing}", "meanings": {"en": "{thing}", "ja": "{thing}"}},  # not a kind
            {"kind": "price", "answer": "peysu", "meanings": {"en": "x", "ja": "x"}},  # nothing to listen for
            {"kind": "price", "answer": "{other}", "meanings": {"en": "{other}", "ja": "{other}"}},  # a slot the construction lacks
            {"kind": "price", "answer": "{thing}", "meanings": {"en": "{thing}"}},  # no Japanese
            {"kind": "price", "answer": "{thing}", "meanings": {"en": "x", "ja": "y"}},  # meanings without the slot
        ):
            raw = ExcludeFillsTests._raw()
            raw["items"][2]["information_probes"] = [bad]
            with self.assertRaises(CurriculumError, msg=str(bad)):
                curriculum_from_dict(raw)
        raw = ExcludeFillsTests._raw()
        raw["items"][0]["information_probes"] = [{"kind": "price", "answer": "{thing}", "meanings": {"en": "{thing}", "ja": "{thing}"}}]
        with self.assertRaises(CurriculumError):  # a vocab item has no slots
            curriculum_from_dict(raw)

    def test_a_word_gloss_is_a_word_of_the_line_with_both_meanings(self):
        from audiolesson.themes import Level, Theme, Turn, _check
        def theme(gloss):
            return Theme(id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=[
                Turn(who="partner", say="Þarftu poka?", meaning="Do you need a bag?", variants=[{"say": "Viltu poka?", "meaning": "Do you want a bag?", "word_glosses": gloss}]),
                Turn(who="you", say="Nei, takk.", cue="Say no.", items=["nei"]),
            ])])
        _check(theme({"viltu": {"en": "do you want", "ja": "ほしいですか"}}))
        for bad in ({"hvar": {"en": "where", "ja": "どこ"}}, {"viltu": {"en": "do you want"}}, {"viltu": {"en": "", "ja": "x"}}):
            with self.assertRaises(CurriculumError, msg=str(bad)):
                _check(theme(bad))
        self.assertEqual(theme({"viltu": {"en": "a", "ja": "b"}}).levels[0].turns[0].lines()[1].word_glosses, {"viltu": {"en": "a", "ja": "b"}})

    def test_the_curriculum_carries_probes_and_glosses(self):
        self.assertEqual({k for k in ("thad_kostar_big", "thad_kostar", "klukkan_er") if self.cur.by_id[k].information_probes}, {"thad_kostar_big", "thad_kostar", "klukkan_er"})

    # -- pick out of a scene's line (#248 step 2)

    @staticmethod
    def _theme(turn):
        from audiolesson.themes import Level, Theme, Turn
        return Theme(id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=[
            turn, Turn(who="you", say="Takk.", cue="Thank her.", items=["takk"]),
        ])])

    def test_a_probe_is_a_stretch_of_its_line_with_a_question_when_there_are_two(self):
        from audiolesson.themes import Turn, _check
        two = [
            {"kind": "price", "answer": "fimm hundruð krónur", "meanings": {"en": "five hundred krónur", "ja": "500クローナ"}, "ask": {"en": "How much is the coffee?", "ja": "コーヒーは？"}},
            {"kind": "price", "answer": "þúsund krónur", "meanings": {"en": "a thousand krónur", "ja": "1000クローナ"}, "ask": {"en": "How much is the sandwich?", "ja": "サンドイッチは？"}},
        ]
        say = "Kaffið kostar fimm hundruð krónur og samlokan kostar þúsund krónur."
        _check(self._theme(Turn(who="partner", say="Hæ.", meaning="Hi.", listen=[{"say": say, "meaning": "m", "probes": two}])))
        def bad(probes, **kw):
            return self._theme(Turn(who="partner", say="Hæ.", meaning="Hi.", listen=[{"say": say, "meaning": "m", "probes": probes}], **kw))
        for broken in (
            [{**two[0], "answer": "tvö hundruð krónur"}, two[1]],  # not in the line
            [{k: v for k, v in two[0].items() if k != "ask"}, two[1]],  # two pieces, no question for one
            [{**two[0], "kind": "weather"}, two[1]],
            [{**two[0], "meanings": {"en": "five hundred krónur"}}, two[1]],
        ):
            with self.assertRaises(CurriculumError, msg=str(broken)):
                _check(bad(broken))
        _check(bad([{k: v for k, v in two[0].items() if k != "ask"}]))  # one piece: the plain question will do
        with self.assertRaises(CurriculumError):
            _check(self._theme(Turn(who="partner", say="Hæ.", meaning="Hi.", listen=[{"say": say, "meaning": "m"}])))  # a listening line without a probe
        with self.assertRaises(CurriculumError):
            _check(self._theme(Turn(who="you", say="Takk.", cue="c", items=["takk"], probes=two)))  # a learner's line has none

    def test_a_scenes_line_with_two_pieces_asks_for_one_in_icelandic(self):
        from audiolesson.listening_tasks import append_task, partner_pick_out
        from audiolesson.cando import load_cando
        from audiolesson.themes import load_themes
        themes = load_themes(ROOT / "curricula" / "is-en", self.cur, load_cando(ROOT / "curricula" / "is-en"))
        tour = next(t for t in themes if t.id == "tour")
        line = tour.levels[0].turns[2].listen_lines()[0]
        self.assertEqual(len(line.probes), 2, "two pieces: how long, and when")
        known = self._known("tuttugu mínútur klukkan hálf þrjú")
        tasks = [partner_pick_out(line, p, known, "en", source="theme:tour:1:2:0", scene="A coach tour.", speaker="native_a") for p in line.probes]
        self.assertEqual([(t.answer, t.meaning, t.ask) for t in tasks], [
            ("tuttugu mínútur", "twenty minutes", "How long do we stop?"), ("klukkan hálf þrjú", "half past two", "When do we leave?")])
        sc = Script(1, "t", "is", "en")
        b = self._builder()
        append_task(b, sc, tasks[0], 120.0)
        self.assertEqual([g.text for g in sc.segments if g.type in ("speak", "answer")], [line.say, "tuttugu mínútur", line.say])
        self.assertIn("How long do we stop?", sc.transcript())
        # the learner must be able to say the answer
        self.assertIsNone(partner_pick_out(line, line.probes[0], known - {"mínútur"}, "en", source="s", scene="", speaker="native_a"))
        # a line with several pieces and a probe without a question asks nothing
        broken = type(line)(who="partner", say=line.say, probes=[{k: v for k, v in line.probes[0].items() if k != "ask"}, line.probes[1]])
        self.assertIsNone(partner_pick_out(broken, broken.probes[0], known, "en", source="s", scene=""))

    def test_a_single_piece_that_is_most_of_its_line_is_an_echo_and_is_not_asked(self):
        """#248 step 2 review: «Það gera tvö þúsund krónur.» → "How much?" → «tvö þúsund krónur» is lesson 21's "just parroting": the answer is 3 of the
        line's 5 words. A single piece is asked only when the words outside it outnumber it."""
        from audiolesson.listening_tasks import append_task, partner_pick_out
        from audiolesson.themes import Turn
        probe = {"kind": "price", "answer": "tvö þúsund krónur", "meanings": {"en": "two thousand krónur", "ja": "2000クローナ"}}
        known = self._known("tvö þúsund krónur tuttugu mínútur")
        echo = Turn(who="partner", say="Það gera tvö þúsund krónur.", meaning="m", probes=[probe])
        self.assertIsNone(partner_pick_out(echo, probe, known, "en", source="theme:supermarket:1:5:0:0", scene=""))
        richer = Turn(who="partner", say="Hér stoppum við í tuttugu mínútur.", meaning="m",
                      probes=[{"kind": "duration", "answer": "tuttugu mínútur", "meanings": {"en": "twenty minutes", "ja": "20分"}}])
        task = partner_pick_out(richer, richer.probes[0], known, "en", source="theme:tour:1:2:2:0", scene="")
        self.assertEqual((task.answer, task.pattern, task.pieces), ("tuttugu mínútur", "theme:tour:1:2", 1))
        sc = Script(1, "t", "is", "en")
        ex = append_task(self._builder(), sc, task, 120.0)
        self.assertIn("How long?", sc.transcript())
        self.assertEqual(ex.stage, "single")

    def test_the_row_counts_a_single_piece_that_is_most_of_its_line(self):
        from audiolesson.planner import Planner
        sc = Script(1, "t", "is", "en")
        for stage, line, answer in (("single", "Það gera tvö þúsund krónur.", "tvö þúsund krónur"), ("single", "Hér stoppum við í tuttugu mínútur.", "tuttugu mínútur"),
                                    ("multi", "Safnið opnar klukkan tíu og lokar klukkan fimm.", "klukkan fimm")):
            ex = sc.new_exercise("pick_out", stage, [], "theme:x:1:1:0:0")
            sc.add(Segment("speak", "native_b", line, "is", 1.0, 1.0, "listening_line", ex.index))
            sc.add(Segment("answer", "native_b", answer, "is", 1.0, 1.0, None, ex.index))
        gen = sc.new_exercise("pick_out", "single", [], "attu: Áttu peysu?")
        self.assertEqual([Planner._is_echo(sc, e) for e in sc.exercises], [True, False, False, True])

    def test_a_price_is_picked_out_of_a_generated_sentence(self):
        from audiolesson.listening_tasks import generated_pick_out
        gen = self._gen("thad_kostar_big", count="fimm")
        probe = self.cur.by_id["thad_kostar_big"].information_probes[0]
        known = self._known(gen.target)
        task = generated_pick_out(self.cur, gen, probe, known, "At the till.", "native_b")
        self.assertEqual((task.line, task.answer, task.meaning), ("Það kostar fimm þúsund krónur.", "fimm þúsund krónur", "five thousand krónur"))
        self.assertEqual((task.kind, task.prompt_key, task.item_ids), ("pick_out", "pick_out_price", ("thad_kostar_big",)))
        self.assertIsNone(generated_pick_out(self.cur, gen, probe, known - {"krónur"}, "", "native_b"), "a word they do not know: not a listening task")
        self.assertIsNone(generated_pick_out(self.cur, gen, {**probe, "meanings": {"de": "x"}}, known, "", "native_b"), "no meaning in the learner's language")

    def test_a_time_is_picked_out_of_the_clock_sentence(self):
        from audiolesson.listening_tasks import generated_pick_out
        gen = self._gen("klukkan_er", hour="thrju")
        task = generated_pick_out(self.cur, gen, self.cur.by_id["klukkan_er"].information_probes[0], self._known(gen.target), "", "native_a")
        self.assertEqual((task.answer, task.meaning, task.prompt_key), ("þrjú", "three o'clock", "pick_out_time"))

    def test_the_question_is_never_guessed_from_a_slot_name(self):
        """«Hvenær opnar {place}?» holds no time: a construction without a probe never makes a pick-out."""
        self.assertFalse([c.id for c in self.cur.items if c.kind == "construction" and c.information_probes and c.id not in ("thad_kostar_big", "thad_kostar", "klukkan_er")])

    def test_a_pick_out_is_built_in_one_exercise_and_records_nothing(self):
        from audiolesson.listening_tasks import append_task, generated_pick_out
        b = self._builder()
        gen = self._gen("thad_kostar_big", count="fimm")
        task = generated_pick_out(self.cur, gen, self.cur.by_id["thad_kostar_big"].information_probes[0], self._known(gen.target), "At the till.", "native_b")
        sc = Script(1, "t", "is", "en")
        ex = append_task(b, sc, task, 120.0)
        self.assertEqual((ex.kind, ex.item_ids), ("pick_out", ["thad_kostar_big"]))
        text = sc.transcript()
        self.assertIn("At the till.", text)
        self.assertIn("How much does he say it costs?", text, "a scene was named: whose line it was")
        sc2 = Script(1, "t", "is", "en")
        from dataclasses import replace as _replace
        append_task(b, sc2, _replace(task, scene="", line="Það kostar tvö þúsund krónur."), 120.0)
        self.assertIn("How much is it?", sc2.transcript(), "no scene: the plain question")
        self.assertNotIn("partner", sc2.transcript() + text)
        self.assertEqual(len([g for g in sc.segments if g.type == "pause" and g.role == "answer"]), 1)
        self.assertEqual([g.text for g in sc.segments if g.type == "speak"], ["Það kostar fimm þúsund krónur."] * 2, "heard, then again after the answer")
        self.assertEqual(sc.review_questions(), [], "the next day's review does not ask a sentence that was only heard")

    def test_a_task_that_does_not_fit_leaves_no_trace(self):
        from audiolesson.listening_tasks import append_task, generated_pick_out
        b = self._builder()
        gen = self._gen("thad_kostar_big", count="fimm")
        task = generated_pick_out(self.cur, gen, self.cur.by_id["thad_kostar_big"].information_probes[0], self._known(gen.target), "", "native_b")
        sc = Script(1, "t", "is", "en")
        heard, said, recent = set(b.heard), dict(b.said), list(b.recent_answers)
        self.assertIsNone(append_task(b, sc, task, 3.0))
        self.assertEqual((sc.segments, sc.exercises, set(b.heard), dict(b.said), b.recent_answers), ([], [], heard, said, recent))

    def test_no_kind_runs_on_for_more_than_three(self):
        from audiolesson.listening_tasks import append_task, generated_pick_out, kind_has_room
        b = self._builder()
        sc = Script(1, "t", "is", "en")
        probe = self.cur.by_id["thad_kostar_big"].information_probes[0]
        made = 0
        for count in ("fimm", "tiu", "tvo", "thrju"):
            if count not in self.cur.by_id:
                continue
            gen = self._gen("thad_kostar_big", count=count)
            task = generated_pick_out(self.cur, gen, probe, self._known(gen.target), "", "native_b")
            made += append_task(b, sc, task, 120.0) is not None
        self.assertEqual(made, 3, "the fourth of a kind is refused")
        self.assertFalse(kind_has_room(sc, "pick_out"))
        self.assertTrue(kind_has_room(sc, "catch_unknown"))

    # -- catch an unknown word

    def test_one_unknown_word_with_a_meaning_is_caught(self):
        from audiolesson.listening_tasks import catch_unknown
        repair = self.cur.by_id["hvad_thydir_thetta"]
        glosses = {"viltu": {"en": "do you want", "ja": "ほしいですか"}, "poka": {"en": "a bag", "ja": "袋"}}
        known = self._known("Ég vil poka með því.")
        task = catch_unknown("Viltu poka?", glosses, known, "en", repair, repair_known=True, source="theme:x:1:0:1", scene="")
        self.assertEqual((task.kind, task.answer, task.meaning, task.repair, task.item_ids), ("catch_unknown", "Viltu", "do you want", repair.target, (repair.id,)))
        each = lambda **kw: catch_unknown(**{"line": "Viltu poka?", "glosses": glosses, "known_words": known, "known_lang": "en", "repair": repair, "repair_known": True, "source": "s", "scene": "", **kw})
        self.assertIsNone(each(repair_known=False), "the learner cannot yet ask what a word means")
        self.assertIsNone(each(line="Viltu poka? Viltu."), "the same unknown word twice")
        self.assertIsNone(each(known_words=known - {"poka"}), "two unknown words")
        self.assertIsNone(each(known_words=known | {"viltu"}), "no unknown word")
        self.assertIsNone(each(glosses={}), "an unknown word without an authored meaning")

    def test_a_catch_is_asked_with_the_repair_phrase_and_records_nothing(self):
        from audiolesson.listening_tasks import append_task, catch_unknown
        repair = self.cur.by_id["hvad_thydir_thetta"]
        b = self._builder(known=[repair.id])
        task = catch_unknown("Viltu poka?", {"viltu": {"en": "do you want", "ja": "ほしいですか"}}, self._known("poka"), "en", repair, repair_known=True, source="s", scene="")
        sc = Script(1, "t", "is", "en")
        ex = append_task(b, sc, task, 120.0)
        self.assertEqual(ex.kind, "catch_unknown")
        answers = [g for g in sc.segments if g.type == "answer"]
        self.assertEqual([g.text for g in answers], ["Viltu", repair.target])
        self.assertTrue(all(g.speaker == "native_a" for g in answers), "the model answer is the other voice than the partner's")
        self.assertIn("Do you want", sc.transcript())
        self.assertEqual(b.learner.items.keys(), {repair.id}, "nothing is credited")

    # -- the rotation

    def test_the_rotation_goes_round_and_skips_what_cannot_be_added(self):
        from audiolesson.listening_tasks import SecondHalfRotation
        r = SecondHalfRotation()
        asked = []
        def emit(kind):
            asked.append(kind)
            return True
        for _ in range(7):
            r.play(emit)
        self.assertEqual(asked, ["heard", "pick_out", "pick_out", "catch_unknown", "today", "heard", "pick_out"])
        r = SecondHalfRotation()
        asked.clear()
        self.assertTrue(r.play(lambda k: asked.append(k) or k == "today"))
        self.assertEqual(asked, ["heard", "pick_out", "pick_out", "catch_unknown", "today"], "one round, to the first kind that could be added")
        self.assertFalse(SecondHalfRotation().play(lambda k: False))

    # -- in a lesson

    @staticmethod
    def _course(lessons):
        from audiolesson.cando import load_cando
        from audiolesson.themes import load_themes, scenario_order
        path = ROOT / "curricula" / "is-en"
        cur = load_curriculum(path)
        scenarios = load_cando(path)
        themes = load_themes(path, cur, scenarios)
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for n in range(1, lessons + 1):
            cfg = PlanConfig(minutes=30, new_target=8, themes=themes, theme_scenarios=scenario_order(scenarios))
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=day).build()
            yield cur, learner, sc
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)

    def test_the_second_half_of_a_lesson_listens_for_information_and_unknown_words(self):
        from audiolesson.cli import _plan
        lessons = list(self._course(21))
        kinds = Counter(e.kind for _, _, sc in lessons for e in sc.exercises)
        self.assertGreater(kinds["pick_out"], 3)
        self.assertGreater(kinds["catch_unknown"], 3)
        for cur, learner, sc in lessons:
            m = sc.meta
            closing_at = next((e.start for e in sc.exercises if e.kind == "closing"), float("inf"))  # the closing block's own exercises are not counted
            self.assertEqual(m["pick_out_count"], sum(e.kind == "pick_out" for e in sc.exercises if m["target_reached_at"] <= e.start < closing_at))
            self.assertEqual(_plan(sc, cur)["second_half"]["pick_out_count"], m["pick_out_count"])
            self.assertLessEqual(sc.total_duration, 30 * 60 + 120, sc.lesson_number)
            # #248 review: the same two frames and the same word over and over would be a new boredom
            picks = Counter(":".join(e.label.split(":")[:4]) for e in sc.exercises if e.kind == "pick_out")  # per partner turn of a scene: one a lesson (#248 review)
            self.assertLessEqual(max(picks.values(), default=0), PlanConfig().max_pick_outs_per_pattern, f"lesson {sc.lesson_number}: {picks}")
            # #248 step 2: a line of a scene, never a drilled frame plus its answer
            self.assertTrue(all(e.label.startswith("theme:") for e in sc.exercises if e.kind == "pick_out"), f"lesson {sc.lesson_number}")
            self.assertEqual(m["pick_out_echo_count"], 0)
            words = [next(g.text.lower() for g in sc.segments if g.exercise == e.index and g.type == "answer") for e in sc.exercises if e.kind == "catch_unknown"]
            self.assertEqual(len(words), len(set(words)), f"lesson {sc.lesson_number}: a word caught twice: {words}")
            # the run row stops at the closing block, whose recalls are a run of their own
            from itertools import groupby
            closing_at = next((e.start for e in sc.exercises if e.kind == "closing"), float("inf"))
            between = [e for e in sc.exercises if m["target_reached_at"] <= e.start < closing_at and e.kind not in ("opening", "closing")]
            self.assertEqual(m["longest_kind_run_after_target"], max((sum(1 for _ in g) for _, g in groupby(between, key=lambda e: e.kind)), default=0))
            row = [e.kind for e in sc.exercises]
            for k in range(len(row) - 3):
                if row[k] in ("pick_out", "catch_unknown"):
                    self.assertFalse(row[k] == row[k + 1] == row[k + 2] == row[k + 3], f"lesson {sc.lesson_number}: four {row[k]} in a row")
            # what was only heard is not practised: the exposures name no item for an exercise of these kinds alone
            heard_only = {i for e in sc.exercises if e.kind in ("pick_out", "catch_unknown") for i in e.item_ids}
            practised = {i for e in sc.exercises if e.kind in ("intro", "recall", "generative", "connect", "dialogue") for i in e.item_ids}
            for item in heard_only - practised:
                self.assertNotIn(item, m["exposures"], f"lesson {sc.lesson_number}: {item} was only heard")

    def test_a_line_with_two_pieces_is_asked_with_a_question_that_names_one(self):
        asked = set()
        for _, _, sc in self._course(30):
            text = sc.transcript()
            for q in ("How much is the coffee?", "How much is the sandwich?", "How much is the skyr?", "How much is the milk?", "How long do we stop?", "When do we leave?"):
                if q in text:
                    asked.add(q)
        self.assertGreaterEqual(len(asked), 2, asked)

    def test_no_pick_out_before_the_target_is_delivered(self):
        for _, _, sc in self._course(21):
            reached = sc.meta["target_reached_at"]
            for e in sc.exercises:
                if e.kind in ("pick_out", "catch_unknown") and sc.meta["target_reached_at"]:
                    self.assertGreaterEqual(e.start + 0.01, reached - 1, f"lesson {sc.lesson_number}")


class RepeatedWordFillsTests(unittest.TestCase):
    """#251 review (owner): a generated sentence never repeats a word across two of its fills («Ég ætla að fá mjólk með mjólk.»)."""

    def test_two_fills_sharing_a_word_never_make_a_sentence(self):
        from audiolesson.exercises import Builder
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        c = cur.by_id["eg_aetla_ad_fa_addon"]
        learner = fresh()
        for i in ("mjolk", "kaffi", "med_mjolk", "eg_aetla_ad_fa"):
            self.assertIn(i, cur.by_id, i)
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
        seen = set()
        for _ in range(30):
            g = b.generate(c, prefer_unused=False)
            if g is not None:
                seen.add(g.target)
        self.assertNotIn("Ég ætla að fá mjólk með mjólk.", seen)
        self.assertIn("Ég ætla að fá kaffi með mjólk.", seen, "a different word is still fine")


class ExcludeFillsTests(unittest.TestCase):
    """#192 (owner, after lesson 20): a named fill a construction never takes although its tag fits: an exception to the tags, not a
    new tagging scheme («Áttu leigubíl?» is not said; «Ég þarf leigubíl.» stays)."""

    @staticmethod
    def _raw(exclude=("bil",)):
        return {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "peysa", "kind": "vocab", "target": "peysu", "meaning": "a sweater", "tags": ["acc"]},
                {"id": "bil", "kind": "vocab", "target": "leigubíl", "meaning": "a taxi", "tags": ["acc"]},
                {"id": "attu", "kind": "construction", "target": "Áttu {thing}?", "meaning": "Do you have {thing}?",
                 "slots": {"thing": "acc"}, "example": {"thing": "peysa"}, "exclude_fills": list(exclude)},
                {"id": "tharf", "kind": "construction", "target": "Ég þarf {thing}.", "meaning": "I need {thing}.",
                 "slots": {"thing": "acc"}, "example": {"thing": "bil"}},
            ],
        }

    def test_the_construction_never_takes_the_excluded_fill_and_another_one_does(self):
        from audiolesson.exercises import Builder
        cur = curriculum_from_dict(self._raw())
        self.assertEqual([i.id for i in cur.items_with_tag("acc", cur.by_id["attu"])], ["peysa"])
        self.assertEqual([i.id for i in cur.items_with_tag("acc", cur.by_id["tharf"])], ["peysa", "bil"])
        learner = fresh()
        for i in ("peysa", "bil"):
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
        said = set()
        for _ in range(12):
            for c in ("attu", "tharf"):
                g = b.generate(cur.by_id[c], prefer_unused=False)
                if g is not None:
                    said.add(g.target)
        self.assertNotIn("Áttu leigubíl?", said)
        self.assertIn("Ég þarf leigubíl.", said)
        self.assertIn("Áttu peysu?", said)

    def test_validate_rejects_an_unknown_fill_a_wrong_tag_and_a_non_construction(self):
        for bad in ("nope", "tharf"):
            with self.assertRaises(CurriculumError):
                curriculum_from_dict(self._raw(exclude=(bad,)))
        raw = self._raw()
        raw["items"][0]["exclude_fills"] = ["bil"]
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)

    def test_the_course_excludes_leigubil_from_attu_only(self):
        cur = load_curriculum(Path(__file__).resolve().parent.parent / "curricula" / "is-en")
        self.assertEqual(cur.by_id["attu"].exclude_fills, ["leigubil"])
        self.assertNotIn("leigubil", [i.id for i in cur.items_with_tag("acc_thing", cur.by_id["attu"])])
        self.assertIn("leigubil", [i.id for i in cur.items_with_tag("acc_thing")])


class PatternInstanceIntroTests(unittest.TestCase):
    """#192, the rest (owner, after lesson 18): a linked phrase whose pattern and fillers are *known* comes in as one sentence of its
    pattern, not as a new item with a ladder; it stays in ``new_items`` and the next-day question decides."""

    @staticmethod
    def _cur():
        return curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "tvo", "kind": "vocab", "target": "tvo", "meaning": "two", "tags": ["c"]},
                {"id": "thrja", "kind": "vocab", "target": "þrjá", "meaning": "three", "tags": ["c"]},
                {"id": "pat", "kind": "construction", "target": "{count} miða, takk.", "meaning": "{count} tickets, please.",
                 "slots": {"count": "c"}, "example": {"count": "tvo"}},
                {"id": "ph", "kind": "phrase", "target": "Þrjá miða, takk.", "meaning": "Three tickets, please.",
                 "instance_of": "pat", "instance_fill": {"count": "thrja"}},
            ],
        })

    @staticmethod
    def _learner(known=("tvo", "thrja", "pat")):
        learner = LearnerState("is", "en", "A1")
        for i in known:
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3,
                                         due=(TODAY + timedelta(days=5)).isoformat(), last_practiced=(TODAY - timedelta(days=2)).isoformat())
        learner.lessons_completed = 4
        return learner

    def _plan(self, learner, day=TODAY):
        return Planner(self._cur(), learner, Prompts.load("en"), Timing(level="A1"),
                       PlanConfig(minutes=10, new_items=1, max_new_items=1, priority=["ph"], seed=3), today=day).build()

    def test_a_known_pattern_and_filler_take_the_phrase_as_one_pattern_sentence(self):
        sc = self._plan(self._learner())
        self.assertEqual((sc.meta["embedded_items"], sc.meta["pattern_instances"]), (["ph"], ["ph"]))
        self.assertIn("ph", sc.meta["new_items"], "it stays in new_items: the bot asks it the next day")
        mine = [e for e in sc.exercises if "ph" in e.item_ids]
        self.assertEqual([e.kind for e in mine], ["embed"], "one exercise: no ladder, no closing recall")
        self.assertIn("A sentence from a pattern you know", sc.transcript())
        self.assertNotIn("ph", sc.meta["exposures"], "nothing is recorded for the phrase")
        self.assertEqual(sc.meta["exposures"]["pat"], ["recombine"], "credited to the pattern")
        self.assertEqual(sc.meta["exposures"]["thrja"], ["recombine"], "and its filler")

    def test_the_next_day_question_asks_the_phrase_in_its_own_form(self):
        qs = [q for q in self._plan(self._learner()).review_questions() if q["items"] == ["ph"]]
        self.assertEqual([(q["prompt"], q["answer"], q["stage"]) for q in qs], [("Three tickets, please.", "Þrjá miða, takk.", "embed")])

    def test_said_back_it_is_met_with_one_durable_success_and_not_said_it_is_introduced_the_usual_way(self):
        learner = self._learner()
        apply_to_learner(self._plan(learner), learner, TODAY)
        self.assertEqual(learner.embedded, {"ph": 5})
        self.assertFalse(learner.has_met("ph"))
        said = copy.deepcopy(learner)
        said.report([], [], TODAY + timedelta(days=1), recalled=["ph"])
        self.assertTrue(said.has_met("ph"))
        self.assertEqual(said.items["ph"].durable_successes, 1)
        learner.report(["ph"], [], TODAY + timedelta(days=1))
        self.assertEqual(learner.embed_failed, ["ph"])
        sc = self._plan(learner, TODAY + timedelta(days=2))
        self.assertEqual((sc.meta["embedded_items"], sc.meta["pattern_instances"]), ([], []))
        self.assertIn("ph", sc.meta["exposures"], "a normal introduction")
        self.assertTrue(any(e.kind == "intro" and e.item_ids == ["ph"] for e in sc.exercises))

    def test_with_the_pattern_or_a_filler_not_yet_known_the_introduction_is_as_today(self):
        for known in (("tvo", "thrja"), ("pat", "tvo")):
            sc = self._plan(self._learner(known))
            self.assertEqual(sc.meta["pattern_instances"], [], known)
            self.assertTrue(any(e.kind == "intro" and e.item_ids == ["ph"] for e in sc.exercises), known)

    def test_the_real_curriculum_links_the_receipt_and_bill_phrases(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for phrase, filler in (("get_eg_fengid_kvittun", "kvittun"), ("get_eg_fengid_reikninginn", "reikninginn")):
            self.assertEqual((cur.by_id[phrase].instance_of, cur.by_id[phrase].instance_fill), ("get_eg_fengid", {"thing": filler}))
        self.assertIn("acc_request", cur.by_id["kvittun"].tags)


class InstanceOfPatternTests(unittest.TestCase):
    """#192 (owner's decisions): a fixed phrase that is an instance of a pattern is linked to it. Once the pattern is known,
    the phrase's later practice in a lesson is another sentence of the pattern with other fillers, credited to the pattern
    and its fillers, never to the phrase."""

    @staticmethod
    def _cur(fill=None, kind="phrase"):
        return curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "tvo", "kind": "vocab", "target": "tvo", "meaning": "two", "tags": ["c"]},
                {"id": "thrja", "kind": "vocab", "target": "þrjá", "meaning": "three", "tags": ["c"]},
                {"id": "fjora", "kind": "vocab", "target": "fjóra", "meaning": "four", "tags": ["c"]},
                {"id": "pat", "kind": "construction", "target": "{count} miða, takk.", "meaning": "{count} tickets, please.",
                 "slots": {"count": "c"}, "example": {"count": "thrja"}},
                {"id": "ph", "kind": kind, "target": "Þrjá miða, takk.", "meaning": "Three tickets, please.",
                 "instance_of": "pat", "instance_fill": fill or {"count": "thrja"}},
            ],
        })

    def test_a_link_must_make_the_phrase_exactly(self):
        self._cur()
        with self.assertRaisesRegex(CurriculumError, "says 'Tvo miða, takk.'"):
            self._cur(fill={"count": "tvo"})
        with self.assertRaisesRegex(CurriculumError, "every slot"):
            self._cur(fill={"other": "thrja"})
        with self.assertRaisesRegex(CurriculumError, "instance_of names the construction"):
            self._cur(kind="vocab")

    def test_the_real_curriculum_links_its_ticket_phrases(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        linked = {i.id: (i.instance_of, i.instance_fill) for i in cur.items if i.instance_of}
        self.assertEqual(linked["thrja_mida"], ("count_mida_takk", {"count": "thrja_acc"}))
        self.assertEqual(linked["einn_fullordinn_takk"], ("partei_takk", {"party": "einn_fullordinn"}))
        for ja in (None, "ja"):  # both glosses make a sentence of every filler
            c = load_curriculum(ROOT / "curricula" / "is-en", known_lang=ja)
            for pattern in ("count_mida_takk", "partei_takk"):
                item = c.by_id[pattern]
                tag = next(iter(item.slots.values()))
                for f in c.items_with_tag(tag):
                    target, meaning = c.resolve_slots(item, {next(iter(item.slots)): f})
                    self.assertTrue(target and meaning, (pattern, f.id))

    def test_a_sibling_recall_repeats_a_heard_sentence_rather_than_the_phrase(self):
        from audiolesson.exercises import Builder

        cur = self._cur()
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        b.in_lesson.update({"tvo", "thrja", "fjora", "pat"})
        sc = Script(1, "t", "is", "en")
        own = {"count": cur.by_id["thrja"]}
        for _ in range(8):  # every other sentence is heard in turn, then they repeat: always another than «Þrjá miða»
            ex = b.sibling_recall(sc, cur.by_id["pat"], own)
            self.assertIsNotNone(ex)
            self.assertNotIn("thrja", ex.item_ids)
            self.assertNotIn("ph", ex.item_ids)
            self.assertEqual((ex.kind, ex.stage), ("recall", "meaning"))
        none_left = {"count": cur.by_id["thrja"], **{}}
        b2 = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        b2.in_lesson.update({"thrja", "pat"})
        self.assertIsNone(b2.sibling_recall(Script(1, "t", "is", "en"), cur.by_id["pat"], none_left), "no other filler: nothing to offer")

    def test_the_real_party_pattern_has_fillers_to_rotate(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertGreaterEqual(len(cur.items_with_tag("party")), 4)
        self.assertTrue({"eitt_barn", "tvo_born"} <= {i.id for i in cur.items_with_tag("party")})

    def _lesson(self):
        from unittest import mock

        from audiolesson.exercises import Builder

        cur = self._cur()
        learner = LearnerState("is", "en", "A1")
        for i in ("tvo", "thrja", "fjora", "pat", "ph"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="situation", recalled=3,
                                         last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=3)).isoformat())
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=8, new_items=0, max_sentence_utterances=1, seed=1), today=TODAY)
        calls = []
        real = Builder._recombine

        def spy(self, sc, item, met_fills=False, form=None, exclude=None):
            ex = real(self, sc, item, met_fills=met_fills, form=form, exclude=exclude)
            calls.append((item.id, dict(exclude or {}), list(ex.item_ids) if ex else None, ex.label if ex else None))
            return ex

        with mock.patch.object(Builder, "_recombine", spy):
            sc = planner.build()
        return cur, sc, calls

    def test_the_phrase_past_its_cap_is_practised_in_another_sentence_of_the_pattern(self):
        cur, sc, calls = self._lesson()
        siblings = [c for c in calls if c[0] == "pat" and c[1].get("count") is not None and c[1]["count"].id == "thrja"]
        self.assertTrue(siblings, "the pattern was asked for a sentence other than the phrase's own")
        for _, _, ids, label in siblings:
            if ids is not None:
                self.assertNotIn("ph", ids, "never credited to the phrase")
                self.assertNotIn("Þrjá", label, "another filler")

    def test_a_pattern_not_yet_known_leaves_the_phrase_as_it_was(self):
        from unittest import mock

        from audiolesson.exercises import Builder

        cur = self._cur()
        learner = LearnerState("is", "en", "A1")
        learner.items["ph"] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="situation", recalled=3,
                                        last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=3)).isoformat())
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=6, new_items=0, max_sentence_utterances=1, seed=1), today=TODAY)
        with mock.patch.object(Builder, "_recombine", side_effect=AssertionError("no pattern sentence before the pattern is known")):
            planner.build()


class NoveltyAnnouncementTests(unittest.TestCase):
    """#197: «Now something you haven't heard yet» is for a new pattern or form, not for each new filler: once per construction
    and form in a lesson. The owner also dropped «Klukkan er ekki {hour}.»."""

    def _builder(self, known):
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"), random.Random(1))
        b.in_lesson.update(known)
        return cur, b

    @staticmethod
    def _narration(sc, ex):
        return " ".join(s.text for s in sc.segments if s.exercise == ex.index and s.type == "narrate")

    def test_a_run_of_fillers_is_announced_once(self):
        cur, b = self._builder({"klukkan_er", "thrju", "fimm", "sex", "sjo", "atta"})
        sc = Script(1, "t", "is", "en")
        said = []
        for _ in range(4):
            ex = b._recombine(sc, cur.by_id["klukkan_er"], met_fills=True)
            self.assertIsNotNone(ex)
            said.append("haven't heard yet" in self._narration(sc, ex))
        self.assertEqual(said, [True, False, False, False])

    def test_another_pattern_is_announced_again(self):
        cur, b = self._builder({"klukkan_er", "thrju", "fimm", "sex", "eg_aetla_ad", "fara_heim", "fara_i_sund", "versla"})
        sc = Script(1, "t", "is", "en")
        first = b._recombine(sc, cur.by_id["klukkan_er"], met_fills=True)
        other = b._recombine(sc, cur.by_id["eg_aetla_ad"], met_fills=True)
        self.assertTrue("haven't heard yet" in self._narration(sc, first))
        self.assertTrue(other is not None and "haven't heard yet" in self._narration(sc, other))

    def test_a_new_lesson_announces_again_and_the_clock_has_no_negative(self):
        cur, b = self._builder({"klukkan_er", "thrju", "fimm", "sex"})
        self.assertEqual(cur.by_id["klukkan_er"].negative, "")
        self.assertTrue(cur.by_id["klukkan_er"].question)
        sc = Script(1, "t", "is", "en")
        b._recombine(sc, cur.by_id["klukkan_er"], met_fills=True)
        _, again = self._builder({"klukkan_er", "thrju", "fimm", "sex"})
        sc2 = Script(2, "t", "is", "en")
        ex = again._recombine(sc2, cur.by_id["klukkan_er"], met_fills=True)
        self.assertIn("haven't heard yet", self._narration(sc2, ex))


class LeastSaidSentenceTests(unittest.TestCase):
    """#192: a generated sentence is, once every combination was used, the one said fewest times in the lesson."""

    def test_a_generated_sentence_is_the_one_said_fewest_times(self):
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))
        c = cur.by_id["virkar_ekki"]
        b.in_lesson.update({"virkar_ekki", "sturtan", "ljosid", "netid"})
        sentences = {i: _norm_utterance(cur.resolve_slots(c, {"thing": cur.by_id[i]}, "f", None)[0]) for i in ("sturtan", "ljosid", "netid")}
        for i in sentences:
            b.used_combos.add(f"virkar_ekki:thing={i}")
        b.said[sentences["sturtan"]] = 5
        b.said[sentences["ljosid"]] = 3
        b.said[sentences["netid"]] = 4
        for _ in range(10):
            self.assertEqual(b.generate(c).fills["thing"].id, "ljosid", "every combination used: the least said")


class OpenItemsInThePlanTests(unittest.TestCase):
    """#199: plan.json carries the open items the lesson practised and those waiting, every practised one has a written
    question, and an open item is repaired, not «tried», in a theme or listening turn."""

    def setUp(self):
        from audiolesson.cando import load_cando
        from audiolesson.themes import load_themes, scenario_order

        self.cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", self.cur)
        self.themes = load_themes(ROOT / "curricula" / "is-en", self.cur, scenarios)
        self.order = scenario_order(scenarios)
        self.supermarket = next(t for t in self.themes if t.id == "supermarket")
        self.learner = LearnerState("is", "en", "A1")
        known = list(self.supermarket.levels[0].items) + [i.id for i in sorted(self.cur.items, key=lambda i: i.order)[:120]]
        for i in dict.fromkeys(known):
            self.learner.items[i] = ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning",
                                              recalled=2, last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=1)).isoformat())

    def _planner(self):
        return Planner(self.cur, self.learner, Prompts.load("en"), Timing(level="A1"),
                       PlanConfig(minutes=30, new_items=0, themes=[self.supermarket], theme_scenarios=["A3"], seed=1), today=TODAY)

    def _open(self, item_id):
        self.learner.items[item_id].last_outcome = "not_recalled"
        self.learner.items[item_id].failures = 1
        self.assertTrue(self.learner.is_open(item_id))

    def test_the_plan_lists_open_items_and_every_practised_one_has_a_question(self):
        from audiolesson.cli import _plan

        for i in ("skyr", "attu"):
            self._open(i)
        sc = self._planner().build()
        plan = _plan(sc, self.cur)
        self.assertIn("open_items", plan)
        self.assertIn("open_not_fitted", plan)
        self.assertEqual(plan["open_items"], sc.meta["open_items"])
        self.assertTrue(plan["open_items"], "an open item was practised")
        asked = {i for q in plan["review"] for i in q["items"]}
        for i in plan["open_items"]:
            if self.cur.by_id[i].kind != "construction":
                self.assertIn(i, asked, f"{i}: an open item the review can ask")

    def test_an_open_item_that_did_not_fit_the_lesson_has_a_question_too(self):
        """#220: the review asks every open item, so one the lesson had no room for needs its question as well."""
        from audiolesson.cli import _plan

        sc = Script(1, "t", "is", "en")
        sc.meta["open_items"] = ["skyr"]
        sc.meta["open_not_fitted"] = ["sofa"]
        plan = _plan(sc, self.cur)
        (q,) = [q for q in plan["review"] if q["items"] == ["sofa"]]
        self.assertEqual(q["answer"], self.cur.by_id["sofa"].target)
        self.assertEqual(q["stage"], "open")
        self.assertEqual(sum(1 for q in plan["review"] if q["items"] == ["skyr"]), 1)

    def test_a_construction_has_no_question_of_its_own(self):
        from audiolesson.cli import _plan

        cons = next(i.id for i in self.cur.items if i.kind == "construction")
        sc = Script(1, "t", "is", "en")
        sc.meta["open_not_fitted"] = [cons]
        self.assertEqual([q for q in _plan(sc, self.cur)["review"] if cons in q["items"]], [])

    def test_the_questions_command_gives_the_lessons_cue(self):
        """#220/#73: «sofa» is asked as «to sleep», not «Sleep.»; a form with a context is asked with it; a construction is left out."""
        import contextlib
        import io

        from audiolesson.cli import main

        cons = next(i.id for i in self.cur.items if i.kind == "construction")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["questions", str(ROOT / "curricula" / "is-en"), "--ids", f"sofa,gott,{cons},no_such_item"]), 0)
        got = json.loads(out.getvalue())
        self.assertEqual(set(got), {"sofa", "gott"})
        self.assertEqual(got["sofa"]["answer"], "sofa")
        self.assertIn("To sleep", got["sofa"]["prompt"])
        self.assertNotIn("Sleep.", got["sofa"]["prompt"])
        self.assertIn(self.cur.by_id["gott"].context, got["gott"]["prompt"])
        for i in ("sofa", "gott"):  # «cues»: every way the bare item is asked now, the first being the prompt
            self.assertIn(got[i]["prompt"], got[i]["cues"])
        prompts = Prompts.load("en")
        templates = prompts.data["meaning"]
        self.assertGreater(len(templates), 1)
        for t in templates:  # every wording the lesson can use for the meaning cue is a current cue
            self.assertIn(t.format(meaning="To sleep.", language="Icelandic"), got["sofa"]["cues"])
        in_context = prompts.data["meaning_in_context"]
        for t in in_context if isinstance(in_context, list) else [in_context]:
            self.assertTrue(any(c.endswith(t.split("{meaning}")[-1].format(context=self.cur.by_id["gott"].context)) for c in got["gott"]["cues"]))
        with_situations = next(it for it in self.cur.items if len(it.situations) > 1 and it.kind != "construction")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["questions", str(ROOT / "curricula" / "is-en"), "--ids", with_situations.id])
        self.assertTrue(set(with_situations.situations) <= set(json.loads(out.getvalue())[with_situations.id]["cues"]))

    def test_an_open_item_without_a_written_question_gets_one_from_its_situation_or_meaning(self):
        from audiolesson.cli import _plan

        sc = Script(1, "t", "is", "en")
        sc.meta["open_items"] = ["skyr"]
        plan = _plan(sc, self.cur)
        (q,) = [q for q in plan["review"] if q["items"] == ["skyr"]]
        self.assertEqual(q["answer"], self.cur.by_id["skyr"].target)
        self.assertEqual(q["stage"], "open")
        self.assertTrue(q["prompt"])
        self.assertNotIn("(", q["prompt"], "the narrated meaning carries no recall disambiguator")

    def test_the_fallback_prompt_uses_the_lessons_own_meaning_cue_in_the_known_language(self):
        from audiolesson.cli import _plan
        from audiolesson.exercises import meaning_prompt

        for lang in (None, "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            item = next(i for i in cur.items if i.kind in ("phrase", "vocab") and not i.has_situation)
            sc = Script(1, "t", cur.target_lang, cur.known_lang)
            sc.meta["open_items"] = [item.id]
            (q,) = [q for q in _plan(sc, cur)["review"] if q["items"] == [item.id]]
            prompts = Prompts.load(cur.known_lang)
            # the lesson's cue: an item with a context is asked with it (#220)
            expected = meaning_prompt(prompts, cur.known_lang, cur.target_lang, item.spoken_meaning, item.context)
            self.assertEqual(q["prompt"], expected)
            if item.context:
                self.assertIn(item.context, q["prompt"])
            if lang == "ja":
                self.assertNotIn("Say:", q["prompt"])

    def test_an_open_item_in_a_theme_turn_is_asked_not_tried(self):
        pick = self._planner().pick_theme()
        self.assertEqual(pick[2], set())
        for i in self.supermarket.levels[0].items:
            self._open(i)
        self.assertEqual(self._planner().pick_theme()[2], set(), "open items are met: no turn is tried")
        del self.learner.items["skyr"]
        self.assertTrue(self._planner().pick_theme()[2], "an item never met still makes its turn tried")

    def test_an_open_item_in_a_listening_turn_is_not_tried(self):
        planner = self._planner()
        dlg = next(d for d in self.cur.dialogues if any(t.expect for t in d.turns))
        turn = next(t for t in dlg.turns if t.expect)
        for i in [turn.expect, *turn.expect_fill.values()]:
            self.learner.items.setdefault(i, ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning",
                                                       recalled=2, last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=1)).isoformat()))
            self._open(i)
        heard, tried = planner.classify_turns(dlg)
        self.assertNotIn(turn.expect, heard)
        self.assertNotIn(turn.expect, tried)


class AdmissionOfPartsTests(unittest.TestCase):
    """#206 review: one admission rule for a part, whichever way it is introduced. A part some construction lists as a
    prerequisite is not given alone while that construction can still come with it; a part only a phrase holds comes with
    that phrase."""

    def setUp(self):
        self.cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.learner = LearnerState("is", "en", "A1")
        self.known = dict(stage="meaning", durable_successes=2, successes=8, interval_days=7, due=(TODAY + timedelta(days=5)).isoformat(),
                          last_practiced=(TODAY - timedelta(days=2)).isoformat())

    def _planner(self, **cfg):
        return Planner(self.cur, self.learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, **{"new_items": 1, **cfg}), today=TODAY)

    def test_a_variant_part_is_not_offered_while_its_frame_is_still_to_come(self):
        for i in self.cur.items:
            if i.order < self.cur.by_id["count_mida_takk"].order and i.id not in ("thrja_acc", "thrja_mida"):
                self.learner.items[i.id] = ItemState(**self.known)
        planner = self._planner()
        self.assertEqual([c.id for c in planner.frames_of(self.cur.by_id["thrja_acc"])], ["count_mida_takk"])
        self.assertFalse(planner.part_has_home(self.cur.by_id["thrja_acc"], set()), "not alone while its frame can still come with it")
        planner.builder.in_lesson.add("count_mida_takk")  # the frame is in the lesson already: the variant may follow
        self.assertTrue(planner.part_has_home(self.cur.by_id["thrja_acc"], {"count_mida_takk"}))

    def test_a_variant_part_comes_with_its_frame_when_selected(self):
        for i in self.cur.items:
            if i.order < self.cur.by_id["count_mida_takk"].order and i.id not in ("thrja_acc", "thrja_mida"):
                self.learner.items[i.id] = ItemState(**self.known)
        ids = [i.id for i in self._planner(priority=["thrja_acc"]).select_new(2)]
        self.assertIn("thrja_acc", ids)
        self.assertIn("count_mida_takk", ids, ids)

    def test_a_part_whose_phrase_is_known_but_not_scheduled_is_not_offered_as_an_extra(self):
        """#206 review (lesson 18 of the real path): «þrjá» was admitted because «Þrjá miða, takk.» is a met phrase that holds it,
        yet nothing made the lesson say that phrase, so «þrjá» was drilled bare. A phrase counts as the part's home as an extra only
        once the lesson has practised it."""
        for i in self.cur.items:
            if i.order < self.cur.by_id["count_mida_takk"].order and i.id not in ("thrja_acc", "count_mida_takk"):
                self.learner.items[i.id] = ItemState(**self.known)
        planner = self._planner()
        self.assertTrue(self.learner.has_met("thrja_mida"))
        self.assertFalse(planner.part_has_home(self.cur.by_id["thrja_acc"], set()))
        planner.builder.in_lesson.add("thrja_mida")  # the lesson says the phrase: the part has its sentence
        self.assertTrue(planner.part_has_home(self.cur.by_id["thrja_acc"], set()))

    def test_select_new_asks_the_same_question_for_a_variant_part(self):
        """#206 review: lesson 18 took «þrjá» through ``select_new``, which accepted a met phrase as its home. Whatever the path, a
        variant part with a met phrase that the lesson does not practise comes with its frame, or waits when the frame cannot."""
        for i in self.cur.items:
            if i.order < self.cur.by_id["count_mida_takk"].order and i.id not in ("thrja_acc", "count_mida_takk"):
                self.learner.items[i.id] = ItemState(**self.known)
        planner = self._planner(priority=["thrja_acc"])
        self.assertIn("thrja_acc", [i.id for i in planner.select_new(2)])
        self.assertIn("count_mida_takk", [i.id for i in planner.select_new(2)], "the frame comes with it")
        # the frame cannot come (a prerequisite nobody has): the part waits, though «Þrjá miða, takk.» is known
        self.cur.by_id["count_mida_takk"].prereqs = list(self.cur.by_id["count_mida_takk"].prereqs) + ["fjall"]
        planner = self._planner(priority=["thrja_acc"])
        self.assertNotIn("thrja_acc", [i.id for i in planner.select_new(2)])

    def test_a_part_no_construction_takes_comes_with_the_phrase_that_holds_it(self):
        planner = self._planner(priority=["fjall"])
        self.assertEqual(planner.frames_of(self.cur.by_id["fjall"]), [], "no construction lists it as a prerequisite")
        self.assertEqual([w.id for w in planner.candidate_wholes(self.cur.by_id["fjall"])][:1], ["hvad_er_thetta_fjall"])
        for i in self.cur.items:
            if i.order < self.cur.by_id["fjall"].order and i.id not in ("fjall", "hvad_er_thetta_fjall", "thetta_er_noun"):
                self.learner.items[i.id] = ItemState(**self.known)
        ids = [i.id for i in self._planner(priority=["fjall"]).select_new(2)]
        self.assertIn("fjall", ids)
        self.assertIn("hvad_er_thetta_fjall", ids, ids)


class PartWithItsFrameTests(unittest.TestCase):
    """#149 step 2: a part comes with its frame. «sturtan» alone has no sentence to live in («{thing} virkar ekki.» is the
    only one, and it lists «sturtan» as a prerequisite), so the frame is taught in the same selection, one over the count."""

    def setUp(self):
        self.cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.learner = LearnerState("is", "en", "A1")
        for i in self.cur.items:
            if i.order < self.cur.by_id["virkar_ekki"].order and i.id not in ("sturtan", "ljosid"):
                self.learner.items[i.id] = ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning",
                                                     recalled=2, last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=1)).isoformat())

    def _planner(self, **cfg):
        cfg = {"new_items": 1, **cfg}
        return Planner(self.cur, self.learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, **cfg), today=TODAY)

    def test_a_part_is_selected_with_the_construction_that_lists_it(self):
        planner = self._planner(priority=["sturtan"])
        self.assertEqual([c.id for c in planner.frames_of(self.cur.by_id["sturtan"])], ["virkar_ekki"])
        ids = [i.id for i in planner.select_new(2)]
        self.assertEqual(ids, ["sturtan", "ljosid", "virkar_ekki"], "the part, the second filler the pattern needs, then the frame: one over the count")
        alone = [i.id for i in self._planner(priority=["sturtan"]).select_new(1)]
        self.assertNotIn("sturtan", alone, "the group (part, filler, frame) doesn't fit one place: the part waits rather than coming alone")

    def test_a_part_with_two_ready_frames_takes_one_and_the_group_stays_within_one_over_the_count(self):
        cur = self.cur
        learner = LearnerState("is", "en", "A1")
        for i in cur.items:
            if i.order < cur.by_id["sundlaugin"].order or i.id == "hvenaer":
                learner.items[i.id] = ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning",
                                                recalled=2, last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=1)).isoformat())
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=3, seed=1, priority=["sundlaugin"]), today=TODAY)
        frames = [c.id for c in planner.frames_of(cur.by_id["sundlaugin"])]
        self.assertEqual(sorted(frames), ["hvar_er", "hvenaer_opnar"])
        for count in (1, 2, 3, 4):
            ids = [i.id for i in planner.select_new(count)]
            self.assertLessEqual(len(ids), count + 1, ids)
            self.assertLessEqual(sum(1 for f in frames if f in ids), 1, f"one frame per part: {ids}")
        # an utterance (a ``phrase``) is no part: it is not the trigger
        self.assertEqual(cur.by_id["hvenaer"].kind, "phrase")
        learner.items.pop("hvenaer")
        ids = [i.id for i in Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=1, seed=1, priority=["hvenaer"]), today=TODAY).select_new(1)]
        self.assertEqual(ids, ["hvenaer"], "«Hvenær?» comes alone, as an utterance")

    def test_a_frame_with_an_unmet_prerequisite_stays_out(self):
        for gone in ("dag_acc", "godan_daginn"):
            del self.learner.items[gone]
        self.assertIn("dag_acc", self.cur.by_id["eigdu_godur"].prereqs)
        ids = [i.id for i in self._planner(priority=["dag_acc"]).select_new(1)]
        self.assertIn("dag_acc", ids)
        self.assertNotIn("eigdu_godur", ids, "«godan_daginn» is still unmet: the frame can't be taught yet")

    def test_the_plan_does_not_drill_it_alone(self):
        sc = self._planner(priority=["sturtan"], new_items=3).build()
        self.assertIn("sturtan", sc.meta["new_items"])
        self.assertIn("virkar_ekki", sc.meta["new_items"])


class SpreadIntroductionTests(unittest.TestCase):
    """Lesson 13 feedback: all nine new expressions came in the first 15 of 30 minutes and the
    second half only repeated them. New material is spread over the lesson."""

    def test_introductions_are_spread_over_a_real_course(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        first_third, intros, worst_gap = 0, 0, 0.0
        for n in range(1, 17):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=5), today=day).build()
            starts = [e.start for e in sc.exercises if e.kind == "intro"]
            if n >= 8 and len(starts) >= 5:
                total = sc.total_duration
                first_third += sum(1 for t in starts if t < total / 3)
                intros += len(starts)
                worst_gap = max(worst_gap, max(b - a for a, b in zip(starts, starts[1:])))
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertGreater(intros, 20)
        self.assertLess(first_third / intros, 0.55, "most new items used to come in the first third")
        self.assertLess(worst_gap, 9 * 60, "the longest stretch without a new item used to be 10-11 minutes")


    def test_the_spread_does_not_depend_on_the_lesson_seed(self):
        """#187: the test above passed by the luck of its seed (the seed is the lesson number); the same course with seeds 0-5
        had up to 11 minutes with no introduction, because an idle lesson took its cheap construction or variant at the very end."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for seed in range(6):
            learner = LearnerState("is", "en", "A1")
            day, worst = TODAY, 0.0
            for n in range(1, 17):
                sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=5, seed=seed), today=day).build()
                starts = [e.start for e in sc.exercises if e.kind == "intro"]
                if n >= 8 and len(starts) >= 5:
                    worst = max(worst, max(b - a for a, b in zip(starts, starts[1:])))
                apply_to_learner(sc, learner, day)
                learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
                day += timedelta(days=1)
            self.assertLess(worst, 9 * 60, (seed, worst))

    def test_taking_the_extras_early_adds_no_item(self):
        """#187: a lesson that took a last-resort extra is built again with it known, so the idle stretch takes it when it starts.
        Only timing changes: the lesson's new items and its extras are those of its first build."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day, rebuilt = TODAY, 0
        for n in range(1, 17):
            def planner():
                return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=5, seed=2), today=day)
            first = planner()
            sc1 = first._build()
            sc = planner().build()
            extras = lambda s: set(s.meta.get("cheap_constructions", [])) | set(s.meta.get("variant_items", []))
            self.assertEqual(set(sc.meta["new_items"]), set(sc1.meta["new_items"]), n)
            self.assertEqual(extras(sc), extras(sc1), n)
            rebuilt += bool(first._extras_taken)
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertGreater(rebuilt, 2, "some lessons took an extra, so some were rebuilt")


class SayableLineTests(unittest.TestCase):
    """#179 (lesson 14 feedback): "can the learner say this line?" is judged per line, not per item
    from ``knows()``: a line they can say is asked (with a pause) even in a listening dialogue, and a
    short item already said in a sentence is asked in one at the closing, not as a bare part."""

    @staticmethod
    def _cur():
        items = [
            {"id": "k0", "kind": "phrase", "target": "Þekkt núll.", "meaning": "Known zero."},
            {"id": "fimm", "kind": "vocab", "target": "fimm", "meaning": "five", "tags": ["num"]},
            {"id": "tk", "kind": "vocab", "target": "þúsund krónur", "meaning": "a thousand krónur", "tags": ["price"]},
            {"id": "kostar", "kind": "construction", "target": "Það kostar {price}.", "meaning": "It costs {price}.", "slots": {"price": "price"}},
            {"id": "big", "kind": "construction", "target": "Það kostar {count} þúsund krónur.", "meaning": "It costs {count} thousand krónur.", "slots": {"count": "num"}},
        ]
        turns = [
            {"cue": "Tell him it costs five thousand krónur.", "expect": "big", "expect_fill": {"count": "fimm"}, "partner": "Dýrt.", "partner_meaning": "Dear."},
            {"cue": "Say known zero.", "expect": "k0"},
        ]
        return curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": items,
            "dialogues": [{"id": "d1", "setting": "A stall.", "requires": ["k0", "fimm"], "turns": turns}],
        })

    @staticmethod
    def _learner(met):
        learner = LearnerState("is", "en", "A1")
        for i in met:  # met and recalled once: not `knows()` (two durable recalls), but the learner can say it
            learner.items[i] = ItemState(stage="meaning", successes=1, recalled=1, durable_successes=1, interval_days=1,
                                         due=(TODAY + timedelta(days=1)).isoformat(), last_practiced=TODAY.isoformat())
        return learner

    def _planner(self, cur, learner):
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, new_items=0, max_new_items=0), today=TODAY)

    def test_a_line_another_pattern_makes_is_asked_not_told(self):
        cur = self._cur()
        learner = self._learner(["k0", "fimm", "tk", "kostar"])
        planner = self._planner(cur, learner)
        turn = cur.dialogues[0].turns[0]
        self.assertFalse(any(learner.knows(i) for i in ("big", "tk", "kostar")))
        self.assertTrue(planner.can_say_turn(turn), "«Það kostar | fimm | þúsund krónur.»: every chunk is something they say")
        found = planner.listening_dialogue()
        self.assertEqual((found[0].id, found[1]), ("d1", set()), "nothing is missing: an ordinary dialogue")
        sc = Script(1, "t", "is", "en")
        planner._play_listening(sc, *found)
        pauses = [s for s in sc.segments if s.type == "pause" and s.role == "answer"]
        self.assertEqual(len(pauses), 2, "both turns are asked, with a pause")
        self.assertNotIn("Here you would say", sc.transcript())
        self.assertEqual(planner.dialogues_listened, [], "an ordinary dialogue is not counted against the listening rest")
        self.assertEqual(planner.listening_asked[0]["dialogue"], "d1")
        self.assertIn("big", planner.listening_asked[0]["items"])
        # without «Það kostar {price}.» and «þúsund krónur» the line can't be said: it is heard
        bare = self._planner(cur, self._learner(["k0", "fimm"]))
        self.assertFalse(bare.can_say_turn(turn))
        self.assertEqual(bare.listening_dialogue()[1], {"big"})

    def test_the_real_solubas_line_is_sayable_from_chunks(self):
        """#179's named case on the real curriculum: «Það kostar {price}.» met, «fimm» known, «þúsund krónur»
        met, and `thad_kostar_big` unmet. No met pattern makes the exact sentence («fimm þúsund krónur» is no
        filler of «Það kostar {price}.»), but every chunk of the line is something the learner says."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        dlg = next(d for d in cur.dialogues if d.id == "solubas")
        turn = dlg.turns[0]
        self.assertEqual(turn.expect, "thad_kostar_big")
        learner = self._learner(["thad_kostar", "thusund_kronur"])
        learner.items["fimm"] = ItemState(stage="meaning", durable_successes=2, successes=4, recalled=2, interval_days=3,
                                          due=(TODAY + timedelta(days=3)).isoformat(), last_practiced=TODAY.isoformat())
        self.assertNotIn("thad_kostar_big", learner.items)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=TODAY)
        self.assertTrue(planner.can_say_turn(turn))
        bare = Planner(cur, self._learner(["thad_kostar"]), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=TODAY)
        self.assertFalse(bare.can_say_turn(turn), "«þúsund krónur» and «fimm» are not met: a word outside what they say")

    def test_a_heard_line_has_no_task_cue(self):
        cur = self._cur()
        planner = self._planner(cur, self._learner(["k0"]))  # nothing of «Það kostar fimm þúsund krónur.» is theirs
        self.assertEqual(planner.classify_turns(cur.dialogues[0]), ({"big"}, set()))
        sc = Script(1, "t", "is", "en")
        planner._play_listening(sc, cur.dialogues[0], {"big"})
        text = sc.transcript()
        self.assertIn("Here you would say:", text)
        self.assertNotIn("Tell him it costs five thousand krónur.", text, "«Tell him…» contradicts «Here you would say:»")
        self.assertIn("Say known zero.", text, "the lines that are asked keep their cue")
        self.assertEqual(planner.listening_tried, [])

    def test_a_line_they_can_say_part_of_is_heard_not_tried(self):
        """#240 (§9 #183 as revised by the concept): a listening scene never asks for a line that wasn't taught. «fimm»
        is theirs, the rest of the line isn't: the line is heard with its meaning, «Try it.» is gone, nothing is
        recorded for it, and no bonus question comes from it. The line they can say in full is still asked."""
        cur = self._cur()
        planner = self._planner(cur, self._learner(["k0", "fimm"]))
        self.assertEqual(planner.classify_turns(cur.dialogues[0]), (set(), {"big"}), "partly sayable, as before")
        sc = Script(1, "t", "is", "en")
        planner._play_listening(sc, cur.dialogues[0], {"big"})
        text = sc.transcript()
        self.assertNotIn("Try it.", text)
        self.assertIn("Here you would say:", text)
        self.assertIn("It costs five thousand krónur.", text, "a heard line comes with its meaning")
        self.assertIn("Say known zero.", text, "the taught line keeps its cue")
        self.assertEqual(len([s for s in sc.segments if s.type == "pause" and s.role == "answer"]), 1, "only the taught line is asked")
        self.assertEqual(planner.listening_tried, [])
        self.assertEqual(planner.listening_untaught, [])
        self.assertNotIn("big", planner.exposures, "the untaught construction is not recorded")

    def test_a_line_with_a_word_from_a_known_line_is_heard_on_the_real_curriculum(self):
        """#183 re-check (owner): the learner's words live inside longer known lines («þarf» in «Ég þarf hjálp.»), so a
        part is judged at word level, and «Ég þarf símkort.» is partly sayable for one who has «Ég þarf hjálp.». Since
        #240 a listening scene hears it all the same; a line they can say whole is asked."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        dlg = next(d for d in cur.dialogues if d.id == "simabud")
        known = Planner(cur, self._learner(["eg_tharf_hjalp"]), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=TODAY)
        heard, partly = known.classify_turns(dlg)
        self.assertIn("eg_tharf_simkort", partly)
        self.assertNotIn("eg_tharf_simkort", heard)
        nothing = Planner(cur, self._learner([]), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=TODAY)
        heard, partly = nothing.classify_turns(dlg)
        self.assertIn("eg_tharf_simkort", heard)
        self.assertEqual(partly, set())
        whole = Planner(cur, self._learner(["eg_tharf_simkort"]), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=TODAY)
        self.assertNotIn("eg_tharf_simkort", set().union(*whole.classify_turns(dlg)))
        sc = Script(1, "t", "is", "en")
        known._play_listening(sc, dlg, set())
        self.assertEqual(known.listening_tried, [])
        self.assertNotIn("Try it.", sc.transcript())
        self.assertIn("Here you would say:", sc.transcript())

    def test_a_listening_scene_that_asks_nothing_says_just_listen(self):
        """#240: the framing stays true to what follows. Every learner line heard → «just hear how it goes»."""
        cur = self._cur()
        planner = self._planner(cur, self._learner([]))
        sc = Script(1, "t", "is", "en")
        planner.builder.dialogue(sc, cur.dialogues[0], translate=True, listening={"big", "k0"})
        self.assertIn(Prompts.load("en").get("listening_intro"), sc.transcript())
        self.assertNotIn(Prompts.load("en").get("listening_intro_some_asked"), sc.transcript())

    def test_tried_lines_become_bonus_review_questions_and_a_said_one_counts(self):
        """#183 addendum: at most two tried lines go into the next review as bonus questions; 言えた makes the
        tried items met with one durable success; a miss changes nothing; the learner file keeps `tried`."""
        cur = self._cur()
        learner = self._learner(["k0", "fimm"])
        planner = self._planner(cur, learner)
        sc = Script(1, "t", "is", "en")
        # a tried line, as a theme turn makes one (a listening scene no longer tries, #240)
        planner.listening_tried.append({"dialogue": "d1", "items": ["big", "fimm"], "unknown": ["big"],
                                        "prompt": "Tell him it costs five thousand krónur.", "answer": "Það kostar fimm þúsund krónur."})
        bonus = planner._bonus_review()
        self.assertEqual(len(bonus), 1)
        self.assertEqual((bonus[0]["prompt"], bonus[0]["answer"], bonus[0]["bonus"]), ("Tell him it costs five thousand krónur.", "Það kostar fimm þúsund krónur.", True))
        self.assertEqual(set(bonus[0]["items"]), {"big", "fimm"})
        planner.cfg.max_bonus_questions = 0
        self.assertEqual(planner._bonus_review(), [])
        sc.meta = {"exposures": planner.exposures, "ladders": {}, "dialogues_listened": ["d1"], "new_items": [], "listening_tried": planner.listening_tried}
        apply_to_learner(sc, learner, TODAY)
        self.assertEqual(learner.tried, {"big": 1}, "the unknown construction is tried, not met")
        self.assertNotIn("big", learner.items)
        with tempfile.TemporaryDirectory() as tmp:
            learner.save(Path(tmp) / "l.json")
            self.assertEqual(LearnerState.load(Path(tmp) / "l.json").tried, {"big": 1}, "kept in the learner file")
        # a miss: nothing recorded, the item stays unmet and tried
        learner.report(["big"], [], TODAY + timedelta(days=1), lesson_number=1)
        learner.report([], [], TODAY + timedelta(days=1), lesson_number=1, hesitated=["big"])
        self.assertNotIn("big", learner.items)
        self.assertEqual(learner.tried, {"big": 1})
        # 言えた: met with one durable success, a normal first interval, known on its next recall
        learner.report([], [], TODAY + timedelta(days=1), lesson_number=1, recalled=["big", "fimm"])
        st = learner.items["big"]
        self.assertEqual((st.durable_successes, st.successes, st.recalled, st.interval_days), (1, 1, 1, 3))
        self.assertFalse(learner.knows("big"), "one durable success is not two (§9)")
        self.assertNotIn("big", learner.tried)

    def test_plan_json_carries_the_bonus_questions_and_the_tried_lines(self):
        from audiolesson.cli import _plan

        cur = self._cur()
        planner = self._planner(cur, self._learner(["k0", "fimm"]))
        sc = Script(1, "t", "is", "en")
        # a tried line, as a theme turn makes one (a listening scene no longer tries, #240)
        planner.listening_tried.append({"dialogue": "d1", "items": ["big", "fimm"], "unknown": ["big"],
                                        "prompt": "Tell him it costs five thousand krónur.", "answer": "Það kostar fimm þúsund krónur."})
        sc.meta = {"bonus_review": planner._bonus_review(), "listening_tried": planner.listening_tried, "listening_asked": planner.listening_asked}
        plan = _plan(sc, cur)
        self.assertEqual([q["items"] for q in plan["review"] if q.get("bonus")], [planner.listening_tried[0]["items"]])
        self.assertEqual(plan["listening_tried"][0]["dialogue"], "d1")
        self.assertIn("listening_asked", plan)
        self.assertFalse(any(q.get("bonus") for q in _plan(Script(1, "t", "is", "en"), cur)["review"]), "no bonus without tried lines")

    def test_a_short_item_said_in_a_sentence_is_asked_in_one_at_the_closing(self):
        checked = 0
        for n, (cur, sc) in enumerate(ShortItemRepetitionTests._course(14), 1):
            closing = next((e.index for e in sc.exercises if e.kind == "closing" and e.label == "final review"), None)
            if closing is None:
                continue
            for i in sc.meta["new_items"]:
                it = cur.by_id[i]
                if i in sc.meta["embedded_items"] or it.kind in ("construction", "transform") or it.word_count > 2:
                    continue
                before = [e for e in sc.exercises if e.index < closing and (e.kind == "generative" and i in e.item_ids or e.kind == "recall" and i in e.item_ids[1:])]
                if not before:
                    continue
                at_close = [e for e in sc.exercises if e.index > closing and i in e.item_ids]
                if not at_close:
                    continue
                checked += 1
                self.assertFalse(any(e.item_ids == [i] and e.kind == "recall" for e in at_close), (n, i, [e.label for e in at_close]))
        self.assertGreater(checked, 10)


class ShortItemRepetitionTests(unittest.TestCase):
    """Lesson 13 feedback, and lessons 6 and 13 before it (G14, §9 "Repetition"): a short new
    item was said alone six to nine times, within minutes, and the same English situation was
    narrated seven to ten times."""

    @staticmethod
    def _course(lessons: int = 18):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for n in range(1, lessons + 1):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=5), today=day).build()
            yield cur, sc
            apply_to_learner(sc, learner, day)
            new = sc.meta["new_items"]
            failed = new[:2] if n in (3, 4, 6, 7, 12) else []
            learner.report(failed, [], day + timedelta(days=1), lesson_number=n, recalled=[i for i in new if i not in failed])
            day += timedelta(days=1)

    def test_a_part_or_short_utterance_is_said_alone_at_most_three_times(self):
        """A part (a ``vocab`` item, whatever its length) is said alone at most three times: any bare practice counts, a
        mixed-review turn included (#187). A short utterance (a ``phrase``) is a complete thing to say, so a scene is its proper
        use (the owner's decision on #190): only its meaning-cued bare practices count."""
        bare = {"intro", "cloze", "hinted", "meaning", "situation"}
        cued = {"intro", "cloze", "hinted", "meaning"}
        checked = utterances = lapsed = in_sentences = 0
        for cur, sc in self._course():
            if sc.meta["bare_cap_lapsed"]:
                lapsed += 1  # nothing else was left to fill the lesson
                continue
            for i in sc.meta["new_items"]:
                it = cur.by_id[i]
                part = it.kind == "vocab"
                if i in sc.meta["embedded_items"] or it.kind in ("construction", "transform") or (not part and it.word_count > 2):
                    continue
                ex = [e for e in sc.exercises if i in e.item_ids]
                alone = sum(1 for e in ex if e.item_ids[0] == i and e.kind in ("intro", "recall") and e.stage in (bare if part else cued))
                if part:
                    alone += sum(1 for e in ex if e.kind == "connect")  # a pair's situation turns say each part alone
                self.assertLessEqual(alone, 3, (sc.lesson_number, i, alone))
                in_sentences += sum(1 for e in ex if e.kind == "generative" or (e.kind == "recall" and e.item_ids[0] != i))
                checked += 1
                utterances += not part
        self.assertGreater(checked, 30)
        self.assertGreater(utterances, 5, "short utterances are checked too")
        self.assertLessEqual(lapsed, 7, "the cap should hold in most lessons of a course")
        self.assertGreater(in_sentences, 20, "the rest of a part's practice is inside sentences")

    def test_a_due_short_review_item_is_asked_in_a_sentence_that_holds_it(self):
        """#187: the learner said «Hvar er bankinn?» and is then asked «bankinn» alone: the part after the whole. A short
        item due for review is a sentence that holds it, when one can be said."""
        items = [
            {"id": "bankinn", "kind": "vocab", "target": "bankinn", "meaning": "the bank"},
            {"id": "hvar_er_bankinn", "kind": "phrase", "target": "Hvar er bankinn?", "meaning": "Where is the bank?"},
        ] + [{"id": f"r{i}", "kind": "phrase", "target": f"Rifja {i}.", "meaning": f"Review {i}."} for i in range(6)]
        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})
        learner = LearnerState("is", "en", "A1")
        for i in ["bankinn", "hvar_er_bankinn"] + [f"r{i}" for i in range(6)]:
            overdue = (TODAY - timedelta(days=9)).isoformat() if i == "bankinn" else TODAY.isoformat()
            learner.items[i] = ItemState(due=overdue, successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=1, new_items=0), today=TODAY).build()
        asked = [e.item_ids[0] for e in sc.exercises if e.kind == "recall"]
        self.assertNotIn("bankinn", asked, "never alone while its sentence can be said")
        self.assertGreaterEqual(asked.count("hvar_er_bankinn"), 2, "its review is the sentence (besides the sentence's own)")

    def test_a_part_is_not_reviewed_by_asking_the_sentence_just_asked(self):
        """#190 review: «Hvenær?» was reviewed by asking «Hvenær leggjum við af stað?» right after that sentence was asked, so the
        sentence came again and again and «Hvenær?» itself never. The review path does not repeat the previous exercise: the sentence
        just asked, or asked twice, is not asked again; the part was just said inside it, so its review is done through that exercise and nothing more is played."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for seed in range(6):
            learner = LearnerState("is", "en", "A1")
            for i in ("hvenaer", "hvenaer_leggjum_vid_af_stad"):
                learner.items[i] = ItemState(due=(TODAY - timedelta(days=9)).isoformat(), successes=1, durable_successes=0, stage="meaning", recalled=1, last_outcome="hesitated")
            for i in ("ja", "nei", "takk", "hae", "bless", "godan_daginn", "afsakid", "eg_skil"):
                learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=seed, new_items=0), today=TODAY).build()
            asked = [e.item_ids[0] for e in sc.exercises if e.kind == "recall"]
            self.assertFalse([a for a, b in zip(asked, asked[1:]) if a == b], (seed, asked))
            self.assertLessEqual(asked.count("hvenaer_leggjum_vid_af_stad"), 4, (seed, asked))
            self.assertTrue(sc.meta["exposures"].get("hvenaer"), "the part is credited as reviewed, through the sentence that was just asked")
            sentence = "hvenaer_leggjum_vid_af_stad"
            self.assertFalse([b for a, b in zip(asked, asked[1:]) if a == sentence and b == "hvenaer"], "never as a scene right after its sentence")

    def test_a_generated_sentence_is_not_the_one_the_learner_just_said(self):
        """#190 review: the closing recalls of «peysu» and of «Áttu {thing}?» both said «Áttu peysu?», back to back: the first, asked as
        the part's sentence, was not counted as used, and the pattern's three fillers were all used by then. The sentence just said
        (or the one before) is not drawn again while another is possible; sentence_recall marks its combination used."""
        from audiolesson.exercises import _norm_utterance

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        for i in ("attu", "peysu", "poka", "vegabref"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        builder = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY).builder
        builder.recent_answers = [_norm_utterance("Áttu peysu?")]
        drawn = {builder.generate(cur.by_id["attu"]).target for _ in range(40)}
        self.assertEqual(drawn, {"Áttu poka?", "Áttu vegabréf?"})
        builder.recent_answers = []
        self.assertIn("Áttu peysu?", {builder.generate(cur.by_id["attu"]).target for _ in range(40)}, "otherwise it is drawn like any other")

    def test_a_negated_sentence_does_not_hold_its_part(self):
        """#190 review: «Ég skil ekki.» says the opposite of «Ég skil.» and must not be the sentence its review asks."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        planner = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30), today=TODAY)
        planner.exposures["eg_skil_ekki"] = ["meaning"]
        self.assertEqual(planner.containing_items(cur.by_id["eg_skil"]), [])

    def test_the_repeat_after_the_model_only_teaches_for_the_first_asking(self):
        """#192: cloze and hinted recalls play the model answer twice (answer, then repeat), so five practices of one line were
        ten utterances. The repeat stays for the first asking of a line in a lesson; the later ones are one answer."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        item = next(i for i in cur.items if i.kind == "phrase" and i.word_count >= 3 and not i.target_m and not i.alternatives)
        builder = Builder(cur, Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"), random.Random(1))
        sc = Script(1, "t", "is", "en")
        answers = []
        for _ in range(3):
            ex = builder.recall(sc, item, "hinted")
            answers.append(sum(1 for g in sc.segments if g.exercise == ex.index and g.type == "answer"))
        self.assertEqual(answers, [2, 1, 1])
        self.assertEqual(builder.said[_norm_utterance(item.target)], 4, "every model answer is counted, the repeat included")

    def test_a_sentence_is_not_said_ten_times_and_a_recall_is_not_followed_by_its_own_pair(self):
        """#192: the same sentence was said up to 17 times in a lesson of the simulated course (the repeat counted), and a
        recall was followed directly by a mixed-review pair asking the same line in the same situation again (22-31 times in
        20 lessons). The repeat is dropped after two askings, a sentence past six utterances is practised in another sentence
        that holds it where one exists, and a pair avoids the item just practised."""
        from audiolesson.exercises import _norm_utterance as norm

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for seed in (None, 0):
            learner = LearnerState("is", "en", "A1")
            day, worst, adjacent = TODAY, 0, 0
            for n in range(1, 21):
                cfg = PlanConfig(minutes=30, new_items=5) if seed is None else PlanConfig(minutes=30, new_items=5, seed=seed)
                sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), cfg, today=day).build()
                said = Counter(norm(g.text) for g in sc.segments if g.type == "answer" and g.exercise is not None and sc.exercises[g.exercise].kind != "intro")
                said.update(norm(cur.by_id[e.item_ids[0]].target) for e in sc.exercises if e.kind == "intro" and e.item_ids and e.item_ids[0] in cur.by_id)
                worst = max(worst, max(said.values(), default=0))
                adjacent += sum(1 for a, b in zip(sc.exercises, sc.exercises[1:]) if a.kind == "recall" and b.kind == "connect" and a.item_ids[0] in b.item_ids)
                apply_to_learner(sc, learner, day)
                learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
                day += timedelta(days=1)
            self.assertLessEqual(worst, 15, (seed, worst))
            self.assertLessEqual(adjacent, 12, (seed, adjacent))  # 10 before #238: the pool is smaller once what the review asked today is out of it

    def test_a_part_is_a_vocab_item_whatever_its_length(self):
        """#190, the owner's decision: «fara á safnið» is a part though it has three words, so after the learner has said «Ég vil
        fara á safnið.» it is not asked alone; a phrase like «Hvenær?» is an utterance (scenes may repeat it)."""
        items = [
            {"id": "safnid", "kind": "vocab", "target": "fara á safnið", "meaning": "to go to the museum"},
            {"id": "vil_safnid", "kind": "phrase", "target": "Ég vil fara á safnið.", "meaning": "I want to go to the museum."},
        ] + [{"id": f"r{i}", "kind": "phrase", "target": f"Rifja {i}.", "meaning": f"Review {i}."} for i in range(6)]
        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})
        learner = LearnerState("is", "en", "A1")
        for i in ["safnid", "vil_safnid"] + [f"r{i}" for i in range(6)]:
            overdue = (TODAY - timedelta(days=9)).isoformat() if i == "safnid" else TODAY.isoformat()
            learner.items[i] = ItemState(due=overdue, successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=1, new_items=0), today=TODAY).build()
        asked = [e.item_ids[0] for e in sc.exercises if e.kind == "recall"]
        self.assertNotIn("safnid", asked, "a three-word part is not asked alone while its sentence can be said")
        self.assertGreaterEqual(asked.count("vil_safnid"), 2)

    def test_a_sentence_said_earlier_in_the_lesson_holds_its_part_though_not_yet_known(self):
        """#190 review: «Hvenær leggjum við af stað?» had no durable recall (it hesitated), so it held no part, though the
        learner had said it twice minutes before: «Hvenær?» was asked alone right after it."""
        items = [
            {"id": "bankinn", "kind": "vocab", "target": "bankinn", "meaning": "the bank"},
            {"id": "hvar_er_bankinn", "kind": "phrase", "target": "Hvar er bankinn?", "meaning": "Where is the bank?"},
        ]
        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})
        learner = LearnerState("is", "en", "A1")
        for i in ("bankinn", "hvar_er_bankinn"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=1, durable_successes=0, stage="meaning", recalled=1, last_outcome="hesitated")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=1, new_items=0), today=TODAY)
        self.assertEqual(planner.containing_items(cur.by_id["bankinn"]), [], "met, not known, not practised today")
        planner.exposures["hvar_er_bankinn"] = ["meaning"]
        self.assertEqual([i.id for i in planner.containing_items(cur.by_id["bankinn"])], ["hvar_er_bankinn"])

    def test_a_situation_is_narrated_in_full_twice_a_lesson_and_review_is_announced_once(self):
        for cur, sc in self._course():
            texts = {t for it in cur.items for t in ([it.situation] if it.situation else []) + list(it.situations)}
            narrated = Counter(s.text for s in sc.segments if s.type == "narrate" and s.text in texts)
            self.assertLessEqual(max(narrated.values(), default=0), 2, (sc.lesson_number, narrated.most_common(1)))
            quick = sum(1 for s in sc.segments if (s.text or "").startswith("Quick review"))
            self.assertLessEqual(quick, 1, sc.lesson_number)

    def test_an_item_with_no_slot_is_practised_in_a_phrase_that_holds_it(self):
        """No pattern takes «Hvenær?» (no tags), so its sentence is a known phrase that contains
        it; and the item stops there rather than going back to being said alone."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        learner.items["hvenaer_leggjum_vid_af_stad"] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="situation")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)
        self.assertIn("hvenaer_leggjum_vid_af_stad", [i.id for i in planner.containing_items(cur.by_id["hvenaer"])])
        self.assertEqual(planner.containing_items(cur.by_id["hvenaer_leggjum_vid_af_stad"]), [])


class VariantFillTests(unittest.TestCase):
    """§9 "Repetition": when a lesson has run out of other material, a close variant of something
    the learner knows (another case, another gender) comes in beyond the new-item limit."""

    @staticmethod
    def _cur(variant_extra=None):
        items = [
            {"id": "n0", "kind": "phrase", "target": "Ný setning núll.", "meaning": "New sentence zero."},
            {"id": "bankinn", "kind": "vocab", "target": "bankinn", "meaning": "the bank"},
            {"id": "bankanum", "kind": "vocab", "target": "bankanum", "meaning": "the bank (after 'to')", "variant_of": "bankinn", "meaning_spoken": "the bank, after to"},
        ] + [{"id": f"r{i}", "kind": "phrase", "target": f"Rifja {i}.", "meaning": f"Review {i}."} for i in range(6)]
        return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items + (variant_extra or [])})

    def _learner(self, cur, known=("bankinn",)):
        learner = LearnerState("is", "en", "A1")
        for i in [f"r{i}" for i in range(6)] + list(known):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        return learner

    def test_an_idle_lesson_takes_no_variant_as_filler(self):
        """#218 b1: a form comes in with a purpose, never to fill time (it used to: «bankanum», beyond the new-item limit)."""
        cur = self._cur()
        sc = Planner(cur, self._learner(cur), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_items=1, max_new_items=1, max_arcs=1), today=TODAY).build()
        self.assertEqual(sc.meta["variant_items"], [])
        self.assertEqual(sc.meta["new_items"], ["n0"])

    def test_a_variant_of_something_not_yet_known_waits(self):
        cur = self._cur()
        sc = Planner(cur, self._learner(cur, known=()), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_items=1, max_new_items=1, max_arcs=1), today=TODAY).build()
        self.assertEqual(sc.meta["variant_items"], [])
        self.assertNotIn("bankanum", sc.meta["new_items"])

    def test_however_many_variants_there_are_none_fills(self):
        extra = [{"id": f"v{i}", "kind": "vocab", "target": f"vara{i}", "meaning": f"variant {i}", "variant_of": "bankinn", "meaning_spoken": f"variant {i}"} for i in range(6)]
        cur = self._cur(extra)
        sc = Planner(cur, self._learner(cur), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_items=1, max_new_items=1, max_arcs=1), today=TODAY).build()
        self.assertEqual(sc.meta["variant_items"], [])

    def test_an_idle_lesson_takes_listening_not_a_variant(self):
        extra = [{"id": "u0", "kind": "phrase", "target": "Nýtt núll.", "meaning": "New zero."}]
        cur = self._cur(extra)
        raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": i.id, "kind": i.kind, "target": i.target, "meaning": i.meaning, **({"variant_of": i.variant_of, "meaning_spoken": i.meaning_spoken} if i.variant_of else {})} for i in cur.items],
               "dialogues": [{"id": "d1", "setting": "A test setting.", "requires": ["r0", "r1", "u0"], "turns": [
                   {"cue": "Say r0.", "expect": "r0", "partner": "Gott.", "partner_meaning": "Good."},
                   {"cue": "Say new.", "expect": "u0", "partner": "Já.", "partner_meaning": "Yes."},
                   {"cue": "Say r1.", "expect": "r1"}]}]}
        cur = curriculum_from_dict(raw)
        sc = Planner(cur, self._learner(cur), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_items=0, max_new_items=0, max_arcs=1), today=TODAY).build()
        self.assertEqual(sc.meta["dialogues_listened"], ["d1"], "the spare time is more to hear")
        self.assertEqual(sc.meta["variant_items"], [])
        self.assertNotIn("bankanum", sc.meta["exposures"])

    def test_a_variant_the_theme_does_not_want_stays_out_of_select_new(self):
        cur = self._cur()
        planner = Planner(cur, self._learner(cur), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_items=10), today=TODAY)
        self.assertEqual([i.id for i in planner.select_new(10)], ["n0"])
        # something pulls it: a phrase still to come lists it as a prerequisite (#202), so the course does not stall
        raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": "bankinn", "kind": "vocab", "target": "bankinn", "meaning": "the bank"},
                         {"id": "bankanum", "kind": "vocab", "target": "bankanum", "meaning": "the bank (to)", "variant_of": "bankinn", "meaning_spoken": "the bank, after to"},
                         {"id": "fer", "kind": "phrase", "target": "Ég fer í bankanum.", "meaning": "I go.", "prereqs": ["bankanum"]}]}
        pulled = curriculum_from_dict(raw)
        learner = LearnerState("is", "en", "A1")
        learner.items["bankinn"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        planner = Planner(pulled, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_items=3), today=TODAY)
        self.assertIn("bankanum", [i.id for i in planner.select_new(3)])

    def test_variant_of_is_validated(self):
        def items(**variant):
            return [
                {"id": "a", "kind": "vocab", "target": "a", "meaning": "A"},
                {"id": "b", "kind": "vocab", "target": "b", "meaning": "B", **variant},
            ]
        for bad in ({"variant_of": "b"}, {"variant_of": "missing"}, {"variant_of": "a", "target": "a"}):
            with self.assertRaises(CurriculumError, msg=str(bad)):
                curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items(**bad)})
        chained = items(variant_of="a") + [{"id": "c", "kind": "vocab", "target": "c", "meaning": "C", "variant_of": "b"}]
        with self.assertRaises(CurriculumError):
            curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": chained})
        curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items(variant_of="a")})

    def test_the_real_curriculum_has_variants_to_give(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        variants = [i for i in cur.items if i.variant_of]
        self.assertGreaterEqual(len(variants), 15)
        self.assertTrue({"dat_place", "adj_masc", "adj_fem", "small_count"} <= {t for i in variants for t in i.tags})


class FormFamilyCueTests(unittest.TestCase):
    """The owner, on «Say: good» → «gott» alone: a word's other forms (góður, góðan…) get no
    context. A variant is introduced as a form of one the learner has, and the recall after the
    introduction says what sentence the word is said in."""

    def _cur(self):
        return curriculum_from_dict({
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "gott", "kind": "vocab", "target": "gott", "meaning": "good", "context": "This is good."},
                {"id": "godur", "kind": "vocab", "target": "góður", "meaning": "good (of a man)", "meaning_spoken": "good, said of a man", "variant_of": "gott"},
            ],
        })

    def _builder(self, cur, met=()):
        from audiolesson.exercises import Builder
        learner = LearnerState("is", "en", "A1")
        for i in met:
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=1, stage="meaning")
        return Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)

    def _narration(self, sc, ex):
        return [s.text for s in sc.segments if s.exercise == ex.index and s.type == "narrate"]

    def test_a_recall_after_the_introduction_says_what_sentence_the_word_is_in(self):
        cur = self._cur()
        b = self._builder(cur)
        sc = Script(1, "t", "is", "en")
        said = self._narration(sc, b.recall(sc, cur.by_id["gott"], "meaning"))[0]
        self.assertTrue(said.lower().startswith(("say: good", "how do you say good")), said)
        self.assertIn("as in: This is good.", said)
        self.assertNotIn(".,", said)
        intro = self._narration(sc, b.intro(sc, cur.by_id["gott"]))
        self.assertFalse(any("as in" in t for t in intro), "the introduction keeps its own wording")

    def test_a_variant_is_introduced_as_a_form_of_one_the_learner_has(self):
        cur = self._cur()
        sc = Script(1, "t", "is", "en")
        ex = self._builder(cur, met=["gott"]).intro(sc, cur.by_id["godur"])
        said = [(s.type, s.text) for s in sc.segments if s.exercise == ex.index and s.type in ("narrate", "speak")]
        self.assertEqual(said[0], ("narrate", "You know this one:"))
        self.assertEqual(said[1], ("speak", "gott"))
        self.assertIn("another form", said[2][1])
        self.assertEqual(ex.kind, "intro")
        sc = Script(1, "t", "is", "en")
        plain = self._builder(cur).intro(sc, cur.by_id["godur"])
        self.assertTrue(self._narration(sc, plain)[0].startswith("Something new"), "base not met: the usual introduction")

    def test_context_is_for_phrases_and_vocab_only(self):
        with self.assertRaises(CurriculumError):
            curriculum_from_dict({
                "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
                "items": [{"id": "c", "kind": "construction", "target": "A {x}.", "meaning": "A {x}.", "slots": {"x": "t"}, "context": "Hi."}],
            })


class ConstructionFormTests(unittest.TestCase):
    """#171 A: a construction's authored negative and question forms. They are used in generated
    sentences only after the note that teaches them has been heard."""

    @staticmethod
    def _raw(**construction):
        return {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [
                {"id": "kalt", "kind": "vocab", "target": "kalt", "meaning": "cold", "tags": ["w"]},
                {"id": "heitt", "kind": "vocab", "target": "heitt", "meaning": "hot", "tags": ["w"]},
                {"id": "c", "kind": "construction", "target": "Það er {w}.", "meaning": "It's {w}.", "slots": {"w": "w"},
                 "negative": "Það er ekki {w}.", "negative_meaning": "It isn't {w}.",
                 "question": "Er {w}?", "question_meaning": "Is it {w}?", **construction},
            ],
            "notes": [
                {"id": "n_neg", "teaches": "negative", "text": "Put «ekki» after the verb."},
                {"id": "n_q", "teaches": "question", "text": "Put the verb first."},
            ],
        }

    def _builder(self, cur, taught=(), modelled=None):
        """``modelled``: the ``construction:form`` keys already shown (#211); by default every form of ``c`` the notes taught."""
        from audiolesson.exercises import Builder
        learner = LearnerState("is", "en", "A1")
        for i in ("kalt", "heitt", "c"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        for n in taught:
            learner.notes_heard[n] = 1
        learner.forms_modelled = {"c:negative", "c:question"} if modelled is None else set(modelled)
        return Builder(cur, Prompts.load("en"), Timing(level="A1"), learner, rng=random.Random(1))

    def test_the_forms_wait_for_their_note(self):
        cur = curriculum_from_dict(self._raw())
        c = cur.by_id["c"]
        b = self._builder(cur)
        self.assertEqual({b.generate(c, forms=True).form for _ in range(40)}, {None})
        self.assertIsNone(b.generate(c, form="negative"))
        b = self._builder(cur, taught=["n_neg"], modelled=[])
        self.assertEqual({b.generate(c, forms=True).form for _ in range(40)}, {None}, "the note is not the model (#211)")
        self.assertIsNone(b.generate(c, form="negative"))
        b = self._builder(cur, taught=["n_neg"])
        forms = []
        for _ in range(60):  # the way recombination counts what it generates
            form = b.generate(c, forms=True, prefer_unused=False).form
            b.form_counts[form or "plain"] = b.form_counts.get(form or "plain", 0) + 1
            forms.append(form)
        self.assertEqual(set(forms), {None, "negative"})
        self.assertGreaterEqual(forms.count(None), 40, "the plain sentence stays the larger share")
        self.assertLessEqual(forms.count("negative"), 20)
        self.assertEqual(b.generate(c, form="negative").target.split()[:3], ["Það", "er", "ekki"])
        self.assertIsNone(b.generate(c, form="question"), "the question note hasn't been heard")
        b = self._builder(cur, taught=["n_neg", "n_q"])
        gen = b.generate(c, form="question")
        self.assertTrue(gen.target.endswith("?") and gen.meaning.startswith("Is it"), (gen.target, gen.meaning))
        self.assertNotEqual(gen.key, b.generate(c, fixed=gen.fills).key, "a form is a different sentence")

    def test_a_note_played_this_lesson_counts(self):
        cur = curriculum_from_dict(self._raw())
        b = self._builder(cur)
        b.notes_taught.add("n_neg")
        self.assertEqual(b.forms_taught(), {"negative"})

    def test_the_negative_note_comes_first_and_one_a_lesson(self):
        cur = curriculum_from_dict(self._raw())
        learner = self._builder(cur).learner
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=1), today=TODAY)
        self.assertIsNone(planner.forms_note_due(), "one known construction is not two")
        raw = self._raw()
        raw["items"].append({"id": "c2", "kind": "construction", "target": "Það er {w} núna.", "meaning": "It's {w} now.", "slots": {"w": "w"},
                             "negative": "Það er ekki {w} núna.", "negative_meaning": "It isn't {w} now."})
        cur = curriculum_from_dict(raw)
        learner = self._builder(cur).learner
        learner.items["c2"] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=1), today=TODAY)
        self.assertEqual(planner.forms_note_due().id, "n_neg")
        learner.notes_heard["n_neg"] = 1
        self.assertIsNone(planner.forms_note_due(), "only one construction has a question form")

    def test_validation_of_forms(self):
        def bad(**change):
            with self.assertRaises(CurriculumError, msg=str(change)):
                curriculum_from_dict(self._raw(**change))
        bad(negative="Það er nei {w}.")  # an Icelandic negative contains «ekki»
        bad(question="Er {w}.")  # a question ends with «?»
        bad(negative="Það er ekki {x}.")  # the construction's slots
        bad(negative_meaning="It isn't.")  # the meaning's slots
        bad(negative_meaning="")  # a form and its meaning go together
        raw = self._raw()
        raw["notes"].append({"id": "n2", "teaches": "negative", "text": "again"})
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)
        raw = self._raw()
        raw["notes"][0]["milestone"] = True
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)
        raw = self._raw()
        raw["items"][0]["negative"] = "kalt ekki"
        raw["items"][0]["negative_meaning"] = "not cold"
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)  # forms are for constructions

    def test_every_authored_form_of_the_real_curriculum_resolves_in_both_languages(self):
        for lang in ("en", "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            authored = [c for c in cur.items if c.kind == "construction" and c.forms]
            self.assertGreaterEqual(len(authored), 15)
            for c in authored:
                fills = {slot: cur.items_with_tag(tag)[0] for slot, tag in c.slots.items()}
                for form in c.forms:
                    target, meaning = cur.resolve_slots(c, fills, form=form)
                    self.assertNotIn("{", target + meaning, (c.id, form, target, meaning))
                    self.assertNotEqual(meaning, cur.resolve_slots(c, fills)[1], (c.id, form))

    # ---- #211: a form is modelled before it is asked ----

    def test_a_form_is_offered_only_for_a_known_construction_whose_form_was_modelled(self):
        cur = curriculum_from_dict(self._raw())
        c = cur.by_id["c"]
        taught = ["n_neg", "n_q"]
        for modelled, expected in (([], {None}), (["c:negative"], {None, "negative"}), (["c:negative", "c:question"], {None, "negative", "question"})):
            b = self._builder(cur, taught=taught, modelled=modelled)
            seen = set()
            for _ in range(120):
                form = b.generate(c, forms=True, prefer_unused=False).form
                b.form_counts[form or "plain"] = b.form_counts.get(form or "plain", 0) + 1
                seen.add(form)
            self.assertEqual(seen, expected, modelled)
        b = self._builder(cur, taught=taught, modelled=["c:negative"])
        self.assertIsNone(b.generate(c, form="question"))
        b.learner.items["c"] = ItemState(due=TODAY.isoformat(), successes=1, durable_successes=1, stage="meaning")  # introduced, not yet known
        self.assertEqual({b.generate(c, forms=True).form for _ in range(40)}, {None}, "a construction not known yet gets no form sentence")
        self.assertIsNone(b.generate(c, form="negative"))

    def test_a_word_s_sentence_takes_a_form_only_through_a_known_modelled_frame(self):
        cur = curriculum_from_dict(self._raw())
        kalt = cur.by_id["kalt"]
        b = self._builder(cur, taught=["n_neg"], modelled=[])
        self.assertEqual({b.generate_with(kalt, forms=True).form for _ in range(40)}, {None})
        b = self._builder(cur, taught=["n_neg"], modelled=["c:negative"])
        seen = set()
        for _ in range(60):  # the way recombination counts what it generates
            form = b.generate_with(kalt, forms=True, ceiling=False).form
            b.form_counts[form or "plain"] = b.form_counts.get(form or "plain", 0) + 1
            seen.add(form)
        self.assertEqual(seen, {None, "negative"})
        self.assertEqual(b.recombine_status(kalt), "novel")

    def test_the_model_shows_the_plain_sentence_then_the_form_then_another_filler_heard_and_asked(self):
        cur = curriculum_from_dict(self._raw())
        c = cur.by_id["c"]
        b = self._builder(cur, taught=["n_neg", "n_q"], modelled=[])
        sc = Script(1, "t", "is", "en")
        ex = b.model_form(sc, c, "question")
        self.assertEqual((ex.kind, ex.stage), ("model", "form"))
        self.assertEqual(b.models_now, ["c:question"])
        self.assertTrue(b.form_modelled(c, "question") and not b.form_modelled(c, "negative"))
        segs = [(g.type, g.text) for g in sc.segments if g.exercise == ex.index and g.type in ("narrate", "speak", "answer")]
        texts = [t for _, t in segs]
        prompts = Prompts.load("en")
        order = [texts.index(prompts.get("form_model_known")), texts.index(prompts.get("form_model_question")), texts.index(prompts.get("form_model_again"))]
        self.assertEqual(order, sorted(order))
        spoken = [t for kind, t in segs if kind == "speak"]
        self.assertTrue(spoken[0].startswith("Það er ") and not spoken[0].endswith("?"), "the plain sentence first")
        self.assertTrue(spoken[1].endswith("?"), "then the same sentence as a question")
        answers = [t for kind, t in segs if kind == "answer"]
        self.assertEqual(len(answers), 1)
        self.assertTrue(answers[0].endswith("?"))
        self.assertNotEqual(answers[0], spoken[1], "asked with another filler than the one heard first")
        self.assertNotIn(answers[0], spoken, "…and not spoken before it is asked: the form is first produced there")
        self.assertIsNone(b.generate(c, form="negative"), "only the modelled form opens")
        self.assertIsNotNone(b.generate(c, form="question"))

    def test_older_learner_files_are_seeded_from_what_was_heard_and_the_state_round_trips(self):
        from audiolesson.exercises import Builder

        cur = curriculum_from_dict(self._raw())
        learner = LearnerState("is", "en", "A1")
        self.assertIsNone(learner.forms_modelled)
        learner.heard_utterances.update({"það er ekki kalt", "er heitt"})
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
        self.assertEqual(b.forms_modelled, {"c:negative", "c:question"}, "a form sentence already heard counts as modelled")
        learner.heard_utterances = {"það er kalt"}
        self.assertEqual(Builder(cur, Prompts.load("en"), Timing(level="A1"), learner).forms_modelled, set(), "a plain sentence does not")
        learner.forms_modelled = {"c:negative"}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "l.json"
            learner.save(path)
            self.assertEqual(LearnerState.load(path).forms_modelled, {"c:negative"})
            raw = json.loads(path.read_text())
            raw.pop("forms_modelled")
            path.write_text(json.dumps(raw))
            self.assertIsNone(LearnerState.load(path).forms_modelled, "a file from before #211: seeded when the next lesson is built")

    def test_a_course_models_each_form_once_before_its_first_sentence(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        modelled_at: dict[str, int] = {}
        known_at_model: list[bool] = []
        for n in range(1, 21):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=5), today=day).build()
            before = set(learner.forms_modelled or ())
            now = sc.meta["forms_modelled_now"]
            self.assertLessEqual(len(now), PlanConfig().forms_models, (n, now))
            for key in now:
                self.assertNotIn(key, modelled_at, f"{key} was modelled twice")
                modelled_at[key] = n
                known_at_model.append(learner.knows(key.split(":")[0]))
            models = {k: next(e.index for e in sc.exercises if e.kind == "model" and k.split(":")[0] in e.item_ids) for k in now}
            for e in sc.exercises:
                if e.kind != "generative":
                    continue
                for cid in e.item_ids[:3]:
                    c = cur.by_id.get(cid)
                    if not (c and c.kind == "construction" and c.forms):
                        continue
                    for form in c.forms:
                        template = c.negative if form == "negative" else c.question
                        rx = re.compile("^" + re.sub(r"\\\{[^}]*\\\}", ".+", re.escape(template)) + "$")
                        if rx.match(e.label.split(": ", 1)[1]):
                            key = f"{cid}:{form}"
                            self.assertTrue(key in before or (key in models and models[key] < e.index), (n, key, e.label))
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertTrue(modelled_at, "the course models forms")
        self.assertTrue(all(known_at_model), "only known constructions are modelled")
        self.assertEqual(set(modelled_at), set(learner.forms_modelled))

    def test_a_course_teaches_the_forms_and_uses_them_only_after(self):
        import re as _re

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        # a regex per template: its slots match any words
        patterns: dict[str, list] = {"negative": [], "question": []}
        for c in cur.items:
            if c.kind != "construction":
                continue
            for form in c.forms:
                template = c.negative if form == "negative" else c.question
                patterns[form].append((c.id, _re.compile("^" + _re.sub(r"\\\{[^}]*\\\}", ".+", _re.escape(template)) + "$")))
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        taught: set[str] = set()
        used_before, first_taught, share_rows = 0, {}, []
        for n in range(1, 21):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=5), today=day).build()
            sentences = [(e.label.split(": ", 1)[1], [i for i in e.item_ids if cur.by_id[i].kind == "construction"]) for e in sc.exercises if e.kind == "generative" and ": " in e.label]
            # a form sentence matches the template of a construction in that exercise: «Viltu sofa?» is a plain sentence
            # of «Viltu {inf}?», not the question form of «Ég vil {inf}.»
            by_form = {f: sum(1 for t, cs in sentences if any(p.match(t) for cid, p in pats if cid in cs)) for f, pats in patterns.items()}
            by_form["plain"] = len(sentences) - by_form["negative"] - by_form["question"]
            share_rows.append((n, len(sentences), by_form, set(sc.meta["forms_taught"]), set(taught)))
            if not taught and not sc.meta["forms_taught"]:
                used_before += by_form["negative"] + by_form["question"]  # no form before its note
            for f in sc.meta["forms_taught"]:
                first_taught.setdefault(f, n)
            taught |= set(sc.meta["forms_taught"])
            apply_to_learner(sc, learner, day)
            new = sc.meta["new_items"]
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=new)
            day += timedelta(days=1)
        self.assertEqual(used_before, 0, "no form before its note")
        self.assertEqual(set(first_taught), {"negative", "question"})
        self.assertLess(first_taught["negative"], first_taught["question"], "the negative first, the question in a later lesson")
        after = [r for r in share_rows if r[0] >= first_taught["negative"]]
        total = sum(r[1] for r in after)
        self.assertGreater(total - sum(r[2]["plain"] for r in after), 40, "once taught, the forms are a real part of the supply")
        # the newest form must not crowd out the plain sentences (review of #172)
        self.assertGreaterEqual(sum(r[2]["plain"] for r in after) / total, 0.5, [r[:3] for r in after])
        for form in ("negative", "question"):
            self.assertLessEqual(sum(r[2][form] for r in after) / total, 0.3, form)
        for n, count, by_form, now, before in share_rows:
            if count >= 10:
                self.assertGreaterEqual(by_form["plain"] / count, 0.4, (n, by_form))
                for form in ("negative", "question"):
                    self.assertLessEqual(by_form[form] / count, 0.4, (n, form, by_form))
            for form in now:  # the lesson that teaches a form: its practice and a couple more, not a drill
                self.assertLessEqual(by_form[form], 5, (n, form, by_form))


class CheapConstructionTests(unittest.TestCase):
    """#171 B: a construction whose every slot already has two known fillers adds sentences at once, so
    it gets a place among a lesson's new items (never a trip item's) and, when a lesson has time left,
    comes in beyond the new-item limit."""

    @staticmethod
    def _cur(extra=()):
        words = [{"id": f"w{i}", "kind": "vocab", "target": f"orð{i}", "meaning": f"word {i}", "tags": ["t"]} for i in range(3)]
        items = words + [
            {"id": "u0", "kind": "vocab", "target": "uorð0", "meaning": "u word 0", "tags": ["u"]},
            {"id": "n0", "kind": "phrase", "target": "Ný setning núll.", "meaning": "New sentence zero."},
            {"id": "n1", "kind": "phrase", "target": "Ný setning eitt.", "meaning": "New sentence one."},
            {"id": "c_big", "kind": "construction", "target": "Stórt {x}.", "meaning": "Big {x}.", "slots": {"x": "t"}, "prereqs": ["w0"]},
            {"id": "c_small", "kind": "construction", "target": "Lítið {y}.", "meaning": "Small {y}.", "slots": {"y": "u"}, "prereqs": ["w0"]},
        ] + list(extra)
        return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})

    def _learner(self, known):
        learner = LearnerState("is", "en", "A1")
        for i in known:
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        return learner

    def _planner(self, cur, learner, **cfg):
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, **cfg), today=TODAY)

    def test_a_construction_is_cheap_when_every_slot_has_known_fillers(self):
        cur = self._cur()
        p = self._planner(cur, self._learner(["w0", "w1", "w2", "u0"]))
        self.assertEqual(p.cheap_construction(set()).id, "c_big", "«c_small» has one known filler only")
        p = self._planner(cur, self._learner(["w0", "w1"]))
        self.assertEqual(p.cheap_construction(set()).id, "c_big")
        self.assertIsNone(self._planner(cur, self._learner(["w0"])).cheap_construction(set()))
        # #180 (b): a prerequisite that is only a filler of the construction's own slot is covered by the slot's known fillers
        self.assertEqual(self._planner(cur, self._learner(["w1", "w2"])).cheap_construction(set()).id, "c_big", "its prerequisite w0 is a filler of its slot")
        gated = self._cur([{"id": "c_gated", "kind": "construction", "target": "Hlið {x}.", "meaning": "Side {x}.", "slots": {"x": "t"}, "prereqs": ["n0"]}])
        self.assertEqual(self._planner(gated, self._learner(["w0", "w1", "w2"])).cheap_construction(set(), only={"c_gated"}), None, "a prerequisite that is no filler of its slot still has to be known")
        self.assertEqual(self._planner(gated, self._learner(["w0", "w1", "w2", "n0"])).cheap_construction(set(), only={"c_gated"}).id, "c_gated")
        learner = self._learner(["w0", "w1", "w2"])
        learner.items["c_big"] = ItemState(due=TODAY.isoformat(), stage="meaning")
        self.assertIsNone(self._planner(cur, learner).cheap_construction(set()), "already met")

    def test_a_cheap_construction_takes_the_place_of_a_non_trip_item_never_a_trip_item(self):
        cur = self._cur()
        learner = self._learner(["w0", "w1", "w2"])
        chosen = self._planner(cur, learner).select_new(2, cheap=True)
        self.assertIn("c_big", [i.id for i in chosen])
        self.assertEqual(len(chosen), 2)
        plain = self._planner(cur, learner).select_new(2)
        self.assertNotIn("c_big", [i.id for i in plain], "only the lesson's own selection asks for one")
        trip = self._planner(cur, learner, priority=[i.id for i in plain])
        self.assertEqual([i.id for i in trip.select_new(2, cheap=True)], [i.id for i in plain], "a trip item is never displaced")

    def test_a_cheap_trip_construction_moves_to_the_front_of_the_trip_order(self):
        """Review of #174: with a trip ordering every new item is a trip item, so no place opens for a cheap
        construction. A trip construction the learner can already fill moves to the front of the
        remaining trip order instead: nothing is displaced, only the order changes."""
        cur = self._cur()
        learner = self._learner(["w0", "w1", "w2"])
        trip = ["n0", "n1", "u0", "c_big", "c_small"]
        planner = self._planner(cur, learner, priority=trip)
        self.assertEqual([i.id for i in planner.select_new(2)], ["n0", "n1"], "without it: the trip order")
        chosen = [i.id for i in planner.select_new(2, cheap=True)]
        self.assertEqual(chosen, ["c_big", "n0"])
        self.assertEqual(planner.cheap_placed, ["c_big"])
        self.assertTrue(set(chosen) <= set(trip), "every item is still a trip item")
        # not cheap (one known filler of «c_small»): the order is the trip's own
        fresh = self._planner(cur, self._learner(["w0"]), priority=trip)
        self.assertEqual([i.id for i in fresh.select_new(2, cheap=True)], ["n0", "n1"])
        # …and a cheap construction that isn't a trip item is not promoted (it takes a non-trip place, none here)
        only = self._planner(cur, learner, priority=["n0", "n1"])
        self.assertEqual([i.id for i in only.select_new(2, cheap=True)], ["n0", "n1"])

    def test_a_cheap_refresh_construction_outside_the_trip_list_goes_first(self):
        """#180 (owner's option 1 on #176): a construction with ``refresh`` counts as trip-serving. Cheap and not
        a trip item, it still goes to the front of the trip order, takes one new-item place, and no trip item
        is dropped beyond that place: the trip order behind it shifts by one."""
        cur = self._cur()
        cur.by_id["c_big"].refresh = 3
        learner = self._learner(["w0", "w1", "w2"])
        trip = ["n0", "n1", "u0"]
        planner = self._planner(cur, learner, priority=trip)
        chosen = [i.id for i in planner.select_new(2, cheap=True)]
        self.assertEqual(chosen, ["c_big", "n0"], "ahead of the trip items, one place")
        self.assertEqual(planner.cheap_placed, ["c_big"])
        self.assertEqual(len(chosen), len(set(chosen)))
        self.assertEqual([i.id for i in planner.select_new(2)], ["n0", "n1"], "without the promotion: the trip order")
        again = self._planner(cur, learner, priority=trip).select_new(2, cheap=True)
        self.assertEqual([i.id for i in again][1:], ["n0"], "the trip item behind it is the next one: only n1 waits a lesson")
        # not cheap (its prerequisite is no filler of its slot and isn't known): never promoted
        cur.by_id["c_big"].prereqs = ["n0"]
        self.assertEqual([i.id for i in self._planner(cur, self._learner(["w0", "w1", "w2"]), priority=trip).select_new(2, cheap=True)], ["n0", "n1"])
        cur.by_id["c_big"].prereqs = ["w0"]
        # a construction without ``refresh`` that is not a trip item stays out
        cur2 = self._cur()
        self.assertEqual([i.id for i in self._planner(cur2, learner, priority=trip).select_new(2, cheap=True)], ["n0", "n1"])

    def test_an_idle_lesson_takes_a_cheap_construction_beyond_its_limit(self):
        cur = self._cur()
        learner = self._learner(["w0", "w1", "w2"])
        sc = self._planner(cur, learner, new_items=1, max_new_items=1, max_arcs=1, cheap_place=False).build()
        self.assertEqual(sc.meta["cheap_constructions"], ["c_big"])
        self.assertIn("c_big", sc.meta["new_items"])
        sc = self._planner(cur, self._learner(["w0", "w1", "w2"]), new_items=1, max_new_items=1, max_arcs=1, cheap_place=False, max_cheap_extra=0).build()
        self.assertEqual(sc.meta["cheap_constructions"], [])

    def test_the_patterns_a_course_has_met_come_sooner(self):
        """On the real curriculum, without a trip ordering: the learner has met more constructions
        by lesson 12, and the lessons then have more to practise (the length over lessons 9 to 16; a
        single lesson's length varies with what the course happens to have met)."""
        def course(**cfg):
            cur = load_curriculum(ROOT / "curricula" / "is-en")
            learner = LearnerState("is", "en", "A1")
            day = TODAY
            lengths = []
            for n in range(1, 17):
                sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=5, **cfg), today=day).build()
                if n >= 9:
                    lengths.append(sc.total_duration)
                if n == 12:
                    met_by_12 = sum(1 for c in cur.items if c.kind == "construction" and learner.has_met(c.id))
                apply_to_learner(sc, learner, day)
                learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
                day += timedelta(days=1)
            return met_by_12, sum(lengths)
        with_met, with_len = course()
        without_met, without_len = course(cheap_place=False, max_cheap_extra=0)
        self.assertGreaterEqual(with_met, without_met + 2, (with_met, without_met))
        # not shorter by more than 2%: which parts wait for their frame (#206) moves the sum by about 1% either way
        self.assertGreaterEqual(with_len, without_len * 0.98, (with_len, without_len))


class ColourFormTests(unittest.TestCase):
    """#158: «Ég vil {colour}.» filled its slot with the colour names as stored (masculine nominative) and generated
    «Ég vil blár.»; «vilja» takes the accusative. Slot fills are verbatim targets, with no morphology engine, so the
    construction left the course. The colour words wait for a scene that uses them, and the mechanism that gives a
    colour the form its noun's gender takes (`gender_forms` and the `fills` agreement: «Bíllinn er blár.», «Bókin er
    blá.», «Húsið er blátt.») is ready for it."""

    FORMS = {  # nominative: masculine, feminine, neuter
        "raudur": ("rauður", "rauð", "rautt"), "blar": ("blár", "blá", "blátt"), "graenn": ("grænn", "græn", "grænt"),
        "gulur": ("gulur", "gul", "gult"), "svartur": ("svartur", "svört", "svart"), "hvitur": ("hvítur", "hvít", "hvítt"),
        "grar": ("grár", "grá", "grátt"), "brunn": ("brúnn", "brún", "brúnt"),
    }
    GENDER = {"masc": 0, "fem": 1, "neut": 2}

    def test_a_colour_slot_is_always_agreed_with_a_noun(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertEqual({i.id for i in cur.items_with_tag("colour")}, set(self.FORMS), "the colour words themselves are still taught")
        for c in cur.items:
            if c.kind == "construction" and "colour" in c.slots.values():
                slot = next(s for s, tag in c.slots.items() if tag == "colour")
                rule = c.agreement.get(slot)
                self.assertTrue(rule and rule.get("fills"), f"{c.id}: a colour needs the form its noun's gender takes, not the stored masculine one")

    def test_every_colour_carries_its_feminine_and_neuter_forms(self):
        """The colour words wait for a scene that uses them, with the forms their noun's gender takes ready (#158)."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for col in cur.items_with_tag("colour"):
            masc, fem, neut = self.FORMS[col.id]
            self.assertEqual((col.target, col.gender_forms), (masc, {"fem": fem, "neut": neut}), col.id)

    def test_a_fill_without_forms_for_a_noun_gender_fails_validation(self):
        from audiolesson.content import CurriculumError

        def raw(forms):
            return {
                "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
                "items": [
                    {"id": "bil", "kind": "vocab", "target": "bíllinn", "meaning": "the car", "tags": ["n"], "gender": "masc"},
                    {"id": "bok", "kind": "vocab", "target": "bókin", "meaning": "the book", "tags": ["n"], "gender": "fem"},
                    dict({"id": "bla", "kind": "vocab", "target": "blár", "meaning": "blue", "tags": ["c"]}, **forms),
                    {"id": "is", "kind": "construction", "target": "{n} er {c}.", "meaning": "{n} is {c}.", "slots": {"n": "n", "c": "c"},
                     "agreement": {"c": {"from": "n", "fills": True}}},
                ],
            }

        cur = curriculum_from_dict(raw({"gender_forms": {"fem": "blá"}}))
        self.assertEqual(cur.resolve_slots(cur.by_id["is"], {"n": cur.by_id["bok"], "c": cur.by_id["bla"]})[0], "Bókin er blá.")
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw({}))


class ThemeExchangeTests(unittest.TestCase):
    """#149 1b-ii: a lesson consolidates one theme, a scene of a trip as a short exchange: its exchange is played twice,
    early with the partner's lines translated, late with only the partner's line as the cue; a turn whose items the
    learner lacks is tried; plan.json names the theme and level."""

    @staticmethod
    def _world():
        from audiolesson.cando import load_cando
        from audiolesson.themes import load_themes, scenario_order

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", cur)
        themes = load_themes(ROOT / "curricula" / "is-en", cur, scenarios)
        return cur, scenarios, themes, scenario_order

    @staticmethod
    def _learner(ids):
        learner = LearnerState("is", "en", "A1")
        for i in ids:
            learner.items[i] = ItemState(due=(TODAY + timedelta(days=3)).isoformat(), successes=2, durable_successes=2, stage="meaning",
                                         recalled=2, last_outcome="recalled", interval_days=3, last_practiced=(TODAY - timedelta(days=1)).isoformat())
        return learner

    def _planner(self, learner, themes, order, **cfg):
        cur = self._cur
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=0, themes=themes, theme_scenarios=order, **cfg), today=TODAY)

    def setUp(self):
        self._cur, self._scenarios, self._themes, so = self._world()
        self._order = so(self._scenarios)
        self._supermarket = next(t for t in self._themes if t.id == "supermarket")
        self._known = list(self._supermarket.levels[0].items)
        self._rest = [i.id for i in sorted(self._cur.items, key=lambda i: i.order)[:120] if i.id not in self._known]

    def test_the_themes_load_and_validate_against_the_curriculum(self):
        from audiolesson.themes import level_dialogue

        self.assertGreaterEqual(len(self._themes), 2)
        scenario_ids = {s.id for s in self._scenarios}
        for t in self._themes:
            self.assertIn(t.scenario, scenario_ids)
            for n, lv in enumerate(t.levels):
                self.assertTrue(all(i in self._cur.by_id for i in lv.items))
                dlg = level_dialogue(t, n)
                self.assertEqual(len(dlg.turns), sum(1 for x in lv.turns if x.who == "you"))

    def test_a_level_becomes_a_dialogue_with_openers_and_replies(self):
        from audiolesson.themes import level_dialogue

        dlg = level_dialogue(self._supermarket, 0)
        first = dlg.turns[0]
        self.assertIsNone(first.opener, "the level starts with the learner")
        self.assertTrue(first.partner and first.partner_meaning)
        cafe = next(t for t in self._themes if t.id == "cafe")
        opening = level_dialogue(cafe, 0).turns[0]
        self.assertTrue(opening.opener and opening.opener_meaning, "a partner line first is the opener")
        self.assertEqual(opening.expect_text, "Ég ætla að fá kaffi.")

    def test_the_boosted_scenario_comes_first_and_the_lowest_level_wins(self):
        everything = list(self._cur.by_id)
        learner = self._learner(everything)
        cafe_first = self._planner(learner, self._themes, ["A4", "A3"]).pick_theme()
        self.assertEqual((cafe_first[0].id, cafe_first[1]), ("cafe", 0))
        market_first = self._planner(learner, self._themes, ["A3", "A4"]).pick_theme()
        self.assertEqual(market_first[0].id, "supermarket")
        learner.themes_done = {"supermarket": 1, "cafe": 0, "museum": 1, "tour": 2}
        later = self._planner(learner, self._themes, ["A3", "A4", "B1", "B2"]).pick_theme()
        self.assertEqual((later[0].id, later[1]), ("cafe", 0), "the lowest level not played wins over a boosted theme's next level")
        learner.themes_done = {t.id: len(t.levels) for t in self._themes}
        # premise changed (#149 step 1): with every level played the lesson still has a theme, the last level again
        again = self._planner(learner, self._themes, self._order).pick_theme()
        self.assertIsNotNone(again, "every level played: a played level comes again")
        self.assertEqual(again[1], len(again[0].levels) - 1)

    def test_a_theme_waits_until_the_learner_can_say_most_of_it(self):
        learner = self._learner([i for i in self._known if i not in ("skyr", "attu", "gjordu_svo_vel")])
        planner = self._planner(learner, [self._supermarket], ["A3"])
        self.assertIsNone(planner.pick_theme(), "two of four turns lack an item")
        learner = self._learner([i for i in self._known if i != "gjordu_svo_vel"])
        picked = self._planner(learner, [self._supermarket], ["A3"]).pick_theme()
        self.assertEqual((picked[0].id, picked[1], picked[2]), ("supermarket", 0, {3}), "one turn in four is tried")

    def test_the_exchange_is_played_twice_early_translated_and_late_without_the_translation(self):
        learner = self._learner(self._known + self._rest)
        planner = self._planner(learner, [self._supermarket], ["A3"])
        sc = planner.build()
        plays = [e for e in sc.exercises if e.label.startswith("dialogue: theme:supermarket:1")]
        self.assertEqual(len(plays), 2)
        total = sc.total_duration
        self.assertLess(plays[0].start, 0.3 * 30 * 60, "early in a 30-minute lesson (which, with no filler variants, may end short in a thin course)")
        self.assertGreater(plays[1].start, 0.7 * total)
        segs = lambda e: [g for g in sc.segments if g.exercise == e.index]
        meaning = "Yes, it's over there, in the fridge."
        turn = self._supermarket.levels[0].turns[1]  # the early play says a variant of this line (#134), translated
        self.assertTrue(any(g.text == v["meaning"] for v in turn.variants for g in segs(plays[0])), "early: the partner's line is translated")
        self.assertFalse(any(g.text == meaning for g in segs(plays[1])), "later: only the translation fades")
        cue = self._supermarket.levels[0].turns[2].cue
        self.assertTrue(all(cue in [g.text for g in segs(e) if g.type == "narrate"] for e in plays), "the cue plays in both")
        asked_first = [g for g in segs(plays[0]) if g.type == "pause" and g.role == "answer"]
        self.assertEqual(len(asked_first), 4)
        self.assertEqual(sc.meta["theme"], {"id": "supermarket", "scenario": "A3", "level": 1, "plays": 2, "lines": sc.meta["theme"]["lines"], "replay": False, "heard": sc.meta["theme"]["heard"]})
        self.assertTrue(sc.meta["theme"]["heard"], "the assisted play's variants were heard with their meaning")
        self.assertEqual(len(sc.meta["theme"]["lines"]), 2)

    def test_every_learner_turn_keeps_its_cue_in_the_late_play_and_in_a_replay(self):
        """#210 (it was #186 review): the cue is the intent, so it plays every time; before, 13 of 24 turns lost it in the
        late play and a replay played none."""
        learner = self._learner(self._known + self._rest + ["eg_er_ad_leita_ad_thing", "hvad_er_thetta_mikid_samtals"])
        planner = self._planner(learner, [self._supermarket], ["A3"])
        planner.learner.themes_done = {"supermarket": 1}
        sc = planner.build()
        early, late = [e for e in sc.exercises if e.label.startswith("dialogue: theme:supermarket:2")]
        said = lambda e: [g.text for g in sc.segments if g.exercise == e.index and g.type == "narrate"]
        for cue in ("You're just looking.", "At the till, ask how much it is in total.", "No need."):
            self.assertIn(cue, said(early))
            self.assertIn(cue, said(late))
        replay = self._learner(self._known + self._rest)
        replay.themes_done = {"supermarket": 1}
        replay.themes_last = {}
        sc = self._planner(replay, [self._supermarket], ["A3"]).build()
        self.assertTrue(sc.meta["theme"]["replay"])
        for e in [e for e in sc.exercises if e.label.startswith("dialogue: theme:supermarket:1")]:
            self.assertIn("Thank him.", [g.text for g in sc.segments if g.exercise == e.index and g.type == "narrate"])

    def test_no_turn_of_a_continuing_exchange_drops_its_cue_in_any_play(self):
        """#230 review (owner): the partner's line never decides the reply, so every learner turn of every theme level keeps its cue,
        the second play and a replay included, the tour's «Greet her back.» too."""
        from audiolesson.themes import level_dialogue

        planner = self._planner(self._learner(self._known + self._rest + ["godan_daginn"]), self._themes, self._order)
        for theme in self._themes:
            for n, level in enumerate(theme.levels):
                dlg = level_dialogue(theme, n)
                for translate in (True, False):
                    sc = Script(1, "t", "is", "en")
                    planner.builder.dialogue(sc, dlg, translate=translate)
                    narrated = [g.text for g in sc.segments if g.type == "narrate"]
                    for turn in dlg.turns:
                        self.assertIn(turn.cue, narrated, (theme.id, n + 1, translate))
        self.assertIn("Greet her back.", [t.cue for t in level_dialogue(next(t for t in self._themes if t.id == "tour"), 0).turns])

    def test_a_scene_line_on_a_partner_turn_is_narrated_before_its_line_in_every_play(self):
        from audiolesson.themes import Level, Theme, Turn, level_dialogue

        dlg = level_dialogue(self._supermarket, 0)
        self.assertEqual(dlg.turns[1].partner_scene, "At the till.", "«Viltu poka?» is the partner reply of «Takk.»")
        self.assertEqual(dlg.turns[1].scene, "")
        ja = level_dialogue(self._supermarket, 0, known_lang="ja")
        self.assertTrue(ja.turns[1].partner_scene and ja.turns[1].partner_scene != "At the till.")
        theme = Theme(id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=[
            Turn(who="you", say="Hæ.", cue="Say hi.", items=["hae"]),
            Turn(who="partner", say="Halló.", meaning="Hello.", scene="Later."),
            Turn(who="you", say="Bless.", cue="Say bye.", items=["bless"]),
        ])])
        self.assertEqual(level_dialogue(theme, 0).turns[0].partner_scene, "Later.")
        opener = Theme(id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=[
            Turn(who="partner", say="Hæ.", meaning="Hi.", scene="At the door."),
            Turn(who="you", say="Hæ.", cue="Say hi.", items=["hae"]),
        ])])
        self.assertEqual(level_dialogue(opener, 0).turns[0].scene, "At the door.")
        learner = self._learner(self._known + self._rest)
        sc = self._planner(learner, [self._supermarket], ["A3"]).build()
        for e in [e for e in sc.exercises if e.label.startswith("dialogue: theme:supermarket:1")]:
            seq = [g.text for g in sc.segments if g.exercise == e.index and g.type in ("narrate", "speak")]
            i = seq.index("At the till.")
            self.assertTrue(seq[i + 1].startswith(("Viltu", "Þarftu")) or "poka" in seq[i + 1], seq[i : i + 2])

    def test_a_theme_validation_fails_on_an_empty_cue_or_a_misplaced_flag(self):
        from audiolesson.themes import Level, Theme, Turn, _check
        from audiolesson.content import CurriculumError

        def check(*turns):
            _check(Theme(id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=list(turns))]))

        you = lambda **kw: Turn(**{"who": "you", "say": "Hæ.", "cue": "Say hi.", "items": ["hae"], **kw})
        check(you())
        for bad in (you(cue=""), you(cue="  ")):
            with self.assertRaises(CurriculumError):
                check(bad)
        with self.assertRaises(CurriculumError):
            check(you(scene="At the till."))

    def test_a_dialogue_turn_gets_its_meaning_the_first_time_it_is_heard(self):
        """#210: «tungumal» turn 3 is new at encounter 2 (two turns the first time, one more each time) and used to get neither
        cue nor meaning; now the cue always plays and the meaning comes with the turn."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        dlg = cur.dialogue_by_id["tungumal"]
        learner = LearnerState("is", "en", "A1")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=10, new_items=1), today=TODAY)
        first_turns = planner.cfg.dialogue_first_turns
        self.assertEqual(first_turns, 2)
        meaning = dlg.turns[2].partner_meaning
        for times in range(4):
            learner.dialogues_done["tungumal"] = times
            sc = Script(1, "t", cur.target_lang, cur.known_lang)
            planner._play_dialogue(sc, dlg)
            narr = [s.text for s in sc.segments if s.type == "narrate"]
            played = min(len(dlg.turns), first_turns + times)
            for k in range(played):
                self.assertIn(dlg.turns[k].cue, narr, f"encounter {times}: turn {k + 1} keeps its cue")
            said = lambda k: any(dlg.turns[k].partner_meaning in n for n in narr)
            self.assertEqual(said(2), times == 1 and played > 2, f"turn 3's meaning comes at encounter 2 only (times={times})")
            if times == 0:
                self.assertTrue(said(0) and said(1))
            elif times >= 1:
                self.assertFalse(said(0) or said(1), "earlier turns' meanings have faded")

    def test_a_dialogue_turn_without_a_cue_fails_validation(self):
        from audiolesson.content import validate

        raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": "hae", "kind": "phrase", "target": "Hæ.", "meaning": "Hi."}],
               "dialogues": [{"id": "d", "setting": "A door.", "turns": [{"cue": "", "expect": "hae"}]}]}
        with self.assertRaises(CurriculumError):
            validate(curriculum_from_dict(raw))
        raw["dialogues"][0]["turns"][0]["cue"] = "Say hi."
        validate(curriculum_from_dict(raw))

    def test_partner_lines_vary_between_plays_at_natural_speed_and_the_transcript_says_which(self):
        """#134: a clerk says the same thing in other words: each play picks a variant per line (the second another than
        the first), every line is spoken at natural speed, and the label and plan.json name the lines used."""
        import random
        from audiolesson.themes import Level, Theme, Turn, _check, level_dialogue, pick_variants
        from audiolesson.content import CurriculumError

        for t in self._themes:
            for lv in t.levels:
                if any(x.variants for x in lv.turns):
                    early = pick_variants(lv, random.Random(3))
                    self.assertTrue(early and all(i >= 1 for i in early.values()), f"{t.id}: the early play takes a variant of every line")
                    self.assertEqual(pick_variants(lv, random.Random(3), canonical=True), {}, "the late play says the lines as written")
        self.assertTrue(all(any(x.variants for x in lv.turns if x.who == "partner") for t in self._themes for lv in t.levels), "every level has a line that varies")
        learner = self._learner(self._known + self._rest)
        sc = self._planner(learner, [self._supermarket], ["A3"]).build()
        plays = [e for e in sc.exercises if e.label.startswith("dialogue: theme:supermarket:1")]
        lines = sc.meta["theme"]["lines"]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[1], "1,1,1", "the late play says the lines as written")
        self.assertNotEqual(lines[0], lines[1])
        for e, used in zip(plays, lines):
            self.assertTrue(e.label.endswith(f"[lines {used}]"))
        canonical = [t.say for t in self._supermarket.levels[0].turns if t.who == "partner"]
        late = {g.text for g in sc.segments if g.exercise == plays[1].index and g.type == "speak"}
        self.assertTrue(set(canonical) <= late, "every lesson says the canonical lines once")
        partner = {g.text for e in plays for g in sc.segments if g.exercise == e.index and g.type == "speak"}
        self.assertTrue(len(partner) > 3, "the partner's lines differ between plays")
        self.assertTrue(all(g.rate >= 1.0 for e in plays for g in sc.segments if g.exercise == e.index and g.type == "speak"))
        base = level_dialogue(self._supermarket, 0)
        self.assertEqual(base.variant, "1,1,1")
        self.assertEqual(level_dialogue(self._supermarket, 0, picks={1: 1}).turns[0].partner, self._supermarket.levels[0].turns[1].variants[0]["say"])
        photo = next(t for t in self._themes if t.id == "tour").levels[1].turns[3]
        self.assertTrue(all(x.say.startswith(("Viltu", "Á ég að")) for x in photo.lines()), "every variant offers the photo: «Já, takk.» answers it")
        bad = Theme(id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=[
            Turn(who="partner", say="Hæ.", meaning="Hi.", variants=[{"say": "Hæ."}]),
            Turn(who="you", say="Hæ.", cue="Say hi.", items=["hae"]),
        ])])
        with self.assertRaises(CurriculumError):
            _check(bad)

    def test_an_untaught_turn_keeps_its_cue_and_is_heard_in_both_plays(self):
        """#240 (owner, 2026-10-09: an untaught line can't be said at all, so it is never asked): «Gjörðu svo vel.» is
        never met, so its turn is heard in both plays: the cue (the intent) first, then «Here you would say:»."""
        learner = self._learner([i for i in self._known if i != "gjordu_svo_vel"] + [i for i in self._rest if i != "gjordu_svo_vel"])
        sc = self._planner(learner, [self._supermarket], ["A3"], max_new_items=0).build()  # nothing new: it stays untaught
        first, second = [e for e in sc.exercises if e.label.startswith("dialogue: theme:")]
        for e in (first, second):
            texts = [g.text for g in sc.segments if g.exercise == e.index and g.type == "narrate"]
            self.assertIn("Hand over your card.", texts)
            self.assertNotIn("Try it.", texts)
            self.assertLess(texts.index("Hand over your card."), texts.index("Here you would say:"), "the cue first, then the line")

    def test_the_partner_is_voiced_as_the_cues_say(self):
        """Review of #186: the tour guide is «Anna» and the cues say «her»; a male voice contradicted both."""
        from audiolesson.themes import Level, Theme, Turn, _check, level_dialogue

        tour = next(t for t in self._themes if t.id == "tour")
        self.assertEqual(level_dialogue(tour, 0).partner_speaker, "native_a")
        self.assertEqual(level_dialogue(self._supermarket, 0).partner_speaker, "native_b")
        cafe = next(t for t in self._themes if t.id == "cafe")
        self.assertEqual(level_dialogue(cafe, 2).partner_speaker, "native_a")
        planner = self._planner(self._learner([]), [], [])
        sc = Script(1, "t", "is", "en")
        planner.builder.dialogue(sc, level_dialogue(tour, 0))
        self.assertEqual({g.speaker for g in sc.segments if g.text and g.text.startswith("Góðan daginn öll")}, {"native_a"})
        with self.assertRaises(CurriculumError):
            _check(Theme(id="x", scenario="A1", title="X", levels=[Level(goal="g", partner_speaker="native_c", turns=[Turn(who="you", say="Takk.", cue="Thank him.", items=["takk"])])]))

    def test_the_themes_items_are_credited_and_the_next_lesson_takes_the_next_level(self):
        learner = self._learner(self._known + self._rest + ["eg_er_ad_leita_ad_thing", "hvad_er_thetta_mikid_samtals"])
        planner = self._planner(learner, [self._supermarket], ["A3"])
        sc = planner.build()
        self.assertIn("skyr", planner.exposures)
        apply_to_learner(sc, learner, TODAY)
        self.assertEqual(learner.themes_done, {"supermarket": 1})
        again = self._planner(learner, [self._supermarket], ["A3"]).pick_theme()
        self.assertEqual((again[0].id, again[1]), ("supermarket", 1))
        with tempfile.TemporaryDirectory() as tmp:
            learner.save(Path(tmp) / "l.json")
            self.assertEqual(LearnerState.load(Path(tmp) / "l.json").themes_done, {"supermarket": 1})

    def test_a_lesson_with_every_level_played_replays_the_most_rested_level_unassisted(self):
        learner = self._learner(self._known + self._rest)
        learner.themes_done = {t.id: len(t.levels) for t in self._themes}
        learner.themes_last = {"supermarket": 9, "cafe": 3, "museum": 8, "tour": 7}
        planner = self._planner(learner, self._themes, self._order)
        now = learner.next_lesson_number()
        learner.themes_last = {"supermarket": now - 1, "cafe": now - 5, "museum": now - 4, "tour": now - 2}
        pick = planner.pick_theme()
        self.assertIsNotNone(pick)
        rested = {t.id for t in self._themes if now - learner.themes_last[t.id] >= planner.cfg.theme_rest_lessons}
        self.assertIn(pick[0].id, rested, "a theme played in the last lessons rests")
        sc = planner.build()
        theme = sc.meta["theme"]
        self.assertTrue(theme and theme["replay"] and theme["plays"] == 2)
        apply_to_learner(sc, learner, TODAY)
        self.assertEqual(learner.themes_last[theme["id"]], sc.lesson_number)
        with tempfile.TemporaryDirectory() as tmp:
            learner.save(Path(tmp) / "l.json")
            self.assertEqual(LearnerState.load(Path(tmp) / "l.json").themes_last, learner.themes_last)

    def test_spare_time_hears_a_played_level_again_with_its_cues(self):
        """#218 b1: after the listening dialogues, a theme level already played is heard again (partner lines in variants, the cue
        kept, the learner's line modelled and not asked), at most twice a lesson."""
        learner = self._learner(self._known + self._rest)
        learner.themes_done = {t.id: len(t.levels) for t in self._themes}
        learner.themes_last = {"supermarket": 1, "cafe": 1, "museum": 1, "tour": 1}
        sc = self._planner(learner, self._themes, self._order).build()
        heard = sc.meta["heard_themes"]
        self.assertTrue(0 < len(heard) <= PlanConfig().heard_theme_plays, heard)
        own = f"{sc.meta['theme']['id']}:{sc.meta['theme']['level']}"
        self.assertNotIn(own, heard)
        plays = [e for e in sc.exercises if e.label.startswith("heard: theme:")]
        self.assertEqual(len(plays), len(heard))
        for e in plays:
            segs = [g for g in sc.segments if g.exercise == e.index]
            self.assertFalse(any(g.type == "pause" and g.role == "answer" for g in segs), "heard, not asked")
            self.assertTrue(any(g.type == "answer" for g in segs), "the learner's line is modelled")
            self.assertTrue(sum(1 for g in segs if g.type == "narrate") >= 3, "the cues stay")

    def test_a_replays_early_play_only_says_wordings_already_heard_with_their_meaning(self):
        import random
        from audiolesson.themes import pick_variants

        level = self._supermarket.levels[0]
        varying = [k for k, t in enumerate(level.turns) if t.who == "partner" and t.variants]
        self.assertTrue(varying)
        for seed in range(20):
            self.assertEqual(pick_variants(level, random.Random(seed), heard=set()), {}, "nothing heard: the line as written")
            heard = {(varying[0], 1)}
            self.assertEqual(pick_variants(level, random.Random(seed), heard=heard), {varying[0]: 1})
        learner = self._learner(self._known + self._rest)
        learner.themes_done = {"supermarket": 1}
        learner.themes_last = {}
        sc = self._planner(learner, [self._supermarket], ["A3"]).build()
        self.assertTrue(sc.meta["theme"]["replay"])
        self.assertEqual(sc.meta["theme"]["lines"][0], "1," * (len(varying) - 1) + "1", "no wording was heard: both plays as written")
        self.assertEqual(sc.meta["theme"]["heard"], [])
        apply_to_learner(sc, learner, TODAY)
        self.assertEqual(learner.themes_heard, {})
        # a first play records what it said translated; the replay's early play keeps within it
        fresh = self._learner(self._known + self._rest)
        first = self._planner(fresh, [self._supermarket], ["A3"]).build()
        apply_to_learner(first, fresh, TODAY)
        self.assertTrue(fresh.themes_heard.get("supermarket:1"))
        fresh.themes_last = {"supermarket": 0}
        again = self._planner(fresh, [self._supermarket], ["A3"]).build()
        self.assertTrue(again.meta["theme"]["replay"])
        spoken = again.meta["theme"]["lines"][0].split(",")
        heard = {tuple(map(int, h.split(":"))) for h in fresh.themes_heard["supermarket:1"]}
        for pos, k in enumerate(varying):
            self.assertIn(int(spoken[pos]) - 1, {0} | {i for (turn, i) in heard if turn == k})
        with tempfile.TemporaryDirectory() as tmp:
            fresh.save(Path(tmp) / "l.json")
            self.assertEqual(LearnerState.load(Path(tmp) / "l.json").themes_heard, fresh.themes_heard)

    def test_new_material_is_chosen_for_the_themes_next_level_before_the_trip_order(self):
        missing = [i for i in self._known if i not in ("skyr", "attu")]
        learner = self._learner(missing + self._rest)
        def planner(themes, **cfg):
            return Planner(self._cur, learner, Prompts.load("en"), Timing(level="A1"),
                           PlanConfig(minutes=30, new_items=2, themes=themes, theme_scenarios=["A3"], seed=1, **cfg), today=TODAY)

        trip_first = planner([]).select_new(2)[0].id  # what the course order would teach first
        self.assertNotIn(trip_first, ("skyr", "attu"))
        p = planner([self._supermarket], priority=[trip_first])
        self.assertEqual(p.theme_target()[:2], (self._supermarket, 0))
        wants = p.theme_wants()
        self.assertEqual({"skyr", "attu"} - set(wants), set(), "the items the level lacks")
        self.assertTrue(all(w in self._cur.by_id and not learner.has_met(w) for w in wants))
        chosen = [i.id for i in p.select_new(2)]
        self.assertEqual(chosen, [w for w in wants if w in chosen][:2], "the theme's items first, in the order of its turns")
        self.assertNotIn(trip_first, chosen)
        self.assertEqual(planner([], priority=[trip_first]).select_new(2)[0].id, trip_first, "with no theme the trip order decides")

    def test_a_wanted_item_comes_behind_the_prerequisites_it_needs(self):
        learner = self._learner([i for i in self._known + self._rest if i != "skyr"])
        planner = Planner(self._cur, learner, Prompts.load("en"), Timing(level="A1"),
                          PlanConfig(minutes=30, new_items=2, themes=[self._supermarket], theme_scenarios=["A3"]), today=TODAY)
        wants = planner.theme_wants()
        for k, w in enumerate(wants):
            for p in self._cur.by_id[w].prereqs:
                if not learner.has_met(p):
                    self.assertIn(p, wants[:k])

    def test_the_plan_names_the_theme_new_material_was_chosen_for(self):
        learner = self._learner([i for i in self._known + self._rest if i != "skyr"])
        sc = Planner(self._cur, learner, Prompts.load("en"), Timing(level="A1"),
                     PlanConfig(minutes=30, new_items=2, themes=[self._supermarket], theme_scenarios=["A3"]), today=TODAY).build()
        target = sc.meta["theme_target"]
        self.assertEqual((target["id"], target["level"]), ("supermarket", 1))
        self.assertIn("skyr", target["wanted"])
        self.assertIn("skyr", sc.meta["new_items"])

    def test_an_untaught_theme_turn_is_heard_not_asked(self):
        """#240: the untaught turn has no answer pause and no bonus question, and nothing is recorded for it; the turns
        the learner was taught are asked as before."""
        learner = self._learner([i for i in self._known if i != "gjordu_svo_vel"] + [i for i in self._rest if i != "gjordu_svo_vel"])
        planner = self._planner(learner, [self._supermarket], ["A3"], max_new_items=0)  # nothing new: it stays untaught
        sc = planner.build()
        first, second = [e for e in sc.exercises if e.label.startswith("dialogue: theme:")]
        for e in (first, second):
            segs = [g for g in sc.segments if g.exercise == e.index]
            heard = [k for k, g in enumerate(segs) if g.text == "Here you would say:"]
            self.assertEqual(len(heard), 1)
            # «Here you would say:» is a framing line (#241): a beat, then the line, and no answer pause for it
            self.assertEqual((segs[heard[0] + 1].type, segs[heard[0] + 1].role), ("pause", "beat"))
            self.assertEqual(segs[heard[0] + 2].text, "Gjörðu svo vel.")
            self.assertTrue(any(g.type == "pause" and g.role == "answer" for g in segs), "the taught turns are still asked")
        self.assertNotIn("Try it.", sc.transcript())
        self.assertEqual(planner.listening_tried, [])
        self.assertEqual(planner._bonus_review(), [])
        self.assertNotIn("gjordu_svo_vel", planner.exposures)

    def test_a_turn_taught_earlier_in_the_lesson_is_asked_in_the_play(self):
        """#240: "untaught" is judged when the exchange plays. The theme's next level brings «Gjörðu svo vel.» in as new
        material (#201); introduced before the plays, its turn is asked in both, with a pause, not heard."""
        learner = self._learner([i for i in self._known if i != "gjordu_svo_vel"] + [i for i in self._rest if i != "gjordu_svo_vel"])
        sc = self._planner(learner, [self._supermarket], ["A3"]).build()
        intro = next(e for e in sc.exercises if e.kind == "intro" and "gjordu_svo_vel" in e.item_ids)
        plays = [e for e in sc.exercises if e.label.startswith("dialogue: theme:")]
        self.assertTrue(plays and all(intro.start < e.start for e in plays))
        for e in plays:
            self.assertNotIn("Here you would say:", [g.text for g in sc.segments if g.exercise == e.index])

    def test_the_bus_scene_of_lesson_20_hears_the_untaught_lines(self):
        """#240, lesson 20 (§5.16): «Fer þessi strætó í miðbæinn?» and «Hvar á ég að fara út?» had never been taught and
        were asked with «Try it.» after "just hear how it goes". Now both are heard with their meaning; the lines the
        learner knows are asked, and the framing says so."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        dlg = next(d for d in cur.dialogues if d.id == "straeto")
        met = ["einn_mida_takk", "takk", "eg_fer_i_sund", "hvar_er", "fara_heim"]
        planner = Planner(cur, self._learner([i for i in met if i in cur.by_id]), Prompts.load("en"), Timing(level="A1"),
                          PlanConfig(minutes=15, new_items=0, max_new_items=0), today=TODAY)
        _, partly = planner.classify_turns(dlg)
        self.assertEqual(partly, {"fer_thessi_straeto_i_midbaeinn", "hvar_a_eg_ad_fara_ut"}, "the two lines of lesson 20")
        sc = Script(1, "t", "is", "en")
        planner._play_listening(sc, dlg, set())
        text = sc.transcript()
        self.assertNotIn("Try it.", text)
        self.assertEqual(text.count("Here you would say:"), 2)
        self.assertIn(Prompts.load("en").get("listening_intro_some_asked"), text)
        self.assertNotIn(Prompts.load("en").get("listening_intro"), text, "no «just hear it» when lines are asked")
        self.assertIn("Ask for one ticket.", text, "a taught line is asked with its cue")
        self.assertEqual((planner.listening_tried, planner.listening_untaught), ([], []))

    def test_no_theme_without_themes_or_with_nothing_ready(self):
        sc = self._planner(self._learner(self._known + self._rest), [], []).build()
        self.assertIsNone(sc.meta["theme"])
        self.assertFalse(any(e.label.startswith("dialogue: theme:") for e in sc.exercises))
        sc = self._planner(self._learner([]), [self._supermarket], ["A3"]).build()
        self.assertIsNone(sc.meta["theme"])

    def test_plan_json_names_the_theme_and_level(self):
        from audiolesson.cli import _plan

        planner = self._planner(self._learner(self._known + self._rest), [self._supermarket], ["A3"])
        plan = _plan(planner.build(), self._cur)
        self.assertEqual((plan["theme"]["id"], plan["theme"]["level"]), ("supermarket", 1))

    def test_validation_errors(self):
        from audiolesson.content import CurriculumError
        from audiolesson.themes import Level, Theme, Turn, _check

        good = Turn(who="you", say="Takk.", cue="Thank him.", items=["takk"])
        with self.assertRaises(CurriculumError):
            _check(Theme(id="x", scenario="A1", title="X", levels=[]))
        with self.assertRaises(CurriculumError):
            _check(Theme(id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[Turn(who="partner", say="Hæ.", meaning="Hi.")])]))
        with self.assertRaises(CurriculumError):
            _check(Theme(id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[Turn(who="you", say="Takk.", items=["takk"])])]))
        with self.assertRaises(CurriculumError):
            _check(Theme(id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[good, Turn(who="partner", say="Hæ.")])]))
        with self.assertRaises(CurriculumError):
            _check(Theme(id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[Turn(who="him", say="Hæ.")])]))
        _check(Theme(id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[good])]))


class NoSlotLeakTests(unittest.TestCase):
    """#178: a mixed-review cue narrated «How do you say: It's {hour} o'clock.», the construction's raw template. No
    narrated or spoken segment of a built lesson may contain a slot placeholder, whatever path built it."""

    def _leaks(self, sc):
        return [(s.exercise, s.role, s.text) for s in sc.segments if s.text and ("{" in s.text or "}" in s.text)]

    def test_no_narration_of_a_twenty_lesson_course_contains_a_slot(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for n in range(1, 21):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=5), today=day).build()
            self.assertEqual(self._leaks(sc), [], f"lesson {n}")
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)

    def test_a_mixed_review_cue_names_the_filled_sentence(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        for i in cur.by_id:
            if i in ("klukkan_er", "thrju", "eitt", "tvo", "tekurdu_kort", "kort"):
                learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30), today=TODAY)
        b = planner.builder
        b._situation_texts.update({t: 99 for t in ([cur.by_id["klukkan_er"].situation] if cur.by_id["klukkan_er"].situation else []) + list(cur.by_id["klukkan_er"].situations)})
        sc = Script(1, "t", "is", "en")
        b.connect(sc, [cur.by_id["klukkan_er"], cur.by_id["tekurdu_kort"]])
        self.assertEqual(self._leaks(sc), [])
        self.assertIn("o'clock", sc.transcript())
        # the cue's fill is the answer's: «It's three o'clock.» is answered «Klukkan er þrjú.»
        hours = {it.meaning_forms.get("in_sentence", it.meaning): it.target for it in cur.items_with_tag("hour")}
        segs = [g for g in sc.segments if g.exercise == sc.exercises[-1].index]
        cue = next(g for g in segs if g.type == "narrate" and "o'clock" in (g.text or ""))
        answer = next(g for g in segs[segs.index(cue):] if g.type == "answer")
        said = re.search(r"It's (.+?) o'clock", cue.text).group(1)
        self.assertIn(said, hours, cue.text)
        self.assertEqual(answer.text, f"Klukkan er {hours[said]}.")


class PatternRotationTests(unittest.TestCase):
    """#180 (owner's review of #182): one new pattern with many fillers took 21 of a lesson's sentences, since a
    word's homes were drawn at random. A word's sentences rotate through its homes, the one with the fewest
    sentences this lesson first, and a pattern that has about ten stops taking a word's sentences."""

    @staticmethod
    def _planner():
        items = [{"id": f"w{i}", "kind": "vocab", "target": f"orð{i}", "meaning": f"word {i}", "tags": ["t"]} for i in range(4)]
        items += [
            {"id": "ca", "kind": "construction", "target": "Aðeins {x}.", "meaning": "Only {x}.", "slots": {"x": "t"}},
            {"id": "cb", "kind": "construction", "target": "Líka {x}.", "meaning": "Also {x}.", "slots": {"x": "t"}},
        ]
        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items})
        learner = LearnerState("is", "en", "A1")
        for i in ("w0", "w1", "w2", "w3", "ca", "cb"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1), today=TODAY)

    def test_a_word_goes_to_the_home_with_the_fewest_sentences(self):
        b = self._planner().builder
        word = b.cur.by_id["w0"]
        for ca, cb, want in ((5, 0, "cb"), (0, 5, "ca"), (9, 3, "cb")):
            b.construction_counts = {"ca": ca, "cb": cb}
            self.assertEqual(b.generate_with(word).construction.id, want, (ca, cb))
        b.construction_counts = {}
        seen = {b.generate_with(word).construction.id for _ in range(30)}  # an even count: either, by chance
        self.assertEqual(seen, {"ca", "cb"})

    def test_a_full_pattern_takes_no_more_of_a_words_sentences(self):
        b = self._planner().builder
        word = b.cur.by_id["w0"]
        b.construction_counts = {"ca": 10, "cb": 4}
        self.assertEqual({b.generate_with(word).construction.id for _ in range(20)}, {"cb"})
        b.construction_counts = {"ca": 10, "cb": 10}
        self.assertIsNone(b.generate_with(word), "a word with no home left has no sentence")

    def test_sentences_are_counted_by_construction_in_a_lesson(self):
        planner = self._planner()
        sc = planner.build()
        counts = planner.builder.construction_counts
        self.assertEqual(sum(counts.values()), sum(1 for e in sc.exercises if e.kind == "generative"))


class RequestPatternSupplyTests(unittest.TestCase):
    """#171 C: food, drink and shop nouns can go into the patterns a person uses at a counter, so a new
    noun has sentences to be practised in (lesson 15: ost, egg, smjör, mjólk had none)."""

    SHOP_GOODS = {"kjot", "ost", "egg", "smjor", "mjolk", "epli", "banana", "kartoflur", "graenmeti", "avexti",
                  "sukkuladi", "kleinur", "flatkokur", "rugbraud", "hrisgrjon", "pasta"}
    ASKED_FOR = {"ost", "egg", "smjor", "mjolk", "epli", "banana", "sukkuladi", "kleinur", "flatkokur", "rugbraud"}

    def test_every_food_noun_fits_a_request_pattern(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        request_tags = {t for c in cur.items if c.kind == "construction" and c.id not in ("eg_elska", "eg_borda_ekki") for t in c.slots.values()}
        for it in cur.items_with_tag("acc_food"):
            self.assertTrue(set(it.tags) & request_tags, f"{it.id} fits only «Ég elska …» / «Ég borða ekki …»")

    def test_the_patterns_take_only_what_a_person_says_there(self):
        """«Áttu {thing}?», «Ég þarf {thing}.» and «Get ég fengið {thing}?» take shop goods, never a
        dish on a menu or a place; ordering takes dishes too (H7)."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        food = {i.id for i in cur.items_with_tag("acc_food")}
        self.assertEqual({i.id for i in cur.items_with_tag("acc_thing")} & food, self.SHOP_GOODS)
        self.assertEqual({i.id for i in cur.items_with_tag("acc_request")} & food, self.ASKED_FOR & food)
        for dish in ("plokkfisk", "humar", "sushi", "pitsu", "kjotsupu", "hakarl"):
            self.assertIn("acc_orderable", cur.by_id[dish].tags)
            self.assertNotIn("acc_thing", cur.by_id[dish].tags)
            self.assertNotIn("acc_request", cur.by_id[dish].tags)

    def test_a_new_food_noun_gets_sentences_once_the_patterns_are_met(self):
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        for i in ("eg_aetla_ad_fa", "get_eg_fengid", "attu", "kaffi", "vatn", "matsedilinn", "poka", "peysu"):
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner, rng=random.Random(1))
        b.in_lesson.add("ost")
        seen = set()
        for _ in range(30):
            gen = b.generate_with(cur.by_id["ost"])
            self.assertIsNotNone(gen)
            seen.add(gen.target)
        self.assertGreaterEqual(len(seen), 3, seen)
        self.assertTrue(seen <= {"Ég ætla að fá ost.", "Get ég fengið ost?", "Áttu ost?"}, seen)


class RefreshConstructionTests(unittest.TestCase):
    """Owner, on «Má ég {inf}?», «Ég ætla að {inf}.», «Viltu {inf}?»: a few sentences of each in every
    lesson is welcome, with the parts changing; the real practice is for the first appearance and for
    what the learner couldn't say."""

    @staticmethod
    def _cur(refresh=3):
        words = [{"id": f"w{i}", "kind": "vocab", "target": f"orð{i}", "meaning": f"word {i}", "tags": ["t"]} for i in range(8)]
        others = [{"id": f"r{i}", "kind": "phrase", "target": f"Rifja {i}.", "meaning": f"Review {i}."} for i in range(40)]
        c = {"id": "c", "kind": "construction", "target": "Má ég {x}?", "meaning": "May I {x}?", "slots": {"x": "t"}}
        if refresh:
            c["refresh"] = refresh
        return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": words + others + [c]})

    def _build(self, cur, known=True, outcome="recalled", minutes=30):
        """Neither the construction nor its fillers are due (their own reviews wait ten days): what the
        construction gets is the light review."""
        learner = LearnerState("is", "en", "A1")
        for i in [f"r{i}" for i in range(40)]:
            learner.items[i] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="meaning", recalled=3, last_outcome="recalled")
        for i in [f"w{i}" for i in range(8)]:  # known, not due: their own reviews don't use up the sentences
            learner.items[i] = ItemState(due=(TODAY + timedelta(days=10)).isoformat(), successes=3, durable_successes=3, stage="meaning", recalled=3, interval_days=10, last_outcome="recalled")
        if known:
            learner.items["c"] = ItemState(due=(TODAY + timedelta(days=10)).isoformat(), successes=3, durable_successes=3, stage="meaning", recalled=3, interval_days=10, last_outcome=outcome)
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=minutes, seed=1, new_items=0), today=TODAY).build()

    def test_a_known_construction_comes_back_a_few_times_spread_over_the_lesson(self):
        sc = self._build(self._cur())
        mine = [e for e in sc.exercises if e.kind == "generative" and e.item_ids[0] == "c"]
        self.assertGreaterEqual(sc.meta["refresh_sentences"].get("c", 0), 3)
        self.assertGreaterEqual(len(mine), 3)
        self.assertEqual(len({e.label for e in mine}), len(mine), "a different sentence each time")
        starts = [e.start / sc.total_duration for e in mine]
        self.assertLess(starts[0], 0.4)
        self.assertGreater(starts[-1], 0.5, "spread over the lesson, not stacked")

    def test_not_a_construction_that_isnt_known_or_failed_or_has_no_refresh(self):
        self.assertEqual(self._build(self._cur(), known=False).meta["refresh_sentences"], {})
        self.assertEqual(self._build(self._cur(), outcome="not_recalled").meta["refresh_sentences"], {}, "an open one has its own practice")
        self.assertEqual(self._build(self._cur(refresh=0)).meta["refresh_sentences"], {})

    def test_refresh_is_validated(self):
        for bad in (0, 6, -1):
            raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
                   "items": [{"id": "w", "kind": "vocab", "target": "w", "meaning": "w", "tags": ["t"]},
                             {"id": "c", "kind": "construction", "target": "A {x}.", "meaning": "A {x}.", "slots": {"x": "t"}, "refresh": bad}]}
            if bad == 0:
                curriculum_from_dict(raw)  # 0 is the default: no refresh
                continue
            with self.assertRaises(CurriculumError):
                curriculum_from_dict(raw)
        with self.assertRaises(CurriculumError):
            curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
                                  "items": [{"id": "p", "kind": "phrase", "target": "P.", "meaning": "P.", "refresh": 2}]})

    def test_the_real_curriculum_refreshes_the_three_permission_and_intention_patterns(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertEqual({c.id for c in cur.items if c.refresh}, {"ma_eg_inf", "eg_aetla_ad", "viltu"})


class ReplayToolTests(unittest.TestCase):
    """tools/replay_lesson.py, the daily read's table (LEARNING-DESIGN §1): it rebuilds an export's
    lesson from ``learner.before.json`` and the manifest's arguments, continues it, and prints one row
    per figure. A smoke test on an export made from a short real-curriculum course."""

    def test_the_tool_rebuilds_an_export_and_prints_the_table(self):
        import contextlib
        import io
        import importlib.util

        cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang="en")
        learner = LearnerState(cur.target_lang, cur.known_lang, "A1")
        day = date(2026, 1, 1)
        for _ in range(3):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, new_items=4), today=day).build()
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        with tempfile.TemporaryDirectory() as td:
            export = Path(td) / "lesson-004"
            export.mkdir()
            learner.save(export / "learner.before.json")
            manifest = {"lesson": 4, "created_at": f"{day.isoformat()}T08:00:00+09:00", "revisions": {"lla": "test"},
                        "generate_args": ["generate", "--curriculum", "curricula/is-en", "--known", "en", "--minutes", "20"]}
            (export / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            spec = importlib.util.spec_from_file_location("replay_lesson", ROOT / "tools" / "replay_lesson.py")
            tool = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tool)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(tool.main([str(export), "--lessons", "2", "--curriculum", str(ROOT / "curricula" / "is-en")]), 0)
        text = out.getvalue()
        self.assertIn("| | lesson 4 | lesson 5 |", text)
        for row in ("| minutes |", "| short new item alone, most |", "| bare_cap_lapsed |", "| tried lines / bonus questions |", "| lines a listening scene asks for that were never taught (#240) |", "| theme (level) / plays |"):
            self.assertIn(row, text)


class PlausibleFillTests(unittest.TestCase):
    """Owner, after lesson 12: never generate a sentence that makes no sense in its scene
    ("order a passport at the café"). Slot tags keep the grammar right; they must also keep
    the sense right."""

    def test_opening_hours_are_asked_only_of_places_that_open(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for cid in ("hvenaer_opnar", "hvenaer_lokar"):
            fills = {f.id for f in cur.items_with_tag(cur.by_id[cid].slots["place"])}
            self.assertTrue({"sundlaugin", "safnid", "apotekid", "bankinn"} <= fills, cid)
            self.assertFalse(fills & {"isskapurinn", "lyftan", "rofinn", "strætó", "lykillinn", "klosettid"}, cid)


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
                    # «You could also say:» is a framing line: a beat, then the alternative (#241)
                    self.assertEqual((sc.segments[i - 1].type, sc.segments[i - 1].role), ("pause", "beat"))
                    self.assertEqual((sc.segments[i - 2].type, sc.segments[i - 2].role), ("narrate", "frame"))


class FramingBeatTests(unittest.TestCase):
    """#241 (lesson 20: «sometimes no pause between the instructor's line and the example»): a framing line that introduces
    an example or a scene is followed by a beat; a cue for the learner's own action joins its line at once."""

    FRAMING = ("construction_slot", "also", "embed_known", "embed_part", "variant_known", "form_model_known",
               "listening_line", "dialogue_replay", "milestone_intro", "aside", "instance_sentence", "embed_sentence")

    @classmethod
    def setUpClass(cls):
        cls.lessons = [sc for _, sc in ShortItemRepetitionTests._course(12)]

    def test_no_framing_line_runs_into_target_language_speech(self):
        prompts = Prompts.load("en")
        framing = {prompts.get(k) for k in self.FRAMING}
        framed = 0
        for sc in self.lessons:
            for a, b in zip(sc.segments, sc.segments[1:]):
                if a.type != "narrate":
                    continue
                if a.role == "frame" or a.text in framing:
                    framed += 1
                    self.assertFalse(b.type in ("speak", "answer"), f"lesson {sc.lesson_number}: {a.text!r} runs into {b.text!r}")
        self.assertGreater(framed, 20, "the course has framing lines to check")

    def test_a_scene_line_comes_with_a_beat_before_the_partner_speaks(self):
        from audiolesson.themes import level_dialogue, load_themes

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        supermarket = next(t for t in load_themes(ROOT / "curricula" / "is-en", cur) if t.id == "supermarket")

        planner = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=TODAY)
        sc = Script(1, "t", "is", "en")
        planner.builder.dialogue(sc, level_dialogue(supermarket, 0))
        scenes = [k for k, s in enumerate(sc.segments) if s.type == "narrate" and s.role == "frame"]
        self.assertTrue(scenes, "supermarket level 1 has its «at the till» line (#230)")
        for k in scenes:
            self.assertEqual((sc.segments[k + 1].type, sc.segments[k + 1].role), ("pause", "beat"))

    def test_the_next_turns_opener_has_a_beat_after_the_partner_lines_meaning(self):
        """#241 review (L21, supermarket:2): «That's three thousand five hundred krónur.» ran straight into the next turn's
        opener «Viltu fá kvittun?». Nothing narrated runs into the partner's Icelandic."""
        from audiolesson.themes import level_dialogue, load_themes

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        themes = load_themes(ROOT / "curricula" / "is-en", cur)
        planner = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=TODAY)
        checked = 0
        for theme in themes:
            for n in range(len(theme.levels)):
                sc = Script(1, "t", "is", "en")
                planner.builder.dialogue(sc, level_dialogue(theme, n))
                for a, b in zip(sc.segments, sc.segments[1:]):
                    if a.type == "narrate" and b.type == "speak" and b.speaker.startswith("native"):
                        cue = a.text in (Prompts.load("en").get("repeat"),)
                        self.assertTrue(cue, f"{theme.id}:{n + 1}: {a.text!r} runs into {b.text!r}")
                    checked += a.type == "narrate" and a.text == Prompts.load("en").get("dialogue_start")
        self.assertGreater(checked, 3)

    def test_a_cue_for_the_learners_action_joins_its_line(self):
        repeat = Prompts.load("en").get("repeat")
        joins = [(a, b) for sc in self.lessons for a, b in zip(sc.segments, sc.segments[1:]) if a.type == "narrate" and a.text == repeat]
        self.assertTrue(joins)
        self.assertTrue(all(b.type == "speak" for _, b in joins), "«Repeat.» is followed by the line at once")


class FailureThinkTimeTests(unittest.TestCase):
    """Issue #104: a reported failure gives the item one more second on its answer pauses in
    the next lesson that recalls it, and only then."""

    def setUp(self):
        self.learner, scripts = course(3)
        self.day = TODAY + timedelta(days=6)
        # an item the next lesson recalls on its own
        probe = build(copy.deepcopy(self.learner), today=self.day)
        self.item = next(e.item_ids[0] for e in probe.exercises if e.kind == "recall" and len(e.item_ids) == 1)

    @staticmethod
    def pauses(sc, role):
        return [(e.index, e.item_ids, [s.duration for s in sc.segments if s.exercise == e.index and s.type == "pause" and s.role == role])
                for e in sc.exercises]

    def test_only_the_failed_items_answer_pauses_grow(self):
        plain = copy.deepcopy(self.learner)
        flagged = copy.deepcopy(self.learner)
        flagged.items[self.item].extra_think_time = True
        a, b = build(plain, today=self.day), build(flagged, today=self.day)
        extra = Timing().failure_think_time
        compared = 0
        # adding time can only change what fits at the end of the lesson: compare the exercises both share
        for (ia, ids, pa), (ib, _, pb) in zip(self.pauses(a, "answer"), self.pauses(b, "answer")):
            if [e.item_ids for e in a.exercises[: ia + 1]] != [e.item_ids for e in b.exercises[: ib + 1]]:
                break
            if ids == [self.item]:
                self.assertEqual([round(x + extra, 1) for x in pa], pb)
                compared += 1
            elif self.item not in ids:
                self.assertEqual(pa, pb, "other items keep their pauses")
        self.assertGreater(compared, 0)
        self.assertEqual(
            [p for _, ids, p in self.pauses(a, "repeat") if ids == [self.item]][:1],
            [p for _, ids, p in self.pauses(b, "repeat") if ids == [self.item]][:1],
            "repeating after the model is unchanged",
        )
        self.assertEqual(b.meta["think_time_boosted"], [self.item])
        self.assertEqual(a.meta["think_time_boosted"], [])
        floors = {s.floor for e in b.exercises if e.item_ids == [self.item] for s in b.segments
                  if s.exercise == e.index and s.type == "pause" and s.role == "answer"}
        timing = Timing()
        self.assertTrue(floors <= {timing.min_recall_pause + extra, timing.min_supported_pause + extra},
                        f"the extra second survives fitting the audio: {floors}")

    def test_report_sets_it_the_lesson_uses_it_a_new_failure_sets_it_again(self):
        learner = copy.deepcopy(self.learner)
        learner.report([self.item], [], self.day)
        self.assertTrue(learner.items[self.item].extra_think_time)
        sc = build(learner, today=self.day)
        self.assertIn(self.item, sc.meta["think_time_boosted"])
        apply_to_learner(sc, learner, self.day)
        self.assertFalse(learner.items[self.item].extra_think_time, "used up by the lesson")
        nxt = build(copy.deepcopy(learner), today=self.day + timedelta(days=2))
        self.assertEqual(nxt.meta["think_time_boosted"], [], "no boost without a new failure")
        learner.report([self.item], [], self.day + timedelta(days=1))
        self.assertTrue(learner.items[self.item].extra_think_time)

    def test_the_boost_waits_for_a_lesson_that_recalls_the_item(self):
        learner = copy.deepcopy(self.learner)
        sc = build(copy.deepcopy(learner), minutes=2, today=self.day)
        absent = next(i for i in learner.items if i not in sc.meta["exposures"])
        learner.items[absent].extra_think_time = True
        sc = build(learner, minutes=2, today=self.day)
        self.assertNotIn(absent, sc.meta["exposures"])
        apply_to_learner(sc, learner, self.day)
        self.assertTrue(learner.items[absent].extra_think_time, "kept for the first lesson that practises it")

    def test_older_learner_files_load_without_the_flag(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "l.json"
            self.learner.save(path)
            raw = json.loads(path.read_text())
            for st in raw["items"].values():
                st.pop("extra_think_time", None)
            path.write_text(json.dumps(raw))
            self.assertFalse(any(st.extra_think_time for st in LearnerState.load(path).items.values()))


class BinFormCheckTests(unittest.TestCase):
    """#218 b2: a variant item and its base should be forms of one BÍN lemma, looked up once in BÍN's downloaded data and cached so
    ``validate`` runs offline. The check advises and never blocks (owner, after lesson 20)."""

    @staticmethod
    def _cur():
        return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": [
            {"id": "kaffi", "kind": "vocab", "target": "kaffi", "meaning": "coffee"},
            {"id": "kaffid", "kind": "vocab", "target": "kaffið", "meaning": "the coffee", "variant_of": "kaffi", "meaning_spoken": "the coffee"},
        ]})

    @staticmethod
    def _entry(guid, lemma="kaffi"):
        return {"lemma": lemma, "guid": guid, "ofl": "no", "kyn": "", "tag": "NFET", "source": "SHsnid.csv", "checked_on": "2026-10-09"}

    def test_a_pair_of_one_lemma_has_no_warning(self):
        from audiolesson.binform import variant_warnings

        cache = {"kaffi": self._entry("g1"), "kaffið": self._entry("g1")}
        self.assertEqual(variant_warnings(self._cur(), cache), [])

    def test_a_variant_missing_from_the_cache_warns_with_the_command_to_run(self):
        from audiolesson.binform import variant_warnings

        problems = variant_warnings(self._cur(), {"kaffi": self._entry("g1")})
        self.assertEqual(len(problems), 1)
        self.assertIn("tools/bin_lookup.py", problems[0])
        self.assertIn("kaffið", problems[0])

    def test_a_variant_whose_lemma_differs_from_its_base_warns(self):
        from audiolesson.binform import variant_warnings

        problems = variant_warnings(self._cur(), {"kaffi": self._entry("g1"), "kaffið": self._entry("g2", "kaffið")})
        self.assertEqual(len(problems), 1)
        self.assertIn("not one lemma", problems[0])

    def test_validate_only_ever_warns(self):
        import contextlib
        import io
        from audiolesson.binform import save_cache
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "course.toml").write_text(
                '[curriculum]\nname = "x"\ntarget_lang = "is"\nknown_lang = "en"\n\n[[items]]\nid = "kaffi"\nkind = "vocab"\ntarget = "kaffi"\nmeaning = "coffee"\n\n'
                '[[items]]\nid = "kaffid"\nkind = "vocab"\ntarget = "kaffið"\nmeaning = "the coffee"\nmeaning_spoken = "the coffee"\nvariant_of = "kaffi"\n', encoding="utf-8")
            for cache, warns in ((None, "not checked against BÍN yet"),
                                 ({"kaffi": self._entry("g1")}, "not in the BÍN cache"),
                                 ({"kaffi": self._entry("g1"), "kaffið": self._entry("g2", "kaffið")}, "not one lemma"),
                                 ({"kaffi": self._entry("g1"), "kaffið": self._entry("g1")}, None)):
                if cache is not None:
                    save_cache(d / "bin" / "forms.json", cache)
                err = io.StringIO()
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                    self.assertEqual(main(["validate", str(d)]), 0, warns)
                self.assertEqual(warns is None or warns in err.getvalue(), True, (warns, err.getvalue()))

    def test_the_real_cache_when_it_exists_agrees_with_the_curriculum(self):
        from audiolesson.binform import cache_path, load_cache, variant_warnings

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        path = cache_path(ROOT / "curricula" / "is-en")
        if not path.exists():
            self.skipTest("curricula/is-en/bin/forms.json is not built yet: python tools/bin_lookup.py --data SHsnid.csv.zip --variants")
        self.assertEqual(variant_warnings(cur, load_cache(path)), [])

    def _tool(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("bin_lookup", ROOT / "tools" / "bin_lookup.py")
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        return tool

    def test_the_tool_reads_the_downloaded_list_and_waits_for_a_pick_when_ambiguous(self):
        """The fixture ``tests/data/bin_sample.csv`` is HAND-WRITTEN in the layout ``binform.COLUMNS`` assumes (lemma; id; word class;
        domain; form; tag), not a slice of the real file: replace it with one on the first real run."""
        import contextlib
        import io
        import zipfile

        tool = self._tool()
        data = ROOT / "tests" / "data" / "bin_sample.csv"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bin" / "forms.json"
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(tool.run([("miða", None)], data, path, None, "2026-10-09"), 1, "ambiguous: nothing written")
                self.assertFalse(path.exists())
                self.assertIn("pick one with --pick", out.getvalue())
                self.assertEqual(tool.run([("miða", None)], data, path, "no-such-id", "2026-10-09"), 1)
                self.assertIn("no word with id 'no-such-id'", out.getvalue(), "a wrong pick is not 'not found'")
                self.assertEqual(tool.run([("miða", "so")], data, path, None, "2026-10-09"), 0, "--ofl narrows it to one word")
                self.assertEqual(tool.run([("miða", None)], data, path, "1002", "2026-10-09"), 0)
                self.assertEqual(tool.run([("kaffið", None), ("nonexistent", None)], data, path, None, "2026-10-09"), 1, "a form not in the list")
            cache = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual((cache["miða"]["lemma"], cache["miða"]["tag"], cache["miða"]["source"]), ("miði", "ÞFET/ÞGFET", "bin_sample.csv"))
            self.assertEqual(cache["kaffið"]["guid"], "2000")
            # the zipped download works the same
            zpath = Path(td) / "SHsnid.csv.zip"
            with zipfile.ZipFile(zpath, "w") as z:
                z.write(data, "SHsnid.csv")
            from audiolesson.binform import find_forms

            self.assertEqual(find_forms(zpath, {"kaffið"}), find_forms(data, {"kaffið"}))


class NewComponentTests(unittest.TestCase):
    """#218 b3: the pace's unit is weighted new components (the owner's amendments of 2026-10-08/09): a word or chunk 1, a pattern 1
    (its frame's new words included), a phrase 1 for each new word, a close variant w (0.5), known parts and a #192 pattern instance 0."""

    @staticmethod
    def _cur(extra=()):
        items = [
            {"id": "kaffi", "kind": "vocab", "target": "kaffi", "meaning": "coffee", "tags": ["thing"]},
            {"id": "te", "kind": "vocab", "target": "te", "meaning": "tea", "tags": ["thing"]},
            {"id": "taka_mynd", "kind": "vocab", "target": "taka mynd", "meaning": "take a photo"},
            {"id": "hvad_kostar_thetta", "kind": "phrase", "target": "Hvað kostar þetta?", "meaning": "What does this cost?"},
            {"id": "kostar_pat", "kind": "construction", "target": "Hvað kostar {thing}?", "meaning": "What does {thing} cost?", "slots": {"thing": "thing"}, "example": {"thing": "kaffi"}},
            {"id": "opnar_pat", "kind": "construction", "target": "Hvenær opnar {thing}?", "meaning": "When does {thing} open?", "slots": {"thing": "thing"}, "example": {"thing": "kaffi"}},
            {"id": "opnar", "kind": "vocab", "target": "opnar", "meaning": "opens"},
            {"id": "kaffid", "kind": "vocab", "target": "kaffið", "meaning": "the coffee", "variant_of": "kaffi", "meaning_spoken": "the coffee"},
            {"id": "bara", "kind": "phrase", "target": "Ég vil bara kaffi.", "meaning": "I just want coffee."},
            {"id": "sundfot", "kind": "phrase", "target": "Sundföt og handklæði.", "meaning": "Swimsuit and towel."},
        ]
        return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": items + list(extra)})

    @staticmethod
    def _met(learner, *ids):
        for i in ids:
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=2,
                                         due=(TODAY + timedelta(days=5)).isoformat(), last_practiced=(TODAY - timedelta(days=2)).isoformat())

    def _planner(self, *met, cur=None, **cfg):
        cur = cur or self._cur()
        learner = LearnerState("is", "en", "A1")
        self._met(learner, *met)
        return Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=6, new_target=8, **cfg), today=TODAY)

    def test_each_kind_costs_what_it_adds(self):
        planner = self._planner("kaffi")
        cost = lambda i: planner.component_cost(planner.cur.by_id[i])
        self.assertEqual(cost("te"), 1.0, "a word")
        self.assertEqual(cost("taka_mynd"), 1.0, "a chunk counts once, however many words")
        self.assertEqual(cost("sundfot"), 3.0, "a phrase: 1 for each new word")
        self.assertEqual(cost("bara"), 3.0, "…not for the word it shares with what is met («kaffi»)")
        self.assertEqual(cost("kaffid"), 0.5, "a close variant costs w")
        self.assertEqual(cost("kostar_pat"), 1.0, "a pattern counts 1, its frame's new words included")
        self.assertEqual(planner.cfg.form_weight, 0.5)

    def test_a_pattern_of_known_words_still_counts_one_unless_it_sits_inside_a_known_pattern(self):
        planner = self._planner("hvad_kostar_thetta", "kaffi")
        self.assertEqual(planner.component_cost(planner.cur.by_id["kostar_pat"]), 1.0, "after a fixed phrase, the pattern is a new step")
        raw = self._cur([{"id": "hvenaer_pat", "kind": "construction", "target": "Hvenær {thing}?", "meaning": "When {thing}?", "slots": {"thing": "thing"}, "example": {"thing": "kaffi"}}])
        planner = self._planner("opnar_pat", "kaffi", cur=raw)
        self.assertEqual(planner.component_cost(raw.by_id["hvenaer_pat"]), 0.0, "a frame inside a known pattern is a known part")

    def test_a_frames_words_are_not_counted_twice(self):
        planner = self._planner("kaffi")
        a, b = planner.cur.by_id["opnar_pat"], planner.cur.by_id["opnar"]
        self.assertEqual(planner._charge(a), 1.0)
        self.assertEqual(planner._charge(b), 0.0, "«opnar» came with its frame")
        self.assertEqual(planner.components_total, 1.0)

    def test_a_pattern_instance_costs_nothing(self):
        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": [
            {"id": "tvo", "kind": "vocab", "target": "tvo", "meaning": "two", "tags": ["c"]},
            {"id": "thrja", "kind": "vocab", "target": "þrjá", "meaning": "three", "tags": ["c"]},
            {"id": "pat", "kind": "construction", "target": "{count} miða, takk.", "meaning": "{count} tickets, please.", "slots": {"count": "c"}, "example": {"count": "tvo"}},
            {"id": "ph", "kind": "phrase", "target": "Þrjá miða, takk.", "meaning": "Three tickets, please.", "instance_of": "pat", "instance_fill": {"count": "thrja"}}]})
        planner = self._planner("tvo", "thrja", "pat", cur=cur)
        self.assertEqual(planner.component_cost(cur.by_id["ph"]), 0.0)

    def test_the_total_stops_selection_and_the_last_item_may_go_over(self):
        extra = [{"id": f"w{i}", "kind": "vocab", "target": f"orð{'abcdefghijkl'[i]}", "meaning": f"word {i}"} for i in range(12)]
        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": extra})
        planner = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=6, new_target=2.5), today=TODAY)
        chosen = planner.select_new(10)
        self.assertEqual(planner.components_total, 3.0, [i.id for i in chosen])
        self.assertEqual(len(chosen), 3, "2.5 is below the third item's start: the last one goes over")
        self.assertEqual(planner.select_new(10), [], "the target is met")

    @staticmethod
    def _zero_then_words(zeros=12, words=12):
        base = [{"id": "base", "kind": "phrase", "target": "Orð eitt tvö þrjú fjögur fimm.", "meaning": "Words."}]
        ws = ["Orð", "eitt", "tvö", "þrjú", "fjögur"]
        pairs = [(a, b) for a in ws for b in ws if a != b][:zeros]
        zero = [{"id": f"z{i}", "kind": "phrase", "target": f"{a} {b}.", "meaning": f"Zero {i}."} for i, (a, b) in enumerate(pairs)]
        new = [{"id": f"w{i}", "kind": "vocab", "target": f"nýtt{'abcdefghijkl'[i]}", "meaning": f"new {i}"} for i in range(words)]
        return curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": base + zero + new})

    def test_zero_cost_items_do_not_use_up_the_item_ceiling_so_the_target_is_reached(self):
        """#218 b3 (owner, option b): the ceiling caps load. The first ten picks of this course cost nothing; the target must still be reached."""
        cur = self._zero_then_words()
        learner = LearnerState("is", "en", "A1")
        self._met(learner, "base")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=6, new_target=6), today=TODAY)
        chosen = planner.select_new(planner.cfg.new_items_ceiling())
        self.assertGreater(sum(1 for i in chosen if i.id.startswith("z")), 10, "more than the ceiling's worth of free items")
        self.assertGreaterEqual(planner.components_total, 6.0)
        costed = [i for i in chosen if planner.component_by_item[i.id] > 0]
        self.assertLessEqual(len(costed), planner.cfg.new_items_ceiling())
        # counting items the same course would stop at the ceiling, short of the target
        items_mode = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=6), today=TODAY)
        self.assertEqual(len(items_mode.select_new(10)), 10)

    def test_a_lesson_whose_first_picks_cost_nothing_reaches_its_target(self):
        cur = self._zero_then_words()
        learner = LearnerState("is", "en", "A1")
        self._met(learner, "base")
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=6, new_target=6), today=TODAY).build()
        nc = sc.meta["new_components"]
        self.assertGreaterEqual(nc["total"], 6.0, nc)
        self.assertLessEqual(nc["total"], 6.0 + 1.0, "one item over at most")

    def test_the_last_pick_goes_over_by_one_item_at_most(self):
        two = [{"id": f"p{i}", "kind": "phrase", "target": f"Orð{'abcdefgh'[2 * i]} orð{'abcdefgh'[2 * i + 1]}.", "meaning": f"Two {i}."} for i in range(4)]
        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": two})
        for target, expected in ((3.0, 4.0), (2.5, 2.0)):
            planner = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=6, new_target=target), today=TODAY)
            planner.select_new(10)
            self.assertEqual(planner.components_total, expected, target)

    def test_a_phrase_made_of_a_curriculum_chunk_counts_the_chunk_once(self):
        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": [
            {"id": "ma_eg", "kind": "phrase", "target": "Má ég fara?", "meaning": "May I go?"},
            {"id": "taka_mynd", "kind": "vocab", "target": "taka mynd", "meaning": "take a photo"},
            {"id": "ma_eg_taka_mynd", "kind": "phrase", "target": "Má ég taka mynd?", "meaning": "May I take a photo?"}]})
        planner = self._planner("ma_eg", cur=cur)
        self.assertEqual(planner.component_cost(cur.by_id["ma_eg_taka_mynd"]), 1.0, "«taka mynd» is one item: 1, not 2")
        self.assertEqual(planner.component_cost(cur.by_id["taka_mynd"]), 1.0)

    def test_the_backlog_estimate_for_the_target_reserves_item_slots_not_components(self):
        learner = PacingTests._rated([["r"] * 10] * 3)
        slots = max(0, int(30 * 60 / 16) - 6 * 6)
        for k in range(int(slots * 0.7)):  # a backlog just under the limit when new material is 6 items
            learner.items[f"pad{k}"] = ItemState(stage="meaning", due=TODAY.isoformat())
        learner.new_target = 12.0
        self.assertGreaterEqual(learner.suggest_target(30, TODAY)[0], 12.0, "12 components are not reserved as 12 items")

    def test_the_lesson_reports_its_components_and_a_rebuild_keeps_the_total(self):
        extra = [{"id": f"w{i}", "kind": "vocab", "target": f"orð{'abcdefghijklmn'[i]}", "meaning": f"word {i}"} for i in range(14)]
        cur = self._cur(extra)
        learner = LearnerState("is", "en", "A1")
        sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=6, new_target=6), today=TODAY).build()
        nc = sc.meta["new_components"]
        self.assertEqual(set(nc), {"total", "forms", "target", "by_item"})
        self.assertGreaterEqual(nc["total"], 6)
        self.assertLessEqual(nc["total"], 6 + 1.5, "stops once the target is reached, the last item may go over")
        self.assertEqual(nc["total"], round(sum(nc["by_item"].values()), 2))
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=6, new_target=6, planned_extras=["w13"]), today=TODAY)
        sc2 = planner.build()
        self.assertIn("w13", sc2.meta["new_components"]["by_item"], "an extra a first build took counts from the start, so the rebuild keeps the total")

    def test_counting_items_is_unchanged(self):
        cur = self._cur()
        sc = Planner(cur, LearnerState("is", "en", "A1"), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, new_items=3), today=TODAY).build()
        self.assertIsNone(sc.meta["new_components"])

    def test_the_target_moves_by_the_pace_rules_within_four_and_twelve(self):
        learner = PacingTests._rated([["r"] * 10] * 3)
        self.assertEqual(learner.new_target, 8.0)
        target, why = learner.suggest_target(30, TODAY)
        self.assertEqual(target, 9.0, why)
        self.assertEqual(learner.suggest_pace(30, TODAY)[0], 7, "the items pace moves on its own, unchanged")
        bad = PacingTests._rated([["r"] * 6 + ["f"] * 4] * 3)
        self.assertEqual(bad.suggest_target(30, TODAY)[0], 7.0)
        for start, outcomes, expected in ((12.0, [["r"] * 10] * 3, 12.0), (4.0, [["r"] * 6 + ["f"] * 4] * 3, 4.0)):
            lr = PacingTests._rated(outcomes)
            lr.new_target = start
            self.assertEqual(lr.suggest_target(30, TODAY)[0], expected, start)
        light = PacingTests._rated([["r"] * 8 + ["f"] * 2] * 3, [None, "light", "light"])
        self.assertEqual(light.suggest_target(30, TODAY)[0], 9.0, "two light lessons raise it")
        heavy = PacingTests._rated([["r"] * 10] * 3, [None, "heavy", None])
        self.assertEqual(heavy.suggest_target(30, TODAY)[0], 8.0)

    def test_the_target_is_a_rate_per_30_minutes_and_a_lesson_plans_its_share(self):
        """#242: at 5 minutes a rate of 8 plans 1.33; at 30, 8; the saved value is the rate."""
        import contextlib
        import io
        from audiolesson.cli import main

        for minutes, planned in ((5, 8 * 5 / 30), (15, 4.0), (30, 8.0)):
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / "l.json"
                LearnerState("fr", "en", "A1").save(path)
                out = Path(td) / "out"
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["generate", "-c", str(ROOT / "curricula" / "fr-en-a1.toml"), "-l", str(path), "--out", str(out), "--no-audio", "-m", str(minutes)]), 0)
                plan = json.loads(next(out.glob("*.plan.json")).read_text())
                self.assertAlmostEqual(plan["new_components"]["target"], planned, places=2, msg=minutes)
                self.assertEqual(LearnerState.load(path).new_target, 8.0, "the rate is saved, not the share")

    def test_a_very_short_lesson_plans_at_least_one_component(self):
        import contextlib
        import io
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "l.json"
            learner = LearnerState("fr", "en", "A1")
            learner.new_target = 4.0
            learner.save(path)
            out = Path(td) / "out"
            with contextlib.redirect_stdout(io.StringIO()):
                main(["generate", "-c", str(ROOT / "curricula" / "fr-en-a1.toml"), "-l", str(path), "--out", str(out), "--no-audio", "-m", "3"])
            plan = json.loads(next(out.glob("*.plan.json")).read_text())
            self.assertEqual(plan["new_components"]["target"], 1.0)

    def test_the_target_is_saved_and_the_cli_plans_from_it(self):
        import contextlib
        import io
        from audiolesson.cli import main

        learner = LearnerState("fr", "en", "A1")
        learner.new_target = 9.0
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "l.json"
            learner.save(path)
            self.assertEqual(LearnerState.load(path).new_target, 9.0)
            raw = json.loads(path.read_text())
            raw.pop("new_target")
            path.write_text(json.dumps(raw))
            self.assertEqual(LearnerState.load(path).new_target, 8.0, "an older file starts at 8")
            out = Path(td) / "out"
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                self.assertEqual(main(["generate", "-c", str(ROOT / "curricula" / "fr-en-a1.toml"), "-l", str(path), "--out", str(out), "--no-audio", "-m", "10"]), 0)
            self.assertIn("new components (weighted)", buf.getvalue())
            self.assertTrue(LearnerState.load(path).new_target >= 4.0)
            plan = json.loads(next(out.glob("*.plan.json")).read_text())
            self.assertTrue(plan["new_components"]["total"] >= 0)
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                self.assertEqual(main(["generate", "-c", str(ROOT / "curricula" / "fr-en-a1.toml"), "-l", str(path), "--out", str(out), "--no-audio", "-m", "10", "--new", "3"]), 0)
            self.assertNotIn("new components (weighted)", buf.getvalue(), "--new counts items")


class NewFirstOrderTests(unittest.TestCase):
    """#243 (a user option, outside the design): ``--order new-first`` introduces every planned new item first, back to back, then
    turns to known material; ``spread`` is the planner as it was."""

    @staticmethod
    def _state(lessons=8):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        for _ in range(lessons):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=6, seed=3), today=day).build()
            apply_to_learner(sc, learner, day)
            learner.report([], [], day + timedelta(days=1), lesson_number=sc.lesson_number, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        return cur, learner, day

    @staticmethod
    def _cfg(order):
        return PlanConfig(minutes=30, new_items=6, new_target=8.0, seed=3, order=order)  # the default path counts components

    def _plan(self, cur, learner, day, order):
        return Planner(cur, copy.deepcopy(learner), Prompts.load("en"), Timing(level="A1"), self._cfg(order), today=day).build()

    def _block(self, cur, learner, day, sc):
        """(the new items the lesson picked at its start, the indices of their introductions)."""
        first = {i.id for i in Planner(cur, copy.deepcopy(learner), Prompts.load("en"), Timing(level="A1"), self._cfg("new-first"), today=day).select_new(
            self._cfg("new-first").new_items_ceiling(), cheap=True)}
        idx = [e.index for e in sc.exercises if e.kind in ("intro", "embed") and e.item_ids and e.item_ids[0] in first]
        return first, idx

    def test_known_material_waits_until_the_last_introduction(self):
        cur, learner, day = self._state()
        sc = self._plan(cur, learner, day, "new-first")
        today, intros = self._block(cur, learner, day, sc)
        self.assertGreaterEqual(len(intros), 3, "a lesson with several introductions")
        for e in sc.exercises[: max(intros)]:
            if e.kind in ("intro", "embed", "note", "opening"):
                continue
            self.assertNotEqual(e.kind, "dialogue", (e.index, e.label))
            self.assertTrue(set(e.item_ids) & today, f"known material before the last introduction: {e.kind} {e.label} {e.item_ids}")
        spread = self._plan(cur, learner, day, "spread")
        self.assertTrue(any(not set(e.item_ids) & today for e in spread.exercises[: max(intros)] if e.kind not in ("intro", "embed", "note", "opening")),
                        "…which the spread order does not do")

    def test_the_introductions_are_consecutive_apart_from_todays_own_recalls(self):
        cur, learner, day = self._state()
        sc = self._plan(cur, learner, day, "new-first")
        today, intros = self._block(cur, learner, day, sc)
        for a, b in zip(intros, intros[1:]):
            between = [e for e in sc.exercises[a + 1 : b] if e.kind not in ("note", "opening")]
            self.assertLessEqual(len(between), 3, [(e.kind, e.label) for e in between])
            self.assertTrue(all(set(e.item_ids) & today for e in between), [(e.kind, e.label) for e in between])

    def test_the_length_stays_within_5_percent_of_spread_and_spread_is_unchanged(self):
        cur, learner, day = self._state()
        spread = self._plan(cur, learner, day, "spread")
        first = self._plan(cur, learner, day, "new-first")
        # a lesson the hard cap leaves short ends there by design (#206: up to hard_cap_short_max), rather than say short words alone; a part
        # introduced inside its whole (#239) puts that sentence on the cap sooner, so this state can end that much short
        short = spread.total_duration - first.total_duration
        self.assertTrue(
            abs(short) / spread.total_duration < 0.05 or (0 < short <= PlanConfig().hard_cap_short_max and not first.meta["bare_cap_lapsed"]),
            (first.total_duration, spread.total_duration),
        )
        default = Planner(cur, copy.deepcopy(learner), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_items=6, new_target=8.0, seed=3), today=day).build()
        self.assertEqual([e.label for e in default.exercises], [e.label for e in spread.exercises], "spread is the default and today's planner")
        self.assertEqual(spread.meta["config"]["order"], "spread")
        self.assertEqual(first.meta["config"]["order"], "new-first")

    def test_the_cli_takes_order(self):
        import contextlib
        import io
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "l.json"
            LearnerState("fr", "en", "A1").save(path)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["generate", "-c", str(ROOT / "curricula" / "fr-en-a1.toml"), "-l", str(path), "--out", td, "--no-audio", "-m", "10", "--order", "new-first"]), 0)
            self.assertEqual(json.loads(next(Path(td).glob("*.plan.json")).read_text())["config"]["order"], "new-first")


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

    def test_hesitation_counts_as_half_a_failure_for_the_pace(self):
        """Simulated lessons 1-12 with every new item confirmed in the Discord review: the pace
        rose every lesson to 10 because only outright failures counted. A hesitation now
        counts ½: 2 of 12 hesitated (8%) still speeds up, 4 (17%) and 6 (25%) hold, 8 (33%) slows down (#218)."""
        results = {}
        for hesitated in (2, 4, 6, 8):
            learner = fresh()
            day = TODAY
            sc = build(learner, 30, today=day, new_items=6)
            apply_to_learner(sc, learner, day)
            learner.pace = 6
            new = sc.meta["new_items"]
            self.assertGreaterEqual(len(new), hesitated)
            # the fr-en sample lesson 1 has fewer than 12 new items: scale the count to 12
            n = round(hesitated * len(new) / 12)
            learner.report([], [], day, 1, hesitated=new[:n], recalled=new[n:])
            results[hesitated] = learner.suggest_pace(30, day + timedelta(days=1))
        self.assertEqual({k: v[0] for k, v in results.items()}, {2: 7, 4: 6, 6: 6, 8: 5}, results)
        self.assertIn("a hesitation counts ½", results[8][1])

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

    # ---- #218 part a: the recall rate over three lessons and the load rating ----

    @staticmethod
    def _rated(outcomes, loads=None, pace=6):
        """A learner with one lesson per entry of ``outcomes`` (each a list of 'r'ecalled / 'h'esitated / 'f'ailed
        for that lesson's new items), all reported; ``loads`` are stored on the lessons in order."""
        learner = fresh()
        learner.pace = pace
        learner.lessons = []
        for n, outs in enumerate(outcomes, 1):
            ids = []
            for k, o in enumerate(outs):
                item_id = f"i{n}_{k}"
                ids.append(item_id)
                learner.items[item_id] = ItemState(
                    stage="meaning", due=(TODAY + timedelta(days=30)).isoformat(),
                    history=[{"lesson": n, "stages": ["meaning"], "ok": o != "f", **({"outcome": "hesitated"} if o == "h" else {})}],
                )
            learner.lessons.append({"number": n, "new_items": ids, **({"load": loads[n - 1]} if loads and loads[n - 1] else {})})
            learner.reported.append(n)
        learner.lessons_completed = len(outcomes)
        return learner

    def test_the_rate_is_taken_over_the_last_three_reported_lessons(self):
        learner = self._rated(["f" * 3 + "r" * 7, "r" * 10, "r" * 10, "r" * 10])
        self.assertEqual(learner.recall_rate(), (0, 30), "lesson 1 is outside the window")
        learner = self._rated(["r" * 10, "f" * 2 + "r" * 8, "r" * 10])
        self.assertEqual(learner.recall_rate(), (2, 30))
        learner.lessons.insert(1, {"number": 99, "new_items": ["i1_0"]})  # not reported: not in the window
        self.assertEqual(learner.recall_rate(), (2, 30))

    def test_up_at_15_percent_hold_to_25_down_above(self):
        # window of 30 items: 4 failed = 13% (up), 6 = 20% (hold), 8 = 27% (down)
        out = {}
        for failed in (4, 6, 8):
            learner = self._rated([["r"] * 10] * 3)
            for k in range(failed):
                learner.items[f"i{1 + k // 10}_{k % 10}"].history[-1]["ok"] = False
            out[failed] = learner.suggest_pace(30, TODAY)[0]
        self.assertEqual(out, {4: 7, 6: 6, 8: 5})

    def test_a_later_lesson_does_not_hide_an_outcome(self):
        """``history[-1]`` is the latest lesson's entry; the lesson's own is found by number, in the rate and in the report."""
        learner = self._rated([["r"] * 9 + ["f"]])
        learner.items["i1_9"].history.append({"lesson": 2, "stages": ["meaning"], "ok": True})
        self.assertEqual(learner.recall_rate(), (1, 10))
        learner = self._rated([["r"] * 4])
        learner.items["i1_0"].history.append({"lesson": 2, "stages": ["meaning"], "ok": True})
        learner.report(["i1_0"], [], TODAY, 1)
        self.assertEqual([(e["lesson"], e["ok"]) for e in learner.items["i1_0"].history], [(1, False), (2, True)])
        self.assertEqual(learner.recall_rate(), (1, 4))

    def test_an_embedded_item_that_failed_counts_as_weak(self):
        learner = self._rated([["r"] * 3])
        learner.lessons[0]["new_items"].append("emb")
        learner.embedded["emb"] = 1
        self.assertEqual(learner.recall_rate(), (0, 4), "still pending: not counted")
        learner.report(["emb"], [], TODAY, 1)
        self.assertEqual(learner.embed_failed, ["emb"])
        self.assertEqual(learner.recall_rate(), (1, 4))

    def test_two_light_lessons_raise_the_pace_and_one_heavy_blocks_it(self):
        # 20% over the window: a hold on the rate alone
        outs = [["r"] * 4 + ["f"] * 6] + [["r"] * 10] * 2
        self.assertEqual(self._rated(outs).suggest_pace(30, TODAY)[0], 6)
        pace, why = self._rated(outs, [None, "light", "light"]).suggest_pace(30, TODAY)
        self.assertEqual(pace, 7, why)
        self.assertIn("light", why)
        self.assertEqual(self._rated(outs, [None, "right", "light"]).suggest_pace(30, TODAY)[0], 6)
        self.assertEqual(self._rated(outs, [None, "light", "light"]).suggest_pace(30, TODAY)[0], 7)
        pace, why = self._rated(outs, ["heavy", "light", "light"]).suggest_pace(30, TODAY)
        self.assertEqual(pace, 6, why)
        # a heavy lesson also stops a rise on a clean rate
        clean = [["r"] * 10] * 3
        self.assertEqual(self._rated(clean).suggest_pace(30, TODAY)[0], 7)
        self.assertEqual(self._rated(clean, [None, "heavy", None]).suggest_pace(30, TODAY)[0], 6)
        # light lessons do not lift a rate above 25%
        bad = [["r"] * 6 + ["f"] * 4] * 3
        self.assertEqual(self._rated(bad, [None, "light", "light"]).suggest_pace(30, TODAY)[0], 5)

    def test_a_load_only_report_leaves_the_lesson_unreported(self):
        learner = SoonerRequestTests._learner()
        changed = learner.report([], [], TODAY, 1, load="heavy")
        self.assertEqual((learner.reported, learner.lessons[0]["load"], changed["load"]), ([], "heavy", "heavy"))
        self.assertIsNone(learner.recall_rate())
        learner.report([], [], TODAY, 1, load="light")  # the last word stands
        self.assertEqual(learner.lessons[0]["load"], "light")
        learner.report(["a"], [], TODAY, 1, load="right")
        self.assertEqual((learner.reported, learner.lessons[0]["load"]), ([1], "right"))
        with self.assertRaises(ValueError):
            learner.report([], [], TODAY, 1, load="enormous")

    def test_two_light_lessons_need_a_small_backlog_like_the_recall_rise(self):
        outs = [["r"] * 4 + ["f"] * 6] + [["r"] * 10] * 2
        learner = self._rated(outs, [None, "light", "light"])
        self.assertEqual(learner.suggest_pace(30, TODAY)[0], 7)
        slots = max(0, int(30 * 60 / 16) - 6 * 6)
        for k in range(int(slots * 0.6)):  # items due now: between 0.5 and 0.8 of the review slots
            learner.items[f"pad{k}"] = ItemState(stage="meaning", due=TODAY.isoformat())
        self.assertEqual(learner.suggest_pace(30, TODAY)[0], 6, "a backlog the recall rise would not accept blocks the light rise too")

    def test_an_unrated_lesson_neither_breaks_nor_extends_the_run_of_light_lessons(self):
        outs = [["r"] * 8 + ["f"] * 2] * 4
        light_gap = self._rated(outs, ["light", "light", None, None])
        self.assertEqual(light_gap.suggest_pace(30, TODAY)[0], 7, "the last two rated lessons are both light")
        broken = self._rated(outs, ["light", "light", "right", None])
        self.assertEqual(broken.suggest_pace(30, TODAY)[0], 6, "a rated «right» breaks it")

    def test_a_load_for_a_lesson_not_in_the_log_warns(self):
        import contextlib
        import io
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "learner.json"
            SoonerRequestTests._learner().save(path)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(main(["report", "-l", str(path), "--lesson", "9", "--load", "light", "--date", TODAY.isoformat()]), 0)
            self.assertIn("lesson 9 is not in the lesson log", err.getvalue())
            self.assertNotIn("load", LearnerState.load(path).lessons[0])

    def test_the_cli_takes_load_alone_and_saves_it(self):
        import contextlib
        import io
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "learner.json"
            SoonerRequestTests._learner().save(path)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["report", "-l", str(path), "--lesson", "1", "--load", "light", "--date", TODAY.isoformat()]), 0)
            loaded = LearnerState.load(path)
            self.assertEqual((loaded.lessons[0]["load"], loaded.reported), ("light", []))
            self.assertNotIn("all good", out.getvalue())

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

    def test_unsupported_recall_has_its_own_floor(self):
        """Issue #106: an answer pause holds both retrieval and speech, so recall with nothing
        given never drops below min_recall_pause, while repeating and hinted recall keep the
        shorter floors; longer answers still get more time from the speech estimate."""
        t = Timing(level="B2")  # the shortest pauses: familiar item, fast level
        one_word = t.answer_pause("Já.", "is", successes=8)
        self.assertEqual(one_word, t.min_recall_pause)
        self.assertEqual(t.min_recall_pause, 2.5)
        longer = t.answer_pause("Ég er að læra íslensku á hverjum degi.", "is", successes=8)
        self.assertGreater(longer, one_word)
        self.assertEqual(t.repeat_pause("Já.", "is"), t.min_pause, "repetition is unchanged")
        hinted = t.answer_pause("Já takk.", "is", successes=8, supported=True)
        self.assertLess(hinted, t.min_recall_pause)
        self.assertEqual(Timing(level="B2", min_supported_pause=2.0).answer_pause("Já takk.", "is", successes=8, supported=True), 2.0,
                         "the supported floor is configurable on its own")

    def test_lesson_recall_pauses_respect_the_floor(self):
        _, scripts = course(4)
        floor = Timing().min_recall_pause
        checked = 0
        for sc in scripts:
            by_ex = {}
            for seg in sc.segments:
                by_ex.setdefault(seg.exercise, []).append(seg)
            for segs in by_ex.values():
                supported = False
                for seg in segs:
                    if seg.type == "narrate":
                        supported = False
                    elif seg.type == "speak" and seg.role in ("hint", "partial"):
                        supported = True
                    elif seg.type == "pause" and seg.role == "answer" and not supported:
                        self.assertGreaterEqual(seg.duration, floor)
                        checked += 1
        self.assertGreater(checked, 20)

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
            prof.fit_max = 1.25  # both directions of the mechanism, as a profile may still allow
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False)
            self.assertEqual(cues["target_s"], 900)
            self.assertAlmostEqual(cues["duration_s"], 900, delta=1.0, msg=cues["fit_scale"])
            self.assertTrue(0.85 <= cues["fit_scale"] <= 1.25)
            # speech untouched, every pause scaled by the same factor, except that shrinking
            # never takes a pause below its own floor (issue #106)
            answers = [c["dur"] for c in cues["segments"] if c["type"] == "pause" and c["role"] == "answer"]
            planned = [s for s in sc.segments if s.type == "pause" and s.role == "answer"]
            for a, p in zip(answers, planned):
                e = p.duration * cues["fit_scale"]
                if cues["fit_scale"] < 1:
                    e = max(e, min(p.duration, p.floor))
                self.assertAlmostEqual(a, round(e, 2), delta=0.02)

    def test_a_short_lesson_is_not_stretched_by_default(self):
        """Owner, lesson 12 feedback: longer pauses don't make a short lesson better. With the
        default profile, a file under its target keeps the pauses the timing model set."""
        learner, scripts = course(6, minutes=15)
        sc = scripts[-1]
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(None, "stub")
            prof.mp3 = False
            prof.fit_tolerance = 0.0
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False, target_seconds=3000)
            self.assertEqual(cues["fit_scale"], 1.0)
            self.assertLess(cues["duration_s"], 3000)
            planned = [round(s.duration, 2) for s in sc.segments if s.type == "pause" and s.role == "answer"]
            self.assertEqual([c["dur"] for c in cues["segments"] if c["type"] == "pause" and c["role"] == "answer"], planned)

    def test_shrinking_to_fit_keeps_the_recall_floor(self):
        learner, scripts = course(6, minutes=15)
        sc = scripts[-1]
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(None, "stub")
            prof.mp3 = False
            prof.fit_tolerance = 0.0
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False, target_seconds=300)
            self.assertEqual(cues["fit_scale"], prof.fit_min, "far too long: pauses shrink as far as allowed")
            planned = [s for s in sc.segments if s.type == "pause" and s.role == "answer"]
            answers = [c["dur"] for c in cues["segments"] if c["type"] == "pause" and c["role"] == "answer"]
            for p, a in zip(planned, answers):
                self.assertGreaterEqual(a + 0.01, min(p.duration, p.floor))
            self.assertTrue(any(a < p.duration for p, a in zip(planned, answers)), "longer pauses still shrink")

    def _render_squeezed(self, sc):
        """Render with fitting forced far below the plan, so every pause hits its floor."""
        with tempfile.TemporaryDirectory() as td:
            prof = load_profile(None, "stub")
            prof.mp3 = False
            prof.fit_tolerance = 0.0
            prof.fit_min = 0.1
            cues = render_script(sc, prof, Path(td) / "l.wav", cache_dir=Path(td) / "c", progress=False, target_seconds=1)
        return [c["dur"] for c in cues["segments"] if c["type"] == "pause" and c["role"] == "answer"]

    def _long_recalls(self, timing):
        """A hinted and an unsupported recall of the same long phrase, built with ``timing``."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(CURRICULUM)
        item = max((i for i in cur.items if i.kind == "phrase"), key=lambda i: i.word_count)
        b = Builder(cur, Prompts.load("en"), timing, fresh())
        sc = Script(1, "t", cur.target_lang, cur.known_lang)
        b.recall(sc, item, "hinted")
        b.recall(sc, item, "meaning")
        hinted, unsupported = [s for s in sc.segments if s.type == "pause" and s.role == "answer"]
        return sc, hinted, unsupported

    def test_fitting_keeps_each_pauses_own_floor(self):
        """PR #107 review: the renderer keeps the floor the timing model gave each pause — a
        long hinted pause may shrink to the supported floor, unsupported recall keeps the
        recall floor, and a Timing with overridden floors is honoured after fitting."""
        sc, hinted, unsupported = self._long_recalls(Timing(level="A1"))
        self.assertGreater(hinted.duration, 2.5, "long enough that fitting would shrink it")
        self.assertEqual((hinted.floor, unsupported.floor), (1.5, 2.5))
        self.assertEqual(self._render_squeezed(sc), [1.5, 2.5])

        sc, hinted, unsupported = self._long_recalls(Timing(level="A1", min_recall_pause=3.5, min_supported_pause=2.0))
        self.assertEqual(self._render_squeezed(sc), [2.0, 3.5], "overridden floors survive fitting")

    def test_scripts_without_floors_still_render(self):
        sc, _, _ = self._long_recalls(Timing(level="A1"))
        for s in sc.segments:
            s.floor = None  # a script saved before pauses carried floors
        self.assertTrue(all(d < 1.5 for d in self._render_squeezed(sc)))

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
            prof.fit_max = 1.25  # the tolerance band is tested in both directions; stretching is off by default
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

    def test_japanese_slot_tildes_are_not_read_aloud(self):
        from audiolesson.render.renderer import _speak_tildes

        self.assertEqual(_speak_tildes("（〜したい）、", "ja"), "（したい）、")
        self.assertEqual(_speak_tildes("3〜4週間", "ja"), "3〜4週間", "between numbers it means から")
        self.assertEqual(_speak_tildes("A〜B", "en"), "A〜B", "only Japanese")

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


class ReviewQuestionTests(unittest.TestCase):
    def test_every_recalled_item_is_asked_once_with_a_text_cue(self):
        _, scripts = course(8)
        for sc in scripts:
            questions = sc.review_questions()
            asked = [i for q in questions for i in q["items"]]
            self.assertEqual(len(asked), len(set(asked)), f"lesson {sc.lesson_number}: an item asked twice")
            self.assertEqual(set(sc.meta["new_items"]) - set(asked), set(), f"lesson {sc.lesson_number}: a new item not asked")
            answers = {s.text for s in sc.segments if s.type == "answer"}
            narrations = {s.text for s in sc.segments if s.type == "narrate"}
            for q in questions:
                self.assertIn(q["answer"], answers)
                self.assertIn(q["prompt"], narrations)
                self.assertNotIn(q["stage"], ("cloze", "hinted"), "those cues rely on audio")

    def test_preferences_and_shared_sentences(self):
        sc = Script(1, "t", "is", "en")

        def recall(kind, stage, ids, *turns, hint=False):
            ex = sc.new_exercise(kind, stage, ids)
            for cue, answer in turns:
                sc.add(Segment("narrate", "instructor", cue, "en", exercise=ex.index))
                if hint:
                    sc.add(Segment("speak", "native_a", answer.split()[0], "is", role="hint", exercise=ex.index))
                sc.add(Segment("pause", role="answer", duration=3, exercise=ex.index))
                sc.add(Segment("answer", "native_a", answer, "is", exercise=ex.index))
                sc.add(Segment("pause", role="repeat", duration=2, exercise=ex.index))
                sc.add(Segment("answer", "native_a", answer, "is", exercise=ex.index))

        recall("recall", "hinted", ["a"], ("Say hello.", "Halló."), hint=True)
        recall("recall", "situation", ["a"], ("A friend walks in.", "Halló."))
        recall("recall", "meaning", ["a"], ("Say hello.", "Halló."))
        recall("generative", "recombine", ["c", "f"], ("Say: I want to go home.", "Ég vil fara heim."))
        recall("recall", "meaning", ["f"], ("Say: go home.", "fara heim"))
        recall("connect", "exchange", ["b", "a"], ("Greet her.", "Hæ."), ("Answer.", "Allt gott."))

        by_item = {i: q for q in sc.review_questions() for i in q["items"]}
        self.assertEqual(by_item["a"]["prompt"], "A friend walks in.", "a situation beats a meaning, and a hint is skipped")
        self.assertEqual(by_item["f"]["prompt"], "Say: go home.", "an item's own recall beats a shared sentence")
        self.assertEqual(by_item["c"]["items"], ["c"], "the shared sentence only asks about what nothing else covers")
        self.assertEqual(by_item["c"]["answer"], "Ég vil fara heim.")
        self.assertEqual(by_item["b"]["answer"], "Hæ.", "a two-turn exchange maps answers to items in order")

    def test_plan_json_carries_the_questions(self):
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            learner = Path(td) / "learner.json"
            main(["generate", "-c", str(CURRICULUM), "-l", str(learner), "-o", td, "-m", "5", "--no-audio", "--date", "2026-09-18"])
            plan = json.loads((Path(td) / "lesson-001.plan.json").read_text())
            asked = {i for q in plan["review"] for i in q["items"]}
            self.assertEqual({i["id"] for i in plan["new_items"]} - asked, set())
            self.assertIsInstance(plan["review_candidates"], list)

    def test_review_candidates(self):
        """Issue #128: concrete things for the learner to confirm or reject after a lesson —
        a new item last heard early, and a new item never produced without a hint in the
        last third. The same situation asked twice is not one: hearing an item in its scene
        again is practice, not a fault."""
        sc = Script(1, "t", "is", "en")
        sc.meta["new_items"] = ["early", "hinted_late", "fine"]

        def ex(kind, stage, ids, start, cue="Say it.", hint=False):
            e = sc.new_exercise(kind, stage, ids)
            e.start, e.duration = start, 10
            sc.add(Segment("narrate", "instructor", cue, "en", exercise=e.index))
            if hint:
                sc.add(Segment("speak", "native_a", "Ég", "is", role="hint", exercise=e.index))
            if kind not in ("closing",):
                sc.add(Segment("pause", role="answer", duration=3, exercise=e.index))

        ex("intro", "intro", ["early"], 0)
        ex("recall", "situation", ["old"], 10, "A friend walks in.")
        ex("recall", "meaning", ["early"], 100)
        ex("intro", "intro", ["hinted_late"], 200)
        ex("recall", "situation", ["old"], 300, "A friend walks in.")
        ex("recall", "situation", ["old"], 400, "Another friend walks in.")
        ex("recall", "meaning", ["hinted_late"], 450)
        ex("intro", "intro", ["fine"], 500)
        ex("recall", "hinted", ["hinted_late"], 800, hint=True)
        ex("recall", "situation", ["fine"], 850, "Your host asks.")
        ex("closing", None, [], 890)
        got = [(c["kind"], c["items"]) for c in sc.review_candidates()]
        self.assertEqual(got, [
            ("early_last_appearance", ["early"]),
            ("no_late_recall", ["hinted_late"]),
        ])
        by_kind = {c["kind"]: c for c in sc.review_candidates()}
        self.assertEqual((by_kind["early_last_appearance"]["last_s"], by_kind["early_last_appearance"]["end_s"]), (110, 900))
        self.assertEqual(by_kind["no_late_recall"]["last_recall_s"], 450)

    def test_a_late_bridge_exchange_counts_as_an_unhinted_recall(self):
        """PR #130 review: a bridge exchange (connect, stage "exchange") asks the learner to
        answer the partner with no hint, so producing a new item there late in the lesson is
        a late recall — no ``no_late_recall`` for it. A hint spoken inside the same kind of
        exercise still doesn't count."""
        def lesson(hint):
            sc = Script(1, "t", "is", "en")
            sc.meta["new_items"] = ["eg_lika"]
            for kind, stage, start, cue in (("intro", "intro", 0, "New."), ("recall", "meaning", 100, "Say: me too."),
                                            ("connect", "exchange", 700, "Anna says she's tired. Answer her.")):
                e = sc.new_exercise(kind, stage, ["eg_lika"] if kind != "connect" else ["thu_ert_threytt", "eg_lika"])
                e.start, e.duration = start, 10
                sc.add(Segment("narrate", "instructor", cue, "en", exercise=e.index))
                if kind == "connect" and hint:
                    sc.add(Segment("speak", "native_a", "Ég", "is", role="hint", exercise=e.index))
                sc.add(Segment("pause", role="answer", duration=3, exercise=e.index))
                sc.add(Segment("answer", "native_a", "Ég líka.", "is", exercise=e.index))
            end = sc.new_exercise("closing", None, [])
            end.start, end.duration = 890, 10
            return sc.review_candidates()

        self.assertEqual(lesson(hint=False), [])
        (c,) = lesson(hint=True)
        self.assertEqual((c["kind"], c["last_recall_s"]), ("no_late_recall", 100))


class CliTests(unittest.TestCase):
    def test_generate_report_status(self):
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            learner = Path(td) / "learner.json"
            rc = main(["generate", "-c", str(CURRICULUM), "-l", str(learner), "-o", td, "-m", "3", "--new", "3", "--no-audio", "--date", "2026-09-18"])  # --new: this counts items; the target is a share of 30 minutes (#242)
            self.assertEqual(rc, 0)
            self.assertTrue((Path(td) / "lesson-001.script.json").exists())
            self.assertTrue((Path(td) / "lesson-001.transcript.md").exists())
            plan = json.loads((Path(td) / "lesson-001.plan.json").read_text())
            first = plan["new_items"][0]["id"]
            self.assertEqual(main(["report", "-l", str(learner), "--failed", first, "--date", "2026-09-19"]), 0)
            others = [i["id"] for i in plan["new_items"][1:3]]
            self.assertEqual(main(["report", "-l", str(learner), "--lesson", "1", "--hesitated", others[0], "--recalled", others[1], "--date", "2026-09-19"]), 0)
            items = json.loads(learner.read_text())["items"]
            self.assertEqual((items[others[0]]["hesitated"], items[others[1]]["recalled"]), (1, 1))
            self.assertEqual(main(["status", "-l", str(learner), "-c", str(CURRICULUM)]), 0)
            rc = main(["generate", "-c", str(CURRICULUM), "-l", str(learner), "-o", td, "-m", "3", "--provider", "stub", "--date", "2026-09-20"])
            self.assertEqual(rc, 0)
            self.assertTrue((Path(td) / "lesson-002.wav").exists())

    def test_generate_cache_can_be_shared_between_learners(self):
        """--cache puts the TTS clips in one place: a second learner re-uses the first's
        clips (the file name hashes provider, voice, rate, language and text)."""
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            cache = Path(td) / "tts-cache"
            for name in ("a", "b"):
                out = Path(td) / name
                rc = main(["generate", "-c", str(CURRICULUM), "-l", str(out / "learner.json"), "-o", str(out),
                           "-m", "3", "--provider", "stub", "--cache", str(cache), "--date", "2026-09-18"])
                self.assertEqual(rc, 0)
                self.assertFalse((out / "cache").exists(), "nothing cached under --out")
                if name == "a":
                    clips = sorted(cache.iterdir())
                    self.assertTrue(clips)
            self.assertEqual(sorted(cache.iterdir()), clips, "the same lesson adds no new clips")
            self.assertFalse([c for c in clips if c.suffix != ".wav"], "no temp file left behind")

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


class CandoTests(unittest.TestCase):
    """Issue #131: travel can-do scenarios as the course's outcome, with coverage and
    reachability reports."""

    def test_the_travel_scenarios_load_and_name_real_items(self):
        from audiolesson.cando import TIERS, load_cando

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", cur)
        self.assertGreaterEqual(len(scenarios), 20)
        self.assertEqual({s.tier for s in scenarios}, set(TIERS))
        for s in scenarios:
            self.assertTrue(s.title and s.success, s.id)
            if s.tier in ("A", "B"):
                self.assertTrue(s.items or s.missing, s.id)
        # the can-do directory is not a curriculum module
        self.assertNotIn("A1", cur.by_id)

    def test_scenarios_stay_generic(self):
        """Personal trip details live in a private profile (#132), never in the repo."""
        text = "\n".join(p.read_text("utf-8") for p in (ROOT / "curricula" / "is-en" / "cando").glob("*.toml"))
        self.assertIsNone(re.search(r"\b(19|20)\d\d-\d\d-\d\d\b", text))

    def test_bad_scenarios_are_rejected(self):
        from audiolesson.cando import load_cando

        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
                                    "items": [{"id": "takk", "kind": "phrase", "target": "Takk.", "meaning": "Thanks."}]})
        for body, message in (('id = "A1"\ntier = "A"\ntitle = "t"\nitems = ["nope"]', "unknown items"),
                              ('id = "A1"\ntier = "Z"\ntitle = "t"', "tier"),
                              ('id = "A1"\ntier = "A"\ntitle = "t"\ncolour = "red"', "colour")):
            with tempfile.TemporaryDirectory() as td:
                (Path(td) / "cando").mkdir()
                (Path(td) / "cando" / "t.toml").write_text("[[scenarios]]\n" + body, "utf-8")
                with self.assertRaises(CurriculumError) as ctx:
                    load_cando(td, cur)
                self.assertIn(message, str(ctx.exception))
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(load_cando(td, cur), [])

    def test_coverage_flags_what_misses_the_tier_milestone(self):
        from audiolesson.cando import Scenario, coverage, format_coverage, milestone_lesson

        self.assertEqual((milestone_lesson("A", 84), milestone_lesson("B", 84), milestone_lesson("C", 84)), (35, 56, None))
        self.assertEqual(milestone_lesson("A", 40), 0, "the milestone already passed")
        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
                                    "items": [{"id": i, "kind": "phrase", "target": i, "meaning": i} for i in ("a", "b", "c")]})
        scenarios = [Scenario("A1", "A", "early", items=["a", "b"], missing=["x"]), Scenario("B1", "B", "late", items=["c"])]
        reach = {6: {"a": 3, "b": 40}, 10: {"a": 2, "b": 20, "c": 50}}
        rows = coverage(cur, scenarios, reach, 84)
        self.assertEqual(rows[0]["late"], {6: ["b"]})
        self.assertEqual(rows[1]["late"], {6: ["c"]}, "never reached counts as late; 50 ≤ 56 is in time")
        text = format_coverage(rows, 84, [6, 10])
        self.assertIn("late at pace 6 (due lesson 35): b", text)
        self.assertIn("missing: x", text)

    def test_a_passed_milestone_is_reported_overdue_not_hidden(self):
        """PR #137 review: with six weeks left, Tier A's T−7-week milestone has passed; the
        report must show every Tier A item as overdue, not grade nothing."""
        from audiolesson.cando import Scenario, coverage, format_coverage

        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
                                    "items": [{"id": i, "kind": "phrase", "target": i, "meaning": i} for i in ("a", "b", "c")]})
        scenarios = [Scenario("A1", "A", "must", items=["a", "b"]), Scenario("B1", "B", "should", items=["c"]),
                     Scenario("C1", "C", "nice", items=["a"])]
        rows = coverage(cur, scenarios, {10: {"a": 1, "b": 3, "c": 9}}, 42)
        self.assertEqual((rows[0]["due"], rows[0]["overdue"], rows[0]["late"]), (0, True, {10: ["a", "b"]}))
        self.assertEqual((rows[1]["due"], rows[1]["late"]), (14, {}), "Tier B still has a window")
        self.assertEqual((rows[2]["due"], rows[2]["overdue"], rows[2]["late"]), (None, False, {}), "Tier C has no milestone")
        text = format_coverage(rows, 42, [10])
        self.assertIn("Tier A: milestone (T−7 weeks) already passed", text)
        self.assertIn("overdue at pace 10 (milestone already passed): a, b", text)
        self.assertIn("Tier B due by lesson 14", text)
        self.assertNotIn("None", text)

    def test_the_report_rejects_an_empty_horizon(self):
        import contextlib
        import io
        from audiolesson.cli import main

        for args in (["--lessons", "0"], ["--lessons", "-3"], ["--paces", ","], ["--paces", "6,0"]):
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                code = main(["validate", str(ROOT / "curricula" / "is-en"), "--cando", *args])
            self.assertNotEqual(code, 0, args)
            self.assertIn("must", err.getvalue(), args)

    def test_reach_is_the_lesson_an_item_is_first_met(self):
        from audiolesson.cando import simulate_reach

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        reach = simulate_reach(cur, 2, 4)
        self.assertEqual(reach["godan_daginn"], 1)
        self.assertEqual(set(reach.values()), {1, 2})
        self.assertNotIn("goda_ferd", reach)

    def test_validate_reports_cando_coverage(self):
        import contextlib
        import io
        from audiolesson.cli import main

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["validate", str(ROOT / "curricula" / "is-en"), "--cando", "--lessons", "2", "--paces", "3"]), 0)
        self.assertIn("can-do coverage for a horizon of 2 daily lessons", out.getvalue())
        self.assertIn("A3 [A] Supermarket", out.getvalue())


class TripProfileTests(unittest.TestCase):
    """Issue #132: a private trip profile orders the can-do items (#131) first and
    keeps the learner's pace whatever the departure date, without its contents reaching any
    output."""

    def test_profile_parsing(self):
        from audiolesson.trip import TripError, load_trip

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "trip.toml"
            p.write_text('departure = 2030-01-31\nboost = ["A6"]\nplaces = ["Staðurinn"]\n', "utf-8")
            trip = load_trip(p)
            self.assertEqual((trip.departure, trip.boost, trip.places), (date(2030, 1, 31), ["A6"], ["Staðurinn"]))
            self.assertEqual(len(trip.digest), 64)
            self.assertEqual(trip.days_left(date(2030, 1, 21)), 10)
            for bad in ('hotel = "x"', 'departure = "soon"', 'boost = "A6"'):
                p.write_text(bad, "utf-8")
                with self.assertRaises(TripError):
                    load_trip(p)
            p.write_text("", "utf-8")
            self.assertIsNone(load_trip(p).departure)

    def test_priority_items_bring_prereqs_and_keep_tier_order(self):
        from audiolesson.cando import Scenario, priority_items

        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": [
            {"id": "a", "kind": "phrase", "target": "a", "meaning": "a"},
            {"id": "b", "kind": "phrase", "target": "b", "meaning": "b"},
            {"id": "c", "kind": "phrase", "target": "c", "meaning": "c", "prereqs": ["a"]},
            {"id": "d", "kind": "phrase", "target": "d", "meaning": "d"},
            {"id": "e", "kind": "phrase", "target": "e", "meaning": "e"},
        ]})
        scenarios = [Scenario("A1", "A", "t", items=["c"]), Scenario("B1", "B", "t", items=["b", "c"]),
                     Scenario("C1", "C", "t", items=["e"])]
        self.assertEqual(priority_items(cur, scenarios), ["a", "c", "b"])
        self.assertEqual(priority_items(cur, scenarios, ["C1", "nope"]), ["e", "a", "c", "b"])

    def test_seasonal_content_follows_the_profile_season(self):
        """PR #138 review: holiday greetings must not be Tier A for a summer trip. Seasonal
        scenarios and seasonal items apply only when the profile's season matches."""
        from audiolesson.cando import Scenario, for_season, priority_items

        cur = curriculum_from_dict({"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}, "items": [
            {"id": i, "kind": "phrase", "target": i, "meaning": i} for i in ("hello", "xmas", "newyear", "bonfire")]})
        scenarios = [Scenario("A1", "A", "greet", items=["hello"], seasonal={"winter-holidays": ["xmas", "newyear"]}),
                     Scenario("C2", "C", "traditions", items=["bonfire"], season="winter-holidays")]
        self.assertEqual(priority_items(cur, for_season(scenarios, "summer")), ["hello"])
        self.assertEqual(priority_items(cur, for_season(scenarios, None)), ["hello"], "no profile season: none")
        self.assertEqual(priority_items(cur, for_season(scenarios, "winter-holidays")), ["hello", "xmas", "newyear"])
        self.assertEqual([s.id for s in for_season(scenarios, "summer")], ["A1"])
        self.assertEqual(priority_items(cur, for_season(scenarios, "winter-holidays"), ["C2"])[0], "bonfire")
        self.assertEqual(scenarios[0].items, ["hello"], "the loaded scenario is not modified")

    def test_the_planner_introduces_priority_items_first(self):
        raw = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
               "items": [{"id": f"i{n}", "kind": "phrase", "target": f"Orð {n} hér.", "meaning": f"word {n}"} for n in range(12)]}
        raw["items"][11]["prereqs"] = ["i10"]
        cur = curriculum_from_dict(raw)

        def first_lesson(priority):
            sc = Planner(cur, fresh(), Prompts.load("en"), Timing(level="A1"),
                         PlanConfig(minutes=10, new_items=3, seed=1, priority=priority), today=TODAY).build()
            return sc.meta["new_items"][:3], sc.meta["config"]["priority_items"]

        self.assertEqual(first_lesson([]), (["i0", "i1", "i2"], 0))
        self.assertEqual(first_lesson(["i10", "i11"]), (["i10", "i11", "i0"], 2))

    def test_trip_ordering_reaches_every_tier_a_and_b_item_in_time(self):
        """#132's target: at pace 6, Tier A met by T−7 weeks and Tier B by T−4 weeks
        (84 daily lessons: lessons 35 and 56). Without the ordering, both miss it (#131)."""
        from audiolesson.cando import coverage, load_cando, priority_items, simulate_reach

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", cur)
        reach = simulate_reach(cur, 84, 6, priority=priority_items(cur, scenarios))
        late = {r["scenario"].id: r["late"][6] for r in coverage(cur, scenarios, {6: reach}, 84) if r["late"].get(6)}
        self.assertEqual(late, {})

    def test_generate_with_a_trip_profile(self):
        import contextlib
        import io
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            trip = Path(td) / "trip.toml"
            trip.write_text('departure = 2026-09-28\nplaces = ["Leynistaður"]\nboost = ["A6"]\n', "utf-8")
            learner = Path(td) / "learner.json"
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["generate", "-c", str(ROOT / "curricula" / "is-en"), "-l", str(learner), "-o", td,
                             "-m", "10", "--pace", "6", "--no-audio", "--date", "2026-09-18", "--trip", str(trip)])
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn("can-do items first", text)
            self.assertNotIn("halved", text, "the pace never depends on the departure date (PR #138 review)")
            self.assertEqual(json.loads((Path(td) / "lesson-001.plan.json").read_text("utf-8"))["config"]["new_items"], 6)
            plan_text = (Path(td) / "lesson-001.plan.json").read_text("utf-8")
            for private in ("Leynistaður", "2026-09-28", "A6"):
                self.assertNotIn(private, text + plan_text)
            self.assertGreater(json.loads(plan_text)["config"]["priority_items"], 0)
            self.assertEqual(json.loads(learner.read_text("utf-8"))["pace"], 6)


class CultureRespectTests(unittest.TestCase):
    def test_the_culture_pack_fills_the_can_do_gaps(self):
        """Issue #135: the travel phrases the course lacked are items now, each tied to a
        can-do scenario (#131) and to an aside that explains when to use it."""
        from audiolesson.cando import load_cando

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", cur)
        in_scenarios = {i for s in scenarios for i in s.items + [x for v in s.seasonal.values() for x in v]}
        noted = {i for n in cur.notes for i in n.items}
        added = ["gledileg_jol", "gledilega_hatid", "gledilegt_nytt_ar", "gledilegt_nytt_ar_takk_fyrir_thad_lidna",
                 "takk_fyrir_mig", "ma_eg_reyna_ad_tala_islensku", "til_ad_taka_med", "eg_aetla_ad_borda_herna",
                 "einn_fullordinn_takk"]
        for i in added:
            self.assertIn(i, cur.by_id, i)
            self.assertIn(i, in_scenarios, i)
        for i in ("gledileg_jol", "gledilegt_nytt_ar", "takk_fyrir_mig", "ma_eg_reyna_ad_tala_islensku", "einn_fullordinn_takk"):
            self.assertIn(i, noted, i)
        self.assertFalse([m for s in scenarios for m in s.missing if "#135" in m], "no #135 gap left open")
        # seasonal content comes last in the default order; the trip ordering brings it forward
        # only for a trip in its season (PR #138 review)
        self.assertGreater(cur.by_id["gledileg_jol"].order, cur.by_id["ferdin_var_frabaer"].order)
        from audiolesson.cando import for_season, priority_items

        summer = priority_items(cur, for_season(scenarios, "summer"))
        winter = priority_items(cur, for_season(scenarios, "winter-holidays"))
        self.assertNotIn("gledileg_jol", summer)
        self.assertIn("gledileg_jol", winter)


class ScenarioCardTests(unittest.TestCase):
    """#129: scripted scenario cards replace the GPT Voice role-play."""

    def setUp(self):
        from audiolesson.cando import load_cando
        from audiolesson.scenes import load_scenes

        self.cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.scenarios = load_cando(ROOT / "curricula" / "is-en", self.cur)
        self.scenes = load_scenes(ROOT / "curricula" / "is-en", self.cur, self.scenarios)

    def test_every_tier_a_scenario_has_a_card(self):
        from audiolesson.scenes import uncovered

        self.assertEqual(uncovered(self.scenes, self.scenarios, "A"), [])
        self.assertGreaterEqual(len(self.scenes), 30)

    def test_a_local_who_speaks_first_gets_a_respond_card(self):
        """The clerk lines the pilots showed were not understood are practised."""
        partners = {s.partner for s in self.scenes if s.kind == "respond"}
        for line in ("Viltu poka?", "Viltu kvittun?", "Hvað má bjóða þér?", "Eitthvað fleira?", "Gjörðu svo vel."):
            self.assertIn(line, partners)

    def test_cards_appear_once_their_items_are_met_and_in_their_season(self):
        from audiolesson.cando import for_season
        from audiolesson.scenes import available

        summer = for_season(self.scenarios, None)
        self.assertEqual(available(self.scenes, summer, None, set()), [])
        shown = available(self.scenes, summer, None, {"godan_daginn", "takk", "bless"})
        self.assertEqual({s.id for s in shown}, {"a1_enter", "a1_leave", "a2_change"})
        everything = {i.id for i in self.cur.items}
        self.assertNotIn("a1_holidays", [s.id for s in available(self.scenes, summer, None, everything)])
        winter = for_season(self.scenarios, "winter-holidays")
        self.assertIn("a1_holidays", [s.id for s in available(self.scenes, winter, "winter-holidays", everything)])

    def test_bad_cards_are_rejected(self):
        from audiolesson.cando import load_cando
        from audiolesson.scenes import load_scenes

        base = 'id = "x"\nscenario = "A1"\nsituation = "s"\nreplies = ["Takk."]\nitems = ["takk"]\n'
        for body, message in (
            (base + 'kind = "chat"', "kind"),
            (base + 'kind = "respond"', "partner"),
            (base + 'kind = "initiate"\npartner = "Hæ."', "no partner"),
            (base.replace('["Takk."]', "[]") + 'kind = "initiate"', "replies"),
            (base.replace('"A1"', '"Z9"') + 'kind = "initiate"', "unknown scenarios"),
            (base.replace('["takk"]', '["nope"]') + 'kind = "initiate"', "unknown items"),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as td:
                (Path(td) / "cando").mkdir()
                (Path(td) / "cando" / "scenes.toml").write_text("[[scenes]]\n" + body, "utf-8")
                with self.assertRaises(CurriculumError) as ctx:
                    load_scenes(td, self.cur, load_cando(ROOT / "curricula" / "is-en", self.cur))
                self.assertIn(message, str(ctx.exception))

    def test_scenes_cli_prints_the_cards_a_learner_can_take(self):
        import contextlib
        import io

        from audiolesson.cli import main

        def run(*extra):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(main(["scenes", str(ROOT / "curricula" / "is-en"), *extra]), 0)
            return json.loads(buf.getvalue())

        every = run()
        self.assertEqual({c["tier"] for c in every}, {"A", "B"})
        self.assertTrue(all(c["title_ja"] for c in every))
        self.assertEqual(run("--learner", "/nonexistent/learner.json"), [], "nothing met yet")
        with tempfile.TemporaryDirectory() as td:
            learner = LearnerState("is", "ja", "A1")
            learner.items["godan_daginn"] = ItemState(due=TODAY.isoformat())
            learner.save(Path(td) / "l.json")
            self.assertEqual([c["id"] for c in run("--learner", str(Path(td) / "l.json"))], ["a1_enter"])


class ReadingDeckTests(unittest.TestCase):
    """Issue #133: a reading deck for the Discord review, since the audio never shows
    spelling — letters, signs, shop words, place names and their parts."""

    def test_the_deck_covers_every_stage_and_every_can_do_reading_text(self):
        from audiolesson.cando import load_cando
        from audiolesson.reading import STAGES, load_deck, texts

        cards = load_deck(ROOT / "curricula" / "is-en")
        self.assertGreaterEqual(len(cards), 80)
        self.assertEqual([c.stage for c in cards], sorted((c.stage for c in cards), key=STAGES.index))
        self.assertEqual({c.stage for c in cards}, set(STAGES))
        for c in cards:
            self.assertTrue(c.meaning_ja and c.hint_ja, c.id)
        deck = texts(cards)
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        for s in load_cando(ROOT / "curricula" / "is-en", cur):
            self.assertEqual([r for r in s.reading if r.casefold() not in deck], [], s.id)
        raw = "\n".join(p.read_text("utf-8") for p in (ROOT / "curricula" / "is-en" / "reading").glob("*.toml"))
        self.assertIsNone(re.search(r"\b(19|20)\d\d-\d\d-\d\d\b", raw), "general content only")

    def test_own_places_come_from_the_profile_at_run_time(self):
        from audiolesson.reading import load_deck

        cards = load_deck(ROOT / "curricula" / "is-en", ["Reykjavík", "Leynistaður"])
        own = [c for c in cards if c.own]
        self.assertEqual([c.text for c in own], ["Leynistaður"], "a place already in the deck is not repeated")
        self.assertEqual(own[0].stage, "places")

    def test_letters_cards_gloss_every_word_they_list(self):
        """A letters card's ``meaning`` is its spelling rule («þ: the 'th' of 'think'»), so its
        words' meanings are glossed one by one (owner: the answer showed no meaning)."""
        from audiolesson.reading import load_deck

        letters = [c for c in load_deck(ROOT / "curricula" / "is-en") if c.stage == "letters"]
        self.assertTrue(letters)
        for c in letters:
            with self.subTest(card=c.id):
                listed = [t.strip() for t in c.text.split("·")]
                self.assertEqual([w for w, _ in c.words], listed)
                self.assertTrue(all(g.strip() for _, g in c.words))

    def test_a_letters_rule_always_has_an_example_and_a_word_a_rule(self):
        """Owner, after a real review: «Góða nótt · Sjáumst» stated the rule for 'au', yet no
        listed word has an 'au' («sjáumst» has á + u). A letters card names the letters it
        teaches, and the words must show them, and each word one of them."""
        from audiolesson.reading import load_deck

        card = ('[[cards]]\nid = "x"\nstage = "letters"\ntext = "{text}"\nmeaning = "rule"\n'
                'words = [{words}]\ngraphemes = {graphemes}\n')
        words = '["Góða nótt", "おやすみ"], ["Sjáumst", "またね"]'
        for graphemes, message in (('["ó", "au"]', "no listed word shows"),
                                   ('["ó"]', "show none of")):
            with self.subTest(graphemes=graphemes), tempfile.TemporaryDirectory() as td:
                (Path(td) / "reading").mkdir()
                (Path(td) / "reading" / "d.toml").write_text(
                    card.format(text="Góða nótt · Sjáumst", words=words, graphemes=graphemes), "utf-8")
                with self.assertRaises(CurriculumError) as ctx:
                    load_deck(td)
                self.assertIn(message, str(ctx.exception))
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "reading").mkdir()
            (Path(td) / "reading" / "d.toml").write_text(
                card.format(text="Góða nótt · Sól", words='["Góða nótt", "おやすみ"], ["Sól", "太陽"]',
                            graphemes='["ó"]'), "utf-8")
            self.assertEqual([c.id for c in load_deck(td)], ["x"])
        for c in load_deck(ROOT / "curricula" / "is-en"):
            if c.stage == "letters":
                self.assertTrue(c.graphemes, c.id)

    def test_bad_cards_are_rejected(self):
        from audiolesson.reading import load_deck

        for body, message in (('id = "x"\nstage = "menus"\ntext = "a"\nmeaning = "b"', "stage"),
                              ('id = "x"\nstage = "signs"\ntext = ""\nmeaning = "b"', "required"),
                              ('id = "x"\nstage = "signs"\ntext = "a"\nmeaning = "b"\nparts = [["a"]]', "pairs"),
                              ('id = "x"\nstage = "letters"\ntext = "a · b"\nmeaning = "rule"', "glosses its words"),
                              ('id = "x"\nstage = "letters"\ntext = "a · b"\nmeaning = "rule"\nwords = [["b", "B"], ["a", "A"]]', "in order"),
                              ('id = "x"\nstage = "signs"\ntext = "a"\nmeaning = "b"\nwords = [["a"]]', "pairs"),
                              ('id = "x"\nstage = "letters"\ntext = "a"\nmeaning = "rule"\nwords = [["a", "A"]]', "names the letters"),
                              ('id = "x"\nstage = "signs"\ntext = "a"\nmeaning = "b"\ngraphemes = ["a"]', "only a letters card")):
            with tempfile.TemporaryDirectory() as td:
                (Path(td) / "reading").mkdir()
                (Path(td) / "reading" / "d.toml").write_text("[[cards]]\n" + body, "utf-8")
                with self.assertRaises(CurriculumError) as ctx:
                    load_deck(td)
                self.assertIn(message, str(ctx.exception))

    def test_reading_cli_prints_the_deck_as_json(self):
        import contextlib
        import io
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            trip = Path(td) / "trip.toml"
            trip.write_text('places = ["Leynistaður"]\n', "utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["reading", str(ROOT / "curricula" / "is-en"), "--trip", str(trip)]), 0)
        cards = json.loads(out.getvalue())
        self.assertEqual(cards[0]["stage"], "letters")
        self.assertIn({"id": "own_1", "text": "Leynistaður", "own": True},
                      [{k: c[k] for k in ("id", "text", "own")} for c in cards])


class LeverTests(unittest.TestCase):
    """Issue #136: planner levers as settings, off by default, each with the metric that
    shows its effect (the #130 review candidates)."""

    @staticmethod
    def _candidates(lessons=8, **levers):
        from collections import Counter

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day, kinds = LearnerState("is", "en", "A1"), TODAY, Counter()
        for n in range(1, lessons + 1):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"),
                         PlanConfig(minutes=30, new_items=8, seed=n, **levers), today=day).build()
            kinds.update(c["kind"] for c in sc.review_candidates())
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        return kinds, sc

    def test_a_situation_is_narrated_in_full_twice_then_the_cue_is_short(self):
        """§9 "Repetition" (G12): an item with one situation is asked in that situation, narrated
        in full at most twice a lesson; after that the cue is the meaning, short."""
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        item = next(i for i in cur.items if i.kind == "phrase" and i.situation and not i.situations and not i.situation_fill)
        learner = fresh()
        learner.items[item.id] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="situation")
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
        sc = Script(1, "t", "is", "en")
        self.assertEqual([b.recall(sc, item, "situation").stage for _ in range(3)], ["situation", "situation", "meaning"])

    def test_late_unhinted_recall_closes_every_new_item_without_a_hint(self):
        late, sc = self._candidates(late_unhinted_recall=True)
        self.assertEqual(late["no_late_recall"] + late["early_last_appearance"], 0)
        self.assertEqual(sc.meta["config"]["levers"], {"late_unhinted_recall": True})

    def test_levers_pass_through_the_cli(self):
        import contextlib
        import io
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            with contextlib.redirect_stdout(io.StringIO()):
                main(["generate", "-c", str(ROOT / "curricula" / "is-en"), "-l", str(Path(td) / "l.json"), "-o", td,
                      "-m", "10", "--no-audio", "--date", "2026-09-18", "--late-unhinted-recall"])
            levers = json.loads((Path(td) / "lesson-001.plan.json").read_text("utf-8"))["config"]["levers"]
        self.assertEqual(levers, {"late_unhinted_recall": True})


class SpokenMeaningTests(unittest.TestCase):
    """Recall disambiguators written in brackets («English (the language)», «本（〜は・〜が）»)
    were read aloud verbatim. ``meaning_spoken`` folds them into natural speech; the
    written ``meaning`` stays for glosses."""

    def test_the_spoken_form_is_per_language_and_never_borrowed(self):
        en = load_curriculum(ROOT / "curricula" / "is-en")
        ja = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")
        self.assertEqual(en.by_id["hotelinu"].spoken_meaning, "to the hotel")
        self.assertEqual(en.by_id["hotelinu"].meaning, "the hotel (after 'to' / 'for')")
        self.assertEqual(ja.by_id["hotelinu"].spoken_meaning, "ホテルへ")
        self.assertEqual(en.by_id["ensku"].spoken_meaning, "the English language")
        # English's spoken form never reaches a Japanese instruction: 英語 is unambiguous
        self.assertEqual(ja.by_id["ensku"].spoken_meaning, "英語")
        self.assertEqual(ja.by_id["vinna_verb"].spoken_meaning, "働く")
        self.assertEqual(ja.by_id["bok"].spoken_meaning, "本が")
        self.assertEqual(en.by_id["bok"].spoken_meaning, "book", "no spoken form: the meaning")

    def test_no_grammar_form_disambiguator_is_spoken(self):
        """Every bracket that names a grammatical form has a spoken form (issue: category A)."""
        form = re.compile(r"\(after |\(the language\)|\(the\)|\(to work\)|（〜|（複数：〜|（「Takk fyrir")
        for lang in (None, "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            for it in cur.items:
                if form.search(it.meaning):
                    with self.subTest(lang=lang, item=it.id):
                        self.assertNotRegex(it.spoken_meaning, r"[()（）〜]")

    def test_prompts_speak_the_spoken_form(self):
        from audiolesson.exercises import Builder

        cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")
        b = Builder(cur, Prompts.load("ja"), Timing(level="A1"), fresh())
        sc = Script(1, "Lesson 1", cur.target_lang, cur.known_lang)
        b.intro(sc, cur.by_id["hotelinu"])
        for stage in ("hinted", "meaning"):
            b.recall(sc, cur.by_id["hotelinu"], stage)
        spoken = " ".join(s.text for s in sc.segments if s.type == "narrate")
        self.assertIn("ホテルへ", spoken)
        self.assertNotIn("〜", spoken)
        self.assertNotIn("（", spoken)

    def test_nothing_in_brackets_is_spoken_anywhere(self):
        """Owner, lesson 12: «Say: Skyr (Icelandic yoghurt-like dairy).» Every narrated gloss,
        in every curriculum and instructor language, is bracket-free (validation enforces it)."""
        for path, langs in ((ROOT / "curricula" / "is-en", (None, "ja")), (ROOT / "curricula" / "fr-en-a1.toml", (None, "ja")), (ROOT / "curricula" / "fr-ja-a1.toml", (None,))):
            for lang in langs:
                cur = load_curriculum(path, known_lang=lang)
                for it in cur.items:
                    if it.kind != "transform":
                        self.assertNotRegex(it.spoken_meaning, r"[()（）〜～]", (path.name, lang, it.id))
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertEqual(cur.by_id["skyr"].spoken_meaning, "skyr, the Icelandic dairy")
        self.assertEqual(cur.by_id["ertu_state"].spoken_meaning, "to a woman: Are you {state}?")

    def test_a_construction_narrates_its_spoken_meaning(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        c = cur.by_id["ertu_state"]
        fill = next(i for i in cur.items_with_tag(c.slots["state"]))
        self.assertNotIn("(", cur.resolve_slots(c, {"state": fill})[1])

    def test_a_bracketed_meaning_without_a_spoken_form_is_rejected(self):
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": "a", "kind": "vocab", "target": "a", "meaning": "a (b)"}],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)
        raw["items"][0]["meaning_spoken"] = "a, b"
        self.assertEqual(curriculum_from_dict(raw).by_id["a"].spoken_meaning, "a, b")

    def test_a_spoken_form_takes_no_brackets(self):
        raw = {
            "curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"},
            "items": [{"id": "a", "kind": "vocab", "target": "a", "meaning": "a (b)", "meaning_spoken": "a (b)"}],
        }
        with self.assertRaises(CurriculumError):
            curriculum_from_dict(raw)


if __name__ == "__main__":
    unittest.main()
