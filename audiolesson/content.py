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

# Romanized Japanese left outside «ja:…» markup is read by the English voice (#219). A word is flagged when it is made only
# of Japanese morae AND has a mark English rarely has: a macron, tsu/shi/chi/fu/ji, an ending -masu/-desu/-shita, or "gozai".
_MORA = r"(?:(?:tch|ssh|kk|ss|tt|pp|ch|sh|ts|[kgszjtdnhfbpmrw]y?|y)?[aiueoāīūēō]|n(?![aiueoyāīūēō]))"
_JAPANESE_WORD_RE = re.compile(rf"^(?:{_MORA})+$")
_JAPANESE_MARK_RE = re.compile(r"[āīūēō]|tsu|shi|chi|fu|ji|(?:masu|desu|shita)$|gozai")
_ROMAJI_WORD_RE = re.compile(r"[A-Za-zāīūēōĀĪŪĒŌ]+")
# English words that look Japanese, each with its reason; an item's English `meaning` is where they turn up.
ROMAJI_ALLOWED = {
    "fun": "English",
    "machine": "English",
    "chinese": "English (the language)",
    "sushi": "English loanword; the English voice says it as English does",
}


def unmarked_japanese(text: str) -> list[str]:
    """Words of ``text`` that look like romanized Japanese, outside «…» spans (which carry their own language)."""
    out = []
    for w in _ROMAJI_WORD_RE.findall(NOTE_TARGET_RE.sub("", text)):
        w = w.lower()
        if len(w) > 2 and w not in ROMAJI_ALLOWED and _JAPANESE_WORD_RE.match(w) and _JAPANESE_MARK_RE.search(w):
            out.append(w)
    return out


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
    # the man's forms when the words follow the speaker's gender («Ég er þreyttur.»); a
    # side whose words don't change (the listener, "she") stays empty
    source_m: str = ""
    result_m: str = ""


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
    # what the instructor says for ``meaning`` when it names the item alone ("Say: …"): a
    # recall disambiguator written in brackets («the hotel (after 'to' / 'for')», «本（〜は・〜が）»)
    # reads as a note on the page but is spoken verbatim, so the spoken form folds it into
    # natural speech ("to the hotel", «本が»). Per language (``meaning_spoken_ja``), never
    # borrowed from another: without one the plain ``meaning`` is spoken. The transcript's
    # written glosses keep ``meaning``.
    meaning_spoken: str = ""
    instruction: str = ""  # transform: known-language instruction, e.g. "Make it negative:"
    examples: list[TransformExample] = field(default_factory=list)  # transform pairs
    order: int = 0
    gender: str | None = None  # noun's grammatical gender ("masc" | "fem" | "neut"), for agreement
    # construction: {slot} -> {"from": controlling slot, <gender>: surface form, ...}. Never
    # filled by picking an item; its text follows the gender of the ``from`` slot's fill, so
    # "{adj} {noun}." generates «Góður bíll.» / «Góð bók.» / «Gott hús.».
    agreement: dict[str, dict[str, str]] = field(default_factory=dict)
    # an adjective-like item whose surface form follows the gender of the noun it is said of (#158): the forms for
    # the genders other than the stored one («blár» → fem «blá», neut «blátt»). A construction's agreement rule
    # {"from": noun slot, "fills": true} puts the form of this slot's own fill into the sentence.
    gender_forms: dict[str, str] = field(default_factory=dict)
    # An authored bridge: the partner line spoken after item ``partner_cue_after`` and before
    # this item, so "A → partner_cue → this" reads as one real exchange. Set both or neither.
    partner_cue: str = ""
    partner_cue_after: str = ""
    # The bridge's scene, required with ``partner_cue``: ``setup`` replaces A's situation,
    # ``meaning`` says what the partner said (narrated only on the first encounters, see
    # LearnerState.bridges_heard), ``situation`` replaces this item's situation.
    partner_cue_setup: str = ""
    # who speaks ``partner_cue``: match the narration's he/she. Every profile voices native_a
    # female and native_b male; the learner's model answers take the other voice
    partner_cue_speaker: str = "native_b"
    # what a man says when the words follow the speaker's gender («Ég er seinn.» for «Ég er
    # sein.»). ``target`` is the woman's form; lessons practise both and announce which one
    target_m: str = ""
    partner_cue_meaning: str = ""
    partner_cue_situation: str = ""
    # G12 (lesson 13 feedback): the item whose line the partner says to prompt this one
    # («Hvaðan ert þú?» for «Ég er frá Japan.»). Once that line is known (or was introduced
    # earlier in the lesson) it is this item's situation cue, said by the partner with no
    # English narration; until then the authored ``situation`` is narrated as before.
    prompt_by: str = ""
    # §9 "Repetition" (G14): the item this one is a near form of: another case of a noun
    # («bankanum» for «bankinn»), another gender of an adjective («góð» for «gott»). When a lesson has
    # run out of other material, such a variant of something the learner knows (or met earlier
    # that lesson) may be introduced beyond the lesson's new-item limit, to fill the time with
    # something close to what they can already say rather than with the same words again.
    variant_of: str = ""
    # #192 / #149 step 2: a fixed phrase that is one instance of a pattern («Þrjá miða, takk.» of «{count} miða, takk.»):
    # the construction and the fills that make it. Once the pattern is known, the phrase's later practice in a lesson is
    # another sentence of the pattern with other fillers, credited to the pattern and its fillers, never to the phrase.
    instance_of: str = ""
    instance_fill: dict[str, str] = field(default_factory=dict)
    # A short known-language sentence the word is said in («This is good.» for «gott»): the recall
    # prompt after its introduction says «Say: good, as in: This is good.», so the answer is the
    # form that sentence takes rather than any of the word's family (gott, góður, góðan…).
    context: str = ""
    # §9 "Repetition" / #171: a construction's other forms, authored (never derived): the negative
    # («Það er ekki {weather}.») and the yes/no question («Er {weather}?»), each a target template
    # with the construction's slots and a meaning. They are used in generated sentences only
    # once the note that teaches them (``Note.teaches``) has been heard.
    # A light review (#171, owner): once the learner knows this construction and it isn't open, this
    # many sentences of it come in every lesson, spread over the time, with the fillers changing. Not a
    # drill: a construction that is core to what a traveller says (asking permission, saying what you
    # will do) stays in the ear. The first lesson and a failure get the usual practice instead.
    refresh: int = 0
    negative: str = ""
    negative_meaning: str = ""
    question: str = ""
    question_meaning: str = ""

    # ---- derived helpers -------------------------------------------------

    @property
    def spoken_meaning(self) -> str:
        """``meaning`` as the instructor says it when naming the item alone."""
        return self.meaning_spoken or self.meaning

    @property
    def slot_names(self) -> list[str]:
        return _SLOT_RE.findall(self.target)

    def form_templates(self, form: str | None) -> tuple[str, str]:
        """(target, meaning) template of ``form`` ("negative" / "question"); the plain ones for
        None or a form this construction doesn't have."""
        if form == "negative" and self.negative:
            return self.negative, self.negative_meaning
        if form == "question" and self.question:
            return self.question, self.question_meaning
        return self.target, self.meaning

    @property
    def forms(self) -> list[str]:
        """The authored forms besides the plain one."""
        return [f for f, t in (("negative", self.negative), ("question", self.question)) if t]

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
    expect_text_m: str | None = None  # the man's form of ``expect_text`` when the words follow the speaker's gender
    partner: str | None = None  # what the other speaker says after the learner
    partner_meaning: str | None = None
    opener: str | None = None  # partner line spoken *before* the learner's turn
    opener_meaning: str | None = None
    # when ``expect`` is a construction: slot -> item id for every slot, so the learner
    # generates e.g. «Það kostar fimm þúsund krónur.» mid-exchange. The fills count as
    # required items.
    expect_fill: dict[str, str] = field(default_factory=dict)
    # the cue stays even in a later, unassisted play (a theme exchange's turn that no partner line prompts, #149 1b-ii)
    keep_cue: bool = False


