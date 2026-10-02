"""Lesson planner: decides what to practise, in what order, at which stage.

Principles it enforces (see README "How a lesson is built"):
- a few new items, each reactivated at expanding gaps within the lesson
- reviews of older material interleaved between them
- generative recombination and dialogues once enough is known
- a closing block that ends on successful recall of today's material
"""

from __future__ import annotations

import heapq
import math
import random
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import date, timedelta

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
    # a dialogue already heard in full rests this many lessons before it is replayed: with
    # few dialogues eligible, the same full dialogue otherwise played in every lesson
    # (simulated lessons 7-12). One still growing a turn per encounter does not wait.
    dialogue_rest_lessons: int = 3
    max_dialogues: int | None = None  # per lesson (default: one per 10 minutes, at least 2)
    # Issue #149 step 3 (lesson 13: 23.6 of 30 minutes, the last 5 repeating today's items): with
    # nothing else left, a dialogue lacking one or two required items is played as listening
    # (its scene carries the meaning, H8). Those items are heard, not learned: never recorded,
    # never asked in the review. At most this many per lesson, each resting
    # ``listening_rest_lessons`` lessons. 0 reproduces the earlier planner.
    # Issue #149 (lesson 13 feedback: parts of phrases the learner can say came back as single
    # words): such a part is heard inside an easy sentence instead of being introduced alone;
    # the review decides whether it counts as learned. False reproduces the earlier planner.
    embed_parts: bool = True
    max_listening_dialogues: int = 2
    listening_missing_max: int = 2
    listening_rest_lessons: int = 6
    max_notes: int | None = None  # cultural asides per lesson (default: one per 12 minutes, at least 1)
    max_reactive_milestones: int = 2  # milestones fired after their item, per lesson; more wait for the next one
    max_streak_relief_notes: int = 2  # extra notes beyond max_notes, only to break a drill streak no dialogue can
    # every note in a lesson — milestones, asides, streak relief — together (default: one per
    # 10 minutes, at least 2). Milestones keep their own cap and are never blocked by this;
    # asides only play while it has room (lesson 8 feedback: six notes in 28 minutes)
    max_notes_total: int | None = None
    note_chance: float = 0.7  # chance to play a related note right after its item
    note_repeat_gap: int = 20  # lessons before a heard aside may play again
    note_lookahead: int = 100  # filler may use an unheard note about an item this close ahead of what's met
    # when material runs out, review what was reviewed once more (harder); 1 ends the lesson short
    max_review_passes: int = 2
    # Issue #151: an item counts as stable after this many recalls on or after a due date (a
    # recalled latest report counts as one) and ``stable_min_successes`` recalls in all, past
    # the hint stages, with no failure or hesitation in its last three lessons. Fillers (early
    # reviews, the second pass, extra touches, unanchored connect pairs, substitution frames)
    # leave stable items alone until they are due: já and hæ came back in every lesson,
    # interval unchanged, although they were reported as recalled.
    stable_successes: int = 2
    stable_min_successes: int = 8
    # Issue #151: the time stable items no longer fill goes to substitution drills: a known
    # construction with fills in a sentence not heard this lesson, at most this often each
    substitutions_per_construction: int = 3
    # Issue #151: after that, before ending the lesson short, each of today's new items may be
    # recalled once more, at most this often
    consolidations_per_item: int = 2
    # Reviews are the items that are due, plus those due within this many days. The rest wait
    # for their date: spending spare time on them made the same well-known phrases come back
    # every lesson whatever their interval (issue #94). Spare time goes to new material first.
    review_ahead_days: int = 0
    # arcs of new items a lesson may hold while reviews remain; more only once every review
    # filler is used up. The first arc takes new_items, a later one this share of it (rounded
    # up), keeping a lesson near the pace: 30 min, pace 6 → 6 + 3
    max_arcs: int = 2
    extra_arc_share: float = 0.5
    closing_share: float = 0.12  # fraction of time reserved for the final review block
    max_new_items: int | None = None  # hard cap even when there is nothing to review (default: scales with minutes)
    min_time_for_new_item: float = 180.0  # seconds of budget needed to still introduce one
    capability_window: int = 15  # a construction this close after a 3rd slot filler is pulled ahead of it
    presume_success: bool = True
    translate_partner: bool = True
    # Issue #149 (step 1a, G11): an item the learner failed stays open until a later confirmed
    # recall. Every lesson practises up to ``max_open_items`` of them: first those that failed
    # in the last lesson, then the least recently practised, so a backlog comes round. The
    # practices fall at these fractions of the lesson's time before the closing block (by time,
    # not exercise counts: five practices 3-13 exercises apart bunched in the first 8 minutes),
    # interleaved between items. ``open_item_practice`` False reproduces the earlier planner.
    open_item_practice: bool = True
    max_open_items: int = 5
    open_item_times: list[float] = field(default_factory=lambda: [0.04, 0.27, 0.48, 0.68, 0.88])
    # the trip ordering (#132): item ids introduced before the rest, in this order (their
    # prereqs included by cando.priority_items); empty keeps curriculum order
    priority: list[str] = field(default_factory=list)
    # levers (#136), off by default; turned on per deployment, by hand (docs/LEVERS.md)
    late_unhinted_recall: bool = False  # the closing recall of a new item never gives a hint

    def resolved_max_new_items(self) -> int:
        """Extra new items may fill a lesson that has nothing to review (the first ones),
        but only a little beyond the pace — a short first lesson beats a 12-item dump."""
        if self.max_new_items is not None:
            return self.max_new_items
        return self.resolved_new_items() + 2

    def resolved_extra_arc_items(self, capped: bool = True) -> int:
        """A later arc's size: ``extra_arc_share`` of the pace, but (``capped``) never taking
        the lesson past ``new_items_ceiling`` — a pace of 10 plus half again was 15 new items
        in 30 minutes. Uncapped only as the last resort, when nothing else is left to do."""
        size = math.ceil(self.resolved_new_items() * self.extra_arc_share)
        if capped:
            size = min(size, max(0, self.new_items_ceiling() - self.resolved_new_items()))
        return size

    def new_items_ceiling(self) -> int:
        """New items a lesson takes while it has other work: about one per 3 minutes, the top
        of the 6–10 per 30 minutes that audio courses of this kind converge on (README)."""
        return max(self.resolved_new_items(), round(self.minutes / 3))

    def resolved_new_items(self) -> int:
        if self.new_items is not None:
            return max(0, self.new_items)
        return int(max(3, min(10, round(self.minutes / 5))))


