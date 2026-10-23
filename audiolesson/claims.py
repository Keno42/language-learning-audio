"""Framing lines that promise something: «another sentence», «other words», «something new», «again».

The most frequent remark of the feedback was one of these said when what it promised did not follow, and each was fixed for its own prompt key
(#197, #263, #287, #303, #335, #357, #386, #387, #388). ``CLAIMS`` lists every promising key with what must hold for it; ``unkept_claims`` lists the
lines of a lesson whose promise does not hold (``meta.unkept_claims``, 0 expected; a row of ``tools/replay_lesson.py``). ``NO_CLAIM`` holds the keys
whose words read like a promise but promise nothing one lesson's script can show, each with the reason; a test keeps every such word of ``en.toml`` in
one of the two, so a new promising line is checked the day it is written.
"""

from __future__ import annotations

import re

from .prompts import Prompts
from .script import Script, Segment
from .text import norm_utterance

# what a promise needs (the target-language line meant is the next one the exercise says after the framing line)
ANOTHER = "another"  # the line is none of those the exercise said before the framing line («other words», «another sentence», #388)
AGAIN = "again"  # the exercise just before practised the same item (#287)
REPLAY = "replay"  # the line is one the exercise said before the framing line («Listen again.», #335)
NEW = "new"  # the line is none of those said earlier in the lesson (#197)
# the exercise's item was not practised earlier in the lesson: a scene's line only heard («Here you would say:», ``heard_ids``, #263) and a note that names
# the item are not practice; the theme's first play comes before the lesson teaches its lines on purpose (LEARNING-DESIGN §9 "Themes")
NEW_ITEM = "new item"

CLAIMS = {
    "construction_of_known": ANOTHER,
    "construction_slot": ANOTHER,
    "embed_sentence": ANOTHER,
    "form_model_again": ANOTHER,
    "variant_form": ANOTHER,
    "connect_next": ANOTHER,
    "recombine_again": AGAIN,
    "recombine_again_lead": AGAIN,
    "recombine_vocab_again": AGAIN,
    "recombine_vocab_again_lead": AGAIN,
    "listen_again": REPLAY,
    "pick_out_again": REPLAY,
    "catch_unknown_again": REPLAY,
    "recombine_new": NEW,
    "recombine_new_lead": NEW,
    "intro_new": NEW_ITEM,
    "intro_whole": NEW,  # «A new expression»: the whole is new; its part may have been practised as a pattern's filler (lesson 19 of a simulated course: «eldfjall»)
}

NO_CLAIM = {
    "final_block": "names the closing block («today's new material»), not a line",
    "construction_of_known_later": "the line said when no other word follows: the other words are promised for later lessons (#388)",
    "construction_slot_later": "the same for a new pattern: no other word follows, so the other words are promised for later lessons",
    "listening_intro": "«a few new expressions»: the dialogue's lines the learner has not learned, which the learner's state holds, not the script (H8)",
    "listening_intro_some_asked": "the same, with lines the learner knows asked (#240)",
    "listening_intro_known": "«The conversation again.»: a scene played in an earlier lesson (#263), which one lesson's script does not show",
}

_SPEECH_EXCEPT = ("partial", "hint", "spaced")  # a cloze fragment, a first-word hint, a line said word by word: not a line of their own


def _pattern(template: str) -> re.Pattern:
    """A prompt as said: its placeholders filled with anything; matched from the start, so a lead («Now something you haven't heard yet.») is found
    before the scene that takes the place of its «Say: …»."""
    parts = re.split(r"\{[a-z_]+\}", template)
    return re.compile(".+?".join(re.escape(p) for p in parts), re.DOTALL)


def _templates(prompts: Prompts, key: str) -> list[str]:
    val = prompts.data.get(key)
    return [] if val is None else [val] if isinstance(val, str) else list(val)


def _labels(prompts: Prompts) -> list[str]:
    """«As a woman: » / «As a man: »: the gender label ``speak_as`` puts in front of a prompt."""
    return [t.split("{prompt}")[0] for g in ("f", "m") for t in _templates(prompts, f"speak_as_{g}") if "{prompt}" in t and t.split("{prompt}")[0]]


def claim_of(text: str, prompts: Prompts, patterns: list[tuple[str, re.Pattern]] | None = None) -> str | None:
    """The key of ``CLAIMS`` a narrated line says, its gender label aside; None when it promises nothing."""
    for label in _labels(prompts):
        if text.startswith(label):
            text = text[len(label):]
            break
    for key, pat in patterns if patterns is not None else _claim_patterns(prompts):
        if pat.match(text):
            return key
    return None


def _claim_patterns(prompts: Prompts) -> list[tuple[str, re.Pattern]]:
    return [(key, _pattern(t)) for key in CLAIMS for t in _templates(prompts, key)]


def _is_line(g: Segment, target_lang: str) -> bool:
    return g.type in ("speak", "answer") and g.lang == target_lang and bool(g.text) and g.role not in _SPEECH_EXCEPT


def unkept_claims(sc: Script, prompts: Prompts) -> list[str]:
    """«label: line» for each framing line of ``sc`` whose promise (``CLAIMS``) does not hold."""
    patterns = _claim_patterns(prompts)
    segs = sc.segments
    out = []
    for k, g in enumerate(segs):
        if g.type != "narrate" or g.exercise is None or not g.text:
            continue
        key = claim_of(g.text, prompts, patterns)
        if key is None:
            continue
        ex = sc.exercises[g.exercise]
        need = CLAIMS[key]
        if need == AGAIN:
            kept = ex.index > 0 and bool(ex.item_ids) and ex.item_ids[0] in sc.exercises[ex.index - 1].item_ids
        elif need == NEW_ITEM:
            kept = bool(ex.item_ids) and not any(ex.item_ids[0] in e.item_ids for e in sc.exercises[:ex.index] if e.kind != "note")
        else:
            nxt = next((s for s in segs[k + 1:] if s.exercise == ex.index and _is_line(s, sc.target_lang)), None)
            if nxt is None:
                kept = False
            else:
                said = norm_utterance(nxt.text)
                before = segs[:k] if need == NEW else [s for s in segs[:k] if s.exercise == ex.index]
                heard = {norm_utterance(s.text) for s in before if _is_line(s, sc.target_lang)}
                kept = said in heard if need == REPLAY else said not in heard
        if not kept:
            out.append(f"{ex.label}: {g.text}")
    return out
