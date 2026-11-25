"""Simulated courses shared by the tests of one process (the owner, 2026-11-25: the test time down, without a way to get it wrong).

Many tests build the same course: ``ListeningTaskTests._course`` alone runs 9 to 40 lessons of one recipe in some twenty tests, and each
built it from lesson 1. ``take(key, recipe, n)`` builds a recipe's lessons once per process and hands them out again:

- **Nothing is shared.** Each lesson is kept pickled, and every caller gets fresh copies of the curriculum, the learner and the script: a
  test that changes what it was given cannot change what another test reads.
- **A longer course extends the shorter one.** The recipe's own generator is kept running, so 40 lessons after 30 build ten more. A recipe
  is a generator of one lesson a step, a pure function of its arguments: the same as building from lesson 1 (``tests/test_course_cache.py``
  holds every recipe that uses this to it, lesson by lesson, against a fresh build).
- **Nothing outlives the process.** Nothing is written to disk, so a cached course is never older than the code.

Each lesson is handed out as it stood when the recipe yielded it: a fresh build shares one learner between its steps, which a test that
kept a step's learner past the next step would see change (none does).

A recipe yields ``(curriculum, …)``, the same curriculum object every step: it is unpickled once per call and shared by that call's lessons,
as the recipe shares it.
"""
from __future__ import annotations

import pickle
from typing import Callable, Iterator

ENDLESS = 10**6


class _Course:
    def __init__(self, recipe: Callable[[int], Iterator[tuple]]):
        self.gen = recipe(ENDLESS)
        self.lessons: list[bytes] = []
        self.first: object = None
        self.first_bytes = b""

    def grow(self, n: int) -> None:
        while len(self.lessons) < n:
            step = next(self.gen)
            if not isinstance(step, tuple) or len(step) < 2:
                raise TypeError("a recipe yields (curriculum, …) tuples")
            if not self.lessons:
                self.first, self.first_bytes = step[0], pickle.dumps(step[0], pickle.HIGHEST_PROTOCOL)
            elif step[0] is not self.first:
                raise TypeError("a recipe yields the same curriculum object every step")
            self.lessons.append(pickle.dumps(step[1:], pickle.HIGHEST_PROTOCOL))


_STORE: dict[str, _Course] = {}


def take(key: str, recipe: Callable[[int], Iterator[tuple]], n: int) -> Iterator[tuple]:
    """The first ``n`` steps of ``recipe`` (a generator function of the number of lessons, yielding ``(curriculum, …)``), as fresh copies;
    built once per process per ``key``. The curriculum is one fresh copy per call, the rest one per step."""
    course = _STORE.get(key)
    if course is None:
        course = _STORE[key] = _Course(recipe)
    course.grow(n)
    cur = pickle.loads(course.first_bytes)
    for raw in course.lessons[:n]:
        yield (cur, *pickle.loads(raw))
