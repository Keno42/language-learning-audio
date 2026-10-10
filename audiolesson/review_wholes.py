"""The review asks each target expression once, and a part only through the whole that holds it (#239, concept 1, §9 "Parts against utterances").

The lesson-21 review asked «hjálpina» ("for the help") bare, a part next to the whole that holds it («tvo fullorðna» beside
«Tvo fullorðna, takk.»), and one answer twice («Eigðu góðan dag.» through two items). ``refine_review`` is applied to the questions of
``plan.json`` ``review`` and does three things, in this order:

1. A part's question whose part sits inside the answer of another question is dropped, and the part is credited to that question.
2. A part asked bare, with a whole the learner knows (a construction filled with the part, or a phrase that holds it), is asked through
   that whole: the sentence's meaning is the cue and the sentence the answer. A part that has no home at all in the curriculum (#215: no slot takes
   it, no construction lists it as a prerequisite, no phrase holds its words) can't be asked as one: it comes out of the review and is
   reported. A part whose homes are all unmet stays bare, the fallback when no sentence exists.
3. No two questions share an answer: the later one's items are credited to the first.

A *part* is a vocab item; a construction, a phrase or a transform is a complete thing to say.
"""

from __future__ import annotations

import re

from .exercises import _norm_utterance, meaning_prompts
from .prompts import Prompts

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _holds(sentence_words: list[str], part_words: list[str]) -> bool:
    n = len(part_words)
    return bool(part_words) and any(sentence_words[i : i + n] == part_words for i in range(len(sentence_words) - n + 1))


def _holds_inflected(sentence_words: list[str], part_words: list[str]) -> bool:
    """A long one-word part inside a longer form of itself («norðurljós» in «norðurljósin»): the definite and other endings are the part's own."""
    return len(part_words) == 1 and len(part_words[0]) >= 6 and any(w != part_words[0] and w.startswith(part_words[0]) for w in sentence_words)


def has_home(cur, part) -> bool:
    """Whether the curriculum keeps ``part`` in a sentence anywhere: a construction slot takes its tags, a construction lists it as a prerequisite
    or a phrase holds its words (#215's definition)."""
    part_words = _words(part.target)
    for c in cur.items:
        if c.id == part.id:
            continue
        if c.kind == "construction":
            if part.id in c.prereqs or any(part in cur.items_with_tag(tag, c) for tag in c.slots.values()):
                return True
        elif c.kind == "phrase" and (_holds(_words(c.target), part_words) or _holds_inflected(_words(c.target), part_words)):
            return True
    return False


def whole_for(cur, part, met: set[str], prompts: Prompts) -> dict | None:
    """The sentence the learner knows that holds ``part``: ``{"prompt", "answer", "through"}`` or None. A construction filled with the part (and
    fills the learner has met for its other slots) comes first, the one whose authored situation or example names the part before the rest;
    then the shortest phrase that holds the part's words."""
    options: list[tuple] = []
    for c in cur.items:
        if c.kind != "construction" or c.id not in met or not c.slots:
            continue
        slot = next((s for s, tag in c.slots.items() if part in cur.items_with_tag(tag, c)), None)
        if slot is None:
            continue
        fills = {slot: part}
        for other, tag in c.slots.items():
            if other == slot:
                continue
            authored = c.situation_fill.get(other) or c.example.get(other)
            pick = cur.by_id.get(authored) if authored in met else None
            pick = pick or next((i for i in cur.items_with_tag(tag, c) if i.id in met), None)
            if pick is None:
                break
            fills[other] = pick
        else:
            rank = 0 if part.id in c.situation_fill.values() else 1 if part.id in c.example.values() else 2
            target, meaning = cur.resolve_slots(c, fills)
            options.append(((rank, c.difficulty, c.order), target, meaning, c.id))
    if options:
        _, target, meaning, through = min(options, key=lambda o: o[0])
    else:
        part_words = _words(part.target)
        phrases = [p for p in cur.items if p.kind == "phrase" and p.id in met and _holds(_words(p.target), part_words)]
        if not phrases:
            return None
        phrase = min(phrases, key=lambda p: (len(_words(p.target)), p.order))
        target, meaning, through = phrase.target, phrase.spoken_meaning, phrase.id
    prompt = meaning_prompts(Prompts(prompts.data, prompts.lang), cur.known_lang, cur.target_lang, meaning)[0]
    return {"prompt": prompt, "answer": target, "through": through}


