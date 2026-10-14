# Current status (the short brief)

The status is kept in **one** place, `docs/LEARNING-DESIGN.md` (LD) §8: the "Now" list, the table of built changes with the
number of feedbacks each has had without a remark, and the open issues. This brief does not repeat the table or list changes
and PRs; read LD §8 for what is built and what is being evaluated, and GitHub for open PRs. §7 has the gaps, §4 the
hypotheses with their status, §5 the evidence lesson by lesson. The learning policy is in `docs/CURRENT-POLICY.md`.

Checked against LD §8 on 2026-10-14. If the two differ, LD is the record and this file is wrong.

## Now (copied from LD §8, verbatim)

**Now (updated 2026-10-14, after lesson 26's feedback), in order.** Tomorrow's lesson first, the long run alongside
(owner: about 80% / 20%). This re-ranking is proposed in the PR that wrote it and is the owner's call. The previous list
is built and in the table below: new material by scene (#327 part 1), a hard word through its connections (#326), #220's
LLA half and #198's endings (#323).
1. **The lesson-26 preview's findings (#333),** all heard in the real lesson 26: «Get ég fengið leigubíl?» not linked to
   its pattern; a «pattern you know» play of a phrase taught two minutes earlier; «Showing the address:» read as a cue;
   «Má ég sofa?» (the owner's call: a named exception or a slot tag). Small, and each one is in tomorrow's lesson.
2. **A word reported hard to say gets its slow, split model again (#337).** The rule also reads the words inside
   phrases, and adds the sounds this learner has stumbled on, not a phonetics catalogue. It is H13's first real test:
   the «sooner» items of lesson 26 come back in lesson 27.
3. **The pick-out marks its turns (#335):** «Listen and answer.», «The answer:», «Listen again.», as the learner wrote
   it. Wording only.
4. **A scene's lines that vary in use are taught as a pattern with the scene's fillers (#336),** transport first. It is
   the cause behind «úlpu» (#311), #333's first point and the bus, in the case where no pattern was written, and it
   gives #326's connections at the introduction.

#270's step 2 is what the tags already do (#317, #324). The size and price frames once listed here were an example in the
lesson-25 remark, not a requirement, and #326 replaces them.

**Refactoring alongside (#281), behaviour unchanged:** one place for "which sentence holds this part", one for "can the
learner say this line", then the planner's build loop. Each step leaves the replays of the lesson-21–23 exports
byte-identical. Built: `docs/DESIGN.md`'s invariants are one line per topic (#320) and the word regex and `norm_utterance` are
defined once (`audiolesson/text.py`, #321).

## Where to look
- **Built, and how many feedbacks it has had:** the table under "Built, waiting for three feedbacks without the same remark"
  in LD §8. A row leaves the table at three.
- **Rows read instead of remarks:** LD §8, below the table, and `tools/replay_lesson.py` (the daily read).
- **Open gaps:** LD §7 (the "now" column).
- **Open issues after "Now":** LD §8.
- **Decisions already made:** LD §9. Do not reopen without new evidence.
