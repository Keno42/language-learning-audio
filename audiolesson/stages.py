"""Retrieval-difficulty ladder.

Each item climbs these stages as its memory strengthens. The planner asks for
the next stage; ``exercises`` knows how to build a prompt for each one.

    intro      listen, repeat (backward build for hard phrases)
    cloze      hear the phrase minus its last word; complete it
    hinted     produce from meaning with the first word as a hint
    meaning    produce from meaning alone
    situation  produce from a situation, not a translation
    recombine  use the construction / word inside a new sentence
    dialogue   respond inside a miniature conversation
"""

from __future__ import annotations

STAGES = ["intro", "cloze", "hinted", "meaning", "situation", "recombine", "dialogue"]

# Which stages apply to which kind of item, in climbing order.
LADDER: dict[str, list[str]] = {
    "vocab": ["intro", "meaning", "recombine", "dialogue"],
    "phrase": ["intro", "cloze", "hinted", "meaning", "situation", "dialogue"],
    "construction": ["intro", "hinted", "meaning", "recombine", "situation", "dialogue"],
    "transform": ["intro", "hinted", "meaning", "recombine"],
}

# Stages that only make sense if the item has the matching material.
CONDITIONAL = {"situation": "situation", "dialogue": "in_dialogue", "recombine": "recombinable"}


def ladder_for(kind: str, *, has_situation: bool, in_dialogue: bool, recombinable: bool, word_count: int) -> list[str]:
    caps = {"situation": has_situation, "in_dialogue": in_dialogue, "recombinable": recombinable}
    out = []
    for st in LADDER[kind]:
        need = CONDITIONAL.get(st)
        if need and not caps[need]:
            continue
        if st == "cloze" and word_count < 3:
            continue  # nothing to complete
        if st == "hinted" and word_count < 2:
            continue  # the first word of a one-word item is the whole answer
        out.append(st)
    return out


def stage_index(ladder: list[str], stage: str) -> int:
    return ladder.index(stage) if stage in ladder else 0


def next_stage(ladder: list[str], stage: str) -> str:
    i = stage_index(ladder, stage)
    return ladder[min(i + 1, len(ladder) - 1)]


def is_generative(stage: str) -> bool:
    return stage in ("situation", "recombine", "dialogue")
