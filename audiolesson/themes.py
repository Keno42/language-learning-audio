"""Lesson themes (issue #149): one scene of a trip as a short exchange, at rising levels.

A theme is what a lesson consolidates instead of a word count: a scene with a goal
(ordering at a bakery, reading the road conditions, asking the guide when the bus leaves)
and, per level, the exchange that reaches it. Level 1 is the shortest exchange that
works; later levels raise its resolution (a quantity, a question back, paying, a receipt).

Themes live in ``<curriculum>/cando/themes.toml`` (``load_cando`` reads only
``[[scenarios]]`` and ``load_scenes`` only ``[[scenes]]``, so they share the directory)::

    [[themes]]
    id = "bakery"
    scenario = "A4"                 # the can-do scenario it serves
    title = "Bakery counter"
    title_ja = "パン屋のカウンター"
    setting = "A bakery in the morning."
    setting_ja = "朝のパン屋。"
    topics = ["cafe", "bakery"]     # what reviews and substitution drills it draws on

    [[themes.levels]]
    goal = "Get one pastry by pointing, answer the bag question, leave."
    goal_ja = "指さしで一つ買い、袋の質問に答えて店を出る。"
    turns = [
      { who = "you", cue = "You walk in. Greet the clerk.", cue_ja = "…", say = "Góðan daginn.", items = ["godan_daginn"] },
      { who = "partner", say = "Góðan daginn! Hvað má bjóða þér?", meaning = "Good morning! What can I get you?", meaning_ja = "…" },
      …
    ]
    listen = [{ say = "Næsti, gjörðu svo vel.", meaning = "Next, please.", meaning_ja = "次の方どうぞ。" }]
    read = ["Opið", "Matseðill"]    # reading deck texts met in the scene (#133)

- A ``you`` turn is the learner's line: a ``cue`` (the situation, in the learner's
  language), ``say`` (the model line), ``items`` (the curriculum items it needs) and
  optional ``alts`` (other good answers).
- A ``partner`` turn is what the other person says, with its meaning. It may go beyond the
  course: a learner who gets the gist of 80–90% of what is said is where they should be
  (owner, lesson 12 feedback). ``listen`` lines (announcements, a forecast, the guide
  talking to the group) are the same, outside the exchange.
- Levels come in order; a level is ready once every item of its ``you`` turns is met.

General content only: no learner's dates, itinerary or lodging (the private trip profile,
#132, decides which themes come first).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from .cando import Scenario
from .content import Curriculum, CurriculumError
from .records import check_items, load_records

WHO = ("you", "partner")


@dataclass
class Turn:
    who: str
    say: str
    cue: str = ""
    cue_ja: str = ""
    meaning: str = ""
    meaning_ja: str = ""
    items: list[str] = field(default_factory=list)
    alts: list[str] = field(default_factory=list)


@dataclass
class Line:
    say: str
    meaning: str
    meaning_ja: str = ""


@dataclass
class Level:
    goal: str
    goal_ja: str = ""
    turns: list[Turn] = field(default_factory=list)
    listen: list[Line] = field(default_factory=list)
    read: list[str] = field(default_factory=list)

    @property
    def items(self) -> list[str]:
        """What the learner's lines need, in order, without repeats."""
        return list(dict.fromkeys(i for t in self.turns if t.who == "you" for i in t.items))


@dataclass
class Theme:
    id: str
    scenario: str
    title: str
    title_ja: str = ""
    setting: str = ""
    setting_ja: str = ""
    topics: list[str] = field(default_factory=list)
    season: str | None = None  # only in that season (the trip profile's, #132)
    levels: list = field(default_factory=list)  # list[Level] once loaded

    def __post_init__(self) -> None:
        levels = []
        for n, raw in enumerate(self.levels, 1):
            if isinstance(raw, Level):
                levels.append(raw)
                continue
            raw = dict(raw)
            try:
                turns = [Turn(**t) for t in raw.pop("turns", [])]
                listen = [Line(**x) for x in raw.pop("listen", [])]
                levels.append(Level(turns=turns, listen=listen, **raw))
            except TypeError as e:
                raise CurriculumError(f"theme {self.id!r} level {n}: {e}") from None
        self.levels = levels

    def to_dict(self) -> dict:
        return asdict(self)


