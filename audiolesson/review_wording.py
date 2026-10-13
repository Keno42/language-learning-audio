"""The written review asks in its own words (#312).

A plan's ``review`` question takes its prompt from the lesson exercise that practised the item. For a generated sentence that is the lesson's spoken cue
(«Put it together yourself. Say: …», «In a sentence. Say: …», «Use the pattern again. Say: …», «Your turn. Say: …»). Those cues tell the listener how the
exercise relates to the one before it; read the next morning one question at a time there is no exercise before, and the cue is noise or a false link.
So every prompt that is a lesson cue becomes the meaning in the review's own form («How do you say: …»); a situation, and any other prompt, is kept.
"""

from __future__ import annotations

import re

from .prompts import Prompts

# the prompt keys that are the lesson's cues about how an exercise relates to the one before (and the hint / cloze lead-ins, which rely on audio)
LESSON_CUE_KEYS = ("recombine_new", "recombine", "recombine_again", "recombine_vocab", "recombine_vocab_again", "hinted", "cloze")


def _templates(prompts: Prompts) -> list[re.Pattern]:
    out = []
    for key in LESSON_CUE_KEYS:
        val = prompts.data.get(key)
        for t in val if isinstance(val, list) else ([val] if val else []):
            if "{meaning}" not in t:
                continue
            before, after = t.split("{meaning}", 1)
            out.append(re.compile(rf"^{re.escape(before)}(?P<meaning>.+?){re.escape(after)}$", re.S))
    return out


def lesson_cue_meaning(prompt: str, prompts: Prompts) -> str | None:
    """The meaning inside a prompt that is a lesson cue, else None."""
    for pattern in _templates(prompts):
        m = pattern.match(prompt.strip())
        if m:
            return m.group("meaning")
    return None


def review_prompt(prompt: str, prompts: Prompts, target_lang: str) -> str:
    """The prompt as the review asks it: a lesson cue becomes the meaning in the review's form (the first «meaning» wording, so it is the same every time), anything else is kept."""
    meaning = lesson_cue_meaning(prompt, prompts)
    if meaning is None:
        return prompt
    val = prompts.data["meaning"]
    template = val[0] if isinstance(val, list) else val
    return template.format(meaning=meaning, language=prompts.language_name(target_lang))


def reword_review(review: list[dict], prompts: Prompts, target_lang: str) -> list[dict]:
    """``review`` with every lesson-cue prompt in the review's own words (new dicts; the input is not changed)."""
    return [{**q, "prompt": review_prompt(q["prompt"], prompts, target_lang)} if isinstance(q.get("prompt"), str) else q for q in review]


def lesson_cue_count(review: list[dict], prompts: Prompts) -> int:
    """The daily read's row: review prompts that still carry a lesson cue (0 expected)."""
    return sum(1 for q in review if isinstance(q.get("prompt"), str) and lesson_cue_meaning(q["prompt"], prompts) is not None)
