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

# review_candidates (issue #128): what counts as practising an item, the stages that give
# part of the answer away (an intro's own recall comes right after hearing it), and where
# "late" and "early" start, as shares of the lesson's length
PRACTICE_KINDS = ("intro", "recall", "generative", "connect", "dialogue")
HINTED_STAGES = ("intro", "cloze", "hinted")
LATE_RECALL_SHARE = 2 / 3
EARLY_LAST_SHARE = 0.5


@dataclass
class Segment:
    type: str  # narrate | speak | pause | answer
    speaker: str | None = None  # instructor | native_a | native_b
    text: str | None = None
    lang: str | None = None
    rate: float = 1.0  # 1.0 = natural speed; Timing.slow_rate for pronunciation demos
    duration: float = 0.0  # seconds; exact for pauses, estimated for speech
    role: str | None = None  # for pauses: answer | repeat | beat ; for speech: hint labels
    exercise: int | None = None  # index into Script.exercises
    # what the TTS provider receives when it differs from ``text`` (native script for a
    # romanized display: "sate" → "さて"); None means speak ``text``
    speech_text: str | None = None
    # pauses: the shortest this pause may become when the renderer shrinks pauses to fit
    # the requested length (the timing model's floor for it); None = no floor
    floor: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class Exercise:
    """Bookkeeping for one prompt→pause→answer unit (or a dialogue)."""

    index: int
    kind: str  # opening | intro | recall | generative | connect | dialogue | note | closing
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

    def review_questions(self) -> list[dict]:
        """Written recall questions for reviewing the lesson later (a bot, a page): the
        instructor's cue that preceded an answer, and the answer, so that every item the
        lesson recalled is asked about once.

        Built from the spoken recalls that still work as text: a cloze fragment or a
        first-word hint is audio the reader would not have, so those are skipped. A
        question about the item alone beats a sentence it shares with another item (a
        construction and its fill), a situation cue beats a bare meaning, a recall beats
        the introduction, and among equals the latest wins. A shared sentence asks about
        every item it covers that has no question of its own. Returns, in lesson order,
        [{"items": [ids], "prompt", "answer", "stage"}].
        """
        rank = {"situation": 0, "intro": 2}
        by_ex: dict[int, list[Segment]] = {}
        for seg in self.segments:
            if seg.exercise is not None:
                by_ex.setdefault(seg.exercise, []).append(seg)
        candidates = []
        for ex in self.exercises:
            if not ex.item_ids or ex.kind not in ("intro", "recall", "connect", "generative"):
                continue
            if ex.stage in ("cloze", "hinted"):
                continue
            pairs: list[tuple[str, str]] = []
            cue: str | None = None
            after_answer_pause = False
            for seg in by_ex.get(ex.index, []):
                if seg.type == "narrate":
                    cue = seg.text
                elif seg.type == "speak" and seg.role in ("partial", "hint"):
                    cue = None  # the cue relied on audio
                elif seg.type == "answer" and after_answer_pause and cue:
                    pairs.append((cue, seg.text or ""))
                    cue = None
                after_answer_pause = seg.type == "pause" and seg.role == "answer"
            if len(pairs) == len(ex.item_ids):
                groups = [([i], p) for i, p in zip(ex.item_ids, pairs)]
            elif len(pairs) == 1:
                groups = [(list(ex.item_ids), pairs[0])]
            else:
                continue  # can't tell which answer belongs to which item
            for ids, (prompt, answer) in groups:
                key = (len(ids) > 1, rank.get(ex.stage or "", 1), -ex.index)
                candidates.append((key, ex.index, ids, prompt, answer, ex.stage))
        covered: set[str] = set()
        questions = []
        for _, index, ids, prompt, answer, stage in sorted(candidates, key=lambda c: c[0]):
            fresh = [i for i in ids if i not in covered]
            if fresh:
                covered.update(fresh)
                questions.append((index, {"items": fresh, "prompt": prompt, "answer": answer, "stage": stage}))
        return [q for _, q in sorted(questions, key=lambda q: q[0])]

    def review_candidates(self) -> list[dict]:
        """Deterministic things worth asking the learner about after the lesson (issue
        #128): they confirm or reject concrete candidates instead of recalling a long
        lesson from memory. Never used to change scheduling.

        - ``repeated_situation``: the same situation cue asked for the same item more than
          once in this lesson ({"items", "count", "prompt"}).
        - ``early_last_appearance``: a new item last heard before the middle of the lesson
          ({"items", "last_s", "end_s"}).
        - ``no_late_recall``: a new item heard later on, but never produced without a hint
          in the last third ({"items", "last_recall_s", "end_s"}); ``last_recall_s`` is
          None when it was never produced unhinted at all. Producing it unhinted means an
          answer pause with no hint or cloze fragment spoken first, outside an intro — a
          bridge exchange or a mixed review counts as much as a situation recall.

        Times are the plan's estimates (before audio fitting), so read them as shares of
        ``end_s``. Returns candidates in lesson order of their item's first appearance."""
        by_ex: dict[int, list[str]] = {}
        answered: set[int] = set()
        hinted: set[int] = set()
        for seg in self.segments:
            if seg.exercise is None:
                continue
            if seg.type == "narrate" and seg.text:
                by_ex.setdefault(seg.exercise, []).append(seg.text)
            elif seg.type == "pause" and seg.role == "answer":
                answered.add(seg.exercise)
            elif seg.type == "speak" and seg.role in ("partial", "hint"):
                hinted.add(seg.exercise)

        def unhinted(e: Exercise) -> bool:
            return (e.kind != "intro" and e.stage not in HINTED_STAGES
                    and e.index in answered and e.index not in hinted)

        practice = [e for e in self.exercises if e.item_ids and e.kind in PRACTICE_KINDS]
        end = max((e.start + e.duration for e in self.exercises), default=0.0)
        out: list[tuple[float, dict]] = []

        cues: dict[tuple[str, str], list[Exercise]] = {}
        for e in practice:
            if e.stage == "situation" and by_ex.get(e.index):
                cues.setdefault((e.item_ids[0], " ".join(by_ex[e.index])), []).append(e)
        for (item, prompt), exs in cues.items():
            if len(exs) > 1:
                out.append((exs[0].start, {"kind": "repeated_situation", "items": [item], "count": len(exs), "prompt": prompt}))

        for item in self.meta.get("new_items", []):
            seen = [e for e in practice if item in e.item_ids]
            if not seen:
                continue
            last = max(e.start + e.duration for e in seen)
            recalls = [e.start for e in seen if unhinted(e)]
            first = seen[0].start
            if last < end * EARLY_LAST_SHARE:
                out.append((first, {"kind": "early_last_appearance", "items": [item], "last_s": round(last, 1), "end_s": round(end, 1)}))
            elif not recalls or max(recalls) < end * LATE_RECALL_SHARE:
                last_recall = round(max(recalls), 1) if recalls else None
                out.append((first, {"kind": "no_late_recall", "items": [item], "last_recall_s": last_recall, "end_s": round(end, 1)}))
        return [c for _, c in sorted(out, key=lambda c: c[0])]

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
                # an answer is what the learner should have said, whichever voice models it
                who = "You" if s.type == "answer" else {"instructor": "Instructor", "native_a": "Speaker A", "native_b": "Speaker B"}.get(s.speaker, s.speaker)
                slow = " (slow)" if s.rate < 1 else ""
                lines.append(f"**{who}{slow}:** {s.text}")
        return "\n".join(lines) + "\n"


def _fmt_time(t: float) -> str:
    m, s = divmod(int(t), 60)
    return f"{m:02d}:{s:02d}"
