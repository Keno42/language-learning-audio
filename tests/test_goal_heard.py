"""#327 (lesson 42: «Today's goal: Say you can't tomorrow, that you'll come this evening, and see you then.», but «Ég get ekki á morgun.» was heard in
both plays, waiting for «á morgun» to be learned): when the exchange's last play leaves some of the learner's lines heard, the goal is said again from
the turns' authored aims, the lines the learner says first, then the ones only to listen to. Review of #448: a disclaimer after the whole goal still
promised the line; the goal itself is narrowed, and its meaning is what is tested."""
import unittest

import tests.test_audiolesson as course
from audiolesson.content import load_curriculum
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing
from tests.test_audiolesson import ROOT

LISTEN = "Listen for how to "


class GoalHeardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = [(cur, sc) for cur, _, sc in course.ListeningTaskTests._course(30)]
        from audiolesson.themes import load_themes

        cls.themes = {t.id: t for t in load_themes(ROOT / "curricula" / "is-en")}

    @staticmethod
    def goal_line(sc):
        ex = next(e for e in sc.exercises if e.label == "lesson goal")
        return next(g.text for g in sc.segments if g.exercise == ex.index and g.type == "narrate")

    def test_the_goal_names_the_lines_said_and_then_the_lines_only_heard(self):
        narrowed = 0
        for cur, sc in self.lessons:
            theme = sc.meta.get("theme")
            if not theme or not any(e.label == "lesson goal" for e in sc.exercises):
                continue
            line = self.goal_line(sc)
            if not theme["goal_heard"]:
                self.assertNotIn(LISTEN, line, f"lesson {sc.lesson_number}: every line asked, the authored goal as it is")
                continue
            narrowed += 1
            self.assertEqual(Prompts.load("en").get("lesson_goal", goal=theme["goal"]), line, "review of #448: plan.json records the goal said")
            said, _, heard = line.partition(LISTEN)
            self.assertNotIn(self.themes[theme["id"]].levels[theme["level"] - 1].goal, line, f"lesson {sc.lesson_number}: the whole goal is not promised")
            own = f"theme:{theme['id']}:{theme['level']}"
            last = [e for e in sc.exercises if e.kind == "dialogue" and e.label.split(" ")[1] == own][-1]
            narr = [g.text for g in sc.segments if g.exercise == last.index and g.type == "narrate"]
            cues_heard = [narr[k - 1] for k, t in enumerate(narr) if t == Prompts.load("en").get("listening_line")]
            self.assertEqual(len(cues_heard), theme["goal_heard"], f"lesson {sc.lesson_number}: as many lines heard as the goal names")
            self.assertTrue(heard, f"lesson {sc.lesson_number}: the lines to listen to are named")
            self.assertTrue(said.lower().startswith("today's goal: "), line)
        self.assertGreater(narrowed, 0, "the simulated course has a lesson whose exchange leaves a line heard")

    def test_lesson_42s_goal_said_from_the_aims_in_both_languages(self):
        for lang, want in (
            ("en", "Today's goal: Say you'll come this evening and say see you this evening. Listen for how to say you can't tomorrow."),
            ("ja", "今日の目標：今夜行くと言う。じゃあ今夜、と言う。「明日は無理だと伝える」の言い方は、今日は聞くだけです。"),
        ):
            cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
            from audiolesson.themes import load_themes

            meet = next(t for t in load_themes(ROOT / "curricula" / "is-en", cur) if t.id == "meet")
            b = Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
            sc = Script(42, "t", "is", lang)
            ex = b.theme_goal(sc, meet.levels[1])
            b.goal_heard(sc, ex, [t for t in meet.levels[1].turns if t.who == "you"], {0})
            self.assertEqual(self.goal_line(sc), want)

    def test_a_learners_line_without_its_aim_is_refused(self):
        import tempfile
        from pathlib import Path

        from audiolesson.content import CurriculumError
        from audiolesson.themes import load_themes

        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "cando").mkdir()
            (Path(td) / "cando" / "themes.toml").write_text(
                '[[themes]]\nid = "x"\nscenario = "A1"\ntitle = "X"\nscene_line = "You are there."\n[[themes.levels]]\ngoal = "g"\n'
                'turns = [{ who = "you", cue = "Thank him.", say = "Takk.", items = ["takk"] }]\n', encoding="utf-8")
            with self.assertRaises(CurriculumError):
                load_themes(td)


if __name__ == "__main__":
    unittest.main()
