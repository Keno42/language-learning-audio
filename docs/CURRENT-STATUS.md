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
1. **Instructions in Icelandic (#429, O2, H8).** The learner's choice, asked once by the bot around the tenth lesson: replace them gradually, or not
   at all (owner, 2026-11-14; #543, `generate --instructions`). The pilot of two commands, «Endurtaktu.» (repeat) and «Hlustaðu.» (listen), is built
   (#507): taught as material, said in an Icelandic voice with the English after them. The English follows it in the lesson that teaches it and the next, and is gone from the third (owner, after lesson 56: «no complaint should be treated as understood», and feedback comes only after a lesson; #542), where it waited for two recalls in the written review.
   Lessons 52 and 53 taught them; each was recalled the next day. Lesson 54 taught none, and the learner wrote that the instructions did not
   increase: waiting for the fade held the item still. **Built (#524):** «Hægt.» for «Slowly.» and «Hlustaðu aftur.» for a
   pick-out's «Listen again.», one a lesson, with no wait for the fade; lesson 55 taught «Hægt.» and said it before «Slowly.» in five
   slow models, with no remark. Lesson 57 taught none: the four authored phrases were all taught in lessons 52–56, and the learner wrote that
   without one a lesson the switch will not progress (LD §5.47). **Built, step 1 (#546):** the next four, in order of how often a lesson
   says them: «Og á eðlilegum hraða.» (And at natural speed.), «Svarið:» (The answer:), «Aftur að tala.» (Back to speaking.) and «Samtalinu
   er lokið.» (That's the end of the conversation.); lesson 58 taught the first and said it 11 times, 29 instructor lines in Icelandic in all,
   with no remark (LD §5.48). **Built, step 2 (#551):** a taught instruction inside a longer English line said as a line of its own («Let's
   build it up from the end.» «Endurtaktu.»); lesson 59 left no «Listen, then repeat.» or «Repeat each part.» (LD §5.49). **Built, step 3
   (#554, #555):** «Nú kemur stutt samtal.» for a conversation's opening, taught after «Aftur að tala.» and «Samtalinu er lokið.» (lesson 62 on the
   replay of lesson 59's export); the authored phrases then run out. **Built, step 4 (#557):** a cue's frame, «Segðu:» for «Say:» and «In
   Icelandic, say:» and «Hvernig segir maður:» for «How do you say:», said between the cue's lead and what to say, which stays in the
   learner's language. **Built, step 5 (#560):** «Kláraðu setninguna:» for a cloze's «Complete the sentence to say:» (5–13 a lesson) and
   «Eitthvað nýtt.» for «Something new.» (2–6); from lesson 67 on the replay of lesson 60's export about 111 instructor lines a lesson are in
   Icelandic (90 without them). Lesson 62 was the first built with both (LLA `f5dc903`), and taught «Nú kemur stutt samtal.». **Built, step 6 (#572):** the form work's own
   lines, «Segðu hverja setningu.» for «Now say each one.» and «Æfingunni er lokið.» for «That's the end of the form work.», said as «Samtalinu er
   lokið.» is. Lessons 63 and 64 (LLA `e01e55d`) taught «Segðu:» and «Hvernig segir maður:» and said 82 and 116 instructor lines in Icelandic,
   in a voice of their own since #575–#578 (OpenAI's realtime «cedar», #563). On the replay of lesson 64's export the frames of step 5 and the
   lines of step 6 come in lessons 65–68. **Built, step 7 (#580):** an aside's own lines, «Smá útúrdúr.» for «A quick aside.» and «Aftur að
   efninu.» for «Back to the lesson.», taught in lessons 69 and 70 on the replay of lesson 65's export; a milestone's lines stay in English.
   Lesson 65 (LLA `b4fdd66`) taught «Kláraðu setninguna:» and said 128 instructor lines in Icelandic. **Built, step 8 (#584):** a part's
   frame inside its sentence, «Þessi orð eru í setningunni:» («These words are in it:») and «Þetta orð er í setningunni:» («This word is in it:»),
   and a build-up's lead, «Byrjum á endanum.» («Let's build it up from the end.»), taught in lessons 71–73 on the replay of lesson 66's export.
   Lesson 66 (LLA `f268aba`) taught «Eitthvað nýtt.», asked it by name («The instruction "Something new".», #583) and said 137 instructor lines
   in Icelandic, with no remark. **This round (step 9, #588):** «Úr orðum sem þú kannt.» for «Made of words you know.» (15 in lessons 66–73) and
   «Samtalið aftur. Þú kannt þínar setningar.» for a known conversation's «The conversation again. You know your lines: say them when it's your
   turn.» (14), taught in lessons 74 and 75; neither English line is said from lesson 77. **Then (step 10):** the next most frequent English
   lines on the next export's replay; on lesson 66's, «Your turn.» (14) and «Put it together yourself.» (12).
2. **Forms as choices (#528, owner 2026-11-12).** «New material should not be more numbers, colours and words to memorise; I want to feel a
   coach who makes me choose the right case and the right verb form.» The course itself is one-sided: of 256 sentences that open with a
   subject pronoun, 207 say «ég»; «vilja», «þurfa» and «eiga» exist in one form; the learner has two forms of three nouns. **Built, step 1 (#531):** the
   verb by its subject. Eight sentences the learner says («Ég fer á morgun.», «Ég þarf hjálp.», «Ég er í fríi.» …) are held with «við»,
   «hún» and «þú»; once a lesson, at about minute 14, one is said with two other subjects, the verb's form named, and each asked. **Built, step 3 (#535):**
   the lesson says what it trains. The goal after the opening ends on «Today's form work: One sentence you know, said of someone else.»,
   and the last question before the lesson's closing words asks one of the choice's sentences again, the one whose verb changes («Today's
   form work, once more.»). Lesson 55 played both («Ég kem í kvöld.» with «hún» and «þú»), and its remark asks for a word when the lesson
   goes back to the usual practice after the form work (LD §5.45; «Now» item 1). **Built, step 2 (#539):** the noun by its frame. A noun the
   learner has in two forms is said in the sentence of each, the case named («Hvar er bankinn?» / «Ég er að leita að bankanum.»), then each
   asked; on the replay of lesson 55's export it plays in lessons 56–58 (the bank, fish, the hotel: the three nouns the learner has in two
   forms). **Built, step 4 (#541):** a form the choice could set comes in as new material. A form not met, of another case than the forms
   the learner has of its noun, that a pattern they know takes («sundlauginni» for «Ég er að leita að {place}.»), is brought in one a
   lesson at the form weight, past the rule that holds a close variant back; the noun whose form is newest is set as the choice first. On
   the replay of lesson 55's export lessons 55–59 bring «eggjum», «flugvellinum», «sundlauginni», «safninu» and «stoppistöðinni», and the
   nouns the choice can set go from three to seven. Lessons 56 and 57 played all four steps without a remark on them. Lesson 58's remark asks why a sentence's case is what it is
   («Fluginu er seinkað.», «við sundlaugina»): the reason is said for frames and eight phrases only, and the noun choice played in neither
   lesson 57 nor 58 (#548, «Now» item 1). #528 is closed
   (2026-11-14). More nouns with a second form in a frame the learner has (#270's accusative orders against a nominative, «í» with a
   town, «á» with a day) come as data, each through #368's introduction and #541. It reopens on a remark that new material is words of a
   set again, or that a form choice is a drill with no scene.
3. **Numbers in varied situations (#451, owner 2026-11-09).** Numbers where a traveller meets them, sorted into eight kinds in #451
   (money, time, dates, counts and people, numbers as names, weather and roads, contacts and codes, about oneself), mostly by ear,
   rotated so no kind and no number word comes back within a few lessons. Merged: step 1 (#508), step 2, scenes for every kind
   (#509–#513), step 3, the rotation of the pick-outs and of what the learner says (#515, #516), and step 3d, the number an exchange's
   partner says (#520). **Built (#534):** every number a partner says in an exchange has two other values (16 turns of the hot-dog
   stand, the supermarket, the museum, the tour, the town, small talk, the clothes shop and the meeting; before, only the hotel desk and
   the bus), and a turn's number as written, heard in every earlier play, rests behind them. On the replay of lesson 54's export the
   exchanges heard again say thirteen number lines in six lessons, each with a value new to the learner (the museum's ticket «þrjú þúsund
   krónur», the friend «fjörutíu ára», the walk «svona fimmtán mínútur»; before, twelve lines, each the value as written), and no exchange
   says the same number line in two of the six. **#451's acceptance, restated for what a scene says:** no exchange's number line in two of
   five lessons (met), and no remark over three feedbacks that numbers repeat or come from one situation (lessons 53–55 had none; lesson 55
   played #534: the tour desk's booking number and the meeting's hour each with a value other than the written one).
   «No number word in more than two of five lessons» is dropped as a count: the reviews and the number choice say the forms of 1–4 by
   their own schedule, in every lesson. The issue is closed (owner, 2026-11-12); what reopens it is below.
4. **The learner's own details (#428)** in what they say about themselves, in place of fictional ones.
5. **The listening pool's variety (#339)** and **a fluent speaker's review of the most-heard exchanges (#209)**.

**This round:** after lesson 66, two behaviour PRs: the long run's step 9 (#588), and #579 step 2's first half, at most two new fillers of one
slot a lesson (#590), the answer to the cause that recurs most (lessons 60, 62–66). Lesson 66 had no remark. Its second half, a waiting level's
lines kept for its lesson, is not built: on this learner's path the pharmacy and the accident never play, and on a 15-minute course it brought
back levels heard again lesson after lesson. The C4 lines (#579), the form's «sooner» menu (#585) and the reading deck's hints (#586) wait for
the owner's choice.

## Now (updated 2026-11-24, after lesson 66), in order

The remarks' half of each round (LD §9 "Governance"): each remark ranked by how often its cause recurs on the replay of the latest export and
what a fix costs. The latest export is lesson 66's; the next lesson is 67. Lessons 56–66 were rated «right».
1. **New material tied to its scene (#579, H4, H5; the owner's choice).** Lessons 65 and 66 taught ten and nine new items, none of them in the
   scene they played; eight and six are illness and emergency lines of the pharmacy and the accident (C4), which this learner's path never plays.
   The one «sooner» mark of lesson 66 is among them. **Built (#590):** at most two new fillers of one slot a lesson. **Next:** the owner's choice
   on #579; recommended, an unranked theme's level plays when the course order brings its lines, as a ranked one does (#365).
2. **A review item the form cannot mark (#585, lesson 65).** No remark after lesson 66. **Next:** the owner's choice; recommended, one option
   more, «その他（表現を入力）», matched against the lesson's items (one bot PR).
3. **The instruction voice's takes (#563, lesson 64).** No remark after lessons 65 and 66. **Next:** the owner's choice; recommended, a retake
   list the owner fills by ear.
4. **Three feedbacks without a remark** on similar lines apart (#590, from lesson 67), on an instruction's cue (#583: lesson 66 the first), on
   the form work's lines in Icelandic (#572, lessons 67 and 68 on the replay) and on an aside's (#580, lessons 69 and 70). A pick-out turn that
   gives its last value again when the next does not fit the time left (#589) takes a behaviour place in a later round, once its two repeats on
   the replay are read.

**Alongside:** practice by what is hard in an item (#518, #439, G11): lesson 60's two heavy-dose items were hesitated and not recalled, lesson 59's 2 of 7 recalled; the dose alone does not hold them, and #579 reads it with the pace. A conversation once (#519): lessons 54–61 had four to eight conversations and no remark on their number, eight feedbacks. Hard to hear (#447): «Ég missti af strætó.» and «Hafið þið laust herbergi?», reported after lesson 59, were not recalled the next day and recalled at their next ask. The listening pool's sameness (#339): none of lesson 56's, 57's or 58's pick-outs was on a line heard in the three lessons before (0 of 8, 0 of 6, 0 of 6; lesson 55: 3 of 4). On the replay of lesson 58's export it comes back in lesson 70, when few lines are left that were not heard lately: 12 of 19 pick-outs; 6 of 16 with the batch after lesson 58; at most 1 when C4's four levels play as well. The town names as dative fillers, left unfitted in lessons 53–55, were fitted in 56 and 57. The same exchange heard lesson after lesson (#483): the other learner's next feedback, and the learner's own line that varies in use («Áttu {item}?», #336). Long parts that do not stick (#469's family): read the next-day recall of «við hliðina á bankanum» and «hinum megin við götuna»
before adding practice. Scene coherence (#327): lesson 50 said four of its six new items as turns of the played exchange, lesson 51 none of its
ten (its exchange was a level played again). The note's pieces (#481) have not played yet. A silent clip taken as cut off (#503) is built; «vettlinga», whose syllable «lin» it was found on, has not played since.

**Longer term:** the long run above holds the order; what is not in it waits there as an issue. Remaining after its five: understanding a partner's prompt, not only saying the reply (#327, #265, #464); expressions usable in exchanges (#327, #265); winter and safety scenes (#142), as one bounded batch.

**The long run alongside:** #327, one scene at a time for the new material the path brings, each a data PR of authored
Icelandic (candidates until native-checked). The town (asking the way), small talk (getting to know someone) and the
clothes shop (what you need, the price, trying it on) are written: on the replay of the lesson-30 export the day's new
lines are said in the played exchange in lessons 30–35 (17; before the town, 0 in nine lessons). The goal of the played
level is said after the opening, and the closing ends on the level's lines in the order of its turns. The town has a third
level for the way itself, and small talk a third and fourth; the batch for lessons 41–50 (#432) added arranging to meet and
the weather, and more levels for the town, small talk and the clothes shop (item 3). #451 step 2 added the bus, the hotel desk and the
weather's second and third levels (#511, #512). **The batch after lesson 58:** on the replay of its export the learner had three levels
left (lessons 59–61), and from lesson 62 the lesson's exchange was one already played (the supermarket's third level in 18 of the lessons
62–96). Written: the hotel's levels 3–6 (a room for a night, breakfast and Wi-Fi, a lost key and a cold room, the last morning), a missed
bus (the town's sixth), the path's ice and early dark (the tour's sixth, with #142's lines), the family (small talk's sixth and seventh),
and two themes of Tier C's emergency basics, the pharmacy and an accident, played for a learner whose trip profile boosts C4. A new level
plays in every lesson to 69 (to 73 with C4 boosted). The day's new items are turns of it in two to four of those lessons only: what a
later level wants is taught before its lesson, as the rest of a day's pace. On the replay of lesson 66's export the ranked levels run out
after lesson 69, and the pharmacy and the accident (C4) never play on this path. A waiting level's items kept for its lesson was built and
checked (lesson 66) and is not merged: it reached only small talk's seventh level, and on a 15-minute course it brought back levels heard again
lesson after lesson (#579). **Next:** the owner's choice on #579 for the C4 scenes, and the next batch from the next export (a taxi, daily life).

**Refactoring alongside (#281), behaviour unchanged:** one place for "which sentence holds this part", one for "can the
learner say this line", then the planner's build loop. Each step leaves every lesson `tools/same_lessons.py` builds
identical; the owner's replays of the lesson-21–23 exports, byte-identical, stay the check on the real learner path.
Built: `docs/DESIGN.md`'s invariants are one line per topic (#320) and the word regex and `norm_utterance` are
defined once (`audiolesson/text.py`, #321).

## Built since the last update (2026-10-15)

Each waits for its first feedback in the LD §8 table.
- **After lesson 66:** the long run: a use of known words and a known conversation's opening in Icelandic (#429 step 9: #588); at most two new fillers of one slot a lesson (#579 step 2: #590).
- **After lesson 65:** the long run: a part's frame and a build-up's lead in Icelandic (#429 step 8: #584); data: an instruction asked by name (#583). Lesson 66 played #583 (LD §5.55).
- **After lessons 63 and 64:** the long run: an aside's own lines in Icelandic (#429 step 7: #580); the pace counts the next-day outcome (#579: #582, the owner's). Lesson 65 played #582 (LD §5.54).
- **After lesson 62:** the long run: the form work's own lines in Icelandic (#429 step 6: #572); the form work opens with a line of its own, checked over every block (#573); the instructions in a voice of their own, OpenAI's realtime «cedar» in a plain tone (#563: #575–#578, the owner's). Lessons 63 and 64 played them (LD §5.53).
- **After lesson 61:** fixed dialogues played whole when known, retired after one whole play (#567); a pattern's sentence asked when the learner says its pattern and fills (#265: #570); data: the second native check (#209: #566), the pharmacy's «Ertu með eitthvað við höfuðverk?» (#568). Lesson 62 played #567 and #570 (LD §5.52).
- **After lesson 60:** the long run: a cloze's and a new item's frame in Icelandic, «Kláraðu setninguna:» and «Eitthvað nýtt.» (#429 step 5: #560); a cue names its answer's subject, checked by `validate` (#427: #559, data).
- **After lesson 59:** the long run: a cue's frame in Icelandic, «Segðu:» and «Hvernig segir maður:» (#429 step 4: #557).
- **After lesson 58:** the long run: a taught instruction inside a longer English line (#429 step 2: #551), a conversation's opening (#429
  step 3: #554, #555); the form work at times of its own and the authored contrasts, no grammatical term (#548: #550, #552); three doses for a
  new item (#518: #529); the tests on every core (#553, behaviour unchanged); data: the scenes after lesson 58 (#327: #556).
- **After lesson 57:** the long run: the next instructions in Icelandic, one a lesson again (#429 step 1: #546); data: six dative place forms
  glossed by their case, «the airport (dative)» (#544: #547).
- **After lesson 56:** an instruction's English only in the lesson that teaches it and the next (#429: #542); the instructions in
  Icelandic the learner's choice, asked once by the bot (#429: #543, site_update_notifier#224).
- **After lesson 55:** the way back after the form work (#538); the long run: the noun by its frame (#528 step 2: #539), a form the choice
  could set as new material (#528 step 4: #541).
- **After lesson 54:** a new phrase made of words the learner says is asked as a use of them (#518: #523); the long run: «Hægt.» and «Hlustaðu aftur.» taught as instructions (#429: #524); a new noun's form named against its basic word (#439 step 3: #527); the pace counts the due items a lesson can ask, and a rise reads whether the last lesson's reviews fitted (#526, #530); the verb by its subject, named in the lesson's goal and asked once more in its closing (#528 steps 1 and 3: #531, #535); every number a partner says in an exchange has other values, the old one resting behind them (#451: #534).
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
  «読んでみよう», read without a rating (site_update_notifier#165). The main learner, after lesson 65: «vatn» as «ヴァフトン» seems wrong (a breath
  before «t» and a voiceless «n», which katakana cannot write). #586 holds the options; recommended, no kana hint where katakana cannot write
  the sound, and a reviewer for the rest, as for the scenes.
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
- #209: the packet for a fluent speaker is ready (`tools/export_scene_review.py --scenario A2 --out review-A2.json`: one scenario's cards
  with their situation, partner line, replies and items, corrected by card and field). A first native check (the owner, 2026-11-12) read 22
  of the learner's lines and marked 12 wrong or not what is said: each is corrected, or retired where a correct line already exists. What is
  left needs a person (G10): the review of the rest, starting from the lines the lessons say most (`tools/top_lines.py` on the exported
  scripts). Every scene added since lesson 30 adds authored Icelandic to it.

#326 holds the connections across lessons. The frames a noun takes its other forms in (#270's remainder) come as data, each form through
#368's introduction and #541 (#528, closed below).

**Closed on 2026-11-14:**
- #528 (forms as choices): its four steps are built (#531, #539, #535, #541). Reopens on a remark that new material is words of a set
  again, or that a form choice is a drill with no scene.
- site_update_notifier#179 (a support request apart from the review): its first step is built (support requests, the «sooner» reasons;
  #187). The owner wants the form simpler, not more kinds. Reopens on a remark that asking for help changed an expression's schedule, or
  that the help did not come.

**Closed on 2026-11-12, each with the condition that reopens it** (their steps are merged; the owner asked for the list of open issues
to come down):
- #416 (one ask / voice / hear policy for conversations played again): built by #422, #430, #431 and #519. Reopens on a remark that a
  known conversation or reply is asked again (the family known-repeat).
- #427 (lesson 40's contexts and cue–answer mismatches): built by #433, #458, #471, #472, #475 and #519's opening rule. Reopens on a
  remark that a line answers nothing or a cue does not match its answer; the native check stays with #209.
- #273 (no fifteen minutes without a scene): the daily read's row stands at 4.2–4.4 minutes on the replays of lessons 53 and 54.
  Reopens if the row passes about 5 minutes.
- #439 (practice by what is hard in an item, not its kind): its steps are built (plain numbers #492, #502; the forms of 1–4 as a choice
  #493, #495, #498; a gendered word of him and of her #499; a long word split #496; a new phrase's noun named against its basic word
  #527). What it began goes on in #518 (the dose) and #528 (forms as choices). Reopens if neither holds a remark of the family
  easy-substitution or form-why.
- #265 (expression first, the umbrella): one rule decides every learner line (#263), a part is introduced inside its expression (#262),
  and the pace's unit is weighted components (#218). Reopens on a part introduced or asked before an expression that holds it, or a
  line the learner can say withheld.
- #483 (a level heard again with no rest; another learner): built by #486 and #487. Their lessons 29 and 30 since were rated «light»
  with no remark. Reopens on a remark from either learner that the same exchange comes lesson after lesson.
- #270 (a known word in a new form, the umbrella): the dative place forms and the naming of a form against its basic word are built
  (#368, #527), and the noun is set in the frames of its forms as a choice (#539, #541). The frames left (accusative orders, `dat_town`,
  `dat_hobby`) come as data. Reopens if a frame's form comes with no word on its case.
- #451 (numbers where a traveller meets them): its steps are merged (#508–#513, #515, #516, #520, #534). Reopens on a remark that
  numbers repeat or come from one situation.
- #209 (a packet for a fluent speaker): the tool is built (#532). The review itself needs a person; when one is available, a new issue
  takes the corrections.

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
