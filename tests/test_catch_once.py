"""#339: a word is caught once (across lessons); some new words are introduced through the catch; pick-outs rotate across lessons."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing

TODAY = date(2026, 3, 1)
IS_EN = Path(__file__).resolve().parent.parent / "curricula" / "is-en"


class CatchOnceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(IS_EN)
        scen = load_cando(IS_EN)
        cls.themes = load_themes(IS_EN, cls.cur, scen)
        cls.order = scenario_order(scen)

    def cfg(self):
        return PlanConfig(minutes=30, new_target=8, themes=self.themes, theme_scenarios=self.order)

    def test_the_learner_state_keeps_the_caught_words_and_the_listening_log(self):
        import tempfile

        l = LearnerState("is", "en", "A1")
        l.caught_words = ["sestu"]
        l.listening_log = {"line|answer": 7}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "l.json"
            l.save(path)
            back = LearnerState.load(path)
            self.assertEqual((back.caught_words, back.listening_log), (["sestu"], {"line|answer": 7}))
            LearnerState("is", "en", "A1").save(path)
            self.assertEqual(LearnerState.load(path).caught_words, [], "an old file reads empty")

    def test_a_course_catches_no_word_twice_and_records_what_it_caught(self):
        l = LearnerState("is", "en", "A1")
        day = TODAY
        seen: list[str] = []
        for n in range(1, 24):
            sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
            m = sc.meta
            self.assertEqual(m["caught_before"], 0, f"lesson {n}")
            seen += m["caught_words"]
            apply_to_learner(sc, l, day)
            l.report([], [], day + timedelta(days=1), lesson_number=n, recalled=m["new_items"])
            day += timedelta(days=1)
        self.assertTrue(seen, "the course does catch words (a test that passes with none proves nothing)")
        self.assertEqual(len(seen), len(set(seen)), seen)
        self.assertEqual(set(seen), set(l.caught_words))

    def test_a_word_caught_before_is_not_a_catch_word_again(self):
        l = LearnerState("is", "en", "A1")
        day = TODAY
        for n in range(1, 24):
            sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
            apply_to_learner(sc, l, day)
            l.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        l.caught_words = sorted(set(l.caught_words) | {"sestu", "kjötsúpa", "þarftu"})
        sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
        self.assertFalse({"sestu", "kjötsúpa", "þarftu"} & set(sc.meta["caught_words"]))

    def test_a_new_word_that_a_line_holds_as_its_only_unknown_is_introduced_through_the_catch(self):
        l = LearnerState("is", "en", "A1")
        for i in ("hvad_thydir_thetta", "hvad_kostar_thetta"):
            if i in self.cur.by_id:
                l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled", due=(TODAY + timedelta(days=5)).isoformat())
        p = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=TODAY)
        task = p.catch_intro_task(self.cur.by_id["thusund"], {"tvö", "krónur", "takk"}, set())
        self.assertIsNotNone(task)
        self.assertEqual((task.answer.lower(), task.meaning), ("þúsund", self.cur.by_id["thusund"].meaning))
        again = p.catch_intro_task(self.cur.by_id["thusund"], {"tvö", "krónur", "takk"}, {task.line})
        self.assertTrue(again is None or again.line != task.line, "each line once a lesson")
        l.caught_words = ["þúsund"]
        self.assertIsNone(p.catch_intro_task(self.cur.by_id["thusund"], {"tvö", "krónur", "takk"}, set()), "caught once, never again")

    def test_with_no_authored_line_the_sentence_its_introduction_would_teach_is_the_partners_line(self):
        """The owner (2026-10-15): about one new word in ten is introduced through the catch, the introduction inside its whole included. No authored partner
        line holds «ljósið» as its only unknown word; the sentence its introduction would have taught it in, «Ljósið virkar ekki.», does once the pattern is known."""
        l = LearnerState("is", "en", "A1")
        for i in ("hvad_thydir_thetta", "virkar_ekki", "sturtan"):
            l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled", due=(TODAY + timedelta(days=5)).isoformat())
        p = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=TODAY)
        self.assertTrue(p.builder.intro_catchable(self.cur.by_id["ljosid"]), "a word with a home sentence may be caught")
        task = p.catch_intro_task(self.cur.by_id["ljosid"], {"virkar", "ekki", "sturtan"}, set())
        self.assertIsNotNone(task)
        self.assertEqual((task.line, task.answer.lower(), task.cue), ("Ljósið virkar ekki.", "ljósið", "something doesn't work."))
        self.assertTrue(task.source.startswith("home:virkar_ekki"))

    def test_a_catch_in_place_of_the_introduction_inside_a_whole_keeps_that_sentence(self):
        """Review of #350: the learner knows «Hvað kostar þetta?», so «salat» is caught in «Hvað kostar salat?», the sentence its introduction would have
        taught it in. That sentence stays the word's (``wholes_taught``): its practice and its next-day question ask it, not the bare «salat»."""
        l = LearnerState("is", "en", "A1")
        for i in ("hvad_thydir_thetta", "hvad_kostar_thetta"):
            l.items[i] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled", due=(TODAY + timedelta(days=5)).isoformat())
        p = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=30, new_target=10, priority=["salat"]), today=TODAY)
        sc = p.build()
        self.assertEqual(sc.meta["catch_introductions"], ["salat"])
        self.assertEqual(p.builder.wholes_taught.get("salat", {}).get("answer"), "Hvað kostar salat?")
        recalls = [e.label.split(": ", 1)[-1] for e in sc.exercises if "salat" in e.item_ids and e.kind == "recall"]
        self.assertTrue(recalls and "salat" not in recalls, recalls)
        self.assertEqual([q["answer"] for q in sc.review_questions() if "salat" in q["items"]], ["Hvað kostar salat?"])

    def test_about_one_new_item_in_ten_is_introduced_through_the_catch(self):
        self.assertEqual(PlanConfig(minutes=30, new_target=10).catch_intros(), 1)
        self.assertEqual(PlanConfig(minutes=30, new_items=8).catch_intros(), 1)
        self.assertEqual(PlanConfig(minutes=30, new_target=20).catch_intros(), 2)
        self.assertEqual(PlanConfig(minutes=15, new_items=3).catch_intros(), 0)

    def test_a_hard_to_say_word_keeps_its_plain_introduction_with_the_slow_split_model(self):
        """Review of #344: the slow, split model (#212) lives in the plain introduction; a catch must not take it from «eldfjall» and the like."""
        from unittest import mock

        from audiolesson.sounds import hard_sounds, hard_words_of

        asked: list[str] = []
        real = Planner.catch_intro_task

        passed: list[bool] = []

        def spy(self_, item, known, used, caught=None):
            asked.append(item.id)
            passed.append(caught is not None)  # the build hands over the lesson's caught set (the seed and this lesson's catches), not only the saved one
            return real(self_, item, known, used, caught)

        l = LearnerState("is", "en", "A1")
        day = TODAY
        with mock.patch.object(Planner, "catch_intro_task", spy):
            for n in range(1, 31):
                sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
                apply_to_learner(sc, l, day)
                l.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
                day += timedelta(days=1)
        self.assertTrue(asked, "the catch was considered for some words")
        self.assertTrue(all(passed), "review of #344: the caught set of the lesson is passed at every call")
        self.assertEqual([i for i in asked if hard_sounds(self.cur.by_id[i]) or hard_words_of(self.cur.by_id[i])], [], "never for a hard-to-say word")

    def course_to(self, n):
        l, day = LearnerState("is", "en", "A1"), TODAY
        for k in range(1, n + 1):
            sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
            apply_to_learner(sc, l, day)
            l.report([], [], day + timedelta(days=1), lesson_number=k, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        return l, day

    def test_a_file_made_before_the_log_is_seeded_once_with_the_words_that_were_asked(self):
        """Review of #344: the seed is the glossed words of the played levels' lines that held that word as their only unknown one; the others were never asked."""
        l, day = self.course_to(22)
        asked = set(l.caught_words)
        self.assertTrue(asked, "the course asked some words (a test over an empty list proves nothing)")
        l.caught_words, l.caught_seeded = [], False  # a file made before the log
        p = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day)
        known = set(p._component_base()[0])
        seed = p.caught_seed(known)
        self.assertTrue(seed)
        self.assertTrue({w for w in asked if w not in known} <= set(seed), "every asked word that is still unknown is seeded")
        # a glossed word of a line with two unknown words was never asked and is not seeded
        two = [
            w.lower()
            for t in self.themes for n in range(min(l.themes_done.get(t.id, 0), len(t.levels))) for turn in t.levels[n].turns if turn.who == "partner"
            for ln in turn.lines() for w in (ln.word_glosses or {})
            if len([x for x in __import__("audiolesson.text", fromlist=["WORD"]).WORD.findall(ln.say) if x.lower() not in known]) >= 2
        ]
        self.assertTrue(two, "the data has glossed lines that do not qualify yet")
        only_two = [w for w in two if not any(w in ln.word_glosses and len([x for x in __import__("audiolesson.text", fromlist=["WORD"]).WORD.findall(ln.say) if x.lower() not in known]) == 1
                                              for t in self.themes for lv in t.levels for turn in lv.turns if turn.who == "partner" for ln in turn.lines())]
        self.assertTrue(only_two)
        self.assertFalse(set(only_two) & set(seed), "never asked, so not seeded")
        sc = p.build()
        apply_to_learner(sc, l, day)
        self.assertTrue(l.caught_seeded)
        self.assertTrue(set(seed) <= set(l.caught_words))
        again = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day + timedelta(days=1)).build()
        self.assertEqual(again.meta["caught_seed"], [], "seeded once")
        self.assertFalse(set(seed) & set(again.meta["caught_words"]))

    def test_the_pick_out_log_keys_on_the_turn_so_its_wordings_are_one_question(self):
        l, _ = self.course_to(22)
        self.assertTrue(l.listening_log, "pick-outs were heard")
        for key in l.listening_log:
            self.assertNotIn("|", key)
            self.assertTrue(key.startswith("theme:") or key in self.cur.by_id, key)

    def test_a_turn_drawn_again_gives_the_line_and_piece_heard_least_recently(self):
        """#339 (lesson 37): «klukkan hálf þrjú» was the answer every time the tour's line was drawn, so it was remembered, not heard. A turn
        rotates across lessons as before, and within it the line and piece heard least recently come first: a turn drawn again never repeats
        the line and piece it gave last while it has another it can give."""
        from collections import defaultdict

        l, day = LearnerState("is", "en", "A1"), TODAY
        drawn = defaultdict(list)
        for k in range(1, 31):
            sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
            for src in sc.meta["pick_out_answers_heard"]:
                drawn[src.rsplit(":", 2)[0]].append(src)
            apply_to_learner(sc, l, day)
            l.report([], [], day + timedelta(days=1), lesson_number=k, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertTrue(any(key.count(":") == 5 for key in l.listening_log), "the line and piece are logged beside the turn")
        varied = {turn: srcs for turn, srcs in drawn.items() if len(set(srcs)) > 1}
        self.assertTrue(varied, "some turns gave more than one line or piece")
        for turn, srcs in varied.items():
            self.assertFalse([a for a, b in zip(srcs, srcs[1:]) if a == b], f"{turn}: the same line and piece twice in a row: {srcs}")

    def test_a_conjunction_is_not_introduced_through_the_catch_and_a_told_word_is_lower_case(self):
        from audiolesson.exercises import Builder
        from audiolesson.listening_tasks import ListeningTask, introduce_by_catch
        from audiolesson.script import Script

        l = LearnerState("is", "en", "A1")
        for t in self.themes:
            l.themes_done[t.id] = 1
        b = Builder(self.cur, Prompts.load("en"), Timing(level="A1"), l)
        task = ListeningTask("catch_unknown", "x", "A café.", "Og þú talar íslensku?", "Og", "and", "catch_unknown_context", repair="Hvað þýðir og?", cue="Something you speak Icelandic?")
        sc = Script(1, "t", "is", "en")
        ex = introduce_by_catch(b, sc, task, self.cur.by_id["og"])
        self.assertEqual(ex.label, "new (catch): og")
        told = [g.text for g in sc.segments if g.type == "speak" and g.role == "listening_word"]
        self.assertEqual(told, ["og"])
        # the gate: «og» is neither a noun nor the filler of a pattern's slot
        p = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=TODAY)
        self.assertFalse(self.cur.by_id["og"].noun or p.builder.homes_of(self.cur.by_id["og"]))
        self.assertTrue(self.cur.by_id["kaffi"].noun or p.builder.homes_of(self.cur.by_id["kaffi"]))

    def test_the_daily_read_says_where_the_supply_of_catch_introductions_runs_out(self):
        l = LearnerState("is", "en", "A1")
        day = TODAY
        outcomes: set[str] = set()
        for n in range(1, 21):
            sc = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=day).build()
            outcomes |= set(sc.meta["catch_candidates"])
            apply_to_learner(sc, l, day)
            l.report([], [], day + timedelta(days=1), lesson_number=n, recalled=sc.meta["new_items"])
            day += timedelta(days=1)
        self.assertIn("no line holds it as the only unknown", outcomes)
        self.assertTrue(outcomes <= {"a form of a word met", "hard to say (keeps the slow model)", "held by a longer new item", "not a content word", "no line holds it as the only unknown", "introduced"}, outcomes)

    def test_a_word_is_not_caught_twice_in_one_lesson(self):
        from audiolesson.listening_tasks import REPAIR_ITEM

        l = LearnerState("is", "en", "A1")
        l.items[REPAIR_ITEM] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled", due=(TODAY + timedelta(days=5)).isoformat())
        p = Planner(self.cur, l, Prompts.load("en"), Timing(level="A1"), self.cfg(), today=TODAY)
        known = {"tvö", "krónur", "takk"}
        item = self.cur.by_id["thusund"]
        self.assertIsNotNone(p.catch_intro_task(item, known, set(), set()))
        self.assertIsNone(p.catch_intro_task(item, known, set(), {"þúsund"}), "caught earlier in this lesson")

    def test_the_words_own_scene_comes_first(self):
        from audiolesson.content import curriculum_from_dict

        base = {"curriculum": {"name": "x", "target_lang": "is", "known_lang": "en"}}
        items = [
            {"id": "repair", "kind": "phrase", "target": "Hvað þýðir þetta?", "meaning": "What does this mean?"},
            {"id": "kaffi", "kind": "vocab", "target": "kaffi", "meaning": "coffee", "topics": ["cafe"]},
        ]
        def turn(line):
            return {"cue": "x", "expect": "repair", "partner": line, "partner_meaning": "Would you like coffee?"}
        cur = curriculum_from_dict({**base, "items": items, "dialogues": [
            {"id": "d_off", "setting": "At a museum.", "topics": ["travel"], "turns": [turn("Viltu kaffi?")]},
            {"id": "d_cafe", "setting": "At a café.", "topics": ["cafe"], "turns": [turn("Viltu kaffi?")]},
        ]})
        l = LearnerState("is", "en", "A1")
        l.items["repair"] = ItemState(stage="meaning", durable_successes=2, successes=6, recalled=3, interval_days=7, last_outcome="recalled", due=(TODAY + timedelta(days=5)).isoformat())
        from audiolesson import planner as planner_mod  # REPAIR_ITEM is a fixed id: point the test's repair phrase at it

        old = planner_mod.REPAIR_ITEM
        planner_mod.REPAIR_ITEM = "repair"
        try:
            p = Planner(cur, l, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20, themes=[]), today=TODAY)
            task = p.catch_intro_task(cur.by_id["kaffi"], {"viltu"}, set())
        finally:
            planner_mod.REPAIR_ITEM = old
        self.assertIsNotNone(task)
        self.assertTrue(task.source.startswith("dialogue:d_cafe:"), task.source)


if __name__ == "__main__":
    unittest.main()
