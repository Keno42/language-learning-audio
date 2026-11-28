"""#627: the items whose meaning holds a word their target does not say, so their literal words may need authoring (``Item.literal``).

An English meaning that says «is» / «I'm», «my» / «your» or «not» where the Icelandic has no form of «vera», no possessive and no «ekki»
names words the Icelandic lacks («Ég hef það gott.» "I'm doing well", «Ég sakna fjölskyldunnar.» "I miss my family"). The list is a
candidate list for authoring, not a check: an item whose words do match its meaning, said another way, is left as it is.
"""
from __future__ import annotations

import re

# (English words of the meaning, the Icelandic words that say them): a meaning word without one of its Icelandic words is not in the target
_RULES_IS_EN = (
    ({"i'm", "you're", "it's", "we're", "they're", "he's", "she's", "what's", "am", "is", "are", "isn't", "aren't"},
     r"\b(er|ert|ertu|erum|eruð|eru|var|varst|vorum|voru|vera|sé|séu)\b"),
    ({"my", "your", "our", "their", "his", "mine", "yours"},
     r"\b(minn|mín|mitt|mína|mínum|mínu|minni|mínar|mínir|þinn|þín|þitt|þína|þínum|þínu|þínar|okkar|ykkar|þeirra|hans|hennar|sinn|sín|sitt)\b"),
    ({"don't", "doesn't", "didn't", "can't", "won't", "not", "no"}, r"\b(ekki|enginn|engin|ekkert|engan|nei|aldrei)\b"),
)


def missing_words(item) -> list[str]:
    """The words of ``item``'s meaning (its first rendering, brackets and slots left out) that its target does not say."""
    meaning = re.sub(r"\{[^}]*\}|\([^)]*\)", "", item.meaning.split(" / ")[0]).lower()
    words, target = set(re.findall(r"[a-z']+", meaning)), item.target.lower()
    return [w for said, pattern in _RULES_IS_EN for w in sorted(words & said) if not re.search(pattern, target)]


def candidates(cur) -> list[tuple[object, list[str]]]:
    """The phrases and words with no ``literal`` whose meaning holds words their target lacks (an Icelandic course taught in English)."""
    if (cur.target_lang, cur.known_lang) != ("is", "en"):
        return []
    out = []
    for it in cur.items:
        if it.kind in ("phrase", "vocab") and "{" not in it.target and not it.literal and (lack := missing_words(it)):
            out.append((it, lack))
    return out


def with_literal_words(cur, review: list[dict]) -> list[dict]:
    """#627: a written question whose answer is one item's target, where the item has authored literal words, carries them (``literal``), for the
    bot to show with the answer. A question answered by a longer sentence is left as it is: the literal words are the item's, not the sentence's."""
    out = []
    for q in review:
        items = q.get("items") or []
        it = cur.by_id.get(items[0]) if len(items) == 1 else None
        if it is not None and it.literal and isinstance(q.get("answer"), str) and q["answer"].strip() in (it.target.strip(), (it.target_m or "").strip()):
            q = {**q, "literal": it.literal}
        out.append(q)
    return out
