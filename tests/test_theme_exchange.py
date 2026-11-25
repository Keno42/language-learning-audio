"""The lesson's theme exchange, pattern supply, framing lines and timing beats (split from test_audiolesson.py)."""
from __future__ import annotations

from tests.audiolesson_common import *  # noqa: F401,F403
from tests import test_sayable_forms




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
        # these tests pin the one rule (#263: sayable → asked; #210: every turn keeps its cue); the exception for a known set reply voiced in an exchange
        # played again (#416) is off here and pinned in tests/test_set_replies.py
        cfg.setdefault("set_reply_words", 0)
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
        learner.themes_done = {"supermarket": 1, "clothes": 1, "cafe": 0, "museum": 1, "tour": 2}
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
        self.assertEqual(sc.meta["theme"], {"id": "supermarket", "scenario": "A3", "level": 1, "plays": 2, "lines": sc.meta["theme"]["lines"], "replay": False, "heard": sc.meta["theme"]["heard"],
                                            "goal_heard": 0, "goal": self._supermarket.levels[0].goal})  # #327: every line asked in the last play
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
        the second play and a replay included, the tour's «Greet her back.» too. A gendered line's cue names the form first («As a woman:
        …», owner after #381)."""
        from audiolesson.exercises import speak_as
        from audiolesson.themes import level_dialogue

        planner = self._planner(self._learner(self._known + self._rest + ["godan_daginn"]), self._themes, self._order)
        prompts = planner.builder.prompts
        for theme in self._themes:
            for n, level in enumerate(theme.levels):
                dlg = level_dialogue(theme, n)
                for translate in (True, False):
                    sc = Script(1, "t", "is", "en")
                    planner.builder.dialogue(sc, dlg, translate=translate)
                    narrated = [g.text for g in sc.segments if g.type == "narrate"]
                    for turn in dlg.turns:
                        cues = {turn.cue} | ({speak_as(prompts, g, turn.cue) for g in ("f", "m")} if turn.expect_text_m else set())
                        self.assertTrue(cues & set(narrated), (theme.id, n + 1, translate, turn.cue))
        self.assertIn("Greet her back.", [t.cue for t in level_dialogue(next(t for t in self._themes if t.id == "tour"), 0).turns])

    def test_a_scene_line_on_a_partner_turn_is_narrated_before_its_line_in_every_play(self):
        from audiolesson.themes import Level, Theme, Turn, level_dialogue

        dlg = level_dialogue(self._supermarket, 0)
        self.assertEqual(dlg.turns[1].partner_scene, "At the till.", "«Viltu poka?» is the partner reply of «Takk.»")
        self.assertEqual(dlg.turns[1].scene, "")
        ja = level_dialogue(self._supermarket, 0, known_lang="ja")
        self.assertTrue(ja.turns[1].partner_scene and ja.turns[1].partner_scene != "At the till.")
        theme = Theme(scene_line="You are there.", id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=[
            Turn(who="you", say="Hæ.", cue="Say hi.", items=["hae"]),
            Turn(who="partner", say="Halló.", meaning="Hello.", scene="Later."),
            Turn(who="you", say="Bless.", cue="Say bye.", items=["bless"]),
        ])])
        self.assertEqual(level_dialogue(theme, 0).turns[0].partner_scene, "Later.")
        opener = Theme(scene_line="You are there.", id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=[
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
            _check(Theme(scene_line="You are there.", id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=list(turns))]))

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
        bad = Theme(scene_line="You are there.", id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=[
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
            _check(Theme(scene_line="You are there.", id="x", scenario="A1", title="X", levels=[Level(goal="g", partner_speaker="native_c", turns=[Turn(who="you", say="Takk.", cue="Thank him.", items=["takk"])])]))

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
        learner.themes_last = {t.id: 9 for t in self._themes} | {"cafe": 3, "museum": 8, "tour": 7}
        planner = self._planner(learner, self._themes, self._order)
        now = learner.next_lesson_number()
        learner.themes_last = {t.id: now - 1 for t in self._themes} | {"cafe": now - 5, "museum": now - 4, "tour": now - 2}  # the others were just played
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
            texts = [g.text for g in segs if g.type == "narrate"]
            here = texts.count(Prompts.load("en").get("listening_line"))
            asked = sum(1 for g in segs if g.type == "pause" and g.role == "answer")
            self.assertTrue(any(g.type == "answer" for g in segs), "the learner's line is modelled")
            opening = Prompts.load("en").get("listening_intro_known" if here == 0 else "listening_intro" if asked == 0 else "listening_intro_some_asked")
            self.assertIn(opening, texts, "the opening follows from what is asked")
            self.assertEqual("new expressions" in " ".join(texts), here > 0, "«new expressions» only when a line is only heard")
            self.assertTrue(sum(1 for g in segs if g.type == "narrate") >= 3, "the cues stay")

    def _replays(self, met, seed: int = 1):
        """The scenes heard again in a lesson of a learner who has met ``met`` and played every theme level: for each, the expectation computed from the
        theme's own turns (a line is asked when all its items are met) and what the exercise did. ``seed``: the lesson's draw of which levels are heard."""
        learner = self._learner(met)
        learner.themes_done = {t.id: len(t.levels) for t in self._themes}
        learner.themes_last = {"supermarket": 1, "cafe": 1, "museum": 1, "tour": 1}
        planner = self._planner(learner, self._themes, self._order, seed=seed)
        sc = planner.build()
        out = []
        for e in sc.exercises:
            if not e.label.startswith("heard: theme:"):
                continue
            theme_id, level = e.label.split()[1].split(":")[1:3]
            theme = next(t for t in self._themes if t.id == theme_id)
            you = [t for t in theme.levels[int(level) - 1].turns if t.who == "you"]
            taught = {i for x in sc.exercises if x.index < e.index and x.kind in ("intro", "embed") for i in x.item_ids}  # taught earlier in this lesson counts as met
            asked = [t for t in you if all(i in met or i in taught for i in t.items)]
            segs = [g for g in sc.segments if g.exercise == e.index]
            texts = [g.text for g in segs if g.type == "narrate"]
            out.append((you, asked, e, segs, texts, planner))
        self.assertTrue(out, "the lesson has spare time for scenes heard again")
        return out

    def test_a_replay_of_scenes_the_learner_knows_asks_every_line_and_credits_them(self):
        prompts = Prompts.load("en")
        met = sorted({i for t in self._themes for lv in t.levels for tn in lv.turns if tn.who == "you" for i in tn.items})
        for you, asked, e, segs, texts, planner in self._replays(met):
            self.assertEqual(len(asked), len(you))
            self.assertEqual(sum(1 for g in segs if g.type == "pause" and g.role == "answer"), len(you), e.label)
            self.assertEqual(texts.count(prompts.get("listening_line")), 0)
            self.assertIn(prompts.get("listening_intro_known"), texts)
            self.assertEqual(e.item_ids, list(dict.fromkeys(i for t in you for i in t.items)), e.label)
            self.assertEqual(e.heard_ids, [])
            self.assertTrue(set(e.item_ids) <= set(planner.exposures), "credited as practice")

    def test_a_replay_of_scenes_the_learner_has_not_met_asks_nothing(self):
        prompts = Prompts.load("en")
        none_asked = 0
        for you, asked, e, segs, texts, planner in self._replays([]):
            if asked:
                continue  # «Takk.» was taught earlier in this lesson, so that scene is a mixed one
            none_asked += 1
            self.assertEqual(sum(1 for g in segs if g.type == "pause" and g.role == "answer"), 0)
            self.assertEqual(texts.count(prompts.get("listening_line")), len(you))
            self.assertIn(prompts.get("listening_intro"), texts)
            self.assertEqual(e.item_ids, [])
            self.assertEqual(e.heard_ids, list(dict.fromkeys(i for t in you for i in t.items)), e.label)
        self.assertGreater(none_asked, 0)

    def test_a_replay_that_mixes_known_and_unmet_lines_asks_exactly_the_known_ones(self):
        prompts = Prompts.load("en")
        met = ["takk", "ja"]
        mixed = 0
        # the levels heard again are drawn at random among those heard longest ago (#483); a few lessons' draws, so that one holds a mixed level
        # whatever the number of levels (#451 step 2e added two, and seed 1 alone no longer drew one)
        replays = [r for seed in (1, 2, 3, 4) for r in self._replays(met, seed)]
        for you, asked, e, segs, texts, planner in replays:
            if not asked or len(asked) == len(you):
                continue
            mixed += 1
            self.assertEqual(sum(1 for g in segs if g.type == "pause" and g.role == "answer"), len(asked), e.label)
            self.assertEqual(texts.count(prompts.get("listening_line")), len(you) - len(asked))
            self.assertIn(prompts.get("listening_intro_some_asked"), texts)
            self.assertEqual(e.item_ids, list(dict.fromkeys(i for t in asked for i in t.items)))
            self.assertEqual(set(e.heard_ids), {i for t in you if t not in asked for i in t.items} - set(e.item_ids))
        self.assertGreater(mixed, 0, "a mixed replay was generated")

    def test_the_same_line_gets_the_same_role_in_a_dialogue_and_a_theme(self):
        """«Ég ætla að fá kaffi.» is covered by chunks the learner can say although its construction is unmet: asked in both."""
        learner = self._learner(["eg_aetla_ad_fa_addon", "kaffi"]) if "eg_aetla_ad_fa_addon" in self._cur.by_id else None
        if learner is None:
            self.skipTest("the fixture curriculum has no eg_aetla_ad_fa_addon")
        planner = self._planner(learner, self._themes, self._order)
        cafe = next(t for t in self._themes if t.id == "cafe")
        line = next(t for t in cafe.levels[0].turns if t.who == "you" and t.say == "Ég ætla að fá kaffi.")
        self.assertNotIn("eg_aetla_ad_fa", learner.items)
        self.assertEqual(planner.line_role(line.items, text=line.say), "ask")
        from audiolesson.content import DialogueTurn
        turn = DialogueTurn(cue="", expect="eg_aetla_ad_fa", expect_fill={"thing": "kaffi"})
        self.assertEqual(planner.line_role([turn.expect, "kaffi"], turn), "ask")

    def test_a_phrase_made_of_known_chunks_gets_the_same_role_in_a_dialogue_and_a_theme(self):
        """#263 review: «Má ég borga með korti?» (the phrase ma_eg_borga_med_korti, unmet) when «má ég» and «borga með korti» are known. The policy
        is one for both callers. The phrase is an instance of «Má ég {inf}?» with «borga með korti» (#265, lesson 61): the pattern's sentence,
        asked in both; with its fill unmet it is heard in both, until it is taught."""
        learner = self._learner(["ma_eg_inf", "borga_med_korti"])
        planner = self._planner(learner, self._themes, self._order)
        self.assertNotIn("ma_eg_borga_med_korti", learner.items)
        theme_turn = next(t for th in self._themes for lv in th.levels for t in lv.turns if t.who == "you" and t.say == "Má ég borga með korti?")
        dialogue_turn = next(t for d in self._cur.dialogues for t in d.turns if t.expect == "ma_eg_borga_med_korti")
        self.assertEqual(planner.line_role(theme_turn.items, text=theme_turn.say), "ask")
        self.assertEqual(planner.line_role([dialogue_turn.expect], dialogue_turn), "ask")
        # …and without the fill, heard in both
        unfilled = self._planner(self._learner(["ma_eg_inf"]), self._themes, self._order)
        self.assertEqual(unfilled.line_role(theme_turn.items, text=theme_turn.say), "hear")
        self.assertEqual(unfilled.line_role([dialogue_turn.expect], dialogue_turn), "hear")

    def test_a_scene_heard_again_hears_only_the_lines_with_an_untaught_item(self):
        learner = LearnerState("is", "en", "A1")
        learner.themes_done = {"supermarket": 1, "cafe": 1, "museum": 1, "tour": 1}
        learner.themes_last = {"supermarket": 1, "cafe": 1, "museum": 1, "tour": 1}
        planner = self._planner(learner, self._themes, self._order)
        you = [t for t in self._supermarket.levels[0].turns if t.who == "you"]
        self.assertEqual({k for k, t in enumerate(you) if planner.line_role(t.items) == "hear"}, set(range(len(you))), "nothing met: every line is heard")
        for t in you:
            for i in t.items:
                if i in planner.cur.by_id:
                    learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3)
        self.assertEqual({k for k, t in enumerate(you) if planner.line_role(t.items) == "hear"}, set(), "all met: every line is asked")

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
        missing = [i for i in self._known if i not in ("skyr", "erud_thid_med")]
        learner = self._learner(missing + self._rest)
        def planner(themes, **cfg):
            return Planner(self._cur, learner, Prompts.load("en"), Timing(level="A1"),
                           PlanConfig(minutes=30, new_items=2, themes=themes, theme_scenarios=["A3"], seed=1, **cfg), today=TODAY)

        trip_first = planner([]).select_new(2)[0].id  # what the course order would teach first
        self.assertNotIn(trip_first, ("skyr", "erud_thid_med"))
        p = planner([self._supermarket], priority=[trip_first])
        self.assertEqual(p.theme_target()[:2], (self._supermarket, 0))
        wants = p.theme_wants()
        self.assertEqual({"skyr", "erud_thid_med"} - set(wants), set(), "the items the level lacks")
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
            _check(Theme(scene_line="You are there.", id="x", scenario="A1", title="X", levels=[]))
        with self.assertRaises(CurriculumError):
            _check(Theme(scene_line="You are there.", id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[Turn(who="partner", say="Hæ.", meaning="Hi.")])]))
        with self.assertRaises(CurriculumError):
            _check(Theme(scene_line="You are there.", id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[Turn(who="you", say="Takk.", items=["takk"])])]))
        with self.assertRaises(CurriculumError):
            _check(Theme(scene_line="You are there.", id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[good, Turn(who="partner", say="Hæ.")])]))
        with self.assertRaises(CurriculumError):
            _check(Theme(scene_line="You are there.", id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[Turn(who="him", say="Hæ.")])]))
        _check(Theme(scene_line="You are there.", id="x", scenario="A1", title="X", levels=[Level(goal="g", turns=[good])]))



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
            if i in ("klukkan_er", "thrju", "eitt", "tvo", "ma_eg_borga_med_korti", "kort"):
                learner.items[i] = ItemState(due=TODAY.isoformat(), successes=2, durable_successes=2, stage="meaning", recalled=2, last_outcome="recalled")
        planner = Planner(cur, learner, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30), today=TODAY)
        b = planner.builder
        b._situation_texts.update({t: 99 for t in ([cur.by_id["klukkan_er"].situation] if cur.by_id["klukkan_er"].situation else []) + list(cur.by_id["klukkan_er"].situations)})
        sc = Script(1, "t", "is", "en")
        b.connect(sc, [cur.by_id["klukkan_er"], cur.by_id["ma_eg_borga_med_korti"]])
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
        for row in ("| minutes |", "| short new item alone, most |", "| bare_cap_lapsed |", "| tried lines / bonus questions |", "| lines a listening scene asks for that were never taught (#240) |", "| theme (level) / plays |",
                    "| target delivered / second half by the guard (#294) |", "| speech touching at a change of voice (#301) |", "| switch gaps inserted (#301) |",
                    "| confirmed recall rate by gap, 3–6 / 7–13 / 14+ days (#220) |", "| pattern sentences said with no scene verdict (G6) |"):
            self.assertIn(row, text)
        rows = {line.split("|")[1].strip(): [c.strip() for c in line.split("|")[2:-1]] for line in text.splitlines() if line.startswith("| ") and line.count("|") >= 4}
        self.assertEqual(rows["target delivered / second half by the guard (#294)"], ["yes", "yes"])
        self.assertEqual(rows["speech touching at a change of voice (#301)"], ["0", "0"])
        self.assertTrue(all(int(c) > 0 for c in rows["switch gaps inserted (#301)"]), "a positive count of gaps")



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



