# Working on this repository

- **Start with `docs/CURRENT-POLICY.md` and `docs/CURRENT-STATUS.md`** (the short briefs: what the project is for and
  what always holds; what we work on now, what was built since the last update, and where to look for the rest).
- **Then read the sources for the task** (the table below), and answer `docs/LEARNING-DESIGN.md` §1's checklist in the
  issue or PR: the outcome it serves, the gap it closes, the hypothesis it relies on, the evidence behind it and what it
  predicts. Read all of `docs/LEARNING-DESIGN.md` for a change to project-wide learning policy or a design change across
  several areas. The document also lists the decisions already made (§9) and our known failure modes (§11). Above all:
  don't answer each remark with its own local fix; find the shared cause and fit it into the roadmap (§8).
- After a round of learner feedback, update its evidence (§5), the hypothesis statuses (§4) and "Now" in
  `docs/CURRENT-STATUS.md`.
- **Documents: replace, don't append** (LEARNING-DESIGN §10). Rewrite a statement that changed rather than adding one
  after it, and name in the PR what you replaced or deleted. `docs/DOC-REVIEW.md` is the brief for the independent
  review.
- `docs/DESIGN.md` is the code map and the invariants the tests pin; `docs/CURRICULUM.md`
  the content format; `docs/TRAVEL-CANDO.md` the scenarios, cards and trip profile.
- Check behaviour changes on the real learner path (replay a feedback export's
  `learner.before.json` with its manifest's arguments), not only on simulated courses.
- **Privacy:** never write trip dates, itinerary, lodging or personal places into the
  repository, issues, PRs or exports.
- One PR per change; the owner merges. Checks: `python -m unittest` and
  `python -m audiolesson.cli validate curricula/is-en`.

## Read for the task

| Task | Relevant sources |
|---|---|
| Lesson flow (what a lesson plays, in what order) | LEARNING-DESIGN §3, §8 and §9 "Themes"; `audiolesson/themes.py`, `audiolesson/planner.py` |
| Form guidance (a word's forms, a part in its sentence) | LEARNING-DESIGN §9 "Parts against utterances"; `docs/CURRICULUM.md`; `audiolesson/exercises.py`, `audiolesson/nouns.py` |
| Content (a scene, items, scene verdicts) | LEARNING-DESIGN §9 "Good enough overall" and its scene check; `docs/CURRICULUM.md`, `docs/TRAVEL-CANDO.md`, `docs/SCENE-REVIEW.md` |
| Review scheduling (intervals, the written review) | LEARNING-DESIGN §6 and §9 "Evidence"; `audiolesson/learner.py`, `audiolesson/review_wording.py`; the related bot issue |
| Refactoring (behaviour unchanged) | the relevant `docs/DESIGN.md` sections; #281's criterion: the replays stay byte-identical |
| Documents | LEARNING-DESIGN §10; `docs/DOC-REVIEW.md` |

Read the history (`docs/history/`) when a current decision or finding needs it.
