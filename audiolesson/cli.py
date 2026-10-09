"""Command line: generate / render / report / status / validate / voices."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .themes import load_themes, scenario_order
from .cando import check_horizon, coverage, for_season, format_coverage, load_cando, priority_items, simulate_reach
from .exercises import meaning_prompt, meaning_prompts
from .content import CurriculumError, dialogue_sequencing_report, frame_gap_report, load_curriculum, part_before_whole_report
from .learner import LOADS, NEW_TARGET_MINUTES, LearnerState, parse_date
from .planner import PlanConfig, Planner, apply_to_learner
from .prompts import Prompts
from .script import Script
from .timing import Timing
from .reading import load_deck
from .scenes import available, load_scenes, uncovered
from .trip import load_trip


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
    g.add_argument("--new", type=int, default=None, help="new items to introduce this lesson, counting items (default: the learner's target of weighted new components, see README 'Pacing')")
    g.add_argument("--pace", type=int, default=None, help="set the learner's ongoing pace (new items per lesson) before planning; this lesson counts items, not components")
    g.add_argument("--auto", action="store_true", help="auto mode (persists): pace rises on its own every few lessons; `report --failed` still slows it")
    g.add_argument("--manual", action="store_true", help="back to manual mode (persists): pace rises only after `report`")
    g.add_argument("--topics", "-t", default="", help="comma-separated topics to prefer")
    g.add_argument("--level", default=None, help="learner level for pause lengths: A0 A1 A2 B1 B2 (default: from learner state)")
    g.add_argument("--seed", type=int, default=None)
    g.add_argument("--order", choices=("spread", "new-first"), default="spread",
                   help="spread (default): new items over the lesson; new-first: every new item first, then known material (a user option)")
    g.add_argument("--date", default=None, help="pretend today is YYYY-MM-DD (for scheduling/tests)")
    g.add_argument("--pause-multiplier", type=float, default=None, help="scale every answer pause (e.g. 1.3 = more time)")
    g.add_argument("--no-translate", action="store_true", help="don't narrate the meaning of partner lines in dialogues")
    g.add_argument("--profile", "-p", default=None, help="voice profile .toml (see profiles/)")
    g.add_argument("--provider", default=None, help="TTS provider: stub, espeak, edge, openai, say (overrides profile)")
    g.add_argument("--no-audio", action="store_true", help="only write the script and transcript")
    g.add_argument("--late-unhinted-recall", action="store_true", help="lever (#136): the closing recall of each new item gives no hint")
    g.add_argument("--trip", default=None, help="private trip profile .toml (#132): teach the can-do items (for its season) first; its contents are never written to outputs")
    g.add_argument("--cache", default=None, help="TTS cache directory (default: cache/<provider> under --out, or under --root with --user); safe to share between learners")
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

    rp = sub.add_parser("report", help="after listening: tell the model which items you recalled, hesitated on or could not recall")
    add_user_args(rp)
    rp.add_argument("--learner", "-l", default=None)
    rp.add_argument("--lesson", type=int, default=None, help="lesson number the feedback refers to")
    rp.add_argument("--failed", default="", help="comma-separated item ids you failed to produce")
    rp.add_argument("--hesitated", default="", help="comma-separated item ids you produced, but only after hesitating")
    rp.add_argument("--recalled", default="", help="comma-separated item ids you confirmed you recalled")
    rp.add_argument("--easy", default="", help="comma-separated item ids that felt too easy")
    rp.add_argument("--sooner", default="", help="comma-separated item ids the learner does not remember: they come back sooner (due within half their interval), without an outcome being recorded")
    rp.add_argument("--load", choices=LOADS, default=None, help="how heavy the lesson was: light, right or heavy (does not mark the lesson reported on its own)")
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
    v.add_argument("--frames", action="store_true", help="list every vocab item with no frame or dialogue near its introduction")
    v.add_argument("--parts", action="store_true", help="list every item taught after a phrase that already contains it (G13)")
    v.add_argument("--frame-span", type=int, default=50, help="items between a word and its first frame before it counts as late (default 50)")
    v.add_argument("--cando", action="store_true", help="travel can-do coverage (#131): each scenario's items, when they are reached, what is missing (simulates lessons; slow)")
    v.add_argument("--lessons", type=int, default=None, help="--cando: daily lessons before departure (default: days left to the --trip profile's departure, else 84)")
    v.add_argument("--paces", default="6,8,10", help="--cando: new items per lesson to simulate, comma-separated (default 6,8,10)")
    v.add_argument("--trip", default=None, help="--cando: simulate with the trip ordering from this private profile (an empty file: the default A-then-B ordering)")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("reading", help="the reading deck (#133) as JSON, for the Discord review")
    r.add_argument("curriculum")
    r.add_argument("--trip", default=None, help="private trip profile: add a card for each of its places (not stored anywhere)")
    r.set_defaults(func=cmd_reading)

    sc = sub.add_parser("scenes", help="the scenario cards (#129) the learner can take, as JSON, for the Discord review")
    sc.add_argument("curriculum")
    sc.add_argument("--learner", dest="learner_file", default=None, help="learner.json: only cards whose items the learner has met (none met if the file is missing)")
    sc.add_argument("--trip", default=None, help="private trip profile: its season decides the seasonal cards")
    sc.set_defaults(func=cmd_scenes)

    q = sub.add_parser("questions", help="the review question (prompt and answer) for single items as JSON, for the Discord review (#220)")
    q.add_argument("curriculum")
    q.add_argument("--ids", default="", help="item ids, comma-separated; unknown ids and constructions are left out")
    q.add_argument("--known", default=None)
    q.set_defaults(func=cmd_questions)

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
    new_target = None
    if args.new is not None:
        new_items, why = args.new, f"--new {args.new}"
    elif args.pace is not None:
        new_items, why = learner.suggest_pace(args.minutes, today)  # an explicit pace in items: this lesson counts items (#218 b3)
    else:
        new_items, items_why = learner.suggest_pace(args.minutes, today)
        # the target is a rate per 30 minutes, so its rules (the backlog's review slots included) run at 30 minutes: at 5, the slots
        # are about 0 and the backlog rule would lower the rate every lesson (#242)
        new_target, why = learner.suggest_target(NEW_TARGET_MINUTES, today)
        why += f" (≈ {new_items} items)"
    priority: list[str] = []
    scenarios = load_cando(args.curriculum, cur) if Path(args.curriculum).is_dir() else []
    trip = load_trip(args.trip) if args.trip else None
    if trip is not None:
        if not scenarios:
            print("warning: --trip given but the curriculum has no can-do scenarios (cando/*.toml)", file=sys.stderr)
        priority = priority_items(cur, for_season(scenarios, trip.season), trip.boost)
    # #149 1b-ii: the lesson's theme exchange, from the trip profile's boosted scenarios first, else Tier A
    themes = load_themes(args.curriculum, cur, scenarios) if scenarios else []
    theme_scenarios = scenario_order(for_season(scenarios, trip.season) if trip else scenarios, trip.boost if trip else ()) if themes else []
    # the learner's target is a rate per 30 minutes; this lesson plans its share of it (the rate is what is saved)
    plan_target = None if new_target is None else max(1.0, new_target * args.minutes / NEW_TARGET_MINUTES)
    cfg = PlanConfig(
        minutes=args.minutes,
        new_items=new_items,
        new_target=plan_target,
        topics=_split(args.topics),
        seed=args.seed,
        translate_partner=not args.no_translate,
        priority=priority,
        themes=themes,
        theme_scenarios=theme_scenarios,
        late_unhinted_recall=args.late_unhinted_recall,
        order=args.order,
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
    if priority:
        # never the profile's contents: only that one is in use
        print(f"  trip ordering: {len(priority)} can-do items first")
    print(f"  new: {', '.join(script.meta['new_items']) or '(none — curriculum exhausted, review only)'}")
    if script.meta.get("new_components"):
        nc = script.meta["new_components"]
        print(f"  new components (weighted): {nc['total']:g} of a target {nc['target']:g}" + (f", {nc['forms']:g} of them forms" if nc["forms"] else ""))
    carried = len(script.meta.get("due_not_fitted", []))
    early = len(script.meta.get("reviewed_early", []))
    print(f"  reviewed: {len(script.meta['reviewed_items'])} items ({script.meta.get('due_at_start', 0)} were due"
          + (f", {early} early" if early else "")
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
        cache = Path(args.cache) if args.cache else cache_root / "cache" / profile.provider
        cues = render_script(script, profile, f"{stem}.wav", cache_dir=cache)
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
        if new_target is not None:
            learner.new_target = new_target
        learner.save(args.learner)
        _save_user_settings(args)
        print(f"  learner state updated: {args.learner} (use `{_learner_hint(args, ' --failed id,id')}` after listening if some items failed)")
    return 0


def _review_cue(cur, prompts: Prompts, it) -> str:
    """The review question for a single item: its situation, else the meaning cue (with the item's context, like the lesson)."""
    prompts = Prompts(prompts.data, prompts.lang)  # a fresh generator: an item's cue does not depend on the ones asked before it
    return it.situation_for(0) or meaning_prompt(prompts, cur.known_lang, cur.target_lang, it.spoken_meaning, it.context)


def _review_cues(cur, prompts: Prompts, it) -> list[str]:
    """Every cue the bare item is asked with now: each situation, else the meaning cue. The bot rewords only a stored
    bare question whose prompt is none of these (it is stale), not one that is another current cue (#220)."""
    prompts = Prompts(prompts.data, prompts.lang)
    cues = list(it.situations or ([it.situation] if it.situation else []))
    cues += meaning_prompts(prompts, cur.known_lang, cur.target_lang, it.spoken_meaning, it.context)  # every template, not one
    return list(dict.fromkeys(cues))


def _plan(script: Script, cur) -> dict:
    meta = script.meta

    def describe(i: str) -> dict:
        it = cur.by_id.get(i)
        return {"id": i, "target": it.target if it else None, "meaning": it.meaning if it else None, "kind": it.kind if it else None}

    review = script.review_questions() + list(meta.get("bonus_review", []))
    # #199: an open item practised only through a cloze, a hint or a dialogue has no written question, so the review
    # could not check it; it gets one from its situation or meaning (a construction has no single answer: skipped)
    asked = {i for q in review for i in q.get("items", [])}
    prompts = Prompts.load(cur.known_lang)
    for i in list(meta.get("open_items", [])) + list(meta.get("open_not_fitted", [])):  # #220: every open item is asked, fitted or not
        it = cur.by_id.get(i)
        if i in asked or it is None or it.kind == "construction":
            continue
        asked.add(i)
        review.append({"items": [i], "prompt": _review_cue(cur, prompts, it), "answer": it.target, "stage": "open"})
    return {
        "lesson_number": script.lesson_number,
        "date": meta.get("date"),
        "config": meta.get("config"),
        "summary": script.summary(),
        "new_items": [describe(i) for i in meta.get("new_items", [])],
        "reviewed_items": [describe(i) for i in meta.get("reviewed_items", [])],
        "dialogues": meta.get("dialogues", []),
        "theme": meta.get("theme"),  # #149 1b-ii: the lesson's theme and level, and how often its exchange played
        "new_components": meta.get("new_components"),  # #218 b3: the weighted new material, forms apart, and each item's cost (None when counting items)
        "listening_asked": meta.get("listening_asked", []),  # #179: turns asked because the line can be said
        "second_half": {k: meta.get(k, 0) for k in ("pick_out_count", "catch_unknown_count", "longest_kind_run_after_target")},  # #248: the listening rotation
        "listening_tried": meta.get("listening_tried", []),  # #183: turns tried on a part (bonus questions)
        "exposures": meta.get("exposures", {}),
        "open_items": list(meta.get("open_items", [])),  # #199: the bot brings their questions forward and asks the waiting ones
        "open_not_fitted": list(meta.get("open_not_fitted", [])),
        "review": review,
        "review_candidates": script.review_candidates(),
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
    changed = learner.report(
        _split(args.failed), _split(args.easy), today, args.lesson, hesitated=_split(args.hesitated), recalled=_split(args.recalled), sooner=_split(args.sooner),
        load=args.load,
    )
    learner.save(args.learner)
    if changed["failed"]:
        print(f"marked as failed (back to an easier stage, due tomorrow, a second more to answer next time): {', '.join(changed['failed'])}")
    if changed["hesitated"]:
        print(f"marked as hesitated (back sooner, at half the interval): {', '.join(changed['hesitated'])}")
    if changed["recalled"]:
        print(f"confirmed as recalled: {', '.join(changed['recalled'])}")
    if changed["easy"]:
        print(f"marked as easy (longer interval): {', '.join(changed['easy'])}")
    if changed["sooner"]:
        print(f"coming back sooner (due within half the interval; no outcome recorded): {', '.join(changed['sooner'])}")
    if changed["sooner_skipped"]:
        print(f"left to the next-day review (embedded or tried): {', '.join(changed['sooner_skipped'])}")
    if changed["load"]:
        print(f"lesson {changed['lesson']} load recorded: {changed['load']}")
    if changed.get("load_unknown") is not None:
        print(f"warning: lesson {changed['load_unknown']} is not in the lesson log: its load ({args.load}) was not stored", file=sys.stderr)
    if changed["unknown"]:
        print(f"warning: not in learner state: {', '.join(changed['unknown'])}", file=sys.stderr)
    if not (changed["failed"] or changed["hesitated"] or changed["recalled"] or changed["easy"] or args.sooner or args.load):
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
        print(f"new-component target: {learner.new_target:g} weighted components per 30 min (a lesson of m minutes plans m/30 of it); pace: {learner.pace or 'default'} new items/lesson, which `--new` / `--pace`, the simulations and the coverage report count ({learner.feedback_mode} mode); due at start of last lessons: {trend}; not fitted: {carried}")
        unreported = [l["number"] for l in learner.lessons[-3:] if l["number"] not in learner.reported]
        if unreported and learner.feedback_mode != "auto":
            print(f"no feedback yet for lesson(s) {unreported}: run `{_learner_hint(args, ' [--failed ids]')}`")
    return 0


def _check_bin(cur, curriculum) -> list[str]:
    """Warnings (never failures: the BÍN check advises, #218 b2) about the variants against the cached lookups: the cache missing, a form not
    in it, or a variant and its base given to different words."""
    from .binform import cache_path, load_cache, variant_warnings

    if not Path(curriculum).is_dir():
        return []
    path = cache_path(curriculum)
    n = sum(1 for i in cur.items if i.variant_of)
    if not path.exists():
        return [f"{n} variant items are not checked against BÍN yet; run `python tools/bin_lookup.py --data SHsnid.csv.zip --variants` (writes {path})"] if n else []
    return variant_warnings(cur, load_cache(path))


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
    for line in _check_bin(cur, args.curriculum):
        print(f"warning: {line}", file=sys.stderr)
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
    parts = part_before_whole_report(cur)
    if parts:
        print(
            f"advisory (not a failure): {len(parts)} items are taught after a phrase that already contains them "
            f"(G13): the learner meets the part as 'something new' after the whole. Many are chunks taught first on purpose; it is a prompt for a per-case choice, not a count to bring to zero."
            + ("" if args.parts else " --parts lists them.")
        )
        if args.parts:
            for f in parts:
                print(f"  #{f['part_order']:<4} {f['part']} is inside #{f['whole_order']} {f['whole']} ({f['gap']} items earlier)")
    frames = frame_gap_report(cur, args.frame_span)
    if frames["late"] or frames["none"]:
        vocab = sum(1 for i in cur.items if i.kind == "vocab")
        print(
            f"advisory (not a failure): of {vocab} vocab items, {len(frames['none'])} are never used in a frame "
            f"or dialogue, and {len(frames['late'])} wait more than {args.frame_span} items for their first one "
            f"— drilled as bare words until then (#80)."
            + ("" if args.frames else " --frames lists them.")
        )
        if args.frames:
            for f in frames["late"]:
                print(f"  late  #{f['order']:<4} {f['item']}: first {f['context']} (#{f['context_order']}, {f['gap']} items later)")
            for f in frames["none"]:
                print(f"  none  #{f['order']:<4} {f['item']}")
    scenarios = load_cando(args.curriculum, cur) if Path(args.curriculum).is_dir() else []
    if scenarios and not args.cando:
        print(f"{len(scenarios)} travel can-do scenarios (#131); --cando reports their coverage")
    scenes = load_scenes(args.curriculum, cur, scenarios) if scenarios else []
    if scenes:
        missing = uncovered(scenes, scenarios, "A")
        if missing:
            raise CurriculumError(f"Tier A scenarios without a scenario card (#129): {missing}")
        print(f"{len(scenes)} scenario cards (#129); every Tier A scenario has one")
    themes = load_themes(args.curriculum, cur, scenarios) if scenarios else []
    if themes:
        print(f"{len(themes)} lesson themes (#149), {sum(len(t.levels) for t in themes)} levels")
    if args.cando:
        if not scenarios:
            print("no can-do scenarios (<curriculum>/cando/*.toml)")
            return 0
        try:
            paces = [int(p) for p in args.paces.split(",") if p.strip()]
        except ValueError:
            raise ValueError(f"--paces must list positive numbers of new items per lesson (got {args.paces!r})") from None
        trip = load_trip(args.trip) if args.trip else None
        if args.lessons is None:
            left = trip.days_left(date.today()) if trip else None
            args.lessons = left if left is not None else 84
        check_horizon(args.lessons, paces)
        scenarios = for_season(scenarios, trip.season if trip else None)
        priority = priority_items(cur, scenarios, trip.boost) if trip else []
        if priority:
            print(f"trip ordering: {len(priority)} can-do items first")
        reach = {pace: simulate_reach(cur, args.lessons, pace, priority=priority) for pace in paces}
        print(format_coverage(coverage(cur, scenarios, reach, args.lessons), args.lessons, paces))
    return 0


def cmd_reading(args) -> int:
    places = load_trip(args.trip).places if args.trip else []
    cards = load_deck(args.curriculum, places)
    print(json.dumps([c.to_dict() for c in cards], ensure_ascii=False))
    return 0


def cmd_questions(args) -> int:
    cur = load_curriculum(args.curriculum, known_lang=args.known)
    prompts = Prompts.load(cur.known_lang)
    out = {}
    for i in _split(args.ids):
        it = cur.by_id.get(i)
        if it is not None and it.kind != "construction":
            out[i] = {"prompt": _review_cue(cur, prompts, it), "answer": it.target, "cues": _review_cues(cur, prompts, it)}
    print(json.dumps(out, ensure_ascii=False))
    return 0


def cmd_scenes(args) -> int:
    cur = load_curriculum(args.curriculum)
    scenarios = load_cando(args.curriculum, cur)
    season = load_trip(args.trip).season if args.trip else None
    met = None
    if args.learner_file:  # not "learner": the --user wrapper would demand one
        path = Path(args.learner_file)
        learner = LearnerState.load(path) if path.exists() else None
        met = {it.id for it in cur.items if learner is not None and learner.has_met(it.id)}
    by_id = {s.id: s for s in scenarios}
    cards = available(load_scenes(args.curriculum, cur, scenarios), for_season(scenarios, season), season, met)
    out = [
        {**c.to_dict(), "tier": by_id[c.scenario].tier, "title": by_id[c.scenario].title, "title_ja": by_id[c.scenario].title_ja}
        for c in cards
    ]
    print(json.dumps(out, ensure_ascii=False))
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
