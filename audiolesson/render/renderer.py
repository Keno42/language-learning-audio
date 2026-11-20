"""Render a Script to one audio file with a voice profile.

A profile says which provider and which voice per speaker; everything else
(what is said, how long each silence is) comes from the script. Synthesized
clips are cached by content hash so re-rendering with a different pause
multiplier or a fixed prompt does not re-synthesize unchanged lines.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import tomllib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ..script import Script
from ..timing import Timing
from .audio import AudioClip, concat, loudness, read_wav, scaled, silence, to_mp3, write_wav
from .tts import Provider, cache_family, get_provider

# Spelling substitutions applied only to target-language text sent to the TTS engine; the
# curriculum, transcript and cues keep the real spelling. "Halló" the greeting is a loanword
# with a plain l ([ˈhal(ː)ou]), but TTS pre-aspirates the native geminate ([ˈhatlou]).
RESPELL_FOR_SPEECH: dict[str, list[tuple[str, str]]] = {
    "is": [("Halló", "Haló")],
}


def _respell(text: str, lang: str) -> str:
    for find, replace in RESPELL_FOR_SPEECH.get(lang.split("-")[0].lower(), ()):
        text = text.replace(find, replace)
    return text


# "A / B" (or "A／B") in narration is spoken as "A or B", not "A slash B"; text keeps the slash.
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


_TILDE = re.compile(r"[〜～]")


def _speak_tildes(text: str, lang: str) -> str:
    """Written Japanese marks a slot with 〜 («〜したい»), which TTS may read as «から».
    Between numbers («3〜4週間») it does mean «から», so it stays there; the text keeps it."""
    if lang.split("-")[0].lower() != "ja":
        return text

    def keep_between_numbers(m: re.Match[str]) -> str:
        before, after = text[m.start() - 1 : m.start()], text[m.end() : m.end() + 1]
        return m.group(0) if before.isdigit() and after.isdigit() else ""

    return _TILDE.sub(keep_between_numbers, text)


@dataclass
class SpeakerVoice:
    voice: str = ""
    rate: float = 1.0  # multiplier on top of the script's per-segment rate
    # a provider of the speaker's own, other than the profile's (#563: the instructions in the target language in a voice no scene uses,
    # «command = { provider = "openai-realtime", voice = "cedar" }»); "" for the profile's
    provider: str = ""


# #563: a speaker a profile may leave out, and the speaker whose voice it then takes: the instructions said in the target language
# («Endurtaktu.») are the ``command`` speaker's, voiced as the male native voice when the profile gives it none, as before
STANDS_IN = {"command": "native_b"}


@dataclass
class VoiceProfile:
    provider: str = "stub"
    speakers: dict[str, SpeakerVoice] = field(default_factory=dict)
    pause_multiplier: float = 1.0  # scale every learner pause at render time
    mp3: bool = True
    trim: bool = True
    workers: int = 4  # parallel synthesis requests for network providers
    fallback: str = ""  # a provider with the same voices to move the remaining clips to when the speech service refuses (403), e.g. "azure" (#299)
    refusal_budget_min: float = 15.0  # how long the speech service may refuse the connection (403) before the render fails (#296)
    fit: bool = True  # shrink pauses a little so a long file lands on the requested length
    fit_min: float = 0.85  # bounds on the pause scale used for fitting
    # 1.0: never stretch. Longer pauses don't make a short lesson any better, they only pad it
    # (owner, lesson 12 feedback); a profile may still allow it
    fit_max: float = 1.0
    fit_tolerance: float = 60.0  # seconds: within this of the target, pauses are left exactly as planned

    def voice_for(self, speaker: str, lang: str, provider: Provider, idx_hint: int) -> SpeakerVoice:
        sv = self.speakers.get(speaker)
        if sv and sv.voice and not sv.provider:
            return sv
        if speaker in STANDS_IN:  # not voiced by the profile's provider: the voice of the speaker it stands in for
            return self.voice_for(STANDS_IN[speaker], lang, provider, _DEFAULT_INDEX.get(STANDS_IN[speaker], idx_hint))
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
        prof.refusal_budget_min = float(raw.get("refusal_budget_min", 15.0))
        prof.fallback = str(raw.get("fallback", ""))
        prof.fit = bool(raw.get("fit", True))
        prof.fit_min = float(raw.get("fit_min", 0.85))
        prof.fit_max = float(raw.get("fit_max", 1.0))
        prof.fit_tolerance = float(raw.get("fit_tolerance", 60.0))
        for name, spec in raw.get("speakers", {}).items():
            if isinstance(spec, str):
                prof.speakers[name] = SpeakerVoice(voice=spec)
            else:
                prof.speakers[name] = SpeakerVoice(voice=spec.get("voice", ""), rate=float(spec.get("rate", 1.0)), provider=str(spec.get("provider", "")))
    if provider:
        prof.provider = provider
    return prof


# speaker → which default voice index to use (A and B should differ)
_DEFAULT_INDEX = {"instructor": 0, "native_a": 0, "native_b": 1}


def speech_request(script: Script, seg, profile: VoiceProfile, provider: Provider) -> tuple[str, str, str, float]:
    """``(text, lang, voice, rate)`` a speech segment is synthesized from, and cached under: the text as the engine hears it."""
    primary_langs = {script.known_lang.split("-")[0].lower(), script.target_lang.split("-")[0].lower()}
    speaker = seg.speaker or "native_a"
    lang = seg.lang or (script.known_lang if speaker == "instructor" else script.target_lang)
    # a third language (a Japanese example in English narration) must not inherit the
    # speaker's configured voice: an unconfigured key falls through to the provider's
    # default voice for ``lang``
    profile_key = speaker if lang.split("-")[0].lower() in primary_langs else f"{speaker}:{lang}"
    sv = profile.voice_for(profile_key, lang, provider, _DEFAULT_INDEX.get(speaker, 0))
    spoken = seg.speech_text or seg.text or ""
    return (_speak_tildes(_speak_slashes(_respell(spoken, lang), lang), lang), lang, sv.voice, seg.rate * sv.rate)


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
    that length by scaling the learner pauses within ``profile.fit_min..fit_max``; by
    default pauses only shrink, so a short lesson stays short.
    """
    if target_seconds is None:
        minutes = (script.meta.get("config") or {}).get("minutes")
        target_seconds = float(minutes) * 60 if minutes else None
    out_path = Path(out_path)
    provider = get_provider(profile.provider)
    if hasattr(provider, "refusal_budget_min"):
        provider.refusal_budget_min = profile.refusal_budget_min
    if profile.fallback and hasattr(provider, "fallback") and profile.fallback != provider.name:
        backup = get_provider(profile.fallback)
        if (why := backup.check()) is None:
            provider.fallback = backup  # type: ignore[attr-defined]
        else:
            print(f"fallback {profile.fallback!r} cannot run ({why}); the wait for the speech service stays", file=sys.stderr, flush=True)
    problem = provider.check()
    if problem:
        raise RuntimeError(f"TTS provider {provider.name!r} cannot run: {problem}")
    cache = Path(cache_dir) if cache_dir else out_path.parent / "cache" / cache_family(provider)
    cache.mkdir(parents=True, exist_ok=True)

    def request_for(seg) -> tuple[str, str, str, float]:
        return speech_request(script, seg, profile, provider)

    # #563: a speaker with a provider of its own (the instructions' voice), when that provider can run; otherwise, and for a line it fails
    # to say as written, the speaker is said in the profile's voice for the speaker it stands in for (``STANDS_IN``)
    own: dict[str, Provider] = {}
    for name, sv in profile.speakers.items():
        if sv.provider and sv.provider != provider.name:
            other = get_provider(sv.provider)
            if (why := other.check()) is None:
                own[name] = other
            else:
                print(f"speaker {name!r}: provider {sv.provider!r} cannot run ({why}); said in the profile's voice", file=sys.stderr, flush=True)
    failed: set[tuple] = set()  # own-provider requests that failed in this render: said in the profile's voice
    lock = threading.Lock()

    def route(seg) -> tuple[Provider, tuple[str, str, str, float]]:
        """The provider and request a speech segment is said by."""
        req = request_for(seg)
        speaker = seg.speaker or "native_a"
        if speaker in own:
            sv = profile.speakers[speaker]
            mine = (req[0], req[1], sv.voice, seg.rate * sv.rate)
            if (own[speaker].name, *mine) not in failed:
                return own[speaker], mine
        return provider, req

    def clip_for(seg) -> tuple[AudioClip, bool]:
        """The segment's clip, and whether a speaker's own provider said it (its loudness is then matched to the lesson's)."""
        prov, req = route(seg)
        if prov is provider:
            return _cached(provider, cache, *req, profile.trim, held), False
        try:
            return _cached(prov, cache, *req, profile.trim, held), True
        except Exception as e:  # noqa: BLE001: a lesson is never lost to the instructions' voice
            with lock:
                failed.add((prov.name, *req))
            print(f"warning: {prov.name} could not say {req[0]!r} ({e}); said in the profile's voice", file=sys.stderr, flush=True)
            return _cached(provider, cache, *request_for(seg), profile.trim, held), False

    held: dict[Path, AudioClip] = {}  # clips this render keeps out of the cache (``_cached``)
    # warm the cache in parallel for providers that talk to a network
    firsts: dict[tuple, object] = {}
    for seg in script.segments:
        if seg.type != "pause":
            prov, req = route(seg)
            firsts.setdefault((prov.name, *req), seg)
    todo = [seg for (name, *req), seg in firsts.items()
            if not _cache_path(own_or(provider, own, name), cache, *req, profile.trim).exists()]
    if todo and provider.parallel and profile.workers > 1:
        with ThreadPoolExecutor(max_workers=profile.workers) as pool:
            for i, _ in enumerate(pool.map(clip_for, todo), 1):
                if progress and (i % 10 == 0 or i == len(todo)):
                    print(f"  synthesized {i}/{len(todo)} new lines", file=sys.stderr, end="\r")

    # 1. speech clips (pauses are placeholders until we know the speech length)
    clips: list[AudioClip | None] = []
    total = sum(1 for s in script.segments if s.type != "pause")
    done = 0
    est: dict[str, float] = {}
    meas: dict[str, float] = {}
    from_own: list[int] = []  # the clips a speaker's own provider said
    for seg in script.segments:
        if seg.type == "pause":
            clips.append(None)
            continue
        clip, mine = clip_for(seg)
        if mine:
            from_own.append(len(clips))
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
    if from_own:
        clips = match_loudness(script, clips, from_own)

    # 2. pauses: the script's lengths × profile multiplier, then a small uniform scale to hit the target
    speech_total = sum(c.seconds for c in clips if c is not None)
    pause_base = []
    # shrinking to fit never takes a pause below the floor the timing model gave it (issue
    # #106: 2.5 s for unsupported recall, 1.5 s for hinted/cloze and repetition, or whatever
    # the Timing in use set); the floor never exceeds the pause itself. 0 = no floor
    pause_floor = []
    for seg in script.segments:
        if seg.type == "pause":
            secs = seg.duration * (profile.pause_multiplier if seg.role in ("answer", "repeat") else 1.0)
            pause_base.append(secs)
            pause_floor.append(min(secs, seg.floor) if seg.floor else 0.0)

    def scaled(secs: float, floor: float, scale: float) -> float:
        return max(secs * scale, floor) if scale < 1 else secs * scale

    pause_total = sum(pause_base)
    fit_scale = 1.0
    if profile.fit and target_seconds and pause_total > 0:
        delta = target_seconds - (speech_total + pause_total)
        if abs(delta) > profile.fit_tolerance:
            # aim for the nearest edge of the tolerance band, not the exact target: pauses stay
            # as close as possible to what the timing model asked for
            aim = target_seconds - profile.fit_tolerance if delta > 0 else target_seconds + profile.fit_tolerance
            fit_scale = (aim - speech_total) / pause_total
            if fit_scale < 1:
                # pauses held at their floor don't shrink: the others make up for them
                for _ in range(5):
                    held = [(b, f) for b, f in zip(pause_base, pause_floor) if b * fit_scale < f]
                    free = pause_total - sum(b for b, _ in held)
                    if free <= 0:
                        break
                    fit_scale = (aim - speech_total - sum(f for _, f in held)) / free
            fit_scale = max(profile.fit_min, min(profile.fit_max, fit_scale))
    fitted = iter(zip(pause_base, pause_floor))
    cues: list[dict] = []
    final: list[AudioClip] = []
    t = 0.0
    ex_start: dict[int, float] = {}
    for seg, clip in zip(script.segments, clips):
        if clip is None:
            clip = silence(scaled(*next(fitted), fit_scale))
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


