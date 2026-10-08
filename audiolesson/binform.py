"""BÍN (Beygingarlýsing íslensks nútímamáls) check of the curriculum's forms (#218 b2).

A close variant (``Item.variant_of``: another case or gender of a word the learner knows) must be a form of the same lemma as its
base. That is checked once, when the variant is added, against BÍN, and the lookups are cached in ``<curriculum>/bin/forms.json``
so ``validate`` and the tests run offline. The network is used only by ``tools/bin_lookup.py``.

The cache maps a form (casefolded) to ``{lemma, guid, ofl, kyn, tag, checked_on}``. Nothing from BÍN is copied into the curriculum's
TOML. BÍN's data is CC BY-SA 4.0; see ``curricula/is-en/bin/README.md`` for the attribution and what was changed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CACHE_NAME = "forms.json"
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
TOOL_HINT = "python tools/bin_lookup.py {form} [--ofl no|so|lo|to…] [--pick <guid>]"


def form_key(text: str) -> str:
    """The cache key of a form: its letters, casefolded («Kaffið.» → «kaffið»)."""
    return " ".join(w.casefold() for w in _WORD.findall(text))


def cache_path(curriculum_dir: str | Path) -> Path:
    return Path(curriculum_dir) / "bin" / CACHE_NAME


def load_cache(path: str | Path) -> dict[str, dict]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_cache(path: str | Path, cache: dict[str, dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def parse_lookup(data, form: str) -> list[dict]:
    """The candidates a BÍN ``beygingarmynd`` response lists for ``form``: ``[{guid, lemma, ofl, kyn, tags}]``, one per word it could be
    a form of (an ambiguous form such as «miða» is a form of mið, miða and miði). ``tags`` are the grammatical tags the form has in
    that word's paradigm (e.g. ``"ÞFET"``).

    ASSUMED SHAPE, written without network access to BÍN: a list, or an object with the list under ``results``; each word has ``guid``,
    ``ord`` (the lemma), ``ofl`` (word class), optionally ``kyn`` (gender), and its forms under ``bmyndir`` /
    ``beygingarmyndir`` as ``{"b": form, "g": tag}``. Adjust here, and in ``tests/data/bin_beygingarmynd_sample.json``, to the real
    response on the first run of the tool."""
    results = data.get("results", []) if isinstance(data, dict) else data
    want = form_key(form)
    out = []
    for r in results or []:
        forms = r.get("bmyndir") or r.get("beygingarmyndir") or []
        tags = sorted({f.get("g", "") for f in forms if form_key(str(f.get("b", ""))) == want and f.get("g")})
        out.append({"guid": str(r.get("guid", "")), "lemma": r.get("ord") or r.get("lemma") or "", "ofl": r.get("ofl", ""),
                    "kyn": r.get("kyn", ""), "tags": tags})
    return out


def cache_entry(candidate: dict, checked_on: str) -> dict:
    """The cache record of a chosen candidate: a subset of BÍN's fields."""
    return {"lemma": candidate["lemma"], "guid": candidate["guid"], "ofl": candidate["ofl"], "kyn": candidate["kyn"],
            "tag": "/".join(candidate["tags"]), "checked_on": checked_on}


def variant_pairs(cur) -> list[tuple[str, str, str]]:
    """(variant id, variant form, base form) for every ``variant_of`` item."""
    return [(i.id, form_key(i.target), form_key(cur.by_id[i.variant_of].target)) for i in cur.items if i.variant_of]


def check_variants(cur, cache: dict[str, dict]) -> list[str]:
    """What is wrong with the cache for the curriculum's variants: a form or its base missing (with the command to run), or a pair
    whose forms are of different words (the item is wrong, or its base: fix it, do not skip it)."""
    problems = []
    for item_id, form, base in variant_pairs(cur):
        missing = [f for f in (form, base) if f not in cache]
        for f in missing:
            problems.append(f"variant {item_id!r}: {f!r} is not in curricula/*/bin/{CACHE_NAME}; run `{TOOL_HINT.format(form=f)}`")
        if missing:
            continue
        if cache[form]["guid"] != cache[base]["guid"]:
            problems.append(
                f"variant {item_id!r}: {form!r} is a form of {cache[form]['lemma']!r} but its base {base!r} is a form of {cache[base]['lemma']!r} (BÍN): "
                "they are not one lemma, fix the item"
            )
    return problems