@dataclass
class Dialogue:
    id: str
    setting: str  # narrator, known language
    turns: list[DialogueTurn]
    topics: list[str] = field(default_factory=list)
    partner_speaker: str = "native_b"
    variant: str = ""  # a theme exchange: which variant of each varying partner line is spoken (#134), for the label
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
    # #171: "negative" or "question": the note that teaches that form of the constructions. It
    # has no ``items``; it plays once the learner knows two constructions that have the form, and
    # until it has been heard the form is not used in generated sentences.
    teaches: str = ""


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

    def resolve_slots(self, construction: Item, fills: dict[str, Item], speaker: str | None = None, form: str | None = None) -> tuple[str, str]:
        """Return (target, meaning) with every slot filled from ``fills``; agreement
        placeholders resolve first, from the gender of their ``from`` slot's fill.
        ``speaker="m"`` fills with each fill's man's form (``target_m``) where it has one:
        «Ég er {state}.» → «Ég er glaður.»"""
        target, form_meaning = construction.form_templates(form)
        meaning = construction.spoken_meaning if form_meaning == construction.meaning else form_meaning  # narrated: no recall disambiguator in brackets
        for slot, rule in construction.agreement.items():
            gender = fills[rule["from"]].gender
            if rule.get("fills"):
                # the slot's own fill, in the form its noun's gender takes (#158): «Bíllinn er blár.» / «Bókin er blá.»
                fill = fills[slot]
                target = target.replace("{" + slot + "}", fill.gender_forms.get(gender, fill.target).rstrip("."))
                continue
            target = target.replace("{" + slot + "}", rule[gender])
        for slot, item in fills.items():
            spoken = item.target_m if speaker == "m" and item.target_m else item.target
            target = target.replace("{" + slot + "}", spoken.rstrip("."))
            meaning = meaning.replace("{" + slot + "}", item.meaning_forms.get("in_sentence", item.meaning).rstrip("."))
            meaning = _FORM_SLOT_RE.sub(
                lambda m: item.meaning_forms.get(m.group(2), item.meaning).rstrip(".") if m.group(1) == slot else m.group(0), meaning
            )
        # a sentence that opens with a slot ("{thing} virkar ekki.") still starts with a capital
        if construction.form_templates(form)[0].startswith("{"):
            target = target[:1].upper() + target[1:]
        if construction.form_templates(form)[1].startswith("{"):
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
_GLOSSED_ITEM = ("meaning", "context", "negative_meaning", "question_meaning", "situation", "situations", "instruction", "meaning_forms", "partner_cue_setup", "partner_cue_meaning", "partner_cue_situation")
_GLOSSED_EXAMPLE = ("source_meaning", "result_meaning")
_GLOSSED_TURN = ("cue", "opener_meaning", "partner_meaning", "expect_meaning")
_GLOSSED_DIALOGUE = ("setting",)
_GLOSSED_NOTE = ("text",)
_GLOSSED_META = ("name",)


