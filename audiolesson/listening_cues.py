"""Locate an unknown word through the understood meaning (#248, concept 3)."""

from __future__ import annotations

import re


def unknown_cue(line_meaning: str, gloss: dict, known_lang: str) -> tuple[str, str] | None:
    """Return an authored pointer, or the meaning with exactly one gloss masked.

    Authors may supply a pointer for verbs or idioms whose literal masking would
    make the cue hard to understand. Validation and task selection share this rule.
    """
    lang = known_lang.split("-")[0].lower()
    pointer = (gloss.get("pointer") or {}).get(lang)
    if isinstance(pointer, str) and pointer.strip():
        return "pointer", pointer.strip()
    meaning = gloss.get(lang)
    if not isinstance(meaning, str) or not meaning.strip() or not line_meaning.strip():
        return None
    pattern = re.escape(meaning.strip())
    if lang == "en":
        pattern = rf"(?<!\w){pattern}(?!\w)"
    matches = list(re.finditer(pattern, line_meaning, flags=re.IGNORECASE))
    if len(matches) != 1:
        return None
    match = matches[0]
    blank = "何か" if lang == "ja" else "something"
    return "context", line_meaning[:match.start()] + blank + line_meaning[match.end():]
