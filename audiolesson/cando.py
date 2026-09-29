"""Travel can-do scenarios (issue #131): the outcome the course aims at, and whether the
items each scenario needs are in the curriculum and reached in time.

A curriculum directory may carry ``cando/*.toml`` next to its modules (a subdirectory, so
``load_curriculum`` never reads it as a module):

    [[scenarios]]
    id = "A3"
    tier = "A"                      # A must / B should / C nice to have
    title = "Supermarket"
    title_ja = "スーパー"
    setting = "…"
    success = "…"                   # observable
    items = ["hvar_er", "poka"]     # curriculum ids the scenario needs
    missing = ["«Viltu poka?» …"]   # needed, not in the curriculum yet
    reading = ["mjólk"]             # texts to read (issue #133)
    clerk_lines = ["Viltu poka?"]   # lines to understand (issue #134)
    respect = ["greet", "thanks"]   # respect markers the scenario checks

Personal trip details (dates, itinerary) never go here: they live in a private profile
next to the learner file (issue #132). Milestones are relative to departure: Tier A by
T−7 weeks, Tier B by T−4 weeks, one lesson a day.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .content import Curriculum, CurriculumError

TIERS = ("A", "B", "C")
# weeks before departure by which a tier's items should have been introduced
MILESTONE_WEEKS = {"A": 7, "B": 4}


@dataclass
class Scenario:
    id: str
    tier: str
    title: str
    title_ja: str = ""
    setting: str = ""
    success: str = ""
    items: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    reading: list[str] = field(default_factory=list)
    clerk_lines: list[str] = field(default_factory=list)
    respect: list[str] = field(default_factory=list)


def load_cando(curriculum_dir: str | Path, cur: Curriculum | None = None) -> list[Scenario]:
    """Every scenario in ``<curriculum>/cando/*.toml`` (none if there is no such directory).
    With ``cur``, every listed item id must exist in it."""
    d = Path(curriculum_dir) / "cando"
    if not d.is_dir():
        return []
    out: list[Scenario] = []
    for f in sorted(d.glob("*.toml")):
        with f.open("rb") as fh:
            raw = tomllib.load(fh)
        for s in raw.get("scenarios", []):
            try:
                sc = Scenario(**s)
            except TypeError as e:
                raise CurriculumError(f"{f}: scenario {s.get('id')!r}: {e}") from None
            if sc.tier not in TIERS:
                raise CurriculumError(f"{f}: scenario {sc.id!r}: tier must be one of {TIERS}")
            out.append(sc)
    ids = [s.id for s in out]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise CurriculumError(f"can-do scenario ids repeat: {sorted(dupes)}")
    if cur is not None:
        unknown = [(s.id, i) for s in out for i in s.items if i not in cur.by_id]
        if unknown:
            raise CurriculumError(f"can-do scenarios name unknown items: {unknown}")
    return out


def simulate_reach(cur: Curriculum, lessons: int, pace: int, minutes: float = 30, seed: int = 1) -> dict[str, int]:
    """The lesson in which each item is first met, for a new learner doing one lesson a day
    at a fixed pace with every retrieval presumed successful (optimistic: real pace is
    lower). Items never met within ``lessons`` are absent."""
    from .learner import LearnerState
    from .planner import PlanConfig, Planner, apply_to_learner
    from .prompts import Prompts
    from .timing import Timing

    learner = LearnerState(cur.target_lang, cur.known_lang, "A1")
    prompts = Prompts.load(cur.known_lang)
    day = date(2026, 1, 1)
    reach: dict[str, int] = {}
    for n in range(1, lessons + 1):
        sc = Planner(cur, learner, prompts, Timing(level="A1"),
                     PlanConfig(minutes=minutes, new_items=pace, seed=seed + n), today=day).build()
        apply_to_learner(sc, learner, day)
        for it in cur.items:
            if it.id not in reach and learner.has_met(it.id):
                reach[it.id] = n
        day += timedelta(days=1)
    return reach


def milestone_lesson(tier: str, lessons: int) -> int | None:
    """The lesson by which a tier's items should be met, for a horizon of ``lessons``
    daily lessons before departure (None: no milestone, or none left)."""
    weeks = MILESTONE_WEEKS.get(tier)
    if weeks is None:
        return None
    return max(lessons - 7 * weeks, 0) or None


def coverage(cur: Curriculum, scenarios: list[Scenario], reach: dict[int, dict[str, int]], lessons: int) -> list[dict]:
    """Per scenario: its items with curriculum order and the lesson they're reached at each
    simulated pace, the items that miss the tier's milestone at each pace, and what the
    curriculum still lacks. ``reach`` maps pace → simulate_reach()."""
    rows = []
    for s in scenarios:
        due = milestone_lesson(s.tier, lessons)
        items = []
        late: dict[int, list[str]] = {}
        for i in s.items:
            at = {pace: r.get(i) for pace, r in reach.items()}
            items.append({"id": i, "order": cur.by_id[i].order, "reached": at})
            for pace, n in at.items():
                if due is not None and (n is None or n > due):
                    late.setdefault(pace, []).append(i)
        rows.append({"scenario": s, "due": due, "items": items, "late": late, "missing": list(s.missing)})
    return rows


def format_coverage(rows: list[dict], lessons: int, paces: list[int]) -> str:
    lines = [
        f"can-do coverage for a horizon of {lessons} daily lessons (simulated, every retrieval presumed "
        f"successful; paces {', '.join(map(str, paces))}). Tier A due by lesson {milestone_lesson('A', lessons)}, "
        f"Tier B by lesson {milestone_lesson('B', lessons)}."
    ]
    for row in rows:
        s: Scenario = row["scenario"]
        worst = max(row["items"], key=lambda i: i["order"], default=None)
        lines.append(
            f"{s.id} [{s.tier}] {s.title}: {len(row['items'])} items"
            + (f", latest #{worst['order']} {worst['id']}" if worst else "")
            + (f", missing {len(row['missing'])}" if row["missing"] else "")
        )
        for pace in paces:
            late = row["late"].get(pace, [])
            if late:
                lines.append(f"  late at pace {pace} (due lesson {row['due']}): {', '.join(late)}")
        for m in row["missing"]:
            lines.append(f"  missing: {m}")
    return "\n".join(lines)
