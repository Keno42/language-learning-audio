"""The documents' mechanical consistency (LEARNING-DESIGN §10 "Documents: replace, don't append").

What a reader can't check by eye across 1000 lines: "Now" lives in one place (the status brief, #364) and stays within its
limit, as §5 does, a reference such as "§5.14" or §9 "Repetition" names something that exists, and the files `CLAUDE.md`'s
reading table names are there."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
LD = DOCS / "LEARNING-DESIGN.md"
STATUS = DOCS / "CURRENT-STATUS.md"
EVIDENCE = DOCS / "history" / "evidence.md"


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


if __name__ == "__main__":
    unittest.main()
