"""Persistent learner model.

One JSON file per learner. For every item the learner has met it stores the
retrieval stage reached, an SM-2-flavoured interval/ease, counts of successes
and failures, and when it is next due.

Because the lesson is audio-only we cannot observe whether a recall succeeded.
The default assumption is *presumed success*: every scheduled retrieval counts
as a success when the lesson is generated (``successes``, and the schedule grows).
What the learner confirms afterwards (``audiolesson report``, e.g. from the Discord
review) is kept apart from that (issue #119): ``recalled``, ``hesitated`` and
``failures`` count only confirmed outcomes, and each moves the schedule its own way —
recalled keeps it, hesitated brings the item back sooner, failed demotes it to tomorrow.
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
NEW_TARGET_START = 8.0  # weighted new components a lesson starts at (#218 b3)
NEW_TARGET_MIN, NEW_TARGET_MAX = 4.0, 12.0
NEW_TARGET_MINUTES = 30.0  # new_target is a rate per this many minutes; a lesson of m minutes plans m/30 of it (#242)
PACE_WINDOW = 3  # reported lessons the recall rate is taken over (#218)
LOADS = ("light", "right", "heavy")  # the learner's rating of a lesson's load (#218)


@dataclass
class ItemState:
    stage: str = "intro"  # highest stage practised so far
    ease: float = 2.3
    interval_days: float = 0.0
    due: str = ""  # ISO date
    last_practiced: str = ""  # ISO date
    introduced_lesson: int = 0
    successes: int = 0  # retrievals counted as success, presumed at generation unless reported otherwise
    durable_successes: int = 0  # successes on/after their due date only — see is_learned
    failures: int = 0  # confirmed: reported as not recalled
    recalled: int = 0  # confirmed: reported as recalled (issue #119)
    hesitated: int = 0  # confirmed: reported as recalled with hesitation
    last_outcome: str = ""  # the latest confirmed outcome: recalled | hesitated | not_recalled
    exposures: int = 0
    # set by a reported failure: the next lesson that recalls the item gives it a little
    # more time to answer (Timing.failure_think_time), then clears it (issue #104)
    extra_think_time: bool = False
    # the latest lesson that practised the item as an open failure (#149); orders a backlog
    open_practiced: int = 0
    history: list[dict] = field(default_factory=list)  # [{lesson, stages, ok}] compact log

    @property
    def is_learned(self) -> bool:
        """Solid enough to build on (as a component or prerequisite): two recalls on or after
        a due date. Recalls minutes apart in one lesson are practice, not retention."""
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
    new_target: float = NEW_TARGET_START  # weighted new components per ``NEW_TARGET_MINUTES`` minutes (#218 b3, #242), moved by suggest_target
    target_changed_at: int = 0
    speech_calibration: dict[str, float] = field(default_factory=dict)  # lang → measured/estimated TTS length
    notes_heard: dict[str, int] = field(default_factory=dict)  # note id → times played
    notes_last_heard: dict[str, int] = field(default_factory=dict)  # note id → lesson it last played in
    heard_utterances: set[str] = field(default_factory=set)  # normalised target-language lines presented so far
    bridges_heard: dict[str, int] = field(default_factory=dict)  # bridged item id → times its partner_cue played
    # #149 (lesson 13 feedback): a part heard inside an easy sentence instead of being introduced on
    # its own. item id → the lesson that did it. Not met yet: the review decides. Said back
    # (recalled), it counts as learned on its own; not said, it is introduced the usual way
    # later (``embed_failed``, so it is not embedded twice).
    embedded: dict[str, int] = field(default_factory=dict)
    embed_failed: list[str] = field(default_factory=list)
    # #183: the unknown items of a line tried in a listening scene (said part of): item id → the lesson. Not met. Said
    # back in the bonus question of the next review (``report``) the item becomes met with one durable
    # success; anything else records nothing. ``select_new`` ignores it, so a later normal introduction is unaffected.
    tried: dict[str, int] = field(default_factory=dict)
    # #149 1b-ii: theme id → the highest level whose exchange a lesson played. The next lesson takes the next level.
    themes_done: dict[str, int] = field(default_factory=dict)
    themes_last: dict[str, int] = field(default_factory=dict)  # theme -> the lesson that last played one of its levels (#149)
    themes_heard: dict[str, list[str]] = field(default_factory=dict)  # "theme:level" -> "turn:line" partner wordings heard with their meaning (#196)
    # #211: "construction:form" keys whose negative or question form was modelled to the learner ("You know this one… as a question…"). A
    # generated sentence takes a form only once it has been. None: a file from before it existed; the builder seeds it from
    # ``heard_utterances`` (a form sentence already said or heard counts as modelled) and the next lesson saves it.
    forms_modelled: set[str] | None = None

    # ---- queries ---------------------------------------------------------

    def knows(self, item_id: str) -> bool:
        st = self.items.get(item_id)
        return bool(st and st.is_learned)

    def has_met(self, item_id: str) -> bool:
        return item_id in self.items

    def is_open(self, item_id: str) -> bool:
        """A failed item stays open until a later confirmed recall (issue #149, G11): presumed
        success never closes it. The latest confirmed outcome decides; a failure that predates
        ``last_outcome`` counts while nothing was ever confirmed recalled."""
        st = self.items.get(item_id)
        if st is None:
            return False
        if st.last_outcome:
            return st.last_outcome == "not_recalled"
        return st.failures > 0 and st.recalled == 0

    def open_items(self) -> list[str]:
        """Open items in the order a lesson takes them: those that failed in the last lesson
        first (the bot asks them tomorrow), then the one longest without an open practice, so an old
        backlog comes round instead of starving behind new failures; ties go to the most often
        failed."""

        def failed_last_lesson(i: str) -> bool:
            h = self.items[i].history
            return bool(h) and h[-1].get("lesson") == self.lessons_completed and h[-1].get("outcome") == "not_recalled"

        return sorted(
            (i for i in self.items if self.is_open(i)),
            key=lambda i: (not failed_last_lesson(i), self.items[i].open_practiced, -self.items[i].failures, i),
        )

    def next_lesson_number(self) -> int:
        return self.lessons_completed + 1

    def due_count(self, today: date) -> int:
        return sum(1 for i in self.items if self.review_priority(i, today) >= 1.0)

    def _lesson_weakness(self, lesson: dict) -> tuple[float, int]:
        """(weak new items, new items) of one lesson. A failed item counts 1, a hesitated one ½: "it came out,
        but only just" is not the evidence a faster pace needs (with every new item confirmed in the Discord
        review, a pace that ignored hesitation rose every lesson to its ceiling). An item's entry is found by
        the lesson's number: a later lesson appends its own and ``history[-1]`` would be that one (#218). An
        embedded new item that failed or hesitated (``embed_failed``; it has no history of its own) is weak."""
        number = lesson["number"]
        weak = 0.0
        new_items = lesson.get("new_items", [])
        for item_id in new_items:
            st = self.items.get(item_id)
            entry = next((e for e in reversed(st.history) if e.get("lesson") == number), None) if st else None
            if entry is None:
                if item_id in self.embed_failed:
                    weak += 1
                continue
            if not entry.get("ok", True):
                weak += 1
            elif entry.get("outcome") == "hesitated":
                weak += 0.5
        return weak, len(new_items)

    def reported_window(self) -> list[dict]:
        """The last ``PACE_WINDOW`` lessons[] entries whose number is in ``reported``."""
        return [le for le in self.lessons if le["number"] in self.reported][-PACE_WINDOW:]

    def recall_rate(self) -> tuple[float, int] | None:
        """(weak new items, new items) over the last three reported lessons, or None if the last lesson was not
        reported (the pace waits for the review, H2)."""
        if not self.lessons or self.lessons[-1]["number"] not in self.reported:
            return None
        weak, total = 0.0, 0
        for lesson in self.reported_window():
            w, n = self._lesson_weakness(lesson)
            weak += w
            total += n
        return weak, total

    def suggest_pace(self, minutes: float, today: date) -> tuple[int, str]:
        """Decide how many new items the next lesson should introduce, and say why. ``pace`` keeps its meaning in items:
        ``--pace`` / ``--new``, the simulations, ``cando.simulate_reach`` and the coverage report use it. A lesson is planned
        from ``suggest_target`` (weighted new components, #218 b3) unless the number of items is given.

        Rules (see README "Pacing"):
        - start at about one new item per 5 minutes (30 min → 6), never below 3 or above 10
        - the review backlog must fit: if items due exceed ~80% of the review slots, slow down
        - the recall rate is taken over the last three reported lessons (a failed new item counts 1, a
          hesitated one ½): up by one at ≤15% with a small backlog, hold at 15–25%, down by one above 25%
        - the load rating (``report --load``): the last two rated lessons both «light», a rate ≤25% and a small backlog
          (< 0.5, as for the recall-based rise) also raise it by one; any «heavy» in the window blocks a rise. A lesson
          with no rating is skipped: it neither breaks nor extends the run (owner, #229). One step a lesson at most.
        - auto mode: an unreported lesson counts as "all good", but the pace steps up at most
          once every AUTO_STEP_EVERY lessons; `report --failed` still slows it down
        """
        default = int(min(10, max(3, round(minutes / 5))))
        pace = self.pace or default
        new_pace, reasons, changed = self._pace_rules(pace, 3, 10, minutes, today, self.pace_changed_at, "pace", pace)
        if changed:
            self.pace_changed_at = self.lessons_completed
        return int(new_pace), "; ".join(reasons)

    def suggest_target(self, minutes: float, today: date) -> tuple[float, str]:
        """The lesson's target of weighted new components (#218 b3), and why: the same rules as ``suggest_pace`` (the three-lesson
        recall window, the load rating, the backlog) move it by one a lesson, within ``NEW_TARGET_MIN``–``NEW_TARGET_MAX``."""
        # the backlog estimate reserves review slots for new *items*, so it takes the item pace, not the component target
        items = self.pace or int(min(10, max(3, round(minutes / 5))))
        new_target, reasons, changed = self._pace_rules(self.new_target, NEW_TARGET_MIN, NEW_TARGET_MAX, minutes, today, self.target_changed_at, "new-component target", items)
        if changed:
            self.target_changed_at = self.lessons_completed
        return float(new_target), "; ".join(reasons)

    def _pace_rules(self, pace: float, lo: float, hi: float, minutes: float, today: date, changed_at: int, label: str, slots_items: float) -> tuple[float, list[str], bool]:
        reasons: list[str] = []
        due = self.due_count(today)
        # rough capacity: one exercise ≈ 16 s; a new item costs ≈ 6 exercises
        review_slots = max(0, int(minutes * 60 / 16) - round(slots_items) * 6)
        backlog_ratio = due / review_slots if review_slots else 1.0
        fb = self.recall_rate()
        auto_assumed = False
        if fb is None and self.feedback_mode == "auto" and self.lessons:
            fb = (0, len(self.lessons[-1].get("new_items", [])))
            auto_assumed = True
        fail_rate = (fb[0] / fb[1]) if fb and fb[1] else None
        new_pace = pace
        if backlog_ratio > 0.8:
            new_pace -= 1
            reasons.append(f"{due} items due vs ~{review_slots} review slots")
        if fail_rate is not None and fail_rate > 0.25:
            new_pace -= 1
            reasons.append(f"{fb[0]:g}/{fb[1]} new items failed in the last {len(self.reported_window())} lessons (a hesitation counts ½)")
        last = self.lessons[-1] if self.lessons else None
        if last and new_pace == pace and last.get("due_at_start", 0) >= 8 and last.get("due_not_fitted", 0) > 0.25 * last["due_at_start"]:
            new_pace -= 1
            reasons.append(f"{last['due_not_fitted']} of {last['due_at_start']} due reviews did not fit last lesson")
        recent = self.reported_window()
        if last and last not in recent:
            recent.append(last)
        heavy = any(le.get("load") == "heavy" for le in recent)
        rated = [le for le in self.lessons if le.get("load") in LOADS][-2:]
        two_light = len(rated) == 2 and all(le["load"] == "light" for le in rated)
        if new_pace == pace and heavy and fail_rate is not None and fail_rate <= 0.15 and backlog_ratio < 0.5:
            reasons.append("a lesson in the window was rated heavy — not speeding up")
        elif new_pace == pace and not heavy and fail_rate is not None and fail_rate <= 0.15 and backlog_ratio < 0.5 and not auto_assumed:
            new_pace += 1
            reasons.append(f"{fb[0]:g}/{fb[1]} new items failed over the last {len(self.reported_window())} lessons, backlog small")
        elif new_pace == pace and not heavy and two_light and fail_rate is not None and fail_rate <= 0.25 and backlog_ratio < 0.5 and not auto_assumed:
            new_pace += 1
            reasons.append(f"the last two lessons were rated light ({fb[0]:g}/{fb[1]} failed)")
        elif new_pace == pace and not heavy and fail_rate is not None and fail_rate <= 0.15 and backlog_ratio < 0.5 and auto_assumed:
            if self.lessons_completed - changed_at >= AUTO_STEP_EVERY:
                new_pace += 1
                reasons.append(f"auto: {AUTO_STEP_EVERY} lessons without reported failures, backlog small")
            else:
                reasons.append(f"auto: next step after lesson {changed_at + AUTO_STEP_EVERY}")
        if auto_assumed and fb[1] == 0:
            reasons.append("last lesson was review only")
        elif self.feedback_mode != "auto" and self.lessons and self.lessons[-1]["number"] not in self.reported:
            reasons.append("no feedback for the last lesson (run `audiolesson report`, or use --auto) — not speeding up")
        elif fb is not None and fb[1] == 0 and not auto_assumed:
            reasons.append("last lesson was review only")
        new_pace = min(hi, max(lo, new_pace))
        changed = new_pace != pace
        shown = (lambda v: f"{v:g}")
        reasons.insert(0, f"{label} {shown(pace)} → {shown(new_pace)}" if changed else f"{label} {shown(pace)}")
        return new_pace, reasons, changed

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
            stage_before = st.stage
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
                if self.is_open(item_id):
                    # open (#149): practice is not evidence. The stage a failure demoted it to
                    # stands, no success is counted, interval and ease stay, and it is due
                    # again tomorrow, until a confirmed recall
                    st.stage = stage_before
                    st.interval_days = 1
                    st.due = (today + timedelta(days=1)).isoformat()
                else:
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

    def report(
        self,
        failed: list[str],
        easy: list[str],
        today: date,
        lesson_number: int | None = None,
        hesitated: list[str] | None = None,
        recalled: list[str] | None = None,
        sooner: list[str] | None = None,
        load: str | None = None,
    ) -> dict:
        """Learner feedback after listening. Returns a summary of what changed.

        Without ``lesson_number`` the feedback refers to the latest lesson. Calling it with
        no items is meaningful too: it records "I listened, everything came out".

        Confirmed outcomes (issue #119), applied to a schedule that presumed success:
        ``recalled`` keeps it (and counts as confirmed), ``hesitated`` brings the item back
        at half the interval, ``failed`` demotes it and brings it back tomorrow. An item in
        more than one list (two questions sharing it) takes the weakest outcome.

        ``sooner`` (#222) is not an outcome but a request about the schedule: the learner says, right after
        listening, that they don't remember an item (the feedback form). It moves ``due`` to at most half the
        interval from today and changes nothing else: no hesitation, failure or recall is counted, the ease and
        history stay, an embedded or tried item is left to its next-day review (``sooner_skipped``), and a call
        with ``sooner`` alone does not mark the lesson reported (that waits for the review, H2).

        ``load`` (#218) is the learner's rating of the lesson (light / right / heavy), stored as ``lessons[k]["load"]`` for
        the matching number; like ``sooner`` alone, a call with only a load does not mark the lesson reported.
        """
        only_sooner = bool(sooner or load) and not (failed or easy or hesitated or recalled)
        if lesson_number is None:
            lesson_number = self.lessons_completed
        if lesson_number and lesson_number not in self.reported and not only_sooner:
            self.reported.append(lesson_number)
        if load is not None and load not in LOADS:
            raise ValueError(f"load must be one of {', '.join(LOADS)}, not {load!r}")
        failed = list(dict.fromkeys(failed))
        hesitated = [i for i in dict.fromkeys(hesitated or []) if i not in failed]
        recalled = [i for i in dict.fromkeys(recalled or []) if i not in failed and i not in hesitated]
        changed: dict = {"failed": [], "hesitated": [], "recalled": [], "easy": [], "unknown": [], "lesson": lesson_number, "sooner": [], "sooner_skipped": [], "load": None}

        if load is not None:
            for entry in self.lessons:
                if entry["number"] == lesson_number:
                    entry["load"] = load
                    changed["load"] = load
            if changed["load"] is None:
                changed["load_unknown"] = lesson_number

        def state(item_id: str) -> ItemState | None:
            st = self.items.get(item_id)
            if st is None:
                changed["unknown"].append(item_id)
            return st

        # an embedded part (heard in a sentence, not introduced): the review decides
        embedded_result: dict[str, str] = {}
        for item_id in failed:
            if item_id in self.embedded:
                embedded_result[item_id] = "failed"
        for item_id in hesitated:
            if item_id in self.embedded:
                embedded_result[item_id] = "failed"  # "only just" is not "can say it on its own"
        for item_id in recalled:
            if item_id in self.embedded:
                embedded_result[item_id] = "recalled"
        for item_id, result in embedded_result.items():
            lesson = self.embedded.pop(item_id)
            if result == "recalled":
                # said back after a day: that is its first recall on a due date, like any item's
                # (§9: ``knows()`` still takes two); the next one comes after the usual 3 days
                self.items[item_id] = ItemState(
                    stage="meaning", ease=2.3, interval_days=3, due=(today + timedelta(days=3)).isoformat(),
                    last_practiced=today.isoformat(), introduced_lesson=lesson, successes=1, durable_successes=1,
                    recalled=1, last_outcome="recalled", exposures=1,
                    history=[{"lesson": lesson, "stages": ["embed"], "ok": True, "outcome": "recalled"}],
                )
                changed["recalled"].append(item_id)
            else:
                if item_id not in self.embed_failed:
                    self.embed_failed.append(item_id)
                changed["failed"].append(item_id)
        # a tried item (#183): only a 言えた counts, as its first recall; a miss records nothing at all
        tried_result = [i for i in recalled if i in self.tried and i not in self.items]
        for item_id in tried_result:
            lesson = self.tried.pop(item_id)
            self.items[item_id] = ItemState(
                stage="meaning", ease=2.3, interval_days=3, due=(today + timedelta(days=3)).isoformat(),
                last_practiced=today.isoformat(), introduced_lesson=lesson, successes=1, durable_successes=1,
                recalled=1, last_outcome="recalled", exposures=1,
                history=[{"lesson": lesson, "stages": ["tried"], "ok": True, "outcome": "recalled"}],
            )
            changed["recalled"].append(item_id)
        untouched = {i for i in failed + hesitated if i in self.tried and i not in self.items}
        failed = [i for i in failed if i not in untouched]
        hesitated = [i for i in hesitated if i not in untouched]
        recalled = [i for i in recalled if i not in tried_result]
        failed = [i for i in failed if i not in embedded_result]
        hesitated = [i for i in hesitated if i not in embedded_result]
        recalled = [i for i in recalled if i not in embedded_result]

        def note_outcome(st: ItemState, outcome: str) -> None:
            st.last_outcome = outcome
            entry = next((e for e in reversed(st.history) if e.get("lesson") == lesson_number), None) if lesson_number is not None else None
            if entry is not None:  # by number: a later lesson has appended its own entry (#218)
                entry["ok"] = outcome != "not_recalled"
                entry["outcome"] = outcome

        for item_id in failed:
            if (st := state(item_id)) is None:
                continue
            st.failures += 1
            st.successes = max(0, st.successes - 1)
            st.durable_successes = max(0, st.durable_successes - 1)
            st.ease = max(1.3, st.ease - 0.2)
            st.interval_days = 1
            st.due = (today + timedelta(days=1)).isoformat()
            # demote one stage; the ladder is recomputed by the planner, so just mark it
            st.stage = "cloze" if st.stage not in ("intro", "cloze") else "intro"
            st.extra_think_time = True
            note_outcome(st, "not_recalled")
            changed["failed"].append(item_id)
        for item_id in hesitated:
            if (st := state(item_id)) is None:
                continue
            # it came out, so no demotion; but sooner than a clean recall would come back
            st.hesitated += 1
            st.ease = max(1.3, st.ease - 0.1)
            st.interval_days = max(1.0, round(st.interval_days / 2, 1))
            sooner = (today + timedelta(days=int(st.interval_days))).isoformat()
            st.due = min(st.due, sooner) if st.due else sooner
            note_outcome(st, "hesitated")
            changed["hesitated"].append(item_id)
        for item_id in recalled:
            if (st := state(item_id)) is None:
                continue
            st.recalled += 1  # the presumed success stands: the schedule already grew
            note_outcome(st, "recalled")
            changed["recalled"].append(item_id)
        for item_id in dict.fromkeys(sooner or []):
            st = self.items.get(item_id)
            if st is None:
                # decided by its next-day review; anything else is not in the learner state at all
                changed["sooner_skipped" if item_id in self.embedded or item_id in self.tried else "unknown"].append(item_id)
                continue
            earlier = (today + timedelta(days=max(1, round(st.interval_days / 2)))).isoformat()
            st.due = min(st.due, earlier) if st.due else earlier
            changed["sooner"].append(item_id)
        for item_id in easy:
            if (st := state(item_id)) is None:
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
            "new_target": self.new_target,
            "target_changed_at": self.target_changed_at,
            "speech_calibration": self.speech_calibration,
            "notes_heard": self.notes_heard,
            "notes_last_heard": self.notes_last_heard,
            "heard_utterances": sorted(self.heard_utterances),
            "bridges_heard": self.bridges_heard,
            "embedded": self.embedded,
            "embed_failed": self.embed_failed,
            "tried": self.tried,
            "themes_done": self.themes_done,
            "themes_last": self.themes_last,
            "themes_heard": self.themes_heard,
            **({"forms_modelled": sorted(self.forms_modelled)} if self.forms_modelled is not None else {}),
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
            new_target=float(raw.get("new_target", NEW_TARGET_START)),
            target_changed_at=int(raw.get("target_changed_at", 0)),
            speech_calibration=dict(raw.get("speech_calibration", {})),
            notes_heard=dict(raw.get("notes_heard", {})),
            notes_last_heard=dict(raw.get("notes_last_heard", {})),
            heard_utterances=set(raw.get("heard_utterances", [])),
            bridges_heard=dict(raw.get("bridges_heard", {})),
            embedded={k: int(v) for k, v in raw.get("embedded", {}).items()},
            embed_failed=list(raw.get("embed_failed", [])),
            tried={k: int(v) for k, v in raw.get("tried", {}).items()},
            themes_done={k: int(v) for k, v in raw.get("themes_done", {}).items()},
            themes_last={k: int(v) for k, v in raw.get("themes_last", {}).items()},
            themes_heard={k: list(v) for k, v in raw.get("themes_heard", {}).items()},
            forms_modelled=set(raw["forms_modelled"]) if "forms_modelled" in raw else None,
        )
        ls.items = {k: ItemState(**v) for k, v in raw.get("items", {}).items()}
        # a file from before notes_last_heard existed: a note heard back then counts as heard
        # in the latest lesson, so it rests the full repeat gap instead of coming straight back
        for note_id in ls.notes_heard:
            ls.notes_last_heard.setdefault(note_id, ls.lessons_completed)
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
