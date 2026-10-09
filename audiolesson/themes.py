"""Lesson themes (issue #149, step 1b-ii): one scene of a trip as a short exchange, at rising levels.

A theme is what a lesson consolidates instead of a word count: a scene with a goal (ordering at
a café, paying at the supermarket) and, per level, the exchange that reaches it. Level 1 is the
shortest exchange that works; later levels raise its resolution (a question back, paying, a
receipt). The lesson plays the theme's exchange twice (``Planner.pick_theme``, ``play_theme``):
once early with the partner's lines translated, and once late without the translation. Only the
translation fades: the cue (the intent) and the scene line play every time (#210).

Themes live in ``<curriculum>/cando/themes.toml`` (``load_cando`` reads only ``[[scenarios]]``
and ``load_scenes`` only ``[[scenes]]``, so they share the directory)::

    [[themes]]
    id = "cafe"
    scenario = "A4"                 # the can-do scenario it serves
    title = "Café"
    title_ja = "カフェ"
    setting = "A busy café: order at the counter."
    setting_ja = "混んだカフェ。"
    topics = ["cafe"]

    [[themes.levels]]
    goal = "Order a coffee and answer the milk question."
    goal_ja = "コーヒーを注文し、ミルクがいるかに答える。"
    turns = [
      { who = "partner", say = "Hæ! Hvað má bjóða þér?", meaning = "Hi! What can I get you?", meaning_ja = "…" },
      { who = "you", cue = "Order a coffee.", cue_ja = "…", say = "Ég ætla að fá kaffi.", items = ["eg_aetla_ad_fa", "kaffi"], alts = ["Kaffi, takk."] },
      …
    ]

- A ``you`` turn is the learner's line: a ``cue`` (the intent, in the learner's language; always played),
  ``say`` (the model line), ``items`` (the curriculum items it needs) and optional ``alts``
  (other good answers; they wait for the review side, which asks ``say`` only). The cue plays in every
  play (#210), for every turn: no turn of an exchange that goes on drops it, since the partner's line never
  decides the reply.
- A partner turn can carry ``scene`` / ``scene_ja``: a line the narrator says every time before the partner's line
  («At the till.»), where the setting changes. (A learner's turn has its cue for that; a scene on one fails validation.)
- A ``partner`` turn is what the other person says, with its meaning. It may go beyond the
  course: a learner who gets the gist of 80-90% of what is said is where they should be. It is spoken at
  natural speed, and may carry ``variants = [{ say, meaning, meaning_ja }, ...]``: other ways a real
  clerk puts the same thing (#134). The early (translated) play picks a variant per turn; the late play
  says the lines as written, so the learner meets the variation with its meaning and the canonical line every lesson;
  the transcript and plan.json say which was used. Every variant
  must fit the learner's reply that follows: it asks the same thing.
- A level is ready once every item of its ``you`` turns can be said (met, not open).

General content only: no learner's dates, itinerary or lodging (the private trip profile, #132,
decides which scenarios come first).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from .cando import Scenario
from .content import SPEAKERS, Curriculum, CurriculumError, Dialogue, DialogueTurn, unmarked_japanese
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
    scene: str = ""  # a line the narrator says before this turn, every play (#210)
    scene_ja: str = ""
    variants: list[dict] = field(default_factory=list)  # a partner turn: other ways to say it, each {say, meaning, meaning_ja} (#134)
    # a partner line: the meaning of a word in it the learner may not know, per known language {word: {en, ja}} (#248). Authored, never
    # guessed from the line's translation: it is what «One word was new» answers.
    word_glosses: dict[str, dict[str, str]] = field(default_factory=dict)

    def lines(self) -> list[Turn]:
        """The partner's line and its variants, the line as written first: any of them fits the learner's reply."""
        return [self] + [
            Turn("partner", v.get("say", ""), meaning=v.get("meaning", ""), meaning_ja=v.get("meaning_ja", ""), word_glosses=v.get("word_glosses", {}))
            for v in self.variants
        ]


@dataclass
class Level:
    goal: str
    goal_ja: str = ""
    partner_speaker: str = "native_b"  # "native_a" is voiced female, "native_b" male: the partner's, when the cues say «her»
    turns: list[Turn] = field(default_factory=list)

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
                levels.append(Level(turns=turns, **raw))
            except TypeError as e:
                raise CurriculumError(f"theme {self.id!r} level {n}: {e}") from None
        self.levels = levels


def load_themes(curriculum_dir: str | Path, cur: Curriculum | None = None, scenarios: list[Scenario] | None = None) -> list[Theme]:
    """Every theme in ``<curriculum>/cando/*.toml`` (none without the directory). With ``cur``, every item
    id must exist in it; with ``scenarios``, every theme's scenario must."""
    out = [t for _, t in load_records(Path(curriculum_dir) / "cando", "themes", Theme, "theme")]
    for theme in out:
        _check(theme)
    if cur is not None:
        check_items([(t.id, i) for t in out for lv in t.levels for i in lv.items], cur.by_id, "themes")
    if scenarios is not None:
        known = {s.id for s in scenarios}
        bad = [(t.id, t.scenario) for t in out if t.scenario not in known]
        if bad:
            raise CurriculumError(f"themes name unknown can-do scenarios: {bad}")
    return out


def _check(theme: Theme) -> None:
    if not theme.levels:
        raise CurriculumError(f"theme {theme.id!r}: no levels")
    for w in unmarked_japanese(theme.setting):
        raise CurriculumError(f"theme {theme.id!r}: setting: romanized Japanese read by the English voice (only a note can mark it «ja:…»; reword): {w!r}")
    for n, lv in enumerate(theme.levels, 1):
        where = f"theme {theme.id!r} level {n}"
        if not lv.goal:
            raise CurriculumError(f"{where}: no goal")
        if lv.partner_speaker not in SPEAKERS:
            raise CurriculumError(f"{where}: partner_speaker must be one of {SPEAKERS}, not {lv.partner_speaker!r}")
        if not any(t.who == "you" for t in lv.turns):
            raise CurriculumError(f"{where}: no turn for the learner")
        for k, t in enumerate(lv.turns, 1):
            if t.who not in WHO:
                raise CurriculumError(f"{where} turn {k}: who must be one of {WHO}")
            if not t.say:
                raise CurriculumError(f"{where} turn {k}: no line")
            for w in unmarked_japanese(t.meaning):
                raise CurriculumError(f"{where} turn {k}: meaning: romanized Japanese read by the English voice (only a note can mark it «ja:…»; reword): {w!r}")
            for w in unmarked_japanese(t.cue):
                raise CurriculumError(f"{where} turn {k}: cue: romanized Japanese read by the English voice (only a note can mark it «ja:…»; reword): {w!r}")
            if t.who == "you" and not (t.cue.strip() and t.items):
                raise CurriculumError(f"{where} turn {k}: a learner's line needs a cue (the intent, played every time) and the items it needs")
            if t.scene and t.who != "partner":
                raise CurriculumError(f"{where} turn {k}: a scene goes on a partner's line (a learner's turn has its cue)")
            for w in unmarked_japanese(t.scene):
                raise CurriculumError(f"{where} turn {k}: scene: romanized Japanese read by the English voice (only a note can mark it «ja:…»; reword): {w!r}")
            if t.who == "partner" and not t.meaning:
                raise CurriculumError(f"{where} turn {k}: a partner's line needs its meaning")
            if t.variants and t.who != "partner":
                raise CurriculumError(f"{where} turn {k}: only a partner's line has variants")
            for v in t.variants:
                if not (isinstance(v, dict) and v.get("say") and v.get("meaning")) or set(v) - {"say", "meaning", "meaning_ja", "word_glosses"}:
                    raise CurriculumError(f"{where} turn {k}: a variant is {{ say, meaning, meaning_ja, word_glosses }}, with the line and its meaning")
            if t.word_glosses and t.who != "partner":
                raise CurriculumError(f"{where} turn {k}: word glosses go on a partner's line")
            for line in t.lines():
                words = {w.lower() for w in re.findall(r"[^\W\d_]+", line.say)}
                for word, gloss in line.word_glosses.items():
                    if word.lower() not in words:
                        raise CurriculumError(f"{where} turn {k}: word gloss {word!r} is not a word of {line.say!r}")
                    if not isinstance(gloss, dict) or {"en", "ja"} - set(gloss) or not all(isinstance(g, str) and g.strip() for g in gloss.values()):
                        raise CurriculumError(f"{where} turn {k}: word gloss {word!r} needs a non-empty meaning in en and ja")
            if len({x.say for x in t.lines()}) < len(t.lines()):
                raise CurriculumError(f"{where} turn {k}: a variant repeats a line")


def scenario_order(scenarios: list[Scenario], boost: list[str] | tuple[str, ...] = (), tiers: tuple[str, ...] = ("A", "B")) -> list[str]:
    """The scenarios a lesson's theme is taken from, in order: the trip profile's boosted ones first, then each
    tier in ``tiers`` in file order."""
    by_id = {s.id: s for s in scenarios}
    out = [sid for sid in boost if sid in by_id]
    for tier in tiers:
        out += [s.id for s in scenarios if s.tier == tier and s.id not in out]
    return out


def pick_variants(level: Level, rng: random.Random, canonical: bool = False, heard: set[tuple[int, int]] | None = None) -> dict[int, int]:
    """Which line each partner turn with variants says (index into ``Turn.lines()``, keyed by the turn's place in the
    level). The lesson's two plays split the work (#134, review): the early, translated play takes a variant at random,
    heard with its meaning; the late one (``canonical``) says every line as written, the familiar cue when only the
    partner's line is given, and the wording the review cards ask. A replay passes ``heard`` (turn, line) pairs already
    heard with their meaning: its early play takes only those, so no wording comes untranslated (#196).
    A heard-only play (spare time, #218 b1) takes any variant, untranslated, with neither ``canonical`` nor ``heard``: natural-speed
    exposure to wordings in a familiar scene, on purpose (H8; the owner's decision on the review of #233), unlike a replay's early play."""
    if canonical:
        return {}
    if heard is not None:
        picks = {}
        for k, t in enumerate(level.turns):
            if t.who == "partner" and t.variants:
                known = sorted(i for (turn, i) in heard if turn == k)
                if known:
                    picks[k] = rng.choice(known)
        return picks
    return {k: rng.randrange(1, len(t.lines())) for k, t in enumerate(level.turns) if t.who == "partner" and t.variants}


def variant_label(level: Level, picks: dict[int, int]) -> str:
    """The picks as the transcript and plan.json name them: the 1-based line (1 = as written) of each varying turn."""
    return ",".join(str(picks.get(k, 0) + 1) for k, t in enumerate(level.turns) if t.who == "partner" and t.variants)


def level_dialogue(theme: Theme, n: int, known_lang: str = "en", picks: dict[int, int] | None = None) -> Dialogue:
    """Level ``n`` (0-based) as a dialogue the builder can play: a partner line before the learner's first turn
    is its opener, one after a learner's turn is the reply to it; the learner's lines are literal
    (``expect_text``), since a line may be built from several items. A partner turn's scene line is narrated
    before its line, whichever of the two places it lands in (the opener of the next turn, or the previous
    turn's partner reply)."""
    ja = known_lang == "ja"
    level = theme.levels[n]
    turns: list[DialogueTurn] = []
    opener: tuple[str, str] | None = None
    opener_scene = ""
    for k, t in enumerate(level.turns):
        scene = t.scene_ja if ja and t.scene_ja else t.scene
        if t.who == "partner":
            t = t.lines()[(picks or {}).get(k, 0)]
        meaning = (t.meaning_ja if ja and t.meaning_ja else t.meaning)
        if t.who == "partner":
            if turns and turns[-1].partner is None:
                turns[-1].partner, turns[-1].partner_meaning, turns[-1].partner_scene = t.say, meaning, scene
            else:
                opener, opener_scene = (t.say, meaning), scene
            continue
        turn = DialogueTurn(cue=(t.cue_ja if ja and t.cue_ja else t.cue), expect_text=t.say)
        if opener is not None:
            turn.opener, turn.opener_meaning, turn.scene = opener[0], opener[1], opener_scene
            opener, opener_scene = None, ""
        turns.append(turn)
    setting = theme.setting_ja if ja and theme.setting_ja else theme.setting
    return Dialogue(
        id=f"theme:{theme.id}:{n + 1}",
        setting=setting or theme.title,
        turns=turns,
        topics=list(theme.topics),
        partner_speaker=level.partner_speaker,
        variant=variant_label(level, picks or {}),
    )
