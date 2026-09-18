"""Instructor phrasing, loaded from audiolesson/phrasing/<known_lang>.toml."""

from __future__ import annotations

import random
import tomllib
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "phrasing"


class Prompts:
    def __init__(self, data: dict, lang: str, rng: random.Random | None = None):
        self.data = data
        self.lang = lang
        self.rng = rng or random.Random(0)

    @classmethod
    def load(cls, known_lang: str, rng: random.Random | None = None, path: str | Path | None = None) -> "Prompts":
        p = Path(path) if path else PROMPTS_DIR / f"{known_lang.split('-')[0].lower()}.toml"
        if not p.exists():
            available = sorted(x.stem for x in PROMPTS_DIR.glob("*.toml"))
            raise FileNotFoundError(
                f"No instructor phrasing for known language {known_lang!r}. "
                f"Add audiolesson/phrasing/{known_lang}.toml (copy en.toml). Available: {available}"
            )
        with p.open("rb") as fh:
            return cls(tomllib.load(fh), known_lang, rng)

    def get(self, key: str, **fmt) -> str:
        val = self.data[key]
        if isinstance(val, list):
            val = self.rng.choice(val)
        return val.format(**fmt) if fmt else val

    def language_name(self, code: str) -> str:
        names = self.data.get("language_names", {})
        return names.get(code.split("-")[0].lower(), code)
