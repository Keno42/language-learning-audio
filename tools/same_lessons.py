#!/usr/bin/env python3
"""Check that a change leaves the simulated lessons as they were: the repository's own "behaviour unchanged" check (#281).

    python tools/same_lessons.py REV [--lessons 30]

Builds ``--lessons`` lessons of ``curricula/is-en`` from an empty learner, without a trip profile, in three
configs: 30 minutes with a target of 8 weighted components, 15 minutes with 4, and 30 minutes counting items. It does so on a
``git archive REV`` tree and on the working tree, each build in its own ``python3 -I`` process. After each lesson the next
day's review is reported through ``LearnerState.report``: every seventh new item of the course failed, the rest and the open
items asked recalled, so the open and hard items' paths run too. Each lesson's ``script.json`` and ``plan.json`` are compared
by their sha256. Exit 0 when every lesson is identical; 1 when one differs, with the first differing lesson's lines (what
is heard, else the file); 2 when a build fails.

No private data and no network: no trip profile, no feedback export. A simulated course presumes what a real one does not
(#94, #316): the owner's replay of a feedback export (``tools/replay_lesson.py``) stays the check on the real learner path.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = (("30 min, target 8", 30, 8.0), ("15 min, target 4", 15, 4.0), ("30 min, counting items", 30, None))
FAIL_EVERY = 7  # every seventh new item of the course is reported failed

# One course in one process: ``-I`` keeps the environment and the caller's directory out, so each tree imports its own code
CHILD = r"""
import json, os, sys
from datetime import date, timedelta
tree, out, minutes, target, n, fail_every = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
sys.path.insert(0, tree)
os.chdir(tree)
from audiolesson.cando import load_cando
from audiolesson.cli import _plan
from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.themes import load_themes, scenario_order
from audiolesson.timing import Timing

path = "curricula/is-en"
cur = load_curriculum(path)
scenarios = load_cando(path, cur)
themes = load_themes(path, cur, scenarios)
learner = LearnerState(cur.target_lang, cur.known_lang, cur.level)
prompts = Prompts.load(cur.known_lang)
day = date(2026, 9, 1)
new_seen = 0
for _ in range(n):
    cfg = PlanConfig(minutes=minutes, new_target=None if target == "None" else float(target), themes=themes, theme_scenarios=scenario_order(scenarios, ()))
    sc = Planner(cur, learner, prompts, Timing(level=learner.level or cur.level, speech_ratio=dict(learner.speech_calibration)), cfg, today=day).build()
    stem = f"{out}/lesson-{sc.lesson_number:03d}"
    sc.save(f"{stem}.script.json")
    with open(f"{stem}.plan.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(_plan(sc, cur), ensure_ascii=False, indent=1))
    apply_to_learner(sc, learner, day)
    day += timedelta(days=1)
    failed = []
    for i in sc.meta["new_items"]:
        new_seen += 1
        if new_seen % fail_every == 0:
            failed.append(i)
    asked = sc.meta["new_items"] + sc.meta["open_items"] + sc.meta["open_not_fitted"]
    learner.report(failed, [], day, lesson_number=sc.lesson_number, recalled=[i for i in asked if i not in failed])
"""


def checkout(rev: str, dest: Path) -> None:
    """``git archive REV`` unpacked into ``dest``: the tree as committed, without the working tree's changes."""
    p = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", rev], capture_output=True)
    if p.returncode:
        print(f"git archive {rev}: {p.stderr.decode(errors='replace').strip()}", file=sys.stderr)
        raise SystemExit(2)
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as tar:
        tar.extractall(dest, filter="data")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def heard(script: Path) -> list[str]:
    """What the learner hears, a segment a line: who says what, or a pause and its length."""
    segments = json.loads(script.read_text(encoding="utf-8"))["segments"]
    return [f"{s['type']} {s.get('speaker') or s.get('role') or ''}: {s.get('text') or round(s.get('duration', 0.0), 1)}" for s in segments]


def first_lines(a: list[str], b: list[str], limit: int = 20) -> list[str]:
    """The changed lines, at most ``limit``."""
    diff = difflib.unified_diff(a, b, lineterm="", n=0)
    return [line[:200] for line in diff if line[:1] in "+-" and not line.startswith(("+++", "---"))][:limit]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("rev", help="the revision to compare the working tree with (origin/main, a commit)")
    ap.add_argument("--lessons", type=int, default=30, help="lessons to build in each config (default 30)")
    args = ap.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="same_lessons-") as tmp:
        base = Path(tmp) / "rev"
        checkout(args.rev, base)
        runs: list[tuple[subprocess.Popen, Path]] = []
        for k, (_name, minutes, target) in enumerate(CONFIGS):
            for side, tree in (("rev", base), ("work", ROOT)):
                out = Path(tmp) / f"{k}-{side}"
                out.mkdir()
                cmd = [sys.executable, "-I", "-c", CHILD, str(tree), str(out), str(minutes), str(target), str(args.lessons), str(FAIL_EVERY)]
                runs.append((subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True), out))
        failures = []
        for proc, out in runs:
            err = proc.communicate()[1]
            if proc.returncode:
                failures.append(f"the build for {out.name} failed:\n{err[-3000:]}")
        if failures:
            print("\n".join(failures), file=sys.stderr)
            return 2

        differ = False
        for k, (name, _minutes, _target) in enumerate(CONFIGS):
            rev_dir, work_dir = Path(tmp) / f"{k}-rev", Path(tmp) / f"{k}-work"
            files = sorted(p.name for p in rev_dir.iterdir())
            if files != sorted(p.name for p in work_dir.iterdir()):
                print(f"{name}: the two trees built different lessons ({len(files)} files against {len(list(work_dir.iterdir()))})")
                differ = True
                continue
            changed: dict[str, list[str]] = {}  # lesson-NNN → the kinds of file that differ (script, plan)
            for f in files:
                if digest(rev_dir / f) != digest(work_dir / f):
                    stem, kind = f.split(".")[:2]
                    changed.setdefault(stem, []).append(kind)
            if not changed:
                print(f"{name}: {len(files) // 2} lessons, identical")
                continue
            differ = True
            print(f"{name}: {len(files) // 2} lessons, {len(changed)} differ: " + ", ".join(f"{s} ({', '.join(reversed(v))})" for s, v in changed.items()))
            stem, kinds = next(iter(changed.items()))
            a, b = heard(rev_dir / f"{stem}.script.json"), heard(work_dir / f"{stem}.script.json")
            if a != b:
                print(f"  {stem}, what is heard, {args.rev} (-) against the working tree (+):")
            else:  # the same lesson heard: the difference is in the timing, the meta or the plan
                first = f"{stem}.{kinds[-1]}.json"
                print(f"  {first} (the same segments), {args.rev} (-) against the working tree (+):")
                a, b = ((d / first).read_text(encoding="utf-8").splitlines() for d in (rev_dir, work_dir))
            for line in first_lines(a, b):
                print("   ", line)
        return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main())
