"""Hard-to-say words (#212, H13): a word whose sounds the learner stumbles on gets a slow, split model at its introduction.

The signal is a small set of sound rules on the letters of a one-word target of two or more syllables. ``ll`` (pre-stopped: «fallegt» is [fatlɛxt]) and ``ý`` belong to the
reading deck's letters rules (`curricula/is-en/reading/deck.toml`, ``graphemes``; a test keeps them in step); ``tt`` (pre-aspirated, «nýtt», «hættulegt») and
``fj`` («fjall», «fjórir») are the learner's own remarks (lessons 16 and 23) and are not cards of the deck yet. The ending «-ið» («flugið») is not a rule here: it ends every neuter definite
form (a quarter of the flagged words), so it would flag too much. The rules read letters, so a loanword or a name said much as in English or
Japanese («latte», «Tókýó») is marked ``sounds_familiar`` and left out (lesson 35: «latte needs no slow split»). An item carries its authored syllables
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
    """The sound rules the target of ``item`` holds: a one-word vocab item of two or more syllables, not ``sounds_familiar``. Empty for everything else."""
    if item.kind != "vocab" or item.word_count != 1 or item.target_m or item.sounds_familiar:
        return []
    word = item.target.lower().strip(".?!")
    if len(_VOWELS.findall(word)) < 2:
        return []
    return [name for name, rx in HARD_SOUNDS.items() if rx.search(word)]


# the letter pairs of a rule that a split must keep inside one piece: said apart, «hæt» + «tu» or «fal» + «legt» are an ordinary t and l (#212 review)
CLUSTERS = ("ll", "tt", "fj")


def split_breaks_a_cluster(syllables: list[str]) -> str | None:
    """The cluster ("tt") that two neighbouring syllables cut between them, or None."""
    for a, b in zip(syllables, syllables[1:]):
        pair = (a[-1:] + b[:1]).lower()
        if pair in CLUSTERS:
            return pair
    return None


# #337: sounds Icelandic spells unlike English or Japanese, from the learner's remarks (lesson 26). They are NOT introduction rules (``ð`` alone is in a quarter
# of the vocabulary, as «-ið» was): they pick the hard word of an item the learner has reported hard, where the signal is the report.
_V = "aáæeéiíoóöuúyý"
REPORTED_SOUNDS = {
    "ei": re.compile(r"ei"),
    "ng": re.compile(rf"ng(?=[{_V}])"),
    "ð": re.compile(r"ð"),
    "g": re.compile(rf"(?<=[{_V}])g(?=[{_V}])"),
}
_WORDS = re.compile(r"[^\W\d_]+")
_SLOT = re.compile(r"\{[^{}]*\}")


def hard_words_of(item, reported: bool = False) -> list[tuple[str, list[str] | None]]:
    """The words of ``item`` to model slowly, each with its authored syllables (None: the word slowly, whole) (#337).

    A phrase with ``word_syllables`` names its hard words itself, in the order of the phrase. A one-word vocab item is its own word (its ``syllables``, when
    authored). With ``reported`` (the learner reported the item hard) an item with none authored takes the one word of two or more syllables with the most of the
    old and the reported sounds, the longest on a tie; an item of one word that holds none of them is its own word, so an explicit request is never dropped
    (lesson 42: «regnhlíf» reported hard to say got nothing). Empty when nothing qualifies (a pattern; a sentence, which ``Builder.hearing_line`` models whole).
    """
    if item.kind not in ("phrase", "vocab"):
        return []  # a pattern's target holds slot names ({thing}, {language}) that are not words, and is not said bare
    if item.kind == "phrase" and item.word_syllables:
        seen: list[tuple[str, list[str] | None]] = []
        for w in _WORDS.findall(item.target.lower()):
            if w in item.word_syllables and all(w != x for x, _ in seen):
                seen.append((w, list(item.word_syllables[w])))
        return seen
    if item.kind == "vocab" and item.word_count == 1 and item.syllables:
        return [(item.target.lower().strip(".?!"), list(item.syllables))]
    if not reported:
        return []
    best = None
    for w in _WORDS.findall(_SLOT.sub(" ", item.target).lower()):
        if len(_VOWELS.findall(w)) < 2:
            continue
        hits = sum(1 for rx in (*HARD_SOUNDS.values(), *REPORTED_SOUNDS.values()) if rx.search(w))
        if hits and (best is None or (hits, len(w)) > best[0]):
            best = ((hits, len(w)), w)
    if best:
        return [(best[1], None)]
    words = _WORDS.findall(_SLOT.sub(" ", item.target).lower())
    return [(words[0], None)] if len(words) == 1 else []
