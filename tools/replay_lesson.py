#!/usr/bin/env python3
"""Replay a feedback export's lesson and the next ones, and print the daily-read table.

The daily read (docs/LEARNING-DESIGN.md §1, last checklist) starts from the export of the lesson
the learner just heard: its ``learner.before.json`` and ``manifest.json`` (the arguments it was
generated with). This rebuilds that lesson with the current code, as ``generate`` would, then
continues for ``--lessons`` lessons in all, and prints one table of the figures the reads compare:
length, short items said alone, sentence uses, narration repeats, open items, generated sentences by
form, listening scenes, and the planner's own records.

    python tools/replay_lesson.py EXPORT_DIR [--trip PROFILE] [--lessons 3] [--curriculum curricula/is-en]

``EXPORT_DIR`` is the ``lesson-NNN`` folder of an export. ``--trip`` is the private trip profile
(the channel topic's TOML), if the lesson was generated with ``--trip``: it orders the new items
and is read only for that. Its contents are never printed, and nothing is written anywhere.

The first column is the exported lesson rebuilt: when the code is the export's own revision it
reproduces the lesson exactly (the script reports the exported lesson's own size beside it). The
later columns are continuations under a stated assumption about the next day's review: every new
item recalled; open items asked are recalled, except those of ``--fail-words`` words or more.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audiolesson.cando import for_season, load_cando, priority_items  # noqa: E402
from audiolesson.content import load_curriculum  # noqa: E402
from audiolesson.learner import LearnerState  # noqa: E402
from audiolesson.planner import PlanConfig, Planner, apply_to_learner  # noqa: E402
from audiolesson.themes import load_themes, scenario_order  # noqa: E402
from audiolesson.prompts import Prompts  # noqa: E402
from audiolesson.timing import Timing  # noqa: E402
from audiolesson.trip import load_trip  # noqa: E402

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_SLOT = re.compile(r"\{[^{}]+\}")


def words(text: str | None) -> list[str]:
    return [w.lower() for w in _WORD.findall(text or "")]


def _template(t: str) -> re.Pattern:
    return re.compile("^" + ".+".join(re.escape(p) for p in _SLOT.split(t)) + "$", re.I)


def form_of(cur, ex) -> str:
    """plain / negative / question, by matching a generated sentence against its construction's templates."""
    text = ex.label.split(": ", 1)[-1].strip()
    for i in ex.item_ids:
        c = cur.by_id.get(i)
        if c is None or c.kind != "construction":
            continue
        if c.negative and _template(c.negative).match(text):
            return "negative"
        if c.question and _template(c.question).match(text):
            return "question"
    return "plain"


