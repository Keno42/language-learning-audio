"""#327 (lesson 42: «Today's goal: Say you can't tomorrow, that you'll come this evening, and see you then.», but «Ég get ekki á morgun.» was heard in
both plays, waiting for «á morgun» to be learned): when the exchange's last play leaves some of the learner's lines heard, the goal's line says so."""
import unittest

import tests.test_audiolesson as course
from audiolesson.prompts import Prompts

ONE = Prompts.load("en").get("lesson_goal_heard_one")
SOME = Prompts.load("en").get("lesson_goal_heard_some")


class GoalHeardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = [sc for _, _, sc in course.ListeningTaskTests._course(30)]

    def goal_line(self, sc):
        ex = next(e for e in sc.exercises if e.label == "lesson goal")
        return next(g.text for g in sc.segments if g.exercise == ex.index and g.type == "narrate")

    def test_the_goal_says_how_many_lines_the_last_play_only_lets_the_learner_hear(self):
        qualified = 0
        for sc in self.lessons:
            theme = sc.meta.get("theme")
            if not theme or not any(e.label == "lesson goal" for e in sc.exercises):
                continue
            line = self.goal_line(sc)
            count = theme["goal_heard"]
            self.assertEqual(ONE in line, count == 1, f"lesson {sc.lesson_number}")
            self.assertEqual(SOME in line, count > 1, f"lesson {sc.lesson_number}")
            if count:
                qualified += 1
                own = f"theme:{theme['id']}:{theme['level']}"
                plays = [e for e in sc.exercises if e.kind == "dialogue" and e.label.split(" ")[1] == own]
                last = plays[-1].index
                said = [g.text for g in sc.segments if g.exercise == last and g.type == "narrate"]
                self.assertEqual(said.count(Prompts.load("en").get("listening_line")), count, f"lesson {sc.lesson_number}: the last play hears as many lines")
        self.assertGreater(qualified, 0, "the simulated course has a lesson whose exchange leaves a line heard")


if __name__ == "__main__":
    unittest.main()
