"""#416 (lesson 38: «"nei, takk." や "takk." を何度も言う… 言わされすぎ»): in an exchange played again (a scene heard again, the lesson's own
exchange's late play) a set reply the learner plainly knows is said in the model voice, not asked. A limited exception to "sayable → asked"
(#263): every item of the line a named set reply (``Item.set_reply``: a thanks, a yes, a no), two words at most, learned and not weak, not
taught today; a reply due for review keeps one ask. The first play of the lesson's own exchange asks every line, and the opening says what
is asked and what is played (review of #422)."""
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import CurriculumError, load_curriculum, validate
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 3, 1)
PROMPTS = Prompts.load("en")
GUIDES = {PROMPTS.get("listening_intro_known_voiced"), PROMPTS.get("dialogue_voiced_note")}


class SetReplyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", cls.cur)
        cls.themes = load_themes(ROOT / "curricula" / "is-en", cls.cur, scenarios)
        cls.order = scenario_order(scenarios)
        cls.supermarket = next(t for t in cls.themes if t.id == "supermarket")

    def learner(self, **changes):
        """Every item learned and not due (``changes`` overrides an item's state); every theme level played."""
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.by_id:
            learner.items[i] = ItemState(due=(TODAY + timedelta(days=20)).isoformat(), successes=6, durable_successes=3, stage="dialogue", recalled=2,
                                         last_outcome="recalled", interval_days=20, last_practiced=(TODAY - timedelta(days=3)).isoformat())
        for i, change in changes.items():
            learner.items[i] = replace(learner.items[i], **change)
        for t in self.themes:
            learner.themes_done[t.id] = len(t.levels)
            learner.themes_last[t.id] = 1
        return learner

    def planner(self, learner=None, themes=None, **cfg):
        themes = themes if themes is not None else self.themes
        order = self.order if themes is self.themes else [t.scenario for t in themes]
        return Planner(self.cur, learner or self.learner(), PROMPTS, Timing(level="A1"),
                       PlanConfig(minutes=30, themes=themes, theme_scenarios=order, **cfg), today=TODAY)

    # ---------------------------------------------------------------- which lines

    def test_only_named_set_replies_of_two_words_at_most(self):
        p = self.planner()
        for items, say in ((["takk"], "Takk."), (["nei", "takk"], "Nei, takk."), (["ja", "takk"], "Já, takk."), (["takk_kaerlega"], "Takk kærlega.")):
            self.assertTrue(p.known_set_reply(items, say), say)
        # lines that do the scene's work (the review of #422; «Til hægri?» was voiced in lesson 44 of a continued replay)
        for items, say in ((["vatn", "takk"], "Vatn, takk."), (["til_haegri"], "Til hægri?"), (["er_afslattur"], "Er afsláttur?"),
                           (["gjordu_svo_vel"], "Gjörðu svo vel."), (["takk_kaerlega", "bless"], "Takk kærlega. Bless.")):
            self.assertFalse(p.known_set_reply(items, say), say)
        self.assertFalse(self.planner(set_reply_words=0).known_set_reply(["takk"], "Takk."), "0 asks every line")

    def test_a_weak_or_new_reply_is_asked(self):
        for change in ({"last_outcome": "hesitated"}, {"durable_successes": 1}, {"due": TODAY.isoformat()}):
            self.assertFalse(self.planner(self.learner(takk=change)).known_set_reply(["takk"], "Takk."), change)
        p = self.planner()
        p.builder.in_lesson.add("takk")
        self.assertFalse(p.known_set_reply(["takk"], "Takk."), "taught today: asked")

    def test_a_due_reply_keeps_one_ask(self):
        p = self.planner(self.learner(takk={"due": TODAY.isoformat()}))
        self.assertFalse(p.known_set_reply(["takk"], "Takk."))
        p.exposures["takk"] = ["dialogue"]  # asked once in this lesson: its review is done
        self.assertTrue(p.known_set_reply(["takk"], "Takk."))

    def test_set_reply_marks_a_phrase(self):
        cur = load_curriculum(ROOT / "curricula" / "is-en")
        word = next(i for i in cur.items if i.kind == "vocab")
        cur.items[cur.items.index(word)] = cur.by_id[word.id] = replace(word, set_reply=True)
        with self.assertRaisesRegex(CurriculumError, "set_reply marks a fixed phrase"):
            validate(cur)

    def test_a_play_that_would_ask_nothing_keeps_its_replies_asked(self):
        p = self.planner()
        replies = [t for t in self.supermarket.levels[0].turns if t.who == "you" and p.known_set_reply(t.items, t.say)]
        self.assertEqual([t.say for t in replies], ["Takk.", "Já, takk."])
        self.assertEqual(p.voiced_replies(replies, set()), set(), "nothing would be asked")
        you = [t for t in self.supermarket.levels[0].turns if t.who == "you"]
        self.assertEqual({you[k].say for k in p.voiced_replies(you, set())}, {"Takk.", "Já, takk."})

    # ---------------------------------------------------------------- a built lesson

    @staticmethod
    def lines(sc, ex):
        """The learner's lines of exercise ``ex`` in order: (text, how) with how «asked» (an answer pause before it), «heard» («Here you would
        say:») or «voiced» (neither: said as the exchange goes); and the cue narrated just before each asked line."""
        segs = [s for s in sc.segments if s.exercise == ex.index]
        out = []
        for k, s in enumerate(segs):
            if s.type != "answer":
                continue
            if segs[k - 1].type == "pause" and segs[k - 1].role == "answer":
                cue = next(g.text for g in reversed(segs[:k]) if g.type == "narrate")
                out.append((s.text, "asked", cue))
            elif next(g.text for g in reversed(segs[:k]) if g.type != "pause") == PROMPTS.get("listening_line"):
                out.append((s.text, "heard", None))
            else:
                out.append((s.text, "voiced", None))
        return out

    def own_plays(self, sc):
        """The plays of the lesson's own exchange, in the order they were played (its label repeats, so the order tells them apart)."""
        theme = sc.meta["theme"]
        plays = sorted((e for e in sc.exercises if e.label.startswith(f"dialogue: theme:{theme['id']}:{theme['level']}")), key=lambda e: e.index)
        self.assertEqual(len(plays), 2)
        return plays

    def build_supermarket(self, **changes):
        """A lesson whose own exchange is the supermarket's second level, played for the first time («Ég er bara að skoða.», «Hvað er þetta mikið
        samtals?», «Nei, takk.»)."""
        learner = self.learner(**changes)
        learner.themes_done = {"supermarket": 1}
        sc = self.planner(learner, themes=[self.supermarket]).build()
        self.assertEqual((sc.meta["theme"]["id"], sc.meta["theme"]["level"]), ("supermarket", 2))
        return sc

    def test_the_first_play_asks_every_line_and_the_late_play_voices_only_known_replies(self):
        sc = self.build_supermarket()
        first, late = self.own_plays(sc)
        self.assertLess(first.index, late.index)
        you = [t for t in self.supermarket.levels[1].turns if t.who == "you"]
        self.assertEqual([(text, how) for text, how, _ in self.lines(sc, first)], [(t.say, "asked") for t in you], "the first play asks every line")
        late_lines = self.lines(sc, late)
        self.assertEqual([text for text, how, _ in late_lines if how == "voiced"], ["Nei, takk."])
        for t, (text, how, cue) in zip(you, late_lines):
            if how == "asked":
                self.assertEqual(cue, t.cue, "a line asked keeps its cue")
        self.assertEqual({text for text, how, _ in late_lines if how == "asked"}, {"Ég er bara að skoða.", "Hvað er þetta mikið samtals?"}, "the target lines are asked")
        self.assertIn("supermarket:2:3", sc.meta["voiced_replies"])

    def test_a_weak_reply_keeps_its_ask_in_the_late_play(self):
        sc = self.build_supermarket(takk={"last_outcome": "hesitated"})
        _, late = self.own_plays(sc)
        lines = self.lines(sc, late)
        self.assertIn(("Nei, takk.", "asked", "No need."), lines)
        self.assertNotIn("voiced", [how for _, how, _ in lines])

    def test_the_opening_says_what_is_asked_and_what_is_played(self):
        """The first play that voices a reply says so; later ones don't repeat it (#438, lesson 41: three times, about 19 s): a scene heard again
        says «The conversation again.», an authored dialogue its usual opening."""
        sc = self.planner().build()
        played = [e for e in sc.exercises if e.kind == "dialogue"]
        voicing = [e for e in played if any(how == "voiced" for _, how, _ in self.lines(sc, e))]
        self.assertGreater(len(voicing), 1, "an all-known learner hears set replies played again, more than once")
        guided = []
        for e in played:
            narrated = {s.text for s in sc.segments if s.exercise == e.index and s.type == "narrate"}
            if narrated & GUIDES:
                guided.append(e)
            if e in voicing:
                self.assertNotIn(PROMPTS.get("listening_intro_known"), narrated, "«say them when it's your turn» is not said when some are played")
                self.assertTrue(any(how == "asked" for _, how, _ in self.lines(sc, e)), "a play that voices replies still asks")
        self.assertEqual(guided, voicing[:1], "the guide once a lesson, at the first play that voices a reply")
        later = [e for e in voicing[1:] if e.label.startswith("heard: ")]
        for e in later:
            narrated = [s.text for s in sc.segments if s.exercise == e.index and s.type == "narrate"]
            self.assertIn(PROMPTS.get("listening_intro_again"), narrated, e.label)

    def test_without_the_exception_every_reply_is_asked(self):
        sc = self.planner(set_reply_words=0).build()
        self.assertEqual(sc.meta["voiced_replies"], [])
        for e in sc.exercises:
            if "theme:" in e.label and e.kind == "dialogue":
                self.assertNotIn("voiced", [how for _, how, _ in self.lines(sc, e)], e.label)


