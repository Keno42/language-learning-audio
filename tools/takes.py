#!/usr/bin/env python3
"""Make takes of an instruction line to listen to, and install the one chosen as the take a profile's ``retake`` names (#563).

    python tools/takes.py --takes 3 --out takes/ "Samtalinu er lokið." ["Aftur að tala." …]
    python tools/takes.py --install "takes/1. Samtalinu er lokið. take2.wav" --take 1 --cache CACHE_DIR "Samtalinu er lokið."

The lines are said by the ``command`` speaker's own provider (OpenAI's realtime voice in the Icelandic profiles), as a lesson asks for them
(``renderer.speech_request``), ``--takes`` times each, written as ``<n>. <line> take<k>.wav`` in ``--out``. Nothing is cached by that step.

``--install`` puts the clip chosen by ear into the render's cache, under the key of take ``--take`` of that line: the clip heard is the clip the
lesson plays (review of #597: naming a take number alone made the renderer synthesize a fresh clip, whose tone may differ from the one chosen).
It is checked as a rendered clip is: not cut off (``looks_cut_off``), and not far shorter than the profile's voice's clip of the line when that
is cached (``OWN_VOICE_MIN_SHARE``); a clip that fails is not installed. Then name the line and its take in the profile, e.g.
``command = { provider = "openai-realtime", voice = "cedar", retake = { "Samtalinu er lokið." = 1 } }``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audiolesson.render.audio import read_wav, write_wav  # noqa: E402
from audiolesson.render.renderer import OWN_VOICE_MIN_SHARE, _cache_path, load_profile, looks_cut_off, speech_request  # noqa: E402
from audiolesson.render.tts import get_provider  # noqa: E402
from audiolesson.script import Script, Segment  # noqa: E402


def requests(profile, speaker: str, line: str, lang: str, known: str):
    """The line as a lesson asks the speaker's own provider for it, and as the profile's voice says it (the length check's reference)."""
    sv = profile.speakers[speaker]
    script = Script(1, "takes", lang.split("-")[0], known)
    seg = Segment("speak", speaker, line, lang.split("-")[0], 1.0, 1.0)
    base = get_provider(profile.provider)
    text, req_lang, voice, rate = speech_request(script, seg, profile, base)
    return base, (text, req_lang, voice, rate), (text, req_lang, sv.voice, seg.rate * sv.rate)


def install(args, profile, sv) -> int:
    if len(args.lines) != 1 or args.take < 1 or args.cache is None:
        print("--install takes one line, --take 1 or more, and --cache", file=sys.stderr)
        return 2
    own = get_provider(sv.provider)
    base, ref_req, (text, lang, voice, rate) = requests(profile, args.speaker, args.lines[0], args.lang, args.known)
    clip = read_wav(args.install)
    if profile.trim:
        clip = clip.trimmed()
    if looks_cut_off(clip, text, lang, rate):
        print(f"not installed: {args.install} looks cut off ({clip.seconds:.2f} s)", file=sys.stderr)
        return 1
    ref_path = _cache_path(base, args.cache, *ref_req, profile.trim)
    if ref_path.exists() and clip.seconds < OWN_VOICE_MIN_SHARE * (ref := read_wav(ref_path).seconds):
        print(f"not installed: {clip.seconds:.2f} s against the profile's voice's {ref:.2f} s (under {OWN_VOICE_MIN_SHARE})", file=sys.stderr)
        return 1
    path = _cache_path(own, args.cache, text, lang, voice, rate, profile.trim, args.take)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_wav(clip, path)
    print(f"installed as take {args.take} of {text!r}: {path}")
    print(f'name it in the profile: retake = {{ "{text}" = {args.take} }}')
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lines", nargs="+")
    ap.add_argument("--profile", default=str(Path(__file__).resolve().parent.parent / "profiles" / "edge-is-en.toml"))
    ap.add_argument("--speaker", default="command")
    ap.add_argument("--lang", default="is")
    ap.add_argument("--known", default="en")
    ap.add_argument("--takes", type=int, default=3)
    ap.add_argument("--out", type=Path, default=Path("takes"))
    ap.add_argument("--install", type=Path, help="a take chosen by ear, to install into --cache as take --take of the line")
    ap.add_argument("--take", type=int, default=0)
    ap.add_argument("--cache", type=Path, help="the render's cache directory (cache/edge under the lessons' output)")
    args = ap.parse_args(argv)
    profile = load_profile(args.profile)
    sv = profile.speakers.get(args.speaker)
    if sv is None or not sv.provider:
        print(f"the profile gives {args.speaker!r} no provider of its own", file=sys.stderr)
        return 2
    if args.install is not None:
        return install(args, profile, sv)
    provider = get_provider(sv.provider)
    if (why := provider.check()) is not None:
        print(f"{sv.provider} cannot run: {why}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    for n, line in enumerate(args.lines, 1):
        _, _, (text, lang, voice, rate) = requests(profile, args.speaker, line, args.lang, args.known)
        stem = re.sub(r"[^\w .,?!-]", "", line).strip()
        for k in range(1, args.takes + 1):
            clip = provider.synthesize(text, lang, voice, rate)
            path = args.out / f"{n}. {stem} take{k}.wav"
            write_wav(clip.trimmed() if profile.trim else clip, path)
            print(f"{path}  {clip.seconds:.2f} s")
    print("listen, then install the one you choose: --install FILE --take N --cache CACHE_DIR \"<line>\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
