"""Render a Script to one audio file with a voice profile.

A profile says which provider and which voice per speaker; everything else
(what is said, how long each silence is) comes from the script. Synthesized
clips are cached by content hash so re-rendering with a different pause
multiplier or a fixed prompt does not re-synthesize unchanged lines.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ..script import Script
from .audio import AudioClip, concat, read_wav, silence, to_mp3, write_wav
from .tts import Provider, get_provider

# Deliberate spelling substitutions applied only to the text sent to the TTS engine,
# keyed by target language (never to instructor narration, which uses a different
# language). The curriculum, transcript, cues.json and answer-matching all keep the
# correct native spelling; only the synthesized audio hears the substitute.
#
# Icelandic geminate 'll'/'nn' in native words is pre-aspirated (a brief voiceless
# click before the l/n: fjall, gull, allt). "Halló" the greeting is a different case:
# it is a Danish loanword and, per its dictionary entry, does not take that click at
# all (IPA [ˈhal(ː)ou], plain l) — a same-spelled but unrelated slang adjective does
# ([ˈhatlou], from a native compound), which is what misled an earlier pass at this.
# Edge-tts's clicked rendering of the greeting was very likely a genuine mispronun-
# ciation, not correct Icelandic; spelling it with a single 'l' for the TTS (checked
# with `espeak-ng -v is -x`) removes it without touching anything else that word
# triggers elsewhere. See docs/HANDOFF.md session 6 (and its addendum, which corrects
# an earlier over-confident citation) for the full story; this list is the override,
# not the explanation.
RESPELL_FOR_SPEECH: dict[str, list[tuple[str, str]]] = {
    "is": [("Halló", "Haló")],
}


def _respell(text: str, lang: str) -> str:
    for find, replace in RESPELL_FOR_SPEECH.get(lang.split("-")[0].lower(), ()):
        text = text.replace(find, replace)
    return text


# Curriculum authors write "A / B" (and its Japanese fullwidth twin "A／B") to show two
# acceptable phrasings at a glance. Read aloud literally, a TTS voice says the character's
# name ("slash") instead of the word it stands for, which is what it's meant to mean in
# running speech. Fixed at the same render layer as RESPELL_FOR_SPEECH, for the same
# reason: the written curriculum, transcript and cues.json should still show the "/", only
# the audio should say the word.
NARRATION_SLASH_AS_SPOKEN: dict[str, tuple[re.Pattern[str], str]] = {
    "en": (re.compile(r"\s*/\s*"), " or "),
    "ja": (re.compile(r"／"), "または"),
}


def _speak_slashes(text: str, lang: str) -> str:
    fix = NARRATION_SLASH_AS_SPOKEN.get(lang.split("-")[0].lower())
    if fix:
        pattern, replacement = fix
        text = pattern.sub(replacement, text)
    return text


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
    workers: int = 4  # parallel synthesis requests for network providers
    fit: bool = True  # stretch/shrink pauses a little so the file lands on the requested length
    fit_min: float = 0.85  # bounds on the pause scale used for fitting
    fit_max: float = 1.25
    fit_tolerance: float = 60.0  # seconds: within this of the target, pauses are left exactly as planned

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
        prof.workers = int(raw.get("workers", 4))
        prof.fit = bool(raw.get("fit", True))
        prof.fit_min = float(raw.get("fit_min", 0.85))
        prof.fit_max = float(raw.get("fit_max", 1.25))
        prof.fit_tolerance = float(raw.get("fit_tolerance", 60.0))
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
    target_seconds: float | None = None,
) -> dict:
    """Write ``out_path`` (.wav) and, if possible, an .mp3 beside it. Returns cue metadata.

    ``target_seconds`` (default: the script's requested minutes) makes the file land on
    that length by scaling the learner pauses within ``profile.fit_min..fit_max``.
    """
    if target_seconds is None:
        minutes = (script.meta.get("config") or {}).get("minutes")
        target_seconds = float(minutes) * 60 if minutes else None
    out_path = Path(out_path)
    provider = get_provider(profile.provider)
    problem = provider.check()
    if problem:
        raise RuntimeError(f"TTS provider {provider.name!r} cannot run: {problem}")
    cache = Path(cache_dir) if cache_dir else out_path.parent / "cache" / provider.name
    cache.mkdir(parents=True, exist_ok=True)

    primary_langs = {script.known_lang.split("-")[0].lower(), script.target_lang.split("-")[0].lower()}

    def request_for(seg) -> tuple[str, str, str, float]:
        speaker = seg.speaker or "native_a"
        lang = seg.lang or (script.known_lang if speaker == "instructor" else script.target_lang)
        # A third language — neither this lesson's instructor language nor its target
        # language, e.g. a Japanese example embedded in English narration (issue #49) —
        # must not inherit whichever fixed voice the profile configured for this speaker
        # role in kl/tl. Looking the profile up under a key it was never configured for
        # (instead of the plain speaker name) makes ``voice_for`` fall through to the
        # provider's own default voice for ``lang`` automatically, with no schema change.
        profile_key = speaker if lang.split("-")[0].lower() in primary_langs else f"{speaker}:{lang}"
        sv = profile.voice_for(profile_key, lang, provider, _DEFAULT_INDEX.get(speaker, 0))
        # ``speech_text``, when set, is what the provider actually hears — e.g. native
        # orthography for a romanized transcript display (issue #49, PR #51 owner review):
        # pronunciation must not depend on the provider being able to read transliterated
        # text itself, since some providers (e.g. OpenAIProvider) don't even use ``lang``
        # to disambiguate it — they just read whatever text they're given.
        spoken = seg.speech_text or seg.text or ""
        return (_speak_slashes(_respell(spoken, lang), lang), lang, sv.voice, seg.rate * sv.rate)

    # warm the cache in parallel for providers that talk to a network
    unique = {request_for(seg) for seg in script.segments if seg.type != "pause"}
    todo = [r for r in unique if not _cache_path(provider, cache, *r, profile.trim).exists()]
    if todo and provider.parallel and profile.workers > 1:
        with ThreadPoolExecutor(max_workers=profile.workers) as pool:
            for i, _ in enumerate(pool.map(lambda r: _cached(provider, cache, *r, profile.trim), todo), 1):
                if progress and (i % 10 == 0 or i == len(todo)):
                    print(f"  synthesized {i}/{len(todo)} new lines", file=sys.stderr, end="\r")

    # 1. speech clips (pauses are placeholders until we know the speech length)
    clips: list[AudioClip | None] = []
    total = sum(1 for s in script.segments if s.type != "pause")
    done = 0
    est: dict[str, float] = {}
    meas: dict[str, float] = {}
    for seg in script.segments:
        if seg.type == "pause":
            clips.append(None)
            continue
        clip = _cached(provider, cache, *request_for(seg), profile.trim)
        clips.append(clip)
        lang = request_for(seg)[1].split("-")[0].lower()
        est[lang] = est.get(lang, 0.0) + seg.duration
        meas[lang] = meas.get(lang, 0.0) + clip.seconds
        done += 1
        if progress and not todo and (done % 10 == 0 or done == total):
            print(f"  synthesized {done}/{total}", file=sys.stderr, end="\r")
    if progress:
        print(file=sys.stderr)
    calibration = {lang: round(meas[lang] / est[lang], 3) for lang in est if est[lang] > 0}

    # 2. pauses: the script's lengths × profile multiplier, then a small uniform scale to hit the target
    speech_total = sum(c.seconds for c in clips if c is not None)
    pause_base = []
    for seg in script.segments:
        if seg.type == "pause":
            pause_base.append(seg.duration * (profile.pause_multiplier if seg.role in ("answer", "repeat") else 1.0))
    pause_total = sum(pause_base)
    fit_scale = 1.0
    if profile.fit and target_seconds and pause_total > 0:
        delta = target_seconds - (speech_total + pause_total)
        if abs(delta) > profile.fit_tolerance:
            # aim for the nearest edge of the tolerance band, not the exact target: pauses stay
            # as close as possible to what the timing model asked for
            aim = target_seconds - profile.fit_tolerance if delta > 0 else target_seconds + profile.fit_tolerance
            fit_scale = max(profile.fit_min, min(profile.fit_max, (aim - speech_total) / pause_total))
    fitted = iter(pause_base)
    cues: list[dict] = []
    final: list[AudioClip] = []
    t = 0.0
    ex_start: dict[int, float] = {}
    for seg, clip in zip(script.segments, clips):
        if clip is None:
            clip = silence(next(fitted) * fit_scale)
        if seg.exercise is not None and seg.exercise not in ex_start:
            ex_start[seg.exercise] = t
        cues.append({"t": round(t, 2), "type": seg.type, "speaker": seg.speaker, "text": seg.text, "role": seg.role, "dur": round(clip.seconds, 2)})
        final.append(clip)
        t += clip.seconds

    mix = concat(final)
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
        "target_s": target_seconds,
        "fit_scale": round(fit_scale, 3),
        "speech_s": round(speech_total, 1),
        "calibration": calibration,
        "exercises": [
            {"index": ex.index, "label": ex.label, "kind": ex.kind, "start": round(ex_start.get(ex.index, 0.0), 2)}
            for ex in script.exercises
        ],
        "segments": cues,
    }


def _cache_path(provider: Provider, cache: Path, text: str, lang: str, voice: str, rate: float, trim: bool) -> Path:
    key = hashlib.sha1(f"{provider.name}|{voice}|{rate:.3f}|{lang}|{trim}|{text}".encode()).hexdigest()
    return cache / f"{key}.wav"


def _cached(provider: Provider, cache: Path, text: str, lang: str, voice: str, rate: float, trim: bool) -> AudioClip:
    path = _cache_path(provider, cache, text, lang, voice, rate, trim)
    if path.exists():
        return read_wav(path)
    clip = provider.synthesize(text, lang, voice, rate)
    if trim:
        clip = clip.trimmed()
    write_wav(clip, path)
    return clip


def save_cues(cues: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding="utf-8")