if __name__ == "__main__":
    unittest.main()


class AuthoredDialogueReplyTests(unittest.TestCase):
    """Lesson 40 (#416 rescoped): authored dialogues bypassed the theme's selection, so `kynning` asked «Thank her.» → «Takk.» and `kaffihus»
    asked «Say: no, thanks.» → «Nei, takk.» and «Takk.». A dialogue played before voices the set replies the learner plainly knows."""

    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        cls.themes = []  # no theme here: a dialogue alone
        cls.cafe = next(d for d in cls.cur.dialogues if d.id == "kaffihus")

    def learner(self, **changes):
        return SetReplyTests.learner(self, **changes)

    def play(self, learner, times):
        from audiolesson.script import Script

        learner.dialogues_done["kaffihus"] = times
        p = Planner(self.cur, learner, PROMPTS, Timing(level="A1"), PlanConfig(minutes=30), today=TODAY)
        sc = Script(1, "t", "is", "en")
        p._play_dialogue(sc, self.cafe)
        ex = sc.exercises[-1]
        return p, sc, ex, SetReplyTests.lines(sc, ex)

    def test_a_dialogue_played_before_voices_the_known_replies_and_asks_the_rest(self):
        p, sc, ex, lines = self.play(self.learner(), times=5)
        self.assertEqual([t for t, how, _ in lines if how == "voiced"], ["Nei, takk.", "Takk."])
        self.assertIn(("Gætirðu talað hægar?", "asked", "You didn't catch that. Ask her to speak more slowly."), lines)
        self.assertEqual(p.voiced_lines, ["kaffihus:2", "kaffihus:4"])
        narrated = {s.text for s in sc.segments if s.exercise == ex.index and s.type == "narrate"}
        self.assertIn(PROMPTS.get("dialogue_voiced_note"), narrated, "the opening says the short replies are played")
        self.assertNotIn("Thank her.", narrated)
        self.assertNotIn("takk", p.exposures, "a voiced line earns no practice")
        # review of #430: the dialogue's required «nei» and «takk», said only in voiced lines, are heard, not practised
        self.assertFalse({"nei", "takk"} & set(ex.item_ids), ex.item_ids)
        self.assertTrue({"nei", "takk"} <= set(ex.heard_ids), ex.heard_ids)
        self.assertNotIn("nei", p.support)
        self.assertTrue({"godan_daginn", "eg_aetla_ad_fa", "kaffi"} <= set(ex.item_ids), "the asked lines' items stay practised")

    def test_the_first_encounter_and_a_weak_reply_keep_their_asks(self):
        _, _, _, first = self.play(self.learner(), times=0)
        self.assertNotIn("voiced", [how for _, how, _ in first], "a dialogue met for the first time asks every line")
        _, _, _, weak = self.play(self.learner(takk={"last_outcome": "hesitated"}), times=5)
        self.assertIn(("Takk.", "asked", "Thank her."), weak, "a hesitated «takk» keeps «Takk.» asked")
        self.assertEqual([t for t, how, _ in weak if how == "voiced"], ["Nei, takk."], "«Nei, takk.» is its own learned phrase, «nei_takk»")

    def test_a_literal_line_is_read_word_by_word_when_its_phrase_was_never_met(self):
        learner = self.learner()
        del learner.items["nei_takk"]
        p = Planner(self.cur, learner, PROMPTS, Timing(level="A1"), PlanConfig(minutes=30), today=TODAY)
        turn = next(t for t in self.cafe.turns if t.expect_text == "Nei, takk.")
        self.assertEqual(p.dialogue_turn_reply(turn), (["nei", "takk"], "Nei, takk."))
        other = next(t for t in self.cafe.turns if t.expect_text and t.expect_text.startswith("Góðan daginn"))
        self.assertEqual(p.dialogue_turn_reply(other)[0], [], "a line with other words is not a set reply")
