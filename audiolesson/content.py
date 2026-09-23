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
GENDERS = ("masc", "fem", "neut")

_SLOT_RE = re.compile(r"\{(\w+)\}")
# ``{slot:form}`` in a construction's meaning asks for the fill's ``meaning_forms[form]``:
# "I'm {inf:ing}." → "I'm going home."
_FORM_SLOT_RE = re.compile(r"\{(\w+):(\w+)\}")
_WORD_RE = re.compile(r"\w+", re.UNICODE)

# «...» in a note's text is spoken by the target-language voice, not narrated.
NOTE_TARGET_RE = re.compile(r"«([^»]+)»")

# A «...» span may start with a language code for a third language («ja:sate»), and may split
# display text from what the TTS provider receives («ja:sate|さて»), so pronunciation never
# depends on a provider reading a romanization correctly.
NOTE_LANG_PREFIX_RE = re.compile(r"^([a-z]{2,3}):\s*(.+)$", re.DOTALL)


def split_note_span(span: str) -> tuple[str | None, str, str]:
    """Split a «...» span into (language code or None, display text, speech text).

    ``"Halló"`` → ``(None, "Halló", "Halló")``; ``"ja:onigiri"`` → ``("ja", "onigiri",
    "onigiri")``; ``"ja:sate|さて"`` → ``("ja", "sate", "さて")``.
    """
    m = NOTE_LANG_PREFIX_RE.match(span)
    if not m:
        return (None, span, span)
    lang, rest = m.group(1), m.group(2)
    display, _, speech = rest.partition("|")
    return (lang, display, speech or display)

# A run of vowels approximates one syllable. Used only to judge whether a single word is long
# enough for extra practice (``Item.is_hard``), never to split it.
_VOWEL_RUN_RE = re.compile(r"[aáàâäæeéèêëiíîïoóôöœuúùûüyýÿ]+", re.IGNORECASE)


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
    # alternative cues, rotated on repeat retrieval; override ``situation`` when non-empty
    situations: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    pronunciation_notes: str = ""
    chunks: list[str] | None = None  # backward-build chunks, shortest first
    slots: dict[str, str] = field(default_factory=dict)  # construction: slot -> required tag
    example: dict[str, str] = field(default_factory=dict)  # construction: slot -> item id
    # construction: slot -> the fill its situation names ("Ask if she speaks English." only fits
    # «Talar þú ensku?»). Exercises that narrate the situation use it; others generate freely.
    situation_fill: dict[str, str] = field(default_factory=dict)
    # slot filler: other known-language renderings of ``meaning`` ("go home" / "going home"),
    # requested by a construction's ``{slot:form}``; the target-language fill never changes.
    # ``in_sentence`` replaces ``meaning`` for a plain ``{slot}``, so a recall disambiguator
    # ("English (the language)") stays out of sentence prompts.
    meaning_forms: dict[str, str] = field(default_factory=dict)
    instruction: str = ""  # transform: known-language instruction, e.g. "Make it negative:"
    examples: list[TransformExample] = field(default_factory=list)  # transform pairs
    order: int = 0
    gender: str | None = None  # noun's grammatical gender ("masc" | "fem" | "neut"), for agreement
    # construction: {slot} -> {"from": controlling slot, <gender>: surface form, ...}. Never
    # filled by picking an item; its text follows the gender of the ``from`` slot's fill, so
    # "{adj} {noun}." generates «Góður bíll.» / «Góð bók.» / «Gott hús.».
    agreement: dict[str, dict[str, str]] = field(default_factory=dict)
    # An authored bridge: the partner line spoken after item ``partner_cue_after`` and before
    # this item, so "A → partner_cue → this" reads as one real exchange. Set both or neither.
    partner_cue: str = ""
    partner_cue_after: str = ""
    # The bridge's scene, required with ``partner_cue``: ``setup`` replaces A's situation,
    # ``meaning`` says what the partner said (narrated only on the first encounters, see
    # LearnerState.bridges_heard), ``situation`` replaces this item's situation.
    partner_cue_setup: str = ""
    partner_cue_meaning: str = ""
    partner_cue_situation: str = ""

    # ---- derived helpers -------------------------------------------------

    @property
    def slot_names(self) -> list[str]:
        return _SLOT_RE.findall(self.target)

    @property
    def word_count(self) -> int:
        return len(_WORD_RE.findall(self.target))

    @property
    def has_situation(self) -> bool:
        return bool(self.situations or self.situation)

    def situation_for(self, exposures: int) -> str | None:
        """The situation cue for this exposure: ``situations`` round-robin, else ``situation``."""
        if self.situations:
            return self.situations[exposures % len(self.situations)]
        return self.situation

    def is_hard(self) -> bool:
        """Should the introduction use backward construction?"""
        if self.chunks or self.difficulty >= 4 or self.word_count >= 5:
            return True
        # a single long word (3+ syllable-ish vowel runs) is just as hard to hold in memory
        # as a multi-word phrase, even though word_count alone can't see that
        return self.word_count == 1 and len(_VOWEL_RUN_RE.findall(self.target)) >= 3

    def backward_chunks(self) -> list[str]:
        """Progressively longer tails of the phrase, shortest first ("vel" / "svo vel" /
        "Gjörðu svo vel"), or the authored ``chunks``.

        Splits on words only. A single word is never cut into syllables: a guessed boundary
        can be wrong, and TTS mispronounces fragments out of context.
        """
        if self.chunks:
            return list(self.chunks)
        words = self.target.split()
        if len(words) <= 2:
            return [self.target]
        # 1 word, 2 words, ... but cap at 4 partial steps before the full phrase
        steps = min(len(words) - 1, 4)
        out = [" ".join(words[-n:]) for n in range(1, steps + 1)]
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
    # when ``expect`` is a construction: slot -> item id for every slot, so the learner
    # generates e.g. «Það kostar fimm þúsund krónur.» mid-exchange. The fills count as
    # required items.
    expect_fill: dict[str, str] = field(default_factory=dict)


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
        for t in self.turns:
            out += [f for f in t.expect_fill.values() if f not in out]
        for r in self.requires:
            if r not in out:
                out.append(r)
        return out