class AsideBreathTests(unittest.TestCase):
    """#259 (the owner on lesson 20's aside): a note's prose was one narration, however many sentences it held; each sentence is its own narration with a beat
    after it, a «…» span inside a sentence stays inline, and the last sentence is followed by the one closing beat."""

    def _builder(self):
        from audiolesson.exercises import Builder
        return Builder(load_curriculum(ROOT / "curricula" / "is-en"), Prompts.load("en"), Timing(level="A1"), LearnerState("is", "en", "A1"))

    @staticmethod
    def _shape(sc):
        return [("beat" if s.type == "pause" else s.speaker if s.type == "speak" else "narr") + (f":{s.text}" if s.type != "pause" else "") for s in sc.segments]

    def test_each_sentence_is_a_narration_with_a_beat_after_it(self):
        b = self._builder()
        sc = Script(1, "t", "is", "en")
        ex = sc.new_exercise("note", None, [], "n")
        b._speak_note_text(sc, ex, "A quick fact. It is old: really old! Is it? Yes, e.g. in vedur.is. Done.")
        narrated = [g.text for g in sc.segments if g.type == "narrate"]
        self.assertEqual(narrated, ["A quick fact.", "It is old: really old!", "Is it?", "Yes, e.g. in vedur.is.", "Done."])
        kinds = [g.type for g in sc.segments]
        self.assertEqual(kinds, ["narrate", "pause", "narrate", "pause", "narrate", "pause", "narrate", "pause", "narrate"], "a beat between sentences, none after the last")

    def test_a_span_inside_a_sentence_stays_inline_and_a_span_after_a_stop_follows_a_beat(self):
        b = self._builder()
        sc = Script(1, "t", "is", "en")
        ex = sc.new_exercise("note", None, [], "n")
        b._speak_note_text(sc, ex, "The «kennitala» is a ten-digit number. It is like My Number. «Takk» means thanks, e.g. here.")
        shape = [("beat" if g.type == "pause" else g.type + ":" + g.text) for g in sc.segments]
        self.assertEqual(shape, ["narrate:The", "speak:kennitala", "narrate:is a ten-digit number.", "beat", "narrate:It is like My Number.", "beat",
                                 "speak:Takk", "narrate:means thanks, e.g. here."], "'The / kennitala / is a ten-digit number.' is one sentence")

    def test_the_closing_beat_of_a_note_is_a_single_beat(self):
        b = self._builder()
        note = next(n for n in b.cur.notes if n.id == "kennitala") if any(n.id == "kennitala" for n in b.cur.notes) else b.cur.notes[0]
        sc = Script(1, "t", "is", "en")
        b.note(sc, note)
        segs = sc.segments
        end = next(k for k in range(len(segs) - 1, -1, -1) if segs[k].type == "narrate")  # aside_end
        self.assertEqual(segs[end - 1].type, "pause", "one beat before «Back to the lesson.»")
        self.assertNotEqual(segs[end - 2].type, "pause", "and not two")

    def test_japanese_prose_breaks_at_the_full_stop(self):
        b = self._builder()
        sc = Script(1, "t", "is", "ja")
        ex = sc.new_exercise("note", None, [], "n")
        b._speak_note_text(sc, ex, "これは日本語です。次の文です！最後です？")
        self.assertEqual([g.text for g in sc.segments if g.type == "narrate"], ["これは日本語です。", "次の文です！", "最後です？"])

    def test_no_note_of_the_course_has_two_sentences_in_one_narration(self):
        import re
        b = self._builder()
        for lang in ("en", "ja"):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            from audiolesson.exercises import Builder
            bl = Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
            for note in cur.notes:
                sc = Script(1, "t", "is", lang)
                bl.note(sc, note)
                for g in sc.segments:
                    if g.type == "narrate":
                        self.assertIsNone(re.search(r"[.?!] [A-ZÁÐÉÍÓÚÝÞÆÖ]|[。！？].", g.text), f"{lang} {note.id}: {g.text!r}")



