"""Text-to-speech providers behind one tiny interface.

    provider.synthesize(text, lang, voice, rate) -> AudioClip

Add a provider by subclassing ``Provider`` and registering it in PROVIDERS.
Voices are plain strings the provider understands; ``default_voices(lang)``
gives (instructor-style, speaker A, speaker B) suggestions so a profile is
optional.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from .audio import DEFAULT_RATE, AudioClip, silence, to_pcm, wav_bytes_to_clip


class SpeechRefused(RuntimeError):
    """The speech service refused the connection for the whole budget (#296)."""


class Provider:
    name = "base"
    output_format = "wav"  # what synthesize_raw returns
    parallel = False  # safe and worthwhile to call synthesize() from several threads

    def synthesize(self, text: str, lang: str, voice: str, rate: float = 1.0) -> AudioClip:
        raise NotImplementedError

    def default_voices(self, lang: str) -> list[str]:
        """Candidate voices for a language, best first. Return [] if unknown."""
        return []

    def check(self) -> str | None:
        """Return a human-readable problem if the provider cannot run, else None."""
        return None


# --------------------------------------------------------------------------- stub


class StubProvider(Provider):
    """No TTS at all: a soft tone whose length matches the estimated speech.

    Lets you check lesson structure, pauses and total length without any
    network or system voice. Different speakers get different pitches.
    """

    name = "stub"

    def synthesize(self, text: str, lang: str, voice: str, rate: float = 1.0) -> AudioClip:
        from ..timing import Timing

        secs = Timing().speech_estimate(text, lang, rate)
        pitch = {"instructor": 330.0, "native_a": 440.0, "native_b": 523.0}.get(voice, 392.0)
        return _tone(secs, pitch)

    def default_voices(self, lang: str) -> list[str]:
        return ["stub"]


def _tone(seconds: float, freq: float, rate: int = DEFAULT_RATE, amp: int = 6000) -> AudioClip:
    import array

    n = int(seconds * rate)
    buf = array.array("h")
    fade = int(rate * 0.02)
    for i in range(n):
        env = min(1.0, i / fade, (n - i) / fade) if fade else 1.0
        # gentle amplitude wobble so it sounds like syllables, not a test tone
        wobble = 0.6 + 0.4 * math.sin(2 * math.pi * 4.0 * i / rate)
        buf.append(int(amp * env * wobble * math.sin(2 * math.pi * freq * i / rate)))
    return AudioClip(buf.tobytes(), rate)


# ------------------------------------------------------------------------- espeak


class EspeakProvider(Provider):
    """espeak-ng: offline, robotic, available everywhere. Fine for checking a lesson."""

    name = "espeak"

    def check(self) -> str | None:
        return None if shutil.which("espeak-ng") or shutil.which("espeak") else "espeak-ng is not installed (apt install espeak-ng / brew install espeak-ng)"

    def synthesize(self, text: str, lang: str, voice: str, rate: float = 1.0) -> AudioClip:
        exe = shutil.which("espeak-ng") or shutil.which("espeak")
        wpm = int(160 * rate)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "o.wav"
            subprocess.run([exe, "-v", voice or lang, "-s", str(wpm), "-w", str(out), "--", text], check=True, capture_output=True)
            data = out.read_bytes()
        return to_pcm(data, "wav").trimmed()

    def default_voices(self, lang: str) -> list[str]:
        base = lang.split("-")[0].lower()
        table = {"en": ["en-us", "en-gb", "en-us+f3"], "fr": ["fr-fr", "fr-fr+f3", "fr-be"], "ja": ["ja", "ja+f3"], "is": ["is", "is+f3", "is+m3"]}
        return table.get(base, [base, base + "+f3", base + "+m3"])


# --------------------------------------------------------------------------- edge


class EdgeProvider(Provider):
    """Microsoft Edge neural voices via the free ``edge-tts`` package (pip install edge-tts)."""

    name = "edge"
    output_format = "mp3"
    parallel = True

    VOICES = {
        "en": ["en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"],
        "fr": ["fr-FR-DeniseNeural", "fr-FR-HenriNeural", "fr-FR-VivienneMultilingualNeural"],
        "es": ["es-ES-ElviraNeural", "es-ES-AlvaroNeural", "es-MX-DaliaNeural"],
        "de": ["de-DE-KatjaNeural", "de-DE-ConradNeural", "de-DE-AmalaNeural"],
        "it": ["it-IT-ElsaNeural", "it-IT-DiegoNeural", "it-IT-IsabellaNeural"],
        "pt": ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "pt-PT-RaquelNeural"],
        "ja": ["ja-JP-NanamiNeural", "ja-JP-KeitaNeural"],
        "zh": ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-XiaoyiNeural"],
        "ko": ["ko-KR-SunHiNeural", "ko-KR-InJoonNeural"],
        "nl": ["nl-NL-ColetteNeural", "nl-NL-MaartenNeural"],
        "is": ["is-IS-GudrunNeural", "is-IS-GunnarNeural"],
        "sv": ["sv-SE-SofieNeural", "sv-SE-MattiasNeural"],
        "no": ["nb-NO-PernilleNeural", "nb-NO-FinnNeural"],
        "da": ["da-DK-ChristelNeural", "da-DK-JeppeNeural"],
        "fi": ["fi-FI-NooraNeural", "fi-FI-HarriNeural"],
    }

    def check(self) -> str | None:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return "edge-tts is not installed (pip install edge-tts)"
        return None

    def synthesize(self, text: str, lang: str, voice: str, rate: float = 1.0) -> AudioClip:
        import asyncio

        import edge_tts

        pct = int(round((rate - 1.0) * 100))
        rate_s = f"{'+' if pct >= 0 else ''}{pct}%"

        async def run() -> bytes:
            comm = edge_tts.Communicate(text, voice, rate=rate_s, proxy=os.environ.get("HTTPS_PROXY") or None)
            chunks = []
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            return b"".join(chunks)

        data = self._retrying(lambda: asyncio.run(run()))
        return to_pcm(data, "mp3").trimmed()

    # The service now and then answers "no audio", drops the socket or sends a cut-off frame for one clip, and the same request works a
    # moment later (#77): a few retries after a wait, for the errors that look like the service or the network. Decided by family, not by
    # a list of names: every ``EdgeTTSException`` (NoAudioReceived, WebSocketError, UnexpectedResponse, …) plus aiohttp's ClientError, timeouts
    # and connection errors. A malformed argument (a ValueError, a TypeError) is not one and fails at once; an unknown but well-formed voice
    # comes back as NoAudioReceived, so it is retried and then fails with that message.
    RETRY_WAITS = (5.0, 20.0, 60.0)

    @staticmethod
    def _transient(exc: BaseException) -> bool:
        names = {c.__name__ for c in type(exc).__mro__}
        return bool(names & {"EdgeTTSException", "ClientError", "TimeoutError", "ConnectionError"})

    # A refusal of the handshake itself (HTTP 403) is the service saying no to everyone, not a clip failing (#296): it lasts minutes to days. It is one shared state: the
    # first worker to meet it probes after 1, 2, 4, 8 … minutes (``refusal_budget_min`` in all, 15 by default, settable in the voice profile) while the others wait on it;
    # when a probe gets through they all go on, and when the budget is spent they all fail at once with one clear last line. What was synthesized stays in the cache.
    refusal_budget_min = 15.0
    MINUTE = 60.0  # seconds in the wait unit; tests shorten it

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._state = "open"  # open | probing | failed
        self._failure: Exception | None = None

    @staticmethod
    def _refused(exc: BaseException) -> bool:
        """The service refused the connection (status 403 at the handshake): decided by the status, not by the exception's name."""
        return getattr(exc, "status", None) == 403

    def _schedule(self) -> list[float]:
        """The minutes to wait before each probe: 1, 2, 4, 8 … until the budget is spent."""
        waits, spent, step = [], 0.0, 1.0
        while spent + 1e-9 < self.refusal_budget_min:
            wait = min(step, self.refusal_budget_min - spent)
            waits.append(wait)
            spent += wait
            step *= 2
        return waits or [self.refusal_budget_min]

    def _wait_out_refusal(self, attempt, exc: BaseException):
        """Called by a worker that met a refusal: ``("done", result)`` when this worker's own probe got through, ``("go", None)`` when another worker's did (try again),
        and raises ``SpeechRefused`` when the budget is spent (for every worker)."""
        with self._cond:
            if self._state == "failed":
                raise self._failure  # type: ignore[misc]
            if self._state == "probing":
                while self._state == "probing":
                    self._cond.wait()
                if self._state == "failed":
                    raise self._failure  # type: ignore[misc]
                return "go", None
            self._state = "probing"
        schedule = self._schedule()
        try:
            for n, minutes in enumerate(schedule, 1):
                print(f"edge-tts: service refusing (403), waiting {minutes:g} min ({n}/{len(schedule)})", file=sys.stderr, flush=True)
                time.sleep(minutes * self.MINUTE)
                try:
                    result = attempt()
                except Exception as again:
                    if self._refused(again):
                        continue
                    with self._cond:  # not a refusal any more (another error, or none): the service answers
                        self._state = "open"
                        self._cond.notify_all()
                    raise
                with self._cond:
                    self._state = "open"
                    self._cond.notify_all()
                return "done", result
            failure = SpeechRefused(f"speech service refused (403) for {self.refusal_budget_min:g} min; cached clips kept")
            with self._cond:
                self._state, self._failure = "failed", failure
                self._cond.notify_all()
            raise failure
        except BaseException:
            with self._cond:
                if self._state == "probing":
                    self._state = "open"
                    self._cond.notify_all()
            raise

    def _retrying(self, attempt):
        n = 0
        while True:
            wait = self.RETRY_WAITS[n] if n < len(self.RETRY_WAITS) else None
            try:
                return attempt()
            except SpeechRefused:
                raise
            except Exception as exc:
                if self._refused(exc):
                    kind, result = self._wait_out_refusal(attempt, exc)
                    if kind == "done":
                        return result
                    continue  # another worker's probe got through: try this clip again
                if wait is None or not self._transient(exc):
                    raise
                print(f"edge-tts: {type(exc).__name__}, retrying in {wait:g} s ({n + 1}/{len(self.RETRY_WAITS)})", file=sys.stderr, flush=True)
                time.sleep(wait)
                n += 1

    def default_voices(self, lang: str) -> list[str]:
        return list(self.VOICES.get(lang.split("-")[0].lower(), []))


