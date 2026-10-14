# Current status (the short brief)

The status is kept in **one** place, `docs/LEARNING-DESIGN.md` (LD) §8: the "Now" list, the table of built changes with the
number of feedbacks each has had without a remark, and the open issues. This brief does not repeat the table or list changes
and PRs; read LD §8 for what is built and what is being evaluated, and GitHub for open PRs. §7 has the gaps, §4 the
hypotheses with their status, §5 the evidence lesson by lesson. The learning policy is in `docs/CURRENT-POLICY.md`.

Checked against LD §8 on 2026-10-14. If the two differ, LD is the record and this file is wrong.

## Now (copied from LD §8, verbatim)

**Now (updated 2026-10-14, after a review of all open issues against the long-term plan), in order.** Tomorrow's lesson
first, the long run alongside (owner: about 80% / 20%). This re-ranking is proposed in the PR that wrote it and is the
owner's call.
1. **New material chosen by scene (#327, part 1).** The themes' next levels run out at lesson 28 on the real path, three
   lessons away. From then on, new items come from the trip and curriculum order whatever scene the lesson plays (3 of
   112 from the played scene in lessons 25–34). Choose the day's new material as a group from one scene or topic. Make
   the played scene match it where a theme exists. Give the others a scene line. No new content needed.
2. **A word reported hard is practised through its connections (#326).** Its scene, the word in other patterns, and other
   words of the same pattern, not more of the same sentence (the owner, after lesson 25; «úlpu»).
   *Built (the PR of #326, waiting for feedback):* for items open or hesitated at their last review, the 2nd to 4th
   practice of a lesson goes through a scene line, another pattern or the same pattern with other words; the daily
   read lists the connections per item and the items with none (content gaps). Not built: «sooner» (it is not kept
   as an outcome), a remark naming an item, the connections across lessons.
3. **#220, the LLA half of the ranking:** a 言えた on a due item at a real gap extends its interval, and two in a row raise
   the ease. Until then a ranked check saves lesson time on its day only. So the bot's ranking (site_update_notifier#139)
   should keep the retention seats oldest-first, or take at most a third of them. The bot's review on its own (#124)
   waits for this.
4. **#198 finished (#323):** the endings said piece by piece, as the owner decided, and no lone «.» narrated in a note.
   The second is older than #323: `kurteisi` and `tolur_kyn` have it too.

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
