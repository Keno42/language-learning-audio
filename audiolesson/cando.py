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

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from pathlib import Path

from .content import Curriculum, CurriculumError
from .records import check_items, load_records

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
    # seasonal content (PR #138 review): a scenario that only applies in one season, and
    # extra items a scenario needs in a given season; both follow the trip profile's season
    season: str | None = None
    seasonal: dict[str, list[str]] = field(default_factory=dict)


def for_season(scenarios: list[Scenario], season: str | None) -> list[Scenario]:
    """The scenarios as they apply in ``season``: a seasonal scenario only in its season,
    and each scenario's seasonal items added only for that season. No season (no profile,
    or a profile without one): no seasonal content at all."""
    out = []
    for s in scenarios:
        if s.season is not None and s.season != season:
            continue
        extra = [i for i in s.seasonal.get(season or "", []) if i not in s.items]
        out.append(replace(s, items=s.items + extra) if extra else s)
    return out


def load_cando(curriculum_dir: str | Path, cur: Curriculum | None = None) -> list[Scenario]:
    """Every scenario in ``<curriculum>/cando/*.toml`` (none if there is no such directory).
    With ``cur``, every listed item id must exist in it."""
    out: list[Scenario] = []
    for f, sc in load_records(Path(curriculum_dir) / "cando", "scenarios", Scenario, "can-do scenario"):
        if sc.tier not in TIERS:
            raise CurriculumError(f"{f}: scenario {sc.id!r}: tier must be one of {TIERS}")
        out.append(sc)
    if cur is not None:
        pairs = [(s.id, i) for s in out for i in s.items + [x for v in s.seasonal.values() for x in v]]
        check_items(pairs, cur.by_id, "can-do scenarios")
    return out


def priority_items(cur: Curriculum, scenarios: list[Scenario], boost: list[str] | tuple[str, ...] = (),
                   tiers: tuple[str, ...] = ("A", "B")) -> list[str]:
    """The trip ordering (#132): the items to introduce before everything else, in order.
    Boosted scenarios come first, then each tier in ``tiers``; within a group, curriculum
    order. Every item brings its prereqs (transitively) into its group, ahead of it.
    Unknown boost ids are ignored."""
    by_id = {s.id: s for s in scenarios}
    groups = [[i for sid in boost if sid in by_id for i in by_id[sid].items]]
    groups += [[i for s in scenarios if s.tier == t for i in s.items] for t in tiers]
    out: list[str] = []
    seen: set[str] = set()

    def closure(item_id: str, acc: set[str]) -> None:
        if item_id in acc or item_id not in cur.by_id:
            return
        acc.add(item_id)
        for p in cur.by_id[item_id].prereqs:
            closure(p, acc)

    for group in groups:
        acc: set[str] = set()
        for i in group:
            closure(i, acc)
        for i in sorted(acc - seen, key=lambda x: cur.by_id[x].order):
            out.append(i)
            seen.add(i)
    return out


def simulate_reach(cur: Curriculum, lessons: int, pace: int, minutes: float = 30, seed: int = 1,
                   priority: list[str] | None = None) -> dict[str, int]:
    """The lesson in which each item is first met, for a new learner doing one lesson a day
    at a fixed pace with every retrieval presumed successful (optimistic: real pace is
    lower). Items never met within ``lessons`` are absent. ``priority``: the trip ordering."""
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
                     PlanConfig(minutes=minutes, new_items=pace, seed=seed + n, priority=list(priority or [])),
                     today=day).build()
        apply_to_learner(sc, learner, day)
        for it in cur.items:
            if it.id not in reach and learner.has_met(it.id):
                reach[it.id] = n
        day += timedelta(days=1)
    return reach


def milestone_lesson(tier: str, lessons: int) -> int | None:
    """The lesson by which a tier's items should be met, for a horizon of ``lessons``
    daily lessons before departure. None: the tier has no milestone (Tier C). 0: the
    milestone has already passed — no lesson is left before it, so every item of the
    tier is overdue (PR #137 review: a short horizon must show the shortfall, not hide it)."""
    weeks = MILESTONE_WEEKS.get(tier)
    if weeks is None:
        return None
    return max(lessons - 7 * weeks, 0)


def check_horizon(lessons: int, paces: list[int]) -> None:
    """A report needs at least one lesson and at least one positive pace."""
    if lessons <= 0:
        raise ValueError(f"--lessons must be positive (got {lessons})")
    if not paces or any(p <= 0 for p in paces):
        raise ValueError(f"--paces must list positive numbers of new items per lesson (got {paces})")


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
        rows.append({"scenario": s, "due": due, "overdue": due == 0, "items": items, "late": late, "missing": list(s.missing)})
    return rows


def _due_text(tier: str, lessons: int) -> str:
    due = milestone_lesson(tier, lessons)
    if due == 0:
        return (f"Tier {tier}: milestone (T−{MILESTONE_WEEKS[tier]} weeks) already passed — no lesson was left "
                f"before it, so every Tier {tier} item is overdue")
    return f"Tier {tier} due by lesson {due}"


def format_coverage(rows: list[dict], lessons: int, paces: list[int]) -> str:
    lines = [
        f"can-do coverage for a horizon of {lessons} daily lessons (simulated, every retrieval presumed "
        f"successful; paces {', '.join(map(str, paces))}). "
        + "; ".join(_due_text(t, lessons) for t in MILESTONE_WEEKS) + "."
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
            if late and row["overdue"]:
                lines.append(f"  overdue at pace {pace} (milestone already passed): {', '.join(late)}")
            elif late:
                lines.append(f"  late at pace {pace} (due lesson {row['due']}): {', '.join(late)}")
        for m in row["missing"]:
            lines.append(f"  missing: {m}")
    return "\n".join(lines)
