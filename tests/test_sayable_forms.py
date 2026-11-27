"""Which lines can be said, short items' repetition, forms and constructions (split from test_audiolesson.py)."""
from __future__ import annotations

from tests import course_cache
from tests.audiolesson_common import *  # noqa: F401,F403




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
        self.assertNotIn("Here you say", sc.transcript())
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
        self.assertIn("Here you say:", text)
        self.assertNotIn("Tell him it costs five thousand krónur.", text, "«Tell him…» contradicts «Here you say:»")
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
        self.assertIn("Here you say:", text)
        self.assertIn("It costs five thousand krónur.", text, "a heard line comes with its meaning")
        self.assertIn("Say known zero.", text, "the taught line keeps its cue")
        self.assertEqual(len([s for s in sc.segments if s.type == "pause" and s.role == "answer"]), 1, "only the taught line is asked")
        self.assertEqual(planner.listening_tried, [])
        self.assertEqual(planner.listening_untaught, [])
        self.assertNotIn("big", planner.exposures, "the untaught construction is not recorded")

    def test_a_line_with_a_word_from_a_known_line_is_heard_on_the_real_curriculum(self):
        """#183 re-check (owner): the learner's words live inside longer known lines («þarf» in «Ég þarf hjálp.»), so a
        part is judged at word level, and «Mig vantar símkort.» is partly sayable for one who has «Takk fyrir mig.». Since
        #240 a listening scene hears it all the same; a line they can say whole is asked."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        dlg = next(d for d in cur.dialogues if d.id == "simabud")
        known = Planner(cur, self._learner(["takk_fyrir_mig"]), Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=TODAY)
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
        self.assertIn("Here you say:", sc.transcript())

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
        """The first ``lessons`` lessons of the 30-minute course with five new items a lesson, as ``(curriculum, script)``; built once per process
        (``tests/course_cache.py``)."""
        return course_cache.take("short-items-30", ShortItemRepetitionTests._fresh_course, lessons)

    @staticmethod
    def _fresh_course(lessons: int = 18):
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

    def test_a_new_part_taught_in_its_sentence_keeps_its_practice_rungs(self):
        """Lesson 44: a part that only its own sentence can hold lost every rung after its first to the bare cap («hinum megin við götuna», whose one
        frame is «Það er {direction}.», asked 3 times in 29 minutes): it is asked through its sentence again from the sentence's meaning (#270), at
        each of its four rungs, spread over the lesson."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner, day = LearnerState("is", "en", "A1"), TODAY
        parts = {"a_horninu", "hinum_megin_vid_gotuna", "vid_hlidina_a_bankanum"}
        seen = set()
        for _ in range(40):
            sc = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, seed=1, new_target=8.0), today=day).build()
            apply_to_learner(sc, learner, day)
            for i in parts & set(sc.meta["new_items"]):
                intro = next(e for e in sc.exercises if e.kind == "intro" and e.item_ids == [i])
                starts = [intro.start] + [e.start for e in sc.exercises if e.index > intro.index and i in e.item_ids]
                if intro.start > sc.total_duration / 2:
                    # introduced after the lesson's middle (review of #546: the simulated course moved «hinum megin við götuna» to 21:58 of lesson 32):
                    # its last rung, half a lesson after the introduction, falls past the lesson's end, for any item (main's «fyrir framan hótelið» at
                    # 21:48 of its lesson 33 too); the rungs before it are still asked, the closing's recall the last
                    self.assertGreaterEqual(len(starts), 4, f"lesson {sc.lesson_number}: {i} asked {len(starts) - 1} times after its introduction")
                    seen.add(i)
                    continue
                self.assertGreaterEqual(len(starts), 5, f"lesson {sc.lesson_number}: {i} asked {len(starts) - 1} times after its introduction")
                self.assertGreater(starts[4] - starts[0], 300, f"{i}: its rungs are spread over the lesson, not drilled")
                seen.add(i)
            if seen == parts:
                break
            day += timedelta(days=1)
        self.assertEqual(seen, parts)

    def test_a_part_or_short_utterance_is_said_alone_at_most_three_times(self):
        """A part (a ``vocab`` item, whatever its length) is said alone at most three times: any bare practice counts, a
        mixed-review turn included (#187). A short utterance (a ``phrase``) is a complete thing to say, so a scene is its proper
        use (the owner's decision on #190): only its meaning-cued bare practices count. A part's recall that asks its own sentence (#270: «Þetta er
        frábært.» for «frábært») says the sentence, not the part alone, and is not counted (lesson 44: counting it held «hinum megin við götuna» to
        three asks in all)."""
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
                answers = {e.index: {_norm_utterance(g.text) for g in sc.segments if g.exercise == e.index and g.type == "answer"} for e in ex}
                own = {_norm_utterance(t) for t in (it.target, it.target_m) if t}
                said_alone = lambda e: e.kind == "intro" or not part or bool(answers[e.index] & own)  # noqa: E731
                alone = sum(1 for e in ex if e.item_ids[0] == i and e.kind in ("intro", "recall") and e.stage in (bare if part else cued) and said_alone(e))
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
        self.assertNotIn("meaning: bankinn", [e.label for e in sc.exercises], "never alone while its sentence can be said (#277: the part may be credited by its sentence)")
        self.assertGreaterEqual([e.label for e in sc.exercises].count("meaning: Hvar er bankinn?"), 2, "its review is the sentence (besides the sentence's own)")

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
            # the previous exercise, whatever its kind: a mixed review or an aside between two asks of the sentence is not a repeat (lesson 67's
            # asides moved the draws: seed 1 asks it, a mixed review «ja+nei», then asks it again)
            played = [e.item_ids[0] if e.kind == "recall" else e.kind for e in sc.exercises]
            self.assertFalse([a for a, b in zip(played, played[1:]) if a == b and a in asked], (seed, played))
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
        self.assertNotIn("meaning: fara á safnið", [e.label for e in sc.exercises], "a three-word part is not asked alone while its sentence can be said")
        self.assertGreaterEqual([e.label for e in sc.exercises].count("meaning: Ég vil fara á safnið."), 2)

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
        # not shorter by more than 3%: which parts wait for their frame (#206) moves the sum by about 1% either way, and a pattern met earlier makes more
        # conversation replies known ones, answered a second sooner (#272)
        self.assertGreaterEqual(with_len, without_len * 0.97, (with_len, without_len))



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


if __name__ == "__main__":
    unittest.main()