def measure(cur, sc, known_constructions: int) -> dict:
    """The daily-read figures of one built lesson."""
    m, exs = sc.meta, sc.exercises
    answers = collections.defaultdict(list)
    for s in sc.segments:
        if s.type == "answer" and s.exercise is not None:
            answers[s.exercise].append(" ".join(words(s.text)))
    narrated = [s.text for s in sc.segments if s.type == "narrate" and s.speaker == "instructor" and s.text]
    situations = collections.Counter(t for t in narrated if len(t) > 25)
    intros = sorted(e.start / 60 for e in exs if e.kind in ("intro", "embed"))
    short = {}
    for i in m["new_items"]:
        it = cur.by_id[i]
        if it.kind in ("construction", "transform") or len(words(it.target)) > 1:
            continue
        alone, sentences, distinct, scenes = 1, 0, set(), 0
        for e in exs:
            if i not in e.item_ids or e.kind == "intro":
                continue
            said = answers.get(e.index, [])
            if " ".join(words(it.target)) in said:
                if it.kind != "vocab" and (e.kind == "connect" or e.stage == "situation"):
                    scenes += 1  # an utterance in a scene is its proper use, not a drill (#187): not counted as alone
                else:
                    alone += 1
            else:
                sentences += 1
                distinct.update(said)
        short[i] = (alone, sentences, len(distinct), scenes)
    # #187: a part (any vocab item) or short utterance asked alone after a sentence holding it was already said this lesson
    said_before: list[str] = []
    part_after_whole = 0
    for e in exs:
        said = answers.get(e.index, [])
        it = cur.by_id.get(e.item_ids[0]) if e.item_ids else None
        if it and e.kind == "recall" and it.kind not in ("construction", "transform") and e.item_ids[0] not in m["new_items"] and (it.kind == "vocab" or len(words(it.target)) <= 2):
            own = " ".join(words(it.target))
            if own in said and any(f" {own} " in f" {t} " and t != own for t in said_before):
                part_after_whole += 1
        said_before.extend(said)
    open_practice = {i: sum(1 for e in exs if i in e.item_ids) for i in m.get("open_items", [])}
    forms = collections.Counter(form_of(cur, e) for e in exs if e.kind == "generative")
    per_construction = collections.Counter(
        c for e in exs if e.kind == "generative" for c in e.item_ids[:3] if cur.by_id.get(c) and cur.by_id[c].kind == "construction"
    )
    return {
        "lesson": sc.lesson_number,
        "minutes": round(max(e.start + e.duration for e in exs) / 60, 1),
        "exercises": len(exs),
        "new items": len(m["new_items"]),
        "constructions known at start": known_constructions,
        "short new item alone, most": max((v[0] for v in short.values()), default=0),
        "short items (alone / in sentences / distinct)": ", ".join(f"{k} {v[0]}/{v[1]}/{v[2]}" + (f" +{v[3]} in scenes" if v[3] else "") for k, v in short.items()) or "–",
        "short review item alone after its sentence": part_after_whole,
        "longest gap between introductions (min)": round(max((b - a for a, b in zip(intros, intros[1:])), default=0), 1),
        "most narrations of one situation": situations.most_common(1)[0][1] if situations else 0,
        "«Quick review» announcements": narrated.count("Quick review: two separate situations."),
        "narrations with «{»": sum(1 for t in narrated if "{" in t),
        "open items fitted / waiting": f"{len(m.get('open_items', []))} / {len(m.get('open_not_fitted', []))}",
        "open item practices, fewest": min(open_practice.values(), default="–"),
        "most appearances of one new item": max((sum(1 for e in exs if i in e.item_ids) for i in m["new_items"]), default=0),
        "generated sentences (plain / negative / question)": f"{sum(forms.values())} ({forms['plain']} / {forms['negative']} / {forms['question']})",
        "most sentences of one construction": max(per_construction.values(), default=0),
        "theme (level) / plays": f"{m['theme']['id']} ({m['theme']['level']}) / {m['theme']['plays']}" if m.get("theme") else "–",
        "listening dialogues": len(m.get("dialogues_listened", [])),
        "heard-only lines": narrated.count(Prompts.load(cur.known_lang).get("listening_line")),
        "tried lines / bonus questions": f"{len(m.get('listening_tried', []))} / {len(m.get('bonus_review', []))}",
        "cheap constructions": ", ".join(m.get("cheap_constructions", [])) or "–",
        "refresh sentences": sum((m.get("refresh_sentences") or {}).values()),
        "variants": ", ".join(m.get("variant_items", [])) or "–",
        "bare_cap_lapsed": m.get("bare_cap_lapsed"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("export", type=Path, help="the lesson-NNN folder of a feedback export")
    ap.add_argument("--trip", type=Path, default=None, help="the private trip profile, if the lesson used --trip")
    ap.add_argument("--lessons", type=int, default=3, help="lessons to build, the exported one included (default 3)")
    ap.add_argument("--curriculum", default="curricula/is-en")
    ap.add_argument("--fail-words", type=int, default=3, help="continuation: open items of this many words or more fail again")
    args = ap.parse_args(argv)

    manifest = json.loads((args.export / "manifest.json").read_text(encoding="utf-8"))
    gen = manifest.get("generate_args", [])

    def arg(name: str, default=None):
        return gen[gen.index(name) + 1] if name in gen else default

    if "--trip" in gen and args.trip is None:
        print("warning: the lesson was generated with --trip; without --trip here the new items differ", file=sys.stderr)
    minutes = float(arg("--minutes", 30))
    known = arg("--known")
    cur = load_curriculum(args.curriculum, known_lang=known)
    learner = LearnerState.load(args.export / "learner.before.json")
    priority: list[str] = []
    scenarios = load_cando(args.curriculum, cur) if Path(args.curriculum).is_dir() else []
    trip = load_trip(args.trip) if args.trip else None
    if trip is not None:
        priority = priority_items(cur, for_season(scenarios, trip.season), trip.boost)
    # the lesson's theme exchange (#149 1b-ii), loaded as `generate` does
    themes = load_themes(args.curriculum, cur, scenarios) if scenarios else []
    theme_scenarios = scenario_order(for_season(scenarios, trip.season) if trip else scenarios, trip.boost if trip else ()) if themes else []
    prompts = Prompts.load(cur.known_lang)
    day = date.fromisoformat(manifest["created_at"][:10])

    exported = None
    scripts = list(args.export.glob("*.script.json"))
    if scripts:
        raw = json.loads(scripts[0].read_text(encoding="utf-8"))
        ex = raw.get("exercises", [])
        if ex:
            exported = (len(ex), round(max(e["start"] + e["duration"] for e in ex) / 60, 1))

    rows: list[dict] = []
    for _ in range(args.lessons):
        known_c = sum(1 for c in cur.items if c.kind == "construction" and learner.knows(c.id))
        pace, _why = learner.suggest_pace(minutes, day)
        timing = Timing(level=learner.level or cur.level, speech_ratio=dict(learner.speech_calibration))
        sc = Planner(cur, learner, prompts, timing, PlanConfig(minutes=minutes, new_items=pace, priority=priority, themes=themes, theme_scenarios=theme_scenarios), today=day).build()
        rows.append(measure(cur, sc, known_c))
        apply_to_learner(sc, learner, day)
        day += timedelta(days=1)
        m = sc.meta
        asked = m.get("open_items", []) + m.get("open_not_fitted", [])[:3]
        failed = [i for i in asked if len(words(cur.by_id[i].target)) >= args.fail_words]
        learner.report(failed, [], day, lesson_number=sc.lesson_number,
                       recalled=[i for i in m["new_items"] + asked if i not in failed])

    print(f"Replay of {args.export.name} (exported LLA {manifest.get('revisions', {}).get('lla', '?')[:7]}), "
          f"--minutes {minutes:g}, trip ordering {'on' if priority else 'off'}")
    if exported:
        print(f"Exported lesson: {exported[0]} exercises, {exported[1]} min; rebuilt here: "
              f"{rows[0]['exercises']} exercises, {rows[0]['minutes']} min")
    print()
    print("| | " + " | ".join(f"lesson {r['lesson']}" for r in rows) + " |")
    print("|---" * (len(rows) + 1) + "|")
    for key in rows[0]:
        if key == "lesson":
            continue
        print(f"| {key} | " + " | ".join(str(r[key]) for r in rows) + " |")
    print()
    print(f"Lessons after the first assume: every new item recalled next day; open items asked recalled, "
          f"except those of {args.fail_words}+ words.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
