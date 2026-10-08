#!/usr/bin/env python3
"""Look a form up in BÍN and cache it for ``validate`` (#218 b2). The only code that uses the network.

    python tools/bin_lookup.py <form> [--ofl no|so|lo|to…] [--pick <guid>] [--curriculum curricula/is-en]
    python tools/bin_lookup.py --variants [--curriculum curricula/is-en]     # every variant_of item and its base

Calls https://bin.arnastofnun.is/api/beygingarmynd/<form> (or /beygingarmynd/<ofl>/<form>). An ambiguous form («miða» is mið, miða and
miði) returns several words: the tool lists them with their guids and the author picks one with ``--pick <guid>``. The full paradigm
comes from /api/ord/<guid>. The choice is written to ``<curriculum>/bin/forms.json`` (form → lemma, guid, ofl, kyn, tag, checked_on).

One request at a time, a pause between requests, a User-Agent naming the project. BÍN is CC BY-SA 4.0: see
curricula/is-en/bin/README.md.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audiolesson.binform import cache_entry, cache_path, form_key, load_cache, parse_lookup, save_cache, variant_pairs  # noqa: E402
from audiolesson.content import load_curriculum  # noqa: E402

API = "https://bin.arnastofnun.is/api"
USER_AGENT = "language-learning-audio/curriculum-form-check (https://github.com/Keno42/language-learning-audio)"
PAUSE = 1.5  # seconds between requests


def fetch(path: str):
    req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def lookup(form: str, ofl: str | None = None):
    quoted = urllib.parse.quote(form, safe="")
    return fetch(f"beygingarmynd/{ofl}/{quoted}" if ofl else f"beygingarmynd/{quoted}")


def resolve(form: str, data, pick: str | None = None, ofl: str | None = None) -> tuple[dict | None, list[dict]]:
    """(the chosen candidate or None, all candidates). One candidate is chosen on its own; several need ``pick``; ``ofl`` narrows them."""
    cands = parse_lookup(data, form)
    if ofl:
        cands = [c for c in cands if c["ofl"] == ofl] or cands
    if pick:
        cands = [c for c in cands if c["guid"] == pick]
    return (cands[0] if len(cands) == 1 else None), cands


def run(forms: list[tuple[str, str | None]], path: Path, pick: str | None, today: str, fetcher=lookup, pause: float = PAUSE) -> int:
    cache = load_cache(path)
    status = 0
    for k, (form, ofl) in enumerate(forms):
        if k:
            time.sleep(pause)
        key = form_key(form)
        chosen, cands = resolve(form, fetcher(form, ofl), pick if len(forms) == 1 else None, ofl)
        if chosen is None:
            status = 1
            print(f"{form!r}: {len(cands)} words it could be a form of; pick one with --pick <guid>:" if cands else f"{form!r}: not found in BÍN")
            for c in cands:
                print(f"   {c['guid']}  {c['lemma']} ({c['ofl']}{' ' + c['kyn'] if c['kyn'] else ''})  {'/'.join(c['tags'])}")
            continue
        cache[key] = cache_entry(chosen, today)
        print(f"{form!r} → {chosen['lemma']} ({chosen['ofl']}) {cache[key]['tag']}  [{chosen['guid']}]")
        save_cache(path, cache)
    return status


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("form", nargs="?", help="the form to look up")
    ap.add_argument("--ofl", default=None, help="word class: no, so, lo, to…")
    ap.add_argument("--pick", default=None, help="the guid to take when the form is ambiguous")
    ap.add_argument("--variants", action="store_true", help="look up every variant_of item and its base (single words)")
    ap.add_argument("--curriculum", default="curricula/is-en")
    args = ap.parse_args(argv)
    path = cache_path(args.curriculum)
    if args.variants:
        cur = load_curriculum(args.curriculum)
        cache = load_cache(path)
        forms = [(f, None) for _, v, b in variant_pairs(cur) for f in (v, b) if f not in cache]
        forms = list(dict.fromkeys(forms))
        print(f"{len(forms)} forms to look up")
    elif args.form:
        forms = [(args.form, args.ofl)]
    else:
        ap.error("a form, or --variants")
    return run(forms, path, args.pick, date.today().isoformat())


if __name__ == "__main__":
    raise SystemExit(main())