def _check(theme: Theme, where: str) -> None:
    if not theme.title.strip() or not theme.setting.strip():
        raise CurriculumError(f"{where}: title and setting are required")
    if not theme.levels:
        raise CurriculumError(f"{where}: at least one level is required")
    for n, level in enumerate(theme.levels, 1):
        at = f"{where} level {n}"
        if not level.goal.strip():
            raise CurriculumError(f"{at}: a goal is required")
        if not any(t.who == "you" for t in level.turns):
            raise CurriculumError(f"{at}: the learner says nothing")
        for k, t in enumerate(level.turns, 1):
            if t.who not in WHO:
                raise CurriculumError(f"{at} turn {k}: who must be one of {WHO}")
            if not t.say.strip():
                raise CurriculumError(f"{at} turn {k}: say is required")
            if t.who == "you" and (not t.cue.strip() or not t.items):
                raise CurriculumError(f"{at} turn {k}: a learner's turn needs a cue and items")
            if t.who == "partner" and (not t.meaning.strip() or t.items or t.cue):
                raise CurriculumError(f"{at} turn {k}: a partner's turn has a meaning, and no cue or items")
        for x in level.listen:
            if not x.say.strip() or not x.meaning.strip():
                raise CurriculumError(f"{at}: listen lines need say and meaning")


def load_themes(
    curriculum_dir: str | Path,
    cur: Curriculum | None = None,
    scenarios: list[Scenario] | None = None,
    reading: set[str] | None = None,
) -> list[Theme]:
    """Every theme in ``<curriculum>/cando/*.toml`` (none without the directory). With
    ``cur``, every item must exist; with ``scenarios``, every scenario id; with ``reading``
    (the deck's texts, casefolded), every ``read`` text."""
    out: list[Theme] = []
    for f, theme in load_records(Path(curriculum_dir) / "cando", "themes", Theme, "theme"):
        _check(theme, f"{f}: theme {theme.id!r}")
        out.append(theme)
    if cur is not None:
        check_items([(t.id, i) for t in out for lv in t.levels for i in lv.items], cur.by_id, "themes")
    if scenarios is not None:
        known = {s.id for s in scenarios}
        orphans = [t.id for t in out if t.scenario not in known]
        if orphans:
            raise CurriculumError(f"themes name unknown scenarios: {orphans}")
    if reading is not None:
        unread = [(t.id, r) for t in out for lv in t.levels for r in lv.read if r.casefold() not in reading]
        if unread:
            raise CurriculumError(f"themes name texts the reading deck lacks: {unread}")
    return out


def readiness(theme: Theme, met: set[str]) -> list[dict]:
    """Per level: the items still to meet before the learner can say every line."""
    return [{"level": n, "goal": lv.goal, "missing": [i for i in lv.items if i not in met]}
            for n, lv in enumerate(theme.levels, 1)]


def format_themes(themes: list[Theme], met: set[str] | None = None) -> str:
    """A readable catalogue: each theme, its levels and their exchange; with ``met``, what
    each level still needs."""
    lines: list[str] = []
    for t in themes:
        lines.append(f"{t.id} [{t.scenario}] {t.title}" + (f" — {t.title_ja}" if t.title_ja else ""))
        ready = readiness(t, met) if met is not None else None
        for n, lv in enumerate(t.levels, 1):
            todo = ready[n - 1]["missing"] if ready else []
            status = "" if ready is None else (" (ready)" if not todo else f" (needs {', '.join(todo)})")
            lines.append(f"  level {n}: {lv.goal}{status}")
            for turn in lv.turns:
                lines.append(f"    {'→' if turn.who == 'you' else '←'} {turn.say}")
    return "\n".join(lines)
