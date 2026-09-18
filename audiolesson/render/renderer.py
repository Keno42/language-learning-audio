"""Render a Script to one audio file with a voice profile.

A profile says which provider and which voice per speaker; everything else
(what is said, how long each silence is) comes from the script. Synthesized
clips are cached by content hash so re-rendering with a different pause
multiplier or a fixed prompt does not re-synthesize unchanged lines.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from ..script import Script
from .audio import AudioClip, concat, read_wav, silence, to_mp3, write_wav
from .tts import Provider, get_provider


@dataclass
class SpeakerVoice:
    voice: str = ""
    rate: float = 1.0  # multiplier on top of the script's per-segment rate


@dataclass
class VoiceProfile:
    provider: str = "stub"
    speakers: dict[str, SpeakerVoice] = field(default_factory=dict)
    pause_multiplier: float = 1.0  # scale every learner pause at render time
    mp3: bool = True
    trim: bool = True

    def voice_for(self, speaker: str, lang: str, provider: Provider, idx_hint: int) -> SpeakerVoice:
        sv = self.speakers.get(speaker)
        if sv and sv.voice:
            return sv
        defaults = provider.default_voices(lang)
        if not defaults:
            raise ValueError(f"profile has no voice for speaker {speaker!r} and provider {provider.name!r} has no default for language {lang!r}")
        voice = defaults[min(idx_hint, len(defaults) - 1)]
        return SpeakerVoice(voice=voice, rate=sv.rate if sv else 1.0)


def load_profile(path: str | Path | None, provider: str | None = None) -> VoiceProfile:
    prof = VoiceProfile()
    if path:
        with Path(path).open("rb") as fh:
            raw = tomllib.load(fh)
        prof.provider = raw.get("provider", prof.provider)
        prof.pause_multiplier = float(raw.get("pause_multiplier", 1.0))
        prof.mp3 = bool(raw.get("mp3", True))
        prof.trim = bool(raw.get("trim", True))
        for name, spec in raw.get("speakers", {}).items():
            if isinstance(spec, str):
                prof.speakers[name] = SpeakerVoice(voice=spec)
            else:
                prof.speakers[name] = SpeakerVoice(voice=spec.get("voice", ""), rate=float(spec.get("rate", 1.0)))
    if provider:
        prof.provider = provider
    return prof


# speaker → which default voice index to use (A and B should differ)
_DEFAULT_INDEX = {"instructor": 0, "native_a": 0, "native_b": 1}


def render_script(
    script: Script,
    profile: VoiceProfile,
    out_path: str | Path,
    cache_dir: str | Path | None = None,
    *,
    progress: bool = True,
) -> dict:
    """Write ``out_path`` (.wav) and, if possible, an .mp3 beside it. Returns cue metadata."""
    out_path = Path(out_path)
    provider = get_provider(profile.provider)
    problem = provider.check()
    if problem:
        raise RuntimeError(f"TTS provider {provider.name!r} cannot run: {problem}")
    cache = Path(cache_dir) if cache_dir else out_path.parent / "cache" / provider.name
    cache.mkdir(parents=True, exist_ok=True)

    clips: list[AudioClip] = []
    cues: list[dict] = []
    t = 0.0
    total = sum(1 for s in script.segments if s.type != "pause")
    done = 0
    ex_start: dict[int, float] = {}
    for seg in script.segments:
        if seg.type == "pause":
            secs = seg.duration * (profile.pause_multiplier if seg.role in ("answer", "repeat") else 1.0)
            clip = silence(secs)
        else:
            lang = seg.lang or (script.known_lang if seg.speaker == "instructor" else script.target_lang)
            sv = profile.voice_for(seg.speaker or "native_a", lang, provider, _DEFAULT_INDEX.get(seg.speaker or "", 0))
            rate = seg.rate * sv.rate
            clip = _cached(provider, cache, seg.text or "", lang, sv.voice, rate, profile.trim)
            done += 1
            if progress and (done % 10 == 0 or done == total):
                print(f"  synthesized {done}/{total}", file=sys.stderr, end="\r")
        if seg.exercise is not None and seg.exercise not in ex_start:
            ex_start[seg.exercise] = t
        cues.append({"t": round(t, 2), "type": seg.type, "speaker": seg.speaker, "text": seg.text, "role": seg.role, "dur": round(clip.seconds, 2)})
        clips.append(clip)
        t += clip.seconds
    if progress:
        print(file=sys.stderr)

    mix = concat(clips)
    write_wav(mix, out_path)
    mp3_path = None
    if profile.mp3:
        candidate = out_path.with_suffix(".mp3")
        if to_mp3(out_path, candidate):
            mp3_path = str(candidate)
    return {
        "wav": str(out_path),
        "mp3": mp3_path,
        "duration_s": round(mix.seconds, 1),
        "provider": provider.name,
        "exercises": [
            {"index": ex.index, "label": ex.label, "kind": ex.kind, "start": round(ex_start.get(ex.index, 0.0), 2)}
            for ex in script.exercises
        ],
        "segments": cues,
    }


def _cached(provider: Provider, cache: Path, text: str, lang: str, voice: str, rate: float, trim: bool) -> AudioClip:
    key = hashlib.sha1(f"{provider.name}|{voice}|{rate:.3f}|{lang}|{trim}|{text}".encode()).hexdigest()
    path = cache / f"{key}.wav"
    if path.exists():
        return read_wav(path)
    clip = provider.synthesize(text, lang, voice, rate)
    if trim:
        clip = clip.trimmed()
    write_wav(clip, path)
    return clip


def save_cues(cues: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding="utf-8")
