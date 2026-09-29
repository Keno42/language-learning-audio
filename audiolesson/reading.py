"""The reading deck (issue #133): cards for the Discord review — letters and sounds, signs,
shop words, place names and their parts — since the audio course never shows spelling.

Cards live in ``<curriculum>/reading/*.toml`` (a subdirectory, so ``load_curriculum``
never reads them as modules). A learner's own place names come from the private trip
profile (#132) as extra cards built at run time; they are never written to the repository.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .content import CurriculumError

STAGES = ("letters", "signs", "shop", "places", "parts")


@dataclass
class Card:
    id: str
    stage: str
    text: str
    meaning: str
    meaning_ja: str = ""
    hint_ja: str = ""  # a katakana approximation; the 🔊 TTS is the real pronunciation
    parts: list[list[str]] = field(default_factory=list)  # [[part, gloss], …] for compounds
    own: bool = False  # from the private trip profile: never stored in the repository

    def to_dict(self) -> dict:
        return asdict(self)


def load_deck(curriculum_dir: str | Path, places: list[str] | None = None) -> list[Card]:
    """The deck in stage order (file order within a stage), plus a card for each of the
    learner's own ``places`` (from the trip profile) not already in it."""
    d = Path(curriculum_dir) / "reading"
    cards: list[Card] = []
    if d.is_dir():
        for f in sorted(d.glob("*.toml")):
            with f.open("rb") as fh:
                raw = tomllib.load(fh)
            for c in raw.get("cards", []):
                try:
                    card = Card(**c)
                except TypeError as e:
                    raise CurriculumError(f"{f}: card {c.get('id')!r}: {e}") from None
                if card.stage not in STAGES:
                    raise CurriculumError(f"{f}: card {card.id!r}: stage must be one of {STAGES}")
                if not card.text.strip() or not card.meaning.strip():
                    raise CurriculumError(f"{f}: card {card.id!r}: text and meaning are required")
                if any(len(p) != 2 for p in card.parts):
                    raise CurriculumError(f"{f}: card {card.id!r}: parts are [part, gloss] pairs")
                cards.append(card)
    ids = [c.id for c in cards]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise CurriculumError(f"reading card ids repeat: {dupes}")
    known = {c.text.casefold() for c in cards}
    for n, place in enumerate(places or [], 1):
        if place.strip() and place.casefold() not in known:
            cards.append(Card(id=f"own_{n}", stage="places", text=place, meaning="a place on your trip",
                              meaning_ja="あなたの旅程の地名", own=True))
    return sorted(cards, key=lambda c: STAGES.index(c.stage))


def texts(cards: list[Card]) -> set[str]:
    """Every readable text in the deck, casefolded; a card listing several («A · B»)
    counts each."""
    out: set[str] = set()
    for c in cards:
        out.add(c.text.casefold())
        out.update(t.strip().casefold() for t in c.text.split("·"))
    return out
