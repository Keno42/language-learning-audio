"""Lesson 34's feedback: after a pick-out (the answer, then the line heard again) the switch to the next question «always feels a little
abrupt». A listening exercise that a drill follows ends with «Back to speaking.», as an aside ends with «Back to the lesson.»."""
import unittest

import tests.test_audiolesson as course


class ListeningEndsWithAWayBackTests(unittest.TestCase):
    def test_a_listening_exercise_before_a_drill_ends_with_back_to_speaking_and_only_then(self):
        closed = 0
        for cur, _, sc in course.ListeningTaskTests._course(20):  # pick-outs and catches start around lesson 15
            spoken = {s.exercise for s in sc.segments if s.exercise is not None and s.duration > 0}
            order = [e for e in sc.exercises if e.index in spoken]
            for e, nxt in zip(order, order[1:]):
                listening = e.kind in ("pick_out", "catch_unknown") or (e.kind == "intro" and e.label.startswith("new (catch)"))
                last = [s.text for s in sc.segments if s.exercise == e.index and s.type in ("speak", "narrate", "answer")][-1:]
                next_listening = nxt.kind in ("pick_out", "catch_unknown") or (nxt.kind == "intro" and nxt.label.startswith("new (catch)"))
                wants = listening and not (next_listening or nxt.kind in ("dialogue", "note", "closing"))
                self.assertEqual(last == ["Back to speaking."], wants, (sc.lesson_number, e.label, nxt.kind))
                closed += wants
            self.assertEqual(sc.meta["listening_closed"], sum(1 for s in sc.segments if s.role == "listening_back"), sc.lesson_number)
        self.assertGreater(closed, 5, "the course has pick-outs and catches followed by drills")


if __name__ == "__main__":
    unittest.main()
