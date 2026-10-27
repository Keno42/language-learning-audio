"""#416 (lesson 38: «"nei, takk." や "takk." を何度も言う… 言わされすぎ»): in an exchange played again (a scene heard again, the lesson's own
exchange's late play) a set reply the learner plainly knows is said in the model voice, not asked. A limited exception to "sayable → asked"
(#263): two words at most, every item learned and not weak, not taught today, and a reply due for review keeps one ask."""
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from audiolesson.cando import load_cando
from audiolesson.content import load_curriculum
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 3, 1)


class SetReplyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cur = load_curriculum(ROOT / "curricula" / "is-en")
        scenarios = load_cando(ROOT / "curricula" / "is-en", cls.cur)
        cls.themes = load_themes(ROOT / "curricula" / "is-en", cls.cur, scenarios)
        cls.order = scenario_order(scenarios)

    def learner(self):
        """Every item learned and not due; every theme level played."""
        learner = LearnerState("is", "en", "A1")
        for i in self.cur.by_id:
            learner.items[i] = ItemState(due=(TODAY + timedelta(days=20)).isoformat(), successes=6, durable_successes=3, stage="dialogue", recalled=2,
                                         last_outcome="recalled", interval_days=20, last_practiced=(TODAY - timedelta(days=3)).isoformat())
        for t in self.themes:
            learner.themes_done[t.id] = len(t.levels)
            learner.themes_last[t.id] = 1
        return learner

    def planner(self, learner=None, **cfg):
        return Planner(self.cur, learner or self.learner(), Prompts.load("en"), Timing(level="A1"),
                       PlanConfig(minutes=30, themes=self.themes, theme_scenarios=self.order, **cfg), today=TODAY)

    def test_the_conditions(self):
        p = self.planner()
        self.assertTrue(p.known_set_reply(["takk"], "Takk."))
        self.assertTrue(p.known_set_reply(["nei", "takk"], "Nei, takk."))
        self.assertFalse(p.known_set_reply(["gjordu_svo_vel"], "Gjörðu svo vel."), "three words: asked")
        self.assertFalse(self.planner(set_reply_words=0).known_set_reply(["takk"], "Takk."), "0 asks every line")
        for change in ({"last_outcome": "hesitated"}, {"durable_successes": 1}, {"due": TODAY.isoformat()}):
            learner = self.learner()
            learner.items["takk"] = replace(learner.items["takk"], **change)
            self.assertFalse(self.planner(learner).known_set_reply(["takk"], "Takk."), change)
        p.builder.in_lesson.add("takk")
        self.assertFalse(p.known_set_reply(["takk"], "Takk."), "taught today: asked")

    def test_a_due_reply_keeps_one_ask(self):
        learner = self.learner()
        learner.items["takk"] = replace(learner.items["takk"], due=TODAY.isoformat())
        p = self.planner(learner)
        self.assertFalse(p.known_set_reply(["takk"], "Takk."))
        p.exposures["takk"] = ["dialogue"]  # asked once in this lesson: its review is done
        self.assertTrue(p.known_set_reply(["takk"], "Takk."))

    def test_a_play_of_voiced_replies_only_keeps_them_asked(self):
        p = self.planner()
        you = [t for t in self.themes[0].levels[0].turns if t.who == "you"]
        replies = [t for t in you if len(t.say.split()) <= 2 and p.known_set_reply(t.items, t.say)]
        self.assertTrue(replies)
        self.assertEqual(p.voiced_replies(replies, set()), set(), "nothing would be asked")
        self.assertEqual(p.voiced_replies(replies, {99}), set(range(len(replies))), "a line heard: the play announces it")

    def voiced_segments(self, sc):
        """For each learner line of a theme play, (label, text, asked): asked when an answer pause comes before it."""
        out = []
        for k, s in enumerate(sc.segments):
            if s.type != "answer" or s.exercise is None:
                continue
            ex = sc.exercises[s.exercise]
            if "theme:" not in ex.label:
                continue
            prev = sc.segments[k - 1]
            out.append((ex.label, s.text, prev.type == "pause" and prev.role == "answer"))
        return out

    def test_a_lesson_voices_known_replies_in_plays_again_only(self):
        sc = self.planner().build()
        voiced = sc.meta["voiced_replies"]
        self.assertTrue(voiced, "an all-known learner hears set replies again")
        lines = self.voiced_segments(sc)
        said = [(label, text) for label, text, asked in lines if not asked and text in {"Takk.", "Já, takk.", "Nei, takk.", "Takk kærlega."}]
        self.assertTrue(said)
        first = next((e.label for e in sc.exercises if e.label.startswith("dialogue: theme:")), None)
        for label, text in said:
            self.assertTrue(label.startswith("heard: ") or label != first or [e.label for e in sc.exercises].count(label) > 1, (label, text))
        for k, s in enumerate(sc.segments):
            if s.type == "answer" and s.text == said[0][1] and sc.exercises[s.exercise].label == said[0][0]:
                self.assertNotEqual(sc.segments[k - 1].text, "Here you would say:")
                break
        # the same lesson without the exception asks every one of them
        plain = self.planner(set_reply_words=0).build()
        self.assertEqual(plain.meta["voiced_replies"], [])
        self.assertTrue(all(asked for _, text, asked in self.voiced_segments(plain) if text in {"Takk.", "Já, takk.", "Nei, takk."}))


if __name__ == "__main__":
    unittest.main()
