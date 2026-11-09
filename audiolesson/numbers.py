"""Numbers by what is hard in them (#439 step 1, the owner after lesson 49).

**Plain numbers (step 1a).** A number whose form never changes needs no word's practice. Lesson 49 introduced «sextán», «fimmtán», «tvö þúsund
krónur» and «þrjú þúsund krónur» as words: a slow word-by-word model, four timed recalls, «use it in another sentence». The owner: «ただの数字でそういう
練習は不要» (a plain number needs no such practice). A plain number is introduced plainly (heard, repeated once, said once), with no slow model, and is
asked once more later in the lesson; it comes back as it is used, in its expression and in the scene lines it is picked out of (§9's numbers exception).

What counts as a plain number is read from the data: a vocab item tagged as a number, an age, a count or a price, that is not a form of 1–4. A form of
1–4 is any item with a gender of its own («eitt», «tvö»), a form of another item («tvær» of «tveir»), the base of such a form («tveir»), a man's
form beside it, or one of the forms in ``FORMS`` («einn», which has no other form in the course yet). A price that holds a form of 1–4 («tvö þúsund
krónur») is plain: the form there is fixed by «þúsund», not chosen.

**The forms of 1–4 as a choice (step 1b).** The owner: the forms of 1–4, which change with the gender and case of the noun they count, lack practice
to use them right. The learner had each form through one frame («tvo» for tickets, «tvö» for prices and hours, «eina» for a hot dog) and no exercise
asked for the form a noun chooses. A line whose 1–4 form agrees with a noun names that noun (``Item.counts``); ``choice_lines`` finds the lines the
learner knows, and the planner plays one number's lines of different genders side by side, the reason named once, then asks each again.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

NUMBER_TAGS = frozenset({"number", "age", "big_count", "small_count", "price"})

# the forms of 1–4: value -> gender -> (nominative, accusative, dative, genitive)
FORMS = {
    1: {"masc": ("einn", "einn", "einum", "eins"), "fem": ("ein", "eina", "einni", "einnar"), "neut": ("eitt", "eitt", "einu", "eins")},
    2: {"masc": ("tveir", "tvo", "tveimur", "tveggja"), "fem": ("tvær", "tvær", "tveimur", "tveggja"), "neut": ("tvö", "tvö", "tveimur", "tveggja")},
    3: {"masc": ("þrír", "þrjá", "þremur", "þriggja"), "fem": ("þrjár", "þrjár", "þremur", "þriggja"), "neut": ("þrjú", "þrjú", "þremur", "þriggja")},
    4: {"masc": ("fjórir", "fjóra", "fjórum", "fjögurra"), "fem": ("fjórar", "fjórar", "fjórum", "fjögurra"), "neut": ("fjögur", "fjögur", "fjórum", "fjögurra")},
}
GENDER_ORDER = ("masc", "fem", "neut")
CASES = ("nom", "acc", "dat", "gen")  # the order of each gender's forms in ``FORMS``

# every form of 1–4 (and «einan», «one» as «alone»): a one-word item that is one of them changes with its noun, so it is never plain
ONE_TO_FOUR = frozenset({f for genders in FORMS.values() for forms in genders.values() for f in forms} | {"einan"})

_WORD = re.compile(r"[^\W\d_]+")

# the words a number is said with past 1–4 (#451 step 3): the units, the teens, the tens, «hundrað» and «þúsund». With ``ONE_TO_FOUR`` they are what
# rests between lessons («þúsund», «fimm» and «tíu» in every lesson: the owner after lesson 51)
NUMBER_WORDS = ONE_TO_FOUR | frozenset({
    "fimm", "sex", "sjö", "átta", "níu", "tíu", "ellefu", "tólf", "þrettán", "fjórtán", "fimmtán", "sextán", "sautján", "átján", "nítján",
    "tuttugu", "þrjátíu", "fjörutíu", "fimmtíu", "sextíu", "sjötíu", "áttatíu", "níutíu", "hundrað", "hundruð", "þúsund",
})


def number_words(text: str) -> list[str]:
    """The number words in ``text``, lower case, each once, in their order (#451 step 3)."""
    return list(dict.fromkeys(w for w in (w.lower() for w in _WORD.findall(text)) if w in NUMBER_WORDS))


def plain_number(item, cur) -> bool:
    """Whether ``item`` is a plain number (#439 step 1a): see the module's docstring."""
    if item.kind != "vocab" or not (set(item.tags) & NUMBER_TAGS):
        return False
    if item.variant_of or item.gender or item.target_m:
        return False
    if item.target.strip(".?!").lower() in ONE_TO_FOUR:
        return False
    return not any(other.variant_of == item.id for other in cur.items)


def value_of(word: str) -> int | None:
    """The value ``word`` is a form of, 1 to 4; None for any other word."""
    low = word.lower()
    return next((value for value, genders in FORMS.items() if any(low in forms for forms in genders.values())), None)


def number_in(text: str) -> tuple[str, int, str] | None:
    """The first form of 1–4 in ``text`` as written, its value, and the word after it (the word it counts: «miða» in «Tvo miða, takk.»); None when
    the text holds none, or nothing follows it."""
    words = _WORD.findall(text)
    for k, w in enumerate(words):
        if (value := value_of(w)) is not None:
            return (w, value, words[k + 1]) if k + 1 < len(words) else None
    return None


def agrees(form: str, value: int, gender: str) -> bool:
    """Whether ``form`` is a form of ``value`` for a noun of ``gender``, in any case."""
    return form.lower() in FORMS.get(value, {}).get(gender, ())


def noun_gender(cur, noun: str) -> str | None:
    """The gender of the noun ``noun`` (an item's ``noun`` key, #270), from any of its forms."""
    return next((i.gender for i in cur.items if i.noun == noun and i.gender), None)


@dataclass(frozen=True)
class ChoiceLine:
    """A sentence the learner knows whose 1–4 form agrees with the noun it counts (#439 step 1b)."""

    sentence: str
    meaning: str
    value: int
    form: str  # the number as said in the sentence («tvo»)
    word: str  # the word it counts, as said («miða»)
    gender: str  # that noun's gender
    item_ids: tuple[str, ...]  # the items the sentence is made of (the phrase, or the pattern and its filler)
    voice: str | None = None  # the speaker's gender the sentence is said in, for a gendered line
    # the case the form shows when it is not the nominative («þrjá»: acc), with the nominative it is told from («þrír»; lesson 50 as drafted: «miða
    # is masculine, so: þrjá» left out why not «þrír»); "nom" when the form is also the nominative («tvö», «einn»)
    case: str = "nom"
    nominative: str = ""


def choice_lines(candidates) -> dict[int, dict[str, list[ChoiceLine]]]:
    """``candidates``: (sentence, meaning, gender of the counted noun, item ids, voice) for each line the learner knows that names what it counts.
    Grouped by value, then gender; a line whose number does not agree with its noun («Tvo kaffi, takk.»: «bolla» is understood) is left out."""
    out: dict[int, dict[str, list[ChoiceLine]]] = {}
    for sentence, meaning, gender, ids, voice in candidates:
        found = number_in(sentence)
        if found is None or gender is None:
            continue
        form, value, word = found
        if not agrees(form, value, gender):
            continue
        forms = FORMS[value][gender]
        case = CASES[forms.index(form.lower())]
        out.setdefault(value, {}).setdefault(gender, []).append(ChoiceLine(sentence, meaning, value, form, word, gender, tuple(ids), voice, case, forms[0]))
    return out


def pick_choice(groups: dict[int, dict[str, list[ChoiceLine]]], turn: int) -> list[ChoiceLine]:
    """One number's lines of different genders, one line each (masculine, feminine, neuter): the numbers with two genders or more take turns by
    ``turn`` (the lesson number). Empty when no number has two genders yet. A gender with several lines takes them in turn too, each time its number
    comes round (#451 step 3: the neuter of 2 was «Það kostar tvö þúsund krónur.» every time, with «Tvö börn» known beside it)."""
    values = sorted(v for v, g in groups.items() if len(g) >= 2)
    if not values:
        return []
    value = values[turn % len(values)]
    round_ = turn // len(values)
    return [groups[value][g][round_ % len(groups[value][g])] for g in GENDER_ORDER if g in groups[value]]
