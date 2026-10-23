"""tools/top_lines.py (G10, #209): the native check starts from the lines the lessons say most, counted from the lesson scripts, the learner's answers
as said and any other Icelandic as heard, a piece of a line not counted."""
import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

from audiolesson.script import Script, Segment

ROOT = Path(__file__).resolve().parent.parent


def tool():
    spec = importlib.util.spec_from_file_location("top_lines", ROOT / "tools" / "top_lines.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TopLinesTests(unittest.TestCase):
    def test_the_table_ranks_the_lines_by_how_often_they_are_said(self):
        one = Script(1, "t", "is", "en", segments=[
            Segment("narrate", "instructor", "Say: thanks.", "en"),
            Segment("speak", "native_a", "Takk.", "is"),
            Segment("answer", "native_a", "Takk", "is"),
            Segment("speak", "native_a", "Ég", "is", role="hint"),  # a piece of a line
            Segment("answer", "native_a", "Ég er þreytt.", "is"),
            Segment("speak", "native_a", "Bonjour.", "fr"),  # a note's third language
        ])
        two = Script(2, "t", "is", "en", segments=[Segment("answer", "native_b", "takk.", "is"), Segment("speak", "native_b", "Góðan daginn!", "is")])
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as td:
            paths = []
            for sc in (one, two):
                paths.append(str(Path(td) / f"lesson-{sc.lesson_number:03d}.script.json"))
                sc.save(paths[-1])
            with contextlib.redirect_stdout(out):
                self.assertEqual(tool().main([*paths, "--top", "2"]), 0)
        text = out.getvalue()
        self.assertTrue(text.startswith("# The most-said lines: candidates awaiting native review"))
        self.assertIn("| # | line | said | heard | ok / unnatural / wrong | what a native would say |", text)
        rows = [line for line in text.splitlines() if line.startswith("| ") and line[2].isdigit()]
        self.assertEqual(rows, ["| 1 | Takk. | 2 | 1 | | |", "| 2 | Ég er þreytt. | 1 | 0 | | |"], "a tie goes to the line the learner says")
        self.assertIn("the 2 most frequent of 3 lines", text, "the hint's «Ég» and the French line are not lines of the course")


if __name__ == "__main__":
    unittest.main()
