"""What each kind of exercise is to the learner, and the way in and back between tasks.

- ``MODES``: the mode of each exercise kind (a listening task, a conversation, an aside, a drill …). A test keeps every kind the code builds in
  it, so a new kind is classified the day it is written.
- The way back (lesson 34, #387; lessons 37 and 39, #415, #425): ``WAY_BACK`` is the line that ends a listening task or a conversation where a
  drill follows. The way in (#427, #433): ``WAY_IN`` opens a listening task that would start with its target-language line, a catch with no
  scene. ``close_tasks`` says both on the finished script, where the next exercise is known and the time they take moves nothing the lesson
  holds.
- The check: ``unmarked_turns`` lists every change of task whose line is missing or out of place, an aside's end line included (``END_LINES``),
  as ``claims.unkept_claims`` does for promises (0 expected; a row of ``tools/replay_lesson.py`` and a test over a simulated course).
- The kinds the lesson's rhythm counts, from ``MODES``: the scene units (#273) and the listening tasks (#421).

The ledger's family «pick-out-turns» (the turns between and inside tasks) was remarked in eight lessons from 24 to 39, each turn fixed on its
own; this is one home for its part between tasks. Not here: the turns inside a pick-out (``listening_tasks._build``: #306, #343, #353, #411),
the closing block's content (#421, #435, #437), and an aside's end («Back to the lesson.», «Let's continue.»), which ``Builder.note`` says
whatever follows.
"""

from __future__ import annotations

from dataclasses import replace

from .claims import _templates
from .listening_tasks import CATCH_INTRO
from .prompts import Prompts
from .script import Exercise, Script, Segment
from .timing import Timing

# what each exercise kind is to the learner
MODES = {
    "pick_out": "listening",  # #248
    "catch_unknown": "listening",  # #339
    "dialogue": "conversation",  # an authored dialogue, a theme level played or heard again
    "note": "aside",
    "closing": "closing",
    "opening": "opening",
    "intro": "drill",
    "model": "drill",
    "embed": "drill",
    "recall": "drill",
    "generative": "drill",
    "connect": "drill",
}
# the modes that open with their own line («Listen …», a conversation's setting, «A note:», the closing): no way back comes before them
OPENS_WITH_ITS_OWN_LINE = {"listening", "conversation", "aside", "closing"}
# the line that ends a mode when the next exercise does not open with its own (#387: «Back to speaking.», as an aside ends with «Back to the
# lesson.»; #415: «That's the end of the conversation.»)
WAY_BACK = {"listening": "listening_back", "conversation": "conversation_back"}
# the ways back the builder writes into every exercise of their mode, so the lesson's time counts them (``Builder.close_conversations``);
# ``close_tasks`` drops them where they are not wanted, and inserts the others where they are
BUILT_IN = {"conversation_back"}
# the line that opens a mode when its exercise would otherwise start with a target-language line straight after the task before: a catch with no
# scene to frame it, such as one that introduces a word through its home sentence (``Builder.whole_home``); a pick-out always opens with its need
WAY_IN = {"listening": "listen"}
# the lines the builder says at the end of every exercise of a mode, whatever follows: an aside ends «Back to the lesson.» or, for a milestone,
# «Let's continue.» (``Builder.note``). Whether they should follow ``WAY_BACK``'s rule (none before a task that opens with its own line) is open
END_LINES = {"aside": ("aside_end", "milestone_end")}
SPOKEN = ("speak", "narrate", "answer")
# the kinds the lesson's rhythm counts: a scene unit (#273: no fifteen minutes without one) and a listening task (the stretch before the closing
# holds one at a time, #421). From ``MODES`` by kind, so a catch that introduces a new word (#339, kind ``intro``, a listening task to ``mode``)
# is left out of both, as before
SCENE_UNIT_KINDS = frozenset(k for k, m in MODES.items() if m in ("listening", "conversation"))
LISTENING_TASK_KINDS = frozenset(k for k, m in MODES.items() if m == "listening")


def mode(e: Exercise) -> str:
    """The exercise's mode. A new word introduced through the catch (#339) is the catch's own turn. A kind not in ``MODES`` is an error, not a
    guess: a listening kind taken for a drill would get «Back to speaking.» before it."""
    if e.kind == "intro" and e.label.startswith(CATCH_INTRO):
        return "listening"
    return MODES[e.kind]


def ways_back(order: list[Exercise]) -> dict[int, str]:
    """Exercise index → the prompt key of the way back it ends with, for the exercises in ``order`` (as spoken) that hand over to one that
    does not open with its own line."""
    out: dict[int, str] = {}
    for e, nxt in zip(order, order[1:]):
        if mode(nxt) in OPENS_WITH_ITS_OWN_LINE:
            continue
        line = WAY_BACK.get(mode(e))
        if line:
            out[e.index] = line
    return out


def as_spoken(sc: Script) -> list[Exercise]:
    """The exercises in the order the learner hears them: those with a segment that takes time."""
    timed = {s.exercise for s in sc.segments if s.exercise is not None and s.duration > 0}
    return [e for e in sc.exercises if e.index in timed]


