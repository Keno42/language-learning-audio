"""Words and normalised lines: the one place the planner, builder, review and tools agree on what a word is (#281).

``WORD`` matches a run of letters: digits and underscores are not part of a word («Klukkan 5» has one word). Places where digits matter keep their own
``\\w+`` and say so (``timing``).
"""

from __future__ import annotations

import re

WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def words(text: str, lower: bool = False) -> list[str]:
    """The words of ``text`` in order; lower-cased when ``lower``."""
    found = WORD.findall(text)
    return [w.lower() for w in found] if lower else found


def norm_utterance(text: str) -> str:
    """Case- and trailing-punctuation-insensitive form of a target-language line."""
    return text.strip().rstrip(".?!…").strip().lower()
