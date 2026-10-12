"""Hard-to-say words (#212, H13): a word whose sounds the learner stumbles on gets a slow, split model at its introduction.

The signal is a small set of sound rules on the letters of a one-word target of two or more syllables. ``ll`` (pre-aspirated) and ``ý`` belong to the
reading deck's letters rules (`curricula/is-en/reading/deck.toml`, ``graphemes``; a test keeps them in step); ``tt`` (pre-aspirated, «nýtt», «hættulegt») and
``fj`` («fjall», «fjórir») are the learner's own remarks. The ending «-ið» («flugið») is not a rule here: it ends every neuter definite form (a quarter of the flagged words), so it would flag too much (lessons 16 and 23) and are not cards of the deck yet. An item carries its authored syllables
(``Item.syllables``, checked to make the word); without them it is given a slow whole-word repetition.
"""

from __future__ import annotations

import re

# rule name → what it looks for in a lower-cased one-word target
HARD_SOUNDS = {
    "ll": re.compile(r"ll"),
    "tt": re.compile(r"tt"),
    "fj": re.compile(r"fj"),
    "ý": re.compile(r"ý"),
}
# the rules that are cards of the reading deck (the others are the learner's remarks, not yet cards)
DECK_RULES = ("ll", "ý")
_VOWELS = re.compile(r"[aáæeéiíoóöuúyý]+")


def hard_sounds(item) -> list[str]:
    """The sound rules the target of ``item`` holds: a one-word vocab item of two or more syllables. Empty for everything else."""
    if item.kind != "vocab" or item.word_count != 1 or item.target_m:
        return []
    word = item.target.lower().strip(".?!")
    if len(_VOWELS.findall(word)) < 2:
        return []
    return [name for name, rx in HARD_SOUNDS.items() if rx.search(word)]
