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
WORDS_PER_SECOND = {"default": 2.3, "en": 2.5, "fr": 2.2, "es": 2.4, "de": 2.1, "it": 2.3, "pt": 2.3}
CHARS_PER_SECOND = {"ja": 5.5, "zh": 4.5, "ko": 5.0, "th": 5.0}  # languages without spaces


@dataclass
class Timing:
    # base answer windows in seconds, by expected response size
    word: float = 2.5
    short_phrase: float = 4.0
    sentence: float = 6.5
    long_sentence: float = 8.5
    generative_bonus: float = 1.5  # extra thinking time for novel combinations / situations
    repeat_factor: float = 0.7  # "now repeat" pauses relative to an answer pause
    beat: float = 0.8  # tiny gap between speech segments
    between_exercises: float = 1.2
    min_pause: float = 1.5
    max_pause: float = 15.0
    level: str = "A1"
    level_multiplier: dict[str, float] = field(default_factory=lambda: dict(LEVEL_MULTIPLIER))
    # familiarity: fewer successful recalls → more time
    unfamiliar_multiplier: float = 1.15  # successes < 2
    familiar_multiplier: float = 0.85  # successes >= 6
    difficulty_step: float = 0.08  # per difficulty point above 2
    slow_rate: float = 0.72  # TTS rate for slow pronunciation
    global_pause_multiplier: float = 1.0  # one knob for "everything a bit longer/shorter"

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
    ) -> float:
        base = self._base_for(answer_text, lang)
        if generative:
            base += self.generative_bonus
        mult = self.level_multiplier.get(self.level, 1.0)
        if successes < 2:
            mult *= self.unfamiliar_multiplier
        elif successes >= 6:
            mult *= self.familiar_multiplier
        mult *= 1.0 + self.difficulty_step * max(0, difficulty - 2)
        mult *= self.global_pause_multiplier
        return round(min(self.max_pause, max(self.min_pause, base * mult)), 1)

    def repeat_pause(self, answer_text: str, lang: str) -> float:
        base = self._base_for(answer_text, lang) * self.repeat_factor * self.global_pause_multiplier
        return round(min(self.max_pause, max(self.min_pause, base)), 1)

    def _base_for(self, text: str, lang: str) -> float:
        n = _units(text, lang)
        if n <= 1:
            return self.word
        if n <= 4:
            return self.short_phrase
        if n <= 9:
            return self.sentence
        return self.long_sentence

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
        return round(secs, 2)


def _units(text: str, lang: str) -> int:
    lang2 = lang.split("-")[0].lower()
    if lang2 in CHARS_PER_SECOND:
        # ~3 chars ≈ one "word" of effort
        return max(1, len(text.replace(" ", "")) // 3)
    return word_count(text)
