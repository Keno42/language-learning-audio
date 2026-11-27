"""Trust in a target-language line: whether Icelanders write its words side by side (the owner, 2026-11-28; G10, #631).

No fluent speaker has reviewed most of the course (G10). The owner's rule: a line whose every pair of neighbouring words is found in
texts Icelanders wrote counts as checked. The pairs are looked up by ``tools/attest_pairs.py`` in the corpora of the Árni Magnússon
Institute (Risamálheild and others: forums, blogs, subtitles, Wikipedia, news, books, parliament; about 2.5 billion words) and kept in
``<curriculum>/trust/pairs.json``, so ``validate``, the planner and the tests run offline.

A line is **trusted** when every pair is found, **unusual** when one pair (or a word standing alone) is found in no text, and
**unknown** while one is not looked up yet. Pairs are taken inside a stretch of words: punctuation and digits end a stretch, so «Takk.
Þú …» and «klukkan 5 í dag» make no pair across them, and a word alone in its stretch («Vá!») is looked up as a word. A proper name (a
capital letter not at the start of a sentence: «Hekla», the persona's «Yuki») is no evidence either way, so no pair or word with one is
asked. ``course_lines`` lists every line the course can say, the sentences its patterns make included, for the tool and the report.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

from .text import WORD

FILE_NAME = "pairs.json"
TOOL_HINT = "python tools/attest_pairs.py <curriculum>"
# a stretch of words ends at any character that is neither a letter nor white space: punctuation, a digit, a hyphen
_BREAK = re.compile(r"[^\w\s]|[\d_]")
_SENTENCE_END = re.compile(r"[.?!…:]\s*$")
_SPAN = re.compile(r"«([^»]+)»")


def table_path(curriculum_dir: str | Path) -> Path:
    return Path(curriculum_dir) / "trust" / FILE_NAME


@dataclass(frozen=True)
class Parts:
    """What a line is judged by: its pairs of neighbouring words and its words standing alone, lower-cased."""

    pairs: tuple[str, ...]
    words: tuple[str, ...]


def parts(text: str) -> Parts:
    """The pairs and lone words of ``text`` («Vá! Útsýnið er fallegt.» → pairs «útsýnið er», «er fallegt»; word «vá»)."""
    pairs: list[str] = []
    alone: list[str] = []
    run: list[str] = []
    named: list[bool] = []

    def close() -> None:
        if len(run) == 1 and not named[0]:
            alone.append(run[0])
        for i in range(len(run) - 1):
            if not named[i] and not named[i + 1]:
                pairs.append(f"{run[i]} {run[i + 1]}")
        run.clear()
        named.clear()

    pos = 0
    for m in WORD.finditer(text):
        between = text[pos:m.start()]
        if _BREAK.search(between):
            close()
        before = text[:m.start()]
        sentence_start = not before.strip() or bool(_SENTENCE_END.search(before))
        run.append(m.group(0).lower())
        named.append(m.group(0)[:1].isupper() and not sentence_start)
        pos = m.end()
    close()
    return Parts(tuple(pairs), tuple(alone))


@dataclass
class Verdict:
    status: str  # "trusted", "unusual" or "unknown"
    absent: list[str] = field(default_factory=list)  # pairs and lone words no text has
    missing: list[str] = field(default_factory=list)  # pairs and lone words not looked up yet


@dataclass
class Trust:
    """The looked-up pairs and words: how many corpora have each (0: none)."""

    pairs: dict[str, int] = field(default_factory=dict)
    words: dict[str, int] = field(default_factory=dict)

    def verdict(self, text: str) -> Verdict:
        p = parts(text)
        absent: list[str] = []
        missing: list[str] = []
        for key, table in [(k, self.pairs) for k in p.pairs] + [(k, self.words) for k in p.words]:
            n = table.get(key)
            if n is None:
                missing.append(key)
            elif n == 0:
                absent.append(key)
        status = "unusual" if absent else "unknown" if missing else "trusted"
        return Verdict(status, absent, missing)

    def usual(self, text: str) -> bool:
        """Not unusual: every pair found, or not looked up yet (a line the lookup has not reached is not held back)."""
        return self.verdict(text).status != "unusual"


def load(curriculum_dir: str | Path) -> Trust | None:
    """The table beside the curriculum, or None when it has none (a curriculum file, or no lookup made yet)."""
    path = table_path(curriculum_dir)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Trust(pairs=dict(raw.get("pairs", {})), words=dict(raw.get("words", {})))


def save(curriculum_dir: str | Path, trust: Trust, about: dict) -> None:
    path = table_path(curriculum_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {**about, "pairs": dict(sorted(trust.pairs.items())), "words": dict(sorted(trust.words.items()))}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")


def spans(text: str) -> list[str]:
    """The target-language «spans» of a known-language text (a note, a reason, a lead); a «ja:…» span is the third language."""
    return [s for s in _SPAN.findall(text or "") if not s.startswith("ja:")]


def _filled_sentences(cur, c) -> Iterator[str]:
    """Every sentence pattern ``c`` makes: each combination of its slots' fills, in each form and each speaker's voice, its alternatives too."""
    from .exercises import _fills_repeat_a_word  # the builder's own rule: no two fills of a sentence share a word

    pools = [cur.items_with_tag(tag, c) for tag in c.slots.values()]
    authored = [dict(c.example), dict(c.situation_fill)]
    combos = [dict(zip(c.slots, combo)) for combo in product(*pools)]
    for ref in authored:  # an authored fill need not carry the slot's tag
        if ref and set(ref) == set(c.slots) and all(i in cur.by_id for i in ref.values()):
            combos.append({slot: cur.by_id[i] for slot, i in ref.items()})
    for fills in combos:
        if _fills_repeat_a_word(fills):
            continue
        for form in (None, *c.forms):
            if not cur.fits_form(c, fills, form):
                continue
            for speaker in (None, "m"):
                yield cur.resolve_slots(c, fills, speaker, form)[0]
        for speaker in (None, "m"):
            yield from cur.resolve_alternatives(c, fills, speaker)


def course_lines(cur, themes: Iterable = ()) -> list[tuple[str, str]]:
    """``(line, where)`` for every target-language line the course can say aloud, each line once: items and their alternatives, the
    sentences patterns make, authored dialogues, the themes' turns and their variants and listening lines, contrasts, and the «spans» of
    notes, reasons and leads. ``where`` names the first place the line comes from."""
    seen: dict[str, str] = {}

    def add(text: str, where: str) -> None:
        text = (text or "").strip()
        if text and "{" not in text and text not in seen:
            seen[text] = where

    for it in cur.items:
        if it.kind == "construction" and it.slots:
            for s in _filled_sentences(cur, it):
                add(s, f"pattern {it.id}")
        else:
            add(it.target, f"item {it.id}")
            add(it.target_m, f"item {it.id}")
            for a in it.alternatives:
                add(a, f"item {it.id}")
        add(it.partner_cue, f"item {it.id}")
        for v in list(it.said_of.values()) + list(it.subjects.values()) + [it.subjects_base]:
            add(v, f"item {it.id}")
        for e in it.examples:
            for s in (e.source, e.result, e.source_m, e.result_m):
                add(s, f"item {it.id}")
        for s in spans(it.form_reason):
            add(s, f"item {it.id} (reason)")
    for d in cur.dialogues:
        for t in d.turns:
            for s in (t.opener, t.partner, t.expect_text, t.expect_text_m):
                add(s or "", f"dialogue {d.id}")
    for n in cur.notes:
        for s in spans(n.text) + spans(n.text_plain):
            add(s, f"note {n.id}")
    for c in cur.contrasts:
        for s in spans(c.lead):
            add(s, f"contrast {c.id}")
        for ln in c.lines:
            add(ln.target, f"contrast {c.id}")
            add(ln.answer, f"contrast {c.id}")
    for th in themes:
        for n, lv in enumerate(th.levels, 1):
            for t in lv.turns:
                where = f"theme {th.id}:{n}"
                add(t.say_m, where)
                for ln in t.lines() + t.listen_lines():
                    add(ln.say, where)
    return sorted(seen.items(), key=lambda kv: kv[1])
