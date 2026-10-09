"""Listening exercises of a lesson's second half (#248, LEARNING-DESIGN concept 2 and 3, O2, O5, G16).

Once the lesson has delivered what it set out to teach, the time that is left goes round a rotation instead of saying
known sentences again::

    hear the scene → pick out information × 2 → catch an unknown word × 1 → use one of today's expressions → again

- **Pick out information** (``generated_pick_out``): a sentence of a known pattern, built from words the learner knows, is heard;
  the instructor asks for one piece of information in it (the price, the time) and the learner says it. The probe that names
  the piece lives with the pattern (``Item.information_probes``): never inferred from a slot's name.
- **Catch an unknown word** (``catch_unknown``): a line the partner of a scene said, with exactly one word the learner does not
  know. The learner says the word and asks what it means (the repair phrase they already can say); the word's meaning is
  authored with the line (``Turn.word_glosses``), never guessed from the line's translation.

Both are listening exercises of their own kind. What was only heard is not recorded as practised (no ``Planner._record``): hearing
a pattern or an unknown word does not make it learnt, and the next day's review does not ask for it.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, replace
from typing import Callable

from .exercises import _norm_utterance, _other_voice
from .script import Script

# the phrase that asks what a word means; the catch-an-unknown-word exercise only runs once the learner can say it
REPAIR_ITEM = "hvad_thydir_thetta"

# the same split as Planner._fixed_text_words (what counts as a word)
WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def tokens(text: str) -> list[str]:
    return WORD.findall(text)


def language(code: str) -> str:
    return code.split("-")[0].lower()


def kind_has_room(sc: Script, kind: str, limit: int = 3) -> bool:
    """False when the last ``limit`` exercises are all of ``kind``: no kind of exercise runs on for more than ``limit``."""
    tail = [e for e in sc.exercises if e.kind != "opening"][-limit:]
    return len(tail) < limit or any(e.kind != kind for e in tail)


class SecondHalfRotation:
    """The order the second half takes its exercises in. ``play`` offers each kind in turn; one that cannot be added (nothing to
    hear, no time) passes to the next, and the cursor moves on either way, so the rotation never sticks on a kind."""

    order = ("heard", "pick_out", "pick_out", "catch_unknown", "today")

    def __init__(self) -> None:
        self.cursor = 0

    def play(self, emit: Callable[[str], bool]) -> bool:
        """``emit`` returns True only when it really added an exercise."""
        for _ in self.order:
            kind = self.order[self.cursor]
            self.cursor = (self.cursor + 1) % len(self.order)
            if emit(kind):
                return True
        return False


@dataclass(frozen=True)
class ListeningTask:
    kind: str  # pick_out | catch_unknown
    source: str  # where the line comes from (the exercise's label)
    scene: str  # the scene the line belongs to, said first; "" for none
    line: str  # the sentence heard
    answer: str  # what the learner says
    meaning: str  # the answer's meaning
    prompt_key: str
    speaker: str = "native_b"
    item_ids: tuple[str, ...] = ()
    repair: str = ""  # catch_unknown: the phrase that asks what the word means
    ask: str = ""  # pick_out of a line holding several pieces: the question that names the one to find; else the plain question of the kind
    pattern: str = ""  # what the planner caps per lesson: a construction for a generated sentence, the line for a scene's line


def generated_pick_out(cur, gen, probe: dict, known_words: set[str], scene: str, speaker: str = "native_b") -> ListeningTask | None:
    """A pick-out exercise from a generated sentence ``gen`` and one of its pattern's probes; None when the sentence does not
    hold the piece of information, holds a word the learner does not know, or a probe has no meaning in the learner's language."""
    gloss = probe["meanings"].get(language(cur.known_lang))
    if not gloss or gen.form is not None:
        return None
    gender = "m" if speaker == "native_b" else "f"
    line, _ = cur.resolve_slots(gen.construction, gen.fills, gender, gen.form)
    # the slot resolution of the pattern itself resolves the probe's answer: agreement and number forms are not re-implemented here
    fragment = replace(gen.construction, target=probe["answer"], meaning=gloss, meaning_spoken="", negative="", question="")
    answer, meaning = cur.resolve_slots(fragment, gen.fills, gender)
    if "{" in answer or "{" in meaning:
        return None
    spans = [(m.group().lower(), m.start(), m.end()) for m in WORD.finditer(line)]
    words = [w for w, _, _ in spans]
    part = [w.lower() for w in tokens(answer)]
    # the model answer must be a stretch of the sentence that was heard, and is said as it was written there (a slot at the start of
    # the probe's template would capitalise it)
    at = next((i for i in range(len(words)) if part and words[i : i + len(part)] == part), None)
    if at is None:
        return None
    answer = line[spans[at][1] : spans[at + len(part) - 1][2]]
    if gloss.startswith("{") and meaning[:1].isupper():
        meaning = meaning[:1].lower() + meaning[1:]
    if any(w not in known_words for w in words):
        return None
    return ListeningTask(
        kind="pick_out",
        source=f"{gen.construction.id}: {line}",
        scene=scene,
        line=line,
        answer=answer,
        meaning=meaning,
        prompt_key=f"pick_out_{probe['kind']}",
        speaker=speaker,
        item_ids=(gen.construction.id,),
        pattern=gen.construction.id,
    )


