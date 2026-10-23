"""The review asks each target expression once, and a part only through the whole that holds it (#239, concept 1, §9 "Parts against utterances").

The lesson-21 review asked «hjálpina» ("for the help") bare, a part next to the whole that holds it («tvo fullorðna» beside
«Tvo fullorðna, takk.»), and one answer twice («Eigðu góðan dag.» through two items). ``refine_review`` is applied to the questions of
``plan.json`` ``review`` and does three things, in this order:

1. A part's question whose part sits inside the answer of another question is dropped, and the part is credited to that question.
2. A part asked bare, with a whole the learner knows (a construction filled with the part, or a phrase that holds it), is asked through
   that whole: the sentence's meaning is the cue and the sentence the answer. A part that has no home at all in the curriculum (#215: no slot takes
   it, no construction lists it as a prerequisite, no phrase holds its words) can't be asked as one: it comes out of the review and is
   reported. A part whose homes are all unmet stays bare, the fallback when no sentence exists.
   A part whose cue is its own answer (a name, «krónur») and has no whole is a trivial question (#277) and comes out as well.
3. No two questions share an answer: the later one's items are credited to the first.

A *part* is a vocab item; a construction, a phrase or a transform is a complete thing to say.
"""

from __future__ import annotations

import re

from .exercises import _norm_utterance, answer_gender, cue_is_answer, meaning_prompts, speak_as
from .prompts import Prompts
from .review_wording import restore_transform_sources, speaker_form
from .text import WORD

_WORD = WORD


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _holds(sentence_words: list[str], part_words: list[str]) -> bool:
    n = len(part_words)
    return bool(part_words) and any(sentence_words[i : i + n] == part_words for i in range(len(sentence_words) - n + 1))


def _holds_inflected(sentence_words: list[str], part_words: list[str]) -> bool:
    """A long one-word part inside a longer form of itself («norðurljós» in «norðurljósin»): the definite and other endings are the part's own."""
    return len(part_words) == 1 and len(part_words[0]) >= 6 and any(w != part_words[0] and w.startswith(part_words[0]) for w in sentence_words)


def _phrase_holds(phrase_words: list[str], part_words: list[str]) -> bool:
    return _holds(phrase_words, part_words) or _holds_inflected(phrase_words, part_words)


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
        elif c.kind == "phrase" and _phrase_holds(_words(c.target), part_words):
            return True
    return False


def whole_for(cur, part, met: set[str], prompts: Prompts, taught: dict | None = None) -> dict | None:
    """The sentence the learner knows that holds ``part``: ``{"prompt", "answer", "through"}`` or None. A construction filled with the part (and
    fills the learner has met for its other slots) comes first, the one whose authored situation or example names the part before the rest;
    then the shortest phrase that holds the part's words. ``taught`` is the sentence the part came in with today (``Builder.wholes_taught``): when its
    pattern is not met yet it is asked exactly as taught, never rebuilt with other words (#262 review); and when nothing else holds the part (a line
    such as «þúsund krónur» is neither a pattern nor a phrase), it is asked as taught too. A sentence whose words follow the speaker's gender names the
    form it expects («As a woman: …»), as the lesson does."""

    def ask(meaning: str, answer: str, *made_of) -> str:
        prompt = meaning_prompts(Prompts(prompts.data, prompts.lang), cur.known_lang, cur.target_lang, meaning)[0]
        return speak_as(prompts, answer_gender(answer, *speaker_items(cur, answer, [part, *made_of])), prompt)

    as_taught = lambda: {
        "prompt": ask(taught["meaning"], taught["answer"], cur.by_id.get(taught["through"])),
        "answer": taught["answer"],
        "through": taught["through"],
    }
    if taught and taught["through"] not in met:
        return as_taught()
    options: list[tuple] = []
    for c in cur.items:
        if c.kind != "construction" or not (c.id in met) or not c.slots:
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
            options.append(((rank, c.difficulty, c.order), target, meaning, c.id, [c, *fills.values()]))
    if options:
        _, target, meaning, through, made_of = min(options, key=lambda o: o[0])
    else:
        part_words = _words(part.target)
        phrases = [p for p in cur.items if p.kind == "phrase" and p.id in met and _phrase_holds(_words(p.target), part_words)]
        if not phrases:
            return as_taught() if taught else None
        phrase = min(phrases, key=lambda p: (len(_words(p.target)), p.order))
        target, meaning, through, made_of = phrase.target, phrase.spoken_meaning, phrase.id, [phrase]
    return {"prompt": ask(meaning, target, *made_of), "answer": target, "through": through}


