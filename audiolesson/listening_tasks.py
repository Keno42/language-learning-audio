"""Listening exercises of a lesson's second half (#248, LEARNING-DESIGN concept 2 and 3, O2, O5, G16).

Once the lesson has delivered what it set out to teach, the time that is left goes round a rotation instead of saying
known sentences again::

    hear the scene → pick out information × 2 → catch an unknown word × 1 → use one of today's expressions → again

- **Pick out information** (``generated_pick_out``): a sentence of a known pattern, built from words the learner knows, is heard;
  the instructor asks for one piece of information in it (the price, the time) and the learner says it. The probe that names
  the piece lives with the pattern (``Item.information_probes``): never inferred from a slot's name.
- **Catch an unknown word** (``catch_unknown``): a line the partner of a scene said, with exactly one word the learner does not
  know. Its place is cued through the understood meaning. The learner asks «Hvað þýðir {word}?», using the repair phrase
  they already can say; the word's gloss and optional pointer are authored with the line (``Turn.word_glosses``).

Both are listening exercises of their own kind. What was only heard is not recorded as practised (no ``Planner._record``): hearing
a pattern or an unknown word does not make it learnt, and the next day's review does not ask for it.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, replace
from typing import Callable

from .exercises import _norm_utterance, _other_voice
from .script import Exercise, Script
from .text import WORD
from .listening_cues import unknown_cue

CATCH_INTRO = "new (catch)"  # the label of an intro made through a catch (#339): the catch's own turn (``transitions.mode``)

# the phrase that asks what a word means; the catch-an-unknown-word exercise only runs once the learner can say it
REPAIR_ITEM = "hvad_thydir_thetta"


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
    repair: str = ""  # catch_unknown: the complete question, with the heard word in place of þetta
    ask: str = ""  # pick_out of a line holding several pieces: the question that names the one to find; else the plain question of the kind
    pattern: str = ""  # what the planner caps per lesson: a construction for a generated sentence, the partner turn for a scene's line
    pieces: int = 1  # how many pieces of information the line holds (a generated sentence holds the frame and one)
    cue: str = ""  # catch_unknown: the masked meaning or authored pointer


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
    if len(line.probes) == 1 and len(words) - len(part) <= len(part):
        return None  # a single piece that is most of the line is an echo of it (#248 step 2 review): nothing is found
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
        pattern=source.rsplit(":", 2)[0],  # the partner turn: its variants and listening lines count as one a lesson
        pieces=len(line.probes),
    )


def word_as_asked(line: str, word: str) -> str:
    """The heard word as the learner says it inside the question (#272): lower-cased when it only had a capital because it began a sentence, kept when it is
    a name in the middle of one."""
    m = re.search(rf"(^|[.!?]\s+)({re.escape(word)})(?!\w)", line)
    return word[:1].lower() + word[1:] if m else word


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
    line_meaning: str = "",
) -> ListeningTask | None:
    """An unknown-word exercise from a partner's ``line``; None unless the learner can already say the repair phrase, the line holds exactly
    one word they do not know (counted by occurrence, so a word said twice excludes the line), and that word has an authored
    meaning and a cue locating it in the understood part. ``answer`` stays the word for the planner's per-word deduplication;
    ``repair`` is the complete question the learner says."""
    if not repair_known:
        return None
    unknown = [w for w in tokens(line) if w.lower() not in known_words]
    if len(unknown) != 1:
        return None
    word = unknown[0]
    spoken = word_as_asked(line, word)
    gloss = (glosses or {}).get(word.lower(), {})
    meaning = gloss.get(language(known_lang))
    cue = unknown_cue(line_meaning, gloss, known_lang)
    if not meaning or cue is None:
        return None
    question, replacements = re.subn(r"\bþetta\b", lambda _: spoken, repair.target, count=1, flags=re.IGNORECASE)
    if replacements != 1:
        return None
    cue_kind, cue_text = cue
    return ListeningTask(
        kind="catch_unknown",
        source=f"{source}: {line}",
        scene=scene,
        line=line,
        answer=word,
        meaning=meaning,
        prompt_key=f"catch_unknown_{cue_kind}",
        speaker=speaker,
        item_ids=(repair.id,),
        repair=question,
        cue=cue_text,
    )


def _build(b, sc: Script, task: ListeningTask, introduces: str = "") -> None:
    """``introduces`` (#339): the id of a new item this catch introduces; the exercise is then its introduction (kind ``intro``), so the planner records it like one."""
    if introduces:
        ex = sc.new_exercise("intro", "intro", [introduces], f"{CATCH_INTRO}: {word_as_asked(task.line, task.answer)}")
    else:
        ex = sc.new_exercise(task.kind, ("multi" if task.pieces > 1 else "single") if task.kind == "pick_out" else None, list(task.item_ids), task.source)
    if task.scene:
        b._frame(sc, ex, task.scene)
    who = b.prompts.get("speaker_he" if task.speaker == "native_b" else "speaker_she")
    if task.kind == "pick_out":
        # #303: concept 2 is finding the information one needs, so the need is named before the line (after the scene), and the learner listens for it
        b._narr(sc, ex, b.prompts.get("pick_out_need_ask", ask=task.ask) if task.ask else b.prompts.get(task.prompt_key.replace("pick_out_", "pick_out_need_", 1)))
    b._speak(sc, ex, task.line, speaker=task.speaker, role="listening_line")
    b._beat(sc, ex)
    if task.kind == "catch_unknown":
        question = b.prompts.get(task.prompt_key, context=task.cue, pointer=task.cue)
        b._narr(sc, ex, question)
    expected = task.repair or task.answer
    # a pick-out's answer is words the learner has just heard, found, not made: a recall's pause, not the generative one (lesson 28: 4.2-4.5 s for «klukkan
    # fimm» felt long); the catch's question is made, and keeps it
    b._pause(sc, ex, b.timing.answer_pause(expected, b.tl, generative=task.kind != "pick_out"), "answer", floor=b.timing.answer_floor())
    voice = _other_voice(task.speaker)  # the learner's answer is never in the voice of the line it answers (lesson 28; the catch's question already was not)
    if task.kind == "pick_out":
        b._frame(sc, ex, b.prompts.get("pick_out_answer"))  # #335: the model answer is announced (a line that leads into an example is a framing line with its beat, #241), so it is not heard as the line going on
    b._answer(sc, ex, expected, speaker=voice)
    b._beat(sc, ex)
    if task.kind == "catch_unknown":
        # #279: the partner answered the question; the narrator reports it, the line is then heard again with the meaning known
        b._narr(sc, ex, b.prompts.get("catch_unknown_told", who=who[:1].upper() + who[1:]))
        b._speak(sc, ex, word_as_asked(task.line, task.answer), speaker=task.speaker, role="listening_word")  # as the learner asked it: «og», not «Og» (the line's capital)
        b._narr(sc, ex, b.prompts.get("catch_unknown_means", meaning=b._m(task.meaning)))
        b._beat(sc, ex)
        b._frame(sc, ex, b.prompts.get("catch_unknown_again"))
    else:
        b._narr(sc, ex, b._m(task.meaning))
        b._beat(sc, ex)
        b._frame(sc, ex, b.prompts.get("pick_out_again"))  # #335: the replay is announced
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


def introduce_by_catch(b, sc: Script, task: ListeningTask, item) -> Exercise:
    """A new word's introduction through the catch (#339, the owner's decision): the partner's line, the cue through the meaning understood, «Hvað þýðir …?»,
    what the partner says, the line again; the item's usual ladder follows. Counts as the introduction (said once)."""
    b.said[_norm_utterance(item.target)] += 1
    _build(b, sc, task, introduces=item.id)
    return sc.exercises[-1]