def partner_pick_out(line, probe: dict, known_words: set[str], known_lang: str, *, source: str, scene: str, speaker: str = "native_b") -> ListeningTask | None:
    """A pick-out from a scene's partner ``line`` (#248 step 2): the learner has to find one piece of information in wording they haven't drilled, and says
    it in Icelandic as it was said. ``probe`` is one of the line's ``probes``. None when the learner can't say the answer yet (a word of it they don't know)
    or the probe has no meaning (or question) in their language."""
    lang = language(known_lang)
    meaning = probe["meanings"].get(lang)
    ask = (probe.get("ask") or {}).get(lang, "")
    if not meaning or (len(line.probes) > 1 and not ask):
        return None
    spans = [(m.group().lower(), m.start(), m.end()) for m in WORD.finditer(line.say)]
    words = [w for w, _, _ in spans]
    part = [w.lower() for w in tokens(probe["answer"])]
    at = next((i for i in range(len(words)) if part and words[i : i + len(part)] == part), None)
    if at is None or any(w not in known_words for w in part):
        return None
    return ListeningTask(
        kind="pick_out",
        source=source,
        scene=scene,
        line=line.say,
        answer=line.say[spans[at][1] : spans[at + len(part) - 1][2]],
        meaning=meaning,
        prompt_key=f"pick_out_{probe['kind']}",
        speaker=speaker,
        ask=ask,
        pattern=line.say,
    )


def catch_unknown(
    line: str,
    glosses: dict,
    known_words: set[str],
    known_lang: str,
    repair,
    *,
    repair_known: bool,
    source: str,
    scene: str,
    speaker: str = "native_b",
) -> ListeningTask | None:
    """An unknown-word exercise from a partner's ``line``; None unless the learner can already say the repair phrase, the line holds exactly
    one word they do not know (counted by occurrence, so a word said twice excludes the line) and that word has an authored meaning."""
    if not repair_known:
        return None
    unknown = [w for w in tokens(line) if w.lower() not in known_words]
    if len(unknown) != 1:
        return None
    word = unknown[0]
    meaning = (glosses or {}).get(word.lower(), {}).get(language(known_lang))
    if not meaning:
        return None
    return ListeningTask(
        kind="catch_unknown",
        source=f"{source}: {line}",
        scene=scene,
        line=line,
        answer=word,
        meaning=meaning,
        prompt_key="catch_unknown",
        speaker=speaker,
        item_ids=(repair.id,),
        repair=repair.target,
    )


def _build(b, sc: Script, task: ListeningTask) -> None:
    ex = sc.new_exercise(task.kind, None, list(task.item_ids), task.source)
    if task.scene:
        b._frame(sc, ex, task.scene)
    b._speak(sc, ex, task.line, speaker=task.speaker, role="listening_line")
    b._beat(sc, ex)
    # named after the scene it comes from when there is one: whose line it was; otherwise the plain question
    who = b.prompts.get("speaker_he" if task.speaker == "native_b" else "speaker_she")
    question = task.ask or (b.prompts.get(task.prompt_key + "_scene", who=who) if task.scene and task.kind == "pick_out" else b.prompts.get(task.prompt_key))
    b._narr(sc, ex, question)
    expected = f"{task.answer} {task.repair}" if task.repair else task.answer
    b._pause(sc, ex, b.timing.answer_pause(expected, b.tl, generative=True), "answer", floor=b.timing.answer_floor())
    voice = _other_voice(task.speaker) if task.repair else task.speaker
    b._answer(sc, ex, task.answer, speaker=voice)
    b._beat(sc, ex)
    if task.repair:
        b._answer(sc, ex, task.repair, speaker=voice)
        b._beat(sc, ex)
    b._narr(sc, ex, b._m(task.meaning))
    b._beat(sc, ex)
    b._speak(sc, ex, task.line, speaker=task.speaker, role="listening_replay")
    b._gap(sc, ex)


def append_task(b, sc: Script, task: ListeningTask, remaining: float):
    """Add ``task`` to ``sc`` when its kind has room and it fits in ``remaining`` seconds; the exercise, or None. The exercise is first built
    in a scratch script, with the builder's memory of what was said put back, so a task that does not fit leaves no trace."""
    if not kind_has_room(sc, task.kind):
        return None
    heard, said, recent = set(b.heard), Counter(b.said), list(b.recent_answers)
    scratch = Script(sc.lesson_number, "", sc.target_lang, sc.known_lang)
    _build(b, scratch, task)
    cost = scratch.total_duration
    b.heard.clear(); b.heard.update(heard)
    b.said.clear(); b.said.update(said)
    b.recent_answers = recent
    if cost > remaining:
        return None
    _build(b, sc, task)
    return sc.exercises[-1]


def key_of(task: ListeningTask) -> tuple[str, str, str]:
    return (task.kind, _norm_utterance(task.line), _norm_utterance(task.answer))
