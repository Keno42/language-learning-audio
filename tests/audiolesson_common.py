"""Shared fixtures of the lesson tests split from test_audiolesson.py (#281): the French test curriculum, a lesson builder and a
course. Not a test module: the loader does not collect it, and ``__all__`` exports every name, the underscored ones included."""
from __future__ import annotations

import copy
import json
import os
import random
import re
import tempfile
import unittest
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from audiolesson.exercises import SITUATION_FULL_MAX, _norm_utterance
from audiolesson.content import NOTE_TARGET_RE, CurriculumError, curriculum_from_dict, load_curriculum, unmarked_japanese
from audiolesson.learner import ItemState, LearnerState
from audiolesson.planner import PlanConfig, Planner, apply_to_learner
from audiolesson.prompts import Prompts
from audiolesson.render import load_profile, render_script
from audiolesson.render.audio import read_wav
from audiolesson.script import Script, Segment
from audiolesson.stages import ladder_for, stage_index
from audiolesson.timing import Timing

ROOT = Path(__file__).resolve().parent.parent
CURRICULUM = ROOT / "curricula" / "fr-en-a1.toml"
TODAY = date(2026, 9, 18)
_WORD_RE = re.compile(r"[^\W\d]+", re.UNICODE)


def build(learner: LearnerState, minutes: float = 15, today: date = TODAY, **cfg) -> Script:
    cur = load_curriculum(CURRICULUM)
    prompts = Prompts.load(cur.known_lang)
    planner = Planner(cur, learner, prompts, Timing(level="A1"), PlanConfig(minutes=minutes, seed=1, **cfg), today=today)
    return planner.build()


_LADDERS: dict[str, list[str]] = {}


def learner_ladder(item_id: str) -> list[str]:
    """Ladder of an item in the sample curriculum, as the planner computes it."""
    if not _LADDERS:
        cur = load_curriculum(CURRICULUM)
        planner = Planner(cur, fresh(), Prompts.load("en"), Timing(), PlanConfig(), today=TODAY)
        _LADDERS.update({i.id: planner.ladder(i) for i in cur.items})
    return _LADDERS[item_id]


def fresh() -> LearnerState:
    return LearnerState("fr", "en", "A1")


def course(n_lessons: int, minutes: float = 15) -> tuple[LearnerState, list[Script]]:
    learner = fresh()
    scripts = []
    day = TODAY
    for _ in range(n_lessons):
        sc = build(learner, minutes, today=day)
        apply_to_learner(sc, learner, day)
        scripts.append(sc)
        day += timedelta(days=2)
    return learner, scripts

__all__ = [name for name in dir() if not name.startswith('__')]
