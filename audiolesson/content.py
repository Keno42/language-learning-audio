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
_WORD_RE = re.compile(r"\w+", re.UNICODE)

# «...» inside a Note's text marks a target-language phrase that Builder.note() (exercises.py)
# hands to the target-language voice instead of narrating it as instructor-language text
# (issue #34 point 1). Shared here, not in exercises.py, so validate() below can also use it
# without exercises.py importing back into this module.
NOTE_TARGET_RE = re.compile(r"«([^»]+)»")

# A «...» span may open with an explicit "xx:" language code (issue #49): a note can
# legitimately mention a *third* language besides its own narration language and the
# course's target language — e.g. an English note about Icelandic naming a Japanese
# word — and that word needs its own voice, not the target-language one «...» alone
# implies. «Jæja» (bare) still means "target language," unchanged; «ja:sate» means "say
# this in Japanese instead." 2-3 lowercase letters keeps this from misfiring on a
# genuine target-language phrase that happens to contain a colon (e.g. a clock time).
NOTE_LANG_PREFIX_RE = re.compile(r"^([a-z]{2,3}):\s*(.+)$", re.DOTALL)


def split_note_span(span: str) -> tuple[str | None, str]:
    """Split one «...»-marked note span into (explicit language code or None, spoken text).

    ``split_note_span("Halló")`` -> ``(None, "Halló")`` — spoken in the target-language
    voice, as before this existed. ``split_note_span("ja:sate")`` -> ``("ja", "sate")`` —
    an embedded third-language example, spoken in that language's voice instead.
    """
    m = NOTE_LANG_PREFIX_RE.match(span)
    return (m.group(1), m.group(2)) if m else (None, span)