class FramingBeatTests(unittest.TestCase):
    """#241 (lesson 20: «sometimes no pause between the instructor's line and the example»): a framing line that introduces
    an example or a scene is followed by a beat; a cue for the learner's own action joins its line at once."""

    FRAMING = ("construction_slot", "also", "embed_known", "embed_part", "variant_known", "form_model_known",
               "listening_line", "dialogue_replay", "milestone_intro", "aside", "instance_sentence", "embed_sentence")

    @classmethod
    def setUpClass(cls):
        cls.lessons = [sc for _, sc in test_sayable_forms.ShortItemRepetitionTests._course(12)]

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

    def test_a_cue_for_the_learners_action_is_followed_by_its_line_after_a_switch_gap(self):
        """#241 had the cue join its line at once; #301 puts the switch pause between them (a change of voice always has a gap)."""
        repeat = Prompts.load("en").get("repeat")
        joins = [(a, b, c) for sc in self.lessons for a, b, c in zip(sc.segments, sc.segments[1:], sc.segments[2:]) if a.type == "narrate" and a.text == repeat]
        self.assertTrue(joins)
        self.assertTrue(all((b.type, b.role) == ("pause", "switch") and c.type == "speak" for _, b, c in joins), "«Repeat.», a switch gap, then the line")



class FramingClaimTests(unittest.TestCase):
    """A framing line that promises something («other words», «another sentence», «again», «something new») keeps the promise. The remark came
    back one prompt key at a time (#197, #287, #335, #386, #388); ``audiolesson/claims.py`` lists every promising key with what must hold for it."""

    PROMISE = re.compile(r"\b(another|other|again|new|haven't|later|same)\b", re.I)

    @classmethod
    def setUpClass(cls):
        cls.lessons = [sc for _, sc in test_sayable_forms.ShortItemRepetitionTests._course(12)]

    def test_no_framing_line_of_a_simulated_course_promises_what_does_not_follow(self):
        from audiolesson.claims import claim_of
        prompts = Prompts.load("en")
        claimed = 0
        for sc in self.lessons:
            self.assertEqual(sc.meta["unkept_claims"], [], f"lesson {sc.lesson_number}")
            claimed += sum(1 for g in sc.segments if g.type == "narrate" and g.text and claim_of(g.text, prompts))
        self.assertGreater(claimed, 50, "the course has promising lines to check")

    def test_every_promising_line_of_the_phrasing_is_checked_or_reviewed(self):
        from audiolesson.claims import CLAIMS, NO_CLAIM
        en = Prompts.load("en").data
        promising = {k for k, v in en.items() if isinstance(v, (str, list)) and any(self.PROMISE.search(t) for t in ([v] if isinstance(v, str) else v))}
        self.assertEqual(sorted(promising - set(CLAIMS) - set(NO_CLAIM)), [], "a line that promises: what must hold in CLAIMS, or why nothing can in NO_CLAIM")
        self.assertEqual(sorted((set(CLAIMS) | set(NO_CLAIM)) - set(en)), [], "every key of the table is a line of en.toml")
        self.assertEqual(set(CLAIMS) & set(NO_CLAIM), set())

    def test_a_promise_that_does_not_follow_is_found(self):
        """Main before the new-pattern fix: «You can put other words in the same place.», then the worked example asked again. The gender label in
        front of a line does not hide its promise (lesson 34: «In another sentence» was the phrase just said, #386)."""
        from audiolesson.claims import unkept_claims
        from audiolesson.exercises import speak_as
        en = Prompts.load("en")
        sc = Script(1, "t", "is", "en")

        def exercise(label, *lines, kind="intro"):
            ex = sc.new_exercise(kind, "intro", [label], label)
            for t in lines:  # «>» marks an Icelandic line
                tl = t.startswith(">")
                sc.add(Segment("speak" if tl else "narrate", "native_a" if tl else "instructor", t.lstrip(">"), "is" if tl else "en", 1.0, 1.0, None, ex.index))

        slot, another = en.get("construction_slot"), speak_as(en, "f", en.get("embed_sentence"))
        exercise("hnetum", "Here is a useful pattern. I'm allergic to nuts.", ">Ég er með ofnæmi fyrir hnetum.", slot, ">Ég er með ofnæmi fyrir hnetum.")
        exercise("fiski", "Here is a useful pattern. I'm allergic to fish.", ">Ég er með ofnæmi fyrir fiski.", slot, ">Ég er með ofnæmi fyrir hnetum.")
        exercise("hotel", en.get("embed_known"), ">Á þetta hótel, takk.", another, ">Á þetta hótel, takk.", kind="embed")
        exercise("hotel", "Something new. To this hotel.", ">Á þetta hótel.")
        self.assertEqual(unkept_claims(sc, en), [f"hnetum: {slot}", f"hotel: {another}", "hotel: Something new. To this hotel."])



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


if __name__ == "__main__":
    unittest.main()
