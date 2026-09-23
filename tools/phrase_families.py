#!/usr/bin/env python3
"""Fixed-phrase family scan (issue #29, curriculum-wide audit).

Groups phrase items that share a two-word opening or closing frame ("Má ég …?",
"… á morgun") and reports, per family, whether any construction already covers that
frame. A family of several fixed strings sharing a frame is a *candidate* for one of
the three dispositions in docs/AUDIT-29.md — a lexicalised chunk to keep whole, a
phrase whose structure can later become productive, or a family where teaching the
shared dimension reduces what must be memorised. Like dialogue_sequencing_report(),
this is a diagnostic signal for an author to read, not a gate.

    python tools/phrase_families.py [curriculum-path] [--min N]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audiolesson.content import load_curriculum  # noqa: E402

_WORD = re.compile(r"[^\W\d]+", re.UNICODE)


def families(cur, min_size: int = 3) -> list[tuple[str, list, str | None]]:
    """(frame, member phrases, covering construction id or None), largest first."""
    groups: dict[str, list] = defaultdict(list)
    for it in cur.items:
        if it.kind != "phrase":
            continue
        words = [w.lower() for w in _WORD.findall(it.target)]
        if len(words) < 3:
            continue
        groups[" ".join(words[:2]) + " …"].append(it)
        groups["… " + " ".join(words[-2:])].append(it)
    constructions = [c for c in cur.items if c.kind == "construction"]

    def covering(frame: str) -> str | None:
        fixed = frame.replace("…", "").split()
        for c in constructions:
            words = [w.lower() for w in _WORD.findall(re.sub(r"\{\w+\}", "", c.target))]
            if words[: len(fixed)] == fixed or words[-len(fixed) :] == fixed:
                return c.id
        return None

    rows = [(frame, members, covering(frame)) for frame, members in groups.items() if len(members) >= min_size]
    rows.sort(key=lambda r: (-len(r[1]), r[0]))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path", nargs="?", default="curricula/is-en")
    ap.add_argument("--min", type=int, default=3, help="smallest family size to report (default 3)")
    args = ap.parse_args()
    cur = load_curriculum(args.path)
    print("| frame | size | covered by | members (curriculum order) |")
    print("|---|---|---|---|")
    for frame, members, cover in families(cur, args.min):
        shown = "; ".join(f"{m.target} ({m.order})" for m in sorted(members, key=lambda m: m.order))
        print(f"| {frame} | {len(members)} | {cover or '—'} | {shown} |")


if __name__ == "__main__":
    main()