def _pick_spoken(entry: dict, lang: str | None) -> dict:
    """``meaning_spoken`` is optional per language: the learner's language's own, or none
    (the plain meaning is then spoken). It never mixes languages: a glossed meaning never
    takes the primary language's spoken form (English in a Japanese instruction), and a
    meaning that falls back to the primary language takes its spoken form too."""
    out = {k: v for k, v in entry.items() if not k.startswith("meaning_spoken")}
    key = f"meaning_spoken_{lang}" if lang and f"meaning_{lang}" in entry else "meaning_spoken"
    if key in entry:
        out["meaning_spoken"] = entry[key]
    return out


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
        entry = _pick_gloss(_pick_spoken(entry, lang), _GLOSSED_ITEM, lang, langs, missing, label)
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


# written-only marks: brackets and 〜 read aloud as noise (or «から») by TTS
_UNSPEAKABLE_RE = re.compile(r"[()（）〜～]")
_ANY_SLOT_RE = re.compile(r"\{[^{}]+\}")  # {slot} and {slot:form}
def _slot_names(text: str) -> list[str]:
    """The slots a template names, ignoring a ``:form`` suffix."""
    return [m[1:-1].split(":")[0] for m in _ANY_SLOT_RE.findall(text)]


FORMS = ("negative", "question")  # a construction's authored forms besides the plain one (#171)

