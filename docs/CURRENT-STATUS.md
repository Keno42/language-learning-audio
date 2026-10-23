# Current status (the short brief)

This file is the one home of "Now": what we work on next, in order, and what was built since the last update. Rewrite
it when the state changes: an item leaves "Now" when the PR that builds it merges, and "Now" is re-ranked after every
round of learner feedback (`docs/LEARNING-DESIGN.md` (LD) §1). The owner approves a re-ranking by merging the PR that
makes it. Everything else is in LD: the long run and the table of built changes waiting for feedback (§8), the gaps
(§7), the hypotheses with their status (§4), the evidence lesson by lesson (§5). The learning policy is in
`docs/CURRENT-POLICY.md`.

## Now (updated 2026-10-23, after lesson 34), in order

Ranked by the effect on the next lesson as the replay of the latest export shows it (LD §9 "Governance": about 80% /
20%). The latest export is lesson 34's; the next lesson is 35. Lesson 34's four remarks are answered in review (LD
§5.24): a stored pattern question names its form (#385, then the bot's `REFINE_VERSION` 6), an embed's «other sentence»
is never its own phrase (#386), a pick-out that a drill follows ends with «Back to speaking.» (#387), and a pattern's
introduction promises a swap only when one follows (#388). Three of them share a cause: a framing line said for the
general case, without looking at what follows.
1. **The coming lessons' sentences get a verdict before they are said (G6; the scene check, LD §9 "Good enough
   overall").** On the replay of the lesson-30 export, the sentences that lessons 30–43 can generate were sent to an
   outside review: it judged «Ég borða ekki mjólk.» false and gave four permission questions their scenes, and 142
   still have no verdict, «Má ég versla?» among them. The sheet was printed for the patterns and words the learner had
   met, so a word introduced today is generated unjudged the same day, and the negative and question forms are on no
   sheet. **Next smallest step:** scene lines for the 142 from a reviewer (`docs/SCENE-REVIEW.md`), faithful to each
   sentence's meaning; then, from each new export, the sheet its replay prints (`--scene-sheet`: the sentences the coming
   lessons say, the forms included), until the replay's row «pattern sentences said with no scene verdict» reads 0.
2. **The new material after lesson 40 has no level to play (#327).** On the replay of the lesson-33 export, «today's new
   items said as a turn of the played exchange» reads 2 to 5 in every lesson from 33 to 40, with the town's third level
   (the way, #381) in lesson 38 and small talk's third and fourth (nationality and work, age and married; #383) in
   lessons 39 and 40; from lesson 41 it is 0. The day's material is then making arrangements («á morgun», «í kvöld», «Ég
   fer {time}.», «Hentar það?», «Það hentar vel.», «Ég er sein.», «Ég kem eftir tíu mínútur.») and more of the way
   («Hvernig kemst ég að …?», «á horninu», «hinum megin við götuna», «hálftíma»). **Next smallest step:** a level for
   arranging to meet (when, whether it suits, being late); no can-do scenario names it yet.
3. **The feedback form says what a load answer will change.** Another learner, on 15-minute lessons: «15分レッスンも4つ
   くらい新出表現がほしい», and «変わらなかったから最近フィードバックしてなかった». A «light» answer raises the next
   lesson's target only after two in a row (with at most 25% of new items failed and a small backlog), and «heavy» only
   blocks a rise (`suggest_target`, LD §9 "Pace"); the form says none of it, so a single answer looks as if it changed
   nothing, and the signal the pace depends on (H9) stops. **Next smallest step:** an LLA command that prints the next
   lesson's target for each load answer, and the bot shows it beside the choice (the owner's proposal).

**The long run alongside:** #327, one scene at a time for the new material the path brings, each a data PR of authored
Icelandic (candidates until native-checked). The town (asking the way), small talk (getting to know someone) and the
clothes shop (what you need, the price, trying it on) are written: on the replay of the lesson-30 export the day's new
lines are said in the played exchange in lessons 30–35 (17; before the town, 0 in nine lessons). The goal of the played
level is said after the opening, and the closing ends on the level's lines in the order of its turns. The town has a third
level for the way itself, and small talk a third and fourth. Next: arranging to meet (item 2), then taxi and bus, winter talk.

**Refactoring alongside (#281), behaviour unchanged:** one place for "which sentence holds this part", one for "can the
learner say this line", then the planner's build loop. Each step leaves the replays of the lesson-21–23 exports
byte-identical. Built: `docs/DESIGN.md`'s invariants are one line per topic (#320) and the word regex and `norm_utterance` are
defined once (`audiolesson/text.py`, #321).

## Built since the last update (2026-10-15)

Each waits for its first feedback in the LD §8 table.
- **Scenes (#327):** the town (#365, its third level #381), small talk (#371, its third and fourth levels #383) and the clothes shop (#372); a gendered learner
  line said in the form of the learner's voice, named in the cue (#382); an authored dialogue that repeats the lesson's
  scene is not played (#384); a level played in
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
- **Documents:** a route per task in `CLAUDE.md`, and «Now» in this file only (#364: #374).
- **The scene check:** the first outside review of the coming lessons' sentences, six verdicts (#376).
- **Connections (#326):** the allergy line in the café's fourth level, a scene to practise it through (#379), and its pattern
  «Ég er með ofnæmi fyrir {…}.» with nouns in the dative, so its other practices are other sentences (#380).

## Open issues after "Now", in order
- **The reading deck has had no outside review.** Another learner: its cards ask to read words no lesson has taught, and
  a hint such as «allt は例外的に「アルト」» sounds wrong to them. It is: «allt» is [al̥t], a voiceless «l» with no vowel
  after it, and «ル» gives both a voice and a vowel. Katakana hints add vowels throughout the deck. The corner becomes
  «読んでみよう», read without a rating (site_update_notifier#165); the hints need a reviewer, as the scenes do.
- **An item counted toward the target when it is selected, not when it is taught.** On the replay, lesson 30's second
  half starts through #294's guard: an arc selected «Ég vil hvíla mig.» at minute 17 and the item was taught in lesson
  31 (7 of 8 components taught). The guard keeps the second half (#308); the cause is not fixed.
- **A transform asked from its few authored pairs, under one instruction (G12, G17).** Lesson 31 asked «asking for the same
  thing more politely» 8 times from 5 pairs, its instruction narrated 9 times. It does not recur in lessons 33–35; it
  will with the next transform introduced.
- #336: the other scenes' frames that vary in use, as each scene comes (`validate` lists the candidates; only the frames
  a scene varies).
- #270: the other frames (accusative orders, `dat_town`, `dat_hobby`), after the dative place forms' first feedback.
- #209: when a fluent speaker is available (G10). Every scene added since lesson 30 adds authored Icelandic to it.
- #364: the issue template's use, and the measured comparison of reading before and after the route per task.
- #236: a one-off reply gets several example answers (owner: low priority).

#265 (expression first), #149 (themes) and #270 (a noun with its gender and forms) are the umbrellas the items above
belong to; #220 stays open for its ranking; #326 for the connections across lessons. The bot's review on its own
(site_update_notifier#124) is closed (2026-10-23): what it waited for is built (site_update_notifier#133, #139; #331),
lesson 34's queue held 3 never-asked entries of 109 due, and recalls at 7 and 14+ days are recorded. It reopens if the
records show older lines no longer confirmed by the usual review, or if the learner asks for a short review apart from
the lesson; the last lesson's new items are then still checked the next day, never earlier.

## Where to look
- **Built, and how many feedbacks it has had:** the table under "Built, waiting for three feedbacks without the same remark"
  in LD §8.
- **Rows read instead of remarks:** LD §8, below the table, and `tools/replay_lesson.py` (the daily read).
- **Open gaps:** LD §7 (the "now" column).
- **The long run, step by step:** LD §8.
- **Decisions already made:** LD §9. Do not reopen without new evidence.
