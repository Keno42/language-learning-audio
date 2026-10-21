"""The written review asks in its own words (#312).

A plan's ``review`` question takes its prompt from the lesson exercise that practised the item. For a generated sentence that is the lesson's spoken cue
(«Put it together yourself. Say: …», «In a sentence. Say: …», «Use the pattern again. Say: …», «Your turn. Say: …»). Those cues tell the listener how the
exercise relates to the one before it; read the next morning one question at a time there is no exercise before, and the cue is noise or a false link.
So every prompt that is a lesson cue becomes the meaning in the review's own form («How do you say: …»); a situation, and any other prompt, is kept.
"""

from __future__ import annotations

import re

from .prompts import Prompts
from .text import norm_utterance

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


def speaker_form(prompt: str, prompts: Prompts) -> tuple[str | None, str]:
    """``(gender, the rest)`` of a prompt that names the speaker's form («As a woman: …»), else ``(None, prompt)``."""
    for gender in ("f", "m"):
        template = prompts.data.get(f"speak_as_{gender}")
        if isinstance(template, str) and "{prompt}" in template:
            before, after = template.split("{prompt}", 1)
            if prompt.startswith(before) and prompt.endswith(after) and len(prompt) > len(before) + len(after):
                return gender, prompt[len(before) : len(prompt) - len(after)]
    return None, prompt


def lesson_cue_meaning(prompt: str, prompts: Prompts) -> str | None:
    """The meaning inside a prompt that is a lesson cue, else None; behind the speaker's form too («As a man: In a sentence. Say: …»)."""
    rest = speaker_form(prompt.strip(), prompts)[1]
    for pattern in _templates(prompts):
        m = pattern.match(rest.strip())
        if m:
            return m.group("meaning")
    return None


def review_prompt(prompt: str, prompts: Prompts, target_lang: str) -> str:
    """The prompt as the review asks it: a lesson cue becomes the meaning in the review's form (the first «meaning» wording, so it is the same every time), anything else is kept.
    The speaker's form in front of it stays («As a man: How do you say: …»): the answer's words depend on it."""
    meaning = lesson_cue_meaning(prompt, prompts)
    if meaning is None:
        return prompt
    val = prompts.data["meaning"]
    template = val[0] if isinstance(val, list) else val
    gender = speaker_form(prompt.strip(), prompts)[0]
    reworded = template.format(meaning=meaning, language=prompts.language_name(target_lang))
    return prompts.get(f"speak_as_{gender}", prompt=reworded) if gender else reworded


def reword_review(review: list[dict], prompts: Prompts, target_lang: str) -> list[dict]:
    """``review`` with every lesson-cue prompt in the review's own words (new dicts; the input is not changed)."""
    return [{**q, "prompt": review_prompt(q["prompt"], prompts, target_lang)} if isinstance(q.get("prompt"), str) else q for q in review]


def lesson_cue_count(review: list[dict], prompts: Prompts) -> int:
    """The daily read's row: review prompts that still carry a lesson cue (0 expected)."""
    return sum(1 for q in review if isinstance(q.get("prompt"), str) and lesson_cue_meaning(q["prompt"], prompts) is not None)


def restore_transform_sources(review: list[dict], cur, prompts: Prompts) -> tuple[list[dict], list[dict]]:
    """Repair legacy instruction-only questions using a unique authored input for their saved answer.

    Already complete questions are left alone. Missing or ambiguous matches are reported for
    inspection; never choose another example's input or change the saved answer.
    """
    out, report = [], []
    for original in review:
        q = dict(original)
        out.append(q)
        prompt, answer = q.get("prompt"), q.get("answer")
        if q.get("bonus") or not isinstance(prompt, str) or not isinstance(answer, str):
            continue
        sources: set[str] = set()
        matched_instruction = False
        for item_id in q.get("items", []):
            item = cur.by_id.get(item_id)
            if item is None or item.kind != "transform":
                continue
            for example in item.examples:
                genders = ("f", "m") if example.source_m or example.result_m else (None,)
                for gender in genders:
                    instruction = item.instruction
                    if example.result_m:
                        instruction = prompts.get(f"speak_as_{gender}", prompt=instruction)
                    if prompt.strip() != instruction.strip():
                        continue
                    matched_instruction = True
                    result = example.result_m if gender == "m" and example.result_m else example.result
                    if norm_utterance(answer) == norm_utterance(result):
                        source = example.source_m if gender == "m" and example.source_m else example.source
                        sources.add(source)
        if not matched_instruction:
            continue
        if len(sources) == 1:
            q["prompt"] = f"{prompt.rstrip()}\n{next(iter(sources))}"
            report.append({"items": q["items"], "kind": "transform_source_restored"})
        else:
            report.append({"items": q["items"], "kind": "transform_source_unresolved", "matches": len(sources)})
    return out, report
