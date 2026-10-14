# Working on this repository

- **Read `docs/CURRENT-POLICY.md` and `docs/CURRENT-STATUS.md` first** (the short briefs: what the
  project is for, what always holds, what is built and what is next).
- **Before opening an issue, proposing a change or implementing one, read the sections of
  `docs/LEARNING-DESIGN.md` the briefs point at** (all of it for a change to learning policy or to the
  structure of lessons or review), and answer its §1 checklist in the issue or PR: the outcome it
  serves, the gap it closes, the hypothesis it relies on, the evidence behind it and what it
  predicts. The document also lists the decisions already made (§9) and our known failure
  modes (§11). Above all: don't answer each remark with its own local fix; find the shared
  cause and fit it into the roadmap (§8).
- After a round of learner feedback, update its evidence (§5) and hypothesis statuses (§4).
- `docs/DESIGN.md` is the code map and the invariants the tests pin; `docs/CURRICULUM.md`
  the content format; `docs/TRAVEL-CANDO.md` the scenarios, cards and trip profile.
- Check behaviour changes on the real learner path (replay a feedback export's
  `learner.before.json` with its manifest's arguments), not only on simulated courses.
- **Privacy:** never write trip dates, itinerary, lodging or personal places into the
  repository, issues, PRs or exports.
- One PR per change; the owner merges. Checks: `python -m unittest` and
  `python -m audiolesson.cli validate curricula/is-en`.
