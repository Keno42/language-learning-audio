"""#303: a pick-out names what to listen for before the line."""
import unittest
from pathlib import Path

from audiolesson.content import load_curriculum
from audiolesson.listening_tasks import ListeningTask, _build
from audiolesson.exercises import Builder
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.script import Script
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("price", "time", "count", "place", "duration")


def build(lang, task):
    cur = load_curriculum(ROOT / "curricula" / "is-en", known_lang=lang)
    b = Builder(cur, Prompts.load(lang), Timing(level="A1"), LearnerState("is", lang, "A1"))
    sc = Script(1, "t", "is", lang)
    _build(b, sc, task)
    return sc


class PickOutNeedTests(unittest.TestCase):
    def test_the_need_comes_after_the_scene_and_before_the_line_in_both_languages(self):
        for lang in ("en", "ja"):
            for kind in KINDS:
                task = ListeningTask("pick_out", "x", "At a museum.", "Safnið lokar klukkan fimm.", "klukkan fimm", "five", f"pick_out_{kind}")
                spoken = [g.text for g in build(lang, task).segments if g.type in ("narrate", "speak")]
                line = spoken.index("Safnið lokar klukkan fimm.")
                self.assertEqual(spoken[0], "At a museum.")
                self.assertGreater(line, 1, f"{lang}/{kind}: the need stands before the line")
                self.assertIn(Prompts.load(lang).get(f"pick_out_need_{kind}"), spoken[:line])

    def test_a_line_with_several_pieces_names_the_one_asked_for(self):
        task = ListeningTask("pick_out", "x", "", "Safnið opnar klukkan tíu og lokar klukkan fimm.", "klukkan fimm", "five", "pick_out_time", ask="When does it close?", pieces=2)
        spoken = [g.text for g in build("en", task).segments if g.type in ("narrate", "speak")]
        self.assertEqual(spoken[0], "You want to know: When does it close? Listen and answer.")
        self.assertEqual(spoken[1], task.line)

    def test_the_question_is_not_asked_after_the_line(self):
        task = ListeningTask("pick_out", "x", "", "Það kostar fimm.", "fimm", "five", "pick_out_price")
        spoken = [g.text for g in build("en", task).segments if g.type in ("narrate", "speak")]
        self.assertNotIn("How much is it?", spoken)

    def test_the_flow_marks_the_answer_and_the_replay_in_both_languages(self):
        """#335: need and «answer» → line → pause → «The answer:» → answer → meaning → «Listen again.» → line."""
        for lang in ("en", "ja"):
            p = Prompts.load(lang)
            task = ListeningTask("pick_out", "x", "", "Safnið lokar klukkan fimm.", "klukkan fimm", "Five o'clock.", "pick_out_time")
            segs = [g for g in build(lang, task).segments if g.type in ("narrate", "speak", "answer", "pause")]
            texts = [g.text for g in segs if g.type != "pause"]
            self.assertEqual(
                texts[:7],
                [p.get("pick_out_need_time"), task.line, p.get("pick_out_answer"), "klukkan fimm", task.meaning, p.get("pick_out_again"), task.line],
                lang,
            )
            roles = [(g.type, g.role) for g in segs]
            at = next(k for k, g in enumerate(segs) if g.type == "pause" and g.role == "answer")
            self.assertEqual(
                roles[at : at + 4],
                [("pause", "answer"), ("narrate", "frame"), ("pause", "beat"), ("answer", None)],
                f"{lang}: the learner's turn, «The answer:» as a framing line with its beat, then the answer",
            )
            again = next(k for k, g in enumerate(segs) if g.text == p.get("pick_out_again"))
            self.assertEqual((segs[again].role, segs[again + 1].type, segs[again + 1].role), ("frame", "pause", "beat"), "«Listen again.» is a framing line too")
            self.assertEqual(segs[again + 2].text, task.line)

    def test_the_answer_is_in_the_other_voice_after_a_recall_pause(self):
        """Lesson 28: the model answer was said by the speaker of the line (as if the partner said it again), after the generative pause (4.2-4.5 s for
        «klukkan fimm»). It is the learner's answer: the other voice, after a recall's pause; the catch's question keeps its longer pause."""
        t = Timing(level="A1")
        for speaker, other in (("native_a", "native_b"), ("native_b", "native_a")):
            task = ListeningTask("pick_out", "x", "", "Safnið lokar klukkan fimm.", "klukkan fimm", "Five o'clock.", "pick_out_time", speaker=speaker)
            segs = build("en", task).segments
            answer = next(g for g in segs if g.type == "answer")
            self.assertEqual(answer.speaker, other, "not the voice of the line")
            pause = next(g for g in segs if g.type == "pause" and g.role == "answer")
            self.assertEqual(pause.duration, t.answer_pause("klukkan fimm", "is"))
            self.assertLess(pause.duration, t.answer_pause("klukkan fimm", "is", generative=True))
        catch = ListeningTask("catch_unknown", "x", "", "Viltu sestu?", "sestu", "sit", "catch_unknown_context", repair="Hvað þýðir sestu?", cue="Do you want to something?")
        pause = next(g for g in build("en", catch).segments if g.type == "pause" and g.role == "answer")
        self.assertEqual(pause.duration, t.answer_pause("Hvað þýðir sestu?", "is", generative=True), "the question is made: its pause stays")

    def test_the_catch_task_is_unchanged(self):
        task = ListeningTask("catch_unknown", "x", "", "Viltu sestu?", "sestu", "sit", "catch_unknown_context", repair="Hvað þýðir sestu?", cue="Do you want to something?")
        texts = [g.text for g in build("en", task).segments if g.type in ("narrate", "speak", "answer")]
        self.assertNotIn(Prompts.load("en").get("pick_out_answer"), texts)
        self.assertNotIn(Prompts.load("en").get("pick_out_again"), texts)


if __name__ == "__main__":
    unittest.main()
