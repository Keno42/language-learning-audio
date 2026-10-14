# Current status (the short brief)

The status is kept in **one** place, `docs/LEARNING-DESIGN.md` (LD) §8: the "Now" list, the table of built changes with the
number of feedbacks each has had without a remark, and the open issues. This brief does not repeat the table or list changes
and PRs; read LD §8 for what is built and what is being evaluated, and GitHub for open PRs. §7 has the gaps, §4 the
hypotheses with their status, §5 the evidence lesson by lesson. The learning policy is in `docs/CURRENT-POLICY.md`.

Checked against LD §8 on 2026-10-14. If the two differ, LD is the record and this file is wrong.

## Now (copied from LD §8, verbatim)

**Now (updated 2026-10-14, after #133, #132, #312, #311 and #270 step 1 were built), in order.** Tomorrow's lesson first,
the long run alongside (owner: about 80% / 20%). This re-ranking is proposed in the PR that wrote it (#322) and is the owner's
call.
1. **#220's ranking:** choose the review's checks by the lesson time a 言えた would save, so older items are confirmed where
   it pays. The review backlog's near-term part is built (site_update_notifier#133); a review on its own (the bot's #124)
   waits for this.
2. **#270 steps 2–3:** a slot asks for a case and the noun gives the form the learner has or is being taught; each scene lists
   its frames and the case each asks. #198 («heiti potturinn») is its first case; #311's size and price frames need it.

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
