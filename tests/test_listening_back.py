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


    def test_a_conversation_right_after_another_says_another(self):
        """Lesson 45 (owner): a conversation that ends where another begins says no «That's the end of the conversation.», so the next one opens
        «Now another short conversation.»; one after anything else opens «Now a short conversation.»."""
        from audiolesson.prompts import Prompts

        prompts = Prompts.load("en")
        start, another = prompts.get("dialogue_start"), prompts.get("dialogue_start_another")
        pairs = 0
        for cur, _, sc in course.ListeningTaskTests._course(20):
            spoken = {s.exercise for s in sc.segments if s.exercise is not None and s.duration > 0}
            order = [e for e in sc.exercises if e.index in spoken]
            for prev, e in zip(order, order[1:]):
                said = [s.text for s in sc.segments if s.exercise == e.index and s.type == "narrate"]
                if e.kind != "dialogue" or not ({start, another} & set(said)):
                    self.assertNotIn(another, said, (sc.lesson_number, e.label))
                    continue
                after_one = prev.kind == "dialogue"
                self.assertIn(another if after_one else start, said, (sc.lesson_number, prev.label, e.label))
                self.assertNotIn(start if after_one else another, said, (sc.lesson_number, prev.label, e.label))
                pairs += after_one
        self.assertGreater(pairs, 0, "the course has a conversation right after another")


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

    def test_a_listening_task_with_nothing_to_frame_it_opens_with_listen(self):
        """#427, #433 (lesson 40: «every listening task opens with its scene line»): a catch with no scene, such as one that introduces a word
        through its home sentence, started with its target-language line straight after the task before. ``close_tasks`` opens it with
        «Listen.», on the finished script; a pick-out, which opens with its need, and the lesson's first exercise get nothing."""
        from audiolesson.prompts import Prompts
        from audiolesson.script import Script, Segment
        from audiolesson.timing import Timing
        from audiolesson.transitions import close_tasks

        sc = Script(1, "t", "is", "en")
        for kind, lines in (("catch_unknown", [("speak", "native_b", "Hvar er bankinn?"), ("narrate", "instructor", "Ask what it means.")]),
                            ("recall", [("narrate", "instructor", "Say: thanks."), ("answer", "native_a", "Takk.")]),
                            ("catch_unknown", [("speak", "native_b", "Mig langar í súpu."), ("narrate", "instructor", "Ask what it means.")]),
                            ("pick_out", [("narrate", "instructor", "Listen for the price, then say it."), ("speak", "native_b", "Það kostar þúsund.")])):
            ex = sc.new_exercise(kind, None, [], kind)
            for typ, who, text in lines:
                sc.add(Segment(typ, who, text, "en" if who == "instructor" else "is", 1.0, 1.0, None, ex.index))
        close_tasks(sc, Prompts.load("en"), Timing(level="A1"), "en")
        heard = [(s.exercise, s.text) for s in sc.segments if s.type != "pause"]
        self.assertEqual(heard[0], (0, "Hvar er bankinn?"), "the lesson's first exercise")
        self.assertEqual([t for i, t in heard if i == 2][:2], ["Listen.", "Mig langar í súpu."])
        self.assertEqual(sum(t == "Listen." for _, t in heard), 1, "not before a pick-out, which opens with its need")

    def test_no_turn_between_tasks_goes_unmarked_over_the_course(self):
        """``transitions.unmarked_turns`` reads 0 on every lesson of the course: each way back where the table wants it, each aside ending with
        its end line, and each task that opens with its own line opening with the instructor's."""
        from audiolesson.prompts import Prompts
        from audiolesson.transitions import unmarked_turns

        prompts = Prompts.load("en")
        for cur, _, sc in course.ListeningTaskTests._course(20):
            self.assertEqual(unmarked_turns(sc, prompts), [], sc.lesson_number)

    def test_each_kind_of_unmarked_turn_is_found(self):
        from audiolesson.prompts import Prompts
        from audiolesson.script import Script, Segment
        from audiolesson.transitions import unmarked_turns

        prompts = Prompts.load("en")

        def found(*exercises):
            sc = Script(1, "t", "is", "en")
            for kind, label, lines in exercises:
                ex = sc.new_exercise(kind, None, [], label)
                for typ, who, text, role in lines:
                    sc.add(Segment(typ, who, text, "is" if who != "instructor" else "en", 1.0, 1.0, role, ex.index))
            return unmarked_turns(sc, prompts)

        listen = ("narrate", "instructor", "Listen.", None)
        line = ("speak", "native_a", "Hvað kostar kaffi?", "listening_line")
        back = ("narrate", "instructor", "Back to speaking.", "listening_back")
        drill = ("recall", "recall: x", [("narrate", "instructor", "Say: thanks.", None), ("answer", "native_a", "Takk.", None)])
        aside_end = ("narrate", "instructor", "Back to the lesson.", None)
        self.assertEqual(found(drill, ("pick_out", "p", [listen, line, back]), drill), [])
        self.assertEqual(found(drill, ("pick_out", "p", [listen, line]), drill), ["p: no way back before recall"])
        self.assertEqual(found(drill, ("pick_out", "p", [listen, back, line]), drill), ["p: no way back before recall"], "said, but not last")
        self.assertEqual(found(drill, ("pick_out", "p", [listen, line, back]), ("note", "n", [listen, aside_end])),
                         ["p: a way back where the next task opens with its own line, or none follows"])
        self.assertEqual(found(drill, ("note", "n", [listen]), drill), ["n: no end line"])
        self.assertEqual(found(drill, ("catch_unknown", "c", [line, back]), drill), ["c: opens with «Hvað kostar kaffi?» straight after recall"])


if __name__ == "__main__":
    unittest.main()
