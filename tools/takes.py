#!/usr/bin/env python3
"""Write takes of instruction lines to listen to, before naming one in a profile's ``retake`` (#563).

    python tools/takes.py --profile profiles/edge-is-en.toml --takes 3 --out takes/ "Samtalinu er lokið." ["Aftur að tala." …]

The lines are said by the ``command`` speaker's own provider (OpenAI's realtime voice in the Icelandic profiles), as a lesson says them,
``--takes`` times each, written as ``<n>. <line> take<k>.wav`` in ``--out``. Nothing is cached: listen, choose, then name the line and its
take in the profile, e.g. ``command = { provider = "openai-realtime", voice = "cedar", retake = { "Samtalinu er lokið." = 1 } }``; the next
render says it anew under that take's own cache key. A take number names a new clip, not one of these files: what the next render
synthesizes is heard in the lesson, and a take that sounds off there is replaced by naming the next number.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audiolesson.render.audio import write_wav  # noqa: E402
from audiolesson.render.renderer import load_profile  # noqa: E402
from audiolesson.render.tts import get_provider  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lines", nargs="+")
    ap.add_argument("--profile", default=str(Path(__file__).resolve().parent.parent / "profiles" / "edge-is-en.toml"))
    ap.add_argument("--speaker", default="command")
    ap.add_argument("--takes", type=int, default=3)
    ap.add_argument("--lang", default="is-IS")
    ap.add_argument("--out", type=Path, default=Path("takes"))
    args = ap.parse_args(argv)
    profile = load_profile(args.profile)
    sv = profile.speakers.get(args.speaker)
    if sv is None or not sv.provider:
        print(f"the profile gives {args.speaker!r} no provider of its own", file=sys.stderr)
        return 2
    provider = get_provider(sv.provider)
    if (why := provider.check()) is not None:
        print(f"{sv.provider} cannot run: {why}", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    for n, line in enumerate(args.lines, 1):
        stem = re.sub(r"[^\w .,?!-]", "", line).strip()
        for k in range(1, args.takes + 1):
            clip = provider.synthesize(line, args.lang, sv.voice, sv.rate)
            path = args.out / f"{n}. {stem} take{k}.wav"
            write_wav(clip.trimmed() if profile.trim else clip, path)
            print(f"{path}  {clip.seconds:.2f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