def own_or(provider: Provider, own: dict[str, Provider], name: str) -> Provider:
    """The provider called ``name``: the profile's, or a speaker's own."""
    return next((p for p in own.values() if p.name == name), provider)


# #563 (the owner, 2026-11-20: «not sure if the volume matches the other parts»): a voice from another provider is brought to the level of
# the lesson's native voices, the median of up to ``LOUDNESS_SAMPLE`` of their clips, so an instruction is neither louder nor softer than
# the lines around it
LOUDNESS_SAMPLE = 40


def match_loudness(script: Script, clips: list, from_own: list[int]) -> list:
    """``clips`` with each clip at an index of ``from_own`` scaled to the median loudness of the native voices' clips."""
    natives = [c for c, seg in zip(clips, script.segments) if c is not None and seg.speaker in ("native_a", "native_b")]
    step = max(1, len(natives) // LOUDNESS_SAMPLE)
    levels = sorted(x for x in (loudness(c) for c in natives[::step]) if x > 0)
    if not levels:
        return clips
    target = levels[len(levels) // 2]
    out = list(clips)
    memo: dict[int, AudioClip] = {}
    for k in from_own:
        clip = out[k]
        if id(clip) not in memo:
            level = loudness(clip)
            memo[id(clip)] = scaled(clip, target / level) if level > 0 else clip
        out[k] = memo[id(clip)]
    return out


def _cache_path(provider: Provider, cache: Path, text: str, lang: str, voice: str, rate: float, trim: bool) -> Path:
    key = hashlib.sha1(f"{cache_family(provider)}|{voice}|{rate:.3f}|{lang}|{trim}|{text}".encode()).hexdigest()
    return cache / f"{key}.wav"


# #462 (lesson 43): the speech service can end a clip's stream early without an error. «Ask where she lives.» was cached as a valid WAV of
# 0.57 s, about half the sentence, and played cut off three times in the lesson. A clip of a line of several words far shorter than its
# language usually takes against the script's estimate is taken as cut off: synthesized once more, and not cached while it stays short.
# Only for a provider that calls a service (``parallel``): a local engine's short clip is its own speech. A line of one or two words is
# left out, where the estimate's floor dominates.
# The share is per language (review of the first threshold, a flat 0.4 of the estimate): the server's cache of 351 clips had its Icelandic
# lines from 0.35 of their estimate up, a continuous spread with no gap, so 0.4 flagged seven whole clips. ``TYPICAL_SHARE`` is what the
# voices take on average (the learner's speech calibration, 2026-11-01); a clip under ``CUT_OFF_SHARE`` of that is cut off: Icelandic under
# 0.26 of the estimate, English under 0.33 («Ask where she lives.» was at 0.29).
TYPICAL_SHARE = {"is": 0.57, "en": 0.74, "ja": 0.72}
TYPICAL_SHARE_DEFAULT = 0.65
CUT_OFF_SHARE = 0.45
CUT_OFF_MIN_WORDS = 3
# Lesson 51: the syllable «lin» of vett · lin · ga was cached as 0.06 s, the 60 ms either side that ``AudioClip.trimmed`` keeps around a clip
# with no sample above its threshold: the service had answered silence. A line of one or two words was left out of the check above, so it
# was cached and played as nothing. A clip shorter than ``SILENT_CLIP_S`` holds no speech, whatever its words: it is cut off too.
SILENT_CLIP_S = 0.15
_TIMING = Timing()


def cut_off_threshold(lang: str) -> float:
    """The share of the script's estimate under which a clip in ``lang`` looks cut off."""
    return CUT_OFF_SHARE * TYPICAL_SHARE.get(lang.split("-")[0].lower(), TYPICAL_SHARE_DEFAULT)


def looks_cut_off(clip: AudioClip, text: str, lang: str, rate: float = 1.0) -> bool:
    """Whether ``clip`` is far too short for ``text``: shorter than ``SILENT_CLIP_S`` (no speech in it, a line of any length), or a line of
    ``CUT_OFF_MIN_WORDS`` words or more that lasts less than ``cut_off_threshold(lang)`` of the script's estimate (``Timing.speech_estimate``
    at no calibration)."""
    words = len(re.findall(r"[^\W\d_]+", text))
    if words and clip.seconds < SILENT_CLIP_S:
        return True
    if words < CUT_OFF_MIN_WORDS:
        return False
    return clip.seconds < cut_off_threshold(lang) * _TIMING.speech_estimate(text, lang, rate)


def _cached(provider: Provider, cache: Path, text: str, lang: str, voice: str, rate: float, trim: bool, held: dict[Path, AudioClip] | None = None) -> AudioClip:
    """The clip for a request: from the cache, else synthesized and cached. ``held`` (one render's) keeps a clip left out of the cache
    because it still looks cut off, so the render asks the service for it once, not at every line that says it (review of #466)."""
    path = _cache_path(provider, cache, text, lang, voice, rate, trim)
    if path.exists():
        return read_wav(path)
    if held is not None and path in held:
        return held[path]

    def synth() -> AudioClip:
        clip = provider.synthesize(text, lang, voice, rate)
        return clip.trimmed() if trim else clip

    clip = synth()
    if provider.parallel and looks_cut_off(clip, text, lang, rate):
        again = synth()
        clip = max(clip, again, key=lambda c: c.seconds)
        if looks_cut_off(clip, text, lang, rate):
            # used this once, never cached: the next render asks the service again
            print(f"warning: {text!r} came back cut off twice ({clip.seconds:.2f} s); not cached", file=sys.stderr, flush=True)
            if held is not None:
                held[path] = clip
            return clip
    # write then rename: a cache shared between learners (generate --cache) may be read
    # by another run meanwhile, and a crash must not leave a truncated clip behind
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp")
    write_wav(clip, tmp)
    os.replace(tmp, path)
    return clip


def save_cues(cues: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding="utf-8")