@dataclass
class Note:
    """A short aside in the learner's language, spoken by the instructor.

    Asides are rationed and placed right after an exercise on one of ``items``.
    A ``milestone`` note names a grammatical pattern: it fires as soon as every one of
    ``items`` has been met, is never used as filler, and is followed by discrimination
    practice. ``«...»`` spans in ``text`` are spoken by the target-language voice.
    """

    id: str
    text: str
    items: list[str] = field(default_factory=list)  # related item ids; they trigger the note
    topics: list[str] = field(default_factory=list)
    milestone: bool = False
    # items a milestone's discrimination practice may use once known; never needed to fire
    transfer_items: list[str] = field(default_factory=list)
    # items the note recommends the learner say: it waits until each is learned or was
    # introduced earlier in the lesson. Mere illustrations need no entry.
    requires: list[str] = field(default_factory=list)


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
        """Return (target, meaning) with every slot filled from ``fills``; agreement
        placeholders resolve first, from the gender of their ``from`` slot's fill."""
        target = construction.target
        meaning = construction.meaning
        for slot, rule in construction.agreement.items():
            gender = fills[rule["from"]].gender
            target = target.replace("{" + slot + "}", rule[gender])
        for slot, item in fills.items():
            target = target.replace("{" + slot + "}", item.target.rstrip("."))
            meaning = meaning.replace("{" + slot + "}", item.meaning_forms.get("in_sentence", item.meaning).rstrip("."))
            meaning = _FORM_SLOT_RE.sub(
                lambda m: item.meaning_forms.get(m.group(2), item.meaning).rstrip(".") if m.group(1) == slot else m.group(0), meaning
            )
        # a sentence that opens with a slot ("{thing} virkar ekki.") still starts with a capital
        if construction.target.startswith("{"):
            target = target[:1].upper() + target[1:]
        if construction.meaning.startswith("{"):
            meaning = meaning[:1].upper() + meaning[1:]
        return target, meaning

    def situation_fills(self, construction: Item) -> dict[str, Item]:
        """The fills a construction's authored situation is bound to, by slot."""
        return {slot: self.by_id[ref] for slot, ref in construction.situation_fill.items()}

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
_GLOSSED_ITEM = ("meaning", "situation", "situations", "instruction", "meaning_forms", "partner_cue_setup", "partner_cue_meaning", "partner_cue_situation")
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
        if it.gender is not None and it.gender not in GENDERS:
            raise CurriculumError(f"item {it.id!r}: gender {it.gender!r} must be one of {sorted(GENDERS)}")
    for d in cur.dialogues:
        if d.id in {x.id for x in cur.dialogues if x is not d}:
            raise CurriculumError(f"duplicate dialogue id {d.id!r}")
    seen_notes: set[str] = set()
    for n in cur.notes:
        if n.id in seen_notes:
            raise CurriculumError(f"duplicate note id {n.id!r}")
        seen_notes.add(n.id)
        for ref in n.items + n.transfer_items + n.requires:
            if ref not in ids:
                raise CurriculumError(f"note {n.id!r} references unknown item {ref!r}")
        # strip matched pairs; any « or » left over is malformed ("»foo«", "«a» «b")
        unmatched = NOTE_TARGET_RE.sub("", n.text)
        if "«" in unmatched or "»" in unmatched:
            raise CurriculumError(f"note {n.id!r} has malformed or unmatched «» markers")
    for it in cur.items:
        for ref in it.components + it.prereqs:
            if ref not in ids:
                raise CurriculumError(f"item {it.id!r} references unknown item {ref!r}")
        if bool(it.partner_cue) != bool(it.partner_cue_after):
            raise CurriculumError(f"item {it.id!r}: partner_cue and partner_cue_after must be set together, or not at all")
        if it.partner_cue_after and it.partner_cue_after not in ids:
            raise CurriculumError(f"item {it.id!r}: partner_cue_after references unknown item {it.partner_cue_after!r}")
        scene = {"partner_cue_setup": it.partner_cue_setup, "partner_cue_meaning": it.partner_cue_meaning, "partner_cue_situation": it.partner_cue_situation}
        if it.partner_cue and not all(scene.values()):
            missing = [k for k, v in scene.items() if not v]
            raise CurriculumError(f"item {it.id!r}: a partner_cue bridge needs its whole scene — missing {missing}")
        if not it.partner_cue and any(scene.values()):
            raise CurriculumError(f"item {it.id!r}: partner_cue_setup/meaning/situation without a partner_cue")
        if it.kind == "construction":
            slots = it.slot_names
            if not slots:
                raise CurriculumError(f"construction {it.id!r} has no {{slot}} in its target")
            for s in slots:
                if s in it.agreement:
                    # not a picked fill: its controlling slot must be able to drive it instead
                    rule = it.agreement[s]
                    controller = rule.get("from")
                    if not controller:
                        raise CurriculumError(f"construction {it.id!r}: agreement for {{{s}}} needs a 'from' slot")
                    if controller not in it.slots:
                        raise CurriculumError(f"construction {it.id!r}: agreement for {{{s}}} names unknown controlling slot {controller!r}")
                    candidates = cur.items_with_tag(it.slots[controller])
                    ungendered = [c.id for c in candidates if c.gender is None]
                    if ungendered:
                        raise CurriculumError(f"construction {it.id!r}: agreement controller slot {controller!r} has ungendered candidates {ungendered}")
                    forms = {k: v for k, v in rule.items() if k != "from"}
                    missing = {c.gender for c in candidates} - set(forms)
                    if missing:
                        raise CurriculumError(f"construction {it.id!r}: agreement for {{{s}}} is missing forms for {sorted(missing)}")
                    continue
                if s not in it.slots:
                    raise CurriculumError(f"construction {it.id!r}: slot {s!r} has no tag in [slots]")
                forms = [f for slot, f in _FORM_SLOT_RE.findall(it.meaning) if slot == s]
                if "{" + s + "}" not in it.meaning and not forms:
                    raise CurriculumError(f"construction {it.id!r}: meaning must also contain {{{s}}}")
                for form in forms:
                    lacking = [c.id for c in cur.items_with_tag(it.slots[s]) if form not in c.meaning_forms]
                    if lacking:
                        raise CurriculumError(f"construction {it.id!r}: {{{s}:{form}}} needs meaning_forms.{form} on {lacking}")
                if not cur.items_with_tag(it.slots[s]):
                    raise CurriculumError(f"construction {it.id!r}: no item carries tag {it.slots[s]!r}")
            for s, ref in it.example.items():
                if ref not in ids:
                    raise CurriculumError(f"construction {it.id!r}: example fill {ref!r} unknown")
            if it.situation_fill and not it.has_situation:
                raise CurriculumError(f"construction {it.id!r}: situation_fill without a situation")
            for s, ref in it.situation_fill.items():
                if s not in it.slots:
                    raise CurriculumError(f"construction {it.id!r}: situation_fill names unknown slot {s!r}")
                if ref not in ids:
                    raise CurriculumError(f"construction {it.id!r}: situation_fill {s!r} references unknown item {ref!r}")
                if it.slots[s] not in cur.by_id[ref].tags:
                    raise CurriculumError(f"construction {it.id!r}: situation_fill {ref!r} is not a valid fill for slot {s!r} (needs tag {it.slots[s]!r})")
        elif it.situation_fill:
            raise CurriculumError(f"item {it.id!r}: situation_fill is only for constructions")
        elif it.slot_names:
            raise CurriculumError(f"item {it.id!r} has {{slots}} but kind is {it.kind!r}, not construction")
        if it.kind == "transform" and len(it.examples) < 2:
            raise CurriculumError(f"transform {it.id!r} needs at least two examples")
    for d in cur.dialogues:
        for t in d.turns:
            if not t.expect and not t.expect_text:
                raise CurriculumError(f"dialogue {d.id!r}: each turn needs expect or expect_text")
            if t.expect_text and not t.expect_meaning:
                raise CurriculumError(f"dialogue {d.id!r}: expect_text needs expect_meaning")
            if t.expect and t.expect not in ids:
                raise CurriculumError(f"dialogue {d.id!r} expects unknown item {t.expect!r}")
            c = cur.by_id.get(t.expect) if t.expect else None
            if t.expect_fill:
                if c is None or c.kind != "construction":
                    raise CurriculumError(f"dialogue {d.id!r}: expect_fill needs a construction as expect")
                for s, ref in t.expect_fill.items():
                    if s not in c.slots:
                        raise CurriculumError(f"dialogue {d.id!r}: expect_fill names unknown slot {s!r} of {c.id!r}")
                    if ref not in ids or c.slots[s] not in cur.by_id[ref].tags:
                        raise CurriculumError(f"dialogue {d.id!r}: expect_fill {ref!r} is not a valid fill for {c.id!r}'s slot {s!r}")
            if c is not None and c.kind == "construction":
                # every spoken part must be a required item, so every slot must be bound
                unbound = sorted(set(c.slots) - set(t.expect_fill))
                if unbound:
                    raise CurriculumError(f"dialogue {d.id!r}: a turn expecting construction {c.id!r} must bind every slot in expect_fill — unbound {unbound}")
        for r in d.requires:
            if r not in ids:
                raise CurriculumError(f"dialogue {d.id!r} requires unknown item {r!r}")


