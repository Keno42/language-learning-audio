"""#281 finding 1: which sentence holds a part, decided in one place.

Introduction (``Builder.whole_home``, ``Builder.phrase_home``), the planner before it (``Planner.embed_source``) and the written review
(``review_wholes.whole_for``, ``review_wholes.has_home``) each looked for a part's sentence with their own copy of two searches. They are here:

- ``holds``: a line's words hold the part's words, in order and together («hjálpina» in «Takk fyrir hjálpina.»);
- ``fill_slots``: a pattern whose slot takes the part, its other slots filled from the authored fills first, else the first item of the slot's tag
  that ``ok`` accepts («Ég ætla að fá {food}.» filled with «köku»).

Each caller keeps its own policy (what counts as available, how the candidates are ranked)."""
from __future__ import annotations

from typing import Callable

from .text import WORD


def words(text: str) -> list[str]:
    """The lower-case words of ``text`` (no digits, no punctuation)."""
    return [w.lower() for w in WORD.findall(text)]


def holds(whole_words: list[str], part_words: list[str], longer: bool = False) -> bool:
    """Whether ``part_words`` sit in ``whole_words`` in order and together; ``longer``: and the whole has more words than the part."""
    n = len(part_words)
    if not part_words or (longer and len(whole_words) <= n):
        return False
    return any(whole_words[i : i + n] == part_words for i in range(len(whole_words) - n + 1))


def fill_slots(cur, construction, part, ok: Callable[[str], bool]) -> dict | None:
    """``{slot: item}`` for ``construction`` with ``part`` in the first slot that takes it and every other slot filled: the authored fill
    (``situation_fill``, else ``example``) when ``ok`` accepts it, else the first item of the slot's tag that ``ok`` accepts. None when no slot
    takes the part or a slot has no fill."""
    slot = next((s for s, tag in construction.slots.items() if cur.takes(tag, construction, part)), None)
    if slot is None:
        return None
    fills = {slot: part}
    for other, tag in construction.slots.items():
        if other == slot:
            continue
        ref = construction.situation_fill.get(other) or construction.example.get(other)
        pick = cur.by_id.get(ref) if ref and ok(ref) else None
        pick = pick or next((i for i in cur.items_with_tag(tag, construction) if ok(i.id)), None)
        if pick is None:
            return None
        fills[other] = pick
    return fills
