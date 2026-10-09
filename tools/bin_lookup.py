#!/usr/bin/env python3
"""Look the curriculum's forms up in BÍN's downloaded data and cache them for ``validate`` (#218 b2). No network.

    python tools/bin_lookup.py --data SHsnid.csv.zip <form> [--ofl no|so|lo|to…] [--pick <id>] [--curriculum curricula/is-en]
    python tools/bin_lookup.py --data SHsnid.csv.zip --variants [--curriculum curricula/is-en]   # every variant_of item and its base

``--data`` is the form list from BÍN's download page (``SHsnid.csv``, plain or zipped; CC BY-SA 4.0). Do not commit it: only the subset
written to ``<curriculum>/bin/forms.json`` is committed (form → lemma, guid, ofl, tag, source, checked_on). An ambiguous form («miða» is mið,
miða and miði) lists the words it could be with their ids; the author picks one with ``--pick <id>``. The check advises and never blocks:
see curricula/is-en/bin/README.md for the licence, the attribution and what was changed.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audiolesson.binform import cache_entry, cache_path, find_forms, form_key, load_cache, save_cache, variant_pairs  # noqa: E402
from audiolesson.content import load_curriculum  # noqa: E402


def resolve(candidates: list[dict], pick: str | None = None, ofl: str | None = None) -> tuple[dict | None, list[dict]]:
    """(the chosen word or None, the words left). One word is chosen on its own; several need ``pick``; ``ofl`` narrows them."""
    cands = candidates
    if ofl:
        cands = [c for c in cands if c["ofl"] == ofl] or cands
    if pick:
        cands = [c for c in cands if c["guid"] == pick]
    return (cands[0] if len(cands) == 1 else None), cands


def run(forms: list[tuple[str, str | None]], data: Path, path: Path, pick: str | None, today: str) -> int:
    cache = load_cache(path)
    found = find_forms(data, {form_key(f) for f, _ in forms})
    status = 0
    for form, ofl in forms:
        key = form_key(form)
        all_words = found.get(key, [])
        chosen, cands = resolve(all_words, pick if len(forms) == 1 else None, ofl)
        if chosen is None:
            status = 1
            if pick and all_words and not cands:
                print(f"{form!r}: no word with id {pick!r} among: " + ", ".join(f"{c['guid']} ({c['lemma']})" for c in all_words))
            elif cands:
                print(f"{form!r}: {len(cands)} words it could be a form of; pick one with --pick <id>:")
                for c in cands:
                    print(f"   {c['guid']}  {c['lemma']} ({c['ofl']})  {'/'.join(c['tags'])}")
            else:
                print(f"{form!r}: not found in {data.name}")
            continue
        cache[key] = cache_entry(chosen, today, data.name)
        print(f"{form!r} → {chosen['lemma']} ({chosen['ofl']}) {cache[key]['tag']}  [{chosen['guid']}]")
        save_cache(path, cache)
    return status


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("form", nargs="?", help="the form to look up")
    ap.add_argument("--data", required=True, type=Path, help="BÍN's downloaded form list (SHsnid.csv or its .zip)")
    ap.add_argument("--ofl", default=None, help="word class: no, so, lo, to…")
    ap.add_argument("--pick", default=None, help="the id to take when the form is ambiguous")
    ap.add_argument("--variants", action="store_true", help="look up every variant_of item and its base (single words)")
    ap.add_argument("--curriculum", default="curricula/is-en")
    args = ap.parse_args(argv)
    path = cache_path(args.curriculum)
    if args.variants:
        cur = load_curriculum(args.curriculum)
        cache = load_cache(path)
        forms = list(dict.fromkeys((f, None) for _, v, b in variant_pairs(cur) for f in (v, b) if f not in cache))
        print(f"{len(forms)} forms to look up")
    elif args.form:
        forms = [(args.form, args.ofl)]
    else:
        ap.error("a form, or --variants")
    return run(forms, args.data, path, args.pick, date.today().isoformat())


if __name__ == "__main__":
    raise SystemExit(main())
