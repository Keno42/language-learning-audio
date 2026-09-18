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
class Note:
    """A short cultural aside in the learner's language, spoken by the instructor.

    Notes are passive content, so the planner rations them (a couple per lesson)
    and prefers to place one right after an exercise on one of its ``items``.
    """

    id: str
    text: str
    items: list[str] = field(default_factory=list)  # related item ids
    topics: list[str] = field(default_factory=list)


@dataclass
class Curriculum:
    name: str
    target_lang: str
    known_lang: str
    items: list[Item]
    dialogues: list[Dialogue]
    level: str = "A1"
    source: str = ""
    notes: list[Note] = field(default_factory=list)
    known_langs: list[str] = field(default_factory=list)  # languages the file carries glosses for
    missing_glosses: list[str] = field(default_factory=list)  # ids without a gloss in the requested known_lang

    def __post_init__(self) -> None:
        self.by_id: dict[str, Item] = {i.id: i for i in self.items}
        self.dialogue_by_id: dict[str, Dialogue] = {d.id: d for d in self.dialogues}
        self.note_by_id: dict[str, Note] = {n.id: n for n in self.notes}

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


def load_curriculum(path: str | Path, known_lang: str | None = None) -> Curriculum:
    """Load one .toml file, or a directory of them (merged in sorted filename order).

    In a directory, exactly one file carries ``[curriculum]``; ``[[items]]`` and
    ``[[dialogues]]`` from every file are concatenated, so a course can be split
    into topic modules (``01-greetings.toml``, ``02-cafe.toml`` …).

    ``known_lang`` selects the learner's language when a file carries glosses for
    several (``meaning_ja``, ``situation_ja``, ``cue_ja`` … next to the primary
    ``meaning``). Items without a gloss in that language are listed in
    ``Curriculum.missing_glosses`` and fall back to the primary text.
    """
    path = Path(path)
    if path.is_dir():
        files = sorted(path.glob("*.toml"))
        if not files:
            raise CurriculumError(f"{path}: no .toml files")
        merged: dict = {"items": [], "dialogues": [], "notes": []}
        for f in files:
            with f.open("rb") as fh:
                raw = tomllib.load(fh)
            if "curriculum" in raw:
                if "curriculum" in merged:
                    raise CurriculumError(f"{f}: [curriculum] is already defined in another file")
                merged["curriculum"] = raw["curriculum"]
            merged["items"] += raw.get("items", [])
            merged["dialogues"] += raw.get("dialogues", [])
            merged["notes"] += raw.get("notes", [])
        if "curriculum" not in merged:
            raise CurriculumError(f"{path}: no file defines [curriculum]")
        return curriculum_from_dict(merged, source=str(path), known_lang=known_lang)
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    return curriculum_from_dict(raw, source=str(path), known_lang=known_lang)


# fields that may carry per-language glosses (``<field>_<lang>``)
_GLOSSED_ITEM = ("meaning", "situation", "instruction")
_GLOSSED_EXAMPLE = ("source_meaning", "result_meaning")
_GLOSSED_TURN = ("cue", "opener_meaning", "partner_meaning", "expect_meaning")
_GLOSSED_DIALOGUE = ("setting",)
_GLOSSED_NOTE = ("text",)
_GLOSSED_META = ("name",)


def _pick_gloss(entry: dict, fields: tuple[str, ...], lang: str | None, langs: list[str], missing: list[str], label: str) -> dict:
    """Return a copy of ``entry`` with ``<field>_<lang>`` promoted to ``<field>`` and all other
    ``<field>_<xx>`` keys dropped. Records which languages appear and what is missing."""
    out = dict(entry)
    for f in fields:
        for key in list(out):
            if key.startswith(f + "_") and key[len(f) + 1 :].isalpha() and len(key) - len(f) - 1 <= 3:
                lang_code = key[len(f) + 1 :]
                if lang_code not in langs:
                    langs.append(lang_code)
                val = out.pop(key)
                if lang and lang_code == lang:
                    out[f] = val
        if lang and f in entry and (f + "_" + lang) not in entry:
            missing.append(f"{label}.{f}")
    return out


def curriculum_from_dict(raw: dict, source: str = "", known_lang: str | None = None) -> Curriculum:
    meta = raw.get("curriculum", {})
    for key in ("name", "target_lang", "known_lang"):
        if key not in meta:
            raise CurriculumError(f"[curriculum] is missing {key!r}")
    lang = None if known_lang in (None, meta["known_lang"]) else known_lang
    langs: list[str] = [meta["known_lang"]]
    missing: list[str] = []
    meta = _pick_gloss(meta, _GLOSSED_META, lang, langs, missing, "curriculum")

    items: list[Item] = []
    for order, entry in enumerate(raw.get("items", [])):
        label = entry.get("id", f"item#{order}")
        entry = _pick_gloss(entry, _GLOSSED_ITEM, lang, langs, missing, label)
        if "examples" in entry:
            entry["examples"] = [_pick_gloss(e, _GLOSSED_EXAMPLE, lang, langs, missing, f"{label}.examples") for e in entry["examples"]]
        items.append(_item_from_dict(entry, order))

    dialogues: list[Dialogue] = []
    for entry in raw.get("dialogues", []):
        label = entry.get("id", "dialogue")
        entry = _pick_gloss(entry, _GLOSSED_DIALOGUE, lang, langs, missing, label)
        turns = [DialogueTurn(**_pick_gloss(t, _GLOSSED_TURN, lang, langs, missing, f"{label}.turn")) for t in entry.get("turns", [])]
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

    notes = [Note(**_pick_gloss(n, _GLOSSED_NOTE, lang, langs, missing, n.get("id", "note"))) for n in raw.get("notes", [])]

    cur = Curriculum(
        name=meta["name"],
        target_lang=meta["target_lang"],
        known_lang=known_lang or meta["known_lang"],
        level=meta.get("level", "A1"),
        items=items,
        dialogues=dialogues,
        source=source,
        notes=notes,
        known_langs=langs,
        missing_glosses=missing,
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
    targets: dict[str, str] = {}
    for it in cur.items:
        if it.id in ids:
            raise CurriculumError(f"duplicate item id {it.id!r}")
        ids.add(it.id)
        key = it.target.strip().lower()
        if key in targets:
            raise CurriculumError(f"items {targets[key]!r} and {it.id!r} have the same target {it.target!r}")
        targets[key] = it.id
    for d in cur.dialogues:
        if d.id in {x.id for x in cur.dialogues if x is not d}:
            raise CurriculumError(f"duplicate dialogue id {d.id!r}")
    seen_notes: set[str] = set()
    for n in cur.notes:
        if n.id in seen_notes:
            raise CurriculumError(f"duplicate note id {n.id!r}")
        seen_notes.add(n.id)
        for ref in n.items:
            if ref not in ids:
                raise CurriculumError(f"note {n.id!r} references unknown item {ref!r}")
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
