"""Lesson planner: decides what to practise, in what order, at which stage.

Principles it enforces (see README "How a lesson is built"):
- a few new items, each reactivated at expanding gaps within the lesson
- reviews of older material interleaved between them
- generative recombination and dialogues once enough is known
- a closing block that ends on successful recall of today's material
"""

from __future__ import annotations

import heapq
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import date

from .content import Curriculum, Dialogue, Item
from .exercises import Builder
from .learner import LearnerState
from .prompts import Prompts
from .script import Script
from .stages import ladder_for, next_stage, stage_index
from .timing import Timing


@dataclass
class PlanConfig:
    minutes: float = 15.0
    new_items: int | None = None  # default derived from minutes
    topics: list[str] = field(default_factory=list)
    seed: int | None = None
    reactivation_gaps: list[int] = field(default_factory=lambda: [3, 5, 8, 13])  # exercises between recalls
    intro_gap: int = 3  # min exercises between two introductions
    dialogue_every: int = 7  # try a dialogue roughly every N exercises
    dialogue_first_turns: int = 2  # turns played the first time; one more each later encounter
    max_dialogues: int | None = None  # per lesson (default: one per 10 minutes, at least 2)
    max_notes: int | None = None  # cultural asides per lesson (default: one per 12 minutes, at least 1)
    note_chance: float = 0.7  # chance to play a related note right after its item
    max_review_passes: int = 2  # when material runs out, review what was reviewed once more (harder)
    closing_share: float = 0.12  # fraction of time reserved for the final review block
    max_new_items: int | None = None  # hard cap even when there is nothing to review (default: scales with minutes)
    min_time_for_new_item: float = 180.0  # seconds of budget needed to still introduce one
    presume_success: bool = True
    translate_partner: bool = True

    def resolved_max_new_items(self) -> int:
        """Extra new items may fill a lesson that has nothing to review (the first ones),
        but only a little beyond the pace — a short first lesson beats a 12-item dump."""
        if self.max_new_items is not None:
            return self.max_new_items
        return self.resolved_new_items() + 2

    def resolved_new_items(self) -> int:
        if self.new_items is not None:
            return max(0, self.new_items)
        return int(max(3, min(10, round(self.minutes / 5))))


@dataclass
class _Pending:
    due: int
    seq: int
    item: Item
    stage: str

    def __lt__(self, other: "_Pending") -> bool:
        return (self.due, self.seq) < (other.due, other.seq)