def refine_review(review: list[dict], cur, met: set[str], prompts: Prompts, wholes_taught: dict[str, dict] | None = None) -> tuple[list[dict], list[dict]]:
    """The review with every part asked through its whole, no part beside its whole and no two questions with one answer; and a report of
    what was changed. Bonus questions are left alone. See the module docstring for the rules."""
    out, report = restore_transform_sources(review, cur, prompts)

    # 0. a sentence to the person spoken to in the form its meaning names: «Ertu þreyttur?», made before #385's review as «As a man: To a woman: …»,
    # is «Ertu þreytt?» (review of #385). Found from the answer itself: the bot stores no ``through``.
    for k, q in enumerate(out):
        answer = q.get("answer")
        fixed = addressee_answer(cur, answer) if isinstance(answer, str) else answer
        if fixed != answer:
            out[k] = {**q, "answer": fixed}
            report.append({"items": q.get("items", []), "kind": "addressee_form", "was": answer, "now": fixed})

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
        whole = whole_for(cur, part, met, prompts, (wholes_taught or {}).get(part.id))
        if whole is not None:
            report.append({"items": q["items"], "kind": "through_whole", "was": q["answer"], "now": whole["answer"]})
            q["prompt"], q["answer"], q["through"] = whole["prompt"], whole["answer"], whole["through"]
        elif cue_is_answer(part):
            out.remove(q)
            report.append({"items": q["items"], "kind": "trivial", "answer": q["answer"]})
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

    # 4. the speaker's form the answer expects, on every question whose answer has a woman's and a man's form, the stored ones included («How do you
    # say: I'm hungry.» → «Ég er svöng.» kept from an earlier lesson): from its items, the sentence it was asked through, the fillers of a pattern it
    # names, and its answer (lesson 33, review of #375; lesson 34: a pattern sentence stored with the pattern alone, «Ég er svangur.» of «Ég er {state}.»)
    for k, q in enumerate(out):
        prompt, answer = q.get("prompt"), q.get("answer")
        if not isinstance(prompt, str) or not isinstance(answer, str):
            continue
        ids = [*q.get("items", []), q.get("through") or ""]
        gender = answer_gender(answer, *made_of(cur, ids, answer))
        named, rest = speaker_form(prompt, prompts)
        if gender is not None and named != gender:
            out[k] = {**q, "prompt": speak_as(prompts, gender, rest)}
            report.append({"items": q.get("items", []), "kind": "speaker_form", "form": gender})
        elif gender is None and named is not None and _addressed_fills(cur, answer):
            # «As a woman: …» on «Ertu þreytt?»: the form follows the woman asked, whom the cue already names (review of #385)
            out[k] = {**q, "prompt": rest}
            report.append({"items": q.get("items", []), "kind": "speaker_form", "form": None})
    return out, report



def _template_form(construction, answer: str) -> str | None:
    """The form of ``construction`` whose template ``answer`` is («Ertu þreytt?» of «Ertu {state}?»: "plain"), or None."""
    said = answer.strip().lower()
    for form in (None, *construction.forms):
        template = construction.form_templates(form)[0]
        pattern = re.sub(r"\\\{[^}]*\\\}", "(.+?)", re.escape(template.strip().lower()))
        if re.fullmatch(pattern, said):
            return form or "plain"
    return None


def _addressed(cur, answer: str) -> list:
    """The patterns whose subject is the person spoken to and whose template of that kind ``answer`` is («Ertu þreytt?» of «Ertu {state}?»). Read from
    the answer, not from the question's items: the bot stores no ``through``, and a part's question names only the part (review of #385)."""
    return [c for c in cur.items if c.kind == "construction" and c.addressee and (form := _template_form(c, answer)) is not None and not cur.speaker_agrees(c, form)]


def _addressed_fills(cur, answer: str) -> set[str]:
    """The fills of the patterns ``_addressed`` finds: their man's or woman's form follows the person spoken to, not the speaker («Ertu þreytt?» asks a
    woman)."""
    return {f.id for c in _addressed(cur, answer) for tag in c.slots.values() for f in cur.items_with_tag(tag, c)}


def addressee_answer(cur, answer: str) -> str:
    """``answer`` in the form its pattern's meaning names, when it is a sentence to the person spoken to: a fill said in its man's form there
    («Ertu þreyttur?», made before #385's review alternated it) takes the stored form («Ertu þreytt?», «To a woman: Are you tired?»)."""
    for c in _addressed(cur, answer):
        for f in (f for tag in c.slots.values() for f in cur.items_with_tag(tag, c) if f.target_m):
            fixed = re.sub(rf"(?<!\w){re.escape(f.target_m)}(?!\w)", f.target, answer, flags=re.IGNORECASE)
            if fixed != answer:
                return fixed
    return answer


def speaker_items(cur, answer: str, items: list) -> list:
    """``items`` without the fills whose form follows the person spoken to: what ``answer_gender`` reads the speaker's form from."""
    drop = _addressed_fills(cur, answer)
    return [it for it in items if it is not None and it.id not in drop]


def made_of(cur, ids: list[str], answer: str = "") -> list:
    """The items a question's answer can be made of, as far as they follow the speaker: its own items, and for a pattern among them, the fillers of
    its slots. A question stored with the pattern alone («Ég er {state}.» for «Ég er svangur.») still shows which filler, and so which speaker's
    form, its answer holds. A pattern whose subject is the person spoken to («Ertu {state}?») gives none, and takes its fillers out (review of #385)."""
    found = [cur.by_id[i] for i in ids if i in cur.by_id]
    for it in list(found):
        if it.kind == "construction":
            found += [f for tag in it.slots.values() for f in cur.items_with_tag(tag, it)]
    return speaker_items(cur, answer, found)

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


def bare_parts_with_a_home(review: list[dict], cur) -> list[str]:
    """The daily read's row for #262: the parts the review still asks bare (the answer is the part itself) although the curriculum keeps them in a sentence
    (``has_home``). A part with no home is not counted here: it comes out of the review (#215)."""
    out = []
    for q in review:
        if q.get("bonus"):
            continue
        for i in q.get("items", []):
            it = cur.by_id.get(i)
            if it is not None and it.kind == "vocab" and _norm_utterance(it.target) == _norm_utterance(q.get("answer", "")) and has_home(cur, it):
                out.append(i)
    return list(dict.fromkeys(out))
