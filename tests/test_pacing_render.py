"""New components and pacing, prompts, timing, rendering, the review, the CLI, can-do and trip profiles (split from test_audiolesson.py)."""
from __future__ import annotations

from tests.audiolesson_common import *  # noqa: F401,F403
from tests import test_lesson_structure




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
        # a phrase that holds a new part is introduced before it (#262 `phrase_first`): it is one of today's introductions too
        first |= {e.item_ids[0] for e in sc.exercises if e.kind in ("intro", "embed") and e.item_ids and self._is_phrase(cur, e.item_ids[0])}
        idx = [e.index for e in sc.exercises if e.kind in ("intro", "embed") and e.item_ids and e.item_ids[0] in first]
        return first, idx

    @staticmethod
    def _is_phrase(cur, item_id):
        return cur.by_id[item_id].kind == "phrase"

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
            self.assertLessEqual(len(between), 5, [(e.kind, e.label) for e in between])  # #262: a phrase and its part are two introductions, each with its own recalls
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

    def test_the_rate_keeps_the_next_day_outcome(self):
        """#579 (lessons 62–64): a later review that names the lesson as its source updates the item, not the lesson's entry, so the pace reads
        the next-day outcome. Lesson 62's «höfuðverk», not recalled the next day and hesitated at its next ask, still counts as failed; a
        report the same day (a correction) replaces the outcome."""
        learner = self._rated([["r"] * 4])
        learner.report(["i1_0"], [], TODAY, 1, hesitated=["i1_1"])
        self.assertEqual(learner.recall_rate(), (1.5, 4))
        later = TODAY + timedelta(days=2)
        learner.report([], [], later, 1, hesitated=["i1_0"], recalled=["i1_1"])
        self.assertEqual(learner.recall_rate(), (1.5, 4), "the next-day outcomes stand")
        self.assertEqual((learner.items["i1_0"].last_outcome, learner.items["i1_1"].last_outcome), ("hesitated", "recalled"), "the item moves on")
        self.assertEqual([e["outcome"] for e in learner.items["i1_0"].history], ["not_recalled"])
        # review of #582: an embedded or tried item's entry, made by its first review, keeps that review's outcome too
        for pending in ("embedded", "tried"):
            first = self._rated([["r"] * 3])
            first.lessons[0]["new_items"].append("x")
            getattr(first, pending)["x"] = 1
            first.report([], [], TODAY, 1, recalled=["x"])
            first.report(["x"], [], later, 1)
            self.assertEqual([(e["lesson"], e["outcome"]) for e in first.items["x"].history], [(1, "recalled")], pending)
            self.assertEqual(first.items["x"].last_outcome, "not_recalled", f"{pending}: the item moves on")
            self.assertEqual(first.recall_rate(), (0, 4), pending)
        again = self._rated([["r"] * 4])
        again.report(["i1_0"], [], TODAY, 1)
        again.report([], [], TODAY, 1, recalled=["i1_0"])  # corrected the same day
        self.assertEqual(again.recall_rate(), (0, 4))

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
        learner = test_lesson_structure.SoonerRequestTests._learner()
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
            test_lesson_structure.SoonerRequestTests._learner().save(path)
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
            test_lesson_structure.SoonerRequestTests._learner().save(path)
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

        import dataclasses

        # the trust check (#631) is off: this pins the trip ordering's reach, not which lines the table lets through («Hvenær er útritun?», B7, has a pair no text has)
        cur = dataclasses.replace(load_curriculum(ROOT / "curricula" / "is-en"), trust=None)
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

    def test_a_word_katakana_cannot_write_has_its_hint_in_ipa(self):
        """#586 (lesson 65: «vatn» introduced as «ヴァフトン», two vowels the word does not have): a card with pre-aspiration, the «tl» of
        ll, the «tn» of rn and nn, or a voiceless l, m, n or r gives IPA in its hint; validate fails on a kana-only hint of such a word."""
        import tempfile

        from audiolesson.content import CurriculumError
        from audiolesson.reading import kana_cannot_write, load_deck

        self.assertEqual(kana_cannot_write("vatn"), ["pre-aspiration"])
        for word in ("Hætta", "Epli", "Nafn", "fjall", "Björn", "Steinn", "Mjólk", "allt", "hraun"):
            self.assertTrue(kana_cannot_write(word), word)
        for word in ("Snæfellsnes", "Inngangur", "Bannað", "daginn", "Kaffi", "Gjörðu"):
            self.assertEqual(kana_cannot_write(word), [], word)
        cards = {c.id: c for c in load_deck(ROOT / "curricula" / "is-en")}
        self.assertTrue(cards["w_vatn"].hint_ja.startswith("[vaʰtn̥]"), "the owner's wording, after the IPA")
        self.assertNotIn("フト", cards["w_vatn"].hint_ja)
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "reading").mkdir()
            (Path(td) / "reading" / "deck.toml").write_text(
                '[[cards]]\nid = "w_vatn"\nstage = "shop"\ntext = "Vatn"\nmeaning = "Water"\nhint_ja = "ヴァフトン"\n', encoding="utf-8")
            with self.assertRaisesRegex(CurriculumError, "katakana cannot write \\(pre-aspiration\\)"):
                load_deck(td)

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
        self.assertEqual(sc.meta["config"]["levers"], {"late_unhinted_recall": True, "dialogue_full_play_limit": 1})

    def test_levers_pass_through_the_cli(self):
        import contextlib
        import io
        from audiolesson.cli import main

        with tempfile.TemporaryDirectory() as td:
            with contextlib.redirect_stdout(io.StringIO()):
                main(["generate", "-c", str(ROOT / "curricula" / "is-en"), "-l", str(Path(td) / "l.json"), "-o", td,
                      "-m", "10", "--no-audio", "--date", "2026-09-18", "--late-unhinted-recall"])
            levers = json.loads((Path(td) / "lesson-001.plan.json").read_text("utf-8"))["config"]["levers"]
        self.assertEqual(levers, {"late_unhinted_recall": True, "dialogue_full_play_limit": 1})



class SpokenMeaningTests(unittest.TestCase):
    """Recall disambiguators written in brackets («English (the language)», «本（〜は・〜が）»)
    were read aloud verbatim. ``meaning_spoken`` folds them into natural speech; the
    written ``meaning`` stays for glosses."""

    def test_the_spoken_form_is_per_language_and_never_borrowed(self):
        en = load_curriculum(ROOT / "curricula" / "is-en")
        ja = load_curriculum(ROOT / "curricula" / "is-en", known_lang="ja")
        # #544 (lesson 57): a form every frame shares is glossed by its case, not by the first frames' preposition
        self.assertEqual(en.by_id["hotelinu"].spoken_meaning, "the hotel, in the dative")
        self.assertEqual(en.by_id["hotelinu"].meaning, "the hotel (dative)")
        self.assertEqual(ja.by_id["hotelinu"].spoken_meaning, "ホテル、与格")
        self.assertEqual(en.by_id["eggjum"].spoken_meaning, "eggs, as in: I'm allergic to eggs")
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
        self.assertIn("ホテル、与格", spoken)
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
