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
    max_streak_relief_notes: int = 2  # extra notes beyond max_notes, only to break a drill streak no dialogue can
    note_chance: float = 0.7  # chance to play a related note right after its item
    note_repeat_gap: int = 20  # lessons before a heard aside may play again
    note_lookahead: int = 100  # filler may use an unheard note about an item this close ahead of what's met
    # when material runs out, review what was reviewed once more (harder); 1 ends the lesson short
    max_review_passes: int = 2
    closing_share: float = 0.12  # fraction of time reserved for the final review block
    max_new_items: int | None = None  # hard cap even when there is nothing to review (default: scales with minutes)
    min_time_for_new_item: float = 180.0  # seconds of budget needed to still introduce one
    capability_window: int = 15  # a construction this close after a 3rd slot filler is pulled ahead of it
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
        constructions = [c for c in self.cur.items if c.kind == "construction"]

        def met_fills(tag: str) -> int:
            return sum(1 for i in self.cur.items_with_tag(tag) if self.learner.has_met(i.id) or i.id in chosen_ids)

        def payoff(filler: Item) -> tuple[bool, Item | None]:
            """Capability-aware arcs: once a slot has two fillers, a third one just before its
            construction would be one more isolated word while the pattern that makes them all
            usable sits a few items on. Returns ``(hold, construction)``: the construction to
            teach now instead, if it is ready; else whether this filler should wait for it.

            Only a construction within ``capability_window`` items after the filler counts, and
            only one whose other prereqs are already met or chosen, so a hold never deadlocks."""
            for c in constructions:
                if not (0 < c.order - filler.order <= self.cfg.capability_window) or self.learner.knows(c.id):
                    continue
                if not any(tag in filler.tags for tag in c.slots.values()) or filler.id in c.prereqs:
                    continue
                if not all(self.learner.has_met(p) or p in chosen_ids for p in c.prereqs):
                    continue
                if not all(met_fills(tag) >= 2 for tag in c.slots.values()):
                    continue
                if c.id not in chosen_ids and not self.learner.has_met(c.id) and ready(c) and all(known_fills(t) >= 2 for t in c.slots.values()):
                    return False, c
                return True, None
            return False, None

        def slot_members(c: Item) -> set[str]:
            return {i.id for t in c.slots.values() for i in self.cur.items_with_tag(t)}

        def slot_tags(filler: Item) -> set[str]:
            return {t for t in filler.tags for c in constructions if t in c.slots.values()}

        def transfer_capped(filler: Item) -> bool:
            """Once a slot's construction has been met, its remaining fillers are transfer
            material: at most two of one slot per arc, never a homogeneous block of them."""
            for tag in slot_tags(filler):
                if any(self.learner.has_met(c.id) and tag in c.slots.values() for c in constructions):
                    if sum(1 for x in chosen if tag in x.tags and x.kind != "construction") >= 2:
                        return True
            return False

        # walk in order, but a not-yet-ready item is skipped rather than blocking
        progress = True
        while len(chosen) < count and progress:
            progress = False
            for it in pool:
                if it.id in chosen_ids or not ready(it):
                    continue
                if it.kind != "construction" and it.tags:
                    hold, target = payoff(it)
                    if hold or (target is None and transfer_capped(it)):
                        continue
                    if target is not None:
                        it = target  # the payoff construction goes in now; this filler waits
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
        # Don't end the arc between a slot's fillers and the nearby construction they unlock:
        # take the construction too if it is ready (one over ``count``), else drop the trailing
        # filler so it starts the next arc with its siblings and pattern.
        if chosen and chosen[-1].kind != "construction" and slot_tags(chosen[-1]):
            last = chosen[-1]
            nearby = [
                c
                for c in constructions
                if 0 < c.order - last.order <= self.cfg.capability_window
                and any(t in last.tags for t in c.slots.values())
                and c.id not in chosen_ids
                and not self.learner.has_met(c.id)
            ]
            if nearby:
                c = nearby[0]
                if ready(c) and all(known_fills(t) >= 2 for t in c.slots.values()):
                    chosen.append(c)
                    chosen_ids.add(c.id)
                elif len(chosen) > 1 and all(
                    self.learner.has_met(p) or p in chosen_ids or p in slot_members(c) for p in c.prereqs
                ):
                    # only when nothing else the pattern needs is missing, or the filler would
                    # be dropped from arc after arc
                    chosen.pop()
                    chosen_ids.discard(last.id)
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
        """The number of consecutive recalls at the end of the script. Recomputed each time:
        one loop iteration can append several exercises (a milestone and its discrimination)."""
        streak = 0
        for ex in reversed(sc.exercises):
            if ex.kind != "recall":
                break
            streak += 1
        return streak

    # ------------------------------------------------------------------ notes

    def _aside_played(self) -> bool:
        """Whether an ordinary (non-milestone) note has played this lesson."""
        return any(not self.cur.note_by_id[nid].milestone for nid in self.notes_played)

    def _note_budget_left(self) -> bool:
        """Rations ordinary asides; milestones neither draw on nor count against it."""
        limit = self.cfg.max_notes if self.cfg.max_notes is not None else max(1, int(self.cfg.minutes // 12))
        played_asides = sum(1 for nid in self.notes_played if not self.cur.note_by_id[nid].milestone)
        return played_asides < limit

    def _eligible_milestone(self, related: list[str]) -> object | None:
        """A due milestone related to ``related``: every one of its ``items`` met, or exposed
        this lesson (the learner state only updates after the lesson). Due, never a coin flip."""
        for i in related:
            for n in self._notes_by_item.get(i, []):
                if (
                    n.milestone
                    and self._note_available(n)
                    and n.id not in self.notes_played
                    and self.learner.notes_heard.get(n.id, 0) == 0
                    and all(self.learner.has_met(x) or x in self.exposures for x in n.items)
                ):
                    return n
        return None

    def _note_available(self, note) -> bool:
        """Everything the note recommends saying (``Note.requires``) is learned, or was
        introduced earlier in this lesson."""
        return all(self.learner.knows(i) or i in self.builder.in_lesson for i in note.requires)

    def _pick_note(self, related: list[str] | None) -> object | None:
        """An ordinary note to play: related to ``related`` items if given; as filler, one about
        material the learner has met, else about material coming up within ``note_lookahead``
        items. Unheard notes come first; a heard one may come back once ``note_repeat_gap``
        lessons have passed. An unheard note about distant material is never spent as filler:
        the only unrelated filler is a repeat, and only when nothing closer is left."""
        heard = self.learner.notes_heard
        now = self.learner.next_lesson_number()

        def rested(n) -> bool:
            last = self.learner.notes_last_heard.get(n.id)
            return heard.get(n.id, 0) == 0 or last is None or now - last >= self.cfg.note_repeat_gap

        def met(n) -> bool:  # a note with no items is general and always in context
            return not n.items or any(self.learner.has_met(i) or i in self.exposures for i in n.items)

        reached = max((self.cur.by_id[i].order for i in list(self.learner.items) + list(self.exposures) if i in self.cur.by_id), default=0)

        def near(n) -> bool:
            return any(i in self.cur.by_id and self.cur.by_id[i].order <= reached + self.cfg.note_lookahead for i in n.items)

        pool = [n for i in related for n in self._notes_by_item.get(i, [])] if related else list(self.cur.notes)
        pool = [n for n in pool if not n.milestone and n.id not in self.notes_played and self._note_available(n) and rested(n)]
        unheard = [n for n in pool if heard.get(n.id, 0) == 0]
        repeats = [n for n in pool if heard.get(n.id, 0) > 0]
        if related:
            tiers = [unheard, repeats]
        else:
            tiers = [[n for n in unheard if met(n)], [n for n in unheard if near(n)], [n for n in repeats if met(n)], repeats]
        for tier in tiers:
            if tier:
                least = min(heard.get(n.id, 0) for n in tier)
                return self.rng.choice([n for n in tier if heard.get(n.id, 0) == least])
        return None

    def _maybe_note(self, sc: Script, related: list[str], remaining: float) -> object | None:
        """Play a due milestone, else maybe a related aside. Returns the milestone, if one
        played, so ``build()`` can follow it with discrimination practice. A milestone skips
        the aside ration and ``note_chance``."""
        if remaining >= 40:
            milestone = self._eligible_milestone(related)
            if milestone is not None:
                self._play_note(sc, milestone)
                return milestone
        if not self._note_budget_left() or remaining < 40:
            return None
        if self.rng.random() > self.cfg.note_chance:
            return None
        note = self._pick_note(related)
        if note is not None:
            self._play_note(sc, note)
        return None

    def _play_note(self, sc: Script, note) -> None:
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
        drill_streak = 0  # consecutive isolated recalls, no dialogue/note/intro in between
        # time kept for the closing block: one recall per new item (~14 s) plus the announcement
        closing_reserve = min(budget * cfg.closing_share, 8 + 14 * len(new_queue))
        need_for_new = min(cfg.min_time_for_new_item, budget * 0.6)  # short lessons still get something new
        reviews_used: list[str] = []
        passes = 1
        streak_relief_notes_used = 0
        # An arc is the batch of items one ``select_new()`` call picked: the initial one, or a
        # fresh arc started in step 5. Each arc gets one connect() attempt of its own (step
        # 0b) once all ``arc_target`` items are introduced and ready for a situation.
        current_arc_id = 0
        arc_items: dict[int, list[Item]] = {}
        arc_target: dict[int, int] = {0: len(new_queue)}
        arc_connect_attempted: set[int] = set()
        # connect() history: pairs are never replayed, and item reuse is spread out
        connect_pairs_used: set[frozenset[str]] = set()
        connect_item_uses: dict[str, int] = {}

        def touch(item: Item) -> None:
            recent.append(item.id)
            if item.topics:
                recent_topics.append(item.topics[0])

        def do_intro(item: Item) -> None:
            nonlocal last_intro, seq
            # A milestone this item's prereqs complete plays before the intro: a construction's
            # intro speaks its worked example, which must not come before the note naming the
            # pattern. A loop, since the prereqs can complete more than one milestone.
            while (milestone := self._eligible_milestone(item.prereqs)) is not None:
                self._play_note(sc, milestone)
                do_discriminate(milestone)
            ex = b.intro(sc, item)
            b.in_lesson.add(item.id)
            introduced.append(item)
            arc_items.setdefault(current_arc_id, []).append(item)
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
                # An item introduced this lesson always tries its dialogue (its arc's connected
                # use); older review items keep the spacing between dialogues.
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
            """After a milestone names a pattern, recall two of its examples back to back from
            their own situations: notice, name, discriminate. Known ``transfer_items`` come
            first, so the pattern is applied to new words rather than replaying the same
            examples. An example whose situation isn't usable now (none authored, or a
            construction whose bound fill isn't available) is recalled from its meaning instead,
            so the contrast keeps two recalls whenever two other examples exist (#84). Excludes
            only the item just exercised, and always completes once the milestone has played."""
            nonlocal idx, since_dialogue
            just_touched = recent[-1] if recent else None
            known_transfer = [i for i in note.transfer_items if self.learner.has_met(i) or i in self.exposures]
            others = list(dict.fromkeys(i for i in known_transfer + note.items if i != just_touched and i in self.cur.by_id))
            by_situation = [i for i in others if b.situation_usable(self.cur.by_id[i])]
            by_meaning = [i for i in others if i not in by_situation]
            picks = [(i, "situation") for i in by_situation] + [(i, "meaning") for i in by_meaning]
            for item_id, stage in picks[:2]:
                do_recall(self.cur.by_id[item_id], stage)
                idx += 1
                since_dialogue += 1

        def _ready_for_situation(it: Item) -> bool:
            """Whether recording ``it`` at the situation stage now continues its climb rather
            than skipping stages it hasn't practised (a stage is never lowered afterwards): its
            current stage is at most one step short of ``situation``."""
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

        def _connect_pair(pool: list[Item], last_touched_id: str | None, anchor: set[str] | None = None, exchange_only: bool = False) -> list[Item] | None:
            """The pair from ``pool`` for connect(), never one already played this lesson.
            Preference: an authored bridge (in its authored order), then two items sharing a
            topic, then any pair; within a tier, the items least used in earlier connects.

            ``anchor`` requires one of the pair to come from it (an arc's own material);
            ``exchange_only`` allows authored bridges only. ``last_touched_id`` goes second in
            a non-bridge pair rather than repeating immediately. ``None`` if no pair is left."""
            seen: set[str] = set()
            valid: list[Item] = []
            for it in pool:
                if it.id in seen or not b.situation_usable(it) or not _ready_for_situation(it):
                    continue
                seen.add(it.id)
                valid.append(it)
            best: tuple | None = None
            for i, a in enumerate(valid):
                for j in range(i + 1, len(valid)):
                    b_ = valid[j]
                    if frozenset((a.id, b_.id)) in connect_pairs_used:
                        continue
                    if anchor is not None and a.id not in anchor and b_.id not in anchor:
                        continue
                    if b_.partner_cue and b_.partner_cue_after == a.id:
                        pair, tier = [a, b_], 0
                    elif a.partner_cue and a.partner_cue_after == b_.id:
                        pair, tier = [b_, a], 0
                    else:
                        if exchange_only:
                            continue
                        pair = [a, b_]
                        tier = 1 if a.topics and b_.topics and a.topics[0] == b_.topics[0] else 2
                    reuse = connect_item_uses.get(a.id, 0) + connect_item_uses.get(b_.id, 0)
                    key = (tier, reuse, i, j)
                    if best is None or key < best[0]:
                        best = (key, pair)
            if best is None:
                return None
            (tier, *_), pair = best
            if tier != 0 and pair[0].id == last_touched_id:
                pair = [pair[1], pair[0]]
            return pair

        def do_connect(prefer: list[Item] | None = None) -> bool:
            """One connect() exercise; ``False`` if no unused pair is left. ``prefer`` scopes it
            to an arc's items (default: this lesson's introductions). An authored exchange
            anchored in that scope comes first, then a pair from the scope alone, then a wider
            pair; for an arc, the wider pair must still include one of its items."""
            just_touched = recent[-1] if recent else None
            preferred = prefer if prefer is not None else introduced
            rest = [it for it in introduced if it not in preferred] + [self.cur.by_id[i] for i in self.learner.items if i in self.cur.by_id]
            scope = {it.id for it in preferred}
            candidates = _connect_pair(list(preferred) + rest, just_touched, scope, exchange_only=True) if scope else None
            if candidates is None:
                candidates = _connect_pair(list(preferred), just_touched)
            if candidates is None:
                anchor = scope if prefer is not None else None
                candidates = _connect_pair(list(preferred) + rest, just_touched, anchor)
                if candidates is None:
                    return False
            ex = b.connect(sc, candidates)
            connect_pairs_used.add(frozenset(i.id for i in candidates))
            for item in candidates:
                connect_item_uses[item.id] = connect_item_uses.get(item.id, 0) + 1
            self._record([i.id for i in candidates], "situation", ex.item_ids)
            for item in candidates:
                touch(item)
            return True

        while sc.total_duration < budget - closing_reserve:
            remaining = budget - closing_reserve - sc.total_duration
            due = [p for p in pending if p.due <= idx]
            due.sort()
            acted = False

            # 0. drill streak too high: break it with a dialogue, else a note, else a connect(),
            #    before anything that would be one more isolated recall (step 1 included).
            #    If none works, end the lesson rather than extend the streak.
            if drill_streak >= cfg.drill_streak_limit:
                dlg = self.eligible_dialogue()
                if dlg is not None:
                    self._play_dialogue(sc, dlg)
                    since_dialogue = 0
                    acted = True
                if not acted and remaining >= 40:
                    # the aside ration may be spent already; a small separate allowance
                    # (max_streak_relief_notes) keeps streak relief from becoming unlimited asides
                    ration_left = self._note_budget_left()
                    if ration_left or streak_relief_notes_used < cfg.max_streak_relief_notes:
                        note = self._pick_note(None)
                        if note is not None:
                            self._play_note(sc, note)
                            acted = True
                            if not ration_left:
                                streak_relief_notes_used += 1
                if not acted and remaining >= 40:
                    acted = do_connect()
                if not acted:
                    break

            # 0b. an arc's own connected-use moment, once every item of the arc is ready for a
            #     situation: an authored exchange if one fits, else a mixed review of its items.
            #     Scoped to that arc's items; attempted once even if it finds nothing.
            if not acted and remaining >= 40:
                ready_arc = next(
                    (
                        aid
                        for aid in arc_items
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
                    # a filler can come back with the construction it made teachable
                    new_queue.extend(more[1:])
                elif pending and sorted(pending)[0].item.id != (recent[-1] if recent else None):
                    p = heapq.heappop(pending)  # a repeat, but not of the very last exercise
                    do_recall(p.item, p.stage)
                elif self._note_budget_left() and remaining >= 40 and self._pick_note(None) is not None:
                    self._play_note(sc, self._pick_note(None))  # nothing to practise now: an aside
                elif reviews_used and not new_queue and remaining >= need_for_new and (
                    more := self.select_new(cfg.resolved_new_items(), exclude={i.id for i in introduced})
                ):
                    # A fresh arc of new material rather than a second review pass: the new-item
                    # cap bounds an arc, not the lesson. Only once the review pool ran dry (a
                    # first lesson still ends short on purpose) and the previous arc is fully
                    # introduced (a queued prereq would look ready to select_new). Consumes an
                    # idx tick like every other branch.
                    current_arc_id += 1
                    arc_target[current_arc_id] = len(more)
                    new_queue.extend(more[1:])
                    do_intro(more[0])
                    # the closing block recalls every introduced item: reserve for the new ones too
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
                self._play_note(sc, note)

        # ---- closing block: end on success with today's new material -----
        if introduced:
            b.final_block_announce(sc)
            # any reactivation that never came due is folded into the closing recall
            order = sorted(introduced, key=lambda i: -i.difficulty)  # hardest first, easiest last
            for item in order:
                stage = self._harder_than_today(item)
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
                "seed": cfg.seed,
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
            # partner interaction in the target language vs recombination practice
            "partner_exchanges": len(self.dialogues_played) + sum(1 for e in sc.exercises if e.kind == "connect" and e.stage == "exchange"),
            "recombinations": sum(1 for e in sc.exercises if e.kind == "connect" and e.stage != "exchange"),
            "heard_utterances": sorted(self.builder.heard),
            "bridges": [e.item_ids[1] for e in sc.exercises if e.kind == "connect" and e.stage == "exchange"],
        }
        return sc

    def _play_dialogue(self, sc: Script, dlg: Dialogue) -> None:
        """Dialogues grow by one turn per encounter; translations and cues are only there the
        first time, so later encounters ask for comprehension of the partner's line."""
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
        learner.notes_last_heard[n] = sc.lesson_number
    learner.heard_utterances.update(sc.meta.get("heard_utterances", []))
    for b in sc.meta.get("bridges", []):
        learner.bridges_heard[b] = learner.bridges_heard.get(b, 0) + 1
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
