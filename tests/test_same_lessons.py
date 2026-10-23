"""#281: ``tools/same_lessons.py``, the public "behaviour unchanged" check, finds two trees that build the same lessons identical and
says what is heard differently when they do not."""
import contextlib
import importlib.util
import io
import shutil
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


def load_tool():
    spec = importlib.util.spec_from_file_location("same_lessons", ROOT / "tools" / "same_lessons.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    return tool


class SameLessonsTests(unittest.TestCase):
    def run_against(self, edit=None, configs=None) -> tuple[int, str]:
        """The tool on one lesson per config, the revision's tree being a copy of the working tree (``edit`` changes the copy)."""
        tool = load_tool()
        if configs is not None:
            tool.CONFIGS = tool.CONFIGS[:configs]

        def checkout(_rev, dest):
            for part in ("audiolesson", "curricula"):
                shutil.copytree(ROOT / part, dest / part, ignore=shutil.ignore_patterns("__pycache__"))
            if edit:
                edit(dest)

        out = io.StringIO()
        with mock.patch.object(tool, "checkout", checkout), contextlib.redirect_stdout(out):
            code = tool.main(["REV", "--lessons", "1"])
        return code, out.getvalue()

    def test_the_same_code_builds_the_same_lessons(self):
        code, text = self.run_against()
        self.assertEqual(code, 0, text)
        self.assertEqual(text.count("1 lessons, identical"), 3, text)

    def test_a_change_of_what_is_heard_is_reported_with_its_lines(self):
        def edit(dest):
            phrasing = dest / "audiolesson" / "phrasing" / "en.toml"
            phrasing.write_text(phrasing.read_text(encoding="utf-8").replace('repeat = "Repeat."', 'repeat = "Repeat it."'), encoding="utf-8")

        code, text = self.run_against(edit, configs=1)
        self.assertEqual(code, 1, text)
        self.assertIn("lesson-001 (script, plan)", text)
        self.assertIn("-narrate instructor: Repeat it.", text)
        self.assertIn("+narrate instructor: Repeat.", text)


if __name__ == "__main__":
    unittest.main()
