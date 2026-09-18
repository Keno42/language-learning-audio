"""Structured learning material: items, dialogues, curriculum.

Everything the planner works on is one of these objects. Nothing here knows
about audio, voices, or the learner — that keeps the curriculum reusable
across learners and TTS providers.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

KINDS = ("vocab", "phrase", "construction", "transform")

_SLOT_RE = re.compile(r"\{(\w+)\}")
_WORD_RE = re.compile(r"\w+", re.UNICODE)


@dataclass
class TransformExample:
    """One before/after pair for a grammatical transformation."""

    source: str
    source_meaning: str
    result: str
    result_meaning: str


@dataclass
class Item:
    id: str
    kind: str
    target: str
    meaning: str
    components: list[str] = field(default_factory=list)
    prereqs: list[str] = field(default_factory=list)
    difficulty: int = 2  # 1 (trivial) .. 5 (hard to say / remember)
    tags: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    situation: str | None = None  # known-language cue for situational recall
    alternatives: list[str] = field(default_factory=list)
    pronunciation_notes: str = ""
    chunks: list[str] | None = None  # backward-build chunks, shortest first
    slots: dict[str, str] = field(default_factory=dict)  # construction: slot -> required tag
    example: dict[str, str] = field(default_factory=dict)  # construction: slot -> item id
    instruction: str = ""  # transform: known-language instruction, e.g. "Make it negative:"
    examples: list[TransformExample] = field(default_factory=list)  # transform pairs
    order: int = 0

    # ---- derived helpers -------------------------------------------------

    @property
    def slot_names(self) -> list[str]:
        return _SLOT_RE.findall(self.target)

    @property
    def word_count(self) -> int:
        return len(_WORD_RE.findall(self.target))

    def is_hard(self) -> bool:
        """Should the introduction use backward construction?"""
        return bool(self.chunks) or self.difficulty >= 4 or self.word_count >= 5

    def backward_chunks(self) -> list[str]:
        """Progressively longer tails of the phrase, shortest first.

        Authors can override with ``chunks``; otherwise we split on words and
        grow from the end, skipping single trailing punctuation.
        """
        if self.chunks:
            return list(self.chunks)
        words = self.target.split()
        if len(words) <= 2:
            return [self.target]
        out = []
        # 1 word, 2 words, ... but cap at 4 partial steps before the full phrase
        steps = min(len(words) - 1, 4)
        for n in range(1, steps + 1):
            out.append(" ".join(words[-n:]))
        out.append(self.target)
        return out


@dataclass
class DialogueTurn:
    cue: str  # narrator instruction in the known language
    expect: str | None = None  # item id the learner should produce
    expect_text: str | None = None  # or a literal target-language line
    expect_meaning: str | None = None
    partner: str | None = None  # what the other speaker says after the learner
    partner_meaning: str | None = None
    opener: str | None = None  # partner line spoken *before* the learner's turn
    opener_meaning: str | None = None


@dataclass
class Dialogue:
    id: str
    setting: str  # narrator, known language
    turns: list[DialogueTurn]
    topics: list[str] = field(default_factory=list)
    partner_speaker: str = "native_b"
    requires: list[str] = field(default_factory=list)  # extra items the expect_text turns rely on

    @property
    def required_items(self) -> list[str]:
        out = [t.expect for t in self.turns if t.expect]
        for r in self.requires:
            if r not in out:
                out.append(r)
        return out


@dataclass
class Curriculum:
    name: str
    target_lang: str
    known_lang: str
    items: list[Item]
    dialogues: list[Dialogue]
    level: str = "A1"
    source: str = ""

    def __post_init__(self) -> None:
        self.by_id: dict[str, Item] = {i.id: i for i in self.items}
        self.dialogue_by_id: dict[str, Dialogue] = {d.id: d for d in self.dialogues}

    def item(self, item_id: str) -> Item:
        return self.by_id[item_id]

    def items_with_tag(self, tag: str) -> list[Item]:
        return [i for i in self.items if tag in i.tags]

    def resolve_slots(self, construction: Item, fills: dict[str, Item]) -> tuple[str, str]:
        """Return (target, meaning) with every slot filled from ``fills``."""
        target = construction.target
        meaning = construction.meaning
        for slot, item in fills.items():
            target = target.replace("{" + slot + "}", item.target.rstrip("."))
            meaning = meaning.replace("{" + slot + "}", item.meaning.rstrip("."))
        return target, meaning

    def example_fill(self, construction: Item) -> dict[str, Item]:
        """The author's example fill for a construction, or the first tagged item per slot."""
        fills: dict[str, Item] = {}
        for slot, tag in construction.slots.items():
            if slot in construction.example:
                fills[slot] = self.by_id[construction.example[slot]]
            else:
                candidates = self.items_with_tag(tag)
                if not candidates:
                    raise CurriculumError(f"construction {construction.id!r}: no items tagged {tag!r} for slot {slot!r}")
                fills[slot] = candidates[0]
        return fills

    def topics(self) -> list[str]:
        seen: dict[str, None] = {}
        for i in self.items:
            for t in i.topics:
                seen.setdefault(t, None)
        return list(seen)


