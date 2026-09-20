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
        total without that being a rationing failure."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        self.assertGreaterEqual(len(cur.notes), 40)
        learner = LearnerState("is", "en", "A1")
        learner.feedback_mode = "auto"
        day = TODAY
        heard: list[str] = []
        for _ in range(12):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=2), today=day).build()
            notes = [e for e in sc.exercises if e.kind == "note"]
            asides = [e for e in notes if not cur.note_by_id[e.label.split(": ")[1]].milestone]
            self.assertLessEqual(len(asides), 2)
            for e in notes:
                note = cur.note_by_id[e.label.split(": ")[1]]
                if not note.milestone:
                    self.assertNotIn(note.id, heard, "no aside repeats while unheard asides remain")
                heard.append(note.id)
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
        self.assertGreater(len(heard), 4)
        self.assertEqual(sum(learner.notes_heard.values()), len(heard))

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
        learner.feedback_mode = "auto"
        day = TODAY
        fired: set[str] = set()
        for _ in range(20):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=3), today=day).build()
            played = {e.label.split(": ")[1] for e in sc.exercises if e.kind == "note" and e.label.split(": ")[1] in milestones}
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
            for note_id in played:
                self.assertTrue(
                    all(learner.has_met(i) for i in milestones[note_id]),
                    f"{note_id} fired in a lesson that didn't end up knowing all its items",
                )
                fired.add(note_id)
        self.assertEqual(fired, set(milestones), "not every milestone note fired across 20 simulated lessons")

    def test_milestone_note_is_followed_by_contrastive_discrimination(self):
        """Issue #34 point 2: right after a milestone plays, the lesson must immediately
        switch between two *different* of its own already-known examples ("notice, name,
        discriminate") — reusing each item's own ``situation`` (all of both milestones' items
        have one) — never just one recall (that would be retrieval, not discrimination) and
        never zero (owner review on #38: a milestone that fires must complete its
        discrimination block even if the lesson runs slightly over its nominal time target).
        Checked for every milestone note in the curriculum, not just ``godur_gender``."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        milestones = {n.id: set(n.items) for n in cur.notes if n.milestone}
        self.assertGreaterEqual(len(milestones), 2)
        learner = LearnerState("is", "en", "A1")
        learner.feedback_mode = "auto"
        day = TODAY
        checked: set[str] = set()
        for _ in range(20):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15, seed=3), today=day).build()
            note_positions = [(i, e.label.split(": ")[1]) for i, e in enumerate(sc.exercises) if e.kind == "note" and e.label.split(": ")[1] in milestones]
            apply_to_learner(sc, learner, day)
            day += timedelta(days=1)
            for note_idx, note_id in note_positions:
                gate_ids = milestones[note_id]
                self.assertGreater(len(sc.exercises), note_idx + 2, f"{note_id} wasn't followed by two discrimination exercises")
                first, second = sc.exercises[note_idx + 1], sc.exercises[note_idx + 2]
                for ex in (first, second):
                    self.assertEqual((ex.kind, ex.stage), ("recall", "situation"))
                    self.assertEqual(len(ex.item_ids), 1)
                    self.assertIn(ex.item_ids[0], gate_ids)
                self.assertNotEqual(first.item_ids[0], second.item_ids[0])
                checked.add(note_id)
        self.assertEqual(checked, set(milestones), "not every milestone note fired across 20 simulated lessons")

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
                for slot in it.slot_names:
                    self.assertIn("{" + slot + "}", it.meaning, f"{it.id}: slot missing from Japanese meaning")
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
        human to act on, same as the owner's own worked example (a real dialogue in the
        Icelandic course needing a word from item #926 of 993)."""
        from audiolesson.content import dialogue_sequencing_report

        cur = load_curriculum(ROOT / "curricula" / "is-en")
        findings = dialogue_sequencing_report(cur)
        self.assertTrue(findings)
        worst = findings[0]
        self.assertEqual(worst["dialogue"], "nagranni")
        self.assertEqual(worst["word"], "heyra")
        self.assertGreater(worst["gap"], 900)
        # never gates: the flagged item isn't part of what actually decides eligibility
        dlg = cur.dialogue_by_id["nagranni"]
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
