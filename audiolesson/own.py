"""#428 (the owner, 2026-11-25: «a lesson-configure option»): the learner's own name and age in the lines they say about themselves.

The course is written for a persona: her name is ``PERSONA_NAME`` («Ég heiti Yuki.», «Á nafninu Yuki.») and she says she is twenty. With
``--own-name`` the learner's lines that hold the persona's name say theirs instead, and with ``--own-age`` the line where they give their age
says theirs, when the course has their age as an item (an age the learner can be taught to say); otherwise it stays the persona's.

Only the learner's own lines change: an item whose text holds the persona's name, an authored dialogue's learner turn, a theme's learner turn.
A partner's line, a note and every other number exercise are left as they are; nothing is replaced across the course as a string. The values
are personal: they live in the bot's user settings and in this lesson's script, and the bot's export puts the persona's back (#428)."""
from __future__ import annotations

import dataclasses
import re

PERSONA_NAME = "Yuki"
PERSONA_NAME_JA = "ユキ"
NAME_RE = re.compile(r"^(?=.{1,24}$)[^\W\d_]+(?:['\-][^\W\d_]+)*$")
AGE_CONSTRUCTION = "eg_er_ara"
# the Icelandic words of an age the course teaches (the target, whatever language the course is glossed in: review of #608)
_IS_NUMBERS = {"eitt": 1, "einn": 1, "tvö": 2, "tveir": 2, "þrjú": 3, "þrír": 3, "fjögur": 4, "fjórir": 4, "fimm": 5, "sex": 6, "sjö": 7, "átta": 8,
               "níu": 9, "tíu": 10, "ellefu": 11, "tólf": 12, "þrettán": 13, "fjórtán": 14, "fimmtán": 15, "sextán": 16, "sautján": 17,
               "átján": 18, "nítján": 19, "tuttugu": 20, "þrjátíu": 30, "fjörutíu": 40, "fimmtíu": 50, "sextíu": 60, "sjötíu": 70,
               "áttatíu": 80, "níutíu": 90}


def valid_name(name: str) -> bool:
    """One word of letters (a hyphen or an apostrophe inside it), at most 24: a name the target voice can say in «Ég heiti …»."""
    return bool(NAME_RE.match(name))


def _swap(value, name: str):
    """``value`` with the persona's name as a whole word replaced by ``name``, through strings, lists, dicts and dataclasses."""
    if isinstance(value, str):
        return re.sub(rf"\b{PERSONA_NAME}\b", name, value).replace(PERSONA_NAME_JA, name)
    if isinstance(value, list):
        return [_swap(v, name) for v in value]
    if isinstance(value, dict):
        return {k: _swap(v, name) for k, v in value.items()}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.replace(value, **{f.name: _swap(getattr(value, f.name), name) for f in dataclasses.fields(value) if f.init})
    return value


def _holds_name(value) -> bool:
    return _swap(value, "\x00") != value


def age_value(item) -> int | None:
    """An age filler's value, read from its Icelandic target («tuttugu og fimm» → 25), so a course glossed in any language reads it the same."""
    words = [w for w in re.findall(r"[^\W\d_]+", item.target.lower()) if w != "og"]
    if not words or any(w not in _IS_NUMBERS for w in words):
        return None
    return sum(_IS_NUMBERS[w] for w in words)


def age_item(cur, age: int):
    """The course's item for ``age`` as an age («tuttugu og fimm»), or None."""
    return next((i for i in cur.items_with_tag("age") if age_value(i) == age), None)


def personalize(cur, themes: list, name: str | None = None, age: int | None = None) -> tuple:
    """``(cur, themes, applied)``: the course and its themes with the learner's own name and age in their own lines; ``applied`` says which were
    used ({"name": bool, "age": bool}: an age the course has no item for is not used)."""
    applied = {"name": False, "age": False}
    if name:
        if not valid_name(name):
            raise ValueError(f"--own-name: one word of letters, not {name!r}")
        items = [_swap(i, name) if _holds_name(i) else i for i in cur.items]
        dialogues = [dataclasses.replace(d, turns=[_swap(t, name) if _holds_name(t) else t for t in d.turns]) for d in cur.dialogues]
        cur = dataclasses.replace(cur, items=items, dialogues=dialogues)
        themes = [_with_turns(t, lambda turn: _swap(turn, name) if turn.who == "you" and _holds_name(turn) else turn) for t in themes]
        applied["name"] = True
    if age is not None and (fill := age_item(cur, age)) is not None:
        def own_age(turn):
            if turn.who != "you" or AGE_CONSTRUCTION not in turn.items:
                return turn
            fills = [i for i in turn.items if i != AGE_CONSTRUCTION and cur.by_id.get(i) is not None and "age" in cur.by_id[i].tags]
            if not fills:
                return turn
            items = [fill.id if i in fills else i for i in turn.items]
            return dataclasses.replace(turn, items=items, say=f"Ég er {fill.target} ára.", say_m="", cue=f"Say you're {age}.", cue_ja=f"{age}歳だと言ってください。")
        themes = [_with_turns(t, own_age) for t in themes]
        applied["age"] = True
    return cur, themes, applied


def _with_turns(theme, change):
    return dataclasses.replace(theme, levels=[dataclasses.replace(lv, turns=[change(t) for t in lv.turns]) for lv in theme.levels])
