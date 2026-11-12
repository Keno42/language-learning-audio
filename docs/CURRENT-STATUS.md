# Current status (the short brief)

This file is the one home of "Now": what we work on next, in order, and what was built since the last update. Rewrite
it when the state changes: an item leaves "Now" when the PR that builds it merges, and "Now" is re-ranked after every
round of learner feedback (`docs/LEARNING-DESIGN.md` (LD) §1). The owner approves a re-ranking by merging the PR that
makes it. Everything else is in LD: the long run and the table of built changes waiting for feedback (§8), the gaps
(§7), the hypotheses with their status (§4), the evidence lesson by lesson (§5). The learning policy is in
`docs/CURRENT-POLICY.md`.

## The long run: one step every round

What the project is for is the learner's accomplishment over the long run (LD §9 "Governance", owner 2026-11-09): their time is limited,
and a lesson that only answers yesterday's remarks spends it on how lessons feel, not on what they will be able to do. Every round builds
one step of the long run, whatever the remarks say; only the owner waives it, with a reason, in the ledger (`long_run_waived`).
`tests/test_docs.py` fails from lesson 53 on a round that names neither its long-run PR nor a waiver, or on more than seven lessons
in a row without one. Lessons 35–51 built none; lesson 52 was the first built with long-run PRs (#507, #508, #511, #512).

In order:
1. **Instructions in Icelandic (#429, O2, H8).** The pilot of two commands, «Endurtaktu.» (repeat) and «Hlustaðu.» (listen), is built
   (#507): taught as material, said in an Icelandic voice with the English after them, the English faded as the review recalls each twice.
   Lessons 52 and 53 taught them; each was recalled the next day. Lesson 54 taught none, and the learner wrote that the instructions did not
   increase: waiting for the fade held the item still. **This round's step (#524):** «Hægt.» for «Slowly.» and «Hlustaðu aftur.» for a
   pick-out's «Listen again.», one a lesson, with no wait for the fade. **Next:** «And at natural speed.», «The answer:», «Back to
   speaking.» and the catch's «Now listen again.», once these two have had their feedback.
2. **Numbers in varied situations (#451, owner 2026-11-09).** Numbers where a traveller meets them, sorted into eight kinds in #451
   (money, time, dates, counts and people, numbers as names, weather and roads, contacts and codes, about oneself), mostly by ear,
   rotated so no kind and no number word comes back within a few lessons. Merged: step 1 (#508), step 2, scenes for every kind
   (#509–#513), step 3, the rotation of the pick-outs and of what the learner says (#515, #516), and step 3d, the number an exchange's
   partner says, with other rooms, hours, codes and fares for the hotel desk and the bus (#520). Lesson 54 asked «Það eru mínus ellefu
   gráður.»; #520 has not played (the museum's lines have one value). **Next:** variants for the 18 other partner turns whose exchange
   says one value (data, scene by scene), and #451's acceptance restated for what a scene says: «no number word in more than two of five
   lessons» counts the reviews and the number choice too, and is not met.
3. **The learner's own details (#428)** in what they say about themselves, in place of fictional ones.
4. **The listening pool's variety (#339)** and **a fluent speaker's review of the most-heard exchanges (#209)**.

**This round:** #429's second step (#524), above. On the replay of lesson 54's export the next lesson teaches «Hægt.» and the one after
«Hlustaðu aftur.», each said four times or more with its English after it.

## Now (updated 2026-11-12, after lesson 54), in order

The remarks' half of each round (LD §9 "Governance"): each remark ranked by how often its cause recurs on the replay of the latest export and
what a fix costs. The latest export is lesson 54's; the next lesson is 55. Lesson 54 was rated «light», fitted 54 of the 56 due items it
could ask, played four conversations without a remark (#519), and drew two remarks: the practice of «two adults and two children» is too
thick, and the instructions in Icelandic did not increase (LD §5.44). The learner also asked what case «á mánudaginn» is.
1. **Practice by what is hard in an item, not its kind (#439, #518, G11, H11).** The remark of lessons 41, 44, 49, 51 and 54, and the
   owner's on #516. Built this round (#523): a new phrase made of words the learner says is asked as a use of them, once more after a gap,
   in its scene and in the closing (the tickets sentence six times, not nine). It reaches two of the fourteen new phrases of lessons 54–58; a short
   one with one new word («Er þetta ull?») is still said nine times. **Next, two steps:** (a) #439 step 3, a new noun met in a form
   other than its nominative gets a word on its form: lesson 52's «nafninu» and «bókun» failed in the review, and lesson 54's question
   is on «mánudaginn»; (b) the rest of #518, a dose for every new item, which waits for the owner's three decisions.
2. **The pace cannot rise while the reviews fit (H9).** Lesson 54 was «light» at a target of 7. Built (#526): the backlog counts the due
   items a lesson can ask (lesson 54: 56, not 72), and each unfitted item once. It would not have changed lesson 54: the target fell
   by lesson 53's unfitted reviews (20 of 45), rightly. What holds it at 7 is the rise's «small backlog», due items under half the
   review slots: on the replay 43–56 are due each day against 82 slots, and every lesson fits them. **Next:** the owner's call on
   whether a rise reads «the last lesson's due reviews fitted» in its place (LD §9 "Pace").
3. **The listening pool's sameness (#339).** All four of lesson 54's pick-outs were on a line heard in the three lessons before. On the
   replay lesson 56 has 14 pick-outs after its target. **Next:** a pick-out rotates by line, a line heard recently is left for another,
   and a lesson's pick-outs have a ceiling.
4. **Hard to hear (#447).** The listening support played in lesson 54 for «Aðeins eitt, takk.» and «buxur», not for «trefil» or «Hvenær er
   útritun?», which was hesitated in the review. **Next:** read why two of the four had none; the slow model, word by word, still takes
   out the linking of «Aðeins eitt» the learner asked about.

**Alongside:** a conversation once (#519): lesson 54 had four conversations in 2.8 minutes and no remark; two more feedbacks to read. Two due items no lesson fits: the town names as dative fillers (`reykjavik_dat`, `akureyri_dat`), left in lessons 53 and 54. The same exchange heard lesson after lesson (#483): the other learner's next feedback, and the learner's own line that varies in use («Áttu {item}?», #336). Long parts that do not stick (#469's family): read the next-day recall of «við hliðina á bankanum» and «hinum megin við götuna»
before adding practice. Scene coherence (#327): lesson 50 said four of its six new items as turns of the played exchange, lesson 51 none of its
ten (its exchange was a level played again). The note's pieces (#481) have not played yet. A silent clip taken as cut off (#503) is built; «vettlinga», whose syllable «lin» it was found on, has not played since.

**Longer term:** the long run above holds the order; what is not in it waits there as an issue. Remaining after its four: understanding a partner's prompt, not only saying the reply (#327, #265, #464); expressions usable in exchanges (#327, #265); winter and safety scenes (#142), as one bounded batch.

**The long run alongside:** #327, one scene at a time for the new material the path brings, each a data PR of authored
Icelandic (candidates until native-checked). The town (asking the way), small talk (getting to know someone) and the
clothes shop (what you need, the price, trying it on) are written: on the replay of the lesson-30 export the day's new
lines are said in the played exchange in lessons 30–35 (17; before the town, 0 in nine lessons). The goal of the played
level is said after the opening, and the closing ends on the level's lines in the order of its turns. The town has a third
level for the way itself, and small talk a third and fourth; the batch for lessons 41–50 (#432) added arranging to meet and
the weather, and more levels for the town, small talk and the clothes shop (item 3). #451 step 2 added the bus, the hotel desk and the
weather's second and third levels (#511, #512). Next: a taxi.

**Refactoring alongside (#281), behaviour unchanged:** one place for "which sentence holds this part", one for "can the
learner say this line", then the planner's build loop. Each step leaves every lesson `tools/same_lessons.py` builds
identical; the owner's replays of the lesson-21–23 exports, byte-identical, stay the check on the real learner path.
Built: `docs/DESIGN.md`'s invariants are one line per topic (#320) and the word regex and `norm_utterance` are
defined once (`audiolesson/text.py`, #321).

## Built since the last update (2026-10-15)

Each waits for its first feedback in the LD §8 table.
- **After lesson 54:** a new phrase made of words the learner says is asked as a use of them (#518: #523); the long run: «Hægt.» and «Hlustaðu aftur.» taught as instructions (#429: #524).
- **After lesson 53:** a fixed dialogue retires after two whole plays, and a hard item's scene line is cut once a level, never from the lesson's own (#519); the long run: the number a scene's exchange says rotates, with other rooms, hours, codes and fares (#451 step 3d: #520).
- **Before lesson 53, the long run:** #451 step 3, a number word rests between lessons in the pick-outs, the number choice takes its lines in turn, a scene's number carries a form of 1–4 (#515); a number line the learner says is practised over its values (#516).
- **Before lesson 52, the long run:** «Endurtaktu.» and «Hlustaðu.» in Icelandic, the English faded by the review (#429: #507); #451's numbers, a plain number entering where it is used (#508), and scenes for every kind of number: money and time by ear (#509), hot dogs for a group and family tickets (#510), a hotel desk and a bus (#511), a temperature said whole, the wind and the road (#512), a tour desk and the guide's phone number (#513).
- **After lesson 51:** a situation's instruction names what its answer names, checked by `validate` (#500); «Sjáumst í dag!» never generated (#501); a plain number made only of known words asked as a use of them (#502); a silent clip counts as cut off whatever its words (#503); lesson 52 as drafted: price answers framed as question and answer, a weather opener the reply agrees with, «small» in sentences (#506).
- **After lesson 50:** the number choice grows its feminine side, a line that adds a missing gender coming forward (#498); a gendered word said of him and of her (#499).
- **After lesson 49:** a slow model that plays a line by ear settles its listening support too (#490); a plain number introduced plainly, asked once more, never moved to new sentences (#492); the forms of 1–4 as a choice (#493), naming the case (#495); «Þetta reddast» with a full café (#494); a long word inside an item of two words split, «fyrr·a·mál·ið» (#496).
- **After lesson 48:** the lesson's goal said sentence by sentence, a beat between them (#488).
- **After lesson 47:** two different answers never share a cue meaning, written or spoken, in any language: `validate` checks it, and nine meanings are told apart (#484); the theme levels heard again take turns, the one heard longest ago first (#486); the supermarket asks about other things, with a third level for lamb (#487).
- **After lesson 46:** a grammar note's pieces led by what each group builds, each repeated, the whole at natural speed (#481).
- **After lesson 45:** the due reviews keep their time when they cannot fit (#478); «svona tíu mínútur» in pick-outs (#477); a part reported hard tried as its sentence, then built up from its end, and no two slow models in a row (#480).
- **After lesson 44:** a word reported hard to say first asked from its meaning, then broken down (#468); a part only its own sentence holds keeps its rungs, a long part built up from its end inside its sentence (#469); a cue that asks a person names them, checked by `validate` (#470); the café's fourth level asks for a cake without nuts (#471); a scene line's lead-in after the question it answers (#472); «Now another short conversation.» (#473); a part's generated sentence cued by its meaning (#474); the late call's own scene line (#475).
- **After lesson 43:** «Same change:» only right after the same transform (#463); a note bridging «komið hingað» to «verið hér» (#464); a cut-off clip synthesized again and not cached, the threshold per language (#466, #467).
- **After lesson 42:** a word asked for always modelled (#459); small talk 4 as a coffee with a friend, a level's own scene line (#458).
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
