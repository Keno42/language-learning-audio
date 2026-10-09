"""BÍN (Beygingarlýsing íslensks nútímamáls) check of the curriculum's forms (#218 b2).

A close variant (``Item.variant_of``: another case or gender of a word the learner knows) should be a form of the same lemma as its
base. That is looked up once, when the variant is added, in BÍN's **downloadable language-technology data** (CC BY-SA 4.0; the
website's tables and the API are not covered by that licence), and cached in ``<curriculum>/bin/forms.json`` so ``validate`` and the
tests run offline. The check **advises and never blocks** (owner, after lesson 20; LEARNING-DESIGN §9 "Good enough overall"):
``validate`` warns when the cache is missing, when a form is not in it, or when a pair disagrees.

The cache maps a form (casefolded) to ``{lemma, guid, ofl, kyn, tag, source, checked_on}``. Nothing from BÍN is copied into the
curriculum's TOML. See ``curricula/is-en/bin/README.md`` for the licence, the attribution and what was changed.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from pathlib import Path

CACHE_NAME = "forms.json"
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
TOOL_HINT = "python tools/bin_lookup.py --data SHsnid.csv.zip {form} [--ofl no|so|lo|to…] [--pick <id>]"
# ASSUMED layout of a row of the downloaded form list (``SHsnid.csv``: one row per form, semicolon-separated), from the owner's reading of
# BÍN's terms page: lemma; id; word class; domain; form; tag. Check against BÍN's "Sjá skýringar" and adjust here on the first real run.
COLUMNS = {"lemma": 0, "id": 1, "ofl": 2, "domain": 3, "form": 4, "tag": 5}
DELIMITER = ";"


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


def open_rows(path: str | Path):
    """The downloaded file as text lines: a plain ``.csv``, or the first file of a ``.zip``."""
    p = Path(path)
    if p.suffix == ".zip":
        z = zipfile.ZipFile(p)
        name = next(n for n in z.namelist() if not n.endswith("/"))
        return io.TextIOWrapper(z.open(name), encoding="utf-8")
    return p.open(encoding="utf-8", newline="")


def find_forms(path: str | Path, wanted: set[str]) -> dict[str, list[dict]]:
    """One pass over the data: for each wanted form (as ``form_key``), the words it could be a form of, as
    ``[{guid, lemma, ofl, domain, tags}]`` (``guid`` is the data file's id, which may differ from the API's)."""
    found: dict[str, dict[tuple[str, str, str], dict]] = {w: {} for w in wanted}
    with open_rows(path) as fh:
        for row in csv.reader(fh, delimiter=DELIMITER):
            if len(row) <= max(COLUMNS.values()):
                continue
            key = form_key(row[COLUMNS["form"]])
            if key not in found:
                continue
            word = (row[COLUMNS["lemma"]], row[COLUMNS["id"]], row[COLUMNS["ofl"]])
            entry = found[key].setdefault(word, {"guid": word[1], "lemma": word[0], "ofl": word[2], "domain": row[COLUMNS["domain"]], "tags": []})
            tag = row[COLUMNS["tag"]]
            if tag and tag not in entry["tags"]:
                entry["tags"].append(tag)
    return {w: list(d.values()) for w, d in found.items()}


def cache_entry(candidate: dict, checked_on: str, source: str) -> dict:
    """The cache record of a chosen candidate: a subset of BÍN's fields, and which file it came from."""
    return {"lemma": candidate["lemma"], "guid": candidate["guid"], "ofl": candidate["ofl"], "kyn": candidate.get("kyn", ""),
            "tag": "/".join(candidate["tags"]), "source": source, "checked_on": checked_on}


def variant_pairs(cur) -> list[tuple[str, str, str]]:
    """(variant id, variant form, base form) for every ``variant_of`` item."""
    return [(i.id, form_key(i.target), form_key(cur.by_id[i.variant_of].target)) for i in cur.items if i.variant_of]


def variant_warnings(cur, cache: dict[str, dict]) -> list[str]:
    """What the cache says is off about the curriculum's variants, as warnings (never failures): a form or its base missing (with the command
    to run), or a pair whose forms BÍN gives to different words (the item may be wrong, or its base)."""
    problems = []
    for item_id, form, base in variant_pairs(cur):
        missing = [f for f in (form, base) if f not in cache]
        for f in missing:
            problems.append(f"variant {item_id!r}: {f!r} is not in the BÍN cache; run `{TOOL_HINT.format(form=f)}`")
        if missing:
            continue
        if cache[form]["guid"] != cache[base]["guid"]:
            problems.append(
                f"variant {item_id!r}: {form!r} is a form of {cache[form]['lemma']!r} but its base {base!r} is a form of {cache[base]['lemma']!r} (BÍN): "
                "not one lemma; check the item (BÍN advises, it does not block)"
            )
    return problems
