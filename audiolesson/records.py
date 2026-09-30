"""TOML record files that sit next to a curriculum: the can-do scenarios and scenario cards
(``cando/``) and the reading deck (``reading/``). They live in subdirectories, so
``load_curriculum`` never reads them as modules.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, TypeVar

from .content import CurriculumError

T = TypeVar("T")


def load_records(directory: str | Path, key: str, cls: type[T], label: str) -> list[tuple[Path, T]]:
    """Every ``[[key]]`` table in ``directory/*.toml`` (in file order) as ``cls``, with the
    file it came from for error messages. None without the directory. Unknown fields and
    repeated ids fail."""
    d = Path(directory)
    if not d.is_dir():
        return []
    out: list[tuple[Path, T]] = []
    for f in sorted(d.glob("*.toml")):
        with f.open("rb") as fh:
            raw = tomllib.load(fh)
        for record in raw.get(key, []):
            try:
                out.append((f, cls(**record)))
            except TypeError as e:
                raise CurriculumError(f"{f}: {label} {record.get('id')!r}: {e}") from None
    ids = [getattr(r, "id") for _, r in out]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise CurriculumError(f"{label} ids repeat: {dupes}")
    return out


def check_items(pairs: list[tuple[str, str]], known: set[str] | dict[str, Any], label: str) -> None:
    """Fail on any (record id, item id) pair whose item is not in ``known``."""
    unknown = [(r, i) for r, i in pairs if i not in known]
    if unknown:
        raise CurriculumError(f"{label} name unknown items: {unknown}")
