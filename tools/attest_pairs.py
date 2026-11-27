#!/usr/bin/env python3
"""Look up in Icelandic texts every pair of neighbouring words the course says, for the trust check (the owner, 2026-11-28; G10, #631).

    python tools/attest_pairs.py curricula/is-en            # look up what is not in the table yet, then save it
    python tools/attest_pairs.py curricula/is-en --report   # only count what is missing and what is unusual; no network

Every line the course can say (``trust.course_lines``: items, the sentences patterns make, dialogues, themes, contrasts, the spans of notes)
is cut into pairs of neighbouring words and lone words (``trust.parts``). Each one not in ``<curriculum>/trust/pairs.json`` is looked up in
the corpora of the Árni Magnússon Institute through their public Korp service (https://malheildir.arnastofnun.is): first in everyday
writing (forums, blogs, subtitles), then, when none has it, in every corpus of present-day Icelandic (news, books, parliament, Wikipedia
too), and, for a pair with a number word, once more with the number in digits, as texts write it («ertu átján»: «Ertu 18 ára?»).
``--recheck`` looks up again what the table has as found in no text. The table keeps, for each pair, how many corpora have it (0: none). Only the existence is asked (the search stops at a corpus's first
hit), one request at a time with a pause: a public service. The table is saved every 50 lookups, so a run can stop and go on.
Network access is needed for the lookup only; the planner, ``validate`` and the tests read the table offline.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audiolesson import trust  # noqa: E402
from audiolesson.content import load_curriculum  # noqa: E402
from audiolesson.themes import load_themes  # noqa: E402

KORP = "https://malheildir.arnastofnun.is/korp-api"
AGENT = "language-learning-audio/attest_pairs (word-pair lookup for a language course)"
# the corpora of everyday writing, then every corpus of present-day Icelandic (old texts, laws and court rulings are left out)
EVERYDAY = ("IGC22_SOCIAL", "MIM_BLOGG", "MIM_TALMAL", "MIM_TOLVUPOSTUR", "MIM_VEFMIDLAR", "MIM_VEFSETUR", "MIM_VEFTIMARIT",
            "SAMHLIDA_OPENSUBTITLES_IS")
OTHERS = ("IGC22_WIKI", "IGC22_NEWS", "IGC2410EXT_NEWS", "IGC22_BOOKS", "IGC2410EXT_BOOKS", "IGC22_JOURNALS", "IGC22_PARLA",
          "IGC2410EXT_PARLA", "MIM_FRETTABLAD", "MIM_MOGGI", "MIM_RUV", "MIM_MBL_KVIKMYNDIR", "MIM_TEXTAVARP", "MIM_BAEKUR",
          "MIM_TIMARIT", "MIM_RITGERDIR", "MIM_VISINDAVEFUR", "MIM_ALTHINGI")
# a number word and the digits Icelanders write it with: written texts give ages, prices and times in digits («Ertu 18 ára?»), so a pair with a
# number word that no text has as words is looked up with the digits too (1–4 in every form: ``numbers.value_of``)
NUMBER_DIGITS = {
    "fimm": 5, "sex": 6, "sjö": 7, "átta": 8, "níu": 9, "tíu": 10, "ellefu": 11, "tólf": 12, "þrettán": 13, "fjórtán": 14, "fimmtán": 15,
    "sextán": 16, "sautján": 17, "átján": 18, "nítján": 19, "tuttugu": 20, "þrjátíu": 30, "fjörutíu": 40, "fimmtíu": 50, "sextíu": 60,
    "sjötíu": 70, "áttatíu": 80, "níutíu": 90,
}
ABOUT = {
    "about": "How many corpora of present-day Icelandic have each pair of neighbouring words (0: none), looked up by "
             "tools/attest_pairs.py in the corpora of the Árni Magnússon Institute (https://malheildir.arnastofnun.is): see README.md.",
}


def post(command: str, params: dict, tries: int = 4) -> dict:
    data = urllib.parse.urlencode(params).encode()
    last: Exception | None = None
    for n in range(tries):
        try:
            req = urllib.request.Request(f"{KORP}/{command}", data=data, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001: a busy service; wait and ask again
            last = e
            time.sleep(5 * (n + 1))
    raise RuntimeError(f"Korp {command} failed: {last}")


def corpora() -> tuple[str, str]:
    names = post("info", {})["corpora"]
    pick = lambda prefixes: ",".join(c for c in names if c.startswith(prefixes))  # noqa: E731
    return pick(EVERYDAY), pick(EVERYDAY + OTHERS)


def cqp(key: str) -> str:
    return " ".join(f'[word="{w}" %c]' for w in key.split(" "))


def found(corpus_list: str, key: str) -> int:
    """How many of the corpora have ``key``: the search stops at each corpus's first hit."""
    r = post("query", {"corpus": corpus_list, "cqp": cqp(key), "start": 0, "end": 0, "cut": 1, "default_context": "1 word"})
    if "ERROR" in r:
        raise RuntimeError(f"Korp: {r['ERROR']}")
    return int(r.get("hits", 0))


