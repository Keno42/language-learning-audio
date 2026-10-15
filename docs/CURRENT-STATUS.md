# Current status (the short brief)

The status is kept in **one** place, `docs/LEARNING-DESIGN.md` (LD) §8: the "Now" list, the table of built changes with the
number of feedbacks each has had without a remark, and the open issues. This brief does not repeat the table or list changes
and PRs; read LD §8 for what is built and what is being evaluated, and GitHub for open PRs. §7 has the gaps, §4 the
hypotheses with their status, §5 the evidence lesson by lesson. The learning policy is in `docs/CURRENT-POLICY.md`.

If the two differ, LD is the record and this file is wrong; `tests/test_docs.py` checks that the copy is verbatim.

## Now (copied from LD §8, verbatim)

**Now (updated 2026-10-15), in order,** ranked by the effect on the next lesson as the replay of the latest export
shows it (§9 "Governance": about 80% / 20%).
1. **A word is caught once, some new words are introduced through the catch, and the pick-outs rotate across lessons
   (#339; the owner's decision, §9 "Conversation").** The replay of lesson 27 asks «sestu», «kjötsúpa», «þarftu» and
   the same two pick-outs again, as every lesson since 23 and 25. The two parts go together: the three words have had
   their catch, so with «once» alone the form would leave the lessons from lesson 27, and the introductions bring it
   back. The second half catches only words never caught. Of the 8 glossed partner lines, the 3 usable today are
   those words; the other 5 become usable as the learner learns their other words, and #327's theme levels can add
   more.
2. **A word reported hard to say gets its slow, split model again (#337).** The «sooner» items of lesson 26 come back in
   lesson 27, so it is H13's first real test. The rule also reads the words inside phrases and adds the sounds this
   learner has stumbled on.
3. **The pick-out marks its turns (#335):** «Listen and answer.», «The answer:», «Listen again.», as the learner wrote
   it. Wording only, and 1–3 pick-outs come in every lesson.
4. **A scene's lines that vary in use are taught as a pattern with the scene's fillers (#336).** The replay of lesson 27
   says six of its sentences 8 times each in one wording («Ég vakna klukkan sjö.», «Ég kem heim klukkan sex.»), the
   bus's shape. The largest effect on repetition and the largest cost (data); the frames a scene varies first.

**The long run alongside, started now:** #327, the rest of part 1 (a scene line for new items whose topic has no theme)
and part 2 (more theme levels: authored Icelandic, candidates until native-checked, so they take longest to start).
The themes' levels run out at lesson 28, and the replay of lesson 27 takes 0 of its 12 new items from the played
scene.

**Refactoring alongside (#281), behaviour unchanged:** one place for "which sentence holds this part", one for "can the
learner say this line", then the planner's build loop. Each step leaves the replays of the lesson-21–23 exports
byte-identical. Built: `docs/DESIGN.md`'s invariants are one line per topic (#320) and the word regex and `norm_utterance` are
defined once (`audiolesson/text.py`, #321).

## Where to look
- **Built, and how many feedbacks it has had:** the table under "Built, waiting for three feedbacks without the same remark"
  in LD §8.
- **Rows read instead of remarks:** LD §8, below the table, and `tools/replay_lesson.py` (the daily read).
- **Open gaps:** LD §7 (the "now" column).
- **Open issues after "Now":** LD §8.
- **Decisions already made:** LD §9. Do not reopen without new evidence.