def _spoken(sc: Script) -> dict[int, list[int]]:
    """Exercise index → the positions of its spoken segments in ``sc.segments``."""
    out: dict[int, list[int]] = {}
    for k, s in enumerate(sc.segments):
        if s.exercise is not None and s.type in SPOKEN and s.duration > 0:
            out.setdefault(s.exercise, []).append(k)
    return out


def _instructor(s: Segment) -> bool:
    return s.type == "narrate" and s.speaker == "instructor"


def ways_in(sc: Script, order: list[Exercise]) -> dict[int, str]:
    """Exercise index → the prompt key of the line it opens with (``WAY_IN``), for an exercise after the first whose first spoken line is a
    target-language one."""
    spoken = _spoken(sc)
    out: dict[int, str] = {}
    for k, e in enumerate(order):
        line = WAY_IN.get(mode(e))
        if k and line and e.index in spoken and not _instructor(sc.segments[spoken[e.index][0]]):
            out[e.index] = line
    return out


def close_tasks(sc: Script, prompts: Prompts, timing: Timing, known_lang: str) -> tuple[int, int]:
    """Each way in and way back where it is wanted, on the finished script: a way in (``WAY_IN``) is said before the exercise's first line, with
    a beat; a built-in way back (``BUILT_IN``) is kept or dropped with its beat, any other is said after the exercise's last spoken line, after a
    beat. A conversation right after another opens «Now another short conversation.» (``dialogue_start_another``). Returns how many listening
    exercises and conversations were closed."""
    order = as_spoken(sc)
    roles = ways_back(order)
    opens = ways_in(sc, order)
    first = {i: ks[0] for i, ks in _spoken(sc).items()}
    # a conversation right after another one says so (owner, lesson 45: «Now a short conversation.» after a conversation that ended with no
    # «That's the end of the conversation.», which is not said before a task that opens with its own line)
    another = {e.index for prev, e in zip(order, order[1:]) if mode(prev) == "conversation" and mode(e) == "conversation"}
    start, start_another = prompts.get("dialogue_start"), prompts.get("dialogue_start_another")
    out: list[Segment] = []
    for k, s in enumerate(sc.segments):
        if s.exercise in another and _instructor(s) and s.text == start:
            s = replace(s, text=start_another, duration=timing.speech_estimate(start_another, known_lang))
        if s.exercise in opens and first.get(s.exercise) == k:
            text = prompts.get(opens[s.exercise])
            out.append(Segment("narrate", "instructor", text, known_lang, 1.0, timing.speech_estimate(text, known_lang), opens[s.exercise], s.exercise))
            out.append(Segment("pause", None, None, None, 1.0, timing.beat, "beat", s.exercise))
        if s.role in BUILT_IN:
            if roles.get(s.exercise) == s.role:
                out.append(s)
            elif out and out[-1].type == "pause" and out[-1].role == "beat" and out[-1].exercise == s.exercise:
                out.pop()  # its beat goes with it
            continue
        out.append(s)
        role = roles.get(s.exercise)
        if role and role not in BUILT_IN and s.type in SPOKEN and not any(
            t.exercise == s.exercise and t.type in SPOKEN for t in sc.segments[k + 1 :]
        ):
            text = prompts.get(role)
            out.append(Segment("pause", None, None, None, 1.0, timing.beat, "beat", s.exercise))
            out.append(Segment("narrate", "instructor", text, known_lang, 1.0, timing.speech_estimate(text, known_lang), role, s.exercise))
    sc.segments = out
    said = [s.role for s in out]  # what is said, not what was wanted: a builder that writes no built-in line closes nothing
    return said.count("listening_back"), said.count("conversation_back")


def unmarked_turns(sc: Script, prompts: Prompts) -> list[str]:
    """The changes of task on a finished script whose line is missing or out of place, «label: what is wrong» (0 expected):
    - a way back the table wants that is not the exercise's last spoken line («no way back»), or one said where it wants none («a way back
      where …»);
    - an aside that does not end with its end line («no end line»);
    - a task that opens with its own line whose first spoken line is a target-language one («opens with …»)."""
    spoken = _spoken(sc)
    order = as_spoken(sc)  # the order ``close_tasks`` reads
    wanted = ways_back(order)
    backs = set(WAY_BACK.values())
    out: list[str] = []
    for k, e in enumerate(order):
        lines = [sc.segments[j] for j in spoken.get(e.index, [])]
        if e.index in wanted and (not lines or lines[-1].role != wanted[e.index]):
            out.append(f"{e.label}: no way back before {order[k + 1].kind}")
        if e.index not in wanted and any(s.role in backs for s in lines):
            out.append(f"{e.label}: a way back where the next task opens with its own line, or none follows")
        if not lines:
            continue
        ends = END_LINES.get(mode(e))
        if ends and not any(lines[-1].text in _templates(prompts, key) for key in ends):
            out.append(f"{e.label}: no end line")
        if k and mode(e) in OPENS_WITH_ITS_OWN_LINE and not _instructor(lines[0]):
            out.append(f"{e.label}: opens with «{lines[0].text}» straight after {order[k - 1].kind}")
    return out
