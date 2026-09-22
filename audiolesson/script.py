"""Intermediate lesson script: a flat, pre-timed list of segments.

The renderer never sees curriculum or learner objects — only this. That is
what lets the same lesson be re-rendered with different voices, speeds, pause
lengths or TTS providers.

Segment types
-------------
narrate   instructor speaks in the learner's known language
speak     a target-language speaker says something (prompt, partner line, chunk)
pause     silence for the learner to answer (``role`` = "answer" | "repeat" | "beat")
answer    the model answer in the target language (what the learner should have said)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

SPEAKERS = ("instructor", "native_a", "native_b")


@dataclass
class Segment:
    type: str  # narrate | speak | pause | answer
    speaker: str | None = None
    text: str | None = None
    lang: str | None = None
    rate: float = 1.0  # 1.0 = natural speed; 0.75 = slow
    duration: float = 0.0  # seconds; exact for pauses, estimated for speech
    role: str | None = None  # for pauses: answer | repeat | beat ; for speech: hint labels
    exercise: int | None = None  # index into Script.exercises
    # What actually reaches the TTS provider, when it must differ from ``text`` (issue #49,
    # PR #51 owner review): a note may show a romanized form (``text``, e.g. "sate") but
    # need native orthography spoken (``speech_text``, e.g. "さて") so pronunciation doesn't
    # depend on a provider correctly reading transliterated text — some providers don't even
    # use ``lang`` to disambiguate it. None (the common case) means "speak ``text`` as-is."
    speech_text: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class Exercise:
    """Bookkeeping for one prompt→pause→answer unit (or a dialogue)."""

    index: int
    kind: str  # intro | recall | generative | dialogue | closing | opening
    stage: str | None
    item_ids: list[str] = field(default_factory=list)
    label: str = ""
    start: float = 0.0  # estimated start time in seconds
    duration: float = 0.0


@dataclass
class Script:
    lesson_number: int
    title: str
    target_lang: str
    known_lang: str
    segments: list[Segment] = field(default_factory=list)
    exercises: list[Exercise] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    # ---- construction --------------------------------------------------

    def add(self, seg: Segment) -> Segment:
        self.segments.append(seg)
        return seg

    def extend(self, segs: Iterable[Segment]) -> None:
        self.segments.extend(segs)

    def new_exercise(self, kind: str, stage: str | None, item_ids: list[str], label: str = "") -> Exercise:
        ex = Exercise(index=len(self.exercises), kind=kind, stage=stage, item_ids=list(item_ids), label=label)
        self.exercises.append(ex)
        return ex

    # ---- stats ----------------------------------------------------------

    @property
    def total_duration(self) -> float:
        return sum(s.duration for s in self.segments)

    def pause_seconds(self, role: str | None = None) -> float:
        return sum(s.duration for s in self.segments if s.type == "pause" and (role is None or s.role == role))

    def retime(self) -> None:
        """Recompute exercise start/duration from segment durations."""
        t = 0.0
        starts: dict[int, float] = {}
        ends: dict[int, float] = {}
        for s in self.segments:
            if s.exercise is not None:
                starts.setdefault(s.exercise, t)
                ends[s.exercise] = t + s.duration
            t += s.duration
        for ex in self.exercises:
            if ex.index in starts:
                ex.start = starts[ex.index]
                ex.duration = ends[ex.index] - starts[ex.index]

    def summary(self) -> dict:
        answers = self.pause_seconds("answer")
        total = self.total_duration
        return {
            "duration_s": round(total, 1),
            "exercises": len(self.exercises),
            "answer_pause_s": round(answers, 1),
            "all_pause_s": round(self.pause_seconds(), 1),
            "active_ratio": round(self.pause_seconds() / total, 2) if total else 0.0,
            "prompts": sum(1 for s in self.segments if s.type == "pause" and s.role == "answer"),
        }

    # ---- I/O -----------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "format": "audiolesson-script/1",
            "lesson_number": self.lesson_number,
            "title": self.title,
            "target_lang": self.target_lang,
            "known_lang": self.known_lang,
            "meta": self.meta,
            "summary": self.summary(),
            "exercises": [asdict(e) for e in self.exercises],
            "segments": [s.to_dict() for s in self.segments],
        }

    def save(self, path: str | Path) -> None:
        self.retime()
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Script":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if raw.get("format") != "audiolesson-script/1":
            raise ValueError(f"{path}: not an audiolesson script")
        sc = cls(
            lesson_number=raw["lesson_number"],
            title=raw["title"],
            target_lang=raw["target_lang"],
            known_lang=raw["known_lang"],
            meta=raw.get("meta", {}),
        )
        sc.exercises = [Exercise(**e) for e in raw.get("exercises", [])]
        sc.segments = [Segment(**s) for s in raw["segments"]]
        return sc

    def transcript(self, pronunciation_notes: dict[str, str] | None = None) -> str:
        """Human-readable transcript (supplementary material, never required).

        ``pronunciation_notes`` optionally maps item id -> a short note (typically
        ``Item.pronunciation_notes``) printed once, under the first exercise that
        touches that item. Kept as a plain dict rather than a Curriculum reference
        so this module stays independent of ``content.py``.
        """
        notes = pronunciation_notes or {}
        shown: set[str] = set()
        lines = [f"# {self.title}", ""]
        current = None
        for s in self.segments:
            if s.exercise is not None and s.exercise != current:
                current = s.exercise
                ex = self.exercises[current]
                lines.append("")
                lines.append(f"## {ex.index + 1}. {ex.label or ex.kind}  ({_fmt_time(ex.start)})")
                for item_id in ex.item_ids:
                    note = notes.get(item_id)
                    if note and item_id not in shown:
                        lines.append(f"*Pronunciation ({item_id}): {note}*")
                        shown.add(item_id)
                lines.append("")
            if s.type == "pause":
                lines.append(f"    … {s.duration:.1f}s {s.role or ''}".rstrip())
            else:
                who = {"instructor": "Instructor", "native_a": "Speaker A", "native_b": "Speaker B"}.get(s.speaker, s.speaker)
                slow = " (slow)" if s.rate < 1 else ""
                lines.append(f"**{who}{slow}:** {s.text}")
        return "\n".join(lines) + "\n"


def _fmt_time(t: float) -> str:
    m, s = divmod(int(t), 60)
    return f"{m:02d}:{s:02d}"
