"""#272: conversations sound like conversations: a beat after every partner line, reply pauses that fit the reply, one intro for a scene heard again,
and a catch task that reads as one sentence."""
import unittest
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import ItemState, LearnerState
from audiolesson.listening_tasks import append_task, catch_unknown, tokens, word_as_asked
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.themes import level_dialogue, load_themes
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent


def learner_with(ids, successes=3):
    learner = LearnerState("is", "en", "A1")
    for i in ids:
        learner.items[i] = ItemState(due=(date(2026, 3, 1) + timedelta(days=3)).isoformat(), successes=successes, durable_successes=successes, stage="meaning",
                                     recalled=successes, last_outcome="recalled", interval_days=3, last_practiced="2026-02-28")
    return learner


class ConversationTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", cls.cur)
        cls.themes = load_themes(ROOT / "curricula" / "is-en", cls.cur, scenarios)
        cls.en = Prompts.load("en")
        cls.cafe = next(t for t in cls.themes if t.id == "supermarket")

    def play(self, learner, translate, **kw):
        dlg = level_dialogue(self.cafe, 0, "en", {})
        b = Builder(self.cur, self.en, Timing(level="A1"), learner)
        sc = Script(1, "t", "is", "en")
        you = [t for t in self.cafe.levels[0].turns if t.who == "you"]
        ex = b.dialogue(sc, dlg, translate=translate, turn_items={k: t.items for k, t in enumerate(you)}, **kw)
        return sc, ex, dlg

    def test_every_partner_line_is_followed_by_a_beat_glossed_or_not(self):
        for translate in (True, False):
            sc, ex, dlg = self.play(learner_with([]), translate)
            partner = {t.opener for t in dlg.turns if t.opener} | {t.partner for t in dlg.turns if t.partner}
            segs = [g for g in sc.segments if g.exercise == ex.index]
            seen = 0
            for i, g in enumerate(segs):
                if g.type == "speak" and g.text in partner:
                    seen += 1
                    self.assertEqual((segs[i + 1].type, segs[i + 1].role), ("pause", "beat"), (translate, g.text))
            self.assertGreaterEqual(seen, 2)

    def test_a_reply_the_learner_has_said_before_gets_the_pause_of_a_single_exercise(self):
        you = [t for t in self.cafe.levels[0].turns if t.who == "you"]
        line = next(t for t in you if t.say == "Já, takk.")
        ids = list(line.items)
        timing = Timing(level="A1")

        def reply_pause(learner):
            sc, ex, dlg = self.play(learner, False)
            k = you.index(line)
            answers = [g for g in sc.segments if g.exercise == ex.index and g.type == "pause" and g.role == "answer"]
            return answers[k].duration
        known = reply_pause(learner_with(self.all_items()))
        first = reply_pause(learner_with([]))
        single = timing.answer_pause("Já, takk.", "is", difficulty=max(self.cur.by_id[i].difficulty for i in ids), successes=3, generative=False)
        self.assertLessEqual(abs(known - single), 1.0, (known, single))
        self.assertLessEqual(known, 3.0)
        self.assertGreater(first, known + 1.0, "a first-time line keeps the longer pause")

    def all_items(self):
        return sorted({i for lv in self.cafe.levels for t in lv.turns if t.who == "you" for i in t.items})

    def test_an_open_item_keeps_the_first_time_pause(self):
        known = learner_with(self.all_items())
        for i in self.all_items():
            known.items[i].last_outcome = "not_recalled"
            known.items[i].extra_think_time = True
        learner = learner_with(self.all_items())
        sc_open, ex_open, _ = self.play(known, False)
        sc_known, ex_known, _ = self.play(learner, False)
        total = lambda sc, ex: sum(g.duration for g in sc.segments if g.exercise == ex.index and g.type == "pause" and g.role == "answer")
        self.assertGreater(total(sc_open, ex_open), total(sc_known, ex_known))

    def test_a_scene_heard_again_has_one_intro(self):
        learner = learner_with(self.all_items())
        sc, ex, dlg = self.play(learner, False, heard_play=True, heard_turns=set())
        texts = [g.text for g in sc.segments if g.exercise == ex.index and g.type == "narrate"]
        self.assertIn(self.en.get("listening_intro_known"), texts)
        self.assertNotIn(self.en.get("dialogue_start"), texts)
        sc2, ex2, _ = self.play(learner_with([]), False, heard_play=True, heard_turns={0, 1, 2, 3, 4, 5})
        texts2 = [g.text for g in sc2.segments if g.exercise == ex2.index and g.type == "narrate"]
        self.assertIn(self.en.get("dialogue_start"), texts2, "the other openings are unchanged")

    def test_the_catch_task_reads_as_one_sentence_and_lowercases_the_word(self):
        self.assertEqual(word_as_asked("Þarftu poka?", "Þarftu"), "þarftu")
        self.assertEqual(word_as_asked("Já. Þarftu poka?", "Þarftu"), "þarftu")
        self.assertEqual(word_as_asked("Þetta er Hekla.", "Hekla"), "Hekla", "a name inside a sentence keeps its capital")
        repair = self.cur.by_id["hvad_thydir_thetta"]
        gloss = {"þarftu": {"en": "do you need", "ja": "必要ですか", "pointer": {"en": "the word used in the question about a bag", "ja": "袋についての質問で使ったことば"}}}
        task = catch_unknown("Þarftu poka?", gloss, {w.lower() for w in tokens("poka")}, "en", repair, repair_known=True, source="s", scene="", line_meaning="Do you need a bag?")
        self.assertEqual(task.repair, "Hvað þýðir þarftu?")
        b = Builder(self.cur, self.en, Timing(level="A1"), learner_with([repair.id]))
        sc = Script(1, "t", "is", "en")
        append_task(b, sc, task, 120)
        cue = next(g.text for g in sc.segments if g.type == "narrate" and "bag" in g.text)
        self.assertEqual(cue, "Ask what the word used in the question about a bag means.")
        self.assertEqual(cue.count("Ask"), 1)


if __name__ == "__main__":
    unittest.main()
