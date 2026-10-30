"""Lesson 34's feedback: after a pick-out (the answer, then the line heard again) the switch to the next question «always feels a little
abrupt». A listening exercise that a drill follows ends with «Back to speaking.», as an aside ends with «Back to the lesson.». Lessons 37 and 39 (#415):
a conversation that a drill follows ends with «That's the end of the conversation.»."""
import unittest

import tests.test_audiolesson as course


class ListeningEndsWithAWayBackTests(unittest.TestCase):
    # these two keep their own copy of which kinds listen or open with their own line: an oracle apart from ``audiolesson/transitions.py``

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

    def test_a_conversation_before_a_drill_ends_with_its_line_and_only_then(self):
        from audiolesson.prompts import Prompts

        line = Prompts.load("en").get("conversation_back")
        closed = kept = 0
        for cur, _, sc in course.ListeningTaskTests._course(20):
            spoken = {s.exercise for s in sc.segments if s.exercise is not None and s.duration > 0}
            order = [e for e in sc.exercises if e.index in spoken]
            for e, nxt in zip(order, order[1:]):
                if e.kind != "dialogue":
                    self.assertNotIn(line, [s.text for s in sc.segments if s.exercise == e.index], e.label)
                    continue
                last = [s.text for s in sc.segments if s.exercise == e.index and s.type in ("speak", "narrate", "answer")][-1:]
                next_listening = nxt.kind in ("pick_out", "catch_unknown") or (nxt.kind == "intro" and nxt.label.startswith("new (catch)"))
                wants = not (next_listening or nxt.kind in ("dialogue", "note", "closing"))
                self.assertEqual(last == [line], wants, (sc.lesson_number, e.label, nxt.kind, nxt.label))
                closed += wants
                kept += not wants
            self.assertEqual(sc.meta["conversations_closed"], sum(1 for s in sc.segments if s.role == "conversation_back"), sc.lesson_number)
        self.assertGreater(closed, 10, "the course has conversations followed by drills")
        self.assertGreater(kept, 0, "and conversations followed by another task that opens with its own line")


class WayBackTableTests(unittest.TestCase):
    """The way between two tasks is one table (``audiolesson/transitions.py``): every kind of exercise has a mode, and a change of mode says
    what the table says."""

    def test_every_kind_the_code_builds_has_a_mode(self):
        """A new kind of exercise gets a mode the day it is written: each literal kind given to ``Script.new_exercise``, and each
        kind of listening task (built with ``new_exercise(task.kind, …)``), is in ``MODES``."""
        import re
        from pathlib import Path

        from audiolesson.transitions import MODES

        src = Path(course.ROOT) / "audiolesson"
        text = {p: p.read_text(encoding="utf-8") for p in src.rglob("*.py")}
        literal = {k for t in text.values() for k in re.findall(r'new_exercise\(\s*"([a-z_]+)"', t)}
        tasks = set(re.findall(r'kind="([a-z_]+)"', text[src / "listening_tasks.py"]))
        dynamic = [p.name for p, t in text.items() for _ in re.findall(r'new_exercise\((?!\s*")', t) if p.name != "script.py"]
        self.assertEqual(dynamic, ["listening_tasks.py"], "the one kind not written out is a listening task's")
        self.assertEqual(sorted((literal | tasks) - set(MODES)), [])
        self.assertGreater(len(literal), 8)
        self.assertEqual(tasks, {"pick_out", "catch_unknown"})

    def test_a_change_of_mode_says_the_table_s_way_back(self):
        from audiolesson.script import Exercise
        from audiolesson.transitions import ways_back

        def order(*kinds):
            return [Exercise(n, kind, None, label=label) for n, (kind, label) in enumerate((k if isinstance(k, tuple) else (k, "")) for k in kinds)]

        self.assertEqual(ways_back(order("pick_out", "recall")), {0: "listening_back"})
        self.assertEqual(ways_back(order(("intro", "new (catch): x"), "recall")), {0: "listening_back"}, "a word introduced through the catch")
        self.assertEqual(ways_back(order("dialogue", "generative")), {0: "conversation_back"})
        self.assertEqual(ways_back(order("catch_unknown", "pick_out", "dialogue", "note", "recall", "closing")), {},
                         "no way back before a task that opens with its own line, and none after a drill or an aside")
        self.assertEqual(ways_back(order("pick_out")), {}, "the last exercise hands over to nothing")
        with self.assertRaises(KeyError):
            ways_back(order("pick_out", "a_kind_not_in_the_table"))


if __name__ == "__main__":
    unittest.main()
