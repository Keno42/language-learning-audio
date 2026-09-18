"""Minimal PCM audio handling on the standard library.

Everything is 16-bit mono at one sample rate (default 24 kHz). Providers that
return other formats are converted with ffmpeg (if present) — see ``to_pcm``.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

DEFAULT_RATE = 24000


@dataclass
class AudioClip:
    pcm: bytes  # 16-bit little-endian mono
    rate: int = DEFAULT_RATE

    @property
    def seconds(self) -> float:
        return len(self.pcm) / 2 / self.rate

    def trimmed(self, threshold: int = 300, keep_ms: int = 60) -> "AudioClip":
        """Strip leading/trailing near-silence so pauses are exact, not padded by TTS."""
        import array

        samples = array.array("h")
        samples.frombytes(self.pcm)
        n = len(samples)
        start, end = 0, n
        while start < n and abs(samples[start]) < threshold:
            start += 1
        while end > start and abs(samples[end - 1]) < threshold:
            end -= 1
        keep = int(self.rate * keep_ms / 1000)
        start = max(0, start - keep)
        end = min(n, end + keep)
        if start == 0 and end == n:
            return self
        return AudioClip(samples[start:end].tobytes(), self.rate)


def silence(seconds: float, rate: int = DEFAULT_RATE) -> AudioClip:
    n = max(0, int(round(seconds * rate)))
    return AudioClip(b"\x00\x00" * n, rate)


def concat(clips: list[AudioClip], rate: int = DEFAULT_RATE) -> AudioClip:
    buf = io.BytesIO()
    for c in clips:
        if c.rate != rate:
            c = resample(c, rate)
        buf.write(c.pcm)
    return AudioClip(buf.getvalue(), rate)


def write_wav(clip: AudioClip, path: str | Path) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(clip.rate)
        w.writeframes(clip.pcm)


def read_wav(path: str | Path) -> AudioClip:
    with wave.open(str(path), "rb") as w:
        ch, sw, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if ch == 1 and sw == 2:
        return AudioClip(raw, rate)
    return to_pcm(raw, "wav", rate)


def wav_bytes_to_clip(data: bytes) -> AudioClip:
    with wave.open(io.BytesIO(data), "rb") as w:
        ch, sw, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if ch == 1 and sw == 2:
        return AudioClip(raw, rate)
    return to_pcm(data, "wav", rate)


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def to_pcm(data: bytes, fmt: str, rate: int = DEFAULT_RATE) -> AudioClip:
    """Convert any ffmpeg-readable audio bytes (mp3, aiff, multi-channel wav…) to our PCM."""
    if not have_ffmpeg():
        raise RuntimeError(
            f"TTS returned {fmt} audio but ffmpeg is not installed; install ffmpeg or use a provider that returns 16-bit mono WAV"
        )
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", fmt, "-i", "pipe:0", "-ac", "1", "-ar", str(rate), "-f", "s16le", "pipe:1"]
    if fmt == "auto":
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", str(rate), "-f", "s16le", "pipe:1"]
    out = subprocess.run(cmd, input=data, capture_output=True, check=True).stdout
    return AudioClip(out, rate)


def resample(clip: AudioClip, rate: int) -> AudioClip:
    if clip.rate == rate:
        return clip
    if have_ffmpeg():
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "s16le", "-ar", str(clip.rate), "-ac", "1", "-i", "pipe:0", "-ar", str(rate), "-f", "s16le", "pipe:1"]
        return AudioClip(subprocess.run(cmd, input=clip.pcm, capture_output=True, check=True).stdout, rate)
    # crude nearest-neighbour fallback so the lesson still renders
    import array

    src = array.array("h")
    src.frombytes(clip.pcm)
    n_out = int(len(src) * rate / clip.rate)
    dst = array.array("h", (src[min(len(src) - 1, int(i * clip.rate / rate))] for i in range(n_out)))
    return AudioClip(dst.tobytes(), rate)


def to_mp3(wav_path: str | Path, mp3_path: str | Path, bitrate: str = "64k") -> bool:
    """Encode with ffmpeg. Returns False (and leaves no file) if ffmpeg is missing."""
    if not have_ffmpeg():
        return False
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-b:a", bitrate, str(mp3_path)],
        check=True,
    )
    return True
