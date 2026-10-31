"""List the cached speech clips that look cut off (#462): for each line the given scripts say, its clip in the TTS cache, its length
against the script's estimate, shortest first. A clip `looks_cut_off` flags is marked; the others show the spread the threshold sits in.
Nothing is changed: a cut-off clip is renamed by hand (`mv X.wav X.wav.bad`) and the next render synthesizes it again.

    python tools/cut_off_clips.py --cache DIR [--profile profiles/edge-is-en.toml] [--top 20] SCRIPT.json [SCRIPT.json ...]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audiolesson.render.audio import read_wav  # noqa: E402
from audiolesson.render.renderer import _TIMING, _cache_path, cut_off_threshold, load_profile, looks_cut_off, speech_request  # noqa: E402
from audiolesson.render.tts import get_provider  # noqa: E402
from audiolesson.script import Script  # noqa: E402


def rows(scripts: list[Path], cache: Path, profile_path: str | None) -> list[dict]:
    profile = load_profile(profile_path)
    provider = get_provider(profile.provider)
    seen: dict[Path, dict] = {}
    for path in scripts:
        script = Script.load(path)
        for seg in script.segments:
            if seg.type == "pause":
                continue
            text, lang, voice, rate = speech_request(script, seg, profile, provider)
            clip_path = _cache_path(provider, cache, text, lang, voice, rate, profile.trim)
            if clip_path in seen or not clip_path.exists():
                continue
            clip = read_wav(clip_path)
            estimate = _TIMING.speech_estimate(text, lang, rate)
            seen[clip_path] = {"file": clip_path.name, "text": text, "lang": lang, "seconds": round(clip.seconds, 2), "estimate": estimate,
                               "ratio": round(clip.seconds / estimate, 2) if estimate else 0.0, "cut_off": looks_cut_off(clip, text, lang, rate)}
    return sorted(seen.values(), key=lambda r: r["ratio"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scripts", nargs="+", type=Path)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--profile", default=str(Path(__file__).resolve().parent.parent / "profiles" / "edge-is-en.toml"))
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args(argv)
    found = rows(args.scripts, args.cache, args.profile)
    flagged = [r for r in found if r["cut_off"]]
    print(f"{len(found)} cached clips read; {len(flagged)} look cut off")
    # the spread per language, against the threshold: a cut-off clip sits apart below it, a whole one inside the spread
    for lang in sorted({r["lang"] for r in found}):
        ratios = sorted(r["ratio"] for r in found if r["lang"] == lang)
        print(f"  {lang}: {len(ratios)} clips, ratio min {ratios[0]:.2f}, median {ratios[len(ratios) // 2]:.2f}; cut off under {cut_off_threshold(lang):.2f}")
    # every flagged clip first, then the shortest of the others up to --top: a word of one or two words (never flagged) can be shorter
    # against its estimate than a cut-off line, and must not push it off the list (review of #466)
    others = [r for r in found if not r["cut_off"]]
    for r in flagged + others[: max(0, args.top - len(flagged))]:
        print(f"{'CUT ' if r['cut_off'] else '    '}{r['ratio']:.2f}  {r['seconds']:.2f}s/{r['estimate']:.2f}s  {r['lang']}  {r['file']}  {r['text']}")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