_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


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
        self.dialogues_listened: list[str] = []
        self.embedded: list[str] = []  # parts heard inside a sentence this lesson (#149)
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

        pool = [
            i for i in self.cur.items
            if not self.learner.has_met(i.id) and i.id not in chosen_ids and i.id not in self.learner.embedded
        ]
        if self.cfg.topics:
            preferred = [i for i in pool if set(i.topics) & set(self.cfg.topics)]
            rest = [i for i in pool if i not in preferred]
            pool = preferred + rest
        if self.cfg.priority:  # the trip ordering wins over topics
            rank = {i: n for n, i in enumerate(self.cfg.priority)}
            first = sorted((i for i in pool if i.id in rank), key=lambda i: rank[i.id])
            pool = first + [i for i in pool if i.id not in rank]
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
        """The review queue: items due, or due within ``review_ahead_days``, most urgent first.
        Not-due items further off are left for ``select_early_reviews``, the last filler."""
        met = [self.cur.by_id[i] for i in self.learner.items if i in self.cur.by_id]
        horizon = self.today + timedelta(days=self.cfg.review_ahead_days)
        met = [i for i in met if not self.learner.items[i.id].due or date.fromisoformat(self.learner.items[i.id].due) <= horizon]
        return self._by_urgency(met)

    def select_early_reviews(self, exclude: set[str], rested_only: bool = True) -> list[Item]:
        """Not-due items for a lesson that has run out of everything else (due reviews, new
        material, the second pass), the longest ago practised first, so none comes back lesson
        after lesson (#94). ``rested_only``: only those last practised at least half their
        interval ago. Never a stable item (#151): it waits for its date."""
        out = [
            (self.learner.items[i.id].last_practiced, i.order, i)
            for i in self.cur.items
            if i.id in self.learner.items and i.id not in exclude and (not rested_only or self._rested(i.id)) and not self._stable(i)
        ]
        return [i for *_, i in sorted(out, key=lambda t: t[:2])]

    def _stable(self, item: Item) -> bool:
        """Issue #151: plainly known. See ``PlanConfig.stable_successes``."""
        st = self.learner.items.get(item.id)
        if st is None or st.stage in ("intro", "cloze", "hinted"):
            return False
        if any(h.get("ok") is False or h.get("outcome") in ("hesitated", "not_recalled") for h in st.history[-3:]):
            return False
        if st.successes < self.cfg.stable_min_successes:
            return False
        return st.durable_successes + (st.last_outcome == "recalled") >= self.cfg.stable_successes

    def _rested(self, item_id: str) -> bool:
        """Last practised at least half its interval ago (and not today)."""
        st = self.learner.items[item_id]
        if not st.last_practiced:
            return True
        since = (self.today - date.fromisoformat(st.last_practiced)).days
        return since >= max(1.0, st.interval_days / 2)

    def _may_review(self, item_id: str) -> bool:
        """Due, or rested enough to be practised early."""
        return self.learner.review_priority(item_id, self.today) >= 1.0 or self._rested(item_id)

    def _by_urgency(self, items: list[Item]) -> list[Item]:
        scored = [(self.learner.review_priority(i.id, self.today), i) for i in items]
        scored.sort(key=lambda t: (-t[0], t[1].order))
        if self.cfg.topics:
            on_topic = [i for _, i in scored if set(i.topics) & set(self.cfg.topics)]
            off = [i for _, i in scored if i not in on_topic]
            # keep urgency first, but let topic pull ties forward
            return sorted(on_topic + off, key=lambda i: -self.learner.review_priority(i.id, self.today) - (0.4 if i in on_topic else 0))
        return [i for _, i in scored]

    def _may_start_arc(self, arcs: int, early_tier: int, far_short: bool = True) -> bool:
        """Whether a fresh arc may start, with ``arcs`` already in the lesson: up to
        ``max_arcs`` while other work remains; once every review filler (the early reviews and
        the second pass) is used up, no limit, so a lesson with nothing else left fills its
        time with something new rather than ending far short (#34, #94). Only while it would
        end far short (``far_short``: under half its time used): since stable items no longer
        fill (#151), the fillers run out sooner, and a lesson at pace 3 took 13 new items."""
        return (early_tier >= 2 and far_short) or arcs < self.cfg.max_arcs

    def review_stage(self, item: Item) -> str:
        st = self.learner.items[item.id]
        ladder = self.ladder(item)
        cur = st.stage if st.stage in ladder else ladder[min(1, len(ladder) - 1)]
        # climb when the memory looks strong; otherwise repeat the current stage
        if st.successes >= 2 and st.failures <= st.successes:
            return next_stage(ladder, cur)
        return cur if cur != "intro" else ladder[min(1, len(ladder) - 1)]

    def _second_pass(self, reviewed: list[str], recent) -> list[Item]:
        """Today's reviews once more, harder; a stable item was reviewed once and is done (#151)."""
        items = [self.cur.by_id[i] for i in reviewed if i in self.cur.by_id and i not in recent and not self._stable(self.cur.by_id[i])]
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
        """Rations ordinary asides; milestones neither draw on nor count against it. Also
        closed once the lesson's total for every kind of note is used up."""
        limit = self.cfg.max_notes if self.cfg.max_notes is not None else max(1, int(self.cfg.minutes // 12))
        played_asides = sum(1 for nid in self.notes_played if not self.cur.note_by_id[nid].milestone)
        return played_asides < limit and self._total_notes_left()

    def _total_notes_left(self) -> bool:
        """Room under ``max_notes_total``, which counts milestones, asides and streak relief."""
        limit = self.cfg.max_notes_total if self.cfg.max_notes_total is not None else max(2, int(self.cfg.minutes // 10))
        return len(self.notes_played) < limit

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
        the aside ration and ``note_chance``; at most ``max_reactive_milestones`` fire this way
        per lesson, the rest wait for the next lesson."""
        fired = sum(1 for nid in self.notes_played if self.cur.note_by_id[nid].milestone)
        if remaining >= 40 and fired < self.cfg.max_reactive_milestones:
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

    def recombine_or_instead(self, item: Item) -> str:
        """Issue #105: recombine only when it can make a sentence not yet heard this lesson.
        Otherwise practise the item at the hardest stage it already reached today (or
        ``meaning``), so stages never go down within a lesson; if it already did recombine
        today, its situation when usable, else a meaning recall: never replay a line under a
        "make a sentence" prompt, but never drop the recall either. Repeating an item in a
        lesson is fine (owner, lesson 12 feedback): dropping it left new items unheard from
        the third minute to the end. "impossible" (no known fills) keeps the builder's own
        fallback."""
        if self.builder.recombine_status(item) != "heard":
            return "recombine"
        ladder = self.ladder(item)
        today = [s for s in self.exposures.get(item.id, []) if s in ladder and s != "intro"]
        instead = max(today + ["meaning"], key=lambda s: stage_index(ladder, s))
        if stage_index(ladder, instead) < stage_index(ladder, "recombine"):
            return instead
        if "situation" in ladder and stage_index(ladder, "situation") > stage_index(ladder, instead) and self.builder.situation_usable(item):
            return "situation"
        return "meaning"

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
            if self._dialogue_resting(d):
                continue
            times = self.learner.dialogues_done.get(d.id, 0)
            cands.append((times, d))
        if not cands:
            return None
        cands.sort(key=lambda t: t[0])
        least = [d for t, d in cands if t == cands[0][0]]
        return self.rng.choice(least)

    def embeddable(self, item: Item) -> bool:
        """Whether ``item`` is introduced inside an easy sentence, not on its own (#149, lesson 13
        feedback: «opið», «miða»… came back as single words long after the learner could say
        the phrase that holds them). A vocab word with a slot to go in (``embed`` finds the
        sentence) whose words sit inside another item the learner has met (and hasn't failed),
        or met earlier this lesson, and that wasn't embedded before. ``embed_parts=False``
        reproduces the earlier planner."""
        if not self.cfg.embed_parts or item.kind != "vocab" or not item.tags:
            return False
        if item.id in self.learner.embedded or item.id in self.learner.embed_failed or self.learner.has_met(item.id):
            return False
        words = [w.lower() for w in _WORD_RE.findall(item.target)]
        if not words:
            return False
        for whole in self.cur.items:
            if whole.id == item.id or whole.kind not in ("phrase", "vocab"):
                continue
            if not (whole.id in self.builder.in_lesson or (self.learner.has_met(whole.id) and not self.learner.is_open(whole.id))):
                continue
            ww = [w.lower() for w in _WORD_RE.findall(whole.target)]
            if len(ww) > len(words) and any(ww[k : k + len(words)] == words for k in range(len(ww) - len(words) + 1)):
                return True
        return False

    def listening_dialogue(self) -> tuple[Dialogue, set[str]] | None:
        """A dialogue to play as listening: one or two required items short (``listening_missing_max``),
        not played this lesson, not heard as listening within ``listening_rest_lessons``. The
        one with the fewest missing wins, then the one least often practised."""
        if len(self.dialogues_listened) >= self.cfg.max_listening_dialogues:
            return None
        now = self.learner.next_lesson_number()
        cands = []
        for d in self.cur.dialogues:
            if d.id in self.dialogues_played or d.id in self.dialogues_listened:
                continue
            missing = {i for i in d.required_items if not (self.learner.knows(i) or i in self.builder.in_lesson)}
            if not 1 <= len(missing) <= self.cfg.listening_missing_max:
                continue
            last = next((l["number"] for l in reversed(self.learner.lessons) if d.id in l.get("dialogues_listened", [])), None)
            if last is not None and now - last <= self.cfg.listening_rest_lessons:
                continue
            cands.append((len(missing), self.learner.dialogues_done.get(d.id, 0), d.id, d, missing))
        if not cands:
            return None
        best = min(c[:2] for c in cands)
        d, missing = self.rng.choice([(c[3], c[4]) for c in cands if c[:2] == best])
        return d, missing

    def _dialogue_resting(self, d: Dialogue) -> bool:
        """Heard in full at its last encounter, and that was fewer than
        ``dialogue_rest_lessons`` lessons ago."""
        times = self.learner.dialogues_done.get(d.id, 0)
        if not times or self.cfg.dialogue_first_turns + times - 1 < len(d.turns):
            return False  # new, or still growing
        last = next((l["number"] for l in reversed(self.learner.lessons) if d.id in l.get("dialogues", [])), None)
        return last is not None and self.learner.next_lesson_number() - last <= self.cfg.dialogue_rest_lessons

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
        open_ids = self.learner.open_items() if cfg.open_item_practice else []
        open_ids = [i for i in open_ids if i in self.cur.by_id]
        open_today = open_ids[: cfg.max_open_items]
        reviews = deque(i for i in self.select_reviews() if i.id not in open_today)
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
        early_ids: set[str] = set()  # not-due items taken as fillers (select_early_reviews)
        early_tier = 0  # 1: rested items taken, 2: any item taken (see select_early_reviews)
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

        open_timeline: list[tuple[float, int, Item, str]] = []

        def schedule_open(item: Item, k: int) -> None:
            """An open item (#149): practices at fractions of the lesson's time, each a step
            further up its ladder from the stage it stands at (a failure demoted it, and
            practice that isn't confirmed doesn't raise it)."""
            nonlocal seq
            ladder = self.ladder(item)
            st = self.learner.items[item.id]
            stage = st.stage if st.stage in ladder and st.stage != "intro" else ladder[min(1, len(ladder) - 1)]
            usable = budget - closing_reserve
            fractions = cfg.open_item_times
            for j, f in enumerate(fractions):
                # the items interleave across each interval (item k of n at k/n of the way to the
                # next fraction) instead of stacking: five practices in a row were a drill streak
                nxt = fractions[j + 1] if j + 1 < len(fractions) else 1.0
                seq += 1
                open_timeline.append((usable * (f + k * (nxt - f) / n_open), seq, item, stage))
                stage = next_stage(ladder, stage)

        def load_early(rested_only: bool) -> list[Item]:
            items = self.select_early_reviews(exclude=set(self.exposures), rested_only=rested_only)
            early_ids.update(i.id for i in items)
            return items

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
            if self.embeddable(item) and b.embed(sc, item) is not None:
                self.embedded.append(item.id)
                touch(item)
                last_intro = idx
                arc_target[current_arc_id] = max(0, arc_target.get(current_arc_id, 0) - 1)
                return
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
            if stage == "recombine":
                stage = self.recombine_or_instead(item)
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
                if connect_item_uses.get(it.id) and self._stable(it):
                    continue  # a stable item takes part in one connect a lesson (#151)
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

        def not_due_stable(it: Item) -> bool:
            return self._stable(it) and self.learner.review_priority(it.id, self.today) < 1.0

        substitutions: dict[str, int] = {}
        consolidations: dict[str, int] = {}

        def pick_consolidation() -> Item | None:
            """Issue #151: today's new item least practised so far (then the earliest
            introduced), not just exercised, under ``consolidations_per_item`` extra recalls."""
            cands = [
                it for it in introduced
                if it.id not in recent and consolidations.get(it.id, 0) < cfg.consolidations_per_item
            ]
            return min(cands, key=lambda it: len(self.exposures.get(it.id, [])), default=None)

        def continue_substitution() -> Item | None:
            """The construction of a substitution drill that was the last exercise, while it
            can make another sentence: a run stays in one frame (#151)."""
            last = sc.exercises[-1] if sc.exercises else None
            if last is None or last.kind != "generative" or not last.item_ids or last.item_ids[0] not in substitutions:
                return None
            c = self.cur.by_id[last.item_ids[0]]
            if substitutions[c.id] < cfg.substitutions_per_construction and b.recombine_status(c, met_fills=True) == "novel":
                return c
            return None

        def do_substitution(c: Item) -> None:
            substitutions[c.id] = substitutions.get(c.id, 0) + 1
            ex = b.recall(sc, c, "recombine", met_fills=True)
            self._record([c.id], ex.stage or "recombine", ex.item_ids)
            touch(c)

        def pick_substitution() -> Item | None:
            """Issue #151: a construction past its hint stages (met before, not failed; if
            stable, due or rested, as for early reviews) that can still make a sentence not
            heard this lesson, its slots filled with words met before, under
            ``substitutions_per_construction``. The one just drilled goes on while it can, so a
            run swaps words in one frame («Talar þú dönsku?» → «… japönsku?»); then
            constructions sharing a topic with today's new items, the least used, and
            curriculum order."""
            if (c := continue_substitution()) is not None:
                return c
            today_topics = {t for it in introduced for t in it.topics}
            best: tuple | None = None
            for c in self.cur.items:
                if c.kind != "construction" or c.id in recent:
                    continue
                if substitutions.get(c.id, 0) >= cfg.substitutions_per_construction:
                    continue
                st = self.learner.items.get(c.id)
                today = any(s not in ("intro", "hinted") for s in self.exposures.get(c.id, []))
                past_hints = st is not None and st.stage not in ("intro", "hinted") and st.last_outcome != "not_recalled"
                if not (today or past_hints):
                    continue
                if not today and self._stable(c) and not self._may_review(c.id):
                    continue  # a stable frame rests like any stable item, or the same one opens every lesson (#94)
                key = (not set(c.topics) & today_topics, substitutions.get(c.id, 0), c.order)
                if (best is None or key < best[0]) and b.recombine_status(c, met_fills=True) == "novel":
                    best = (key, c)
            return best[1] if best else None

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
            exchanged = self.dialogues_played or any(e.kind == "connect" and e.stage == "exchange" for e in sc.exercises)
            if candidates is None and prefer is None and not exchanged:
                # no partner exchange yet this lesson (#48): an authored one among items in play,
                # before a pair of today's items with no exchange between them (#151 left
                # lesson 4 of the course without one once its new items had no bridge)
                in_play = [it for it in rest if (self._may_review(it.id) or it.id in self.exposures) and not not_due_stable(it)]
                candidates = _connect_pair(list(preferred) + in_play, just_touched, exchange_only=True)
            if candidates is None:
                candidates = _connect_pair(list(preferred), just_touched)
            if candidates is None:
                anchor = scope if prefer is not None else None
                live = rest
                if anchor is None:
                    # nothing ties the pair to today's material: items in play today (due, or
                    # practised this lesson) or rested long enough to review early first, or the
                    # same well-known exchange opens lesson after lesson whatever its interval (#94).
                    # A stable item only when due, whatever it did earlier today (#151)
                    live = [it for it in rest if (it.id in self.exposures or self._may_review(it.id)) and not not_due_stable(it)]
                candidates = _connect_pair(list(preferred) + live, just_touched, anchor)
                if candidates is None and live is not rest:
                    # still better than ending the lesson on a drill streak nothing else breaks
                    candidates = _connect_pair(list(preferred) + [it for it in rest if not not_due_stable(it)], just_touched, anchor)
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

        n_open = max(1, len(open_today))
        for k, item_id in enumerate(open_today):
            schedule_open(self.cur.by_id[item_id], k)
            reviews_used.append(item_id)
        open_timeline.sort(key=lambda t: t[:2])

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
                    if ration_left or (streak_relief_notes_used < cfg.max_streak_relief_notes and self._total_notes_left()):
                        note = self._pick_note(None)
                        if note is not None:
                            self._play_note(sc, note)
                            acted = True
                            if not ration_left:
                                streak_relief_notes_used += 1
                if not acted and remaining >= 40:
                    acted = do_connect()
                if not acted and remaining >= 90 and (ld := self.listening_dialogue()) is not None:
                    self._play_listening(sc, *ld)
                    since_dialogue = 0
                    acted = True
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

            # 0c. a substitution run goes on in its frame before anything else is fitted in (#151)
            if not acted and (sub := continue_substitution()) is not None:
                do_substitution(sub)
                acted = True

            # 0d. an open item's practice whose time has come (#149)
            if not acted and drill_streak < cfg.drill_streak_limit - 1:  # leave room for a non-recall exercise
                for entry in open_timeline:
                    if entry[0] > sc.total_duration:
                        break
                    if entry[2].id in recent:
                        continue
                    open_timeline.remove(entry)
                    do_recall(entry[2], entry[3])
                    acted = True
                    break

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
                    first_touch = passes == 1 or pick.id in early_ids
                    stage = self.review_stage(pick) if first_touch else self._harder_than_today(pick)
                    do_recall(pick, stage)
                    if pick.id not in reviews_used:
                        reviews_used.append(pick.id)
                    # a second, harder touch later in the lesson for weak or climbing items
                    st = self.learner.items[pick.id]
                    ladder = self.ladder(pick)
                    if stage_index(ladder, stage) < len(ladder) - 1 and not self._stable(pick) and (st.failures > 0 or self.rng.random() < 0.5):
                        seq += 1
                        heapq.heappush(pending, _Pending(idx + self.rng.randint(5, 9), seq, pick, next_stage(ladder, stage)))
                    acted = True

            # 5. nothing else fits here (typically the first lessons, with nothing to review):
            #    introduce early, else pull the next reactivation of a *different* item early,
            #    else take an extra new item, else accept a repeat, else stop.
            if not acted:
                candidate = next((p for p in sorted(pending) if p.item.id not in recent), None)
                if candidate is None and [e.kind for e in sc.exercises[-2:]] == ["intro", "intro"]:
                    # never a third introduction in a row (lesson 1 has nothing else to offer):
                    # recall the earlier of the two instead, only the very last item is off limits
                    candidate = next((p for p in sorted(pending) if p.item.id != recent[-1]), None)
                can_intro = idx - last_intro >= 1 and len(introduced) < cfg.resolved_max_new_items()
                # a later arc was admitted whole (_may_start_arc): its queued items may fill a gap too,
                # though not as a third introduction in a row
                can_drain = can_intro or (
                    current_arc_id > 0 and idx - last_intro >= 1 and [e.kind for e in sc.exercises[-2:]] != ["intro", "intro"]
                )
                if candidate is not None:
                    pending.remove(candidate)
                    heapq.heapify(pending)
                    do_recall(candidate.item, candidate.stage)
                elif new_queue and can_drain and remaining >= need_for_new * 0.6:
                    do_intro(new_queue.popleft())
                elif can_intro and not reviews_used and remaining >= need_for_new and (more := self.select_new(1, exclude={i.id for i in introduced} | set(self.embedded))):
                    # an extra item for a lesson with nothing to review (the first ones); a lesson
                    # that ran out of reviews takes a fresh arc below instead
                    do_intro(more[0])
                    # a filler can come back with the construction it made teachable
                    new_queue.extend(more[1:])
                elif pending and sorted(pending)[0].item.id != (recent[-1] if recent else None):
                    p = heapq.heappop(pending)  # a repeat, but not of the very last exercise
                    do_recall(p.item, p.stage)
                elif self._note_budget_left() and remaining >= 40 and self._pick_note(None) is not None:
                    self._play_note(sc, self._pick_note(None))  # nothing to practise now: an aside
                elif reviews_used and (sub := pick_substitution()) is not None:
                    # spare time: a known pattern with other words (#151), before a fresh arc or replayed reviews
                    do_substitution(sub)
                elif (
                    reviews_used
                    and not new_queue
                    and remaining >= need_for_new
                    and self._may_start_arc(current_arc_id + 1, early_tier, far_short=sc.total_duration < budget / 2)
                    and (more := self.select_new(cfg.resolved_extra_arc_items(capped=early_tier < 2), exclude={i.id for i in introduced} | set(self.embedded)))
                ):
                    # A fresh arc of new material rather than a second review pass: the new-item
                    # cap bounds an arc, not the lesson (see _may_start_arc). Only once the review
                    # pool ran dry (a first lesson still ends short on purpose) and the previous
                    # arc is fully introduced (a queued prereq would look ready to select_new).
                    # Consumes an idx tick like every other branch.
                    current_arc_id += 1
                    arc_target[current_arc_id] = len(more)
                    new_queue.extend(more[1:])
                    do_intro(more[0])
                    # the review fillers (rested items, then the second pass) space out the
                    # arc's introductions and reactivations, or they would come back to back
                    if early_tier == 0:
                        early_tier = 1
                        reviews.extend(load_early(rested_only=True))
                    if passes < cfg.max_review_passes:
                        passes += 1
                        reviews.extend(self._second_pass(reviews_used, recent))
                    # the closing block recalls every introduced item: reserve for the new ones too
                    closing_reserve = min(budget * cfg.closing_share, 8 + 14 * (len(introduced) + len(new_queue)))
                elif passes < cfg.max_review_passes and reviews_used and early_tier >= 1:
                    # material ran out before the time did: a second pass over what was reviewed,
                    # most urgent first, each one step harder than earlier in this lesson
                    passes += 1
                    reviews = deque(self._second_pass(reviews_used, recent))
                    continue
                elif reviews_used and (early_tier == 0 or (early_tier == 1 and passes >= cfg.max_review_passes)):
                    # still time left: not-due items, the stalest first. First those rested half
                    # their interval (before the second pass); last, once the second pass is used
                    # up too, any item not practised today. After that, arcs are unlimited.
                    early_tier += 1
                    reviews = deque(load_early(rested_only=early_tier == 1))
                    continue
                elif remaining >= 90 and cfg.max_listening_dialogues > 0 and (ld := self.listening_dialogue()) is not None:
                    # spare time is more to hear (#149 step 3), before today's items once more
                    self._play_listening(sc, *ld)
                    since_dialogue = 0
                elif reviews_used and (extra := pick_consolidation()) is not None:
                    # nothing else worth practising: today's new material once more (#151),
                    # rather than a stable item again or ending far short
                    consolidations[extra.id] = consolidations.get(extra.id, 0) + 1
                    do_recall(extra, self._harder_than_today(extra))
                elif (early_open := next((e for e in open_timeline if e[2].id not in recent), None)) is not None:
                    # nothing else is left: an open item's next practice comes early rather than
                    # not at all (#149); the timed entries (0d) are the normal route
                    open_timeline.remove(early_open)
                    do_recall(early_open[2], early_open[3])
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
                if cfg.late_unhinted_recall and stage in ("intro", "cloze", "hinted"):
                    stage = "meaning"  # #136: the lesson's last word on a new item is unhinted
                if stage == "recombine":
                    stage = self.recombine_or_instead(item)  # no fresh sentence: a meaning recall
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
                "priority_items": len(cfg.priority),  # a count only: the list may reflect a private profile
                "levers": {"late_unhinted_recall": cfg.late_unhinted_recall},
                "seed": cfg.seed,
                "level": self.timing.level,
            },
            "curriculum": self.cur.name,
            "new_items": [i.id for i in introduced] + list(self.embedded),
            "embedded_items": list(self.embedded),
            "reviewed_items": reviews_used,
            "open_items": open_today,
            "open_not_fitted": [i for i in open_ids if i not in open_today],
            "reviewed_early": [i for i in reviews_used if i in early_ids],
            "due_at_start": self.learner.due_count(self.today),
            "due_not_fitted": [i.id for i in reviews if i.id not in self.exposures and self.learner.review_priority(i.id, self.today) >= 1.0],
            "dialogues": list(self.dialogues_played),
            "dialogues_listened": list(self.dialogues_listened),
            "notes": list(self.notes_played),
            "exposures": self.exposures,
            "support_exposures": self.support,
            "ladders": {i: self.ladder(self.cur.by_id[i]) for i in self.exposures if i in self.cur.by_id},
            "not_introduced": [i.id for i in new_queue],
            # partner interaction in the target language vs recombination practice
            "partner_exchanges": len(self.dialogues_played) + sum(1 for e in sc.exercises if e.kind == "connect" and e.stage == "exchange"),
            "recombinations": sum(1 for e in sc.exercises if e.kind == "connect" and e.stage != "exchange"),
            "heard_utterances": sorted(self.builder.heard),
            "think_time_boosted": sorted(self.builder.boosted),
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

    def _play_listening(self, sc: Script, dlg: Dialogue, missing: set[str]) -> None:
        """The whole dialogue as listening (#149 step 3): the items the learner lacks are heard
        with their meaning, not asked for, and not recorded: they stay unmet. The ones they have
        are practised as usual."""
        ex = self.builder.dialogue(sc, dlg, assisted=True, listening=missing)
        self._record([t.expect for t in dlg.turns if t.expect and t.expect not in missing], "dialogue", ex.item_ids)
        self.dialogues_listened.append(dlg.id)


def apply_to_learner(sc: Script, learner: LearnerState, today: date, presume_success: bool = True) -> None:
    """Update the learner model from a built script's metadata."""
    learner.record_lesson(
        sc.lesson_number,
        sc.meta.get("exposures", {}),
        today,
        presume_success=presume_success,
        ladders=sc.meta.get("ladders", {}),
    )
    for item_id in sc.meta.get("open_items", []):
        if item_id in learner.items:
            learner.items[item_id].open_practiced = sc.lesson_number
    for item_id in sc.meta.get("embedded_items", []):
        learner.embedded[item_id] = sc.lesson_number
    for d in sc.meta.get("dialogues", []):
        learner.dialogues_done[d] = learner.dialogues_done.get(d, 0) + 1
    for n in sc.meta.get("notes", []):
        learner.notes_heard[n] = learner.notes_heard.get(n, 0) + 1
        learner.notes_last_heard[n] = sc.lesson_number
    learner.heard_utterances.update(sc.meta.get("heard_utterances", []))
    for item_id in sc.meta.get("think_time_boosted", []):
        if item_id in learner.items:
            learner.items[item_id].extra_think_time = False  # used up; a later failure sets it again
    for b in sc.meta.get("bridges", []):
        learner.bridges_heard[b] = learner.bridges_heard.get(b, 0) + 1
    learner.lessons.append(
        {
            "number": sc.lesson_number,
            "date": today.isoformat(),
            "new_items": sc.meta.get("new_items", []),
            "reviewed_items": sc.meta.get("reviewed_items", []),
            "dialogues": sc.meta.get("dialogues", []),
            "dialogues_listened": sc.meta.get("dialogues_listened", []),
            "duration_s": round(sc.total_duration, 1),
            "due_at_start": sc.meta.get("due_at_start", 0),
            "due_not_fitted": len(sc.meta.get("due_not_fitted", [])),
            "pace": sc.meta.get("config", {}).get("new_items"),
        }
    )
