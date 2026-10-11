"""A noun is one entry; each form the learner gains is a step of its own (#270, the pilot).

The curriculum groups the forms of a noun (``Item.noun`` / ``Item.form``); the learner keeps one state per form item as before, so a form's success or
failure never moves another form's, and an old item id in a learner file or a review queue resolves to its noun and form (``Curriculum.noun_form``)
with its history. ``noun_forms`` is the read: which forms of each noun the learner has met, and when each was last practised.
"""

from __future__ import annotations


def noun_forms(cur, learner) -> dict[str, dict]:
    """``{noun: {"gender", "base", "forms": {form: {"item", "met", "last_practiced", "successes"}}}}`` for every noun the curriculum groups."""
    out: dict[str, dict] = {}
    for noun, entry in cur.nouns.items():
        forms = {}
        for form, item_id in entry["forms"].items():
            st = learner.items.get(item_id)
            forms[form] = {
                "item": item_id,
                "met": learner.has_met(item_id),
                "last_practiced": (st.last_practiced if st else None),
                "successes": (st.successes if st else 0),
            }
        out[noun] = {"gender": entry["gender"], "base": entry["base"], "forms": forms}
    return out


def noun_report(cur, learner) -> str:
    """One line for the daily read: the nouns that have met a form, with the forms met («kaka: acc»)."""
    parts = []
    for noun, entry in noun_forms(cur, learner).items():
        met = [f for f, v in entry["forms"].items() if v["met"]]
        if met:
            parts.append(f"{noun}: {'+'.join(met)}")
    return ", ".join(parts) or "–"
