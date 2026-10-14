"""A noun is one entry; each form the learner gains is a step of its own (#270, the pilot).

The curriculum groups the forms of a noun (``Item.noun`` / ``Item.form``); the learner keeps one state per form item as before, so a form's success or
failure never moves another form's, and an old item id in a learner file or a review queue resolves to its noun and form (``Curriculum.noun_form``)
with its history. ``noun_forms`` is the read: which forms of each noun the learner has met, and when each was last practised.
"""

from __future__ import annotations

import re

_CASE = re.compile(r"^(nom|acc|dat|gen)_")


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


def scene_frames(cur, themes) -> list[dict]:
    """#270 step 1, the other half: each scene's frames and the case each asks, read from the scene data and not authored a second time. One row per learner turn
    of a theme level that says a noun: ``{"theme", "level", "say", "frames": [{"construction", "slot", "case"}], "nouns": [{"item", "noun", "form"}]}``.
    ``case`` is the case of the slot's tag that the noun's tags satisfy; ``None`` for a turn with no frame (a bare answer like «Vatn, takk.»)."""
    rows = []
    for theme in themes:
        for n, level in enumerate(theme.levels):
            for turn in level.turns:
                if turn.who != "you":
                    continue
                items = [cur.by_id[i] for i in turn.items if i in cur.by_id]
                nouns = [i for i in items if i.noun]
                if not nouns:
                    continue
                frames = []
                for c in (i for i in items if i.kind == "construction"):
                    for slot, tag in c.slots.items():
                        if any(tag in i.tags for i in nouns):
                            frames.append({"construction": c.id, "slot": slot, "case": (_CASE.match(tag) or [None, None])[1]})
                rows.append({"theme": theme.id, "level": n + 1, "say": turn.say, "frames": frames, "nouns": [{"item": i.id, "noun": i.noun, "form": i.form} for i in nouns]})
    return rows


def scene_syncretisms(rows: list[dict]) -> list[str]:
    """Frames that ask a case the noun's form is not named for: the form stands for the case because the word is the same («eldfjall» is `nom` and also the accusative
    after «sjá»; the item's tags say it serves the frame). Listed so a reader sees which scenes use a form for another case; not an error."""
    out = []
    for r in rows:
        for f in r["frames"]:
            for noun in r["nouns"]:
                if f["case"] and noun["form"].split("_")[0] != f["case"] and not noun["form"].startswith("pl"):
                    out.append(f"{r['theme']}:{r['level']} «{r['say']}»: {f['construction']} asks {f['case']}; {noun['item']} is {noun['form']}, the same word")
    return out


def scene_unframed(rows: list[dict]) -> list[str]:
    """Learner turns that say a noun and whose ``items`` list no construction: the table cannot show their frame. A bare answer («Vatn, takk.») is fine; a turn
    that is a sentence of a pattern («Afsakið, áttu skyr?» is «Áttu {thing}?») should list the construction in its ``items``."""
    return [f"{r['theme']}:{r['level']} «{r['say']}»" for r in rows if not r["frames"]]


def scene_report(cur, themes) -> str:
    """The lines of ``audiolesson nouns --scenes``: a table of each scene's frames and the form each noun takes in it, the turns whose items list no construction (so the table shows no frame for them), and the forms that stand for another case. It shows what the turns' ``items`` declare, not every frame a scene uses."""
    rows = scene_frames(cur, themes)
    lines = [f"{r['theme']}:{r['level']}  «{r['say']}»  " + ", ".join(f"{f['construction']}[{f['slot']}: {f['case'] or '–'}]" for f in r["frames"]) + "  ← " + ", ".join(f"{n['noun']}:{n['form']}" for n in r["nouns"]) for r in rows]
    notes = scene_syncretisms(rows)
    unframed = scene_unframed(rows)
    lines += [f"no construction in the turn's items, so no frame is shown ({len(unframed)}; a bare answer is fine, a sentence of a pattern should list it): " + "; ".join(unframed)] if unframed else []
    return "\n".join(lines + ([f"a form standing for another case ({len(notes)}):"] + ["  " + h for h in notes] if notes else ["every frame's case is its noun's form"]))