# Vowel letters used by this project's target languages (French, Icelandic), including
# accented forms. A maximal run of these approximates one syllable nucleus, used only to
# gauge whether a single word is long enough to deserve extra practice (see `is_hard`) — not
# to decide where to split it. issue #34 point 7: a former version of this file used the same
# vowel-run boundaries to actually cut a word into sub-word chunks for backward build-up
# (e.g. "Fyrirgefðu" -> "ðu"/"gefðu"/"irgefðu"), with no knowledge of Icelandic consonant
# clusters or gemination — and even a linguistically correct split can still be mispronounced
# by TTS synthesizing the fragment in isolation, with no context that it's part of a longer
# word. `Item.backward_chunks` no longer does this for single words; see its docstring.
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
    situations: list[str] = field(default_factory=list)  # alternative cues for the same target,
    # rotated on repeat retrieval (issue #34 point 4) so spaced review doesn't always replay the
    # identical wording; overrides `situation` when non-empty (see `situation_for`)
    alternatives: list[str] = field(default_factory=list)
    pronunciation_notes: str = ""
    chunks: list[str] | None = None  # backward-build chunks, shortest first
    slots: dict[str, str] = field(default_factory=dict)  # construction: slot -> required tag
    example: dict[str, str] = field(default_factory=dict)  # construction: slot -> item id
    instruction: str = ""  # transform: known-language instruction, e.g. "Make it negative:"
    examples: list[TransformExample] = field(default_factory=list)  # transform pairs
    order: int = 0
    gender: str | None = None  # noun's grammatical gender ("masc" | "fem" | "neut"), for agreement
    # construction: {slot} name -> {"from": controlling slot name, gender: surface form, ...}.
    # Unlike `slots`, an agreement slot is never filled by picking an item — its text is derived
    # from the `.gender` of whatever fills the named `from` slot. This is what lets a
    # construction's own wording (not just which noun it names) change to fit a noun the learner
    # already knows independently, e.g. "{adj} {noun}." with
    # agreement={"adj": {"from": "noun", "masc": "Góður", ...}} genuinely generates "Góður
    # bíll."/"Góð bók."/"Gott hús." rather than requiring each as its own authored phrase (issue
    # #29 owner review: a real generate-from-parts pilot, not fixed-phrase accumulation). `from`
    # is explicit, not inferred from "whichever fill happens to have a gender" (owner review on
    # PR #50 point 2), so a construction with more than one gendered fill slot stays unambiguous.
    agreement: dict[str, dict[str, str]] = field(default_factory=dict)

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
        """The situation cue to narrate for this exercise. Rotates round-robin through
        ``situations`` (if authored) on total exposures so far, so retrieving the same item
        again — the normal course of spaced review — doesn't always replay the identical
        wording; falls back to the single ``situation`` string otherwise."""
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
        """Progressively longer tails of the phrase, shortest first, growing from the end.

        Authors can override with ``chunks`` for a word whose boundaries are actually
        verified. Otherwise, multi-word phrases split on words — a real, pronounceable unit
        ("vel" / "svo vel" / "Gjörðu svo vel") — but a single long word gets no automatic
        sub-word split (issue #34 point 7): guessing a syllable boundary from spelling alone
        risks both an outright wrong boundary (Icelandic has consonant clusters and gemination
        this project has no verified way to reason about) and a correct boundary still coming
        out mispronounced, since a fragment spoken by TTS in isolation has no context that
        it's part of a longer word. ``is_hard()`` still flags a long single word for extra
        practice; ``Builder.intro()`` gives it slow whole-word repetition instead of a
        backward build when this returns just the one, unsplit chunk.
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
    """A short aside in the learner's language, spoken by the instructor.

    Notes are passive content, so the planner rations them (a couple per lesson)
    and prefers to place one right after an exercise on one of its ``items``.

    ``milestone`` marks an instructional note that names a grammatical pattern
    once the learner has met all of ``items`` — as opposed to an optional
    cultural aside. The planner never offers a milestone note as generic
    filler and never skips it once its items are all met (see
    ``Planner._eligible_milestone``); a plain aside can be either.

    Wrap a target-language phrase mentioned inside ``text``/``text_ja`` in
    ``«...»`` to have it actually spoken by the target-language voice
    instead of read aloud as instructor-language text (see
    ``NOTE_TARGET_RE`` and ``Builder._speak_note_text``).
    """

    id: str
    text: str
    items: list[str] = field(default_factory=list)  # related item ids
    topics: list[str] = field(default_factory=list)
    milestone: bool = False
    # Extra items a milestone's discrimination practice (Planner.do_discriminate) may
    # reach into once they're known, on top of `items` — never required for the milestone
    # itself to fire (issue #29, owner review: noticing a grammatical contrast is not the
    # same as being asked to apply it to new vocabulary; gating firing on these too would
    # make the milestone wait on the very transfer material it exists to introduce).
    transfer_items: list[str] = field(default_factory=list)


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
        """Return (target, meaning) with every slot filled from ``fills``.

        Agreement placeholders (``construction.agreement``) resolve first, from the gender of
        whatever fills their named ``from`` slot — so the construction's own wording, not just
        which item it names, tracks the noun that was picked.
        """
        target = construction.target
        meaning = construction.meaning
        for slot, rule in construction.agreement.items():
            gender = fills[rule["from"]].gender
            target = target.replace("{" + slot + "}", rule[gender])
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
_GLOSSED_ITEM = ("meaning", "situation", "situations", "instruction")
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
        for ref in n.items:
            if ref not in ids:
                raise CurriculumError(f"note {n.id!r} references unknown item {ref!r}")
        # A count-only check would pass malformed markup like "»foo«" (one of each, wrong
        # order) or "«a» «b" (one real pair plus a stray, unpaired open) — actually run the
        # matching regex and check nothing with a « or » is left unaccounted for.
        unmatched = NOTE_TARGET_RE.sub("", n.text)
        if "«" in unmatched or "»" in unmatched:
            raise CurriculumError(f"note {n.id!r} has malformed or unmatched «» markers")
    for it in cur.items:
        for ref in it.components + it.prereqs:
            if ref not in ids:
                raise CurriculumError(f"item {it.id!r} references unknown item {ref!r}")
        if it.kind == "construction":
            slots = it.slot_names
            if not slots:
                raise CurriculumError(f"construction {it.id!r} has no {{slot}} in its target")
            for s in slots:
                if s in it.agreement:
                    # an agreement placeholder is never filled by picking an item (see
                    # Item.agreement), so it's exempt from the [slots]/meaning checks below —
                    # instead, its controlling slot must actually be able to drive it.
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


# Proper names spoken in dialogues that don't need a teaching item — see
# dialogue_sequencing_report and its hard-gating cousin, the
# test_dialogue_lines_stay_within_taught_vocabulary test.
_DIALOGUE_PROPER_NAMES = {"sóley"}
_DIALOGUE_WORD_RE = re.compile(r"[^\W\d]+", re.UNICODE)


def dialogue_sequencing_report(cur: Curriculum, gap_threshold: int = 100) -> list[dict]:
    """Diagnostic only (born from issue #25, now tracked under #29) — this never gates
    dialogue eligibility, unlike ``Dialogue.required_items``. It flags words spoken in a
    dialogue's ``opener``/``partner``
    lines whose earliest teaching item sits far past the items the dialogue already requires:
    a signal the curriculum may be sequencing that concept too late, or never introducing it as
    reusable standalone vocabulary at all (buried inside a one-off fixed phrase instead), not
    something to patch by tacking on more prerequisites. A repeat offender across many dialogues
    is exactly the "high-value concept, introduced too late" case worth fixing at the source.

    Returns one finding per (dialogue, word) pair whose gap exceeds ``gap_threshold``, sorted
    worst-first. An empty list is not a guarantee every word is well-sequenced — only that
    none crossed the threshold.
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
