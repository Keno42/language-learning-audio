"""The documents' mechanical consistency (LEARNING-DESIGN §10 "Documents: replace, don't append").

What a reader can't check by eye across 1000 lines: the brief's copy of "Now" is the roadmap's, "Now" and §5 stay within
their limits, and a reference such as "§5.14" or §9 "Repetition" names something that exists."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
LD = DOCS / "LEARNING-DESIGN.md"
STATUS = DOCS / "CURRENT-STATUS.md"
EVIDENCE = DOCS / "history" / "evidence.md"


def now_block(text: str) -> str:
    """The "Now" list, from its bold heading to the paragraph that follows the list."""
    m = re.search(r"^\*\*Now \(updated .*?(?=^\*\*Refactoring alongside)", text, re.M | re.S)
    if m is None:
        raise AssertionError('no "**Now (updated …" block followed by "**Refactoring alongside"')
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

    def test_the_status_brief_copies_now_verbatim(self):
        self.assertEqual(now_block(STATUS.read_text(encoding="utf-8")), now_block(self.ld))

    def test_now_holds_four_items_at_most(self):
        items = re.findall(r"^\d+\. ", now_block(self.ld), re.M)
        self.assertLessEqual(len(items), 4, '§1: "Now" holds three or four items at most')

    def test_section_5_keeps_the_last_three_lessons(self):
        lessons = re.findall(r"^### 5\.\d+ Lesson", sections(self.ld)["5"], re.M)
        self.assertLessEqual(len(lessons), 3, "move the oldest subsection to docs/history/evidence.md")

    def test_every_numbered_evidence_reference_resolves(self):
        headings = set(re.findall(r"^### (5\.\d+) ", self.ld + EVIDENCE.read_text(encoding="utf-8"), re.M))
        for path in referring_files():
            for ref in set(re.findall(r"§(5\.\d+)", path.read_text(encoding="utf-8"))):
                self.assertIn(ref, headings, f"{path.name}: §{ref} names no subsection")

    def test_every_named_section_reference_resolves(self):
        """§9 "Repetition" must name something §9 holds (a bold heading or a phrase in it)."""
        secs = sections(self.ld)
        for path in referring_files():
            for num, name in set(re.findall(r'§(\d+) [«"]([^"»]+)["»]', path.read_text(encoding="utf-8"))):
                if num in secs:
                    name, text = " ".join(name.lower().split()), " ".join(secs[num].lower().split())
                    self.assertIn(name, text, f'{path.name}: §{num} "{name}" is not in §{num}')


if __name__ == "__main__":
    unittest.main()
