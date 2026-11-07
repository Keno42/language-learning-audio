"""Plain numbers (#439 step 1a, the owner after lesson 49): a number whose form never changes needs no word's practice.

Lesson 49 introduced «sextán», «fimmtán», «tvö þúsund krónur» and «þrjú þúsund krónur» as words: a slow word-by-word model, four timed recalls,
«use it in another sentence». The owner: «ただの数字でそういう練習は不要» (a plain number needs no such practice), while the forms of 1–4, which change
with the noun's gender and case, need more (step 1b). A plain number is introduced plainly (heard, repeated once, said once), with no slow model, and is
asked once more later in the lesson; it comes back as it is used, in its expression and in the scene lines it is picked out of (§9's numbers exception).

What counts as a plain number is read from the data: a vocab item tagged as a number, an age, a count or a price, that is not a form of 1–4. A form of
1–4 is any item with a gender of its own («eitt», «tvö»), a form of another item («tvær» of «tveir»), the base of such a form («tveir»), a man's
form beside it, or one of the words below («einn», which has no other form in the course yet). A price that holds a form of 1–4 («tvö þúsund krónur»)
is plain: the form there is fixed by «þúsund», not chosen.
"""

from __future__ import annotations

NUMBER_TAGS = frozenset({"number", "age", "big_count", "small_count", "price"})

# the forms of 1–4 in every gender and case: a one-word item that is one of them changes with its noun, so it is never plain
ONE_TO_FOUR = frozenset({
    "einn", "ein", "eitt", "einan", "eina", "einum", "einni", "eins", "einnar",
    "tveir", "tvær", "tvö", "tvo", "tveimur", "tveggja",
    "þrír", "þrjár", "þrjú", "þrjá", "þremur", "þriggja",
    "fjórir", "fjórar", "fjögur", "fjóra", "fjórum", "fjögurra",
})


def plain_number(item, cur) -> bool:
    """Whether ``item`` is a plain number (#439 step 1a): see the module's docstring."""
    if item.kind != "vocab" or not (set(item.tags) & NUMBER_TAGS):
        return False
    if item.variant_of or item.gender or item.target_m:
        return False
    if item.target.strip(".?!").lower() in ONE_TO_FOUR:
        return False
    return not any(other.variant_of == item.id for other in cur.items)