SPEAKERS = ("native_a", "native_b")  # native_a is voiced female, native_b male, in every profile


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
        if it.kind != "transform" and _UNSPEAKABLE_RE.search(it.spoken_meaning):
            field = "meaning_spoken" if it.meaning_spoken else "meaning"
            raise CurriculumError(
                f"item {it.id!r}: its {field} is spoken verbatim, so it takes no brackets or 〜 "
                f"(write a bracket-free meaning_spoken): {it.spoken_meaning!r}"
            )
        if "inf" in it.tags and cur.known_lang == "en" and not it.spoken_meaning.startswith("to "):
            # an infinitive filler said alone: «Say: buy a ticket» asks for the imperative («Kauptu miða»),
            # «Say: to buy a ticket» for what the item is («kaupa miða»); sentences fill from `meaning`
            raise CurriculumError(f"item {it.id!r}: an infinitive is named with «to» (meaning_spoken = \"to {it.meaning}\"): {it.spoken_meaning!r}")
        if it.meaning_spoken and sorted(_ANY_SLOT_RE.findall(it.meaning_spoken)) != sorted(_ANY_SLOT_RE.findall(it.meaning)):
            raise CurriculumError(f"item {it.id!r}: meaning_spoken must keep the meaning's slots: {it.meaning_spoken!r}")
    for d in cur.dialogues:
        if d.id in {x.id for x in cur.dialogues if x is not d}:
            raise CurriculumError(f"duplicate dialogue id {d.id!r}")
        for t in d.turns:
            if t.expect_text_m and (not t.expect_text or t.expect_text_m == t.expect_text):
                raise CurriculumError(f"dialogue {d.id!r}: expect_text_m is the man's form of expect_text and must differ from it")
        if d.partner_speaker not in SPEAKERS:
            raise CurriculumError(f"dialogue {d.id!r}: partner_speaker must be one of {SPEAKERS}, not {d.partner_speaker!r}")
    seen_notes: set[str] = set()
    for n in cur.notes:
        if n.id in seen_notes:
            raise CurriculumError(f"duplicate note id {n.id!r}")
        seen_notes.add(n.id)
        for ref in n.items + n.transfer_items + n.requires:
            if ref not in ids:
                raise CurriculumError(f"note {n.id!r} references unknown item {ref!r}")
        if n.teaches:
            if n.teaches not in FORMS:
                raise CurriculumError(f"note {n.id!r}: teaches must be one of {FORMS}, not {n.teaches!r}")
            if n.milestone or n.items:
                raise CurriculumError(f"note {n.id!r}: a note that teaches a form has no items and isn't a milestone (it plays once the learner knows two constructions that have it)")
            if sum(1 for x in cur.notes if x.teaches == n.teaches) > 1:
                raise CurriculumError(f"note {n.id!r}: more than one note teaches {n.teaches!r}")
        # strip matched pairs; any « or » left over is malformed ("»foo«", "«a» «b")
        unmatched = NOTE_TARGET_RE.sub("", n.text)
        if "«" in unmatched or "»" in unmatched:
            raise CurriculumError(f"note {n.id!r} has malformed or unmatched «» markers")
        for w in unmarked_japanese(n.text):
            raise CurriculumError(f"note {n.id!r}: romanized Japanese outside «ja:…» markup: {w!r}")
    for it in cur.items:
        for field_name, text in [("situation", it.situation), ("instruction", it.instruction), *[("situations", t) for t in it.situations]]:
            for w in unmarked_japanese(text or ""):
                raise CurriculumError(f"item {it.id!r}: {field_name}: romanized Japanese read by the English voice (only a note can mark it «ja:…»; reword): {w!r}")
        for ref in it.components + it.prereqs:
            if ref not in ids:
                raise CurriculumError(f"item {it.id!r} references unknown item {ref!r}")
        if bool(it.partner_cue) != bool(it.partner_cue_after):
            raise CurriculumError(f"item {it.id!r}: partner_cue and partner_cue_after must be set together, or not at all")
        if it.target_m and (it.kind == "construction" or it.target_m == it.target):
            raise CurriculumError(f"item {it.id!r}: target_m is the man's form of a non-construction target and must differ from it")
        for e in it.examples:
            if (e.source_m and e.source_m == e.source) or (e.result_m and e.result_m == e.result):
                raise CurriculumError(f"item {it.id!r}: a transform example's man's form must differ from its own ({e.source!r})")
        if it.refresh:
            if it.kind != "construction" or not 0 < it.refresh <= 5:
                raise CurriculumError(f"item {it.id!r}: refresh is a number of sentences, 1 to 5, for a construction")
        for form in FORMS:
            template, meaning = it.form_templates(form)
            has = bool(getattr(it, form) or getattr(it, form + "_meaning"))
            if not has:
                continue
            if it.kind != "construction" or it.agreement:
                raise CurriculumError(f"item {it.id!r}: {form} is for a construction without agreement placeholders")
            if not (getattr(it, form) and getattr(it, form + "_meaning")):
                raise CurriculumError(f"item {it.id!r}: {form} and {form}_meaning go together")
            if sorted(_ANY_SLOT_RE.findall(template)) != sorted(_ANY_SLOT_RE.findall(it.target)):
                raise CurriculumError(f"item {it.id!r}: {form} must use the construction's slots, as {it.target!r} does")
            if sorted(_slot_names(meaning)) != sorted(_slot_names(it.meaning)):
                raise CurriculumError(f"item {it.id!r}: {form}_meaning must use the meaning's slots, as {it.meaning!r} does")
            if _UNSPEAKABLE_RE.search(meaning):
                raise CurriculumError(f"item {it.id!r}: {form}_meaning is spoken verbatim, so it takes no brackets or 〜")
            if form == "negative" and cur.target_lang == "is" and not re.search(r"\bekki\b", template, re.IGNORECASE):
                raise CurriculumError(f"item {it.id!r}: an Icelandic negative contains «ekki»: {template!r}")
            if form == "question" and not template.rstrip().endswith("?"):
                raise CurriculumError(f"item {it.id!r}: a question ends with «?»: {template!r}")
        if it.context and it.kind not in ("phrase", "vocab"):
            raise CurriculumError(f"item {it.id!r}: context is for a phrase or vocab item (a construction is recalled through a filled sentence)")
        if it.context and _UNSPEAKABLE_RE.search(it.context):
            raise CurriculumError(f"item {it.id!r}: context is spoken by the instructor, so it takes no brackets or 〜")
        if it.variant_of:
            if it.variant_of == it.id or it.variant_of not in ids:
                raise CurriculumError(f"item {it.id!r}: variant_of must name another item, not {it.variant_of!r}")
            if it.kind not in ("phrase", "vocab") or cur.by_id[it.variant_of].kind not in ("phrase", "vocab"):
                raise CurriculumError(f"item {it.id!r}: variant_of links phrase and vocab items (a construction's variety is its slot fills)")
            if cur.by_id[it.variant_of].variant_of:
                raise CurriculumError(f"item {it.id!r}: variant_of {it.variant_of!r} is itself a variant; name the form it is a variant of")
            if cur.by_id[it.variant_of].target == it.target:
                raise CurriculumError(f"item {it.id!r}: a variant must differ from {it.variant_of!r} in its words")
        if it.instance_of or it.instance_fill:
            c = cur.by_id.get(it.instance_of)
            if it.kind != "phrase" or c is None or c.kind != "construction":
                raise CurriculumError(f"item {it.id!r}: instance_of names the construction a phrase is an instance of, not {it.instance_of!r}")
            if sorted(it.instance_fill) != sorted(c.slots):
                raise CurriculumError(f"item {it.id!r}: instance_fill must name every slot of {c.id!r} ({sorted(c.slots)})")
            fills = {}
            for slot, ref in it.instance_fill.items():
                if ref not in ids or c.slots[slot] not in cur.by_id[ref].tags:
                    raise CurriculumError(f"item {it.id!r}: instance_fill {slot!r}={ref!r} is not a fill with tag {c.slots[slot]!r}")
                fills[slot] = cur.by_id[ref]
            made = cur.resolve_slots(c, fills)[0]
            if made.strip().casefold() != it.target.strip().casefold():
                raise CurriculumError(f"item {it.id!r}: the pattern with these fills says {made!r}, not {it.target!r}")
        if it.prompt_by:
            if it.prompt_by == it.id or it.prompt_by not in ids:
                raise CurriculumError(f"item {it.id!r}: prompt_by must name another item, not {it.prompt_by!r}")
            if cur.by_id[it.prompt_by].kind not in ("phrase", "vocab"):
                raise CurriculumError(f"item {it.id!r}: prompt_by {it.prompt_by!r} must be a phrase or vocab item (its target is spoken as the partner's line)")
            if it.kind == "construction" or it.target_m:
                raise CurriculumError(f"item {it.id!r}: prompt_by is for a plain phrase (no slots, no speaker-gender forms)")
        if it.partner_cue_speaker not in SPEAKERS:
            raise CurriculumError(f"item {it.id!r}: partner_cue_speaker must be one of {SPEAKERS}, not {it.partner_cue_speaker!r}")
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
                    if rule.get("fills"):
                        # the slot is also picked from its own pool; each fill carries the form for every gender its noun can take
                        if s not in it.slots:
                            raise CurriculumError(f"construction {it.id!r}: agreement for {{{s}}} takes the fill's forms, so {s!r} needs a tag in [slots]")
                        genders = {c.gender for c in candidates}
                        lacking = [f.id for f in cur.items_with_tag(it.slots[s]) if any(g != "masc" and g not in f.gender_forms for g in genders)]  # the stored form is the masculine one
                        if lacking:
                            raise CurriculumError(f"construction {it.id!r}: fills of {{{s}}} lack gender_forms (the stored form is the masculine one) for {sorted(genders)}: {lacking}")
                        continue
                    forms = {k: v for k, v in rule.items() if k not in ("from", "fills")}
                    missing = {c.gender for c in candidates} - set(forms)
                    if missing:
                        raise CurriculumError(f"construction {it.id!r}: agreement for {{{s}}} is missing forms for {sorted(missing)}")
                    continue
                if s not in it.slots:
                    raise CurriculumError(f"construction {it.id!r}: slot {s!r} has no tag in [slots]")
                forms = [f for slot, f in _FORM_SLOT_RE.findall(it.meaning) if slot == s]
                form_forms = [f for text in (it.negative_meaning, it.question_meaning) for slot, f in _FORM_SLOT_RE.findall(text) if slot == s]
                if "{" + s + "}" not in it.meaning and not forms:
                    raise CurriculumError(f"construction {it.id!r}: meaning must also contain {{{s}}}")
                for form in forms + form_forms:
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


