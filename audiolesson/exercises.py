"""Build concrete prompt → pause → answer segments for an item at a stage.

The Builder is the only place that knows the *shape* of an exercise. The
planner decides *what* to practise and *when*; the renderer decides how it
sounds. Keep those three concerns apart.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .content import Curriculum, Dialogue, Item, Note, NOTE_TARGET_RE, TransformExample, split_note_span
from .learner import LearnerState
from .prompts import Prompts
from .script import Exercise, Script, Segment
from .stages import is_generative
from .timing import Timing


@dataclass
class Generated:
    """A sentence the learner has never heard verbatim (construction + fills)."""

    construction: Item
    fills: dict[str, Item]
    target: str
    meaning: str

    @property
    def key(self) -> str:
        return self.construction.id + ":" + ",".join(f"{k}={v.id}" for k, v in sorted(self.fills.items()))

    @property
    def item_ids(self) -> list[str]:
        return [self.construction.id] + [f.id for f in self.fills.values()]


@dataclass
class Builder:
    cur: Curriculum
    prompts: Prompts
    timing: Timing
    learner: LearnerState
    rng: random.Random = field(default_factory=lambda: random.Random(0))
    translate_partner: bool = True  # narrate the meaning of partner lines in dialogues
    used_combos: set[str] = field(default_factory=set)
    used_examples: set[str] = field(default_factory=set)
    _situation_uses: dict[str, int] = field(default_factory=dict)  # per-item count, this lesson

    # ------------------------------------------------------------------ utils

    @property
    def tl(self) -> str:
        return self.cur.target_lang

    @property
    def kl(self) -> str:
        return self.cur.known_lang

    def _m(self, meaning: str) -> str:
        """Meaning text ready to drop into a template: ends with punctuation."""
        meaning = meaning.strip()
        if self.kl.split("-")[0] in ("ja", "zh", "ko"):
            return meaning.rstrip("。")  # the phrasing templates wrap it in 「」
        if meaning[-1:] in ".?!…":
            return meaning
        return meaning + "."

    def _situation(self, item: Item) -> str | None:
        """The situation cue to narrate now, rotated across an item's ``situations`` (issue
        #34 point 4) — starting from how many times it's been exercised in *past* lessons
        (0 for an item with no recorded state yet, i.e. its first exposure), then advanced by
        ``_situation_uses`` for every situation narrated so far *within this lesson*.
        ``ItemState.exposures`` only updates once the whole lesson is applied afterwards
        (``record_lesson()``), so it alone can't distinguish a second situation recall in the
        same lesson from the first — without this lesson-local counter, an item recalled at
        the situation stage more than once in one lesson would repeat the same cue each time,
        the exact within-lesson repetition this pilot exists to fix (owner review on #39)."""
        base = self.learner.items[item.id].exposures if item.id in self.learner.items else 0
        offset = self._situation_uses.get(item.id, 0)
        self._situation_uses[item.id] = offset + 1
        return item.situation_for(base + offset)

    def _situation_readonly(self, item: Item) -> str | None:
        """An item's *current* situation cue for a ``connect()`` exercise, without advancing
        its rotation (owner review round 2 on #46). ``connect()`` narrates a situation cue the
        same way a ``situation``-stage recall does, so if it went through ``_situation()`` (and
        its shared, mutating ``_situation_uses`` counter), pairing an item into a connected
        moment would silently consume a rotation step for it — invisible to any ordinary
        recall of that same item elsewhere in the lesson. With a 2-cue item, one such hidden
        step flips which cue a later recall lands on; two hidden steps (e.g. the item gets
        swept into two separate connect() exercises in one lesson) land back on the *same*
        one, regressing the exact same-lesson repeat ``_situation()`` exists to prevent.
        Reading without advancing keeps the two mechanisms fully independent: connect()'s own
        framing is free to reuse an item's current cue without perturbing what an unrelated
        recall of that item sees."""
        base = self.learner.items[item.id].exposures if item.id in self.learner.items else 0
        offset = self._situation_uses.get(item.id, 0)
        return item.situation_for(base + offset)

    def _successes(self, item: Item) -> int:
        st = self.learner.items.get(item.id)
        return st.successes if st else 0

    def _narr(self, sc: Script, ex: Exercise, text: str) -> None:
        sc.add(Segment("narrate", "instructor", text, self.kl, 1.0, self.timing.speech_estimate(text, self.kl), None, ex.index))

    def _speak(
        self,
        sc: Script,
        ex: Exercise,
        text: str,
        speaker: str = "native_a",
        rate: float = 1.0,
        role: str | None = None,
        lang: str | None = None,
        speech_text: str | None = None,
    ) -> None:
        # ``lang`` lets a segment speak a language other than the course's own target
        # language — an embedded third-language example inside a note (issue #49) — while
        # every existing call site (which never passes it) keeps speaking ``self.tl``.
        # ``speech_text``, when given, is what actually reaches the TTS provider — ``text``
        # stays what the transcript shows (issue #49, PR #51 owner review): pronunciation
        # must not depend on the provider being able to read a romanized/transliterated
        # ``text`` correctly, so the estimate below is based on what will really be spoken.
        lang = lang or self.tl
        sc.add(Segment("speak", speaker, text, lang, rate, self.timing.speech_estimate(speech_text or text, lang, rate), role, ex.index, speech_text))

    def _answer(self, sc: Script, ex: Exercise, text: str, speaker: str = "native_a", rate: float = 1.0) -> None:
        sc.add(Segment("answer", speaker, text, self.tl, rate, self.timing.speech_estimate(text, self.tl, rate), None, ex.index))

    def _pause(self, sc: Script, ex: Exercise, seconds: float, role: str) -> None:
        sc.add(Segment("pause", None, None, None, 1.0, seconds, role, ex.index))

    def _beat(self, sc: Script, ex: Exercise) -> None:
        self._pause(sc, ex, self.timing.beat, "beat")

    def _gap(self, sc: Script, ex: Exercise) -> None:
        self._pause(sc, ex, self.timing.between_exercises, "beat")

    def _answer_pause(self, sc: Script, ex: Exercise, answer: str, item: Item | None, generative: bool) -> None:
        secs = self.timing.answer_pause(
            answer,
            self.tl,
            difficulty=item.difficulty if item else 3,
            successes=self._successes(item) if item else 0,
            generative=generative,
        )
        self._pause(sc, ex, secs, "answer")

    def _repeat_pause(self, sc: Script, ex: Exercise, text: str) -> None:
        self._pause(sc, ex, self.timing.repeat_pause(text, self.tl), "repeat")

    # ------------------------------------------------------------ bookends

    def opening(self, sc: Script, n: int, first_lesson: bool) -> Exercise:
        ex = sc.new_exercise("opening", None, [], "opening")
        self._narr(sc, ex, self.prompts.get("lesson_open", n=n))
        if first_lesson or n % 5 == 1:
            self._narr(sc, ex, self.prompts.get("lesson_intro"))
        self._gap(sc, ex)
        return ex

    def final_block_announce(self, sc: Script) -> Exercise:
        ex = sc.new_exercise("closing", None, [], "final review")
        self._narr(sc, ex, self.prompts.get("final_block"))
        self._gap(sc, ex)
        return ex

    def closing(self, sc: Script, n: int) -> Exercise:
        ex = sc.new_exercise("closing", None, [], "closing")
        self._narr(sc, ex, self.prompts.get("lesson_close", n=n))
        return ex

    # ---------------------------------------------------------------- intro

    def intro(self, sc: Script, item: Item) -> Exercise:
        if item.kind == "construction":
            return self._intro_construction(sc, item)
        if item.kind == "transform":
            return self._intro_transform(sc, item)
        ex = sc.new_exercise("intro", "intro", [item.id], f"new: {item.target}")
        self._narr(sc, ex, self.prompts.get("intro_new", meaning=self._m(item.meaning)))
        self._beat(sc, ex)
        self._speak(sc, ex, item.target)
        self._beat(sc, ex)
        chunks = item.backward_chunks() if item.is_hard() else []
        if len(chunks) > 1:
            self._narr(sc, ex, self.prompts.get("build_up"))
            for chunk in chunks:
                # issue #49: each chunk was spoken at natural rate here — the one part of
                # the backward-build ladder that never went through ``slow_rate``, despite
                # existing specifically to let the learner hear and imitate a difficult
                # phrase piece by piece. The trailing beat (beyond the repeat pause itself,
                # which is sized for the learner's own imitation, not for separating
                # chunks) gives clearer acoustic separation before the next chunk starts.
                self._speak(sc, ex, chunk, rate=self.timing.slow_rate)
                self._repeat_pause(sc, ex, chunk)
                self._beat(sc, ex)
            self._narr(sc, ex, self.prompts.get("natural"))
            self._speak(sc, ex, item.target)
            self._repeat_pause(sc, ex, item.target)
        elif item.is_hard():
            # a long single word with no verified sub-word boundary (issue #34 point 7):
            # slow whole-word repetition instead of a guessed, possibly mis-synthesized split
            self._narr(sc, ex, self.prompts.get("slowly"))
            self._speak(sc, ex, item.target, rate=self.timing.slow_rate)
            self._repeat_pause(sc, ex, item.target)
            self._narr(sc, ex, self.prompts.get("natural"))
            self._speak(sc, ex, item.target)
            self._repeat_pause(sc, ex, item.target)
        else:
            self._narr(sc, ex, self.prompts.get("repeat"))
            self._speak(sc, ex, item.target)
            self._repeat_pause(sc, ex, item.target)
            if item.difficulty >= 2 and item.word_count >= 2:
                self._narr(sc, ex, self.prompts.get("slowly"))
                self._speak(sc, ex, item.target, rate=self.timing.slow_rate)
                self._repeat_pause(sc, ex, item.target)
                self._narr(sc, ex, self.prompts.get("natural"))
                self._speak(sc, ex, item.target)
                self._repeat_pause(sc, ex, item.target)
        # end the introduction with a first real retrieval
        self._narr(sc, ex, self.prompts.get("meaning", meaning=self._m(item.meaning), language=self.prompts.language_name(self.tl)))
        self._answer_pause(sc, ex, item.target, item, generative=False)
        self._answer(sc, ex, item.target)
        self._gap(sc, ex)
        return ex

    def _intro_construction(self, sc: Script, item: Item) -> Exercise:
        ex = sc.new_exercise("intro", "intro", [item.id], f"new pattern: {item.target}")
        fills = self.cur.example_fill(item)
        target, meaning = self.cur.resolve_slots(item, fills)
        ex.item_ids += [f.id for f in fills.values() if f.id not in ex.item_ids]
        self._narr(sc, ex, self.prompts.get("construction_intro", meaning=self._m(meaning)))
        self._beat(sc, ex)
        self._speak(sc, ex, target)
        self._beat(sc, ex)
        self._narr(sc, ex, self.prompts.get("repeat"))
        self._speak(sc, ex, target)
        self._repeat_pause(sc, ex, target)
        if item.difficulty >= 2:
            self._narr(sc, ex, self.prompts.get("slowly"))
            self._speak(sc, ex, target, rate=self.timing.slow_rate)
            self._repeat_pause(sc, ex, target)
            self._narr(sc, ex, self.prompts.get("natural"))
            self._speak(sc, ex, target)
            self._repeat_pause(sc, ex, target)
        self._narr(sc, ex, self.prompts.get("construction_slot"))
        # a second example with a known fill, as the first retrieval
        gen = self.generate(item, exclude=fills)
        if gen is None:
            self._narr(sc, ex, self.prompts.get("meaning", meaning=self._m(meaning), language=self.prompts.language_name(self.tl)))
            self._answer_pause(sc, ex, target, item, generative=False)
            self._answer(sc, ex, target)
        else:
            self._speak(sc, ex, gen.target)
            self._beat(sc, ex)
            self._narr(sc, ex, self.prompts.get("meaning", meaning=self._m(gen.meaning), language=self.prompts.language_name(self.tl)))
            self._answer_pause(sc, ex, gen.target, item, generative=False)
            self._answer(sc, ex, gen.target)
            self.used_combos.add(gen.key)
        self._gap(sc, ex)
        return ex

    def _intro_transform(self, sc: Script, item: Item) -> Exercise:
        ex = sc.new_exercise("intro", "intro", [item.id], f"new: {item.meaning}")
        self._narr(sc, ex, self.prompts.get("transform_intro"))
        shown = item.examples[:2]
        for exm in shown:
            self._speak(sc, ex, exm.source)
            self._narr(sc, ex, self.prompts.get("transform_becomes"))
            self._speak(sc, ex, exm.result)
            self._beat(sc, ex)
            self.used_examples.add(item.id + ":" + exm.source)
        self._narr(sc, ex, self.prompts.get("transform_try"))
        exm = self._pick_example(item)
        self._transform_prompt(sc, ex, item, exm)
        self._gap(sc, ex)
        return ex

    # --------------------------------------------------------------- recall

    def recall(self, sc: Script, item: Item, stage: str) -> Exercise:
        if item.kind == "transform":
            return self._recall_transform(sc, item, stage)
        if stage == "recombine":
            gen_ex = self._recombine(sc, item)
            if gen_ex is not None:
                return gen_ex
            stage = "meaning"
        if stage == "situation" and not item.has_situation:
            stage = "meaning"
        if stage == "cloze" and item.word_count < 3:
            stage = "hinted"
        if item.kind == "construction" and stage in ("cloze", "hinted", "meaning", "situation"):
            return self._recall_construction(sc, item, stage)

        ex = sc.new_exercise("recall", stage, [item.id], f"{stage}: {item.target}")
        target = item.target
        if stage == "cloze":
            self._narr(sc, ex, self.prompts.get("cloze"))
            words = [w for w in target.split() if any(ch.isalnum() for ch in w)]
            partial = " ".join(words[:-1]) + "…"
            self._speak(sc, ex, partial, role="partial")
            self._answer_pause(sc, ex, target, item, generative=False)
        elif stage == "hinted":
            self._narr(sc, ex, self.prompts.get("hinted", meaning=self._m(item.meaning)))
            self._speak(sc, ex, target.split()[0].rstrip(".,?!"), role="hint")
            self._answer_pause(sc, ex, target, item, generative=False)
        elif stage == "situation":
            self._narr(sc, ex, self._situation(item))  # type: ignore[arg-type]
            self._answer_pause(sc, ex, target, item, generative=True)
        else:  # meaning (also the fallback for 'dialogue' when no dialogue fits)
            self._narr(sc, ex, self.prompts.get("meaning", meaning=self._m(item.meaning), language=self.prompts.language_name(self.tl)))
            self._answer_pause(sc, ex, target, item, generative=False)
        self._answer(sc, ex, target)
        if stage in ("cloze", "hinted") or item.difficulty >= 4:
            self._repeat_pause(sc, ex, target)
            self._answer(sc, ex, target)
        self._maybe_alternative(sc, ex, item, stage)
        self._gap(sc, ex)
        return ex

    def _maybe_alternative(self, sc: Script, ex: Exercise, item: Item, stage: str) -> None:
        """Once an item is past the hint stages, sometimes mention another acceptable answer."""
        if not item.alternatives or stage in ("intro", "cloze", "hinted"):
            return
        key = item.id + ":alt"
        if key in self.used_examples or self.rng.random() > 0.5:
            return
        self.used_examples.add(key)
        self._beat(sc, ex)
        self._narr(sc, ex, self.prompts.get("also"))
        self._speak(sc, ex, self.rng.choice(item.alternatives), role="alternative")

    def _recall_construction(self, sc: Script, item: Item, stage: str) -> Exercise:
        """Recall of a construction always goes through a filled example."""
        gen = self.generate(item)
        if gen is None:
            fills = self.cur.example_fill(item)
            target, meaning = self.cur.resolve_slots(item, fills)
            gen = Generated(item, fills, target, meaning)
        self.used_combos.add(gen.key)
        ex = sc.new_exercise("recall", stage, gen.item_ids, f"{stage}: {gen.target}")
        if stage == "hinted":
            self._narr(sc, ex, self.prompts.get("hinted", meaning=self._m(gen.meaning)))
            self._speak(sc, ex, gen.target.split()[0].rstrip(".,?!"), role="hint")
        elif stage == "situation" and item.has_situation:
            self._narr(sc, ex, self._situation(item))
        else:
            self._narr(sc, ex, self.prompts.get("meaning", meaning=self._m(gen.meaning), language=self.prompts.language_name(self.tl)))
        self._answer_pause(sc, ex, gen.target, item, generative=is_generative(stage))
        self._answer(sc, ex, gen.target)
        self._gap(sc, ex)
        return ex

    def _recombine(self, sc: Script, item: Item) -> Exercise | None:
        """Generative practice: a sentence the learner has not heard verbatim."""
        if item.kind == "construction":
            gen = self.generate(item)
        else:
            gen = self.generate_with(item)
        if gen is None:
            return None
        self.used_combos.add(gen.key)
        ids = [item.id] + [i for i in gen.item_ids if i != item.id]  # the practised item comes first
        ex = sc.new_exercise("generative", "recombine", ids, f"recombine: {gen.target}")
        key = "recombine" if item.kind == "construction" else "recombine_vocab"
        self._narr(sc, ex, self.prompts.get(key, meaning=self._m(gen.meaning)))
        self._answer_pause(sc, ex, gen.target, item, generative=True)
        self._answer(sc, ex, gen.target)
        self._gap(sc, ex)
        return ex

    def _recall_transform(self, sc: Script, item: Item, stage: str) -> Exercise:
        ex = sc.new_exercise("recall", stage, [item.id], f"{stage}: {item.meaning}")
        exm = self._pick_example(item)
        self._transform_prompt(sc, ex, item, exm, hint=(stage == "hinted"))
        self._gap(sc, ex)
        return ex

    def _transform_prompt(self, sc: Script, ex: Exercise, item: Item, exm: TransformExample, hint: bool = False) -> None:
        self._narr(sc, ex, item.instruction)
        self._speak(sc, ex, exm.source, role="source")
        if hint:
            self._speak(sc, ex, exm.result.split()[0].rstrip(".,?!"), role="hint")
        self._answer_pause(sc, ex, exm.result, item, generative=True)
        self._answer(sc, ex, exm.result)
        self.used_examples.add(item.id + ":" + exm.source)

    def _pick_example(self, item: Item) -> TransformExample:
        fresh = [e for e in item.examples if item.id + ":" + e.source not in self.used_examples]
        pool = fresh or item.examples
        return self.rng.choice(pool)

    # ------------------------------------------------------------ generation

    def generate(self, construction: Item, *, exclude: dict[str, Item] | None = None, prefer_unused: bool = True) -> Generated | None:
        """Fill a construction with words the learner knows; prefer combos not yet used."""
        options: dict[str, list[Item]] = {}
        for slot, tag in construction.slots.items():
            cands = [i for i in self.cur.items_with_tag(tag) if self.learner.knows(i.id) or self._in_lesson(i.id)]
            if exclude and slot in exclude:
                cands = [c for c in cands if c.id != exclude[slot].id]
            if not cands:
                return None
            options[slot] = cands
        slots = list(options)
        combos = self._product(options, slots)
        self.rng.shuffle(combos)
        if prefer_unused:
            unused = [c for c in combos if self._combo_key(construction, c) not in self.used_combos]
            combos = unused or combos
        fills = combos[0]
        target, meaning = self.cur.resolve_slots(construction, fills)
        return Generated(construction, fills, target, meaning)

    def generate_with(self, vocab: Item) -> Generated | None:
        """Find a known construction with a slot that accepts ``vocab`` and fill it."""
        homes = []
        for c in self.cur.items:
            if c.kind != "construction" or not (self.learner.knows(c.id) or self._in_lesson(c.id)):
                continue
            for slot, tag in c.slots.items():
                if tag in vocab.tags:
                    homes.append((c, slot))
        if not homes:
            return None
        self.rng.shuffle(homes)
        for c, slot in homes:
            gen = self.generate(c)
            if gen is None:
                continue
            gen.fills[slot] = vocab
            gen.target, gen.meaning = self.cur.resolve_slots(c, gen.fills)
            if gen.key not in self.used_combos:
                return gen
        c, slot = homes[0]
        gen = self.generate(c, prefer_unused=False)
        if gen is None:
            return None
        gen.fills[slot] = vocab
        gen.target, gen.meaning = self.cur.resolve_slots(c, gen.fills)
        return gen

    # items introduced earlier in *this* lesson count as usable components
    in_lesson: set[str] = field(default_factory=set)

    def _in_lesson(self, item_id: str) -> bool:
        return item_id in self.in_lesson

    @staticmethod
    def _combo_key(c: Item, fills: dict[str, Item]) -> str:
        return c.id + ":" + ",".join(f"{k}={v.id}" for k, v in sorted(fills.items()))

    @staticmethod
    def _product(options: dict[str, list[Item]], slots: list[str]) -> list[dict[str, Item]]:
        out: list[dict[str, Item]] = [{}]
        for s in slots:
            out = [{**d, s: it} for d in out for it in options[s]]
        return out

    # ------------------------------------------------------------------ note

    def _speak_note_text(self, sc: Script, ex: Exercise, text: str) -> None:
        """Narrate ``text`` in the instructor voice, except «...»-marked phrases, which go to
        the target-language voice instead — so a note that names e.g. Góðan daginn actually
        hears it said, rather than the instructor reading it as instructor-language text
        (issue #34 point 1, deferred at pilot 2 for lack of this mechanism).

        A marked span may carry its own explicit language («ja:sate» rather than bare
        «Góðan daginn») — a note can legitimately mention a *third* language besides its
        own narration language and the course's target language, e.g. an English note
        naming a Japanese word (issue #49); ``split_note_span`` picks that apart, and an
        explicit language always wins over the default target-language voice. It may also
        carry a "display|speech" pair («ja:sate|さて»): the transcript keeps the familiar
        romanization, but the TTS provider gets native orthography instead, so
        pronunciation doesn't depend on a provider correctly reading transliterated text.

        A prose fragment between two marked phrases that is only punctuation (e.g. the bare
        "," left behind by "«a», «b»") is never handed to ``_narr`` as its own TTS call —
        several notes mark three or more phrases in a list, so this is common, not a rare
        edge case (owner review on #41). A beat stands in for it instead, preserving the
        pause the punctuation implied. A fragment with real words (e.g. ", and") still
        narrates normally."""
        for i, part in enumerate(NOTE_TARGET_RE.split(text)):
            part = part.strip()
            if not part:
                continue
            if i % 2:
                lang, display, speech = split_note_span(part)
                self._speak(sc, ex, display, lang=lang, speech_text=speech if speech != display else None)
            elif any(ch.isalnum() for ch in part):
                self._narr(sc, ex, part)
            else:
                self._beat(sc, ex)

    def note(self, sc: Script, note: Note) -> Exercise:
        """An aside: no retrieval. Bookended so it's never mistaken for the start of the next
        (unrelated) exercise. Mostly instructor narration, but a «...»-marked phrase inside
        ``note.text`` is spoken by the target-language voice instead (see
        ``_speak_note_text``). A milestone note names a grammatical pattern now that its
        items are known, so it gets its own intro and closing lines instead of being framed
        as optional cultural trivia the lesson is a detour from (issue #34: "this *is* the
        lesson")."""
        ex = sc.new_exercise("note", None, list(note.items), f"note: {note.id}")
        self._narr(sc, ex, self.prompts.get("milestone_intro" if note.milestone else "aside"))
        self._speak_note_text(sc, ex, note.text)
        self._beat(sc, ex)
        self._narr(sc, ex, self.prompts.get("milestone_end" if note.milestone else "aside_end"))
        self._gap(sc, ex)
        return ex

    # ---------------------------------------------------------------- connect

    def connect(self, sc: Script, items: list[Item]) -> Exercise:
        """One connected exchange between two already-known items (issue #44, owner review
        round 2 on #46): the fallback for "connected use" when no authored dialogue requires
        them, and a genuine third option for a drill streak with nowhere else to go — not
        another isolated recall, and not a passive aside either.

        The first cut of this narrated a shared frame and then ran two ordinary situation
        recalls back to back — structurally two independent flashcards under a header, with
        no connection between them (confirmed by the pair the planner happened to choose:
        "leaving a shop" next to "raising a glass for a toast"). A second cut bridged them
        with an explicit connecting line (``connect_then``, "And then —"), narrated by the
        instructor — still the same shape issue #48 named directly: English instruction,
        retrieve one phrase, repeat.

        ``items[1].partner_cue`` (issue #48), when authored, replaces that English bridge
        with an actual partner utterance spoken by ``native_b`` between the two retrievals
        — so, with the instructor's own scaffolding stripped away, "answer A → partner_cue
        → answer B" still reads as one coherent exchange. A first cut of this picked a
        generic already-known "discourse"-topic item instead (owner review round 2 on PR
        #52): that filter let short function words ("og", "en", "með") through as if they
        were standalone turns, and didn't guarantee even a genuine reaction phrase actually
        fit the specific pairing. ``partner_cue`` is curated per item instead of selected
        algorithmically — the instructor's own instruction for B still narrows the task to
        one checkable answer either way (the owner was explicit that keeping it isn't the
        problem); what changes is only whether the *target-language* turns alone already
        form a plausible sequence. Empty (the common case — most items have no authored
        bridge) falls back to the original English narration, unchanged. Its own exercise
        kind (not folded into ``recall``) so it's identifiable as a deliberate recombination
        moment, the same way ``note()`` is bookended rather than left to blend into
        whatever comes next."""
        first, second = items[0], items[1]
        ids = [first.id, second.id]
        ex = sc.new_exercise("connect", None, ids, f"connect: {first.id}+{second.id}")
        self._narr(sc, ex, self.prompts.get("connect_intro"))
        self._beat(sc, ex)
        self._narr(sc, ex, self._situation_readonly(first))  # type: ignore[arg-type]
        self._answer_pause(sc, ex, first.target, first, generative=True)
        self._answer(sc, ex, first.target)
        self._beat(sc, ex)
        if second.partner_cue:
            self._speak(sc, ex, second.partner_cue, speaker="native_b")
            self._beat(sc, ex)
        else:
            self._narr(sc, ex, self.prompts.get("connect_then"))
        self._narr(sc, ex, self._situation_readonly(second))  # type: ignore[arg-type]
        self._answer_pause(sc, ex, second.target, second, generative=True)
        self._answer(sc, ex, second.target)
        self._gap(sc, ex)
        return ex

    # -------------------------------------------------------------- dialogue

    def dialogue(self, sc: Script, dlg: Dialogue, *, replay: bool = False, max_turns: int | None = None, assisted: bool = True) -> Exercise:
        """Play a dialogue; ``max_turns`` lets early encounters stop after a few turns.

        ``assisted`` (issue #26): the first encounter narrates a translation of every partner
        line and an explicit "say X" cue for every turn, so producing the right answer never
        depends on having understood the partner. From the second encounter on, both drop once
        there is an actual partner line to react to — the partner's own utterance becomes the
        retrieval cue. A turn with nothing said yet to react to (the very first turn, when it
        has no ``opener``) always keeps its cue: there would otherwise be nothing to go on."""
        turns = dlg.turns if max_turns is None else dlg.turns[: max(1, max_turns)]
        ids = [t.expect for t in turns if t.expect] + [r for r in dlg.requires if r not in {t.expect for t in turns}]
        label = f"dialogue: {dlg.id}" + ("" if len(turns) == len(dlg.turns) else f" ({len(turns)}/{len(dlg.turns)} turns)")
        ex = sc.new_exercise("dialogue", "dialogue", ids, label)
        partner = dlg.partner_speaker
        self._narr(sc, ex, dlg.setting)
        self._beat(sc, ex)
        lines: list[tuple[str, str]] = []
        heard_partner = False
        for turn in turns:
            if turn.opener:
                self._speak(sc, ex, turn.opener, speaker=partner)
                lines.append((partner, turn.opener))
                heard_partner = True
                if assisted and self.translate_partner and turn.opener_meaning:
                    self._beat(sc, ex)
                    self._narr(sc, ex, self.prompts.get("dialogue_partner_said", meaning=turn.opener_meaning))
            if turn.expect:
                item = self.cur.item(turn.expect)
                expected = item.target
            else:
                item = None
                expected = turn.expect_text or ""
            if assisted or not heard_partner:
                self._narr(sc, ex, turn.cue)
            self._answer_pause(sc, ex, expected, item, generative=True)
            self._answer(sc, ex, expected)
            lines.append(("native_a", expected))
            if turn.partner:
                self._beat(sc, ex)
                self._speak(sc, ex, turn.partner, speaker=partner)
                lines.append((partner, turn.partner))
                heard_partner = True
                if assisted and self.translate_partner and turn.partner_meaning:
                    self._beat(sc, ex)
                    self._narr(sc, ex, self.prompts.get("dialogue_partner_said", meaning=turn.partner_meaning))
        if replay:
            self._gap(sc, ex)
            self._narr(sc, ex, self.prompts.get("dialogue_replay"))
            for who, text in lines:
                self._speak(sc, ex, text, speaker=who)
                self._beat(sc, ex)
        self._gap(sc, ex)
        return ex
