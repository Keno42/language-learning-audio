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
import tempfile
import urllib.request
from pathlib import Path

from .audio import DEFAULT_RATE, AudioClip, silence, to_pcm, wav_bytes_to_clip


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
        table = {"en": ["en-us", "en-gb", "en-us+f3"], "fr": ["fr-fr", "fr-fr+f3", "fr-be"], "ja": ["ja", "ja+f3"]}
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

        data = asyncio.run(run())
        return to_pcm(data, "mp3").trimmed()

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
