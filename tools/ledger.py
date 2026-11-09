#!/usr/bin/env python3
"""The feedback ledger: when a built change is done, computed from the remarks (docs/LEARNING-DESIGN.md §8).

LD §8's table counts by hand the feedbacks each built change has had without a remark of the same kind. This reads
``docs/feedback/ledger.toml``, where each lesson's remarks carry the family of their cause and each change names its
family and the lesson it was first heard in, and computes:

- per change: **done** after three clean feedback lessons since it was first heard (a form, and no remark of its
  family); **recurred** once its family is remarked in that lesson or later; else **waiting**. A lesson with no record
  (form "unknown") never counts as clean. This is the feedback half of §8's rule; its daily-read row is read on the
  replay (``tools/replay_lesson.py``);
- per lesson: the remarks, and which families are new or recurring. A family is known once a lesson remarks it or
  plays a change of it (``first_heard``): a cause something was built for is not a new one when it is first remarked;
- the **settled run** (§9 "Governance"): settled lessons in a row, up to the latest. A settled lesson has a form, load
  not «heavy», and no twenty-point remark of a recurring family: the structural fixes hold. A new family of any class
  does not break the run (new material brings new kinds of remark), and neither does «light» (the pace answers it, H9);
- per lesson, as an advisory: the behaviour PRs it is the first built with (``built``), flagged past two (§9 "Governance");
- per development round from ``LONG_RUN_FROM``: a lesson first built with behaviour PRs names its long-run PR (``long_run``) or the
  owner's waiver (``long_run_waived``), and no more than ``LONG_RUN_SPAN`` lessons pass in a row without one (``long_run_gaps``);
  ``tests/test_docs.py`` fails on a gap: the long run moves every round unless the owner says why not (§9 "Governance", owner 2026-11-09).

    python tools/ledger.py [--ledger docs/feedback/ledger.toml] [--table]

``--table`` prints the §8 table in its format, the third column computed. Nothing is written.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "docs" / "feedback" / "ledger.toml"
CLEAN_FEEDBACKS = 3  # LD §8: three feedbacks without a remark of the same kind
MAX_BUILT = 2  # LD §9 "Governance": at most two behaviour PRs between one lesson and the next
# LD §9 "Governance" (owner, 2026-11-09): one of them advances the long run. From this lesson on, every lesson names its long-run PR or the
# owner's waiver; lessons 35–51 spent every PR on remarks and the long run moved in none of them
LONG_RUN_FROM = 53
LONG_RUN_SPAN = 7  # the weekly round (§1): at most this many lessons in a row without the long run moving or the owner's waiver


def load(path: Path = LEDGER) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def lessons(ledger: dict) -> list[dict]:
    return sorted(ledger.get("lesson", []), key=lambda lesson: lesson["n"])


def remarks(lesson: dict) -> list[dict]:
    return lesson.get("remarks", [])


def remarked(lesson: dict, family: str) -> bool:
    return any(r["family"] == family for r in remarks(lesson))


def clean_for(lesson: dict, family: str) -> bool:
    """A feedback lesson without a remark of the family; a lesson with no record is never clean."""
    return lesson["form"] is True and not remarked(lesson, family)


@dataclass
class ChangeStatus:
    status: str  # "done", "waiting", "recurred" or "not heard"
    clean: list[int] = field(default_factory=list)  # clean lessons since first heard, up to its family's first remark
    unknown: list[int] = field(default_factory=list)  # lessons with no record in the same span
    recurred: list[tuple[int, list[str]]] = field(default_factory=list)  # (lesson, answered_by) of its family's remarks


def change_status(change: dict, ls: list[dict]) -> ChangeStatus:
    first = change.get("first_heard")
    if first is None:
        return ChangeStatus("not heard")
    family = change["family"]
    since = [lesson for lesson in ls if lesson["n"] >= first]
    recurred = [(lesson["n"], [a for r in remarks(lesson) if r["family"] == family for a in r.get("answered_by", [])])
                for lesson in since if remarked(lesson, family)]
    counted = [lesson for lesson in since if not recurred or lesson["n"] < recurred[0][0]]
    clean = [lesson["n"] for lesson in counted if clean_for(lesson, family)]
    unknown = [lesson["n"] for lesson in counted if lesson["form"] == "unknown"]
    if recurred:
        status = "recurred"
    elif len(clean) >= CLEAN_FEEDBACKS:
        status = "done"
    else:
        status = "waiting"
    return ChangeStatus(status, clean, unknown, recurred)


@dataclass
class LessonRead:
    n: int
    form: bool | str
    load: str | None
    remarks: int
    twenty: int
    new: list[str]
    recurring: list[str]
    twenty_recurring: list[str] = field(default_factory=list)  # the families of its twenty-point remarks that were known
    built: list[str] | None = None  # the behaviour PRs it is the first built with; None where the ledger does not say

    @property
    def settled(self) -> bool:
        """A form, load not «heavy», no twenty-point remark of a recurring family; new families and «light» allowed."""
        return self.form is True and self.load != "heavy" and not self.twenty_recurring

    def why_not_settled(self) -> list[str]:
        why = []
        if self.form is not True:
            why.append("no form" if self.form is False else "no record")
        elif self.load == "heavy":
            why.append("load heavy")
        if self.twenty_recurring:
            why.append(f"twenty-point of {', '.join(self.twenty_recurring)}")
        return why


def read_lessons(ls: list[dict], changes: list[dict] = ()) -> list[LessonRead]:
    seen: set[str] = set()
    out = []
    for lesson in ls:
        seen.update(c["family"] for c in changes if c.get("first_heard", lesson["n"] + 1) <= lesson["n"])
        families = list(dict.fromkeys(r["family"] for r in remarks(lesson)))
        twenty = [r["family"] for r in remarks(lesson) if r["class"] == "twenty"]
        out.append(LessonRead(lesson["n"], lesson["form"], lesson.get("load"), len(remarks(lesson)), len(twenty),
                              [f for f in families if f not in seen], [f for f in families if f in seen],
                              list(dict.fromkeys(f for f in twenty if f in seen)), lesson.get("built")))
        seen.update(families)
    return out


def settled_run(reads: list[LessonRead]) -> int:
    """Settled lessons in a row, ending at the latest lesson."""
    run = 0
    for read in reversed(reads):
        if not read.settled:
            break
        run += 1
    return run


def too_many_built(reads: list[LessonRead]) -> list[int]:
    """The lessons that are the first built with more than ``MAX_BUILT`` behaviour PRs (advisory: nothing fails on it)."""
    return [r.n for r in reads if r.built is not None and len(r.built) > MAX_BUILT]


def long_run_gaps(ls: list[dict]) -> list[int]:
    """The lessons from ``LONG_RUN_FROM`` that break the long-run rule, counted by development round, not by lesson (review of #505: a weekly
    round is allowed): a lesson that is the first built with behaviour PRs (``built``) is a round's, and names its long-run PR (``long_run``)
    or the owner's waiver (``long_run_waived``); a lesson built with none needs neither, but no more than ``LONG_RUN_SPAN`` lessons in a row pass
    without one, so a week with no round at all is caught too."""
    gaps: list[int] = []
    since = 0
    for lesson in ls:
        if lesson["n"] < LONG_RUN_FROM:
            continue
        moved = bool(lesson.get("long_run") or lesson.get("long_run_waived"))
        since = 0 if moved else since + 1
        if (lesson.get("built") and not moved) or since > LONG_RUN_SPAN:
            gaps.append(lesson["n"])
    return gaps


def spans(ns: list[int]) -> str:
    """[27, 28, 29, 33] -> "27–29, 33"."""
    out: list[str] = []
    for n in ns:
        if out and int(out[-1].split("–")[-1]) == n - 1:
            out[-1] = f"{out[-1].split('–')[0]}–{n}"
        else:
            out.append(str(n))
    return ", ".join(out)


def feedbacks_cell(st: ChangeStatus) -> str:
    """The §8 table's third column: "2 (25, 26)", with the lessons with no record and the remarks that came back."""
    if st.status == "not heard":
        return "–"
    lessons_ = ", ".join(map(str, st.clean))
    if st.unknown:
        lessons_ = f"{lessons_}; {spans(st.unknown)} no record" if lessons_ else f"{spans(st.unknown)} no record"
    cell = f"{len(st.clean)} ({lessons_})" if lessons_ else str(len(st.clean))
    if st.recurred:
        cell += "; its family remarked in " + ", ".join(f"{n} ({', '.join(a)})" if a else str(n) for n, a in st.recurred)
    return cell


