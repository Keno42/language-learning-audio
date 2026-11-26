"""A lesson's structure: its sections, voices, reviews, open and embedded items, spare time (split from test_audiolesson.py)."""
from __future__ import annotations

from tests.audiolesson_common import *  # noqa: F401,F403




class LessonStructureTests(unittest.TestCase):
    def setUp(self):
        self.script = build(fresh(), new_items=12)  # a full first lesson (the default pace would make it short)

    def test_every_answer_pause_precedes_its_answer(self):
        """Recall before answer: after each answer-pause the next spoken thing is the model answer."""
        segs = self.script.segments
        for i, s in enumerate(segs):
            if s.type == "pause" and s.role == "answer":
                nxt = next(x for x in segs[i + 1 :] if x.type != "pause")
                if nxt.type == "narrate" and nxt.text == Prompts.load("en").get("pick_out_answer"):
                    # #335: a pick-out announces its model answer («The answer:», a framing line with its beat); the answer is the next spoken thing after it
                    nxt = next(x for x in segs[segs.index(nxt) + 1 :] if x.type != "pause")
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
        so its intro must not be framed as "begin at the end" — it should fall back
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
        # #302: no stretched repeat; the word is said once more at natural speed
        self.assertNotIn(prompts.get("slowly"), narrations)
        self.assertEqual([g.rate for g in sc.segments if g.type == "speak"], [1.0] * len([g for g in sc.segments if g.type == "speak"]))
        self.assertGreaterEqual(len([g for g in sc.segments if g.type == "speak" and g.text == item.target]), 2)

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
            # intro + reactivations + closing; the closing may ask it inside another item's sentence (#280: «Je voudrais une bière.» for the
            # pattern holds the late new «une bière», and the one question counts for both), so every recall that says it counts (#439)
            said = [e for e in self.script.exercises if item_id in (e.item_ids or []) and e.kind in ("intro", "recall", "generative", "connect")]
            self.assertGreaterEqual(len(said), 3, item_id)
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
        self.assertIn("begin at the end", text)
        # Issue #49 had the chunks stretched; #302 says them at natural speed (a one-word chunk plain, a longer one word by word): "(slow)" marks a sub-1.0 rate
        self.assertIn("**Speaker A:** plaît", text)
        self.assertNotIn("(slow)", text.split("begin at the end")[1].split("natural")[0])
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

        def eligible(done: dict[str, int], played: dict[int, list[str]], last: int, limit: int = 2) -> set[str]:
            learner = LearnerState("is", "en", "A1")
            for i in range(3):
                learner.items[f"w{i}"] = ItemState(due=TODAY.isoformat(), successes=3, durable_successes=3, stage="meaning")
            learner.dialogues_done = dict(done)
            learner.lessons = [{"number": n, "dialogues": played.get(n, [])} for n in range(1, last + 1)]
            learner.lessons_completed = last
            out = set()
            for _ in range(2):
                planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, dialogue_full_play_limit=limit), today=TODAY)
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
        self.assertEqual(eligible({"short": 1}, {}, 4), {"short", "long"}, "no record of when: never held back")
        self.assertEqual(eligible({"short": 2}, {}, 4), {"long"}, "heard in full twice: retired (lesson 53)")
        # the owner, 2026-11-19: by default a script heard in full once does not return (``dialogue_full_play_limit`` 1); the rest above is
        # for a limit of two or more
        self.assertEqual(eligible(both, {1: ["short", "long"]}, 4, limit=1), {"long"}, "heard in full once: retired")

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
                if e.kind == "recall" and e.item_ids and e.item_ids[0] in stable - due:  # the closing's «Today's form work, once more.» asks no item (#535)
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
                # #326: a practice through a connection (a scene line, a sibling sentence) is a practice that does not name the item
                spots = sorted(spots + sc.meta["hard_connections"].get(i, {}).get("connection_times_s", []))
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

    def test_a_part_of_a_met_line_with_no_pattern_to_put_it_in_is_taken_out_of_the_line(self):
        """#262 (lesson 23 replay: «krónur» and «þúsund» alone although the learner knows «þúsund krónur»): with no known pattern to make a new sentence of the
        part, it is still taken out of the line the learner knows, and the next day asks that line, not the bare word."""
        from audiolesson.cli import _plan
        cur = self._cur(with_frame=False)
        sc = self._plan(cur, self._learner(frame=False))
        self.assertEqual(sc.meta["embedded_items"], [])
        self.assertEqual([e.label for e in sc.exercises if "opid" in e.item_ids and e.kind == "intro"], ["new: Er opið? (opið)"])
        self.assertNotIn("new: opið", sc.transcript())
        self.assertEqual([q["answer"] for q in _plan(sc, cur)["review"] if "opid" in q["items"]], ["Er opið?"])

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
        # lesson 29: an example answer follows (the learner's own line, as one possible answer); the partner's line is not put in English
        self.assertEqual([t for t in said if t[0] == "narrate"], [("narrate", "instructor", "Reply."), ("narrate", "instructor", "For example: I'm from Japan.")])
        self.assertNotIn("Where are you from?", sc.transcript())
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
        """Not the example answer that follows it (lesson 29): the review would give its own answer away."""
        sc, ex = self._recall(learner_items=["q"])
        ex.item_ids = ["a"]
        questions = sc.review_questions()
        self.assertEqual([(q["prompt"], q["answer"]) for q in questions], [("Hvaðan ert þú?", "Ég er frá Japan.")])
        self.assertIn("For example: I'm from Japan.", sc.transcript())

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
        # a frame taken in the lesson (#270's «Mig langar að sjá {…}.») brings the sights it needs as fillers (``take``: a pattern is only teachable with two things
        # to put in its slot), which the set limit does not count: the limit holds for what the lesson takes by itself
        frame_tags = {t for i in ids if self.cur.by_id[i].kind == "construction" for t in self.cur.by_id[i].slots.values()}
        pulled = [i for i in self._of_set(ids) if set(self.cur.by_id[i].tags) & frame_tags]
        self.assertLessEqual(len(self._of_set(ids)) - len(pulled), 1, "two already in the lesson: one more")
        if not pulled:
            self.assertEqual(len(self._of_set(ids)), 1)

    def test_the_items_a_theme_level_wants_are_a_scene_and_exempt(self):
        from audiolesson.themes import Level, Theme, Turn

        scene = ["sjor", "nordurljos", "midnætursol"]  # no slot tag: only the set limit applies to them
        level = Level(goal="g", partner_speaker="native_c", turns=[Turn(who="you", say="Takk.", cue="Thank him.", items=scene)])
        theme = Theme(scene_line="You are there.", id="nature_test", scenario="A1", title="Nature", levels=[level])
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
                              PlanConfig(minutes=30, new_items=8, seed=1, priority=[i.id for i in adjectives], semantic_sets=sets,
                                         max_slot_fillers=99), today=TODAY)  # the set's limit alone; a slot's is #579's (tests/test_slot_fillers.py)
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
                              PlanConfig(minutes=30, new_items=8, seed=1, priority=[i.id for i in colours], **{"max_slot_fillers": 99, **cfg}), today=TODAY)
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
        self.assertEqual(st.reported_hard, TODAY.isoformat(), "#326: «I don't remember it» is also a report that it is hard")
        before.reported_hard = st.reported_hard
        self.assertEqual(st.slow_owed, TODAY.isoformat(), "#337: and the slow model of its hard word is owed")
        before.slow_owed = st.slow_owed
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
        # since #327 a level plays in the lesson that teaches its lines, so the levels are played sooner and the ear's four heard plays are
        # all used from lesson 6 of this course
        self.assertGreaterEqual(checked, 5)

    def test_the_not_due_fillers_start_with_the_scene(self):
        cur, learner, day, extra = self._course_to(9)
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0, **extra), today=day)
        plain = [i.id for i in planner.select_early_reviews(set(), rested_only=False)]
        self.assertGreater(len(plain), 5)
        last = plain[-1]
        first = [i.id for i in planner.select_early_reviews(set(), rested_only=False, prefer=frozenset({last}))]
        self.assertEqual(first[0], last)
        self.assertEqual(sorted(first), sorted(plain))


if __name__ == "__main__":
    unittest.main()
