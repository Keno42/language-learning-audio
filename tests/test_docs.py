"""The documents' mechanical consistency (LEARNING-DESIGN §10 "Documents: replace, don't append").

What a reader can't check by eye across 1000 lines: "Now" lives in one place (the status brief, #364) and stays within its
limit, as §5 does, a reference such as "§5.14" or §9 "Repetition" names something that exists, the files `CLAUDE.md`'s
reading table names are there, and the feedback ledger (`docs/feedback/ledger.toml`, §8) names only lessons and families it
holds."""

import importlib.util
import re
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
LD = DOCS / "LEARNING-DESIGN.md"
STATUS = DOCS / "CURRENT-STATUS.md"
EVIDENCE = DOCS / "history" / "evidence.md"
LEDGER = DOCS / "feedback" / "ledger.toml"


def now_block(text: str) -> str:
    """The status brief's "## Now (updated …)" section, up to the next "## " heading."""
    m = re.search(r"^## Now \(updated .*?(?=^## )", text, re.M | re.S)
    if m is None:
        raise AssertionError('no "## Now (updated …)" section followed by another "## " section')
    return m.group(0)


def sections(text: str) -> dict[str, str]:
    """Top-level sections of LEARNING-DESIGN by number: "9" → the text of "## 9. …" up to the next "## "."""
    parts = re.split(r"^## (\d+)\. ", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def referring_files() -> list[Path]:
    return [*DOCS.glob("*.md"), ROOT / "README.md", ROOT / "CLAUDE.md"]


class DocsTests(unittest.TestCase):
    def setUp(self):
        self.ld = LD.read_text(encoding="utf-8")

    def test_now_holds_four_items_at_most(self):
        items = re.findall(r"^\d+\. ", now_block(STATUS.read_text(encoding="utf-8")), re.M)
        self.assertLessEqual(len(items), 4, '§1: "Now" holds three or four items at most')

    def test_the_roadmap_points_to_the_status_brief_for_now(self):
        """#364: "Now" has one home. §8 names it and holds no list of its own, so there is no copy to drift."""
        self.assertIn("CURRENT-STATUS.md", sections(self.ld)["8"])
        for path in referring_files():
            if path != STATUS:
                self.assertIsNone(re.search(r"(?m)^(\*\*|## )Now \(updated", path.read_text(encoding="utf-8")), f'{path.name} holds a copy of "Now"')

    def test_the_files_the_reading_table_names_exist(self):
        """#364: `CLAUDE.md`'s "Read for the task" names the sources for each kind of task; a renamed file would leave it pointing nowhere."""
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("## Read for the task", text)
        paths = re.findall(r"`((?:docs|audiolesson|tools|tests|curricula)/[^`]+)`", text)
        self.assertTrue(paths)
        for rel in paths:
            self.assertTrue((ROOT / rel).exists(), f"CLAUDE.md names {rel}, which does not exist")

    def test_section_5_keeps_the_last_three_lessons(self):
        lessons = re.findall(r"^### 5\.\d+ Lesson", sections(self.ld)["5"], re.M)
        self.assertLessEqual(len(lessons), 3, "move the oldest subsection to docs/history/evidence.md")

    def test_every_numbered_evidence_reference_resolves(self):
        headings = set(re.findall(r"^### (5\.\d+) ", self.ld + EVIDENCE.read_text(encoding="utf-8"), re.M))
        for path in referring_files():
            for ref in set(re.findall(r"§(5\.\d+)", path.read_text(encoding="utf-8"))):
                self.assertIn(ref, headings, f"{path.name}: §{ref} names no subsection")

    def test_every_named_section_reference_resolves(self):
        """§9 "Repetition" must name a label §9 holds: a bold label (``**Repetition``) or a heading that starts with the name.
        Matching anywhere in the text would let a reference inside its own section match itself."""
        secs = sections(self.ld)
        for path in referring_files():
            for num, name in set(re.findall(r'§(\d+) [«"]([^"»]+)["»]', path.read_text(encoding="utf-8"))):
                if num not in secs:
                    continue
                name = " ".join(name.lower().split())
                bold = re.findall(r"\*\*(.+?)\*\*", secs[num], re.S)
                headings = re.findall(r"^#{2,4} (?:\d+(?:\.\d+)*\.? )?(.+)$", secs[num], re.M)
                labels = [" ".join(lab.lower().split()) for lab in bold + headings]
                self.assertTrue(any(lab.startswith(name) for lab in labels), f'{path.name}: §{num} "{name}" names no label in §{num}')


def ledger_tool():
    if "ledger_tool" not in sys.modules:  # a dataclass needs its module registered
        spec = importlib.util.spec_from_file_location("ledger_tool", ROOT / "tools" / "ledger.py")
        sys.modules["ledger_tool"] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules["ledger_tool"])
    return sys.modules["ledger_tool"]


