"""Timing model: how long a pause is, and how long speech is expected to take.

Everything here is a plain number in a ``Timing`` object so a profile can
override any of it. Nothing is hard-coded elsewhere.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def word_count(text: str) -> int:
    """Tokens that contain letters/digits — 'Où est la gare ?' is 4, not 5."""
    return len(_WORD_RE.findall(text))

# Learner level → multiplier on every answer pause. A0 = absolute beginner.
LEVEL_MULTIPLIER = {"A0": 1.4, "A1": 1.2, "A2": 1.0, "B1": 0.85, "B2": 0.75}

# Rough speaking rates used to *estimate* speech duration before TTS runs.
# Real durations come from the renderer; these only steer lesson length.
WORDS_PER_SECOND = {"default": 2.3, "en": 2.5, "fr": 2.2, "es": 2.4, "de": 2.1, "it": 2.3, "pt": 2.3, "is": 2.0}
CHARS_PER_SECOND = {"ja": 5.5, "zh": 4.5, "ko": 5.0, "th": 5.0}  # languages without spaces


@dataclass
class Timing:
    think_time: float = 1.0  # a moment to recall the answer, before saying it (scaled below)
    generative_bonus: float = 1.5  # extra thinking time for novel combinations / situations
    repeat_delay: float = 0.5  # reaction time before repeating something just heard (not recalled)
    beat: float = 0.8  # tiny gap between speech segments
    between_exercises: float = 1.2
    min_pause: float = 1.5  # floor for repeating what was just heard
    # floors for answer pauses, which include the time to say the answer: recall with nothing
    # given needs time to retrieve as well as speak; a hint or cloze fragment supplies part
    # of the answer, so it keeps the shorter floor
    min_recall_pause: float = 2.5
    min_supported_pause: float = 1.5
    max_pause: float = 15.0
    level: str = "A1"
    level_multiplier: dict[str, float] = field(default_factory=lambda: dict(LEVEL_MULTIPLIER))
    # familiarity: fewer successful recalls → more time
    unfamiliar_multiplier: float = 1.15  # successes < 2
    familiar_multiplier: float = 0.85  # successes >= 6
    difficulty_step: float = 0.08  # per difficulty point above 2
    # TTS rate for pronunciation demos (the only slow speech); 0.72 still felt rushed
    slow_rate: float = 0.6
    global_pause_multiplier: float = 1.0  # one knob for "everything a bit longer/shorter"
    speech_ratio: dict[str, float] = field(default_factory=dict)  # lang → measured / estimated, from past renders

    def with_overrides(self, **kw) -> "Timing":
        kw = {k: v for k, v in kw.items() if v is not None}
        return replace(self, **kw)

    # ---- pauses ----------------------------------------------------------

    def answer_pause(
        self,
        answer_text: str,
        lang: str,
        *,
        difficulty: int = 2,
        successes: int = 0,
        generative: bool = False,
        supported: bool = False,
    ) -> float:
        """A moment to recall the answer, plus however long it actually takes to say it.
        ``supported``: the prompt just gave part of the answer (a first-word hint, a cloze
        fragment), so the floor is ``min_supported_pause`` instead of ``min_recall_pause``."""
        think = self.think_time + (self.generative_bonus if generative else 0.0)
        mult = self.level_multiplier.get(self.level, 1.0)
        if successes < 2:
            mult *= self.unfamiliar_multiplier
        elif successes >= 6:
            mult *= self.familiar_multiplier
        mult *= 1.0 + self.difficulty_step * max(0, difficulty - 2)
        mult *= self.global_pause_multiplier
        speak = self.speech_estimate(answer_text, lang)
        floor = self.answer_floor(supported)
        return round(min(self.max_pause, max(floor, think * mult + speak)), 1)

    def answer_floor(self, supported: bool = False) -> float:
        """The floor ``answer_pause`` applies, for the renderer to keep when it shrinks pauses."""
        return self.min_supported_pause if supported else self.min_recall_pause

    def repeat_pause(self, answer_text: str, lang: str) -> float:
        """Repeating something just heard needs no recall — just enough time to say it."""
        speak = self.speech_estimate(answer_text, lang)
        total = (self.repeat_delay + speak) * self.global_pause_multiplier
        return round(min(self.max_pause, max(self.min_pause, total)), 1)

    # ---- speech estimates --------------------------------------------------

    def speech_estimate(self, text: str, lang: str, rate: float = 1.0) -> float:
        """Seconds a TTS voice will roughly take to say ``text``."""
        lang2 = lang.split("-")[0].lower()
        if lang2 in CHARS_PER_SECOND:
            secs = len(text) / CHARS_PER_SECOND[lang2]
        else:
            wps = WORDS_PER_SECOND.get(lang2, WORDS_PER_SECOND["default"])
            secs = max(1, word_count(text)) / wps
        secs = secs / max(0.3, rate) + 0.35  # + leading/trailing breath
        secs *= self.speech_ratio.get(lang2, 1.0)
        return round(secs, 2)
