"""Command line: generate / render / report / status / validate / voices."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .content import CurriculumError, load_curriculum
from .learner import LearnerState, parse_date
from .planner import PlanConfig, Planner, apply_to_learner
from .prompts import Prompts
from .script import Script
from .timing import Timing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="audiolesson", description="Generate audio-first, recall-driven language lessons.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="plan the next lesson, write script + transcript (+ audio), update the learner model")
    g.add_argument("--curriculum", "-c", required=True, help="curriculum .toml")
    g.add_argument("--learner", "-l", required=True, help="learner state .json (created if missing)")
    g.add_argument("--out", "-o", default="out", help="output directory (default: out/)")
    g.add_argument("--minutes", "-m", type=float, default=15.0)
    g.add_argument("--new", type=int, default=None, help="how many new items to introduce (default: about one per 3 minutes)")
    g.add_argument("--topics", "-t", default="", help="comma-separated topics to prefer")
    g.add_argument("--level", default=None, help="learner level for pause lengths: A0 A1 A2 B1 B2 (default: from learner state)")
    g.add_argument("--seed", type=int, default=None)
    g.add_argument("--date", default=None, help="pretend today is YYYY-MM-DD (for scheduling/tests)")
    g.add_argument("--pause-multiplier", type=float, default=None, help="scale every answer pause (e.g. 1.3 = more time)")
    g.add_argument("--no-translate", action="store_true", help="don't narrate the meaning of partner lines in dialogues")
    g.add_argument("--profile", "-p", default=None, help="voice profile .toml (see profiles/)")
    g.add_argument("--provider", default=None, help="TTS provider: stub, espeak, edge, openai, say (overrides profile)")
    g.add_argument("--no-audio", action="store_true", help="only write the script and transcript")
    g.add_argument("--dry-run", action="store_true", help="don't update the learner state")
    g.set_defaults(func=cmd_generate)

    r = sub.add_parser("render", help="render an existing script to audio (different voices / pauses / provider)")
    r.add_argument("script")
    r.add_argument("--out", "-o", default=None, help="output .wav path (default: next to the script)")
    r.add_argument("--profile", "-p", default=None)
    r.add_argument("--provider", default=None)
    r.add_argument("--pause-multiplier", type=float, default=None)
    r.add_argument("--cache", default=None, help="TTS cache directory")
    r.set_defaults(func=cmd_render)

    rp = sub.add_parser("report", help="after listening: tell the model which items you could not recall")
    rp.add_argument("--learner", "-l", required=True)
    rp.add_argument("--lesson", type=int, default=None, help="lesson number the feedback refers to")
    rp.add_argument("--failed", default="", help="comma-separated item ids you failed to produce")
    rp.add_argument("--easy", default="", help="comma-separated item ids that felt too easy")
    rp.add_argument("--date", default=None)
    rp.set_defaults(func=cmd_report)

    st = sub.add_parser("status", help="show learner progress and what is due")
    st.add_argument("--learner", "-l", required=True)
    st.add_argument("--curriculum", "-c", default=None)
    st.add_argument("--date", default=None)
    st.set_defaults(func=cmd_status)

    v = sub.add_parser("validate", help="check a curriculum file")
    v.add_argument("curriculum")
    v.set_defaults(func=cmd_validate)

    vo = sub.add_parser("voices", help="list default voices a provider offers for a language")
    vo.add_argument("--provider", default="edge")
    vo.add_argument("--lang", default="fr")
    vo.set_defaults(func=cmd_voices)

    args = ap.parse_args(argv)
    try:
        return args.func(args) or 0
    except (CurriculumError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


# ----------------------------------------------------------------------------


def _split(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def cmd_generate(args) -> int:
    cur = load_curriculum(args.curriculum)
    learner = LearnerState.load_or_create(args.learner, cur.target_lang, cur.known_lang, cur.level)
    level = args.level or learner.level or cur.level
    today = parse_date(args.date)
    timing = Timing(level=level).with_overrides(global_pause_multiplier=args.pause_multiplier)
    prompts = Prompts.load(cur.known_lang)
    cfg = PlanConfig(
        minutes=args.minutes,
        new_items=args.new,
        topics=_split(args.topics),
        seed=args.seed,
        translate_partner=not args.no_translate,
    )
    unknown_topics = [t for t in cfg.topics if t not in cur.topics()]
    if unknown_topics:
        print(f"warning: topics not in curriculum: {unknown_topics}; available: {cur.topics()}", file=sys.stderr)

    script = Planner(cur, learner, prompts, timing, cfg, today=today).build()
    n = script.lesson_number
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = out / f"lesson-{n:03d}"
    script.save(f"{stem}.script.json")
    Path(f"{stem}.transcript.md").write_text(script.transcript(), encoding="utf-8")
    Path(f"{stem}.plan.json").write_text(json.dumps(_plan(script, cur), ensure_ascii=False, indent=1), encoding="utf-8")

    s = script.summary()
    print(f"Lesson {n}: {s['duration_s']/60:.1f} min planned, {s['prompts']} spoken responses, "
          f"{int(s['active_ratio']*100)}% of the time is yours to speak")
    print(f"  new: {', '.join(script.meta['new_items']) or '(none — curriculum exhausted, review only)'}")
    print(f"  reviewed: {len(script.meta['reviewed_items'])} items, dialogues: {', '.join(script.meta['dialogues']) or '-'}")
    print(f"  wrote {stem}.script.json, .transcript.md, .plan.json")

    if not args.no_audio:
        from .render import load_profile, render_script
        from .render.renderer import save_cues

        profile = load_profile(args.profile, args.provider)
        cues = render_script(script, profile, f"{stem}.wav", cache_dir=out / "cache" / profile.provider)
        save_cues(cues, f"{stem}.cues.json")
        print(f"  audio: {cues['mp3'] or cues['wav']} ({cues['duration_s']/60:.1f} min, provider {cues['provider']})")

    if args.dry_run:
        print("  (dry run: learner state not updated)")
    else:
        apply_to_learner(script, learner, today, presume_success=cfg.presume_success)
        learner.level = level
        learner.save(args.learner)
        print(f"  learner state updated: {args.learner} (use `audiolesson report` after listening if some items failed)")
    return 0


def _plan(script: Script, cur) -> dict:
    meta = script.meta

    def describe(i: str) -> dict:
        it = cur.by_id.get(i)
        return {"id": i, "target": it.target if it else None, "meaning": it.meaning if it else None, "kind": it.kind if it else None}

    return {
        "lesson_number": script.lesson_number,
        "date": meta.get("date"),
        "config": meta.get("config"),
        "summary": script.summary(),
        "new_items": [describe(i) for i in meta.get("new_items", [])],
        "reviewed_items": [describe(i) for i in meta.get("reviewed_items", [])],
        "dialogues": meta.get("dialogues", []),
        "exposures": meta.get("exposures", {}),
        "exercises": [
            {"index": e.index, "kind": e.kind, "stage": e.stage, "items": e.item_ids, "label": e.label, "start_s": round(e.start, 1), "duration_s": round(e.duration, 1)}
            for e in script.exercises
        ],
    }


def cmd_render(args) -> int:
    from .render import load_profile, render_script
    from .render.renderer import save_cues

    script = Script.load(args.script)
    profile = load_profile(args.profile, args.provider)
    if args.pause_multiplier is not None:
        profile.pause_multiplier = args.pause_multiplier
    src = Path(args.script)
    out = Path(args.out) if args.out else src.with_name(src.name.replace(".script.json", "") + ".wav")
    cache = Path(args.cache) if args.cache else out.parent / "cache" / profile.provider
    cues = render_script(script, profile, out, cache_dir=cache)
    save_cues(cues, out.with_suffix(".cues.json"))
    print(f"audio: {cues['mp3'] or cues['wav']} ({cues['duration_s']/60:.1f} min, provider {cues['provider']})")
    return 0


def cmd_report(args) -> int:
    learner = LearnerState.load(args.learner)
    today = parse_date(args.date)
    changed = learner.report(_split(args.failed), _split(args.easy), today, args.lesson)
    learner.save(args.learner)
    if changed["failed"]:
        print(f"marked as failed (back to an easier stage, due tomorrow): {', '.join(changed['failed'])}")
    if changed["easy"]:
        print(f"marked as easy (longer interval): {', '.join(changed['easy'])}")
    if changed["unknown"]:
        print(f"warning: not in learner state: {', '.join(changed['unknown'])}", file=sys.stderr)
    if not (changed["failed"] or changed["easy"]):
        print("nothing to report; pass --failed and/or --easy item ids (see the lesson's .plan.json)")
    return 0


def cmd_status(args) -> int:
    learner = LearnerState.load(args.learner)
    today = parse_date(args.date)
    cur = load_curriculum(args.curriculum) if args.curriculum else None
    print(f"{learner.target_lang} for {learner.known_lang} speakers, level {learner.level}, {learner.lessons_completed} lessons, {len(learner.items)} items met")
    if cur:
        unmet = [i.id for i in cur.items if i.id not in learner.items]
        print(f"curriculum {cur.name!r}: {len(cur.items) - len(unmet)}/{len(cur.items)} items introduced")
    rows = []
    for item_id, st in learner.items.items():
        rows.append((learner.review_priority(item_id, today), item_id, st))
    rows.sort(key=lambda r: -r[0])
    print(f"{'item':28} {'stage':10} {'due':10} {'ok':>3} {'fail':>4} {'ivl':>5}")
    for prio, item_id, st in rows[:40]:
        flag = "*" if prio >= 1.0 else " "
        print(f"{flag}{item_id:27} {st.stage:10} {st.due:10} {st.successes:3d} {st.failures:4d} {st.interval_days:5.1f}")
    if len(rows) > 40:
        print(f"… and {len(rows) - 40} more")
    due = sum(1 for prio, _, _ in rows if prio >= 1.0)
    print(f"{due} items due for review today ({today.isoformat()}); * = due")
    return 0


def cmd_validate(args) -> int:
    cur = load_curriculum(args.curriculum)
    kinds = {}
    for i in cur.items:
        kinds[i.kind] = kinds.get(i.kind, 0) + 1
    print(f"ok: {cur.name} ({cur.target_lang} for {cur.known_lang} speakers): {len(cur.items)} items {kinds}, {len(cur.dialogues)} dialogues, topics {cur.topics()}")
    return 0


def cmd_voices(args) -> int:
    from .render.tts import get_provider

    p = get_provider(args.provider)
    problem = p.check()
    if problem:
        print(f"note: {problem}", file=sys.stderr)
    voices = p.default_voices(args.lang)
    print("\n".join(voices) if voices else f"(no defaults for {args.lang!r} — set voices in a profile)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
