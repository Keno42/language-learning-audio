#!/usr/bin/env python3
"""A small packet of one scenario's cards for a fluent speaker to review (G10, #209).

No fluent speaker has reviewed the course: every line is a candidate (CURRENT-POLICY). A review of all of it is more than one sitting, so the packet
holds one scenario: up to ``--limit`` of its scenario cards (``cando/scenes.toml``), each with what a reviewer needs to judge the exchange and not an
isolated sentence: the situation, the partner's line with its meanings, the model replies, and the items the first reply needs.

    python tools/export_scene_review.py --scenario A2 --out review-A2.json

A correction names the card and the field, so it maps back to the source: ``card_id: a2_change; field: partner; suggested_value: …``. The fields a
correction may name are listed in the packet (``correction_fields``) and are the card's own fields in its source file (``source_file``).

Read-only: it changes neither the curriculum nor any lesson. Identical inputs give an identical packet (no date, no random order). It holds public
curriculum content only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from audiolesson.cando import load_cando  # noqa: E402
from audiolesson.content import load_curriculum  # noqa: E402
from audiolesson.records import load_records  # noqa: E402
from audiolesson.scenes import Scene  # noqa: E402

STATUS = "awaiting review: these lines are candidates; no fluent speaker has checked them"
CORRECTION_FIELDS = ("situation", "partner", "partner_meaning", "replies")  # the card's own fields a correction may name
HOW = "one line per correction: card_id: <card>; field: <one of correction_fields>; suggested_value: <the line as it should be>; note: <why, optional>"


class UnknownScenario(ValueError):
    pass


def revision(root: Path = ROOT) -> str:
    """The commit the packet was made from, so a correction is applied to the wording it was made on; «unknown» outside a git checkout."""
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def packet(curriculum: str | Path, scenario_id: str, limit: int = 20, rev: str | None = None) -> dict:
    """The review packet of ``scenario_id``: its cards in file order, ``limit`` at most. Source wording is kept exactly."""
    curriculum = Path(curriculum)
    cur = load_curriculum(curriculum)
    scenarios = {s.id: s for s in load_cando(curriculum, cur)}
    if scenario_id not in scenarios:
        raise UnknownScenario(f"no scenario {scenario_id!r}; the scenarios are: {', '.join(sorted(scenarios))}")
    scenario = scenarios[scenario_id]
    cards = []
    for source, scene in load_records(curriculum / "cando", "scenes", Scene, "scene"):
        if scene.scenario != scenario_id:
            continue
        cards.append({
            "card_id": scene.id,
            "source_file": source.relative_to(curriculum).as_posix() if source.is_relative_to(curriculum) else source.name,
            "kind": scene.kind,  # respond: the learner answers the partner's line; initiate: the learner speaks first; repair: something went wrong
            "situation": scene.situation,
            "partner": scene.partner,
            "partner_meaning": scene.partner_meaning,
            "partner_meaning_ja": scene.partner_meaning_ja,
            "replies": list(scene.replies),
            "items": [{"id": i, "target": cur.by_id[i].target, "meaning": cur.by_id[i].meaning} for i in scene.items if i in cur.by_id],
            "corrections": [],
            "reviewer_notes": "",
        })
    return {
        "status": STATUS,
        "revision": revision() if rev is None else rev,
        "curriculum": cur.name if hasattr(cur, "name") else curriculum.name,
        "scenario": {"id": scenario.id, "title": scenario.title, "setting": scenario.setting, "purpose": scenario.success},
        "correction_fields": list(CORRECTION_FIELDS),
        "how_to_correct": HOW,
        "cards_in_scenario": len(cards),
        "cards": cards[: max(0, limit)],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scenario", required=True, help="the scenario's id (A2, B7, …)")
    ap.add_argument("--out", type=Path, default=None, help="the packet's file (default: standard output)")
    ap.add_argument("--curriculum", default=str(ROOT / "curricula" / "is-en"))
    ap.add_argument("--limit", type=int, default=20, help="cards at most (default 20)")
    args = ap.parse_args(argv)
    try:
        data = packet(args.curriculum, args.scenario, args.limit)
    except UnknownScenario as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.write_text(text, encoding="utf-8")
        print(f"{len(data['cards'])} of {data['cards_in_scenario']} cards of {args.scenario} written to {args.out} ({STATUS})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
