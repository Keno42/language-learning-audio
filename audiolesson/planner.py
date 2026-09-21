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
    drill_streak_limit: int = 5  # consecutive isolated recalls before a dialogue is pulled forward
    dialogue_first_turns: int = 2  # turns played the first time; one more each later encounter
    max_dialogues: int | None = None  # per lesson (default: one per 10 minutes, at least 2)
    max_notes: int | None = None  # cultural asides per lesson (default: one per 12 minutes, at least 1)
    max_streak_relief_notes: int = 2  # extra notes beyond max_notes, only to break a drill streak
    # when no dialogue fits either (issue #44 point 1) — a small, separate, bounded allowance,
    # not an unlimited bypass of the ordinary ration
    note_chance: float = 0.7  # chance to play a related note right after its item
    max_review_passes: int = 2  # when material runs out, review what was reviewed once more (harder).
    # Set to 1 to end the lesson short instead (issue #34 point 5, other half) — see docs/HANDOFF.md
    # "Session 17" for why this isn't the default: measured 20-60% shorter lessons on a small
    # curriculum once even one review pass falls short of the target length.
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
            has_situation=item.has_situation,
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

    def _trailing_drill_streak(self, sc: Script) -> int:
        """Length of the run of consecutive ``"recall"`` exercises at the end of the
        transcript so far (issue #34 points 5-6). Recomputed from the actual sequence each
        time, not carried forward by one increment per ``build()`` loop iteration: a single
        iteration can append several exercises (a milestone note plus its discrimination
        recalls, via ``_maybe_note``/``do_discriminate``), and a note or dialogue partway
        through that sequence breaks the streak even though the iteration's *last* exercise
        is still a recall (owner review on #40)."""
        streak = 0
        for ex in reversed(sc.exercises):
            if ex.kind != "recall":
                break
            streak += 1
        return streak

    # ------------------------------------------------------------------ notes

    def _aside_played(self) -> bool:
        """Whether any *ordinary* (non-milestone) note has played this lesson. Milestones
        don't count — a milestone firing must not, by itself, satisfy "an aside already
        played" and suppress the end-of-lesson aside fallback below."""
        return any(not self.cur.note_by_id[nid].milestone for nid in self.notes_played)

    def _note_budget_left(self) -> bool:
        """Rations ordinary asides only. Milestones are curriculum events, not filler — they
        neither draw on this budget (``_maybe_note`` never calls this for one) nor shrink it
        for the asides that do, so however many milestones happen to fire in one lesson (there
        are two now: ``godur_gender`` and ``three_kinds_of_sorry``) never crowds out the
        cultural asides this budget exists to pace."""
        limit = self.cfg.max_notes if self.cfg.max_notes is not None else max(1, int(self.cfg.minutes // 12))
        played_asides = sum(1 for nid in self.notes_played if not self.cur.note_by_id[nid].milestone)
        return played_asides < limit

    def _eligible_milestone(self, related: list[str]) -> object | None:
        """A milestone note whose ``items`` have all been met, triggered by one of them
        having just been exercised. Never offered as generic filler (unlike ``_pick_note``,
        this only ever looks at ``related``) and never subject to ``note_chance`` — once its
        items are all met, it is due, not a coin flip.

        ``learner.has_met`` alone lags a lesson behind: a newly introduced item isn't
        persisted to ``LearnerState`` until ``apply_to_learner()`` runs after the whole
        lesson is built, so the lesson that teaches the final item of the three would
        otherwise not count it yet. ``self.exposures`` already tracks every item touched so
        far *this* lesson, so a met-or-exposed check makes the milestone fire on the very
        lesson its last example is introduced, not one lesson later."""
        for i in related:
            for n in self._notes_by_item.get(i, []):
                if (
                    n.milestone
                    and n.id not in self.notes_played
                    and self.learner.notes_heard.get(n.id, 0) == 0
                    and all(self.learner.has_met(x) or x in self.exposures for x in n.items)
                ):
                    return n
        return None

    def _pick_note(self, related: list[str] | None) -> object | None:
        """Least-heard unplayed non-milestone note, related to ``related`` items if given,
        else any. Milestone notes are never picked here — they only fire once eligible,
        via ``_eligible_milestone``."""
        if related:
            pool = [n for i in related for n in self._notes_by_item.get(i, [])]
        else:
            pool = list(self.cur.notes)
        pool = [n for n in pool if not n.milestone]
        pool = [n for n in pool if n.id not in self.notes_played]
        heard = self.learner.notes_heard
        # "unheard" only counts non-milestone notes here: an ineligible milestone note is
        # permanently unheard from this function's point of view (it never picks one), so
        # counting it would needlessly block repeats of ordinary notes that have all been heard.
        if any(heard.get(n.id, 0) == 0 for n in self.cur.notes if not n.milestone):
            pool = [n for n in pool if heard.get(n.id, 0) == 0]  # never repeat while unheard notes remain
        if not pool:
            return None
        least = min(heard.get(n.id, 0) for n in pool)
        pool = [n for n in pool if heard.get(n.id, 0) == least]
        return self.rng.choice(pool)

    def _maybe_note(self, sc: Script, related: list[str], remaining: float) -> object | None:
        """Returns the milestone note if one just played, so ``build()`` can immediately
        follow it with contrastive discrimination practice (issue #34 point 2) — never for an
        ordinary aside, which isn't a curriculum event to build on."""
        # A due milestone is a curriculum event, not an optional aside: it takes priority
        # over the ordinary note budget/rationing (``_note_budget_left()``) and the
        # ``note_chance`` roll, both checked below only for the non-milestone path. It still
        # needs the same minimum time left in the lesson to actually fit.
        if remaining >= 40:
            milestone = self._eligible_milestone(related)
            if milestone is not None:
                self.builder.note(sc, milestone)
                self.notes_played.append(milestone.id)
                return milestone
        if not self._note_budget_left() or remaining < 40:
            return None
        if self.rng.random() > self.cfg.note_chance:
            return None
        note = self._pick_note(related)
        if note is None:
            return None
        self.builder.note(sc, note)
        self.notes_played.append(note.id)
        return None

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
        drill_streak = 0  # consecutive isolated recalls, no dialogue/note/intro in between
        # time kept for the closing block: one recall per new item (~14 s) plus the announcement
        closing_reserve = min(budget * cfg.closing_share, 8 + 14 * len(new_queue))
        need_for_new = min(cfg.min_time_for_new_item, budget * 0.6)  # short lessons still get something new
        reviews_used: list[str] = []
        passes = 1
        streak_relief_notes_used = 0
        # Per-arc connected-use bookkeeping (issue #44, owner review round 2 on #46): an arc
        # is the batch of items introduced together by one ``select_new()`` call — the initial
        # one below, or a later "fresh arc" pick (step 5). ``arc_items`` maps an arc's id to
        # its own items, populated lazily by ``do_intro`` the first time one of its items is
        # actually introduced (so an arc that never gets any items, e.g. nothing left to
        # teach, never shows up here at all); ``arc_order`` records creation order for the
        # "earliest unattempted arc" scan below. ``arc_target`` is each arc's intended item
        # count, fixed at the moment the arc is created (``len(new_queue)`` for the initial
        # arc, ``len(more)`` for a fresh one) — without it, the readiness check below could
        # fire the instant the *first* item of a still-filling arc got its first reactivation,
        # days before the arc's other items had even been introduced yet, and "recombine this
        # arc" would have only one real member to work with (confirmed: with ``intro_gap=3``
        # separating two items' own intros, the first item's first reactivation reliably landed
        # before the second item's intro). ``current_arc_id`` only advances at an explicit
        # fresh-arc start (see step 5) — every item introduced in between, whether via the
        # initial queue or step 2's ordinary draining of it, belongs to the same arc.
        current_arc_id = 0
        arc_items: dict[int, list[Item]] = {}
        arc_target: dict[int, int] = {0: len(new_queue)}
        arc_order: list[int] = []
        arc_connect_attempted: set[int] = set()

        def touch(item: Item) -> None:
            recent.append(item.id)
            if item.topics:
                recent_topics.append(item.topics[0])

        def do_intro(item: Item) -> None:
            nonlocal last_intro, seq
            ex = b.intro(sc, item)
            b.in_lesson.add(item.id)
            introduced.append(item)
            if current_arc_id not in arc_items:
                arc_items[current_arc_id] = []
                arc_order.append(current_arc_id)
            arc_items[current_arc_id].append(item)
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
                # An item introduced earlier *this lesson* reaching its own dialogue-stage
                # reactivation is that arc's connected-use moment (issue #44 point 2) — always
                # attempt it, not gated by since_dialogue's frequency spacing. That gate exists
                # to keep dialogues from clustering when several long-known review items happen
                # to cycle back to "dialogue" stage close together, not to skip a fresh arc's
                # one chance at connected use within its own reactivation schedule — without
                # this, an item whose schedule reached "dialogue" before since_dialogue had
                # built back up silently fell back to below_dialogue() and, since "dialogue"
                # is always the last ladder stage, never got a connected-use attempt at all
                # this lesson. An older item cycling back via ordinary review keeps the
                # existing spacing gate.
                fresh_arc_item = any(i.id == item.id for i in introduced)
                dlg = self.eligible_dialogue(prefer_item=item) if (fresh_arc_item or since_dialogue >= cfg.dialogue_every // 2) else None
                if dlg is not None:
                    self._play_dialogue(sc, dlg)
                    since_dialogue = 0
                    touch(item)
                    return
                stage = self.below_dialogue(item)
            ex = b.recall(sc, item, stage)
            self._record([item.id], ex.stage or stage, ex.item_ids)
            touch(item)

        def do_discriminate(note) -> None:
            """Right after a milestone names a pattern, switch between two of its own
            already-known examples in quick succession — "notice, name, discriminate"
            (issue #34 point 2) — reusing each item's own ``situation`` rather than writing
            new contrastive content: the three phrases behind ``godur_gender`` already have
            distinct situations (bakery morning / bedtime / evening restaurant), so replaying
            two of them back to back *is* the discrimination exercise.

            Excludes only the single item just exercised (whatever triggered the milestone),
            not the whole ``recent`` de-dup deque used elsewhere — with three items, that still
            guarantees two *different* ones to switch between, which is the actual "discriminate"
            requirement; excluding all of ``recent`` could leave only one. And once a milestone
            has committed to firing (already past its own ``remaining >= 40`` check), the
            discrimination block is treated as part of that same instructional unit and always
            completes — a lesson running a little over its nominal target is preferable to a
            milestone with no follow-up practice at all."""
            nonlocal idx, since_dialogue
            just_touched = recent[-1] if recent else None
            others = [i for i in note.items if i != just_touched]
            candidates = [self.cur.by_id[i] for i in others if i in self.cur.by_id and self.cur.by_id[i].has_situation]
            for item in candidates[:2]:
                do_recall(item, "situation")
                idx += 1
                since_dialogue += 1

        def _ready_for_situation(it: Item) -> bool:
            """True if recording ``it`` at ``"situation"`` stage right now continues its own
            natural climb up the ladder rather than skipping stages it hasn't earned yet
            (owner review round 3 on #46): ``do_connect()`` used to record *any* has-situation
            candidate at stage ``"situation"`` regardless of how far it had actually climbed —
            fine for a short item whose ladder goes straight from ``meaning`` to ``situation``,
            but a multi-word item's ladder also has ``cloze``/``hinted`` in between, and
            ``record_lesson()`` never lowers a stage, only raises it (``max(candidates, key=...
            stage_index)``), so one connect() exercise could jump such an item straight to
            ``situation``, permanently skipping stages it never actually practised. Allows the
            item at its current stage or one step short of ``situation`` (so the *next* natural
            step reaches it) — not further back than that."""
            ladder = self.ladder(it)
            if "situation" not in ladder:
                return False
            situation_idx = stage_index(ladder, "situation")
            if it.id in self.learner.items:
                st = self.learner.items[it.id]
                cur = st.stage if st.stage in ladder else ladder[0]
            else:
                done = [s for s in self.exposures.get(it.id, []) if s != "intro"]
                cur = done[-1] if done and done[-1] in ladder else ladder[0]
            return stage_index(ladder, cur) >= situation_idx - 1

        def _connect_pair(pool: list[Item], last_touched_id: str | None) -> list[Item] | None:
            """The two distinct, situation-ready items in ``pool`` to recombine together,
            preferring a pair that shares a topic — so the connected moment reads as one
            coherent scene rather than two items that merely happen to both be known (owner
            review round 2 on #46: a "leaving a shop" situation paired with a "raising a
            glass" one read as unrelated flashcards). Falls back to any two distinct items if
            no topic pair exists. Returns ``None`` if ``pool`` doesn't have two eligible items.

            If one of the two chosen items is ``last_touched_id``, it's ordered *second*, not
            excluded outright — excluding it entirely (as an earlier version of this did) made
            a fully practiced 2-item arc's own connected-use moment impossible to draw purely
            from its own material: the arc's last-touched item is typically exactly the one
            whose own reactivation just completed the arc's readiness check, so excluding it
            left only one real member and forced a fallback to unrelated material instead —
            precisely the cross-arc contamination this whole scoping exists to prevent.
            Ordering it second still avoids the jarring effect an *immediate* repeat would
            have (the actual reason for the exclusion, shared with ``do_discriminate``)."""
            seen: set[str] = set()
            valid: list[Item] = []
            for it in pool:
                if it.id in seen or not it.has_situation or not _ready_for_situation(it):
                    continue
                seen.add(it.id)
                valid.append(it)
            if len(valid) < 2:
                return None
            by_topic: dict[str, list[Item]] = {}
            for it in valid:
                if it.topics:
                    by_topic.setdefault(it.topics[0], []).append(it)
            pair = next((group[:2] for group in by_topic.values() if len(group) >= 2), None) or valid[:2]
            if pair[0].id == last_touched_id:
                pair = [pair[1], pair[0]]
            return pair

        def do_connect(prefer: list[Item] | None = None) -> bool:
            """Recombine two already-known items into one connected exchange (issue #44):
            the fallback for "connected use" when no authored dialogue exists for the
            current material, and a real third option for a drill streak with nowhere else
            to go — not another isolated recall. ``prefer`` scopes this to a specific arc's
            own material (see the per-arc step below); without it, this lesson's own
            ``introduced`` items are preferred, falling back to any other already-known item.
            Candidates are drawn from ``prefer`` (or ``introduced``) *alone* first — only
            widening to the rest of the pool if that scope alone can't supply two eligible
            items — so a later arc's connected-use guarantee can never be quietly satisfied
            by an earlier arc's material, or by unrelated review items, when its own is
            enough. Returns ``False`` if no two eligible items exist anywhere."""
            just_touched = recent[-1] if recent else None
            preferred = prefer if prefer is not None else introduced
            candidates = _connect_pair(list(preferred), just_touched)
            if candidates is None:
                rest = [it for it in introduced if it not in preferred] + [
                    self.cur.by_id[i] for i in self.learner.items if i in self.cur.by_id
                ]
                candidates = _connect_pair(list(preferred) + rest, just_touched)
                if candidates is None:
                    return False
            ex = b.connect(sc, candidates)
            self._record([i.id for i in candidates], "situation", ex.item_ids)
            for item in candidates:
                touch(item)
            return True

        while sc.total_duration < budget - closing_reserve:
            remaining = budget - closing_reserve - sc.total_duration
            due = [p for p in pending if p.due <= idx]
            due.sort()
            acted = False

            # 0. drill streak too high: break up the run with a dialogue, else a note, else a
            #    recombination of known items, before any branch below that would emit another
            #    isolated recall — including step 1's due reactivation, which does not by
            #    itself break the streak the way an intro or dialogue does. This must come
            #    first: a due reactivation is still an isolated recall, so running it ahead of
            #    this check let the streak continue uninterrupted through step 1 every time one
            #    happened to be due (owner review on #41 — issue #34 point 6). If nothing on
            #    this whole ladder works, stop the lesson rather than let the streak continue
            #    unbounded (owner review on #46 — issue #44's own acceptance criteria: this
            #    must never silently fall through to "one more isolated recall").
            streak_triggered = drill_streak >= cfg.drill_streak_limit
            if streak_triggered:
                dlg = self.eligible_dialogue()
                if dlg is not None:
                    self._play_dialogue(sc, dlg)
                    since_dialogue = 0
                    acted = True
                if not acted and remaining >= 40:
                    # no dialogue fits either: a note is a varied activity, not another
                    # flashcard drill. `_note_budget_left()` alone isn't enough of a gate here
                    # (issue #44 point 1): that budget exists to ration *optional* asides, at as
                    # little as 1 per lesson for a short lesson (`max(1, minutes // 12)`) —
                    # easily spent by the very first ordinary aside roll, long before the streak
                    # ever needs it. A real generated lesson hit exactly this: the streak
                    # trigger fired repeatedly (climbing to 15 unbroken recalls) while
                    # `_note_budget_left()` stayed `False` the entire time, because the lesson's
                    # one allowed aside had already played early on. But an unconditional bypass
                    # overcorrects — measured as high as 19 asides in one 30-minute lesson during
                    # `auto` pace escalation, turning rationing off entirely and recreating
                    # issue #21's original "asides feel like non-sequiturs" complaint from the
                    # other direction. `max_streak_relief_notes` (default 2) is a small, separate
                    # allowance spent only once the ordinary ration is already exhausted — not
                    # unlimited, but enough to break up a couple of real monotony episodes in one
                    # lesson without turning it into a string of asides.
                    ration_left = self._note_budget_left()
                    if ration_left or streak_relief_notes_used < cfg.max_streak_relief_notes:
                        note = self._pick_note(None)
                        if note is not None:
                            b.note(sc, note)
                            self.notes_played.append(note.id)
                            acted = True
                            if not ration_left:
                                streak_relief_notes_used += 1
                if not acted and remaining >= 40:
                    # no dialogue and no note either: recombine two already-known items
                    # instead (issue #44 point 2 — this is also the fallback when a whole arc's
                    # items were never wired into any authored dialogue at all, so a plain
                    # eligible_dialogue() check could never have found anything to play for
                    # them in the first place; recombination doesn't depend on authored
                    # dialogue content existing).
                    acted = do_connect()
                if not acted:
                    # Dialogue, note (ration and relief), and recombination all failed — there
                    # is genuinely nothing left but another isolated recall. Stop the lesson
                    # here rather than let the streak continue unbounded: issue #44's
                    # acceptance criteria explicitly rule out silent fallthrough to "continued
                    # isolated recall" as the outcome of a maxed-out drill streak. This is rare
                    # in practice (it needs no eligible dialogue, an exhausted or absent note
                    # supply, and fewer than two already-known items with a situation cue,
                    # all at once) but must be a real option, not just a theoretical one.
                    break

            # 0b. an arc's own connected-use moment — not just a side effect of the drill-streak
            #     breaker above (issue #44, owner review round 2 on #46: the first cut only ever
            #     reached ``do_connect()`` when a streak had already run past its limit, so an
            #     arc practiced at a normal pace — never triggering the streak breaker — could
            #     finish, and the lesson could move on to another arc or end, with no connected-
            #     use attempt at all). Once every item introduced in an arc is itself individually
            #     ready for a "situation" exposure — ``_ready_for_situation()``, not merely "has
            #     had some touch beyond intro" (owner review round 3: an item still climbing
            #     cloze/hinted isn't ready yet, and the arc's own readiness check used to be
            #     looser than the per-item gate ``_connect_pair`` now enforces, so an arc could be
            #     judged "ready" before any of its items actually were, and its guaranteed
            #     connect() attempt would simply find nothing eligible in its own material) —
            #     that arc gets one deliberate attempt — scoped to its own ``arc_items``
            #     specifically, not ``introduced`` as a whole, so a later arc's guarantee can't be
            #     quietly satisfied by an earlier arc's material (an earlier version of this fix
            #     pulled from whatever had been introduced so far, in intro order, so a later
            #     arc's connected use could end up reusing an earlier arc's items instead of its
            #     own). Marked "attempted" whether or not it actually finds two eligible items, so
            #     a genuinely thin arc isn't retried forever.
            if not acted and remaining >= 40:
                ready_arc = next(
                    (
                        aid
                        for aid in arc_order
                        if aid not in arc_connect_attempted
                        and len(arc_items[aid]) >= arc_target.get(aid, 0)
                        and all(_ready_for_situation(it) for it in arc_items[aid])
                    ),
                    None,
                )
                if ready_arc is not None:
                    if do_connect(prefer=arc_items[ready_arc]):
                        acted = True
                    arc_connect_attempted.add(ready_arc)

            # 1. a scheduled reactivation that is due (but never the item we just did)
            if not acted:
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

            # 3. a dialogue, now and then, when the learner knows enough — pulled forward,
            #    ahead of its usual periodic schedule (the drill-streak trigger is handled by
            #    step 0 above, before it can be preempted by a due reactivation)
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
                elif reviews_used and not new_queue and remaining >= need_for_new and (
                    more := self.select_new(cfg.resolved_new_items(), exclude={i.id for i in introduced})
                ):
                    # Gated on reviews_used (this lesson actually reviewed something and ran the
                    # pool dry) so a genuinely first lesson — no review history at all, reviews_used
                    # stays empty the whole time — still ends short on purpose rather than ballooning
                    # into an unbounded stack of new items just because time remains; that pacing
                    # guarantee (issue #16/session 3) is deliberate and this must not defeat it.
                    # Gated on ``not new_queue`` too: only start a fresh arc once the previous one
                    # has been fully introduced, never while it's still queued — with items still
                    # queued (not yet in ``introduced``), a construction's slot-filler prereq sitting
                    # unintroduced in that queue would look "ready" to a fresh select_new call
                    # (whose readiness check only trusts ``introduced``, correctly, not the queue),
                    # so a second call could return an item that jumps ahead of its own prereq —
                    # caught by test_prerequisites_respected.
                    #
                    # arc 1 is fully spent — its own reactivations are done, nothing else is due,
                    # no note fits — but substantial time remains and the curriculum has more to
                    # teach. Prefer a fresh small arc of new material over padding with a second
                    # pass of what this same lesson already reviewed (owner reframing of #34
                    # point 5/6: the new-item cap should bound *an arc*, not the whole lesson —
                    # a real lesson hit this exactly, stopping ~11 minutes short of a 30-minute
                    # request with plenty of curriculum left, solely because every fallback tier
                    # was independently capped). `can_intro`'s original cap is deliberately left
                    # alone — only this explicit, budget-gated path can start a new arc. Introduce
                    # the first item now (like the single-extra-item branch above) and queue the
                    # rest for step 2 to drain at the normal pace — no ``continue`` here: this
                    # must consume an ``idx`` tick like every other branch, or a lesson where
                    # ``intro_gap`` isn't yet satisfied would re-enter this branch at the same
                    # ``idx`` forever without ever making progress.
                    current_arc_id += 1  # a fresh arc — its own connected-use guarantee (step 0b)
                    arc_target[current_arc_id] = len(more)
                    new_queue.extend(more[1:])
                    do_intro(more[0])
                    # the closing block recalls every introduced item, so a new arc needs more
                    # closing time reserved than arc 1 alone budgeted for — recomputed the same
                    # way the initial reserve was, over the now-larger total.
                    closing_reserve = min(budget * cfg.closing_share, 8 + 14 * (len(introduced) + len(new_queue)))
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
                milestone = self._maybe_note(sc, sc.exercises[-1].item_ids, budget - closing_reserve - sc.total_duration)
                if milestone is not None:
                    do_discriminate(milestone)
            drill_streak = self._trailing_drill_streak(sc)

        # at least one aside per lesson while unheard ones remain (a few seconds over target is fine)
        if not self._aside_played() and self._note_budget_left():
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
