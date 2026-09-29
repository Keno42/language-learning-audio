"""A learner's private trip profile (issue #132).

It lives next to the learner file, outside any repository, and is never copied into
lesson outputs: generate only reports that a profile is in use. The lesson record keeps
at most its digest.

    departure = 2030-01-31        # optional: the horizon for `validate --cando --trip`
    boost = ["A6", "B2"]          # optional: can-do scenario ids (#131) to teach first
    places = ["…"]                # optional: the learner's own place names (reading, #133)
    season = "winter-holidays"    # optional: seasonal can-do content applies only when it matches

Without ``boost``, the trip ordering puts every Tier A item first, then Tier B. The pace
never depends on the departure date: lessons go on at the learner's pace right up to and
through the trip, throttled only by what the learner reports (owner, PR #138 review).
"""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

KEYS = {"departure", "boost", "places", "season"}


class TripError(ValueError):
    pass


@dataclass
class TripProfile:
    departure: date | None = None
    boost: list[str] = field(default_factory=list)
    places: list[str] = field(default_factory=list)
    season: str | None = None
    digest: str = ""  # sha256 of the file, the only trace a lesson record may keep

    def days_left(self, today: date) -> int | None:
        return None if self.departure is None else (self.departure - today).days


def load_trip(path: str | Path) -> TripProfile:
    raw_bytes = Path(path).read_bytes()
    try:
        raw = tomllib.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
        raise TripError(f"trip profile is not valid TOML: {e}") from None
    unknown = set(raw) - KEYS
    if unknown:
        raise TripError(f"trip profile: unknown keys {sorted(unknown)} (allowed: {sorted(KEYS)})")
    dep = raw.get("departure")
    if isinstance(dep, datetime):
        dep = dep.date()
    elif isinstance(dep, str):
        try:
            dep = date.fromisoformat(dep)
        except ValueError:
            raise TripError("trip profile: departure must be a date (YYYY-MM-DD)") from None
    elif dep is not None and not isinstance(dep, date):
        raise TripError("trip profile: departure must be a date (YYYY-MM-DD)")
    for key in ("boost", "places"):
        if not isinstance(raw.get(key, []), list) or not all(isinstance(x, str) for x in raw.get(key, [])):
            raise TripError(f"trip profile: {key} must be a list of strings")
    return TripProfile(
        departure=dep,
        boost=list(raw.get("boost", [])),
        places=list(raw.get("places", [])),
        season=raw.get("season"),
        digest=hashlib.sha256(raw_bytes).hexdigest(),
    )
