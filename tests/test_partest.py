"""``tools/partest.py`` runs what ``python -m unittest`` runs, spread over worker processes: every test once, a class with a class
fixture whole in one worker, the parts of ``--shard`` together the whole suite, and a failing test failing the run."""
import contextlib
import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent

# A small suite of its own, written to a temporary directory: the workers are fresh processes and import it by name.
SAMPLE = '''
import os
import time
import unittest


class Plain(unittest.TestCase):
    def test_a(self):
        pass

    def test_b(self):
        time.sleep(0.2)

    def test_c(self):
        print("said before failing")
        if os.environ.get("PARTEST_SAMPLE_FAILS"):
            self.fail("c is wrong")

    @unittest.skip("not today")
    def test_d(self):
        pass


class Built(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.environ["PARTEST_SAMPLE_LOG"], "a") as f:
            f.write(f"{os.getpid()}\\n")

    def test_e(self):
        pass

    def test_f(self):
        pass

    def test_g(self):
        pass
'''
TESTS = {f"partest_sample.Plain.test_{x}" for x in "abcd"} | {f"partest_sample.Built.test_{x}" for x in "efg"}


class ParallelRunnerTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)
        (self.dir / "partest_sample.py").write_text(SAMPLE, encoding="utf-8")
        self.log = self.dir / "built.log"
        env = mock.patch.dict(os.environ, {"PARTEST_SAMPLE_LOG": str(self.log)})
        env.start()
        self.addCleanup(env.stop)
        # a worker starts with this process's sys.path: it finds the sample and the tool by name there, as this process does
        for d in (str(self.dir), str(ROOT / "tools")):
            sys.path.insert(0, d)
            self.addCleanup(sys.path.remove, d)
        for name in ("partest_sample", "partest"):
            self.addCleanup(sys.modules.pop, name, None)
        self.tool = importlib.import_module("partest")
        times = mock.patch.object(self.tool, "TIMES", self.dir / "times.json")  # not the repository's own record
        times.start()
        self.addCleanup(times.stop)

    def run_tool(self, *args) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.tool.main(["partest_sample", *args])
        return code, out.getvalue()

    def ran(self, text: str) -> list[str]:
        """The tests a ``-v`` run names, one line each as they finish."""
        return [line.split()[-1] for line in text.splitlines() if line.split()[:1] in (["ok"], ["skip"], ["FAIL"])]

    def test_every_test_runs_once_and_a_class_fixture_is_built_once(self):
        code, text = self.run_tool("-j", "3", "-v")
        self.assertEqual(code, 0, text)
        self.assertCountEqual(self.ran(text), TESTS)
        self.assertIn("Ran 7 tests", text)
        self.assertIn("OK (skipped=1)", text)
        self.assertEqual(len(self.log.read_text().split()), 1, "setUpClass ran once: the class went to one worker whole")

    def test_the_parts_of_a_shard_are_the_whole_suite_once(self):
        seen = []
        for k in (1, 2, 3):
            code, text = self.run_tool("-j", "2", "-v", "--shard", f"{k}/3")
            self.assertEqual(code, 0, text)
            seen += self.ran(text)
        self.assertCountEqual(seen, TESTS)

    def test_the_slowest_test_of_the_last_run_starts_first(self):
        """A long test started last keeps one worker busy after the others are done. The first run has no times: the order of the names."""
        first = self.ran(self.run_tool("-j", "1", "-v")[1])
        self.assertEqual(first, sorted(TESTS))
        again = self.ran(self.run_tool("-j", "1", "-v")[1])
        self.assertEqual(again[0], "partest_sample.Plain.test_b", "the one that sleeps")
        self.assertCountEqual(again, TESTS)
        (self.dir / "times.json").write_text("{cut short", encoding="utf-8")
        self.assertEqual(self.ran(self.run_tool("-j", "1", "-v")[1]), sorted(TESTS), "an unreadable record is no record")

    def test_a_failing_test_fails_the_run_and_shows_what_it_printed(self):
        with mock.patch.dict(os.environ, {"PARTEST_SAMPLE_FAILS": "1"}):
            code, text = self.run_tool("-j", "2")
        self.assertEqual(code, 1, text)
        self.assertIn("FAIL: partest_sample.Plain.test_c", text)
        self.assertIn("c is wrong", text)
        self.assertIn("said before failing", text)
        self.assertIn("FAILED (failures=1, skipped=1)", text)
        self.assertNotIn("said before failing", self.run_tool("-j", "2")[1], "a passing test's output is not shown")

    def test_a_name_that_matches_nothing_is_not_a_passing_run(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as stop:
            self.tool.main(["partest_sample.Missing"])
        self.assertEqual(stop.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
