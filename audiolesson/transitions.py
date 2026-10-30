"""The way back after a task: the line that ends a listening task or a conversation where a drill follows.

The ledger's family «pick-out-turns» (the turns between and inside tasks) was remarked in eight lessons from 24 to 39, each turn fixed on its
own. This module homes one part of it, the way back (lesson 34, #387; lessons 37 and 39, #415, #425): every exercise kind has a mode
(``MODES``), the line that ends a mode is ``WAY_BACK``, and ``close_tasks`` says it on the finished script, where the next exercise is known.
A test keeps every kind the code builds in ``MODES``, so whether a way back comes after or before a new kind is decided the day it is written.
Not here: the turns inside a pick-out (``listening_tasks._build``: #306, #343, #353, #411), the closing block's content (#421, #435, #437), and
an aside's end («Back to the lesson.», «Let's continue.»), which ``Builder.note`` says whatever follows.
"""

from __future__ import annotations

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
SPOKEN = ("speak", "narrate", "answer")


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


def close_tasks(sc: Script, prompts: Prompts, timing: Timing, known_lang: str) -> tuple[int, int]:
    """Each way back where it is wanted, on the finished script: a built-in one (``BUILT_IN``) is kept or dropped with its beat, any other is
    said after the exercise's last spoken line, after a beat. Returns how many listening exercises and conversations were closed."""
    spoken = {s.exercise for s in sc.segments if s.exercise is not None and s.duration > 0}
    roles = ways_back([e for e in sc.exercises if e.index in spoken])
    out: list[Segment] = []
    for k, s in enumerate(sc.segments):
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
