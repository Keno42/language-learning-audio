"""#339 (lesson 40): the tour's first level, heard again, said «Hér stoppum við í tuttugu mínútur.», and 35 s later a pick-out asked «How long do
we stop?» with the answer «tuttugu mínútur»: remembered, not found. A pick-out's answer is not said aloud in the five minutes before it."""
import re
import unittest

import tests.test_audiolesson as course

WORDS = re.compile(r"[^\W\d_]+")


def words(text):
    return [w.lower() for w in WORDS.findall(text or "")]


class PickOutHeardTests(unittest.TestCase):
    def test_no_pick_out_answer_was_said_in_the_five_minutes_before(self):
        picks = 0
        for _, _, sc in course.ListeningTaskTests._course(30):
            clock, spoken = 0.0, []  # (start, words, exercise) of every line said
            starts = {}
            for seg in sc.segments:
                starts.setdefault(seg.exercise, clock)
                if seg.type in ("speak", "answer") and seg.text:
                    spoken.append((clock, words(seg.text), seg.exercise))
                clock += seg.duration
            for e in sc.exercises:
                if e.kind != "pick_out":
                    continue
                picks += 1
                answer = next(s.text for s in reversed(sc.segments) if s.exercise == e.index and s.type == "answer")
                a = words(answer)
                at = starts[e.index]
                before = [w for t, w, x in spoken if x != e.index and at - 300 <= t < at and any(w[k : k + len(a)] == a for k in range(len(w)))]
                self.assertEqual(before, [], f"lesson {sc.lesson_number}: {e.label} «{answer}»")
        self.assertGreater(picks, 5)


if __name__ == "__main__":
    unittest.main()
