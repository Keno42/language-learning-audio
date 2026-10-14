# Current policy (the short brief)

Read this first for a routine task, then the sections of `docs/LEARNING-DESIGN.md` (LD) it points at. A change to learning
policy, to the structure of the lessons or of the review, or a new kind of exercise still needs LD in full. This file
summarises; if it and LD disagree, LD §9 (decisions) wins, and this file is wrong and gets fixed. Last checked against LD on
2026-10-14. It states decisions; hypotheses are bets and are marked so. Status of the work is in `docs/CURRENT-STATUS.md`.

## What the project is for
- **The product:** daily audio lessons in the Pimsleur tradition, generated from a curriculum (TOML) and a learner model,
  plus a Discord review (the bot, `Keno42/site_update_notifier`). One learner: a Japanese speaker, fluent in English, A1 in
  Icelandic, preparing for a trip. About 30 minutes of audio a day plus the review (LD §2).
- **The north star:** on the trip the learner can take part in the everyday scenes of travel in Icelandic, enjoy reading
  what is around them, and show respect. Outcomes **O1** say it when it is needed; **O2** get through what locals say; **O3**
  read and enjoy (the reading cards, in Discord); **O4** show respect; **O5** keep going: not boring, not overloading
  (LD §3). O5 is what every other outcome depends on.
- **The concept (owner, after lesson 20):** not an app for any natural Icelandic sentence. Each scene has **target
  expressions**, with only as many parallel expressions as help the target come out quickly. The lessons should leave the
  learner able to (1) use the ear for Icelandic and answer the set scenes, (2) find the information they need in what is
  said, (3) pin down the part they do not understand, (4) keep enjoying it. A finer decision says which of these it serves;
  when none, it waits (LD §3).

## Constraints that always hold
- **The audio cannot hear the learner.** Every retrieval is **presumed** successful until the review says otherwise.
  Presumed success is kept apart from **confirmed** outcomes (the review's 言えた / 迷った / 言えなかった; #119). A confirmed
  recall after a real gap is the evidence of retention (H2: only success after a gap is evidence; one confirmed after 7 days or more also raises the ease, #298); success minutes after an exposure is practice.
  `knows()` means two recalls on or after a due date.
- **A lesson is about 30 minutes and uses its time** (the daily dose, owner after lesson 13). The time is filled with
  material that loads the learner: new material to hear, exchanges, failed items brought back. Never with repetition of what
  is known (H11), never by stretching pauses. Nothing is designed for other lengths.
- **One learner.** Every comparison is within that learner and across time. A single remark or lesson is a lead, not a
  pattern. Feedback must stay nearly effortless; the learner's reports lean to success, and an LLM never produces one.
- **Privacy:** never write trip dates, itinerary, lodging, personal places or scenario weights into the repository, issues,
  PRs, logs or exports. Use lesson numbers and issue numbers. Secrets (the speech key) reach the bot sealed through the
  repository and never appear in logs, URLs or Discord.
- **A human approves every change.** Nothing changes the learner model or the planner automatically. One PR does one
  change; the owner merges. No LLM partner or grader (#129).
- **Content is not native-reviewed.** All scene lines, partner lines, forms, genders and glosses are candidates (G10, #209).
  Native corrections are applied when they come.

## The design in one page
- **Scene first (H4, the main bet; owner decision 2026-10-03).** Every lesson after the first is built around a theme: one
  scene's exchange at rising levels. The theme ranks above the item count and above the trip order of single items.
- **Expression first (#265).** The target expression is the unit for introducing, playing, reviewing and pacing. A **part**
  (a word, «kaupa miða») is introduced inside the expression that holds it, never first; it is asked through a sentence in
  the lesson and in the review. Bare is the fallback only when no sentence exists. A question whose cue is its answer is
  never asked. One rule decides every learner line in every play mode: sayable → asked, otherwise heard with its meaning.
- **Similar items apart (H5).** Group new material by scene, not by semantic set (numbers, colours): at most three new items
  of one set a lesson. A fixed phrase that is an instance of a pattern is linked to it (`instance_of`), and `validate`
  fails for an unlinked one.
- **Pace (H9).** The unit is weighted new components (#218), not new items; it never depends on the departure date, and is
  throttled only by what the learner reports (recall over the last three lessons, the load rating). Close variants do not
  fill spare time; a form comes with a purpose.
- **Repetition.** A short item is said alone at most three times a lesson; a fixed sentence at most nine; the same
  situation narrated in full at most twice. A pattern is not a lesson's whole supply (about ten generated sentences). Not-due
  items wait for their date (#94). An open item (failed) is practised every lesson and asked at the next review until it is
  recalled.
- **Spare time and the second half.** Once the lesson has taught what the target asked for, the second half is a rotation
  of the ear and the scene: hear the scene, pick out information, catch an unknown word, use one of today's expressions
  (concepts 2 and 3, #248). Not recombination of known patterns for its own sake.
- **Good enough overall (owner, after lesson 20).** Eighty points across the whole lesson beat a hundred on one part. Fix a
  part that scores twenty (boring, confusing, contradictory) before any precision work. Rules cover about nine cases in ten;
  the tenth is a named exception (LD §9 lists them), not a new mechanism. About one line in ten that a native speaker
  would not quite say is acceptable; linguistic-detail checks advise and never block.
- **The written review asks in its own words** (no lesson cues) and has its own rules: a first 言えた waits 3 days, the
  backlog is bounded (about 100 due), a new scene or reading card comes every review while the deck has one.
- **Audio.** No pause stretching; only plausible sentences in plausible scenes (H7); a gap at every change of voice (#301);
  a slow model is word by word at natural speed (#261, #302).

## Before you change anything
1. Answer LD §1 in the issue or PR: the outcome and concept it serves, the gap (LD §7) it closes, the hypothesis (LD §4),
   the evidence, the prediction (what changes in which signal, and what would show it wrong), the cost (lesson time is
   fixed: anything added displaces something), the smallest scope, the underlying need, privacy.
2. Do not answer each remark with its own local fix. Find the shared cause and fit the change into the roadmap (LD §8).
   Check LD §9 (decisions already made; do not reopen without new evidence) and LD §11 (our failure modes).
3. State acceptance about the learner (what they hear, say or can do), not only about code paths.

## Verification a change needs
- `python -m unittest` and `python -m audiolesson.cli validate curricula/is-en` pass. The tests pin learner-facing behaviour.
- Check a behaviour change on **the real learner path**: replay the latest feedback export's `learner.before.json` with its
  manifest's arguments, which include the trip ordering (`python tools/replay_lesson.py <export> --trip <the private profile> --lessons 3`), not only a simulated course. Without `--trip` the replay builds a different lesson. Do not write where the profile lives. A simulated course
  presumes every recall and hides what the real path shows (#94, #316).
- A refactoring leaves the replays byte-identical (`script.json`, `plan.json`).
- Every default reproduces today's behaviour, or the change of behaviour is the point and is stated. The settings that
  produced a lesson stay recorded (`plan.json`, the manifest).
- After a round of learner feedback: replay the export, read the signals, update the evidence (LD §5) and the hypothesis
  statuses (LD §4), re-rank the roadmap (LD §8). A change is done when its row in the daily read reads 0 and three feedbacks
  carry no remark of the same kind.
