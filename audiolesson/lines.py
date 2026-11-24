"""Whether a learner's line is one they have said before (#272), decided once for every play mode (#281 finding 2).

The planner owns this decision, as it owns ``Planner.line_role`` (ask or hear): ``Planner.reply_familiarity`` calls ``familiarity`` and hands it to
the builder (``Builder.reply_familiarity``), which only renders the reply pause it sets. A builder used on its own calls ``familiarity`` too, so the
rule is written once.
"""

from __future__ import annotations

import re

from .content import Curriculum, Item
from .learner import LearnerState
from .text import WORD


def said_before(learner: LearnerState, ids: list[str]) -> bool:
    """Whether the learner has said this line before: every item of it met and none open (#272)."""
    return bool(ids) and all(learner.has_met(i) and not learner.is_open(i) for i in ids)


def items_holding(cur: Curriculum, learner: LearnerState, text: str) -> list[Item] | None:
    """The met, not open items whose words cover every word of ``text`` (#272 review): the items a literal line is made of. None when a word is
    not theirs."""
    words = [w.lower() for w in WORD.findall(text)]
    if not words:
        return None
    held: dict[str, Item] = {}
    for it in cur.items:
        if it.kind == "transform" or not learner.has_met(it.id) or learner.is_open(it.id):
            continue
        for t in (re.split(r"\{[^}]*\}", it.target) if it.kind == "construction" else [it.target]):
            for w in WORD.findall(t):
                held.setdefault(w.lower(), it)
    if any(w not in held for w in words):
        return None
    return list({held[w].id: held[w] for w in words}.values())


def familiarity(cur: Curriculum, learner: LearnerState, ids: list[str], text: str, literal: bool) -> tuple[list[str], bool]:
    """A learner's line as the reply pause sees it: its items, and whether the learner has said it before. A ``literal`` line (``expect_text``)
    with no items named is taken as the met items its words come from (#272 review)."""
    if literal and not ids and (made_of := items_holding(cur, learner, text)) is not None:
        ids = [i.id for i in made_of]
    return ids, said_before(learner, ids)
