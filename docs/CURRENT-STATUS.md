# Current status (the short brief)

This file is the one home of "Now": what we work on next, in order, and what is open after it. It holds the current
state only. Rewrite it when the state changes: an item leaves "Now" when the PR that builds it merges, a dated record (what
was built, what was closed) moves to `docs/history/status.md` (LD §10 "Documents"), and "Now" is re-ranked after every
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
   in Icelandic, with no remark. **Built, step 9 (#588):** «Úr orðum sem þú kannt.» for «Made of words you know.» and «Samtalið aftur. Þú kannt
   þínar setningar. Segðu þær þegar þú átt að tala.» for a known conversation's «The conversation again. You know your lines: say them when it's
   your turn.», taught in lessons 74 and 75 on the replay of lesson 67's export. Lesson 67 (LLA `590081e`) taught «Segðu hverja setningu.» and
   said 131 instructor lines in Icelandic; its remark asked for the line's literal words, 'say each sentence' (#601). **Built, step 10 (#600):** a pick-out's need, «Hvað tekur þetta langan tíma? Hlustaðu og segðu það.» and «Hvað kostar þetta? Hlustaðu og
   segðu það.», each the question the learner asks for that information, then «listen and say it»; **step 11 (#611):** the other needs, «Hvaða
   númer?», «Klukkan hvað?» and «Hvað er hitinn?» with the same ending. Lesson 68 (LLA `34c46e7`) taught «Æfingunni er lokið.» and said 125
   instructor lines in Icelandic; on the replay of its export the phrases already authored are taught in lessons 69–80. **This round (step 12,
   #620):** a hinted cue's «It starts with:», the most frequent English instruction left (46 in lessons 68–75, every lesson), said as «Fyrsta
   orðið er:» ('the first word is:', words the learner has; «er» for the ear, the owner) after what to say and before the first word; taught in lesson 81, and «It starts with:»
   is gone from lesson 83. **Then (step 13):** the next most frequent English lines on the next export's replay; on lesson 68's, «Here you would
   say:» (13), «Now listen again.» and «Now answer.» (8 each).
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

**This round:** after lesson 68, one behaviour PR, the long run's step 12 (#620), and one data PR for the remark: the review question «Now
say…» has an answer with no «nú». An instruction's cue quoted the English line it replaces (#583), and 13 of the 27 instruction phrases say
other words; lesson 67 remarked the same phrase, and #601's aside said its words once while the cue kept asking for the line. #621 gives each
instruction's cue its own words (`meaning-gloss`).

## Now (updated 2026-11-26, after lesson 68), in order

The remarks' half of each round (LD §9 "Governance"): each remark ranked by how often its cause recurs on the replay of the latest export and
what a fix costs. The latest export is lesson 68's; the next lesson is 69. Lessons 56–68 were rated «right».
1. **An instruction asked by words it does not say (`meaning-gloss`, lessons 67 and 68).** «Segðu hverja setningu.» was asked as «the
   instruction "Now say each one"», and the learner looked for «nú». **Built (#621, data):** 13 instruction cues give the phrase's own words
   («the instruction "Say each sentence"», «… "How much does this cost? Listen and say it"»), still named an instruction; on the replay of
   lesson 68's export 2–7 such cues a lesson; the English lines they replace say the same words («Say each sentence.», «The exercise is
   over.», the owner: a line and its gloss that differ are not left standing). **Next:** read the next three feedbacks for a cue whose words the answer lacks.
2. **The catch task in an urgent scene, and a caught word never practised (#599, lesson 67).** **Built (#603, #604):** an urgent level gives
   no line to a catch task, and «Mér er illt í fætinum.» is a line the learner says; lesson 68 taught it, and marked it «sooner». **Next:** its
   next-day recall, and the accident's second level when it plays.
3. **New material tied to its scene (#579, #327, H4, H5).** Lesson 68 played the daily level with 4 of its 6 new items inside it. On the replay of
   lesson 68's export the played level holds new items to lesson 76 and none from lesson 77, when the ranked levels run out. **Next:** #327's
   next batch (the taxi, daily life) before lesson 77.
4. **Two «sooner» items failed the next day (lesson 67).** «Hvar er sendiráðið?» and «Ég er með sjúkratryggingu.» were marked «sooner» and not
   recalled; both are hard items with no connection to practise them through (#326's row). **Next:** their recall at the next ask, before adding
   practice.

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
lesson after lesson (#579). The owner chose to play the C4 scenes once their lines are taught (#592). **Next:** the next batch from
the next export (a taxi, daily life).

**Refactoring alongside (#281), behaviour unchanged:** one place for "which sentence holds this part", one for "can the
learner say this line", then the planner's build loop. Each step leaves every lesson `tools/same_lessons.py` builds
identical; the owner's replays of the lesson-21–23 exports, byte-identical, stay the check on the real learner path.
Built: `docs/DESIGN.md`'s invariants are one line per topic (#320) and the word regex and `norm_utterance` are
defined once (`audiolesson/text.py`, #321).

## Open issues after "Now", in order
- **The reading deck has had no outside review.** Another learner: its cards ask to read words no lesson has taught, and
  a hint such as «allt は例外的に「アルト」» sounded wrong to them. The corner became «読んでみよう», read without a rating
  (site_update_notifier#165). The main learner, after lesson 65: «vatn» as «ヴァフトン» seemed wrong (a breath before «t»
  and a voiceless «n», which katakana cannot write without adding vowels). The owner's choice (#586): a word with a sound
  katakana cannot write has its hint in IPA, with what the kana cannot say in Japanese after it («vatn» [vaʰtn̥]（ヴァの
  後に短い息を出し、母音を挟まず t から声を出さない n へ移る）); 26 of the 91 cards, and `validate` fails on a kana-only hint of
  such a word. An outside check corrected notes that added vowels or a second r and the devoiced l of Gullfoss and
  Hallgrímskirkja; its open questions (the r of rn, compound names, final devoicing) wait on #586 for a fluent reviewer (#209).
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

## Where to look
- **What was built or closed before, with the condition that reopens each closed issue:** `docs/history/status.md`.
- **Built, and how many feedbacks it has had:** the table under "Built, waiting for three feedbacks without the same remark"
  in LD §8.
- **Rows read instead of remarks:** LD §8, below the table, and `tools/replay_lesson.py` (the daily read).
- **Open gaps:** LD §7 (the "now" column).
- **The long run, step by step:** LD §8.
- **Decisions already made:** LD §9. Do not reopen without new evidence.
