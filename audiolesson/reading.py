"""The reading deck (issue #133): cards for the Discord review — letters and sounds, signs,
shop words, place names and their parts — since the audio course never shows spelling.

Cards live in ``<curriculum>/reading/*.toml`` (a subdirectory, so ``load_curriculum``
never reads them as modules). A learner's own place names come from the private trip
profile (#132) as extra cards built at run time; they are never written to the repository.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .content import CurriculumError
from .records import load_records

STAGES = ("letters", "signs", "shop", "places", "parts")


@dataclass
class Card:
    id: str
    stage: str
    text: str
    meaning: str
    meaning_ja: str = ""
    # a katakana approximation; the 🔊 TTS is the real pronunciation. IPA in brackets, with a note in Japanese, for a word with a sound
    # katakana cannot write (``kana_cannot_write``, #586)
    hint_ja: str = ""
    parts: list[list[str]] = field(default_factory=list)  # [[part, gloss], …] for compounds
    # [[word, gloss], …]: what each expression listed with «·» means. A letters card's
    # ``meaning`` is its spelling rule, so without these the words' meanings go unshown
    words: list[list[str]] = field(default_factory=list)
    # letters cards: the letters or digraphs the card teaches (``meaning`` states their rule).
    # Each must show in a listed word and every word must show one, so a rule never goes
    # without an example and a word never stands under a rule it doesn't illustrate
    graphemes: list[str] = field(default_factory=list)
    own: bool = False  # from the private trip profile: never stored in the repository

    def to_dict(self) -> dict:
        return asdict(self)


def load_deck(curriculum_dir: str | Path, places: list[str] | None = None) -> list[Card]:
    """The deck in stage order (file order within a stage), plus a card for each of the
    learner's own ``places`` (from the trip profile) not already in it."""
    cards: list[Card] = []
    for f, card in load_records(Path(curriculum_dir) / "reading", "cards", Card, "reading card"):
        where = f"{f}: card {card.id!r}"
        if card.stage not in STAGES:
            raise CurriculumError(f"{where}: stage must be one of {STAGES}")
        if not card.text.strip() or not card.meaning.strip():
            raise CurriculumError(f"{where}: text and meaning are required")
        if any(len(p) != 2 for p in card.parts):
            raise CurriculumError(f"{where}: parts are [part, gloss] pairs")
        if any(len(w) != 2 for w in card.words):
            raise CurriculumError(f"{where}: words are [word, gloss] pairs")
        if card.words and [w for w, _ in card.words] != expressions(card.text):
            raise CurriculumError(f"{where}: words must gloss {expressions(card.text)}, in order")
        if card.stage == "letters" and not card.words:
            raise CurriculumError(f"{where}: a letters card glosses its words")
        if card.hint_ja and "[" not in card.hint_ja and (unwritable := sorted({r for w in _WORD.findall(card.text) for r in kana_cannot_write(w)})):
            raise CurriculumError(f"{where}: {card.text!r} has a sound katakana cannot write ({', '.join(unwritable)}): its hint_ja gives IPA in "
                                  "[brackets] (#586)")
        if card.stage == "letters":
            _check_graphemes(card, where)
        elif card.graphemes:
            raise CurriculumError(f"{where}: only a letters card has graphemes")
        cards.append(card)
    known = {c.text.casefold() for c in cards}
    for n, place in enumerate(places or [], 1):
        if place.strip() and place.casefold() not in known:
            cards.append(Card(id=f"own_{n}", stage="places", text=place, meaning="a place on your trip",
                              meaning_ja="あなたの旅程の地名", own=True))
    return sorted(cards, key=lambda c: STAGES.index(c.stage))


_WORD = re.compile(r"[^\W\d_]+")
_VOWEL = "aáeéiíoóuúyýæö"
# #586 (lesson 65: «vatn» introduced as «ヴァフトン», two vowels the word does not have): the sounds katakana cannot write without adding a vowel
# or a voice. Spelling rules, not a transcription: what they flag is a word whose hint gives IPA instead
_UNWRITABLE = (
    ("pre-aspiration", re.compile(rf"[{_VOWEL}](?:pp|tt|kk|[ptk][lnm]|fn)", re.I)),  # «vatn» [vaʰtn̥], «Hætta» [ˈhaiʰta], «Nafn» [napn̥]
    ("the tl of ll", re.compile(rf"[{_VOWEL}]ll(?![sdtn])", re.I)),  # «fjall» [fjatl̥]; before s, d, t or n a plain l («Snæfellsnes»)
    ("the tn of rn", re.compile(rf"[{_VOWEL}]rn", re.I)),  # «Björn» [pjœtn̥]
    ("the tn of nn", re.compile(r"(?:[áéíóúýæ]|au|ei|ey)nn", re.I)),  # «Steinn» [steitn̥]; not after a short vowel («Bannað», «daginn»)
    ("a voiceless l, m, n or r", re.compile(rf"[{_VOWEL}](?:ll|[lmnr])[ptk]", re.I)),  # «Mjólk» [mjoul̥k], «Sturta» [ˈstʏr̥ta], «allt»
    ("a voiceless initial l, n or r", re.compile(r"^h[lnr]", re.I)),  # «hraun» [r̥œyːn]
)


def kana_cannot_write(word: str) -> list[str]:
    """The sounds of ``word`` katakana cannot write (#586), by its spelling; [] when kana can approximate it."""
    return [name for name, rx in _UNWRITABLE if rx.search(word)]


def _check_graphemes(card: Card, where: str) -> None:
    if not card.graphemes:
        raise CurriculumError(f"{where}: a letters card names the letters it teaches (graphemes)")
    words = [w.casefold() for w, _ in card.words]
    unshown = [g for g in card.graphemes if not any(g.casefold() in w for w in words)]
    if unshown:
        raise CurriculumError(f"{where}: no listed word shows {unshown}: its rule has no example")
    bare = [w for w, _ in card.words if not any(g.casefold() in w.casefold() for g in card.graphemes)]
    if bare:
        raise CurriculumError(f"{where}: {bare} show none of {card.graphemes}: they illustrate no rule of the card")


def expressions(text: str) -> list[str]:
    """The expressions a card lists with «·» (one for a single text)."""
    return [t.strip() for t in text.split("·") if t.strip()]


def texts(cards: list[Card]) -> set[str]:
    """Every readable text in the deck, casefolded; a card listing several («A · B»)
    counts each."""
    out: set[str] = set()
    for c in cards:
        out.add(c.text.casefold())
        out.update(t.casefold() for t in expressions(c.text))
    return out