# proper names spoken in dialogues that need no teaching item
_DIALOGUE_PROPER_NAMES = {"sóley"}
_DIALOGUE_WORD_RE = re.compile(r"[^\W\d]+", re.UNICODE)


def dialogue_sequencing_report(cur: Curriculum, gap_threshold: int = 100) -> list[dict]:
    """Words in a dialogue's partner/opener lines whose earliest teaching item sits more
    than ``gap_threshold`` items past what the dialogue requires, worst first.

    A diagnostic for authors (the concept may be taught too late, or only inside a fixed
    phrase), never an eligibility gate.
    """
    word_to_items: dict[str, list[tuple[int, str]]] = {}
    for it in cur.items:
        for w in _DIALOGUE_WORD_RE.findall(it.target):
            word_to_items.setdefault(w.lower(), []).append((it.order, it.id))
    for lst in word_to_items.values():
        lst.sort()

    findings = []
    for d in cur.dialogues:
        req_orders = [cur.by_id[i].order for i in d.required_items if i in cur.by_id]
        base = max(req_orders) if req_orders else 0
        lines = [t.opener for t in d.turns if t.opener] + [t.partner for t in d.turns if t.partner]
        used = {w.lower() for w in _DIALOGUE_WORD_RE.findall(" ".join(lines))} - _DIALOGUE_PROPER_NAMES
        for w in used:
            cands = word_to_items.get(w)
            if not cands:
                continue  # taught nowhere at all -- test_dialogue_lines_stay_within_taught_vocabulary catches this
            order, item_id = cands[0]
            gap = order - base
            if gap > gap_threshold:
                findings.append({"dialogue": d.id, "word": w, "item": item_id, "item_order": order, "dialogue_base": base, "gap": gap})
    findings.sort(key=lambda f: -f["gap"])
    return findings
