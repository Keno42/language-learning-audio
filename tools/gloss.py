"""Insert per-language glosses into curriculum module files.

    python tools/gloss.py ja curricula/is-en/01-greetings.toml < glosses.json

The JSON maps ids to glosses:
    {"items": {"takk": {"meaning": "ありがとう。", "situation": "…"}},
     "examples": {"negation_ekki": [["わかります。", "わかりません。"], …]},
     "dialogues": {"nagranni": {"setting": "…", "turns": [{"cue": "…", "partner_meaning": "…"}, …]}},
     "notes": {"pylsa": "…"},
     "curriculum": {"name": "…"}}

A key ``meaning`` becomes a ``meaning_<lang>`` line right after the ``meaning`` line of
that entry. Existing ``_<lang>`` lines are replaced. Structure is never changed, so the
file stays reviewable by eye.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _q(v: str) -> str:
    return json.dumps(v, ensure_ascii=False)


def _insert_after(lines: list[str], start: int, end: int, field: str, lang: str, value: str) -> int:
    """Within lines[start:end], put ``field_lang = value`` right after the ``field = …`` line.
    Returns the number of lines added (0 when an existing gloss line was replaced)."""
    key = f"{field}_{lang}"
    for i in range(start, end):
        stripped = lines[i].lstrip()
        if stripped.startswith(key + " ="):
            lines[i] = lines[i][: len(lines[i]) - len(stripped)] + f"{key} = {_q(value)}\n"
            return 0
    for i in range(start, end):
        stripped = lines[i].lstrip()
        if stripped.startswith(field + " ="):
            indent = lines[i][: len(lines[i]) - len(stripped)]
            lines.insert(i + 1, f"{indent}{key} = {_q(value)}\n")
            return 1
    raise SystemExit(f"no '{field} =' line in block starting at line {start + 1}")


def _blocks(lines: list[str], header: str) -> list[tuple[int, int]]:
    """(start, end) of each ``[[header]]`` block; a block ends at the next ``[[`` header of any kind."""
    starts = [i for i, l in enumerate(lines) if l.strip() == f"[[{header}]]"]
    out = []
    for s in starts:
        e = len(lines)
        for j in range(s + 1, len(lines)):
            if lines[j].startswith("[[") or lines[j].strip().startswith("[[dialogues.turns]]"):
                e = j
                break
        out.append((s, e))
    return out


def _id_of(lines: list[str], start: int, end: int) -> str | None:
    for i in range(start, end):
        m = re.match(r'\s*id = "([^"]+)"', lines[i])
        if m:
            return m.group(1)
    return None


def apply(path: Path, lang: str, data: dict) -> int:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    n = 0
    # curriculum meta
    if "curriculum" in data:
        for i, l in enumerate(lines):
            if l.strip() == "[curriculum]":
                for f, v in data["curriculum"].items():
                    _insert_after(lines, i, len(lines), f, lang, v)
                    n += 1
                break
    # items (process from the end so inserted lines don't shift earlier blocks)
    items = data.get("items", {})
    examples = data.get("examples", {})
    for s, e in reversed(_blocks(lines, "items")):
        iid = _id_of(lines, s, e)
        if iid in examples:
            pairs = examples[iid]
            k = 0
            for i in range(s, e):
                if "{ source = " in lines[i]:
                    src_ja, res_ja = pairs[k]
                    k += 1
                    l = lines[i]
                    l = re.sub(r', source_meaning_%s = "[^"]*"' % lang, "", l)
                    l = re.sub(r', result_meaning_%s = "[^"]*"' % lang, "", l)
                    l = re.sub(r'(source_meaning = "[^"]*")', lambda m: m.group(1) + f", source_meaning_{lang} = {_q(src_ja)}", l)
                    l = re.sub(r'(result_meaning = "[^"]*")', lambda m: m.group(1) + f", result_meaning_{lang} = {_q(res_ja)}", l)
                    lines[i] = l
                    n += 2
            if k != len(pairs):
                raise SystemExit(f"{iid}: {len(pairs)} example glosses but {k} examples")
        if iid in items:
            for f, v in items[iid].items():
                e += _insert_after(lines, s, e, f, lang, v)
                n += 1
    # dialogues: setting on the header block, turns in order
    dialogues = data.get("dialogues", {})
    dblocks = _blocks(lines, "dialogues")
    for s, e in reversed(dblocks):
        did = _id_of(lines, s, e)
        if did not in dialogues:
            continue
        d = dialogues[did]
        # turns belonging to this dialogue: from e until the next [[dialogues]]/[[items]]/[[notes]] header
        turn_starts = []
        j = e
        while j < len(lines) and not (lines[j].startswith("[[") and not lines[j].strip().startswith("[[dialogues.turns]]")):
            if lines[j].strip() == "[[dialogues.turns]]":
                turn_starts.append(j)
            j += 1
        turn_ranges = [(t, (turn_starts[k + 1] if k + 1 < len(turn_starts) else j)) for k, t in enumerate(turn_starts)]
        if "turns" in d and len(d["turns"]) != len(turn_ranges):
            raise SystemExit(f"{did}: {len(d['turns'])} turn glosses but {len(turn_ranges)} turns")
        for (ts, te), tg in reversed(list(zip(turn_ranges, d.get("turns", [])))):
            for f, v in tg.items():
                te += _insert_after(lines, ts, te, f, lang, v)
                n += 1
        if "setting" in d:
            _insert_after(lines, s, e, "setting", lang, d["setting"])
            n += 1
    notes = data.get("notes", {})
    for s, e in reversed(_blocks(lines, "notes")):
        nid = _id_of(lines, s, e)
        if nid in notes:
            _insert_after(lines, s, e, "text", lang, notes[nid])
            n += 1
    path.write_text("".join(lines), encoding="utf-8")
    return n


if __name__ == "__main__":
    lang, path = sys.argv[1], Path(sys.argv[2])
    data = json.load(sys.stdin)
    print(f"{path.name}: {apply(path, lang, data)} glosses written")
