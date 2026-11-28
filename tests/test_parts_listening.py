"""Parts inside their wholes, the second half's listening tasks, patterns and their instances (split from test_audiolesson.py)."""
from __future__ import annotations

from tests import course_cache
from tests.audiolesson_common import *  # noqa: F401,F403




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

    def test_a_part_comes_with_a_frame_it_fits_even_when_no_example_names_it(self):
        """#262 (lesson 22): «köku» and «klósettið» were taught bare although «Ég ætla að fá {thing}.» and «Hvar er {place}?» take them; any construction whose slot takes
        the part and whose frame the learner nearly has is the part's home."""
        met = [i.id for i in self.cur.items if i.order < 192 and i.id not in ("koku", "klosettid")]
        for part, frame, slot in (("koku", "eg_aetla_ad_fa", "thing"), ("klosettid", "hvar_er", "place")):
            b = self._builder(met=met)
            home = b.whole_home(self.cur.by_id[part])
            self.assertEqual((home[0].id, {k: v.id for k, v in home[1].items()}[slot]), (frame, part))
            sc = Script(1, "t", "is", "en")
            ex = b.intro(sc, self.cur.by_id[part])
            self.assertTrue(ex.label.startswith("new: ") and ex.label.endswith(f"({self.cur.by_id[part].target})"), ex.label)
            self.assertEqual(b.wholes_taught[part]["through"], frame)

    def test_the_review_asks_the_sentence_exactly_as_it_was_taught(self):
        """#262 review: «Þetta er blá bók.» was taught for «blá», and a sentence rebuilt from other met words («Þetta er blár bíll.») was asked next day."""
        from audiolesson.review_wholes import whole_for
        b = self._builder(met=["thetta_er_noun", "bok"])
        sc = Script(1, "t", "is", "en")
        for part in ("blar", "raudur"):
            ex = b.intro(sc, self.cur.by_id[part])
            taught = b.wholes_taught.get(part)
            if not taught:
                continue
            self.assertEqual(ex.label, f"new: {taught['answer']} ({self.cur.by_id[part].target})")
            met = {"thetta_er_noun", "bok", "bill", part}
            self.assertEqual(whole_for(self.cur, self.cur.by_id[part], met - {taught["through"]}, self.en, taught)["answer"], taught["answer"])

    def test_a_part_of_three_words_is_built_up_from_its_end_inside_its_sentence(self):
        """Lesson 44: «hinum megin við götuna» was said once inside «Það er hinum megin við götuna.» and the sentence word by word, never built up as a plain
        introduction builds a long line. «These words are in the sentence:», then the part from its end, then at natural speed, in place of the sentence's slow line."""
        part = self.cur.by_id["hinum_megin_vid_gotuna"]
        b = self._builder(met=[i.id for i in self.cur.items if i.order < part.order and i.kind != "construction" or i.id == "thad_er_direction"])
        sc = Script(1, "t", "is", "en")
        ex = b.intro(sc, part)
        self.assertEqual(ex.label, "new: Það er hinum megin við götuna. (hinum megin við götuna)")
        narr = [g.text for g in sc.segments if g.type == "narrate"]
        self.assertIn(self.en.get("embed_part_words"), narr)
        self.assertNotIn(self.en.get("embed_part"), narr)
        self.assertIn(self.en.get("build_up"), narr)
        tx = sc.transcript()
        steps = [tx.index(line) for line in ("götuna", "við · götuna", "megin · við · götuna", "hinum · megin · við · götuna")]
        self.assertEqual(steps, sorted(steps), "built up from the end, one word more each time")
        self.assertNotIn("Það · er", tx, "the built-up part replaces the sentence's word-by-word line")
        self.assertNotIn(self.en.get("slowly"), narr)
        speech = [g.text for g in sc.segments if g.type in ("speak", "answer")]
        self.assertEqual(speech[-1], "Það er hinum megin við götuna.", "the first retrieval still asks the whole")

    def test_a_part_of_two_words_is_named_as_words_but_not_built_up(self):
        """Lesson 44: «á horninu» is two words, «These words are in the sentence:», and too short to build up."""
        part = self.cur.by_id["a_horninu"]
        b = self._builder(met=[i.id for i in self.cur.items if i.order < part.order and i.kind != "construction" or i.id == "thad_er_direction"])
        sc = Script(1, "t", "is", "en")
        b.intro(sc, part)
        narr = [g.text for g in sc.segments if g.type == "narrate"]
        self.assertIn(self.en.get("embed_part_words"), narr)
        self.assertNotIn(self.en.get("build_up"), narr)

    def test_a_part_after_the_phrase_it_is_in_is_taken_out_of_it(self):
        """#262: «matinn» right after «Takk fyrir matinn.» in the same lesson is not a new bare word: «You know this: …», «This word is in the sentence: …»."""
        b = self._builder(met=["takk"])
        sc = Script(1, "t", "is", "en")
        b.intro(sc, self.cur.by_id["takk_fyrir_matinn"])
        b.in_lesson.add("takk_fyrir_matinn")
        self.assertEqual(b.phrase_home(self.cur.by_id["matinn"]).id, "takk_fyrir_matinn")
        ex = b.intro(sc, self.cur.by_id["matinn"])
        self.assertEqual((ex.kind, ex.item_ids, ex.label), ("intro", ["matinn"], "new: Takk fyrir matinn. (matinn)"))
        self.assertEqual([(q["items"], q["answer"]) for q in sc.review_questions() if q["items"] == ["matinn"]], [(["matinn"], "Takk fyrir matinn.")])

    @staticmethod
    def _met_learner(ids):
        learner = LearnerState("is", "en", "A1")
        for i in ids:
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3)
        return learner

    def test_a_phrase_whose_prerequisite_is_the_next_new_part_still_comes_first(self):
        """#262: «krónur» and «hundrað» are both new; «Hundrað krónur, takk.» needs «hundrað», which is the next item of the same lesson: it is the whole «krónur»
        is taken out of, and «hundrað» then comes out of it."""
        met = [i.id for i in self.cur.items if i.order < self.cur.by_id["hundrad"].order and i.id not in ("hundrad", "kronur", "hundrad_kronur_takk")]
        planner = Planner(self.cur, self._met_learner(met), self.en, Timing(level="A1"), PlanConfig(minutes=5), today=TODAY)
        self.assertIsNone(planner.phrase_first(self.cur.by_id["kronur"]), "«hundrað» is neither known nor in the lesson")
        phrase = planner.phrase_first(self.cur.by_id["kronur"], {"hundrad"})
        self.assertEqual(phrase.id if phrase else None, "hundrad_kronur_takk")

    def test_a_part_is_taken_out_of_the_worked_example_of_the_pattern_given_with_it(self):
        """#262 review: «Get ég fengið matseðilinn?» is the pattern's worked example, so «matseðilinn» introduced next is taken out of that sentence, not given alone."""
        met = [i.id for i in self.cur.items if i.order < self.cur.by_id["matsedilinn"].order and i.id != "matsedilinn"]
        b = self._builder(met=met)
        pattern, part = self.cur.by_id["get_eg_fengid"], self.cur.by_id["matsedilinn"]
        self.assertIsNone(b.phrase_home(part))
        sc = Script(1, "t", "is", "en")
        ex = b.intro(sc, pattern, {"thing": part})
        b.in_lesson.add(pattern.id)
        speech = [g.text for g in sc.segments if g.type in ("speak", "answer")]
        self.assertIn("Get ég fengið matseðilinn?", speech, "the worked example is made of the part")
        self.assertNotIn("matsedilinn", ex.item_ids, "the part is not credited by the pattern's introduction")
        self.assertEqual(b.modeled_wholes["matsedilinn"]["answer"], "Get ég fengið matseðilinn?")
        ex2 = b.intro(sc, part)
        self.assertEqual((ex2.kind, ex2.item_ids, ex2.label), ("intro", ["matsedilinn"], "new: Get ég fengið matseðilinn? (matseðilinn)"))
        self.assertEqual(b.wholes_taught["matsedilinn"]["through"], "get_eg_fengid")
        q = [(x["items"], x["answer"]) for x in sc.review_questions() if x["items"] == ["matsedilinn"]]
        self.assertEqual(q, [(["matsedilinn"], "Get ég fengið matseðilinn?")])
        # without the pattern's example the part is introduced as before
        self.assertNotIn("matsedilinn", self._builder(met=met).modeled_wholes)

    def test_the_planner_brings_the_queued_pattern_forward_of_its_part(self):
        met = [i.id for i in self.cur.items if i.order < self.cur.by_id["matsedilinn"].order and i.id not in ("matsedilinn", "get_eg_fengid") and "fengið" not in i.target.lower()]
        planner = Planner(self.cur, self._met_learner(met), self.en, Timing(level="A1"), PlanConfig(minutes=5), today=TODAY)
        given = planner.frame_first(self.cur.by_id["matsedilinn"], [self.cur.by_id["get_eg_fengid"]])
        self.assertEqual(given and (given[0].id, given[1]), ("get_eg_fengid", "thing"))
        self.assertIsNone(planner.frame_first(self.cur.by_id["matsedilinn"], []), "no pattern queued: introduced as before")

    def test_a_part_taken_out_of_a_met_line_that_is_not_a_phrase_is_asked_as_taught(self):
        """#262: «þúsund krónur» is a known vocab line, neither a pattern nor a phrase; the review's search finds no whole for «krónur», so it asks the line taught."""
        from audiolesson.review_wholes import whole_for
        taught = {"through": "thusund_kronur", "answer": "þúsund krónur", "meaning": "a thousand krónur"}
        part = self.cur.by_id["kronur"]
        self.assertIsNone(whole_for(self.cur, part, {"thusund_kronur", "kronur"}, self.en))
        self.assertEqual(whole_for(self.cur, part, {"thusund_kronur", "kronur"}, self.en, taught)["answer"], "þúsund krónur")

    def test_the_sentence_a_part_was_taught_in_is_kept_across_lessons(self):
        """#262: «peysu» was taught in «Áttu peysu?» while its pattern is not met; a later lesson's review, and the bot's `refine-review -l`, still ask that sentence."""
        from audiolesson.cli import _plan, cmd_refine_review
        from audiolesson.review_wholes import refine_review
        learner = LearnerState("is", "en", "A1")
        sc = Planner(self.cur, learner, self.en, Timing(level="A1"), PlanConfig(minutes=5, new_items=3, priority=["afsakid", "peysu", "vegabref"]), today=TODAY).build()
        taught = sc.meta["wholes_taught"]["peysu"]
        apply_to_learner(sc, learner, TODAY)
        self.assertEqual(learner.learned_wholes["peysu"], taught)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "l.json"
            learner.save(path)
            loaded = LearnerState.load(path)
            self.assertEqual(loaded.learned_wholes, learner.learned_wholes, "saved and read back")
            old = json.loads(path.read_text())
            del old["learned_wholes"]
            path.write_text(json.dumps(old))
            self.assertEqual(LearnerState.load(path).learned_wholes, {}, "a file from before it existed reads as empty")
            loaded.save(path)
            # a later lesson: the part is asked bare and its pattern is not met; the kept sentence is what the review asks
            review = [{"items": ["peysu"], "prompt": "a sweater", "answer": "peysu", "stage": "meaning"}]
            out, report = refine_review(review, self.cur, {"peysu"}, self.en, loaded.learned_wholes)
            self.assertEqual([q["answer"] for q in out], [taught["answer"]])
            import io, sys, argparse
            from contextlib import redirect_stdout
            args = argparse.Namespace(curriculum=ROOT / "curricula" / "is-en", known="en", learner=str(path))
            stdin, sys.stdin = sys.stdin, io.StringIO(json.dumps({"review": review, "met": ["peysu"]}))
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    cmd_refine_review(args)
            finally:
                sys.stdin = stdin
            self.assertEqual([q["answer"] for q in json.loads(buf.getvalue())["review"]], [taught["answer"]])
        # today's teaching replaces the old line; the script carries a snapshot for a review made without the learner
        plan = _plan(sc, self.cur)
        self.assertEqual({q["answer"] for q in plan["review"] if "peysu" in q["items"]}, {taught["answer"]})
        self.assertIn("learned_wholes", sc.meta)
        learner.learned_wholes["peysu"] = {"through": "attu", "answer": "Old line?", "meaning": "x"}
        apply_to_learner(sc, learner, TODAY)
        self.assertEqual(learner.learned_wholes["peysu"], taught)

    def test_the_daily_read_lists_the_parts_still_asked_bare_that_have_a_home(self):
        from audiolesson.review_wholes import bare_parts_with_a_home
        review = [
            {"items": ["hjalpina"], "prompt": "the help", "answer": "hjálpina"},
            {"items": ["hjalpina"], "prompt": "Thanks for the help.", "answer": "Takk fyrir hjálpina."},
            {"items": ["peysu"], "prompt": "a sweater", "answer": "peysu", "bonus": True},
        ]
        self.assertEqual(bare_parts_with_a_home(review, self.cur), ["hjalpina"])
        self.assertEqual(bare_parts_with_a_home(review[1:], self.cur), [])

    def test_a_whole_taught_for_one_part_does_not_make_other_parts_askable_through_it(self):
        from audiolesson.review_wholes import whole_for
        cur = self.cur
        taught = {"through": "attu", "answer": "Áttu peysu?", "meaning": "Do you have a sweater?"}
        self.assertIsNone(whole_for(cur, cur.by_id["vegabref"], {"takk"}, self.en), "not met, not taught with it")
        self.assertEqual(whole_for(cur, cur.by_id["peysu"], {"takk"}, self.en, taught)["answer"], "Áttu peysu?", "asked exactly as taught")

    def test_a_part_without_an_authored_home_or_with_a_strange_frame_is_introduced_as_before(self):
        b = self._builder()
        self.assertIsNone(b.whole_home(self.cur.by_id["kaffihusid"]), "no construction names it")
        thusund = self._builder(met=[])
        home = thusund.whole_home(self.cur.by_id["tvo"])
        self.assertNotEqual(home[0].id if home else None, "thad_kostar_big", "«Það kostar … þúsund krónur.» has two words they have never met; «klukkan tvö» has one")
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
        # no other filler is known, so no other sentence follows: the swap is promised for later (lesson 34, «hnetum»)
        self.assertIn("It is a pattern: other words can go in its place. You will meet them later.", text)
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
        self.assertEqual(sc.meta["wholes_taught"]["peysu"]["through"], "attu", "taught whole today")  # #277: the part's later asking credits the part, not the pattern

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
        lessons = list(ListeningTaskTests._course(25))  # «hjálpina» comes in lesson 25 since small talk's third and fourth levels took their lines earlier
        changed = 0
        for cur, _, sc in lessons:
            plan = _plan(sc, cur)
            self.assertEqual(parts_outside_their_whole(plan["review"], cur), 0, f"lesson {sc.lesson_number}")
            changed += len(plan["review_refined"])
            answers = [q["answer"].casefold() for q in plan["review"] if not q.get("bonus")]
            self.assertEqual(len(answers), len(set(answers)), f"lesson {sc.lesson_number}: one answer asked twice")
        self.assertGreater(changed, 10, "the review has something to refine on a real course")
        # lesson 20's case on the real path: the part comes in with its whole, introduced in it or caught from the line that holds it (#339)
        labels = [e.label for _, _, sc in lessons for e in sc.exercises if e.kind == "intro"]
        self.assertTrue({"new: Takk fyrir hjálpina. (hjálpina)", "new (catch): hjálpina"} & set(labels))
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
            return Theme(scene_line="You are there.", id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=[
                Turn(who="partner", say="Þarftu poka?", meaning="Do you need a bag?", variants=[{"say": "Viltu poka?", "meaning": "Do you want a bag?", "meaning_ja": "袋がほしいですか？", "word_glosses": gloss}]),
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
        return Theme(scene_line="You are there.", id="x", scenario="A3", title="X", levels=[Level(goal="g", turns=[
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
        self.assertIn("Listen, then answer: How long does this take?", sc.transcript())
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
        self.assertIn("Listen, then answer: How much does this cost?", text, "#303: the need is named")
        self.assertLess(text.index("At the till."), text.index("How much does this cost?"), "the scene, then the need")
        self.assertLess(text.index("How much does this cost?"), text.index("**Speaker B:** Það kostar fimm"), "the need before the line")
        sc2 = Script(1, "t", "is", "en")
        from dataclasses import replace as _replace
        append_task(b, sc2, _replace(task, scene="", line="Það kostar tvö þúsund krónur."), 120.0)
        self.assertIn("Listen, then answer: How much does this cost?", sc2.transcript(), "no scene: the need alone")
        self.assertNotIn("How much is it?", sc2.transcript())
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
        task = catch_unknown("Viltu poka?", glosses, known, "en", repair, repair_known=True, source="theme:x:1:0:1", scene="", line_meaning="Do you want a bag?")
        self.assertEqual((task.kind, task.answer, task.meaning, task.repair, task.item_ids), ("catch_unknown", "Viltu", "do you want", "Hvað þýðir viltu?", (repair.id,)))
        each = lambda **kw: catch_unknown(**{"line": "Viltu poka?", "glosses": glosses, "known_words": known, "known_lang": "en", "repair": repair, "repair_known": True, "source": "s", "scene": "", "line_meaning": "Do you want a bag?", **kw})
        self.assertIsNone(each(repair_known=False), "the learner cannot yet ask what a word means")
        self.assertIsNone(each(line="Viltu poka? Viltu."), "the same unknown word twice")
        self.assertIsNone(each(known_words=known - {"poka"}), "two unknown words")
        self.assertIsNone(each(known_words=known | {"viltu"}), "no unknown word")
        self.assertIsNone(each(glosses={}), "an unknown word without an authored meaning")

    def test_a_catch_is_asked_with_the_repair_phrase_and_records_nothing(self):
        from audiolesson.listening_tasks import append_task, catch_unknown
        repair = self.cur.by_id["hvad_thydir_thetta"]
        b = self._builder(known=[repair.id])
        task = catch_unknown("Viltu poka?", {"viltu": {"en": "do you want", "ja": "ほしいですか"}}, self._known("poka"), "en", repair, repair_known=True, source="s", scene="", line_meaning="Do you want a bag?")
        sc = Script(1, "t", "is", "en")
        ex = append_task(b, sc, task, 120.0)
        self.assertEqual(ex.kind, "catch_unknown")
        answers = [g for g in sc.segments if g.type == "answer"]
        self.assertEqual([g.text for g in answers], ["Hvað þýðir viltu?"])
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
        """The first ``lessons`` lessons of the 30-minute themed course, as ``(curriculum, learner, script)``; built once per process
        (``tests/course_cache.py``)."""
        return course_cache.take("listening-30", ListeningTaskTests._fresh_course, lessons)

    @staticmethod
    def _fresh_course(lessons):
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
        # the pick-outs of this course start around lesson 19: at 21 lessons the count stood at the threshold's edge (4), and #327's goal line,
        # a few seconds at each lesson's start, shifted the course to 3; three lessons more give 12
        lessons = list(self._course(24))
        kinds = Counter(e.kind for _, _, sc in lessons for e in sc.exercises)
        self.assertGreater(kinds["pick_out"], 3)
        self.assertGreater(kinds["catch_unknown"], 3)
        for cur, learner, sc in lessons:
            m = sc.meta
            closing_at = next((e.start for e in sc.exercises if e.kind == "closing"), float("inf"))  # the closing block's own exercises are not counted
            # counted from the target to the closing block, and 0 in a lesson whose target was not delivered (the row's definition, as the run row below)
            self.assertEqual(m["pick_out_count"], sum(e.kind == "pick_out" for e in sc.exercises if m["target_reached_s"] <= e.start < closing_at) if m["target_delivered"] else 0)
            self.assertEqual(_plan(sc, cur)["second_half"]["pick_out_count"], m["pick_out_count"])
            # the plan before the render's fit, which scales the pauses to land on the minutes: within two and a half minutes of them
            self.assertLessEqual(sc.total_duration, 30 * 60 + 150, sc.lesson_number)
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
            between = [e for e in sc.exercises if m["target_reached_s"] <= e.start < closing_at and e.kind not in ("opening", "closing")] if m["target_delivered"] else []
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
        # every question a two-piece line was asked with, whichever lines the simulated course reached (#429 step 11: the course's material moved, and
        # the coffee's and the tour's questions gave way to «When do you meet?»)
        lead = Prompts.load("en").get("pick_out_need_ask", ask="")
        asked = set()
        for _, _, sc in self._course(30):
            asked |= {g.text[len(lead):] for g in sc.segments if g.type == "narrate" and (g.text or "").startswith(lead)}
        self.assertGreaterEqual(len(asked), 2, asked)
        self.assertTrue(all(q.endswith("?") for q in asked), asked)

    def test_a_scene_unit_before_the_target_takes_only_a_scene_already_played(self):
        """#273 (it replaces #248's "no pick-out before the target"): a pick-out or a catch task may come before the target is delivered, but only in a scene the
        learner has played: not the lesson's own, until its exchange has been played in the lesson."""
        before = 0
        for _, _, sc in self._course(21):
            m = sc.meta
            reached = m["target_reached_at"]
            own = m.get("theme")
            for e in sc.exercises:
                if e.kind not in ("pick_out", "catch_unknown") or not (reached and e.start + 0.01 < reached - 1):
                    continue
                before += 1
                if own and not own.get("replay"):  # a level played in an earlier lesson is a scene already played
                    played = any(x.kind == "dialogue" and x.label.startswith(f"dialogue: theme:{own['id']}:{own['level']}") and x.start < e.start for x in sc.exercises)
                    self.assertTrue(played or not e.label.startswith(f"theme:{own['id']}:{own['level']}:"), f"lesson {sc.lesson_number}: {e.label} is from a scene not played yet")
        self.assertGreater(before, 0, "scene units are spread through the lesson, not saved for after the target")

    def test_the_interleave_step_places_units_at_least_an_interval_apart(self):
        """#275 review: the last scene's end is read from the segments (an exercise's start and duration are only filled in when the lesson is done), so the step
        does not fire on every pass after the first interval: two units it places are at least `scene_unit_interval` apart, and no longest stretch exceeds
        the interval by more than one unit's time and the supply allows."""
        interval = PlanConfig().scene_unit_interval
        placed = 0
        for _, _, sc in self._course(21):
            times = sc.meta["scene_units_placed"]
            placed += len(times)
            for a, b in zip(times, times[1:]):
                self.assertGreaterEqual(b - a, interval, f"lesson {sc.lesson_number}: {times}")
        self.assertGreater(placed, 0)

    def test_the_longest_stretch_without_a_scene_is_in_the_plan(self):
        lessons = list(self._course(21))
        for _, _, sc in lessons:
            self.assertIn("longest_without_scene_s", sc.meta)
            self.assertLessEqual(sc.meta["longest_without_scene_s"], sc.total_duration)
        late = [sc.meta["longest_without_scene_s"] for _, _, sc in lessons[12:]]
        self.assertLess(sum(late) / len(late), 11 * 60, late)



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

    def test_a_sentence_built_for_the_word_never_takes_a_construction_that_excludes_it(self):
        """The word's own path (``generate_with``: «Use it in a sentence.» after a new word, #287) honours the exception too: the replay of the
        lesson-25 export gave «Áttu leigubíl?» in lesson 26 through it."""
        from audiolesson.exercises import Builder
        cur = curriculum_from_dict(self._raw())
        learner = fresh()
        for i in ("peysa", "bil", "attu", "tharf"):
            learner.items[i] = ItemState(stage="meaning", durable_successes=2, successes=8, interval_days=7, recalled=3)
        b = Builder(cur, Prompts.load("en"), Timing(level="A1"), learner)
        said = set()
        for seed in range(20):
            b.rng.seed(seed)
            g = b.generate_with(cur.by_id["bil"])
            if g is not None:
                said.add(g.target)
        self.assertEqual(said, {"Ég þarf leigubíl."})

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

    def test_a_pattern_met_but_not_yet_known_is_enough_for_the_new_word_to_be_taught_as_a_word(self):
        """#316 review: on the real learner a pattern often stays below ``knows`` (two confirmed recalls on a due date) for days after it is in use;
        the weaker test of #206 (met, not failed at its last report) decides, since the word still gets its own full introduction."""
        learner = self._learner(("tvo",))
        learner.items["pat"] = ItemState(stage="recombine", successes=8, durable_successes=1, recalled=3, interval_days=3,
                                         due=(TODAY + timedelta(days=1)).isoformat(), last_practiced=(TODAY - timedelta(days=1)).isoformat())
        self.assertFalse(learner.knows("pat"))
        sc = self._plan(learner)
        self.assertEqual(sc.meta["pattern_instances"], ["ph"])
        self.assertIn("thrja", sc.meta["new_items"])

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

    def test_with_the_pattern_not_yet_known_the_introduction_is_as_today(self):
        sc = self._plan(self._learner(("tvo", "thrja")))
        self.assertEqual(sc.meta["pattern_instances"], [])
        self.assertTrue(any(e.kind == "intro" and e.item_ids == ["ph"] for e in sc.exercises))

    def test_with_the_pattern_known_and_the_filler_new_the_word_is_taught_and_the_phrase_is_one_pattern_sentence(self):
        """#311: «Ég þarf úlpu.» of a known pattern with a new word: the word is introduced as a word, the phrase has no ladder of its own."""
        sc = self._plan(self._learner(("pat", "tvo")))
        self.assertEqual(sc.meta["pattern_instances"], ["ph"])
        self.assertIn("thrja", sc.meta["new_items"])
        self.assertFalse(any(e.kind == "intro" and e.item_ids == ["ph"] for e in sc.exercises), "the phrase is not introduced as a unit")
        self.assertTrue(any("thrja" in e.item_ids for e in sc.exercises), "the word has its own exercises")

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

        for i in ("skyr", "erud_thid_med"):
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
        from audiolesson.review_wording import with_literal  # lesson 60: a situation is asked with its literal meaning after it

        asked = {with_literal(s, with_situations, prompts) for s in with_situations.situations}
        self.assertTrue(asked <= set(json.loads(out.getvalue())[with_situations.id]["cues"]))

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
            # the feminine «þrjár» line is known too: without it #439's number choice brings it ahead of the trip order («Þrjá miða» and «þrjú
            # þúsund» are known), which is the choice's own rule, not what these tests are about
            if (i.order < self.cur.by_id["virkar_ekki"].order and i.id not in ("sturtan", "ljosid")) or i.id == "thad_eru_minus_thrjar_gradur":
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
        """Lessons 8–24 (8–16 before the owner's change after lesson 29): with the small sums gone, lessons 13–16 no longer introduce «tvær», «ein» and
        «Ein króna.» late, and a sample of nine lessons moved from 0.52 to 0.56 of new items in the first third; over lessons 8–24 it is 0.50 → 0.53,
        and 0.505 → 0.525 over 8–32. The sample is widened so the share measures the planner, not which cheap items one stretch of the course has."""
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        learner = LearnerState("is", "en", "A1")
        day = TODAY
        first_third, intros, worst_gap = 0, 0, 0.0
        for n in range(1, 25):
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


if __name__ == "__main__":
    unittest.main()