class LedgerTests(unittest.TestCase):
    """`docs/feedback/ledger.toml`, from which `tools/ledger.py` computes §8's "done": a remark or a change that names no
    family, or a lesson missing from the run, would count a change clean that is not."""

    def setUp(self):
        with LEDGER.open("rb") as f:
            self.ledger = tomllib.load(f)

    def test_the_ledger_parses(self):
        self.assertTrue(self.ledger["families"])
        self.assertTrue(self.ledger["lesson"])
        self.assertTrue(self.ledger["change"])

    def test_lesson_numbers_are_contiguous(self):
        ns = [lesson["n"] for lesson in self.ledger["lesson"]]
        self.assertEqual(ns, list(range(ns[0], ns[0] + len(ns))), 'a lesson with no record is listed with form = "unknown"')

    def test_every_family_a_remark_names_exists(self):
        for lesson in self.ledger["lesson"]:
            for remark in lesson.get("remarks", []):
                self.assertIn(remark["family"], self.ledger["families"], f"lesson {lesson['n']}: {remark['text']}")

    def test_every_change_names_a_family_that_exists(self):
        for change in self.ledger["change"]:
            self.assertIn(change["family"], self.ledger["families"], change["title"])

    def test_the_fields_take_their_values(self):
        ref = re.compile(r"^(site_update_notifier)?#\d+$")
        ns = {lesson["n"] for lesson in self.ledger["lesson"]}
        for lesson in self.ledger["lesson"]:
            self.assertIn(lesson["form"], (True, False, "unknown"))
            self.assertEqual("load" in lesson, lesson["form"] is True, f"lesson {lesson['n']}: a load comes with a form")
            if lesson["form"] is True:
                self.assertIn(lesson["load"], ("light", "right", "heavy"))
            for remark in lesson.get("remarks", []):
                self.assertIn(remark["who"], ("main", "other"))
                self.assertIn(remark["class"], ("twenty", "precision", "mechanism"))
                self.assertTrue(remark["text"])
                self.assertTrue(all(ref.match(a) for a in remark["answered_by"]), remark["answered_by"])
        for name, family in self.ledger["families"].items():
            self.assertTrue(family["cause"], name)
            if "structural_pr" in family:
                self.assertRegex(family["structural_pr"], ref)
        for change in self.ledger["change"]:
            self.assertTrue(change.get("issue") or change.get("pr"), change["title"])
            self.assertTrue(all(ref.match(r) for r in change.get("issue", []) + change.get("pr", [])), change["title"])
            if "first_heard" in change:
                self.assertIn(change["first_heard"], ns, change["title"])


class LedgerToolTests(unittest.TestCase):
    """`tools/ledger.py`'s rule on a ledger of five lessons: three clean feedbacks make a change done, a remark of its
    family in its first lesson or later makes it recurred, a lesson with no record never counts as clean, and a family is
    not new once a change of it has been heard."""

    LEDGER = {
        "families": {"a": {"cause": "x"}, "b": {"cause": "y"}},
        "lesson": [
            {"n": 1, "form": True, "load": "right"},
            {"n": 2, "form": "unknown"},
            {"n": 3, "form": True, "load": "right", "remarks": [{"family": "a", "class": "precision", "answered_by": []}]},
            {"n": 4, "form": True, "load": "right", "remarks": [{"family": "b", "class": "precision", "answered_by": ["#9"]}]},
            {"n": 5, "form": True, "load": "right"},
        ],
    }

    def status(self, family, first=None):
        change = {"family": family, **({"first_heard": first} if first else {})}
        return ledger_tool().change_status(change, self.LEDGER["lesson"])

    def test_three_clean_feedbacks_make_a_change_done(self):
        st = self.status("b", 3)
        self.assertEqual((st.status, st.clean, st.recurred), ("recurred", [3], [(4, ["#9"])]))
        st = self.status("a", 4)
        self.assertEqual((st.status, st.clean), ("waiting", [4, 5]))
        st = self.status("b", 5)
        self.assertEqual((st.status, st.clean), ("waiting", [5]))
        st = self.status("a", 1)
        self.assertEqual((st.status, st.clean, st.unknown), ("recurred", [1], [2]))
        ledger = {**self.LEDGER, "lesson": [*self.LEDGER["lesson"], {"n": 6, "form": True, "load": "right"}]}
        st = ledger_tool().change_status({"family": "a", "first_heard": 4}, ledger["lesson"])
        self.assertEqual((st.status, st.clean), ("done", [4, 5, 6]))
        self.assertEqual(self.status("a").status, "not heard")

    def test_a_lesson_with_no_record_is_never_clean(self):
        st = ledger_tool().change_status({"family": "b", "first_heard": 2}, self.LEDGER["lesson"])
        self.assertEqual((st.clean, st.unknown), ([3], [2]))

    def test_the_settled_run_ends_at_a_new_family_or_a_twenty_point_remark(self):
        tool = ledger_tool()
        self.assertEqual(tool.settled_run(tool.read_lessons(self.LEDGER["lesson"])), 1, "lesson 4 brings family b")
        twenty = [*self.LEDGER["lesson"], {"n": 6, "form": True, "load": "right", "remarks": [{"family": "a", "class": "twenty"}]}]
        self.assertEqual(tool.settled_run(tool.read_lessons(twenty)), 0)
        heavy = [*self.LEDGER["lesson"], {"n": 6, "form": True, "load": "heavy"}]
        self.assertEqual(tool.settled_run(tool.read_lessons(heavy)), 0)
        played = [{"family": "b", "first_heard": 4}]
        self.assertEqual(tool.read_lessons(self.LEDGER["lesson"], played)[3].new, [], "a change of b was heard by lesson 4")
        self.assertEqual(tool.settled_run(tool.read_lessons(self.LEDGER["lesson"], played)), 2, "lesson 3 brings family a")

    def test_the_table_has_the_section_8_columns_and_a_row_per_change(self):
        tool = ledger_tool()
        ledger = tool.load()
        rows = tool.table(ledger).splitlines()
        self.assertEqual(rows[0], "| built (issue: PR) | first heard | feedbacks without its remark |")
        self.assertEqual(len(rows), 2 + len(ledger["change"]))


if __name__ == "__main__":
    unittest.main()
