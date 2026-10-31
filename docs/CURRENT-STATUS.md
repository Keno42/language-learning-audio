# Current status (the short brief)

This file is the one home of "Now": what we work on next, in order, and what was built since the last update. Rewrite
it when the state changes: an item leaves "Now" when the PR that builds it merges, and "Now" is re-ranked after every
round of learner feedback (`docs/LEARNING-DESIGN.md` (LD) §1). The owner approves a re-ranking by merging the PR that
makes it. Everything else is in LD: the long run and the table of built changes waiting for feedback (§8), the gaps
(§7), the hypotheses with their status (§4), the evidence lesson by lesson (§5). The learning policy is in
`docs/CURRENT-POLICY.md`.

## Now (updated 2026-10-31, after lesson 42), in order

Ranked as LD §9 "Governance" says: about 80% by how the next lessons feel, 20% by what may change a long-term decision, each
remark by how often its cause recurs on the replay of the latest export and what a fix costs. The latest export is lesson
42's; the next lesson is 43. Lesson 42 brought one remark and one request (LD §5.32): marriage and age with someone met by
chance still felt out of place (a recurrence of lesson 40's, so the lesson is not settled), and «regnhlíf», reported hard to
say, could not be modelled. Load «light» a second time: two «light» ratings raise the target only with a small review backlog
(fewer due than half the review slots, LD §9 "Pace"). On the replay 47 items are due against about 64 slots, so lesson 43 stays
at 9 (lesson 42 was already lowered from 10 to 9 by 53 due).
1. **Conversational contexts (#427).** **In review (#458, a data PR):** small talk 4 is a coffee with Anna, the friend made at
   the guesthouse, by its own scene line; her birthday leads to the age and her remark on your ring to marriage. Accepted on the
   whole progression, partial plays included. **Next:** a catch line that opens on a reply to something not heard («Frábært. En
   pósthúsið?», lesson 42).
2. **Practice allocation after #442 (#439).** «Ertu með regnhlíf?» 9 model answers, «Ég er sein/seinn.» 5 + 5, with load «light»
   twice. **Next:** read lessons 41 and 42 together on the replay from current main, and adjust allocation per item before any
   global weight. The second behaviour PR before lesson 43 (§9 "The change rate"; #459 is the first).
3. **Today's new expressions in the main exchange (#327).** Lesson 42: 2 of 10 new items in the played scene, none said as a turn;
   the replay from current main reads 0, 3, 1, 0, 0, 2 in lessons 42–47, against the criterion of two. **Next:** find, lesson by
   lesson, whether the theme picked or the material picked misses it; scene data alongside (taxi and bus, the town's further levels).

**Alongside:** a word asked for is always modelled (#457: **built, #459**; «vatnsglas» and «versla» had been dropped the same
way). Larger numbers for prices heard (#451), and the listening pool's variety (#339) with it. Waiting: the learner's own name
and age (#428), Icelandic instructions (#429; a small pilot after the items above), two units of one scene back to back (#273;
its longest stretch without a scene was 4.4 minutes in lesson 42), «Mér finnst gaman að hringja heim» and its meaning (#209).
The 15- against 30-minute comparison waits for the second learner's state.

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
- **After lesson 42:** a word asked for always modelled (#459); in review: small talk 4 as a coffee with a friend, a level's own scene line (#458).
- **After lesson 41:** the voiced-reply guide once a lesson (#440); practice shared across a pattern and the fillers taught with it (#442); a «sooner» report keeps its reason, hard to hear gets listening support (#447, site_update_notifier#187); the goal says the lines the exchange asks (#448); «Takk og bless!» gives «og» a sentence (#450); «Sjáumst {time}!» judged sentence by sentence (#449); the ll/nn note corrected (#446); a listening task with nothing to frame it opens with «Listen.» (#455); the change rate and the end of the fix-up phase (owner decision, #456); `transitions.py` (#281: #453, #454).
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
