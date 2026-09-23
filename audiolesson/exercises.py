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
        return _combo_key(self.construction, self.fills)

    @property
    def item_ids(self) -> list[str]:
        return [self.construction.id] + [f.id for f in self.fills.values()]


def _combo_key(construction: Item, fills: dict[str, Item]) -> str:
    return construction.id + ":" + ",".join(f"{k}={v.id}" for k, v in sorted(fills.items()))


def _norm_utterance(text: str) -> str:
    """Case- and trailing-punctuation-insensitive form of a target-language line."""
    return text.strip().rstrip(".?!…").strip().lower()


BRIDGE_GLOSS_ENCOUNTERS = 2  # a partner_cue is glossed on the learner's first N hearings of that bridge


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
    heard: set[str] = field(default_factory=set)  # normalised target-language lines presented this lesson
    in_lesson: set[str] = field(default_factory=set)  # items introduced this lesson: usable as parts
    _situation_uses: dict[str, int] = field(default_factory=dict)  # situation cues narrated this lesson, per item

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

    def _situation(self, item: Item, advance: bool = True) -> str | None:
        """The situation cue to narrate now, rotated by past exposures plus the cues already
        narrated this lesson (exposures only update after the lesson). ``connect()`` reads
        without advancing, so pairing an item never shifts what its own recalls hear."""
        base = self.learner.items[item.id].exposures if item.id in self.learner.items else 0
        offset = self._situation_uses.get(item.id, 0)
        if advance:
            self._situation_uses[item.id] = offset + 1
        return item.situation_for(base + offset)

    def _meaning_prompt(self, meaning: str) -> str:
        return self.prompts.get("meaning", meaning=self._m(meaning), language=self.prompts.language_name(self.tl))

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
        """``lang`` overrides the target language (a third-language example in a note);
        ``speech_text`` is what the TTS provider receives when it differs from ``text``."""
        lang = lang or self.tl
        sc.add(Segment("speak", speaker, text, lang, rate, self.timing.speech_estimate(speech_text or text, lang, rate), role, ex.index, speech_text))
        if lang == self.tl and role not in ("partial", "hint"):  # a cloze fragment or first-word hint isn't the utterance
            self.heard.add(_norm_utterance(text))

    def _answer(self, sc: Script, ex: Exercise, text: str, speaker: str = "native_a", rate: float = 1.0) -> None:
        sc.add(Segment("answer", speaker, text, self.tl, rate, self.timing.speech_estimate(text, self.tl, rate), None, ex.index))
        self.heard.add(_norm_utterance(text))

    def is_new_utterance(self, text: str) -> bool:
        """True only if the learner has never been presented this target-language line: not
        this lesson, not in an earlier one, and not as the target of an item already met
        («Eigðu góðan dag.» is both an authored phrase and a generated sentence)."""
        n = _norm_utterance(text)
        if n in self.heard or n in self.learner.heard_utterances:
            return False
        return not any(_norm_utterance(it.target) == n for it in self.cur.items if self.learner.has_met(it.id))

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
                # slow, with a beat after the learner's repetition to separate the chunks
                self._speak(sc, ex, chunk, rate=self.timing.slow_rate)
                self._repeat_pause(sc, ex, chunk)
                self._beat(sc, ex)
            self._narr(sc, ex, self.prompts.get("natural"))
            self._speak(sc, ex, item.target)
            self._repeat_pause(sc, ex, item.target)
        elif item.is_hard():
            # a long single word: slow whole-word repetition, never a guessed split
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
        self._narr(sc, ex, self._meaning_prompt(item.meaning))
        self._answer_pause(sc, ex, item.target, item, generative=False)
        self._answer(sc, ex, item.target)
        self._gap(sc, ex)
        return ex

    def _intro_construction(self, sc: Script, item: Item) -> Exercise:
        ex = sc.new_exercise("intro", "intro", [item.id], f"new pattern: {item.target}")
        fills = self.cur.example_fill(item)
        target, meaning = self.cur.resolve_slots(item, fills)
        self.used_combos.add(_combo_key(item, fills))  # the worked example is heard, not new
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
            self._narr(sc, ex, self._meaning_prompt(meaning))
            self._answer_pause(sc, ex, target, item, generative=False)
            self._answer(sc, ex, target)
        else:
            self._speak(sc, ex, gen.target)
            self._beat(sc, ex)
            self._narr(sc, ex, self._meaning_prompt(gen.meaning))
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
        if stage == "situation" and not self.situation_usable(item):
            stage = "meaning"
        if stage == "cloze" and item.word_count < 3:
            stage = "hinted"
        if item.kind == "construction" and stage in ("cloze", "hinted", "meaning", "situation"):
            return self._recall_construction(sc, item, stage)

        ex = sc.new_exercise("recall", stage, [item.id], f"{stage}: {item.target}")
        target = item.target
        if stage == "cloze":
            # say what to complete: «Ég skil…» alone could be «Ég skil.» or «Ég skil ekki.»
            self._narr(sc, ex, self.prompts.get("cloze", meaning=self._m(item.meaning)))
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
            self._narr(sc, ex, self._meaning_prompt(item.meaning))
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
        """Recall of a construction always goes through a filled example; at the situation
        stage, one with the fills the situation names."""
        fixed = self.cur.situation_fills(item) if stage == "situation" and self.situation_usable(item) else {}
        gen = self.generate(item, fixed=fixed)
        if gen is None:
            fills = {**self.cur.example_fill(item), **fixed}
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
            self._narr(sc, ex, self._meaning_prompt(gen.meaning))
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
        # the generator only *prefers* unused combinations, so claim novelty only when true
        if item.kind == "construction":
            key = "recombine_new" if self.is_new_utterance(gen.target) else "recombine"
        else:
            key = "recombine_vocab"
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

    def generate(
        self, construction: Item, *, exclude: dict[str, Item] | None = None, prefer_unused: bool = True, fixed: dict[str, Item] | None = None
    ) -> Generated | None:
        """Fill a construction with words the learner knows; prefer combos not yet used.
        ``fixed`` pins slots to specific fills (a situation's binding)."""
        options: dict[str, list[Item]] = {}
        for slot, tag in construction.slots.items():
            if fixed and slot in fixed:
                options[slot] = [fixed[slot]]
                continue
            cands = [i for i in self.cur.items_with_tag(tag) if self._available(i.id)]
            if exclude and slot in exclude:
                cands = [c for c in cands if c.id != exclude[slot].id]
            if not cands:
                return None
            options[slot] = cands
        slots = list(options)
        combos = self._product(options, slots)
        self.rng.shuffle(combos)
        if prefer_unused:
            unused = [c for c in combos if _combo_key(construction, c) not in self.used_combos]
            combos = unused or combos
        fills = combos[0]
        target, meaning = self.cur.resolve_slots(construction, fills)
        return Generated(construction, fills, target, meaning)

    def generate_with(self, vocab: Item) -> Generated | None:
        """Find a known construction with a slot that accepts ``vocab`` and fill it."""
        homes = []
        for c in self.cur.items:
            if c.kind != "construction" or not self._available(c.id):
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

    def _available(self, item_id: str) -> bool:
        """Known, or introduced earlier this lesson: usable as a part of a generated sentence."""
        return self.learner.knows(item_id) or item_id in self.in_lesson

    def situation_usable(self, item: Item) -> bool:
        """Whether ``item``'s situation can be practised now: every fill it names is available
        ("Ask if she speaks German." waits until þýsku is known)."""
        return item.has_situation and all(self._available(f.id) for f in self.cur.situation_fills(item).values())

    @staticmethod
    def _product(options: dict[str, list[Item]], slots: list[str]) -> list[dict[str, Item]]:
        out: list[dict[str, Item]] = [{}]
        for s in slots:
            out = [{**d, s: it} for d in out for it in options[s]]
        return out

    # ------------------------------------------------------------------ note

    def _speak_note_text(self, sc: Script, ex: Exercise, text: str) -> None:
        """Narrate ``text``, speaking «...» spans in their own voice (see ``split_note_span``).
        Punctuation-only prose between spans (the "," in "«a», «b»") becomes a beat rather
        than a TTS call of its own."""
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
        """An aside, no retrieval, bookended so it isn't mistaken for the next exercise. A
        milestone gets its own framing: it is part of the lesson, not a detour."""
        ex = sc.new_exercise("note", None, list(note.items), f"note: {note.id}")
        self._narr(sc, ex, self.prompts.get("milestone_intro" if note.milestone else "aside"))
        self._speak_note_text(sc, ex, note.text)
        self._beat(sc, ex)
        self._narr(sc, ex, self.prompts.get("milestone_end" if note.milestone else "aside_end"))
        self._gap(sc, ex)
        return ex

    # ---------------------------------------------------------------- connect

    def connect(self, sc: Script, items: list[Item]) -> Exercise:
        """Two already-known items in one exercise: connected use when no authored dialogue
        fits, and a way to break a drill streak.

        If ``items[1]`` has a bridge written for ``items[0]`` (``partner_cue_after``), this is
        an ``exchange``: one scene, with the partner's line spoken between the two answers.
        Otherwise it is ``recombine`` practice: two independent situations joined by a neutral
        transition that doesn't imply the second follows from the first."""
        first, second = items[0], items[1]
        first_target = self._connect_target(first)
        second_target = self._connect_target(second)
        ids = [first.id, second.id]
        bridged = bool(second.partner_cue) and second.partner_cue_after == first.id
        ex = sc.new_exercise("connect", "exchange" if bridged else "recombine", ids, f"connect: {first.id}+{second.id}")
        self._narr(sc, ex, self.prompts.get("connect_intro"))
        self._beat(sc, ex)
        # a bridge's own scene replaces the items' standalone situations
        self._narr(sc, ex, second.partner_cue_setup if bridged else self._situation(first, advance=False))  # type: ignore[arg-type]
        self._answer_pause(sc, ex, first_target, first, generative=True)
        self._answer(sc, ex, first_target)
        self._beat(sc, ex)
        if bridged:
            self._speak(sc, ex, second.partner_cue, speaker="native_b")
            self._beat(sc, ex)
            if self.translate_partner and self.learner.bridges_heard.get(second.id, 0) < BRIDGE_GLOSS_ENCOUNTERS:
                # early encounters say what the partner said; later ones rely on comprehension
                self._narr(sc, ex, self.prompts.get("dialogue_partner_said", meaning=second.partner_cue_meaning))
                self._beat(sc, ex)
        else:
            self._narr(sc, ex, self.prompts.get("connect_next"))
        self._narr(sc, ex, second.partner_cue_situation if bridged else self._situation(second, advance=False))  # type: ignore[arg-type]
        self._answer_pause(sc, ex, second_target, second, generative=True)
        self._answer(sc, ex, second_target)
        self._gap(sc, ex)
        return ex

    def _connect_target(self, item: Item) -> str:
        """The spoken target of a ``connect()`` turn. A construction is filled first, with
        the fills its situation names pinned, since connect() narrates that situation."""
        if item.kind != "construction":
            return item.target
        if not self.situation_usable(item):
            # the planner never pairs such an item; refuse rather than speak an unmet fill
            raise ValueError(f"connect(): {item.id!r}'s situation names a fill the learner doesn't have yet")
        fixed = self.cur.situation_fills(item)
        gen = self.generate(item, fixed=fixed)
        if gen is None:
            fills = {**self.cur.example_fill(item), **fixed}
            target, _ = self.cur.resolve_slots(item, fills)
            return target
        self.used_combos.add(gen.key)
        return gen.target

    # -------------------------------------------------------------- dialogue

    def dialogue(self, sc: Script, dlg: Dialogue, *, replay: bool = False, max_turns: int | None = None, assisted: bool = True) -> Exercise:
        """Play a dialogue; ``max_turns`` lets early encounters stop after a few turns.

        ``assisted`` (the first encounter) translates partner lines and cues every turn. Later
        encounters drop both once the partner has said something: their line is the cue. A
        turn before any partner line always keeps its cue."""
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
                if item.kind == "construction":
                    # every spoken part must be a required item (validate() enforces this too)
                    unbound = set(item.slots) - set(turn.expect_fill)
                    if unbound:
                        raise ValueError(f"dialogue {dlg.id!r}: construction turn {item.id!r} leaves slots {sorted(unbound)} unbound")
                    fills = {s: self.cur.by_id[f] for s, f in turn.expect_fill.items()}
                    expected = self.cur.resolve_slots(item, fills)[0]
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