# ------------------------------------------------------------------------- openai


class OpenAIProvider(Provider):
    """OpenAI speech API (paid). Needs OPENAI_API_KEY. Uses plain urllib, no SDK."""

    name = "openai"
    parallel = True
    MODEL = os.environ.get("AUDIOLESSON_OPENAI_TTS_MODEL", "gpt-4o-mini-tts")

    def check(self) -> str | None:
        return None if os.environ.get("OPENAI_API_KEY") else "OPENAI_API_KEY is not set"

    def synthesize(self, text: str, lang: str, voice: str, rate: float = 1.0) -> AudioClip:
        body = {"model": self.MODEL, "input": text, "voice": voice or "alloy", "response_format": "wav", "speed": max(0.25, min(4.0, rate))}
        req = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        return wav_bytes_to_clip(data).trimmed()

    def default_voices(self, lang: str) -> list[str]:
        return ["nova", "onyx", "shimmer"]


# ------------------------------------------------------------------------- macOS


class SayProvider(Provider):
    """macOS built-in voices via ``say``. Needs ffmpeg for the AIFF → WAV step."""

    name = "say"
    output_format = "aiff"

    def check(self) -> str | None:
        if not shutil.which("say"):
            return "the macOS 'say' command is not available"
        if not shutil.which("ffmpeg"):
            return "ffmpeg is needed to convert 'say' output"
        return None

    def synthesize(self, text: str, lang: str, voice: str, rate: float = 1.0) -> AudioClip:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "o.aiff"
            cmd = ["say", "-o", str(out), "-r", str(int(175 * rate))]
            if voice:
                cmd += ["-v", voice]
            subprocess.run(cmd + ["--", text], check=True, capture_output=True)
            data = out.read_bytes()
        return to_pcm(data, "aiff").trimmed()

    def default_voices(self, lang: str) -> list[str]:
        base = lang.split("-")[0].lower()
        table = {"en": ["Samantha", "Daniel"], "fr": ["Thomas", "Amelie"], "ja": ["Kyoko", "Otoya"], "es": ["Monica", "Jorge"], "de": ["Anna", "Markus"], "it": ["Alice", "Luca"], "zh": ["Tingting"], "ko": ["Yuna"]}
        return table.get(base, [])


PROVIDERS: dict[str, type[Provider]] = {
    "stub": StubProvider,
    "espeak": EspeakProvider,
    "edge": EdgeProvider,
    "openai": OpenAIProvider,
    "say": SayProvider,
}


def get_provider(name: str) -> Provider:
    try:
        return PROVIDERS[name]()
    except KeyError:
        raise ValueError(f"unknown TTS provider {name!r}; choose from {sorted(PROVIDERS)}") from None


__all__ = ["Provider", "PROVIDERS", "get_provider", "silence"]
