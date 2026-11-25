# Working on this repository

- **The learner's long-term accomplishment comes first.** Their time and life are limited; what they can do at the end is what the
  lessons are for. Every round of feedback builds one step of the long run named in `docs/CURRENT-STATUS.md` («The long run»),
  whatever the remarks say; only the owner waives it, with a reason recorded in the ledger (`long_run_waived`). `tests/test_docs.py`
  fails on a round that names neither (LEARNING-DESIGN §9 "Governance"). Answering remarks alone is the drift this rule exists to stop.
- **Start with `docs/CURRENT-POLICY.md` and `docs/CURRENT-STATUS.md`** (the short briefs: what the project is for and
  what always holds; what we work on now, what is open after it, and where to look for the rest).
- **Then read the sources for the task** (the table below), and answer `docs/LEARNING-DESIGN.md` §1's checklist in the
  issue or PR: the outcome it serves, the gap it closes, the hypothesis it relies on, the evidence behind it and what it
  predicts. Read all of `docs/LEARNING-DESIGN.md` for a change to project-wide learning policy or a design change across
  several areas. The document also lists the decisions already made (§9) and our known failure modes (§11). Above all:
  don't answer each remark with its own local fix; find the shared cause and fit it into the roadmap (§8).
- After a round of learner feedback, update its evidence (§5), the hypothesis statuses (§4) and "Now" in
  `docs/CURRENT-STATUS.md`.
- **Documents: replace, don't append** (LEARNING-DESIGN §10). Rewrite a statement that changed rather than adding one
  after it, move a dated record the current text no longer needs to `docs/history/`, and name in the PR what you replaced,
  moved or deleted. `docs/DOC-REVIEW.md` is the brief for the independent
  review.
- `docs/DESIGN.md` is the code map and the invariants the tests pin; `docs/CURRICULUM.md`
  the content format; `docs/TRAVEL-CANDO.md` the scenarios, cards and trip profile.
- Check behaviour changes on the real learner path (replay a feedback export's
  `learner.before.json` with its manifest's arguments), not only on simulated courses.
- **Comments say what holds and why, now** (owner, 2026-11-25). A code comment, a test's docstring or a `docs/DESIGN.md` row states the
  rule and its reason, with the issue that decided it («#339: a word is caught once»); how it came to be (what it was before, which
  lesson found it, a threshold's earlier values) belongs in the commit, the PR and `docs/history/`. Don't rewrite comments in bulk:
  when a change touches code, make the comments it touches state the current rule, shortening a chain of dated additions to one
  sentence as you go.
- **Privacy:** never write trip dates, itinerary, lodging or personal places into the
  repository, issues, PRs or exports.
- One PR per change; the owner merges. Checks: `python tools/partest.py` (the tests `python -m unittest` runs, on every
  core: minutes, not tens of minutes) and `python -m audiolesson.cli validate curricula/is-en`.

## Read for the task

| Task | Relevant sources |
|---|---|
| Lesson flow (what a lesson plays, in what order) | LEARNING-DESIGN §3, §8 and §9 "Themes"; `audiolesson/themes.py`, `audiolesson/planner.py` |
| Form guidance (a word's forms, a part in its sentence) | LEARNING-DESIGN §9 "Parts against utterances"; `docs/CURRICULUM.md`; `audiolesson/exercises.py`, `audiolesson/nouns.py` |
| Content (a scene, items, scene verdicts) | LEARNING-DESIGN §9 "Good enough overall" and its scene check; `docs/CURRICULUM.md`, `docs/TRAVEL-CANDO.md`, `docs/SCENE-REVIEW.md` |
| Review scheduling (intervals, the written review) | LEARNING-DESIGN §6 and §9 "Evidence"; `audiolesson/learner.py`, `audiolesson/review_wording.py`; the related bot issue |
| Refactoring (behaviour unchanged) | the relevant `docs/DESIGN.md` sections; #281's criterion: `tools/same_lessons.py` against `origin/main` finds every simulated lesson identical, and the owner's replays stay byte-identical (the real learner path) |
| Documents | LEARNING-DESIGN §10; `docs/DOC-REVIEW.md` |

Read the history (`docs/history/`) when a current decision or finding needs it.
