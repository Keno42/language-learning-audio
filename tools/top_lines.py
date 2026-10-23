#!/usr/bin/env python3
"""The most-said lines, for the native check (G10, #209).

No fluent speaker has reviewed the course: every line is a candidate (CURRENT-POLICY). A review of all of it is more than
one sitting; the lines the lessons say most are where an unnatural one costs most, so the check starts there. This counts
the target-language lines of the given lesson scripts, a model answer (segment ``answer``) as said by the learner and any
other target-language speech as heard, the same line in another case or with another final mark once
(``text.norm_utterance``), and prints the ``--top`` most frequent as a Markdown table for a fluent speaker to fill in.

    python tools/top_lines.py out/lesson-0*.script.json [--top 30]

Read-only. A script holds only the course's lines (the trip profile is never written into it), and the tool reads
nothing else. The pieces of a line (``PIECES``: a hint's first word, a cloze's stem, a slow model's words, a caught word)
are not counted: a piece is checked in its line.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audiolesson.script import Script  # noqa: E402
from audiolesson.text import norm_utterance  # noqa: E402

PIECES = ("hint", "partial", "spaced", "listening_word")


def count_lines(paths: list[Path]) -> tuple[dict[str, list], list[int]]:
    """``({normalised line: [the line as first said, said, heard]}, the lessons' numbers)``."""
    counts: dict[str, list] = {}
    lessons = []
    for path in paths:
        sc = Script.load(path)
        lessons.append(sc.lesson_number)
        for s in sc.segments:
            if s.type not in ("speak", "answer") or s.lang != sc.target_lang or not s.text or s.role in PIECES:
                continue
            entry = counts.setdefault(norm_utterance(s.text), [s.text.strip(), 0, 0])
            entry[1 if s.type == "answer" else 2] += 1
    return counts, lessons


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("scripts", type=Path, nargs="+", help="lesson-NNN.script.json files")
    ap.add_argument("--top", type=int, default=30, help="lines to print (default 30)")
    args = ap.parse_args(argv)

    counts, lessons = count_lines(args.scripts)
    # how often the audio says the line, said and heard together; a tie goes to the line the learner says more
    ranked = sorted(counts.values(), key=lambda e: (-(e[1] + e[2]), -e[1], e[0].casefold()))[: args.top]
    print("# The most-said lines: candidates awaiting native review (G10, #209)\n")
    print(f"Lessons {min(lessons)}–{max(lessons)} ({len(lessons)} scripts), the {len(ranked)} most frequent of {len(counts)} lines. "
          f"Said: the learner's answer; heard: any other line in Icelandic. Every line is a candidate until a fluent speaker marks it.\n")
    print("| # | line | said | heard | ok / unnatural / wrong | what a native would say |")
    print("|---|---|---|---|---|---|")
    for n, (line, said, heard) in enumerate(ranked, 1):
        print(f"| {n} | {line.replace('|', chr(92) + '|')} | {said} | {heard} | | |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
