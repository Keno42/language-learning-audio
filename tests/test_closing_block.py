"""#421 (lesson 38: «最後の今回の新出表現をカバーするパートで聞き取り問題が始まって、入れ子構造っぽくてちょっと違和感があった»): from its
announcement to its end, the closing reviews today's new material only. At 28:42 a clothes-shop pick-out came after three recalls of the closing,
put there by the rule that breaks a long run of recalls (#248); that rule stops at the closing's announcement, and the listening it gave comes in
the last stretch before the closing instead (#421's acceptance: the listening tasks kept)."""
import unittest

import tests.test_audiolesson as course

CLOSING_KINDS = {"closing", "recall", "generative", "connect"}
LISTENING = {"pick_out", "catch_unknown"}


class ClosingBlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = [sc for _, _, sc in course.ListeningTaskTests._course(38)]

    @staticmethod
    def closing_start(sc):
        return next((k for k, e in enumerate(sc.exercises) if e.label == "final review"), None)

    def test_nothing_but_todays_material_inside_the_closing(self):
        """The simulated course's closings held a pick-out from lesson 37 on (before #421: lesson 37 the clothes shop's, 40 the town's)."""
        closings = 0
        for sc in self.lessons:
            start = self.closing_start(sc)
            if start is None:
                continue
            closings += 1
            inside = [(e.kind, e.label) for e in sc.exercises[start:] if e.kind not in CLOSING_KINDS]
            self.assertEqual(inside, [], f"lesson {sc.lesson_number}")
        self.assertGreater(closings, 30)

    def test_the_listening_the_closing_held_comes_before_it(self):
        """Review of #435: with nothing inside the closing, the replay of the lesson-40 export lost 16 of its 51 listening tasks in lessons 40-46,
        their time going to drills. They come in the last stretch before the closing: in this course, listening tasks among the six exercises
        before it rise from 9 to 21, and over the course from 79 to 89."""
        before = sum(e.kind in LISTENING for sc in self.lessons if (s := self.closing_start(sc)) is not None for e in sc.exercises[max(0, s - 6) : s])
        self.assertGreaterEqual(before, 15)
        self.assertGreaterEqual(sum(e.kind in LISTENING for sc in self.lessons for e in sc.exercises), 85)


if __name__ == "__main__":
    unittest.main()