def part_before_whole_report(cur: Curriculum) -> list[dict]:
    """Items the learner meets as "something new" after a phrase that already contains them
    (G13, lesson 13 feedback: «Hvenær?» came as a new item after «Hvenær leggjum við af
    stað?»). An item A is a part of item B when A's words occur in B's words in the same
    order, and A is taught after B (``A.order > B.order``) with no ``prereqs`` path from B
    to A. Worst first (the gap in items between them).

    A diagnostic for authors, never an eligibility gate: most parts are function words or
    question words taught late as items of their own, and moving them is a curriculum edit
    (list A in B's ``prereqs`` and put A before B), not something to apply wholesale."""
    words = {i.id: [w.lower() for w in _DIALOGUE_WORD_RE.findall(i.target)] for i in cur.items}

    def needs(item_id: str, seen: set[str] | None = None) -> set[str]:
        seen = set() if seen is None else seen
        for p in cur.by_id[item_id].prereqs:
            if p not in seen:
                seen.add(p)
                needs(p, seen)
        return seen

    findings = []
    for b in cur.items:
        wb = words[b.id]
        closure = None
        for a in cur.items:
            wa = words[a.id]
            if a.id == b.id or a.kind == "construction" or not wa or len(wa) >= len(wb) or a.order <= b.order:
                continue
            if not any(wb[k : k + len(wa)] == wa for k in range(len(wb) - len(wa) + 1)):
                continue
            closure = needs(b.id) if closure is None else closure
            if a.id not in closure:
                findings.append({"whole": b.id, "whole_order": b.order, "part": a.id, "part_order": a.order, "gap": a.order - b.order})
    findings.sort(key=lambda f: (-f["gap"], f["whole"], f["part"]))
    return findings


