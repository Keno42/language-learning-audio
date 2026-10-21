# Current status (the short brief)

This file is the one home of "Now": what we work on next, in order, and what was built since the last update. Rewrite
it when the state changes: an item leaves "Now" when the PR that builds it merges, and "Now" is re-ranked after every
round of learner feedback (`docs/LEARNING-DESIGN.md` (LD) §1). The owner approves a re-ranking by merging the PR that
makes it. Everything else is in LD: the long run and the table of built changes waiting for feedback (§8), the gaps
(§7), the hypotheses with their status (§4), the evidence lesson by lesson (§5). The learning policy is in
`docs/CURRENT-POLICY.md`.

## Now (updated 2026-10-22), in order

Ranked by the effect on the next lesson as the replay of the latest export shows it (LD §9 "Governance": about 80% /
20%). The latest export is lesson 30's; the next lesson is 31.
1. **The coming lessons' sentences get a verdict before they are said (G6; the scene check, LD §9 "Good enough
   overall").** On the replay of the lesson-30 export, 148 sentences that lessons 30–43 can generate have no verdict.
   «Ég borða ekki mjólk.» and «Má ég versla?» are among them, and lesson 31 asks the second. The sheet so far was printed
   for the patterns and words the learner had met, so a word introduced today is generated unjudged the same day, and
   the negative and question forms are on no sheet. **Next smallest step:** the sheet of the coming material to an
   outside reviewer (`docs/SCENE-REVIEW.md`), the verdicts in one PR; then the sheet printed from the replay of each new
   export, the forms included.
2. **A transform is asked from five sentences, under one instruction (G12, G17).** Lesson 31 introduces «asking for the
   same thing more politely» and asks it 8 more times: «Get ég fengið matseðilinn?» 3 times, and «Say it more politely,
   as a question:» narrated 9 times, where the other lessons of the replay narrate one situation at most 5 times. Its
   examples are 5 authored pairs. Its two patterns («Ég ætla að fá {thing}.», «Get ég fengið {thing}?») share 10
   fillers by their tags, and «kaffi», «te» and «matseðilinn» are not among them. **Next smallest step:** choose between
   more authored pairs and pairs made from the two patterns (the tags aligned first, which also changes the scene
   check's sheets), and shorten the instruction after its second ask.
3. **The new material after lesson 36 has no level to play (#327).** With the town, small talk and the clothes shop,
   «today's new items said as a turn of the played exchange» reads 17 in lessons 30–35 and 0 from lesson 36. From there
   the lessons replay town 2, the supermarket's level 2 and the clothes shop's level 2 in turn, while the day's
   material is still the way («Það er til vinstri.», «Hvað er langt þangað?», «Ég er týnd.», «Geturðu sýnt mér á
   kortinu?», «Það tekur {duration}.») and getting to know someone (age, job, family). **Next smallest step:** a third
   town level for the way itself: left and right, how long it takes, the map.

**The long run alongside:** #327, one scene at a time for the new material the path brings, each a data PR of authored
Icelandic (candidates until native-checked). The town (asking the way), small talk (getting to know someone) and the
clothes shop (what you need, the price, trying it on) are written: on the replay of the lesson-30 export the day's new
lines are said in the played exchange in lessons 30–35 (17; before the town, 0 in nine lessons). The goal of the played
level is said after the opening, and the closing ends on the level's lines in the order of its turns. Next: the way
itself (item 3), then taxi and bus, winter talk.

**Refactoring alongside (#281), behaviour unchanged:** one place for "which sentence holds this part", one for "can the
learner say this line", then the planner's build loop. Each step leaves the replays of the lesson-21–23 exports
byte-identical. Built: `docs/DESIGN.md`'s invariants are one line per topic (#320) and the word regex and `norm_utterance` are
defined once (`audiolesson/text.py`, #321).

## Built since the last update (2026-10-15)

Each waits for its first feedback in the LD §8 table.
- **Scenes (#327):** the town (#365), small talk (#371) and the clothes shop (#372), two levels each; a level played in
  the lesson that teaches its lines (#365); the level's goal said after the opening (#369); the closing ends on the
  level's lines in the order of its turns (#370).
- **Forms:** a known noun's other form taught in its frame, against the form the learner knows, with why it changes
  (#270: #368); a reflexive fill only after «ég» (#373).
- **The scene check:** a verdict for each sentence a pattern makes (#352), a line for the whole pattern (#363), a scene
  line narrated like a situation (#362), the verdicts for lessons 29 and 31 (#354, #361).
- **From lessons 26 and 27:** a word caught once, new words through the catch, pick-outs that rotate (#339: #344,
  #350); a hard word modelled slowly and split (#337: #342, #351); the pick-out's turns (#335: #343, #353); the
  transport frames as patterns (#336: #346); the closing asks each sentence once (#349).
- **The review:** a transform question keeps its input sentence (#366: #367).

## Open issues after "Now", in order
- **An item counted toward the target when it is selected, not when it is taught.** On the replay, lesson 30's second
  half starts through #294's guard: an arc selected «Ég vil hvíla mig.» at minute 17 and the item was taught in lesson
  31 (7 of 8 components taught). The guard keeps the second half (#308); the cause is not fixed.
- #336: the other scenes' frames that vary in use, as each scene comes (`validate` lists the candidates; only the frames
  a scene varies).
- #270: the other frames (accusative orders, `dat_town`, `dat_hobby`), after the dative place forms' first feedback.
- #209: when a fluent speaker is available (G10). Every scene added since lesson 30 adds authored Icelandic to it.
- #364: the issue template's use, and the measured comparison of reading before and after the route per task.
- #236: a one-off reply gets several example answers (owner: low priority).

#265 (expression first), #149 (themes) and #270 (a noun with its gender and forms) are the umbrellas the items above
belong to; #220 stays open for its ranking (the bot's review on its own, site_update_notifier#124, waits for it); #326
for the connections across lessons.

## Where to look
- **Built, and how many feedbacks it has had:** the table under "Built, waiting for three feedbacks without the same remark"
  in LD §8.
- **Rows read instead of remarks:** LD §8, below the table, and `tools/replay_lesson.py` (the daily read).
- **Open gaps:** LD §7 (the "now" column).
- **The long run, step by step:** LD §8.
- **Decisions already made:** LD §9. Do not reopen without new evidence.
