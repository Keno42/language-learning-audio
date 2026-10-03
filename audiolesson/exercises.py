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
    form: str | None = None  # "negative" / "question" (#171); None is the plain sentence

    @property
    def key(self) -> str:
        return _combo_key(self.construction, self.fills, self.form)

    @property
    def item_ids(self) -> list[str]:
        return [self.construction.id] + [f.id for f in self.fills.values()]


def _combo_key(construction: Item, fills: dict[str, Item], form: str | None = None) -> str:
    return construction.id + (f"~{form}" if form else "") + ":" + ",".join(f"{k}={v.id}" for k, v in sorted(fills.items()))


def _other_voice(speaker: str) -> str:
    """The native voice that isn't ``speaker`` (native_a is female, native_b male)."""
    return "native_b" if speaker == "native_a" else "native_a"


VOICE_OF = {"f": "native_a", "m": "native_b"}  # every profile voices native_a female, native_b male
GENDER_OF = {v: g for g, v in VOICE_OF.items()}


def _norm_utterance(text: str) -> str:
    """Case- and trailing-punctuation-insensitive form of a target-language line."""
    return text.strip().rstrip(".?!…").strip().lower()


BRIDGE_GLOSS_ENCOUNTERS = 2  # a partner_cue is glossed on the learner's first N hearings of that bridge
PROMPT_GLOSS_HEARINGS = 2  # a prompt_by line not yet known is glossed on its first N hearings in a lesson
FORM_SHARE = 0.25  # the most a negative or question form takes of a lesson's generated sentences (#171)
FORM_HARD_CAP = 0.35  # a form is not chosen at all if it would pass this share of the lesson's generated sentences
FORM_ALL_HARD_CAP = 0.5  # …nor any form that would leave the forms together above this share
FORM_CAP_FROM = 6  # …counted from this many generated sentences (before that a share is meaningless)
CONSTRUCTION_CEILING = 10  # generated sentences one construction may have in a lesson (#180; §9 "about ten uses", extended to patterns)
FORM_EXTRA_NEW = 2  # sentences in a form taught this lesson, beyond the practice right after its note
SITUATION_FULL_MAX = 2  # an authored situation is narrated in full at most this often in a lesson (G12)


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
    _situation_texts: dict[str, int] = field(default_factory=dict)  # times each authored situation was narrated in full
    _mixed_review_said: bool = False  # «Quick review» is announced once a lesson
    _gender_uses: dict[str, int] = field(default_factory=dict)  # speaker-gendered recalls this lesson, per item
    boosted: set[str] = field(default_factory=set)  # items whose answer pauses got the after-failure time
    _last_partner_cue: int | None = None  # index of the latest partner-line cue exercise (no repeated "Reply.")
    _prompt_glosses: dict[str, int] = field(default_factory=dict)  # partner-line cues glossed this lesson, per prompting item
    notes_taught: set[str] = field(default_factory=set)  # notes played this lesson (the learner state updates after it)
    construction_counts: dict[str, int] = field(default_factory=dict)  # generated sentences this lesson, by construction (#180)
    form_counts: dict[str, int] = field(default_factory=dict)  # generated sentences this lesson, by form ("plain", "negative", "question")
    form_extra: dict[str, int] = field(default_factory=dict)  # …of a form taught this lesson, outside its practice right after the note

    # ------------------------------------------------------------------ utils

    @property
    def tl(self) -> str:
        return self.cur.target_lang

    @property
    def kl(self) -> str:
        return self.cur.known_lang

    def _m(self, meaning: str) -> str:
        """Meaning text ready to drop into a template: starts with a capital (every template
        puts it at the start of a sentence or after "Say:") and ends with punctuation."""
        meaning = meaning.strip()
        if self.kl.split("-")[0] in ("ja", "zh", "ko"):
            return meaning.rstrip("。")  # the phrasing templates wrap it in 「」
        meaning = meaning[:1].upper() + meaning[1:]
        if meaning[-1:] in ".?!…":
            return meaning
        return meaning + "."

    def _next_situation(self, item: Item) -> str | None:
        """The next variant by rotation, skipping any narrated in full ``SITUATION_FULL_MAX``
        times already this lesson; the first one when none has room (``situation_room``)."""
        base = (self.learner.items[item.id].exposures if item.id in self.learner.items else 0) + self._situation_uses.get(item.id, 0)
        variants = list(item.situations) or ([item.situation] if item.situation else [])
        if not variants:
            return None
        for k in range(len(variants)):
            text = variants[(base + k) % len(variants)]
            if self._situation_texts.get(text, 0) < SITUATION_FULL_MAX:
                return text
        return item.situation_for(base)

    def situation_room(self, item: Item) -> bool:
        """Whether some authored situation of ``item`` may still be narrated in full this
        lesson (G12: the same English situation came back 7–10 times). After that the cue
        is the meaning, short, or the partner's line when the item has one."""
        variants = list(item.situations) or ([item.situation] if item.situation else [])
        return any(self._situation_texts.get(t, 0) < SITUATION_FULL_MAX for t in variants)

    def _cue(self, item: Item, meaning: str | None = None) -> str | None:
        """A connect() turn's cue: the situation while it may still be narrated in full, else
        the meaning, short. ``meaning`` is the filled sentence's, for a construction (#178): its own
        ``spoken_meaning`` is the unfilled template."""
        if self.situation_room(item):
            return self._situation(item)
        return self._meaning_prompt(meaning or item.spoken_meaning)

    def prompt_item(self, item: Item) -> tuple[Item, bool] | None:
        """G12: the item whose line the partner says as ``item``'s cue, and whether the line goes
        bare. Bare (no English at all) only when the learner knows it and it isn't open (#149:
        a line they reported not being able to say is no cue). Introduced earlier this lesson,
        met but not yet known, or open: the line, then once what it means, the way a partner
        bridge does. None (the line was never met): narrate the authored situation."""
        if not item.prompt_by or item.kind == "construction" or item.target_m:
            return None
        prompt = self.cur.by_id.get(item.prompt_by)
        if prompt is None:
            return None
        if self.learner.knows(prompt.id) and not self.learner.is_open(prompt.id):
            return prompt, True
        if self._available(prompt.id) or self.learner.has_met(prompt.id):
            return prompt, False
        return None

    def _partner_cue_recall(self, sc: Script, item: Item, prompt: Item, bare: bool) -> Exercise:
        """A situation recall whose cue is the partner's line, in Icelandic. «Reply.» frames it
        unless the exercise just before was one too; unless ``bare``, the line's meaning follows
        on its first ``PROMPT_GLOSS_HEARINGS`` hearings in the lesson (the way a bridge does). The partner speaks in the male voice, the model answer in the female one."""
        follows_cue = bool(sc.exercises) and sc.exercises[-1].index == self._last_partner_cue
        ex = sc.new_exercise("recall", "situation", [item.id], f"situation: {item.target}")
        if not follows_cue:
            self._narr(sc, ex, self.prompts.get("reply"))
        self._speak(sc, ex, prompt.target, speaker="native_b", role="prompt")
        if not bare and self._prompt_glosses.get(prompt.id, 0) < PROMPT_GLOSS_HEARINGS:
            self._prompt_glosses[prompt.id] = self._prompt_glosses.get(prompt.id, 0) + 1
            self._beat(sc, ex)
            self._narr(sc, ex, self.prompts.get("dialogue_partner_said", meaning=self._m(prompt.spoken_meaning)))
        self._answer_pause(sc, ex, item.target, item, generative=True)
        self._answer(sc, ex, item.target, speaker="native_a")
        self._gap(sc, ex)
        self._last_partner_cue = ex.index
        return ex

    def _situation(self, item: Item) -> str | None:
        """The situation cue to narrate now, rotated by past exposures plus the cues already
        narrated this lesson (exposures only update after the lesson). Every narration of an
        item's own cue advances it, connect() included, so the next one is a different variant
        whenever the item has one."""
        cue = self._next_situation(item)
        self._situation_uses[item.id] = self._situation_uses.get(item.id, 0) + 1
        if cue:
            self._situation_texts[cue] = self._situation_texts.get(cue, 0) + 1
        return cue

    # ---- the speaker's gender (Item.target_m) -----------------------------

    def speaker_gender(self, item: Item | None, voice: str | None = None, gendered: bool | None = None) -> str | None:
        """For an item whose words follow the speaker's gender, which form this recall asks
        for: the one ``voice`` implies when an exchange fixes it, else alternating with the
        item's exposures so both get practised. None when the words don't change.
        ``gendered`` overrides whether they do (a construction depends on its fills, a
        transform on its example); by default, whether the item has a ``target_m``."""
        if gendered is None:
            gendered = bool(item and item.target_m)
        if item is None or not gendered:
            return None
        if voice is not None:
            return GENDER_OF[voice]
        base = self.learner.items[item.id].exposures if item.id in self.learner.items else 0
        offset = self._gender_uses.get(item.id, 0)
        self._gender_uses[item.id] = offset + 1
        return "fm"[(base + offset) % 2]

    @staticmethod
    def _gendered(item: Item, gender: str | None) -> str:
        return item.target_m if gender == "m" and item.target_m else item.target

    @staticmethod
    def _fills_gendered(fills: dict[str, Item]) -> bool:
        """Whether a filled construction's words follow the speaker's gender: a fill has a
        man's form («glöð» / «glaður»); «einmana» is the same for both."""
        return any(f.target_m for f in fills.values())

    def _filled(self, construction: Item, fills: dict[str, Item], voice: str | None = None, form: str | None = None) -> tuple[str | None, str]:
        """(speaker gender or None, target) for ``construction`` filled with ``fills``: when a
        fill has a man's form, pick which form this exercise asks for (``speaker_gender``)."""
        gender = self.speaker_gender(construction, voice, gendered=self._fills_gendered(fills))
        return gender, self.cur.resolve_slots(construction, fills, gender, form)[0]

    def forms_taught(self) -> set[str]:
        """The forms of constructions («negative», «question») whose teaching note the learner has
        heard, in an earlier lesson or this one (#171): only those are used in generated sentences."""
        return {
            n.teaches for n in self.cur.notes
            if n.teaches and (self.learner.notes_heard.get(n.id, 0) > 0 or n.id in self.notes_taught)
        }

    def _as(self, gender: str | None, prompt: str) -> str:
        """``prompt`` with "As a man:" / "As a woman:" in front when the words depend on it."""
        return self.prompts.get(f"speak_as_{gender}", prompt=prompt) if gender else prompt

    def _meaning_prompt(self, meaning: str, context: str = "") -> str:
        if context:
            return self.prompts.get("meaning_in_context", meaning=self._m(meaning).rstrip(".。"), context=context)
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
        return not any(n in (_norm_utterance(it.target), _norm_utterance(it.target_m)) for it in self.cur.items if self.learner.has_met(it.id))

    def _pause(self, sc: Script, ex: Exercise, seconds: float, role: str, floor: float | None = None) -> None:
        """``floor``: what fitting the audio to length may shrink this pause to, at most."""
        sc.add(Segment("pause", None, None, None, 1.0, seconds, role, ex.index, floor=floor))

    def _beat(self, sc: Script, ex: Exercise) -> None:
        self._pause(sc, ex, self.timing.beat, "beat")

    def _gap(self, sc: Script, ex: Exercise) -> None:
        self._pause(sc, ex, self.timing.between_exercises, "beat")

    def _answer_pause(
        self, sc: Script, ex: Exercise, answer: str, item: Item | None, generative: bool, supported: bool = False
    ) -> None:
        """``supported``: the prompt just gave part of the answer (hint, cloze fragment)."""
        st = self.learner.items.get(item.id) if item else None
        after_failure = bool(st and st.extra_think_time)
        if after_failure and item:
            self.boosted.add(item.id)
        secs = self.timing.answer_pause(
            answer,
            self.tl,
            difficulty=item.difficulty if item else 3,
            successes=self._successes(item) if item else 0,
            generative=generative,
            supported=supported,
            after_failure=after_failure,
        )
        # the after-failure second is part of the floor too, so fitting the audio can't take it back
        floor = self.timing.answer_floor(supported) + (self.timing.failure_think_time if after_failure else 0.0)
        self._pause(sc, ex, secs, "answer", floor=floor)

    def _repeat_pause(self, sc: Script, ex: Exercise, text: str) -> None:
        self._pause(sc, ex, self.timing.repeat_pause(text, self.tl), "repeat", floor=self.timing.min_pause)

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

    def embed(self, sc: Script, item: Item, source: Item) -> Exercise | None:
        """Introduce a vocab part inside an easy sentence instead of on its own (#149, lesson 13
        feedback: parts of phrases the learner can already say kept coming back as single
        words), as taken out of what they know: «You know this:» ``source``, «This word is in
        it:» the part, «In another sentence. Listen, then repeat.», the sentence, what it means,
        the sentence again and a pause to repeat it. Nothing is recorded for the part: the next
        review asks the sentence, and what the learner says decides whether it counts as learned
        (``LearnerState.report``). None when no known pattern takes the part: the caller
        introduces it the usual way."""
        gen = self.generate_with(item, avoid_heard=True)
        if gen is None:
            return None
        self.used_combos.add(gen.key)
        gender, target = self._filled(gen.construction, gen.fills)
        voice = VOICE_OF[gender or "f"]
        ex = sc.new_exercise("embed", "embed", [item.id], f"embed: {target}")
        self._narr(sc, ex, self.prompts.get("embed_known"))
        self._speak(sc, ex, source.target, speaker=voice)
        self._beat(sc, ex)
        self._narr(sc, ex, self.prompts.get("embed_part"))
        self._speak(sc, ex, item.target, speaker=voice)
        self._beat(sc, ex)
        self._narr(sc, ex, self._as(gender, self.prompts.get("embed_sentence")))
        self._beat(sc, ex)
        self._speak(sc, ex, target, speaker=voice, role="embed_sentence")
        self._beat(sc, ex)
        sc.add(Segment("narrate", "instructor", self.prompts.get("embed_meaning", meaning=self._m(gen.meaning)), self.kl, 1.0,
                       self.timing.speech_estimate(gen.meaning, self.kl), "embed_meaning", ex.index))
        self._beat(sc, ex)
        self._narr(sc, ex, self.prompts.get("repeat"))
        self._speak(sc, ex, target, speaker=voice)
        self._repeat_pause(sc, ex, target)
        self.heard.add(_norm_utterance(target))
        self._gap(sc, ex)
        return ex

    def intro(self, sc: Script, item: Item) -> Exercise:
        if item.kind == "construction":
            return self._intro_construction(sc, item)
        if item.kind == "transform":
            return self._intro_transform(sc, item)
        base = self.cur.by_id.get(item.variant_of) if item.variant_of else None
        if base is not None and not item.target_m and (self.learner.has_met(base.id) or base.id in self.in_lesson):
            return self._intro_variant(sc, item, base)
        ex = sc.new_exercise("intro", "intro", [item.id], f"new: {item.target}")
        self._narr(sc, ex, self.prompts.get("intro_new", meaning=self._m(item.spoken_meaning)))
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
        if item.target_m:
            # the words follow the speaker's gender: a man's form too, in the man's voice
            self._narr(sc, ex, self.prompts.get("man_says"))
            self._speak(sc, ex, item.target_m, speaker=VOICE_OF["m"])
            self._repeat_pause(sc, ex, item.target_m)
        # end the introduction with a first real retrieval
        gender = self.speaker_gender(item)
        target = self._gendered(item, gender)
        self._narr(sc, ex, self._as(gender, self._meaning_prompt(item.spoken_meaning)))
        self._answer_pause(sc, ex, target, item, generative=False)
        self._answer(sc, ex, target, speaker=VOICE_OF[gender or "f"])
        self._gap(sc, ex)
        return ex

    def _intro_variant(self, sc: Script, item: Item, base: Item) -> Exercise:
        """A near form of something the learner has met («tvær» for «tveir», «góð» for «gott»),
        introduced as that: «You know this:» the form they have, «Here is another form:» the
        new one, said and repeated, then a short sentence it goes in, and a first retrieval."""
        ex = sc.new_exercise("intro", "intro", [item.id], f"new: {item.target}")
        self._narr(sc, ex, self.prompts.get("variant_known"))
        self._speak(sc, ex, base.target)
        self._beat(sc, ex)
        self._narr(sc, ex, self.prompts.get("variant_form", meaning=self._m(item.spoken_meaning)))
        self._beat(sc, ex)
        self._speak(sc, ex, item.target)
        self._beat(sc, ex)
        self._narr(sc, ex, self.prompts.get("repeat"))
        self._speak(sc, ex, item.target)
        self._repeat_pause(sc, ex, item.target)
        gen = self.generate_with(item, avoid_heard=True)
        if gen is not None:
            self.used_combos.add(gen.key)
            gender, sentence = self._filled(gen.construction, gen.fills)
            voice = VOICE_OF[gender or "f"]
            self._narr(sc, ex, self._as(gender, self.prompts.get("embed_sentence")))
            self._beat(sc, ex)
            self._speak(sc, ex, sentence, speaker=voice)
            self._beat(sc, ex)
            self._narr(sc, ex, self.prompts.get("embed_meaning", meaning=self._m(gen.meaning)))
            self._beat(sc, ex)
            self._speak(sc, ex, sentence, speaker=voice)
            self._repeat_pause(sc, ex, sentence)
            self.heard.add(_norm_utterance(sentence))
        self._narr(sc, ex, self._meaning_prompt(item.spoken_meaning))
        self._answer_pause(sc, ex, item.target, item, generative=False)
        self._answer(sc, ex, item.target)
        self._gap(sc, ex)
        return ex

    def _intro_construction(self, sc: Script, item: Item) -> Exercise:
        ex = sc.new_exercise("intro", "intro", [item.id], f"new pattern: {item.target}")
        fills = self.cur.example_fill(item)
        # the worked example uses words the learner has: when the authored one isn't, a known filler of the slot
        for slot, tag in item.slots.items():
            if slot in fills and not self._available(fills[slot].id):
                known = next((i for i in self.cur.items_with_tag(tag) if self._available(i.id)), None)
                if known is not None:
                    fills[slot] = known
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
        if self._fills_gendered(fills):
            # the words follow the speaker's gender: a man's form too, in the man's voice
            target_m = self.cur.resolve_slots(item, fills, "m")[0]
            self._narr(sc, ex, self.prompts.get("man_says"))
            self._speak(sc, ex, target_m, speaker=VOICE_OF["m"])
            self._repeat_pause(sc, ex, target_m)
        self._narr(sc, ex, self.prompts.get("construction_slot"))
        # a second example with a known fill, as the first retrieval
        gen = self.generate(item, exclude=fills)
        if gen is None:
            gender, target = self._filled(item, fills)
            self._narr(sc, ex, self._as(gender, self._meaning_prompt(meaning)))
            self._answer_pause(sc, ex, target, item, generative=False)
            self._answer(sc, ex, target, speaker=VOICE_OF[gender or "f"])
        else:
            gender, target = self._filled(item, gen.fills)
            self._speak(sc, ex, target, speaker=VOICE_OF[gender or "f"])
            self._beat(sc, ex)
            self._narr(sc, ex, self._as(gender, self._meaning_prompt(gen.meaning)))
            self._answer_pause(sc, ex, target, item, generative=False)
            self._answer(sc, ex, target, speaker=VOICE_OF[gender or "f"])
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

    def recall(self, sc: Script, item: Item, stage: str, met_fills: bool = False, form: str | None = None) -> Exercise:
        """``met_fills``: a recombination may fill slots with words met in earlier lessons
        and not failed, not only learned ones (a substitution drill, #151). ``form``: the
        negative or question form of a construction, for a recombination (#171)."""
        if item.kind == "transform":
            return self._recall_transform(sc, item, stage)
        if stage == "recombine":
            gen_ex = self._recombine(sc, item, met_fills, form)
            if gen_ex is not None:
                return gen_ex
            stage = "meaning"
        if stage == "situation" and not self.situation_usable(item):
            stage = "meaning"
        if stage == "cloze" and item.word_count < 3:
            stage = "hinted"
        if item.kind == "construction" and stage in ("cloze", "hinted", "meaning", "situation"):
            return self._recall_construction(sc, item, stage)

        if stage == "situation" and (cue := self.prompt_item(item)) is not None:
            return self._partner_cue_recall(sc, item, *cue)
        if stage == "situation" and not self.situation_room(item):
            stage = "meaning"  # that situation was narrated in full enough times: the short cue
        gender = self.speaker_gender(item)
        target = self._gendered(item, gender)
        voice = VOICE_OF[gender or "f"]
        ex = sc.new_exercise("recall", stage, [item.id], f"{stage}: {target}")
        if stage == "cloze":
            # say what to complete: «Ég skil…» alone could be «Ég skil.» or «Ég skil ekki.»
            self._narr(sc, ex, self._as(gender, self.prompts.get("cloze", meaning=self._m(item.spoken_meaning))))
            words = [w for w in target.split() if any(ch.isalnum() for ch in w)]
            partial = " ".join(words[:-1]) + "…"
            self._speak(sc, ex, partial, role="partial")
            self._answer_pause(sc, ex, target, item, generative=False, supported=True)
        elif stage == "hinted":
            self._narr(sc, ex, self._as(gender, self.prompts.get("hinted", meaning=self._m(item.spoken_meaning))))
            self._speak(sc, ex, target.split()[0].rstrip(".,?!"), role="hint")
            self._answer_pause(sc, ex, target, item, generative=False, supported=True)
        elif stage == "situation":
            self._narr(sc, ex, self._as(gender, self._situation(item)))  # type: ignore[arg-type]
            self._answer_pause(sc, ex, target, item, generative=True)
        else:  # meaning (also the fallback for 'dialogue' when no dialogue fits)
            self._narr(sc, ex, self._as(gender, self._meaning_prompt(item.spoken_meaning, item.context)))
            self._answer_pause(sc, ex, target, item, generative=False)
        self._answer(sc, ex, target, speaker=voice)
        if stage in ("cloze", "hinted") or item.difficulty >= 4:
            self._repeat_pause(sc, ex, target)
            self._answer(sc, ex, target, speaker=voice)
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
        gender, target = self._filled(item, gen.fills)
        ex = sc.new_exercise("recall", stage, gen.item_ids, f"{stage}: {target}")
        if stage == "hinted":
            self._narr(sc, ex, self._as(gender, self.prompts.get("hinted", meaning=self._m(gen.meaning))))
            self._speak(sc, ex, target.split()[0].rstrip(".,?!"), role="hint")
        elif stage == "situation" and item.has_situation and self.situation_room(item):
            self._narr(sc, ex, self._as(gender, self._situation(item)))  # type: ignore[arg-type]
        else:
            self._narr(sc, ex, self._as(gender, self._meaning_prompt(gen.meaning)))
        self._answer_pause(sc, ex, target, item, generative=is_generative(stage), supported=stage == "hinted")
        self._answer(sc, ex, target, speaker=VOICE_OF[gender or "f"])
        self._gap(sc, ex)
        return ex

    def _recombine(self, sc: Script, item: Item, met_fills: bool = False, form: str | None = None) -> Exercise | None:
        """Generative practice: a sentence the learner has not heard in this lesson (issue
        #105). With no such combination left, None: the caller falls back to a plain recall
        rather than replaying a line under a "make a sentence" label."""
        if item.kind == "construction":
            if self.construction_full(item):
                return None  # the ceiling: about ten generated sentences of one pattern in a lesson (#180)
            gen = self.generate(item, avoid_heard=True, met_fills=met_fills, forms=True, form=form)
        else:
            gen = self.generate_with(item, avoid_heard=True, forms=True)
        if gen is None:
            return None
        self.used_combos.add(gen.key)
        self.construction_counts[gen.construction.id] = self.construction_counts.get(gen.construction.id, 0) + 1
        self.form_counts[gen.form or "plain"] = self.form_counts.get(gen.form or "plain", 0) + 1
        if gen.form and form is None:
            self.form_extra[gen.form] = self.form_extra.get(gen.form, 0) + 1
        gender, target = self._filled(gen.construction, gen.fills, form=gen.form)
        ids = [item.id] + [i for i in gen.item_ids if i != item.id]  # the practised item comes first
        ex = sc.new_exercise("generative", "recombine", ids, f"recombine: {target}")
        # the generator only *prefers* unused combinations, so claim novelty only when true
        if item.kind == "construction":
            key = "recombine_new" if self.is_new_utterance(target) else "recombine"
        else:
            key = "recombine_vocab"
        self._narr(sc, ex, self._as(gender, self.prompts.get(key, meaning=self._m(gen.meaning))))
        self._answer_pause(sc, ex, target, item, generative=True)
        self._answer(sc, ex, target, speaker=VOICE_OF[gender or "f"])
        self._gap(sc, ex)
        return ex

    def sentence_recall(self, sc: Script, item: Item) -> Exercise | None:
        """A short item asked inside a sentence it was already in this lesson (#179): the closing recall
        of an item said in sentences asks a sentence, not the bare part. A plain meaning recall of a
        filled pattern (a heard line may repeat; it is not offered as «make a sentence»), preferring the
        item's ``context`` sentence. None when no known pattern takes the item."""
        gen = None
        want = _norm_utterance(item.context) if item.context else ""
        for _ in range(12 if want else 1):
            state = self.rng.getstate()
            cand = self.generate_with(item, ceiling=False)  # a recall of a sentence, not a generated one: no ceiling
            if cand is None:
                return None
            gen = cand
            if not want or _norm_utterance(cand.meaning) == want:
                break
            self.rng.setstate(state)  # keep the draw order stable, then try the next home
            self.rng.random()
        if gen is None:
            return None
        gender, target = self._filled(gen.construction, gen.fills, form=gen.form)
        ids = [item.id] + [i for i in gen.item_ids if i != item.id]
        ex = sc.new_exercise("recall", "meaning", ids, f"meaning: {target}")
        self._narr(sc, ex, self._as(gender, self._meaning_prompt(gen.meaning)))
        self._answer_pause(sc, ex, target, item, generative=False)
        self._answer(sc, ex, target, speaker=VOICE_OF[gender or "f"])
        self._gap(sc, ex)
        return ex

    def recombine_status(self, item: Item, met_fills: bool = False) -> str:
        """Whether a recombine exercise for ``item`` could make a sentence now: "novel" (one
        not yet heard this lesson), "heard" (only already-presented sentences are possible)
        or "impossible" (no known fills at all). No side effects: the generator's random
        state is restored."""
        state = self.rng.getstate()
        try:
            def gen(it: Item, avoid_heard: bool = False) -> Generated | None:
                if it.kind == "construction":
                    return self.generate(it, avoid_heard=avoid_heard, met_fills=met_fills, forms=True)
                return self.generate_with(it, avoid_heard=avoid_heard, forms=True)

            if item.kind == "construction" and self.construction_full(item):
                return "heard"
            if gen(item, avoid_heard=True) is not None:
                return "novel"
            return "heard" if gen(item) is not None else "impossible"
        finally:
            self.rng.setstate(state)

    def _recall_transform(self, sc: Script, item: Item, stage: str) -> Exercise:
        ex = sc.new_exercise("recall", stage, [item.id], f"{stage}: {item.meaning}")
        exm = self._pick_example(item)
        self._transform_prompt(sc, ex, item, exm, hint=(stage == "hinted"))
        self._gap(sc, ex)
        return ex

    def _transform_prompt(self, sc: Script, ex: Exercise, item: Item, exm: TransformExample, hint: bool = False) -> None:
        """When the example's words follow the speaker's gender, alternate forms like any
        gendered item: the source in that voice, and — only when the learner's own answer
        changes («Ég var þreyttur í gær.») — an announcement and the answer in that voice.
        A result about someone else («Hún er glöð.») stays as it is."""
        gender = self.speaker_gender(item, gendered=bool(exm.source_m or exm.result_m))
        man = gender == "m"
        source = exm.source_m if man and exm.source_m else exm.source
        result = exm.result_m if man and exm.result_m else exm.result
        answer_gender = gender if exm.result_m else None
        self._narr(sc, ex, self._as(answer_gender, item.instruction))
        self._speak(sc, ex, source, role="source", speaker=VOICE_OF[gender or "f"])
        if hint:
            self._speak(sc, ex, result.split()[0].rstrip(".,?!"), role="hint")
        self._answer_pause(sc, ex, result, item, generative=True, supported=hint)
        self._answer(sc, ex, result, speaker=VOICE_OF[answer_gender or "f"])
        self.used_examples.add(item.id + ":" + exm.source)

    def _pick_example(self, item: Item) -> TransformExample:
        fresh = [e for e in item.examples if item.id + ":" + e.source not in self.used_examples]
        pool = fresh or item.examples
        return self.rng.choice(pool)

    # ------------------------------------------------------------ generation

    def generate(
        self,
        construction: Item,
        *,
        exclude: dict[str, Item] | None = None,
        prefer_unused: bool = True,
        fixed: dict[str, Item] | None = None,
        avoid_heard: bool = False,
        met_fills: bool = False,
        forms: bool = False,
        form: str | None = None,
    ) -> Generated | None:
        """Fill a construction with words the learner knows; prefer combos not yet used.
        ``fixed`` pins slots to specific fills (a situation's binding). ``avoid_heard`` drops
        combinations whose sentence was already presented this lesson (None if none is left).
        ``met_fills`` also takes words met in an earlier lesson and not failed
        (``_frame_available``), for substitution drills (#151). ``forms`` lets the sentence be
        the construction's negative or question form too, once the note that teaches that form has
        been heard (#171); ``form`` asks for one (None if the construction has none, or it isn't
        taught yet)."""
        usable = self._frame_available if met_fills else self._available
        options: dict[str, list[Item]] = {}
        for slot, tag in construction.slots.items():
            if fixed and slot in fixed:
                options[slot] = [fixed[slot]]
                continue
            cands = [i for i in self.cur.items_with_tag(tag) if usable(i.id)]
            if exclude and slot in exclude:
                cands = [c for c in cands if c.id != exclude[slot].id]
            if not cands:
                return None
            options[slot] = cands
        slots = list(options)
        combos = self._product(options, slots)
        self.rng.shuffle(combos)
        taught = self.forms_taught()
        if form:
            if form not in construction.forms or form not in taught:
                return None
            order: list[str | None] = [form]
        else:
            order = self._form_order([None] + ([f for f in construction.forms if f in taught] if forms else []))
        for chosen_form in order:
            picks = [(chosen_form, c) for c in combos]
            if avoid_heard:
                picks = [
                    (f, c) for f, c in picks
                    if not {_norm_utterance(self.cur.resolve_slots(construction, c, g, f)[0]) for g in "fm"} & self.heard
                ]
            if not picks:
                continue
            if prefer_unused:
                unused = [(f, c) for f, c in picks if _combo_key(construction, c, f) not in self.used_combos]
                picks = unused or picks
            if chosen_form:
                # a form adds variety rather than replacing: when the plain sentence of that combination was heard
                picks = [(f, c) for f, c in picks if _combo_key(construction, c) in self.used_combos] or picks
            fills = picks[0][1]
            target, meaning = self.cur.resolve_slots(construction, fills, form=chosen_form)
            return Generated(construction, fills, target, meaning, chosen_form)
        return None

    def _form_order(self, options: list[str | None]) -> list[str | None]:
        """The forms a generated sentence may take, the one furthest below its share first (#171
        review): the plain sentence is at least half of a lesson's generated sentences and each other
        form at most about a quarter, so the newest form doesn't crowd out the sentences the trip
        needs; a form taught in this lesson takes only ``FORM_EXTRA_NEW`` sentences beyond its
        practice right after the note (``do_forms_practice``)."""
        if len(options) == 1:
            return options
        taught = self.forms_taught()
        share = min(FORM_SHARE, 0.5 / max(1, len(taught)))
        desired = {f: (share if f else 1 - share * len(taught)) for f in options}
        total = sum(self.form_counts.values())
        fresh = {n.teaches for n in self.cur.notes if n.teaches and n.id in self.notes_taught and self.learner.notes_heard.get(n.id, 0) == 0}
        ranked = []
        for f in options:
            if f in fresh and self.form_extra.get(f, 0) >= FORM_EXTRA_NEW:
                continue
            actual = self.form_counts.get(f or "plain", 0) / total if total else 0.0
            if f and total >= FORM_CAP_FROM:
                # the shares this sentence would leave (#180: the plain sentences stay at least half of the
                # lesson's: a cap tested before the sentence let the forms settle at the cap, plain just under half)
                forms_after = (total - self.form_counts.get("plain", 0) + 1) / (total + 1)
                form_after = (self.form_counts.get(f, 0) + 1) / (total + 1)
                if form_after > FORM_HARD_CAP or forms_after > FORM_ALL_HARD_CAP:
                    continue  # at its share: the supply may run short rather than the forms crowd out the plain sentences
            ranked.append((-(desired[f] - actual) + self.rng.random() * 0.01, f))
        return [f for _, f in sorted(ranked, key=lambda t: t[0])] or [None]

    def construction_full(self, c: Item) -> bool:
        """A construction that has had ``CONSTRUCTION_CEILING`` generated sentences this lesson (#180). The
        backstop: it stops a word's sentences, and the pattern's own recombinations, going to that pattern.
        Its introduction and its timed recalls (not generated sentences) are not held to it."""
        return self.construction_counts.get(c.id, 0) >= CONSTRUCTION_CEILING

    def generate_with(self, vocab: Item, avoid_heard: bool = False, forms: bool = False, ceiling: bool = True) -> Generated | None:
        """Find a known construction with a slot that accepts ``vocab`` and fill it.
        ``avoid_heard``: only sentences not yet presented this lesson (None if none is left).
        ``forms``: the construction's negative or question form may do (#171)."""
        homes = []
        for c in self.cur.items:
            if c.kind != "construction" or not self._frame_available(c.id):
                continue
            for slot, tag in c.slots.items():
                if tag in vocab.tags:
                    homes.append((c, slot))
        if not homes:
            return None
        self.rng.shuffle(homes)
        # rotate (#180): the home with the fewest sentences this lesson first, so a new pattern with many
        # fillers doesn't win most draws; one that is full takes no more (the ceiling, for a word with one home)
        if ceiling:
            homes = [h for h in homes if not self.construction_full(h[0])]
        homes.sort(key=lambda h: self.construction_counts.get(h[0].id, 0))
        fallback = None
        for c, slot in homes:
            gen = self.generate(c, fixed={slot: vocab}, avoid_heard=avoid_heard, forms=forms)
            if gen is None:
                continue
            if gen.key not in self.used_combos:
                return gen
            fallback = fallback or gen
        return fallback

    def _available(self, item_id: str) -> bool:
        """Known, or introduced earlier this lesson: usable as a part of a generated sentence."""
        return self.learner.knows(item_id) or item_id in self.in_lesson

    def _frame_available(self, item_id: str) -> bool:
        """A construction as the frame for recombining a filler (issue #80): available as
        a part, or met in an earlier lesson and not failed at its last report. The
        construction's own review already recombines it with known fills while it is being
        learned; a filler reviewed the same day may use it for the very same sentences.
        Before, «Ég ætla að fá {thing}» met yesterday could not frame «vatn», which was then
        drilled as "say: water" five times in its first lesson."""
        if self._available(item_id):
            return True
        st = self.learner.items.get(item_id)
        return bool(st and st.stage != "intro" and st.last_outcome != "not_recalled")

    def situation_usable(self, item: Item) -> bool:
        """Whether ``item``'s situation can be practised now: every fill it names is available
        ("Ask if she speaks German." waits until þýsku is known)."""
        return (item.has_situation
                and all(self._available(f.id) for f in self.cur.situation_fills(item).values()))

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
        self._narr(sc, ex, self.prompts.get("milestone_intro" if note.milestone or note.teaches else "aside"))
        self._speak_note_text(sc, ex, note.text)
        self._beat(sc, ex)
        self._narr(sc, ex, self.prompts.get("milestone_end" if note.milestone or note.teaches else "aside_end"))
        self._gap(sc, ex)
        return ex

    # ---------------------------------------------------------------- connect

    def connect(self, sc: Script, items: list[Item]) -> Exercise:
        """Two already-known items in one exercise, used for an arc's connected use and to
        break a drill streak.

        If ``items[1]`` has a bridge written for ``items[0]`` (``partner_cue_after``), this is
        an ``exchange``: one scene, with the partner's line spoken between the two answers.
        Otherwise there is no relation to show, so it is presented as mixed review (stage
        ``recombine``): two independent situations, framed as review and joined by a neutral
        transition, never as a connection or a continuation."""
        first, second = items[0], items[1]
        ids = [first.id, second.id]
        bridged = bool(second.partner_cue) and second.partner_cue_after == first.id
        # the partner speaks in the voice the narration's he/she implies; the learner's model
        # answers take the other voice, so the two sides never sound alike — and words that
        # follow the speaker's gender take that voice's form, announced
        partner = second.partner_cue_speaker if bridged else "native_b"
        learner_voice = _other_voice(partner)
        first_gender, first_target, first_meaning = self._connect_turn(first, learner_voice)
        second_gender, second_target, second_meaning = self._connect_turn(second, learner_voice)
        label = f"connect: {first.id}+{second.id}" if bridged else f"mixed review: {first.id}+{second.id}"
        ex = sc.new_exercise("connect", "exchange" if bridged else "recombine", ids, label)
        if bridged or not self._mixed_review_said:
            self._narr(sc, ex, self.prompts.get("connect_intro" if bridged else "mixed_review_intro"))
            self._beat(sc, ex)
            self._mixed_review_said = self._mixed_review_said or not bridged
        # a bridge's own scene replaces the items' standalone situations
        self._narr(sc, ex, self._as(first_gender, second.partner_cue_setup if bridged else self._cue(first, first_meaning)))  # type: ignore[arg-type]
        self._answer_pause(sc, ex, first_target, first, generative=True)
        self._answer(sc, ex, first_target, speaker=learner_voice)
        self._beat(sc, ex)
        if bridged:
            self._speak(sc, ex, second.partner_cue, speaker=partner)
            self._beat(sc, ex)
            if self.translate_partner and self.learner.bridges_heard.get(second.id, 0) < BRIDGE_GLOSS_ENCOUNTERS:
                # early encounters say what the partner said; later ones rely on comprehension
                self._narr(sc, ex, self.prompts.get("dialogue_partner_said", meaning=second.partner_cue_meaning))
                self._beat(sc, ex)
        else:
            self._narr(sc, ex, self.prompts.get("connect_next"))
        self._narr(sc, ex, self._as(second_gender, second.partner_cue_situation if bridged else self._cue(second, second_meaning)))  # type: ignore[arg-type]
        self._answer_pause(sc, ex, second_target, second, generative=True)
        self._answer(sc, ex, second_target, speaker=learner_voice)
        self._gap(sc, ex)
        return ex

    def _connect_turn(self, item: Item, voice: str) -> tuple[str | None, str, str | None]:
        """(speaker gender or None, spoken target, filled meaning or None) of a ``connect()`` turn
        answered in ``voice``. A construction is filled first, with the fills its situation names
        pinned, since connect() narrates that situation; its meaning is the filled sentence's (#178)."""
        if item.kind != "construction":
            gender = self.speaker_gender(item, voice)
            return gender, self._gendered(item, gender), None
        if not self.situation_usable(item):
            # the planner never pairs such an item; refuse rather than speak an unmet fill
            raise ValueError(f"connect(): {item.id!r}'s situation names a fill the learner doesn't have yet")
        fixed = self.cur.situation_fills(item)
        gen = self.generate(item, fixed=fixed)
        if gen is None:
            fills = {**self.cur.example_fill(item), **fixed}
            return (*self._filled(item, fills, voice), self.cur.resolve_slots(item, fills)[1])
        self.used_combos.add(gen.key)
        return (*self._filled(item, gen.fills, voice), gen.meaning)

    # -------------------------------------------------------------- dialogue

    def dialogue(
        self,
        sc: Script,
        dlg: Dialogue,
        *,
        replay: bool = False,
        max_turns: int | None = None,
        assisted: bool = True,
        listening: frozenset[str] | set[str] = frozenset(),
        tried: frozenset[str] | set[str] = frozenset(),
    ) -> Exercise:
        """Play a dialogue; ``max_turns`` lets early encounters stop after a few turns.

        ``listening`` names required items the learner hasn't learned (H8, #149 step 3): their
        turns are heard, not asked for: «Here you would say:», the line, what it means. The
        scene carries the meaning; nothing is expected back for them.

        ``assisted`` (the first encounter) translates partner lines and cues every turn. Later
        encounters drop both once the partner has said something: their line is the cue. A
        turn before any partner line always keeps its cue."""
        turns = dlg.turns if max_turns is None else dlg.turns[: max(1, max_turns)]
        ids = [t.expect for t in turns if t.expect] + [r for r in dlg.requires if r not in {t.expect for t in turns}]
        label = f"dialogue: {dlg.id}" + ("" if len(turns) == len(dlg.turns) else f" ({len(turns)}/{len(dlg.turns)} turns)")
        ex = sc.new_exercise("dialogue", "dialogue", ids, label)
        partner = dlg.partner_speaker
        learner_voice = _other_voice(partner)
        # the switch from drills to a conversation is the biggest change of mode in a lesson
        if listening or tried:
            self._narr(sc, ex, self.prompts.get("listening_intro"))
        self._narr(sc, ex, self.prompts.get("dialogue_start"))
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
            gender = None
            meaning_text = ""
            if turn.expect:
                item = self.cur.item(turn.expect)
                meaning_text = item.spoken_meaning
                gender = self.speaker_gender(item, learner_voice)
                expected = self._gendered(item, gender)
                if item.kind == "construction":
                    # every spoken part must be a required item (validate() enforces this too)
                    unbound = set(item.slots) - set(turn.expect_fill)
                    if unbound:
                        raise ValueError(f"dialogue {dlg.id!r}: construction turn {item.id!r} leaves slots {sorted(unbound)} unbound")
                    fills = {s: self.cur.by_id[f] for s, f in turn.expect_fill.items()}
                    gender, expected = self._filled(item, fills, learner_voice)
                    meaning_text = self.cur.resolve_slots(item, fills)[1]
            else:
                item = None
                gender = GENDER_OF[learner_voice] if turn.expect_text_m else None
                expected = (turn.expect_text_m if gender == "m" else turn.expect_text) or ""
            heard_only = item is not None and item.id in listening  # no task cue: nothing is asked
            if heard_only:
                pass
            elif assisted or not heard_partner:
                self._narr(sc, ex, self._as(gender, turn.cue))
            elif gender:
                self._narr(sc, ex, self.prompts.get(f"speak_as_{gender}_alone"))
            if item is not None and item.id in tried:
                self._narr(sc, ex, self.prompts.get("listening_try"))  # a line they can say part of: «Try it.»
            if heard_only:
                self._narr(sc, ex, self.prompts.get("listening_line"))
                self._answer(sc, ex, expected, speaker=learner_voice)
                self._beat(sc, ex)
                self._narr(sc, ex, self._m(meaning_text))
            else:
                self._answer_pause(sc, ex, expected, item, generative=True)
                self._answer(sc, ex, expected, speaker=learner_voice)
            lines.append((learner_voice, expected))
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