def frame_gap_report(cur: Curriculum, span: int = 50) -> dict[str, list[dict]]:
    """Vocab items the learner is asked to produce long before anything uses them (#80).

    A vocab item's ladder only climbs past ``meaning`` in a *context*: a construction with a
    slot that takes one of its tags (recombine), or a dialogue that requires it. Its first
    context is the earliest such construction, or the earliest point a requiring dialogue
    becomes playable (its latest required item). Returns ``{"late": [...], "none": [...]}``:
    items whose first context comes more than ``span`` items after them, worst first, and
    items with no context at all, in curriculum order. Each entry: ``{"item", "order",
    "context", "context_order", "gap"}`` (context fields ``None`` for "none").

    A diagnostic for authors, never an eligibility gate: hearing a word in a partner line
    before producing it is fine; repeated bare production with no use is what it flags.
    """
    frames: dict[str, tuple[int, str]] = {}  # tag -> earliest construction taking it
    for c in cur.items:
        if c.kind == "construction":
            for tag in c.slots.values():
                if tag not in frames or c.order < frames[tag][0]:
                    frames[tag] = (c.order, c.id)
    dialogue_at: dict[str, tuple[int, str]] = {}  # item -> earliest dialogue requiring it
    for d in cur.dialogues:
        req = [cur.by_id[i].order for i in d.required_items if i in cur.by_id]
        base = max(req, default=0)
        for i in d.required_items:
            if i not in dialogue_at or base < dialogue_at[i][0]:
                dialogue_at[i] = (base, f"dialogue {d.id}")
    late, none = [], []
    for it in cur.items:
        if it.kind != "vocab":
            continue
        options = [frames[t] for t in it.tags if t in frames] + ([dialogue_at[it.id]] if it.id in dialogue_at else [])
        if not options:
            none.append({"item": it.id, "order": it.order, "context": None, "context_order": None, "gap": None})
            continue
        order, context = min(options)
        gap = max(0, order - it.order)
        if gap > span:
            late.append({"item": it.id, "order": it.order, "context": context, "context_order": order, "gap": gap})
    late.sort(key=lambda f: (-f["gap"], f["order"]))
    none.sort(key=lambda f: f["order"])
    return {"late": late, "none": none}
