"""Command line: generate / render / report / status / validate / voices."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .content import CurriculumError, dialogue_sequencing_report, load_curriculum
from .learner import LearnerState, parse_date
from .planner import PlanConfig, Planner, apply_to_learner
from .prompts import Prompts
from .script import Script
from .timing import Timing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="audiolesson", description="Generate audio-first, recall-driven language lessons.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_user_args(parser):
        parser.add_argument("--user", "-u", default=None, help="learner name: everything lives under <root>/<user>/ and settings are remembered there")
        parser.add_argument("--root", default=os.environ.get("AUDIOLESSON_ROOT", "out"), help="root for --user directories (default: out/, or $AUDIOLESSON_ROOT)")

    g = sub.add_parser("generate", help="plan the next lesson, write script + transcript (+ audio), update the learner model")
    add_user_args(g)
    g.add_argument("--curriculum", "-c", default=None, help="curriculum .toml or directory of modules (remembered per --user)")
    g.add_argument("--known", default=None, help="learner's language when the curriculum carries several glosses (e.g. ja)")
    g.add_argument("--allow-fallback", action="store_true", help="use the primary-language text where a gloss in --known is missing")
    g.add_argument("--learner", "-l", default=None, help="learner state .json (created if missing); implied by --user")
    g.add_argument("--out", "-o", default=None, help="output directory (default: out/, or <root>/<user>/ with --user)")
    g.add_argument("--minutes", "-m", type=float, default=None, help="lesson length (default 15, remembered per --user)")
    g.add_argument("--new", type=int, default=None, help="new items to introduce this lesson (default: the learner's pace, see README 'Pacing')")
    g.add_argument("--pace", type=int, default=None, help="set the learner's ongoing pace (new items per lesson) before planning")
    g.add_argument("--auto", action="store_true", help="auto mode (persists): pace rises on its own every few lessons; `report --failed` still slows it")
    g.add_argument("--manual", action="store_true", help="back to manual mode (persists): pace rises only after `report`")
    g.add_argument("--topics", "-t", default="", help="comma-separated topics to prefer")
    g.add_argument("--level", default=None, help="learner level for pause lengths: A0 A1 A2 B1 B2 (default: from learner state)")
    g.add_argument("--seed", type=int, default=None)
    g.add_argument("--date", default=None, help="pretend today is YYYY-MM-DD (for scheduling/tests)")
    g.add_argument("--pause-multiplier", type=float, default=None, help="scale every answer pause (e.g. 1.3 = more time)")
    g.add_argument("--no-translate", action="store_true", help="don't narrate the meaning of partner lines in dialogues")
    g.add_argument("--profile", "-p", default=None, help="voice profile .toml (see profiles/)")
    g.add_argument("--provider", default=None, help="TTS provider: stub, espeak, edge, openai, say (overrides profile)")
    g.add_argument("--no-audio", action="store_true", help="only write the script and transcript")
    g.add_argument("--no-fit", action="store_true", help="don't scale pauses to land on --minutes")
    g.add_argument("--fit-tolerance", type=float, default=None, help="seconds of slack before pauses are scaled (default 60)")
    g.add_argument("--dry-run", action="store_true", help="don't update the learner state")
    g.set_defaults(func=cmd_generate)

    r = sub.add_parser("render", help="render an existing script to audio (different voices / pauses / provider)")
    r.add_argument("script")
    r.add_argument("--out", "-o", default=None, help="output .wav path (default: next to the script)")
    r.add_argument("--profile", "-p", default=None)
    r.add_argument("--provider", default=None)
    r.add_argument("--pause-multiplier", type=float, default=None)
    r.add_argument("--cache", default=None, help="TTS cache directory")
    r.add_argument("--minutes", "-m", type=float, default=None, help="fit the audio to this length (default: the script's)")
    r.add_argument("--no-fit", action="store_true")
    r.add_argument("--fit-tolerance", type=float, default=None)
    r.set_defaults(func=cmd_render)

    rp = sub.add_parser("report", help="after listening: tell the model which items you could not recall")
    add_user_args(rp)
    rp.add_argument("--learner", "-l", default=None)
    rp.add_argument("--lesson", type=int, default=None, help="lesson number the feedback refers to")
    rp.add_argument("--failed", default="", help="comma-separated item ids you failed to produce")
    rp.add_argument("--easy", default="", help="comma-separated item ids that felt too easy")
    rp.add_argument("--date", default=None)
    rp.set_defaults(func=cmd_report)

    st = sub.add_parser("status", help="show learner progress and what is due")
    add_user_args(st)
    st.add_argument("--learner", "-l", default=None)
    st.add_argument("--curriculum", "-c", default=None)
    st.add_argument("--known", default=None)
    st.add_argument("--date", default=None)
    st.set_defaults(func=cmd_status)

    v = sub.add_parser("validate", help="check a curriculum file or directory, and its gloss coverage per language")
    v.add_argument("curriculum")
    v.add_argument("--known", default=None, help="report what is missing for this learner language")
    v.set_defaults(func=cmd_validate)

    vo = sub.add_parser("voices", help="list default voices a provider offers for a language")
    vo.add_argument("--provider", default="edge")
    vo.add_argument("--lang", default="fr")
    vo.set_defaults(func=cmd_voices)

    args = ap.parse_args(argv)
    try:
        _apply_user(args)
        return args.func(args) or 0
    except (CurriculumError, FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


# ----------------------------------------------------------------------------


USER_SETTINGS = ("curriculum", "known", "profile", "provider", "minutes", "level")


def _user_dir(args) -> Path | None:
    user = getattr(args, "user", None)
    if not user:
        return None
    if "/" in user or user in (".", ".."):
        raise ValueError(f"--user must be a plain name, not a path: {user!r}")
    return Path(args.root) / user


def _apply_user(args) -> None:
    """Resolve --user into learner/out paths and remembered settings; validate explicit mode otherwise."""
    base = _user_dir(args)
    if base is None:
        if hasattr(args, "learner") and not args.learner:
            raise ValueError("pass --user NAME (everything under out/NAME/) or --learner FILE")
        if args.cmd == "generate" and not args.curriculum:
            raise ValueError("pass --curriculum (or --user with a curriculum remembered in its settings)")
        if hasattr(args, "minutes") and args.minutes is None and args.cmd == "generate":
            args.minutes = 15.0
        if hasattr(args, "out") and args.out is None and args.cmd == "generate":
            args.out = "out"
        return
    # --user picks the paths; --learner/--out would silently conflict with that, so refuse rather than override
    if getattr(args, "learner", None):
        raise ValueError(f"--user {args.user!r} already implies --learner {str(base / 'learner.json')!r}; pass one or the other")
    if args.cmd == "generate" and args.out:
        raise ValueError(f"--user {args.user!r} already implies --out {str(base)!r}; pass one or the other")
    base.mkdir(parents=True, exist_ok=True)
    settings_path = base / "settings.json"
    saved = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    for key in USER_SETTINGS:
        if hasattr(args, key) and getattr(args, key) is None and key in saved:
            setattr(args, key, saved[key])
    if args.cmd == "generate":
        if args.minutes is None:
            args.minutes = 15.0
        if not args.curriculum:
            raise ValueError(f"first lesson for {args.user!r}: pass --curriculum (it is remembered in {settings_path})")
        args.out = str(base)
    args.learner = str(base / "learner.json")
    args.user_settings_path = settings_path


def _learner_hint(args, extra: str = "") -> str:
    """How to point another audiolesson command at this same learner, for messages."""
    base = f"audiolesson report -u {args.user}" if getattr(args, "user", None) else f"audiolesson report -l {args.learner}"
    return base + extra


def _save_user_settings(args) -> None:
    """Remember what --curriculum/--known/--profile/--provider/--minutes/--level were used, keyed by --user.

    Feedback mode (auto/manual) and pace are not duplicated here: they already live in
    the learner state file (learner.feedback_mode, learner.pace), which is the one
    place that tracks them.
    """
    path = getattr(args, "user_settings_path", None)
    if not path:
        return
    data = {k: getattr(args, k) for k in USER_SETTINGS if getattr(args, k, None) is not None}
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _split(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def _load(path: str, known: str | None, allow_fallback: bool = False):
    cur = load_curriculum(path, known_lang=known)
    if known and cur.missing_glosses and not allow_fallback:
        sample = ", ".join(cur.missing_glosses[:8])
        raise CurriculumError(
            f"{len(cur.missing_glosses)} strings have no {known!r} gloss (e.g. {sample}); add them or pass --allow-fallback"
        )
    if known and cur.missing_glosses:
        print(f"warning: {len(cur.missing_glosses)} strings fall back to {cur.known_langs[0]!r}", file=sys.stderr)
    return cur


def cmd_generate(args) -> int:
    cur = _load(args.curriculum, args.known, args.allow_fallback)
    learner = LearnerState.load_or_create(args.learner, cur.target_lang, cur.known_lang, cur.level)
    level = args.level or learner.level or cur.level
    today = parse_date(args.date)
    timing = Timing(level=level, speech_ratio=dict(learner.speech_calibration)).with_overrides(global_pause_multiplier=args.pause_multiplier)
    prompts = Prompts.load(cur.known_lang)
    if args.auto:
        learner.feedback_mode = "auto"
    if args.manual:
        learner.feedback_mode = "manual"
    if args.pace is not None:
        learner.pace = args.pace
        learner.pace_changed_at = learner.lessons_completed
    if args.new is not None:
        new_items, why = args.new, f"--new {args.new}"
    else:
        new_items, why = learner.suggest_pace(args.minutes, today)
    cfg = PlanConfig(
        minutes=args.minutes,
        new_items=new_items,
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
    pronunciation_notes = {i.id: i.pronunciation_notes for i in cur.items if i.pronunciation_notes}
    Path(f"{stem}.transcript.md").write_text(script.transcript(pronunciation_notes), encoding="utf-8")
    Path(f"{stem}.plan.json").write_text(json.dumps(_plan(script, cur), ensure_ascii=False, indent=1), encoding="utf-8")

    s = script.summary()
    print(f"Lesson {n}: {s['duration_s']/60:.1f} min planned, {s['prompts']} spoken responses, "
          f"{int(s['active_ratio']*100)}% of the time is yours to speak")
    if s["duration_s"] < args.minutes * 60 * 0.8:
        print(f"  (shorter than {args.minutes:g} min: nothing more to review yet — normal for the first lessons)")
    print(f"  pace: {why}")
    print(f"  new: {', '.join(script.meta['new_items']) or '(none — curriculum exhausted, review only)'}")
    carried = len(script.meta.get("due_not_fitted", []))
    print(f"  reviewed: {len(script.meta['reviewed_items'])} items ({script.meta.get('due_at_start', 0)} were due"
          + (f", {carried} carried over" if carried else "") + f"), dialogues: {', '.join(script.meta['dialogues']) or '-'}"
          + (f", asides: {', '.join(script.meta['notes'])}" if script.meta.get("notes") else ""))
    print(f"  wrote {stem}.script.json, .transcript.md, .plan.json")

    if not args.no_audio:
        from .render import load_profile, render_script
        from .render.renderer import save_cues

        profile = load_profile(args.profile, args.provider)
        if args.no_fit:
            profile.fit = False
        if args.fit_tolerance is not None:
            profile.fit_tolerance = args.fit_tolerance
        cache_root = Path(args.root) if getattr(args, "user", None) else out
        cues = render_script(script, profile, f"{stem}.wav", cache_dir=cache_root / "cache" / profile.provider)
        save_cues(cues, f"{stem}.cues.json")
        print(f"  audio: {cues['mp3'] or cues['wav']} ({_mmss(cues['duration_s'])}, provider {cues['provider']}"
              + (f", pauses ×{cues['fit_scale']:.2f}" if profile.fit and abs(cues['fit_scale'] - 1) > 0.005 else "") + ")")
        if abs(cues["duration_s"] - args.minutes * 60) > 60:
            print(f"  note: {abs(cues['duration_s'] - args.minutes * 60)/60:.1f} min off target — "
                  + ("not enough material yet" if cues["duration_s"] < args.minutes * 60 else "speech ran long") + "; calibration will tighten the next plan")
        if not args.dry_run:
            learner.calibrate(cues.get("calibration", {}))

    if args.dry_run:
        print("  (dry run: learner state not updated)")
    else:
        apply_to_learner(script, learner, today, presume_success=cfg.presume_success)
        learner.level = level
        if args.new is None:
            learner.pace = new_items
        learner.save(args.learner)
        _save_user_settings(args)
        print(f"  learner state updated: {args.learner} (use `{_learner_hint(args, ' --failed id,id')}` after listening if some items failed)")
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
    if args.no_fit:
        profile.fit = False
    if args.fit_tolerance is not None:
        profile.fit_tolerance = args.fit_tolerance
    cues = render_script(script, profile, out, cache_dir=cache, target_seconds=args.minutes * 60 if args.minutes else None)
    save_cues(cues, out.with_suffix(".cues.json"))
    print(f"audio: {cues['mp3'] or cues['wav']} ({_mmss(cues['duration_s'])}, provider {cues['provider']}, pauses ×{cues['fit_scale']:.2f})")
    return 0


def _mmss(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


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
        print(f"lesson {changed['lesson']} recorded as all good (pass --failed/--easy item ids from the lesson's .plan.json otherwise)")
    return 0


def cmd_status(args) -> int:
    learner = LearnerState.load(args.learner)
    today = parse_date(args.date)
    cur = load_curriculum(args.curriculum, known_lang=args.known) if args.curriculum else None
    print(f"{learner.target_lang} for {learner.known_lang} speakers, level {learner.level}, {learner.lessons_completed} lessons, {len(learner.items)} items met")
    if cur:
        unmet = [i.id for i in cur.items if i.id not in learner.items]
        print(f"curriculum {cur.name!r}: {len(cur.items) - len(unmet)}/{len(cur.items)} items introduced")
    rows = []
    for item_id, st in learner.items.items():
        rows.append((learner.review_priority(item_id, today), item_id, st))
    rows.sort(key=lambda r: -r[0])
    print(f"{'item':28} {'stage':10} {'due':10} {'ok':>3} {'dur':>3} {'fail':>4} {'ivl':>5}")
    for prio, item_id, st in rows[:40]:
        flag = "*" if prio >= 1.0 else " "
        print(f"{flag}{item_id:27} {st.stage:10} {st.due:10} {st.successes:3d} {st.durable_successes:3d} {st.failures:4d} {st.interval_days:5.1f}")
    if len(rows) > 40:
        print(f"… and {len(rows) - 40} more")
    due = sum(1 for prio, _, _ in rows if prio >= 1.0)
    print(f"{due} items due for review today ({today.isoformat()}); * = due")
    if learner.lessons:
        trend = " ".join(str(l.get("due_at_start", "?")) for l in learner.lessons[-8:])
        carried = " ".join(str(l.get("due_not_fitted", "?")) for l in learner.lessons[-8:])
        print(f"pace: {learner.pace or 'default'} new items/lesson ({learner.feedback_mode} mode); due at start of last lessons: {trend}; not fitted: {carried}")
        unreported = [l["number"] for l in learner.lessons[-3:] if l["number"] not in learner.reported]
        if unreported and learner.feedback_mode != "auto":
            print(f"no feedback yet for lesson(s) {unreported}: run `{_learner_hint(args, ' [--failed ids]')}`")
    return 0


def cmd_validate(args) -> int:
    cur = load_curriculum(args.curriculum, known_lang=args.known)
    kinds = {}
    for i in cur.items:
        kinds[i.kind] = kinds.get(i.kind, 0) + 1
    print(f"ok: {cur.name} ({cur.target_lang} for {cur.known_lang} speakers): {len(cur.items)} items {kinds}, {len(cur.dialogues)} dialogues, {len(cur.notes)} notes, topics {cur.topics()}")
    others = [l for l in cur.known_langs if l != cur.known_langs[0]]
    if others:
        print(f"glosses also available for: {', '.join(others)}")
    for lang in others if not args.known else [args.known]:
        c = load_curriculum(args.curriculum, known_lang=lang)
        total = len(load_curriculum(args.curriculum, known_lang="zz").missing_glosses)  # every glossable string
        if c.missing_glosses:
            by_item: dict[str, int] = {}
            for m in c.missing_glosses:
                by_item[m.split(".")[0]] = by_item.get(m.split(".")[0], 0) + 1
            print(f"{lang}: {total - len(c.missing_glosses)}/{total} strings glossed; missing in {len(by_item)} entries, e.g. {', '.join(list(by_item)[:10])}")
        else:
            print(f"{lang}: complete ({total} strings)")
    findings = dialogue_sequencing_report(cur)
    if findings:
        words: dict[str, int] = {}
        for f in findings:
            words[f["word"]] = words.get(f["word"], 0) + 1
        repeats = sorted((w for w, n in words.items() if n > 1), key=lambda w: -words[w])
        print(
            f"advisory (not a failure): {len(findings)} dialogue/word pairs where the "
            f"earliest teaching item sits >100 items past the dialogue's own requirements — a "
            f"sequencing signal, not a gate. Worst: {findings[0]['dialogue']!r} needs {findings[0]['word']!r} "
            f"from {findings[0]['item']!r} (#{findings[0]['item_order']}), {findings[0]['gap']} items past its own base."
        )
        if repeats:
            print(f"  words repeating across dialogues (candidates to introduce earlier, as reusable items): {', '.join(repeats[:10])}")
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