def refine_review(review: list[dict], cur, met: set[str], prompts: Prompts) -> tuple[list[dict], list[dict]]:
    """The review with every part asked through its whole, no part beside its whole and no two questions with one answer; and a report of
    what was changed. Bonus questions are left alone. See the module docstring for the rules."""
    out = [dict(q) for q in review]
    report: list[dict] = []

    def part_of(q: dict):
        """The part a bare question asks, or None."""
        if q.get("bonus") or not q.get("items"):
            return None
        items = [cur.by_id.get(i) for i in q["items"]]
        if any(it is None or it.kind != "vocab" for it in items):
            return None
        answer = _norm_utterance(q.get("answer", ""))
        return next((it for it in items if _norm_utterance(it.target) == answer or (it.target_m and _norm_utterance(it.target_m) == answer)), None)

    def beside_whole() -> None:
        """1. a part beside the whole that holds it"""
        for q in list(out):
            part = part_of(q)
            if part is None:
                continue
            pw = _words(part.target)
            cover = next((o for o in out if o is not q and not o.get("bonus") and part_of(o) is None and _holds(_words(o.get("answer", "")), pw)), None)
            if cover is not None:
                cover["items"] = list(dict.fromkeys([*cover["items"], *q["items"]]))
                out.remove(q)
                report.append({"items": q["items"], "kind": "beside_whole", "answer": q["answer"], "whole": cover["answer"]})

    beside_whole()

    # 2. a bare part is asked through its whole, or has none
    for q in list(out):
        part = part_of(q)
        if part is None:
            continue
        whole = whole_for(cur, part, met, prompts)
        if whole is not None:
            report.append({"items": q["items"], "kind": "through_whole", "was": q["answer"], "now": whole["answer"]})
            q["prompt"], q["answer"], q["through"] = whole["prompt"], whole["answer"], whole["through"]
        elif not has_home(cur, part):
            out.remove(q)
            report.append({"items": q["items"], "kind": "no_home", "answer": q["answer"]})

    beside_whole()  # a whole made in step 2 may hold another bare part

    # 3. one answer, one question
    seen: dict[str, dict] = {}
    for q in list(out):
        if q.get("bonus"):
            continue
        key = _norm_utterance(q.get("answer", ""))
        first = seen.get(key)
        if first is None:
            seen[key] = q
            continue
        first["items"] = list(dict.fromkeys([*first["items"], *q["items"]]))
        out.remove(q)
        report.append({"items": q["items"], "kind": "same_answer", "answer": q["answer"]})
    return out, report


def parts_outside_their_whole(review: list[dict], cur) -> int:
    """The daily read's row 5: questions whose answer is a part asked next to the whole that holds it, or that share an answer with another."""
    bare = lambda q: next(
        (it for i in q.get("items", []) if (it := cur.by_id.get(i)) is not None and it.kind == "vocab" and _norm_utterance(it.target) == _norm_utterance(q.get("answer", ""))),
        None,
    )
    asked = [q for q in review if not q.get("bonus")]
    count = 0
    for q in asked:
        part = bare(q)
        if part is not None and any(o is not q and bare(o) is None and _holds(_words(o.get("answer", "")), _words(part.target)) for o in asked):
            count += 1
    answers = [_norm_utterance(q.get("answer", "")) for q in asked]
    return count + len(answers) - len(set(answers))