class CurriculumError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_curriculum(path: str | Path) -> Curriculum:
    path = Path(path)
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    return curriculum_from_dict(raw, source=str(path))


def curriculum_from_dict(raw: dict, source: str = "") -> Curriculum:
    meta = raw.get("curriculum", {})
    for key in ("name", "target_lang", "known_lang"):
        if key not in meta:
            raise CurriculumError(f"[curriculum] is missing {key!r}")

    items: list[Item] = []
    for order, entry in enumerate(raw.get("items", [])):
        items.append(_item_from_dict(entry, order))

    dialogues: list[Dialogue] = []
    for entry in raw.get("dialogues", []):
        turns = [DialogueTurn(**t) for t in entry.get("turns", [])]
        dialogues.append(
            Dialogue(
                id=entry["id"],
                setting=entry["setting"],
                turns=turns,
                topics=list(entry.get("topics", [])),
                partner_speaker=entry.get("partner_speaker", "native_b"),
                requires=list(entry.get("requires", [])),
            )
        )

    cur = Curriculum(
        name=meta["name"],
        target_lang=meta["target_lang"],
        known_lang=meta["known_lang"],
        level=meta.get("level", "A1"),
        items=items,
        dialogues=dialogues,
        source=source,
    )
    validate(cur)
    return cur


def _item_from_dict(entry: dict, order: int) -> Item:
    entry = dict(entry)
    examples = [TransformExample(**e) for e in entry.pop("examples", [])]
    kind = entry.get("kind", "phrase")
    if kind not in KINDS:
        raise CurriculumError(f"item {entry.get('id')!r}: unknown kind {kind!r} (expected one of {KINDS})")
    known_fields = set(Item.__dataclass_fields__)
    unknown = set(entry) - known_fields
    if unknown:
        raise CurriculumError(f"item {entry.get('id')!r}: unknown fields {sorted(unknown)}")
    return Item(order=order, examples=examples, **entry)


def validate(cur: Curriculum) -> None:
    ids = set()
    for it in cur.items:
        if it.id in ids:
            raise CurriculumError(f"duplicate item id {it.id!r}")
        ids.add(it.id)
    for it in cur.items:
        for ref in it.components + it.prereqs:
            if ref not in ids:
                raise CurriculumError(f"item {it.id!r} references unknown item {ref!r}")
        if it.kind == "construction":
            slots = it.slot_names
            if not slots:
                raise CurriculumError(f"construction {it.id!r} has no {{slot}} in its target")
            for s in slots:
                if s not in it.slots:
                    raise CurriculumError(f"construction {it.id!r}: slot {s!r} has no tag in [slots]")
                if "{" + s + "}" not in it.meaning:
                    raise CurriculumError(f"construction {it.id!r}: meaning must also contain {{{s}}}")
                if not cur.items_with_tag(it.slots[s]):
                    raise CurriculumError(f"construction {it.id!r}: no item carries tag {it.slots[s]!r}")
            for s, ref in it.example.items():
                if ref not in ids:
                    raise CurriculumError(f"construction {it.id!r}: example fill {ref!r} unknown")
        elif it.slot_names:
            raise CurriculumError(f"item {it.id!r} has {{slots}} but kind is {it.kind!r}, not construction")
        if it.kind == "transform" and len(it.examples) < 2:
            raise CurriculumError(f"transform {it.id!r} needs at least two examples")
    for d in cur.dialogues:
        for t in d.turns:
            if t.expect and t.expect not in ids:
                raise CurriculumError(f"dialogue {d.id!r} expects unknown item {t.expect!r}")
        for r in d.requires:
            if r not in ids:
                raise CurriculumError(f"dialogue {d.id!r} requires unknown item {r!r}")
            if not t.expect and not t.expect_text:
                raise CurriculumError(f"dialogue {d.id!r}: each turn needs expect or expect_text")
            if t.expect_text and not t.expect_meaning:
                raise CurriculumError(f"dialogue {d.id!r}: expect_text needs expect_meaning")