def as_digits(key: str) -> str | None:
    """``key`` with its number word in digits («ertu átján» → «ertu 18»); None when it has none."""
    from audiolesson.numbers import value_of

    words = key.split(" ")
    out = [str(NUMBER_DIGITS.get(w) or value_of(w) or "") or w for w in words]
    return " ".join(out) if out != words else None


def lookup(everyday: str, every: str, key: str, pause: float) -> int:
    """How many corpora have ``key``: everyday writing first, then every corpus, then (a number word) the same with digits."""
    for variant in [key] + ([d] if (d := as_digits(key)) else []):
        for corpus_list in (everyday, every):
            hits = found(corpus_list, variant)
            time.sleep(pause)
            if hits:
                return hits
    return 0


def needed(curriculum: Path) -> tuple[list[tuple[str, str]], set[str], set[str]]:
    cur = load_curriculum(curriculum)
    lines = trust.course_lines(cur, load_themes(curriculum, cur))
    pairs: set[str] = set()
    words: set[str] = set()
    for text, _ in lines:
        p = trust.parts(text)
        pairs.update(p.pairs)
        words.update(p.words)
    return lines, pairs, words


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("curriculum", type=Path, nargs="?", default=Path("curricula/is-en"))
    ap.add_argument("--report", action="store_true", help="count what is missing and list the unusual lines; no lookup")
    ap.add_argument("--limit", type=int, default=0, help="look up at most this many (0: all)")
    ap.add_argument("--pause", type=float, default=0.5, help="seconds between requests (default 0.5)")
    ap.add_argument("--recheck", action="store_true", help="look up again what the table has as found in no text (after the lookup changed)")
    args = ap.parse_args(argv)

    lines, pairs, words = needed(args.curriculum)
    table = trust.load(args.curriculum) or trust.Trust()
    todo = [("pair", k) for k in sorted(pairs - table.pairs.keys())] + [("word", k) for k in sorted(words - table.words.keys())]
    if args.recheck:
        todo = [("pair", k) for k in sorted(pairs) if table.pairs.get(k) == 0] + [("word", k) for k in sorted(words) if table.words.get(k) == 0]
    print(f"{len(lines)} lines; {len(pairs)} pairs and {len(words)} lone words; {len(todo)} not looked up yet", flush=True)
    if args.report:
        unusual = [(t, w, v.absent) for t, w in lines if (v := table.verdict(t)).status == "unusual"]
        for t, w, absent in unusual:
            print(f"unusual: «{t}» ({w}): no text has " + ", ".join(f"«{a}»" for a in absent))
        print(f"{len(unusual)} unusual lines")
        return 0
    if args.limit:
        todo = todo[: args.limit]
    everyday, every = corpora()
    stamp = {"checked_on": dt.date.today().isoformat(), **ABOUT}
    for n, (kind, key) in enumerate(todo, 1):
        hits = lookup(everyday, every, key, args.pause)
        (table.pairs if kind == "pair" else table.words)[key] = hits
        if n % 50 == 0 or n == len(todo):
            trust.save(args.curriculum, table, stamp)
            print(f"  {n}/{len(todo)} looked up", flush=True)
        if not hits:
            print(f"  none has «{key}»", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
