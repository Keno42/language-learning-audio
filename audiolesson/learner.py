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
MAX_INTERVAL_DAYS = 180
AUTO_STEP_EVERY = 3  # auto mode: lessons between pace increases


@dataclass
class ItemState:
    stage: str = "intro"  # highest stage practised so far
    ease: float = 2.3
    interval_days: float = 0.0
    due: str = ""  # ISO date
    last_practiced: str = ""  # ISO date
    introduced_lesson: int = 0
    successes: int = 0
    durable_successes: int = 0  # successes on/after their due date only — see is_learned
    failures: int = 0
    exposures: int = 0
    history: list[dict] = field(default_factory=list)  # [{lesson, stages, ok}] compact log

    @property
    def is_learned(self) -> bool:
        """Solid enough to build on (used as a component / prerequisite).

        Deliberately keyed on ``durable_successes``, not ``successes``: several correct
        recalls minutes apart in the same lesson (the intra-lesson reactivation ladder) are
        good practice but not evidence of retention across time, so they don't count here —
        only a recall on or after the item's scheduled due date does (see record_lesson)."""
        return self.durable_successes >= 2 and self.stage != "intro"


@dataclass
class LearnerState:
    target_lang: str
    known_lang: str
    level: str = "A1"
    lessons_completed: int = 0
    items: dict[str, ItemState] = field(default_factory=dict)
    dialogues_done: dict[str, int] = field(default_factory=dict)  # id -> times practised
    lessons: list[dict] = field(default_factory=list)  # lesson log
    pace: int | None = None  # new items per lesson, adjusted from feedback (None = default for the length)
    reported: list[int] = field(default_factory=list)  # lesson numbers the learner gave feedback on
    feedback_mode: str = "manual"  # manual: pace rises only on `report`; auto: rises on its own every few lessons
    pace_changed_at: int = 0  # lesson number of the last pace change (auto mode steps slowly)
    speech_calibration: dict[str, float] = field(default_factory=dict)  # lang → measured/estimated TTS length
    notes_heard: dict[str, int] = field(default_factory=dict)  # note id → times played
    heard_utterances: set[str] = field(default_factory=set)  # normalised target-language lines presented so far (issue #68)
    bridges_heard: dict[str, int] = field(default_factory=dict)  # bridged item id → times its partner_cue played

    # ---- queries ---------------------------------------------------------

    def knows(self, item_id: str) -> bool:
        st = self.items.get(item_id)
        return bool(st and st.is_learned)

    def has_met(self, item_id: str) -> bool:
        return item_id in self.items

    def next_lesson_number(self) -> int:
        return self.lessons_completed + 1

    def due_count(self, today: date) -> int:
        return sum(1 for i in self.items if self.review_priority(i, today) >= 1.0)

    def last_lesson_failures(self) -> tuple[int, int] | None:
        """(failed new items, new items) of the last lesson, or None if it was not reported."""
        if not self.lessons:
            return None
        last = self.lessons[-1]
        if last["number"] not in self.reported:
            return None
        failed = 0
        for item_id in last.get("new_items", []):
            st = self.items.get(item_id)
            if st and st.history and st.history[-1].get("lesson") == last["number"] and not st.history[-1].get("ok", True):
                failed += 1
        return failed, len(last.get("new_items", []))

    def suggest_pace(self, minutes: float, today: date) -> tuple[int, str]:
        """Decide how many new items the next lesson should introduce, and say why.

        Rules (see README "Pacing"):
        - start at about one new item per 5 minutes (30 min → 6), never below 3 or above 10
        - the review backlog must fit: if items due exceed ~80% of the review slots, slow down
        - if the last reported lesson had >20% of its new items fail, slow down
        - speed up only on evidence: last lesson reported with ≤10% failures and a small backlog
        - auto mode: an unreported lesson counts as "all good", but the pace steps up at most
          once every AUTO_STEP_EVERY lessons; `report --failed` still slows it down
        """
        default = int(min(10, max(3, round(minutes / 5))))
        pace = self.pace or default
        reasons: list[str] = []
        due = self.due_count(today)
        # rough capacity: one exercise ≈ 16 s; a new item costs ≈ 6 exercises
        review_slots = max(0, int(minutes * 60 / 16) - pace * 6)
        backlog_ratio = due / review_slots if review_slots else 1.0
        fb = self.last_lesson_failures()
        auto_assumed = False
        if fb is None and self.feedback_mode == "auto" and self.lessons:
            fb = (0, len(self.lessons[-1].get("new_items", [])))
            auto_assumed = True
        fail_rate = (fb[0] / fb[1]) if fb and fb[1] else None
        new_pace = pace
        if backlog_ratio > 0.8:
            new_pace -= 1
            reasons.append(f"{due} items due vs ~{review_slots} review slots")
        if fail_rate is not None and fail_rate > 0.2:
            new_pace -= 1
            reasons.append(f"{fb[0]}/{fb[1]} new items failed last lesson")
        last = self.lessons[-1] if self.lessons else None
        if last and new_pace == pace and last.get("due_at_start", 0) >= 8 and last.get("due_not_fitted", 0) > 0.25 * last["due_at_start"]:
            new_pace -= 1
            reasons.append(f"{last['due_not_fitted']} of {last['due_at_start']} due reviews did not fit last lesson")
        if new_pace == pace and fail_rate is not None and fail_rate <= 0.1 and backlog_ratio < 0.5:
            if not auto_assumed:
                new_pace += 1
                reasons.append(f"last lesson reported easy ({fb[0]}/{fb[1]} failed), backlog small")
            elif self.lessons_completed - self.pace_changed_at >= AUTO_STEP_EVERY:
                new_pace += 1
                reasons.append(f"auto: {AUTO_STEP_EVERY} lessons without reported failures, backlog small")
            else:
                reasons.append(f"auto: next step after lesson {self.pace_changed_at + AUTO_STEP_EVERY}")
        if auto_assumed and fb[1] == 0:
            reasons.append("last lesson was review only")
        elif self.feedback_mode != "auto" and self.lessons and self.lessons[-1]["number"] not in self.reported:
            reasons.append("no feedback for the last lesson (run `audiolesson report`, or use --auto) — not speeding up")
        elif fb is not None and fb[1] == 0 and not auto_assumed:
            reasons.append("last lesson was review only")
        new_pace = int(min(10, max(3, new_pace)))
        if new_pace != pace:
            self.pace_changed_at = self.lessons_completed
            reasons.insert(0, f"pace {pace} → {new_pace}")
        else:
            reasons.insert(0, f"pace {pace}")
        return new_pace, "; ".join(reasons)

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
                    # never lower a stage: a fallback exercise (e.g. no dialogue fitted) is not a demotion
                    candidates = climbed + ([st.stage] if st.stage in ladder else [])
                    st.stage = max(candidates, key=lambda s: stage_index(ladder, s))
                else:
                    st.stage = climbed[-1]
            if presume_success:
                st.successes += len(climbed)
                if climbed and self._is_durable_review(st, today, new):
                    st.durable_successes += 1
                self._schedule_success(st, today, new)
            st.last_practiced = today.isoformat()
            st.history.append({"lesson": lesson_number, "stages": stages, "ok": presume_success})
        self.lessons_completed = max(self.lessons_completed, lesson_number)

    def _is_durable_review(self, st: ItemState, today: date, new: bool) -> bool:
        """True for a genuine spaced review: not the item's first (intro) lesson, and not an
        early reactivation before its due date. Call before ``_schedule_success`` mutates
        ``st.due``/``st.interval_days`` — same "was this early" question that function asks,
        for the same reason: an early recall is good practice but no evidence of retention."""
        if new or st.interval_days < 1:
            return False
        due = date.fromisoformat(st.due) if st.due else today
        return today >= due

    def _schedule_success(self, st: ItemState, today: date, new: bool) -> None:
        """SM-2 flavoured. Only a review *at or after* its due date earns a longer interval;
        an item that merely filled a gap in a lesson keeps its schedule, so intervals grow
        with real elapsed time, not with the number of lessons."""
        due = date.fromisoformat(st.due) if st.due else today
        if new or st.interval_days < 1:
            st.interval_days = 1
        elif today < due:
            return  # early: no new evidence about long-term retention, schedule unchanged
        elif st.interval_days < 3:
            st.interval_days = 3
        else:
            elapsed = (today - (due - timedelta(days=int(st.interval_days)))).days  # since the interval was set
            st.interval_days = round(min(MAX_INTERVAL_DAYS, max(st.interval_days, elapsed) * st.ease), 1)
        st.ease = min(3.0, st.ease + 0.05)
        st.due = (today + timedelta(days=int(st.interval_days))).isoformat()

    def report(self, failed: list[str], easy: list[str], today: date, lesson_number: int | None = None) -> dict:
        """Learner feedback after listening. Returns a summary of what changed.

        Without ``lesson_number`` the feedback refers to the latest lesson. Calling it with
        no failed/easy items is meaningful too: it records "I listened, everything came out".
        """
        if lesson_number is None:
            lesson_number = self.lessons_completed
        if lesson_number and lesson_number not in self.reported:
            self.reported.append(lesson_number)
        changed = {"failed": [], "easy": [], "unknown": [], "lesson": lesson_number}
        for item_id in failed:
            st = self.items.get(item_id)
            if not st:
                changed["unknown"].append(item_id)
                continue
            st.failures += 1
            st.successes = max(0, st.successes - 1)
            st.durable_successes = max(0, st.durable_successes - 1)
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
            st.interval_days = min(MAX_INTERVAL_DAYS, max(st.interval_days, 1) * 1.5)
            st.due = (today + timedelta(days=int(st.interval_days))).isoformat()
            changed["easy"].append(item_id)
        return changed

    def calibrate(self, measured: dict[str, float], weight: float = 0.7) -> None:
        """Fold a render's measured/planned speech ratios into the stored calibration.

        The planned lengths already included the current calibration, so the measured
        ratio is a *correction* to it: 1.0 means the plan was spot on.
        """
        for lang, ratio in measured.items():
            old = self.speech_calibration.get(lang, 1.0)
            new = old * ((1 - weight) + weight * ratio)
            self.speech_calibration[lang] = round(min(3.0, max(0.3, new)), 3)

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
            "pace": self.pace,
            "reported": self.reported,
            "feedback_mode": self.feedback_mode,
            "pace_changed_at": self.pace_changed_at,
            "speech_calibration": self.speech_calibration,
            "notes_heard": self.notes_heard,
            "heard_utterances": sorted(self.heard_utterances),
            "bridges_heard": self.bridges_heard,
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
            pace=raw.get("pace"),
            reported=list(raw.get("reported", [])),
            feedback_mode=raw.get("feedback_mode", "manual"),
            pace_changed_at=int(raw.get("pace_changed_at", 0)),
            speech_calibration=dict(raw.get("speech_calibration", {})),
            notes_heard=dict(raw.get("notes_heard", {})),
            heard_utterances=set(raw.get("heard_utterances", [])),
            bridges_heard=dict(raw.get("bridges_heard", {})),
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