class Planner:
    def __init__(self, cur: Curriculum, learner: LearnerState, prompts: Prompts, timing: Timing, cfg: PlanConfig, today: date | None = None):
        self.cur = cur
        self.learner = learner
        self.prompts = prompts
        self.timing = timing
        self.cfg = cfg
        self.today = today or date.today()
        seed = cfg.seed if cfg.seed is not None else learner.next_lesson_number()
        self.rng = random.Random(seed)
        prompts.rng = self.rng
        self.builder = Builder(cur, prompts, timing, learner, self.rng, translate_partner=cfg.translate_partner)
        self.exposures: dict[str, list[str]] = {}
        self.support: dict[str, int] = {}
        self.dialogues_played: list[str] = []
        self.notes_played: list[str] = []
        self._in_dialogue = {i for d in cur.dialogues for i in d.required_items}
        self._notes_by_item: dict[str, list] = {}
        for n in cur.notes:
            for i in n.items:
                self._notes_by_item.setdefault(i, []).append(n)

    # ------------------------------------------------------------------ ladder

    def ladder(self, item: Item) -> list[str]:
        recombinable = (
            item.kind in ("construction", "transform")
            or (item.kind == "vocab" and any(t in c.slots.values() for c in self.cur.items if c.kind == "construction" for t in item.tags))
        )
        return ladder_for(
            item.kind,
            has_situation=bool(item.situation),
            in_dialogue=item.id in self._in_dialogue,
            recombinable=recombinable,
            word_count=item.word_count,
        )

    # --------------------------------------------------------------- selection

    def select_new(self, count: int, exclude: set[str] | None = None) -> list[Item]:
        chosen: list[Item] = []
        chosen_ids: set[str] = set(exclude or ())

        def ready(it: Item) -> bool:
            return all(self.learner.knows(p) or p in chosen_ids for p in it.prereqs)

        def known_fills(tag: str) -> int:
            return sum(1 for i in self.cur.items_with_tag(tag) if self.learner.knows(i.id) or i.id in chosen_ids)

        pool = [i for i in self.cur.items if not self.learner.has_met(i.id) and i.id not in chosen_ids]
        if self.cfg.topics:
            preferred = [i for i in pool if set(i.topics) & set(self.cfg.topics)]
            rest = [i for i in pool if i not in preferred]
            pool = preferred + rest
        # walk in order, but a not-yet-ready item is skipped rather than blocking
        progress = True
        while len(chosen) < count and progress:
            progress = False
            for it in pool:
                if it.id in chosen_ids or not ready(it):
                    continue
                chosen.append(it)
                chosen_ids.add(it.id)
                progress = True
                # a pattern is only teachable with two things to put in its slot
                if it.kind == "construction":
                    for tag in it.slots.values():
                        if known_fills(tag) < 2:
                            extra = next((f for f in pool if tag in f.tags and f.id not in chosen_ids), None)
                            if extra is not None:
                                chosen.append(extra)
                                chosen_ids.add(extra.id)
                if len(chosen) >= count:
                    break
        return chosen

    def select_reviews(self) -> list[Item]:
        met = [self.cur.by_id[i] for i in self.learner.items if i in self.cur.by_id]
        scored = [(self.learner.review_priority(i.id, self.today), i) for i in met]
        scored.sort(key=lambda t: (-t[0], t[1].order))
        if self.cfg.topics:
            on_topic = [i for _, i in scored if set(i.topics) & set(self.cfg.topics)]
            off = [i for _, i in scored if i not in on_topic]
            # keep urgency first, but let topic pull ties forward
            return sorted(on_topic + off, key=lambda i: -self.learner.review_priority(i.id, self.today) - (0.4 if i in on_topic else 0))
        return [i for _, i in scored]

    def review_stage(self, item: Item) -> str:
        st = self.learner.items[item.id]
        ladder = self.ladder(item)
        cur = st.stage if st.stage in ladder else ladder[min(1, len(ladder) - 1)]
        # climb when the memory looks strong; otherwise repeat the current stage
        if st.successes >= 2 and st.failures <= st.successes:
            return next_stage(ladder, cur)
        return cur if cur != "intro" else ladder[min(1, len(ladder) - 1)]

    def _second_pass(self, reviewed: list[str], recent) -> list[Item]:
        items = [self.cur.by_id[i] for i in reviewed if i in self.cur.by_id and i not in recent]
        items.sort(key=lambda i: -self.learner.review_priority(i.id, self.today))
        return items

    def _harder_than_today(self, item: Item) -> str:
        ladder = self.ladder(item)
        done = [s for s in self.exposures.get(item.id, []) if s != "intro"]
        top = max((stage_index(ladder, s) for s in done), default=0)
        return ladder[min(top + 1, len(ladder) - 1)]

    # ------------------------------------------------------------------ notes

    def _note_budget_left(self) -> bool:
        limit = self.cfg.max_notes if self.cfg.max_notes is not None else max(1, int(self.cfg.minutes // 12))
        return len(self.notes_played) < limit

    def _pick_note(self, related: list[str] | None) -> object | None:
        """Least-heard unplayed note, related to ``related`` items if given, else any."""
        if related:
            pool = [n for i in related for n in self._notes_by_item.get(i, [])]
        else:
            pool = list(self.cur.notes)
        pool = [n for n in pool if n.id not in self.notes_played]
        heard = self.learner.notes_heard
        if any(heard.get(n.id, 0) == 0 for n in self.cur.notes):
            pool = [n for n in pool if heard.get(n.id, 0) == 0]  # never repeat while unheard notes remain
        if not pool:
            return None
        least = min(heard.get(n.id, 0) for n in pool)
        pool = [n for n in pool if heard.get(n.id, 0) == least]
        return self.rng.choice(pool)

    def _maybe_note(self, sc: Script, related: list[str], remaining: float) -> None:
        if not self._note_budget_left() or remaining < 40 or self.rng.random() > self.cfg.note_chance:
            return
        note = self._pick_note(related)
        if note is None:
            return
        self.builder.note(sc, note)
        self.notes_played.append(note.id)

    def below_dialogue(self, item: Item) -> str:
        """The hardest non-dialogue stage for an item (used when no dialogue fits right now)."""
        ladder = [s for s in self.ladder(item) if s != "dialogue"]
        return ladder[-1] if ladder else "meaning"

    def eligible_dialogue(self, prefer_item: Item | None = None) -> Dialogue | None:
        limit = self.cfg.max_dialogues if self.cfg.max_dialogues is not None else max(2, int(self.cfg.minutes // 10))
        if len(self.dialogues_played) >= limit:
            return None
        cands = []
        for d in self.cur.dialogues:
            if d.id in self.dialogues_played:
                continue
            if not all(self.learner.knows(i) or i in self.builder.in_lesson for i in d.required_items):
                continue
            if prefer_item and prefer_item.id not in d.required_items:
                continue
            times = self.learner.dialogues_done.get(d.id, 0)
            cands.append((times, d))
        if not cands:
            return None
        cands.sort(key=lambda t: t[0])
        least = [d for t, d in cands if t == cands[0][0]]
        return self.rng.choice(least)

    # -------------------------------------------------------------- recording

    def _record(self, primary: list[str], stage: str, all_ids: list[str]) -> None:
        for i in primary:
            self.exposures.setdefault(i, []).append(stage)
        for i in all_ids:
            if i not in primary:
                self.support[i] = self.support.get(i, 0) + 1

    # ------------------------------------------------------------------ build

    def build(self) -> Script:
        cfg = self.cfg
        n = self.learner.next_lesson_number()
        budget = cfg.minutes * 60.0
        sc = Script(n, f"Lesson {n}", self.cur.target_lang, self.cur.known_lang)
        b = self.builder
        b.opening(sc, n, first_lesson=(n == 1))

        new_queue = deque(self.select_new(cfg.resolved_new_items()))
        reviews = deque(self.select_reviews())
        pending: list[_Pending] = []
        seq = 0
        introduced: list[Item] = []
        recent: deque[str] = deque(maxlen=2)  # item ids of the last exercises
        recent_topics: deque[str] = deque(maxlen=2)
        idx = 0
        last_intro = -cfg.intro_gap
        since_dialogue = 0
        # time kept for the closing block: one recall per new item (~14 s) plus the announcement
        closing_reserve = min(budget * cfg.closing_share, 8 + 14 * len(new_queue))
        need_for_new = min(cfg.min_time_for_new_item, budget * 0.6)  # short lessons still get something new
        reviews_used: list[str] = []
        passes = 1

        def touch(item: Item) -> None:
            recent.append(item.id)
            if item.topics:
                recent_topics.append(item.topics[0])

        def do_intro(item: Item) -> None:
            nonlocal last_intro, seq
            ex = b.intro(sc, item)
            b.in_lesson.add(item.id)
            introduced.append(item)
            self._record([item.id], "intro", ex.item_ids)
            touch(item)
            last_intro = idx
            ladder = self.ladder(item)
            due_at = idx
            for k, gap in enumerate(cfg.reactivation_gaps):
                due_at += gap
                stage = ladder[min(k + 1, len(ladder) - 1)]
                seq += 1
                heapq.heappush(pending, _Pending(due_at, seq, item, stage))

        def do_recall(item: Item, stage: str) -> None:
            nonlocal since_dialogue
            if stage == "dialogue":
                dlg = self.eligible_dialogue(prefer_item=item) if since_dialogue >= cfg.dialogue_every // 2 else None
                if dlg is not None:
                    self._play_dialogue(sc, dlg)
                    since_dialogue = 0
                    touch(item)
                    return
                stage = self.below_dialogue(item)
            ex = b.recall(sc, item, stage)
            self._record([item.id], ex.stage or stage, ex.item_ids)
            touch(item)

        while sc.total_duration < budget - closing_reserve:
            remaining = budget - closing_reserve - sc.total_duration
            due = [p for p in pending if p.due <= idx]
            due.sort()
            acted = False

            # 1. a scheduled reactivation that is due (but never the item we just did)
            for p in due:
                if p.item.id in recent:
                    continue
                pending.remove(p)
                heapq.heapify(pending)
                do_recall(p.item, p.stage)
                acted = True
                break

            # 2. introduce something new
            if not acted and new_queue and idx - last_intro >= cfg.intro_gap and remaining >= need_for_new:
                do_intro(new_queue.popleft())
                acted = True

            # 3. a dialogue, now and then, when the learner knows enough
            if not acted and since_dialogue >= cfg.dialogue_every:
                dlg = self.eligible_dialogue()
                if dlg is not None:
                    self._play_dialogue(sc, dlg)
                    since_dialogue = 0
                    acted = True

            # 4. review older material, interleaving topics
            if not acted and reviews:
                pick = None
                for cand in list(reviews):
                    if cand.id in recent:
                        continue
                    if cand.topics and cand.topics[0] in recent_topics and len(reviews) > 2:
                        continue
                    pick = cand
                    break
                if pick is None:
                    pick = next((c for c in reviews if c.id not in recent), None)
                if pick is not None:
                    reviews.remove(pick)
                    stage = self.review_stage(pick) if passes == 1 else self._harder_than_today(pick)
                    do_recall(pick, stage)
                    if pick.id not in reviews_used:
                        reviews_used.append(pick.id)
                    # a second, harder touch later in the lesson for weak or climbing items
                    st = self.learner.items[pick.id]
                    ladder = self.ladder(pick)
                    if stage_index(ladder, stage) < len(ladder) - 1 and (st.failures > 0 or self.rng.random() < 0.5):
                        seq += 1
                        heapq.heappush(pending, _Pending(idx + self.rng.randint(5, 9), seq, pick, next_stage(ladder, stage)))
                    acted = True

            # 5. nothing else fits here (typically the first lessons, with nothing to review):
            #    introduce early, else pull the next reactivation of a *different* item early,
            #    else take an extra new item, else accept a repeat, else stop.
            if not acted:
                candidate = next((p for p in sorted(pending) if p.item.id not in recent), None)
                can_intro = idx - last_intro >= 1 and len(introduced) < cfg.resolved_max_new_items()
                if candidate is not None:
                    pending.remove(candidate)
                    heapq.heapify(pending)
                    do_recall(candidate.item, candidate.stage)
                elif new_queue and can_intro and remaining >= need_for_new * 0.6:
                    do_intro(new_queue.popleft())
                elif can_intro and remaining >= need_for_new and (more := self.select_new(1, exclude={i.id for i in introduced})):
                    do_intro(more[0])
                elif pending and sorted(pending)[0].item.id != (recent[-1] if recent else None):
                    p = heapq.heappop(pending)  # a repeat, but not of the very last exercise
                    do_recall(p.item, p.stage)
                elif self._note_budget_left() and remaining >= 40 and self._pick_note(None) is not None:
                    note = self._pick_note(None)
                    b.note(sc, note)  # nothing to practise right now: a cultural aside
                    self.notes_played.append(note.id)
                elif passes < cfg.max_review_passes and reviews_used:
                    # material ran out before the time did: a second pass over what was reviewed,
                    # most urgent first, each one step harder than earlier in this lesson
                    passes += 1
                    reviews = deque(self._second_pass(reviews_used, recent))
                    if not reviews:
                        break
                    continue
                else:
                    break  # only immediate repeats are left: end the lesson a little short
            idx += 1
            since_dialogue += 1
            if sc.exercises and sc.exercises[-1].kind not in ("note", "opening"):
                self._maybe_note(sc, sc.exercises[-1].item_ids, budget - closing_reserve - sc.total_duration)

        # at least one aside per lesson while unheard ones remain (a few seconds over target is fine)
        if not self.notes_played and self._note_budget_left():
            note = self._pick_note(None)
            if note is not None:
                b.note(sc, note)
                self.notes_played.append(note.id)

        # ---- closing block: end on success with today's new material -----
        if introduced:
            b.final_block_announce(sc)
            # any reactivation that never came due is folded into the closing recall
            order = sorted(introduced, key=lambda i: -i.difficulty)  # hardest first, easiest last
            for item in order:
                ladder = self.ladder(item)
                done = [s for s in self.exposures.get(item.id, []) if s != "intro"]
                top = max((stage_index(ladder, s) for s in done), default=0)
                stage = ladder[min(top + 1, len(ladder) - 1)]
                if stage == "dialogue":
                    stage = self.below_dialogue(item)
                ex = b.recall(sc, item, stage)
                self._record([item.id], ex.stage or stage, ex.item_ids)
        b.closing(sc, n)

        sc.retime()
        sc.meta = {
            "date": self.today.isoformat(),
            "config": {
                "minutes": cfg.minutes,
                "new_items": cfg.resolved_new_items(),
                "topics": cfg.topics,
                "seed": self.rng and cfg.seed,
                "level": self.timing.level,
            },
            "curriculum": self.cur.name,
            "new_items": [i.id for i in introduced],
            "reviewed_items": reviews_used,
            "due_at_start": self.learner.due_count(self.today),
            "due_not_fitted": [i.id for i in reviews if self.learner.review_priority(i.id, self.today) >= 1.0],
            "dialogues": list(self.dialogues_played),
            "notes": list(self.notes_played),
            "exposures": self.exposures,
            "support_exposures": self.support,
            "ladders": {i: self.ladder(self.cur.by_id[i]) for i in self.exposures if i in self.cur.by_id},
            "not_introduced": [i.id for i in new_queue],
        }
        return sc

    def _play_dialogue(self, sc: Script, dlg: Dialogue) -> None:
        """Dialogues grow: the first encounter plays a couple of turns, each later one adds a
        turn. Scaffolding fades on the same schedule (issue #26): translations and response
        cues are only there the first time, so later encounters ask for comprehension of the
        partner's actual line, not just recall of a cue."""
        times = self.learner.dialogues_done.get(dlg.id, 0)
        max_turns = min(len(dlg.turns), self.cfg.dialogue_first_turns + times)
        full = max_turns >= len(dlg.turns)
        ex = self.builder.dialogue(sc, dlg, replay=(times > 0 and full), max_turns=max_turns, assisted=(times == 0))
        primary = [t.expect for t in dlg.turns[:max_turns] if t.expect]
        self._record(primary, "dialogue", ex.item_ids)
        self.dialogues_played.append(dlg.id)


def apply_to_learner(sc: Script, learner: LearnerState, today: date, presume_success: bool = True) -> None:
    """Update the learner model from a built script's metadata."""
    learner.record_lesson(
        sc.lesson_number,
        sc.meta.get("exposures", {}),
        today,
        presume_success=presume_success,
        ladders=sc.meta.get("ladders", {}),
    )
    for d in sc.meta.get("dialogues", []):
        learner.dialogues_done[d] = learner.dialogues_done.get(d, 0) + 1
    for n in sc.meta.get("notes", []):
        learner.notes_heard[n] = learner.notes_heard.get(n, 0) + 1
    learner.lessons.append(
        {
            "number": sc.lesson_number,
            "date": today.isoformat(),
            "new_items": sc.meta.get("new_items", []),
            "reviewed_items": sc.meta.get("reviewed_items", []),
            "dialogues": sc.meta.get("dialogues", []),
            "duration_s": round(sc.total_duration, 1),
            "due_at_start": sc.meta.get("due_at_start", 0),
            "due_not_fitted": len(sc.meta.get("due_not_fitted", [])),
            "pace": sc.meta.get("config", {}).get("new_items"),
        }
    )
