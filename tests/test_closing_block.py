"""#421 (lesson 38: «最後の今回の新出表現をカバーするパートで聞き取り問題が始まって、入れ子構造っぽくてちょっと違和感があった»): from its
announcement to its end, the closing reviews today's new material only. At 28:42 a clothes-shop pick-out came after three recalls of the closing,
put there by the rule that breaks a long run of recalls (#248); that rule stops at the closing's announcement."""
import unittest

import tests.test_audiolesson as course

CLOSING_KINDS = {"closing", "recall", "generative", "connect"}


class ClosingBlockTests(unittest.TestCase):
    def test_nothing_but_todays_material_inside_the_closing(self):
        """The simulated course's closings held a pick-out from lesson 37 on (before #421: lesson 37 the clothes shop's, 40 the town's)."""
        closings = 0
        for _, _, sc in course.ListeningTaskTests._course(38):
            start = next((k for k, e in enumerate(sc.exercises) if e.label == "final review"), None)
            if start is None:
                continue
            closings += 1
            inside = [(e.kind, e.label) for e in sc.exercises[start:] if e.kind not in CLOSING_KINDS]
            self.assertEqual(inside, [], f"lesson {sc.lesson_number}")
        self.assertGreater(closings, 30)


if __name__ == "__main__":
    unittest.main()
