"""Scenario cards (issue #129): one scripted beat of a travel can-do scenario (#131), for
the Discord review. They replace the GPT Voice role-play, which did not follow a script.

A card states the situation in the learner's language. It may carry the local's line
(``partner``), which the learner hears (🔊) before answering and only reads afterwards.
It lists the model replies and the curriculum items the first reply needs:

    [[scenes]]
    id = "a2_change"
    scenario = "A2"
    kind = "respond"                # respond | initiate | repair
    situation = "At the till you are handed your change."
    situation_ja = "レジでお釣りを渡されます。"
    partner = "Gjörðu svo vel."
    partner_meaning = "Here you go."
    partner_meaning_ja = "どうぞ。"
    replies = ["Takk.", "Takk fyrir."]
    items = ["takk"]

- ``respond``: hear the partner, answer.
- ``initiate``: no partner line; start the exchange (greet, ask, apologise).
- ``repair``: the partner line is deliberately beyond the learner; the goal is to keep the
  conversation going («Ég skil ekki», «Gætirðu talað hægar?»).

A card may name the theme level whose goal it asks, ``level = "cafe:2"`` (``"<theme>:<n>"``,
``n`` from 1; #327). ``validate`` fails a level that does not exist and lists the levels no
card asks.

Cards live in ``<curriculum>/cando/scenes.toml`` (``load_cando`` reads only
``[[scenarios]]``, so the files can share the directory). A card is shown only once the
learner has met every item in ``items``; a partner line may go beyond the course (the
clerk-side lines of #134), and its meaning is revealed with the answer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from .cando import Scenario
from .content import Curriculum, CurriculumError
from .records import check_items, load_records
from .themes import Theme

KINDS = ("respond", "initiate", "repair")


@dataclass
class Scene:
    id: str
    scenario: str
    kind: str
    situation: str
    situation_ja: str = ""
    partner: str = ""
    partner_meaning: str = ""
    partner_meaning_ja: str = ""
    replies: list[str] = field(default_factory=list)
    items: list[str] = field(default_factory=list)
    note_ja: str = ""
    season: str | None = None  # only in that season (the trip profile's, #132)
    level: str = ""  # "<theme>:<n>": the theme level whose goal this card asks (#327)

    def to_dict(self) -> dict:
        return asdict(self)


def load_scenes(
    curriculum_dir: str | Path, cur: Curriculum | None = None, scenarios: list[Scenario] | None = None
) -> list[Scene]:
    """Every card in ``<curriculum>/cando/*.toml`` (none without the directory). With
    ``cur``, every item must exist; with ``scenarios``, every scenario id."""
    out: list[Scene] = []
    for f, scene in load_records(Path(curriculum_dir) / "cando", "scenes", Scene, "scene"):
        where = f"{f}: scene {scene.id!r}"
        if scene.kind not in KINDS:
            raise CurriculumError(f"{where}: kind must be one of {KINDS}")
        if scene.kind != "initiate" and not scene.partner.strip():
            raise CurriculumError(f"{where}: a {scene.kind} card needs the partner's line")
        if scene.kind == "initiate" and scene.partner.strip():
            raise CurriculumError(f"{where}: an initiate card has no partner line")
        if not scene.replies or not all(r.strip() for r in scene.replies):
            raise CurriculumError(f"{where}: replies are required")
        if not scene.situation.strip() or not scene.items:
            raise CurriculumError(f"{where}: situation and items are required")
        out.append(scene)
    if cur is not None:
        check_items([(s.id, i) for s in out for i in s.items], cur.by_id, "scenes")
    if scenarios is not None:
        known = {s.id for s in scenarios}
        orphans = [s.id for s in out if s.scenario not in known]
        if orphans:
            raise CurriculumError(f"scenes name unknown scenarios: {orphans}")
    return out


def uncovered(scenes: list[Scene], scenarios: list[Scenario], tier: str = "A") -> list[str]:
    """The scenarios of ``tier`` that have no card."""
    covered = {s.scenario for s in scenes}
    return [s.id for s in scenarios if s.tier == tier and s.id not in covered]


def theme_levels(themes: list[Theme]) -> list[str]:
    """Every theme level as a card names it, ``"<theme>:<n>"`` with ``n`` from 1 (the planner's key for a level)."""
    return [f"{t.id}:{n}" for t in themes for n in range(1, len(t.levels) + 1)]


def unknown_levels(scenes: list[Scene], themes: list[Theme]) -> list[tuple[str, str]]:
    """(card, level) for each card whose ``level`` names no theme level."""
    known = set(theme_levels(themes))
    return [(s.id, s.level) for s in scenes if s.level and s.level not in known]


def unasked_levels(scenes: list[Scene], themes: list[Theme]) -> list[str]:
    """The theme levels no card asks (#327): a level's goal the review never checks."""
    asked = {s.level for s in scenes}
    return [lv for lv in theme_levels(themes) if lv not in asked]


def available(
    scenes: list[Scene], scenarios: list[Scenario], season: str | None = None, met: set[str] | None = None
) -> list[Scene]:
    """The cards the learner can take: their scenario applies (``scenarios`` already
    filtered by season, see ``cando.for_season``), a seasonal card only in its season, and,
    with ``met``, every item of the card has been met. Without ``met`` (no learner), every
    applicable card."""
    applies = {s.id for s in scenarios}
    return [
        s
        for s in scenes
        if s.scenario in applies and s.season in (None, season) and (met is None or set(s.items) <= met)
    ]