def heard_cell(change: dict) -> str:
    first, heard = change.get("first_heard"), change.get("heard")
    if first is None:
        return heard or "not yet"
    return f"lesson {first} ({heard})" if heard else f"lesson {first}"


def table(ledger: dict) -> str:
    ls = lessons(ledger)
    rows = ["| built (issue: PR) | first heard | feedbacks without its remark |", "|---|---|---|"]
    for change in ledger.get("change", []):
        st = change_status(change, ls)
        cell = f"**done**: {feedbacks_cell(st)}" if st.status == "done" else feedbacks_cell(st)
        rows.append(f"| {change['title']} | {heard_cell(change)} | {cell} |")
    return "\n".join(rows)


def report(ledger: dict) -> str:
    ls = lessons(ledger)
    reads = read_lessons(ls, ledger.get("change", []))
    out = ["lesson  form     load   remarks  twenty  new families / recurring families"]
    for r in reads:
        form = {True: "yes", False: "no"}.get(r.form, r.form)
        fams = f"{', '.join(r.new) or '-'} / {', '.join(r.recurring) or '-'}"
        state = "settled" if r.settled else "not settled: " + ", ".join(r.why_not_settled())
        out.append(f"{r.n:<7} {form:<8} {r.load or '-':<6} {r.remarks:<8} {r.twenty:<7} {fams}  [{state}]")
    run = settled_run(reads)
    out.append("")
    out.append(f"settled run: {run} lesson{'s' if run != 1 else ''} up to lesson {reads[-1].n}" if reads else "settled run: no lessons")
    recorded = [r for r in reads if r.built is not None]
    if recorded:
        over = set(too_many_built(reads))
        out.append(f"behaviour PRs a lesson is the first built with, at most {MAX_BUILT} "
                   f"(advisory; lessons {spans([r.n for r in recorded])}):")
        for r in recorded:
            flag = f"  [more than {MAX_BUILT}]" if r.n in over else ""
            out.append(f"  {r.n:<5} {len(r.built):<3} {', '.join(r.built) or '-'}{flag}")
    out.append(f"the long run (a PR in every round from lesson {LONG_RUN_FROM}, or the owner's waiver; at most {LONG_RUN_SPAN} lessons without one):")
    gaps = set(long_run_gaps(ls))
    for lesson in (lesson for lesson in ls if lesson["n"] >= LONG_RUN_FROM):
        said = ", ".join(lesson.get("long_run", [])) or (f"waived: {lesson['long_run_waived']}" if lesson.get("long_run_waived") else
                                                         ("MISSING" if lesson["n"] in gaps else "no round"))
        out.append(f"  {lesson['n']:<5} {said}")
    statuses = [(change, change_status(change, ls)) for change in ledger.get("change", [])]
    counts = {s: sum(st.status == s for _, st in statuses) for s in ("done", "waiting", "recurred", "not heard")}
    out.append("changes: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    for change, st in statuses:
        refs = ": ".join(", ".join(change[k]) for k in ("issue", "pr") if change.get(k))
        out.append(f"  {st.status:<9} {change['family']:<18} {refs:<28} {feedbacks_cell(st)}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--table", action="store_true", help="print the LEARNING-DESIGN §8 table, its third column computed")
    args = ap.parse_args(argv)
    ledger = load(args.ledger)
    print(table(ledger) if args.table else report(ledger))
    return 0


if __name__ == "__main__":
    sys.exit(main())
