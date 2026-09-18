"""Persistent learner model.

One JSON file per learner. For every item the learner has met it stores the
retrieval stage reached, an SM-2-flavoured interval/ease, counts of successes
and failures, and when it is next due.

Because the lesson is audio-only we cannot observe whether a recall succeeded.
The default assumption is *presumed success*: every scheduled retrieval counts
as a success when the lesson is generated. After listening, the learner can
correct that with ``audiolesson report --failed …`` which demotes the item and
brings it back sooner.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from .stages import ladder_for, next_stage, stage_index

STATE_FORMAT = "audiolesson-learner/1"


@dataclass
class ItemState:
    stage: str = "intro"  # highest stage practised so far
    ease: float = 2.3
    interval_days: float = 0.0
    due: str = ""  # ISO date
    last_practiced: str = ""  # ISO date
    introduced_lesson: int = 0
    successes: int = 0
    failures: int = 0
    exposures: int = 0
    history: list[dict] = field(default_factory=list)  # [{lesson, stages, ok}] compact log

    @property
    def is_learned(self) -> bool:
        """Solid enough to build on (used as a component / prerequisite)."""
        return self.successes >= 2 and self.stage != "intro"


@dataclass
class LearnerState:
    target_lang: str
    known_lang: str
    level: str = "A1"
    lessons_completed: int = 0
    items: dict[str, ItemState] = field(default_factory=dict)
    dialogues_done: dict[str, int] = field(default_factory=dict)  # id -> times practised
    lessons: list[dict] = field(default_factory=list)  # lesson log

    # ---- queries ---------------------------------------------------------

    def knows(self, item_id: str) -> bool:
        st = self.items.get(item_id)
        return bool(st and st.is_learned)

    def has_met(self, item_id: str) -> bool:
        return item_id in self.items

    def next_lesson_number(self) -> int:
        return self.lessons_completed + 1

    def review_priority(self, item_id: str, today: date) -> float:
        """Higher = more urgent. 0 if not due yet."""
        st = self.items[item_id]
        if not st.due:
            return 1.0
        due = date.fromisoformat(st.due)
        overdue_days = (today - due).days
        if overdue_days < 0:
            # not due: small positive so we can still fill a lesson with the *least* premature ones
            return 0.05 / (1 + -overdue_days)
        interval = max(1.0, st.interval_days)
        score = 1.0 + overdue_days / interval
        score += 0.5 * st.failures
        score += 0.3 if st.successes < 3 else 0.0
        return score

    # ---- updates ---------------------------------------------------------

    def record_lesson(
        self,
        lesson_number: int,
        exposures: dict[str, list[str]],
        today: date,
        *,
        presume_success: bool = True,
        ladders: dict[str, list[str]] | None = None,
    ) -> None:
        """Apply one generated lesson to the model.

        ``exposures`` maps item id → list of stages practised, in order.
        ``ladders`` (item id → climbing order) lets us pick the highest stage
        reached; without it the last non-intro stage is used.
        """
        ladders = ladders or {}
        for item_id, stages in exposures.items():
            st = self.items.get(item_id)
            new = st is None
            if new:
                st = ItemState(introduced_lesson=lesson_number, due=today.isoformat())
                self.items[item_id] = st
            st.exposures += len(stages)
            # highest stage reached in this lesson (ladder order is per kind; the planner only
            # emits stages in climbing order, so the last non-intro stage is the highest)
            climbed = [s for s in stages if s != "intro"]
            if climbed:
                ladder = ladders.get(item_id)
                if ladder:
                    ranked = sorted(climbed, key=lambda s: stage_index(ladder, s))
                    st.stage = ranked[-1]
                else:
                    st.stage = climbed[-1]
            if presume_success:
                st.successes += len(climbed)
                self._schedule_success(st, today, new)
            st.last_practiced = today.isoformat()
            st.history.append({"lesson": lesson_number, "stages": stages, "ok": presume_success})
        self.lessons_completed = max(self.lessons_completed, lesson_number)

    def _schedule_success(self, st: ItemState, today: date, new: bool) -> None:
        if new or st.interval_days < 1:
            st.interval_days = 1
        elif st.interval_days < 3:
            st.interval_days = 3
        else:
            st.interval_days = round(st.interval_days * st.ease, 1)
        st.ease = min(3.0, st.ease + 0.05)
        st.due = (today + timedelta(days=int(st.interval_days))).isoformat()

    def report(self, failed: list[str], easy: list[str], today: date, lesson_number: int | None = None) -> dict:
        """Learner feedback after listening. Returns a summary of what changed."""
        changed = {"failed": [], "easy": [], "unknown": []}
        for item_id in failed:
            st = self.items.get(item_id)
            if not st:
                changed["unknown"].append(item_id)
                continue
            st.failures += 1
            st.successes = max(0, st.successes - 1)
            st.ease = max(1.3, st.ease - 0.2)
            st.interval_days = 1
            st.due = (today + timedelta(days=1)).isoformat()
            # demote one stage; the ladder is recomputed by the planner, so just mark it
            st.stage = "cloze" if st.stage not in ("intro", "cloze") else "intro"
            if lesson_number is not None and st.history and st.history[-1].get("lesson") == lesson_number:
                st.history[-1]["ok"] = False
            changed["failed"].append(item_id)
        for item_id in easy:
            st = self.items.get(item_id)
            if not st:
                changed["unknown"].append(item_id)
                continue
            st.ease = min(3.0, st.ease + 0.15)
            st.interval_days = max(st.interval_days, 1) * 1.5
            st.due = (today + timedelta(days=int(st.interval_days))).isoformat()
            changed["easy"].append(item_id)
        return changed

    # ---- I/O -------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "format": STATE_FORMAT,
            "target_lang": self.target_lang,
            "known_lang": self.known_lang,
            "level": self.level,
            "lessons_completed": self.lessons_completed,
            "items": {k: asdict(v) for k, v in self.items.items()},
            "dialogues_done": self.dialogues_done,
            "lessons": self.lessons,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "LearnerState":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if raw.get("format") != STATE_FORMAT:
            raise ValueError(f"{path}: not a learner state file")
        ls = cls(
            target_lang=raw["target_lang"],
            known_lang=raw["known_lang"],
            level=raw.get("level", "A1"),
            lessons_completed=raw.get("lessons_completed", 0),
            dialogues_done=raw.get("dialogues_done", {}),
            lessons=raw.get("lessons", []),
        )
        ls.items = {k: ItemState(**v) for k, v in raw.get("items", {}).items()}
        return ls

    @classmethod
    def load_or_create(cls, path: str | Path, target_lang: str, known_lang: str, level: str = "A1") -> "LearnerState":
        p = Path(path)
        if p.exists():
            ls = cls.load(p)
            if (ls.target_lang, ls.known_lang) != (target_lang, known_lang):
                raise ValueError(
                    f"{path} is for {ls.target_lang}/{ls.known_lang}, curriculum is {target_lang}/{known_lang}"
                )
            return ls
        return cls(target_lang=target_lang, known_lang=known_lang, level=level)


def today_iso() -> str:
    return date.today().isoformat()


def parse_date(s: str | None) -> date:
    if not s:
        return date.today()
    return datetime.strptime(s, "%Y-%m-%d").date()


__all__ = ["ItemState", "LearnerState", "ladder_for", "next_stage", "stage_index", "today_iso", "parse_date"]
