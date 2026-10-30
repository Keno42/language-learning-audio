# Current status (the short brief)

This file is the one home of "Now": what we work on next, in order, and what was built since the last update. Rewrite
it when the state changes: an item leaves "Now" when the PR that builds it merges, and "Now" is re-ranked after every
round of learner feedback (`docs/LEARNING-DESIGN.md` (LD) §1). The owner approves a re-ranking by merging the PR that
makes it. Everything else is in LD: the long run and the table of built changes waiting for feedback (§8), the gaps
(§7), the hypotheses with their status (§4), the evidence lesson by lesson (§5). The learning policy is in
`docs/CURRENT-POLICY.md`.

## Now (updated 2026-10-29, after lesson 41), in order

Ranked as LD §9 "Governance" says: about 80% by how the next lessons feel, 20% by what may change a long-term decision, each
remark by how often its cause recurs on the replay of the latest export and what a fix costs. The latest export is lesson
41's; the next lesson is 42. Lesson 41 brought two remarks (LD §5.31): four new items made of two verbs and two time words
felt light as learning, and the guide on voiced replies came too often. Its closing held only today's new material (#435),
and no pick-out asked an answer just heard (#436). Load «light» after one «right»: the pace is not raised on one rating.
1. **Practice shared across easy substitutions (#439).** «Ég fer/kem á morgun/í kvöld.»: 3 weighted components, 20 model
   answers on four sentences, each item running its own ladder. **Next smallest step:** a recall whose sentence says several of
   today's new items advances each of their ladders; the time freed goes to other material or listening. Measured on the replay
   of the lesson-41 export before it is built.
2. **The voiced-reply guide once a lesson (#438).** **Built, in review (#440):** later plays say «The conversation again.» only;
   on the replay of lessons 41–44, the guide 3/3/1/4 → 1/1/1/1.
3. **Scenes for the material after lesson 50 (#327), in parallel.** Built (#432): the batch for lessons 41–50, heard from lesson
   41 (arranging to meet). Next: taxi and bus, the weather's further levels.

**Alongside:** the stretch before the closing in lesson 41 was 17 recalls of known material with no listening task (#437 found
none to give there): read again with #439, whose freed time may go to listening. What #427 leaves after #433, a `validate`
rule for a gendered partner reply to the learner's line; two units of one scene back to back (#273); «Mér finnst gaman að
hringja heim» and its meaning (#209). Listening help for a word reported hard to hear («lögreglustöðin», lesson 41) is
site_update_notifier#179's. The learner's own name and age (#428): an opt-in setting with a preview of the lines it makes and
of the name as Icelandic speech says it; Icelandic instructions (#429): each to start small.

**The long run alongside:** #327, one scene at a time for the new material the path brings, each a data PR of authored
Icelandic (candidates until native-checked). The town (asking the way), small talk (getting to know someone) and the
clothes shop (what you need, the price, trying it on) are written: on the replay of the lesson-30 export the day's new
lines are said in the played exchange in lessons 30–35 (17; before the town, 0 in nine lessons). The goal of the played
level is said after the opening, and the closing ends on the level's lines in the order of its turns. The town has a third
level for the way itself, and small talk a third and fourth; the batch for lessons 41–50 (#432) added arranging to meet and
the weather, and more levels for the town, small talk and the clothes shop (item 3). Next: taxi and bus, the weather's
further levels.

**Refactoring alongside (#281), behaviour unchanged:** one place for "which sentence holds this part", one for "can the
learner say this line", then the planner's build loop. Each step leaves every lesson `tools/same_lessons.py` builds
identical; the owner's replays of the lesson-21–23 exports, byte-identical, stay the check on the real learner path.
Built: `docs/DESIGN.md`'s invariants are one line per topic (#320) and the word regex and `norm_utterance` are
defined once (`audiolesson/text.py`, #321).

## Built since the last update (2026-10-15)

Each waits for its first feedback in the LD §8 table.
- **After lesson 41:** in review: the voiced-reply guide once a lesson (#440).
- **After lesson 40:** an authored dialogue played before voices the known set replies too (#430); a fixed dialogue played whole four times is not played whole again (#431); scenes for lessons 41–50 (#432); lesson 40's contexts (#433); the closing as one block, its listening just before it (#435, #437); no pick-out on an answer just heard (#436); help on an expression from the feedback form, and a new expression heard and asked about from the new-expression list (site_update_notifier#180, #183).
- **After lessons 38 and 39:** a pick-out turn's lines carry other values (#417); a known set reply in an exchange played again is voiced (#422); a sentence reported hard is tried again from its meaning first (#424); a conversation's end is marked (#425); the review's 🔊 replies named by card (site_update_notifier#176).
- **After lessons 36 and 37:** a cue says the learner's action first (#411); the replay plans the coming lessons as production does (#413); a theme level of three or more turns plays with one heard (#414).
- **Lesson 35's remarks (#407):** a loanword gets no slow split; the closing says «some of» when it leaves new items out; a pattern's other answers («Hún er …») and an aside on «hún».
- **Merged on 2026-10-23 (first heard in lesson 35 unless named):** a transform's pair (#394) and its instruction (#405);
  every promising framing line checked against what follows (#397); the town's slower reply (#393, lesson 38); a hard
  item's scene line by `line_role` (#392); the charge of an item never taught given back (#404); and tools: the feedback
  ledger (#399), the scene sheet of the replay (#402), `load-preview` (#401), `same_lessons.py` (#403), `top_lines.py`
  (#396), scenario coverage in `validate` (#395). The end of the fix-up phase is a §9 decision (#406).
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
  31 (7 of 8 components taught). The guard keeps the second half (#308), and once the lesson is built the charge of an
  item never taught is given back: `new_components` (the CLI's «X of a target Y», the replay's row) says what was taught,
  `charge_given_back` what was not. Within the build an item still counts from its selection, which is what stops the selection.
- **A transform asked from its few authored pairs, under one instruction (G12, G17).** Lesson 31 asked «asking for the same
  thing more politely» 8 times from 5 pairs, its instruction narrated 9 times. It does not recur in lessons 33–35; it
  will with the next transform introduced.
- #336: the other scenes' frames that vary in use, as each scene comes (`validate` lists the candidates; only the frames
  a scene varies).
- #270: the other frames (accusative orders, `dat_town`, `dat_hobby`), after the dative place forms' first feedback.
- #209: when a fluent speaker is available (G10), starting from the lines the lessons say most (`tools/top_lines.py` on the
  exported scripts). Every scene added since lesson 30 adds authored Icelandic to it.

#265 (expression first) and #270 (a noun with its gender and forms) are the umbrellas the items above belong to; #326
for the connections across lessons.

**Closed on 2026-10-23, each with the condition that reopens it** (the owner, after a structural review: an umbrella that
never closes collects work without a finish line):
- #149 (themes): every step merged. Reopens if a lesson plays no theme, or a feedback calls the lesson unrelated items again.
- #220 (retention after the first day): after lesson 34, recall at 7–13 days 13 of 13, at 14+ days 4 of 4, and 109 due with
  3 never asked. Reopens if the retention rows stop growing, or the queue grows past about 150 due again.
- site_update_notifier#124 (the bot's review on its own): closed on the same evidence. Reopens if the records show older
  lines no longer confirmed by the usual review, or if the learner asks for a short review apart from the lesson; the last
  lesson's new items are then still checked the next day, never earlier.
- #364 (a route per task, «Now» in one home): built by #374. Reopens if less reading comes with more misses.
- #236 (a one-off reply with several example answers): low priority, never asked for. Reopens on a learner remark that a
  good reply was treated as wrong.

## Where to look
- **Built, and how many feedbacks it has had:** the table under "Built, waiting for three feedbacks without the same remark"
  in LD §8.
- **Rows read instead of remarks:** LD §8, below the table, and `tools/replay_lesson.py` (the daily read).
- **Open gaps:** LD §7 (the "now" column).
- **The long run, step by step:** LD §8.
- **Decisions already made:** LD §9. Do not reopen without new evidence.
