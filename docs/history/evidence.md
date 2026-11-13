# Evidence of older lessons (archive of LEARNING-DESIGN §5)

This file holds §5.1–§5.38 (lessons 1–48), moved from `docs/LEARNING-DESIGN.md` §5 since 2026-10-15 with only their
references fixed. Older subsections move here as new ones are written (LEARNING-DESIGN §10 "Documents"), under their
own numbers, so a reference such as "§5.14" in any document finds it here. These are a dated record: a statement about what was built or open holds for its
lesson. Where things stand now is in LEARNING-DESIGN §4, §7 and §8.

### 5.1 Owner reviews of real lessons

| lesson | finding | led to |
|---|---|---|
| L3 | A grammar note named too many dimensions at once and closed with "back to the lesson" ("this *is* the lesson"). Long runs of isolated recall. | #34, #44 |
| L4 | `connect` produced «Ha?» → [English "and then"] → «Ég skil.»: two recalls, not a conversation. The same pair was replayed all lesson. | #48, #55 |
| L6 | The same prompts were replayed. «vegabréf» was drilled seven times as a bare word, with no frame to use it in. Asides were used up early. | #77–#87, #80 |
| L8 | Too many asides, some repeated. The voice's gender didn't match the gender in the English instruction. Numbers 1–4: masculine and neuter forms couldn't be told apart in the prompts. | One cap on all notes; #113 and the speaker-gender changes |
| L12 | Covered in §5.6. | #147, #148–#155 |

The early findings were mostly about form (prompts, pauses, coherence). From L6 on they are
about the shape of learning: words with no use, the same material every day, no context.

### 5.2 Report history (lessons 1–11)

- Reports exist for 8 of 11 lessons (3, 4, 6, 7, 8, 9, 10, 11).
- Lines marked not recalled, per lesson: L3 4, L4 4, L6 6, L7 3, and **none from L8 to L11**.
  By then the pace had dropped from 6 to 3–5. At the same time the bot started asking about
  every new item of the previous lesson before generating the next one. The data can't
  separate the two causes.
- **Longer phrases failed far more often.** Of the items introduced in L3–L7, 9 of 24 with
  three or more words failed at least once (fyrirgefðu, verði þér að góðu, gangi þér vel,
  eigðu góðan dag, hvað þýðir þetta?…). Of those with one or two words, 2 of 27 did. The
  numbers are small, but it is the clearest pattern in the data.
- **«迷った» (hesitated) has never been reported**: zero in the whole learner file. Since
  per-lesson outcomes were first stored (L8), every confirmed outcome is 言えた. A scale that
  only ever reads 言えた cannot tell easy from shaky (H10, §6.2).
- **New items per lesson are not the pace.** From L1 to L11 there were 8, 8, 14, 11, 11, 9,
  7, 9, 5, 6 and 8 new items, at paces of 6, 6, 6, 5, 6, 6, 5, 4, 3, 4 and 5. The extra arcs
  add up to half the pace again, and more when the fillers run out (H9, §7 G4).
- In L6 and L8, most of the due reviews did not fit into the lesson (34 of 42, 21 of 34).

### 5.3 The first feedback form (lesson 12)

- Load: "about right". Friction: "repetitive".
- Usable now: 2 of the 9 new items (Hvar er …?, safnið). Bring back sooner: none.
- The learner confirmed all four "same situation twice" candidates. All four were well-known
  review items: já, nei, Hvað kostar þetta?, Ekkert að þakka.
- Note: "I didn't hear «kaupa miða» nor «fara á safnið» during the lesson." Both were
  introduced in the first minute, practised three times within the first three minutes, and
  never came back, not even in the closing block. That was fixed in #147.
- **How the signal was misread.** The "same situation twice" candidate came from an
  automated audit (#130), and a lever to cap situation repeats had already been built on it
  (#141). When the learner confirmed the four candidates, that was read as a reason to turn
  the lever on. The owner then explained what was actually wrong: well-known items came back
  at all (§5.4), and the lesson had no context. Situations themselves are welcome. The lever
  was removed (#148). A candidate is a prompt for the learner's judgement, not a diagnosis
  of the cause (§6.2).

### 5.4 Recurrences: what simulation missed

- #94 found «Góðan daginn» in 30 of 30 simulated lessons, and PR #116 fixed it in
  simulation. In the real learner's path, with the trip ordering, real reports and later
  fillers, já, nei and hæ were still practised in every lesson from L1–L2 to L11. Their
  interval stayed at 7.2 days because early practice never moves the schedule. Replaying
  L12, they came 3–4 times each (#151).
- The same replay, after #147: each new item was practised in a burst of 5–8 recalls within
  five to eight minutes of its introduction. The next practice came 18–20 minutes later, in
  the closing block. Reviews came in urgency order, with no shared scene.

### 5.5 The GPT Voice pilots (#129)

- The repair phrases came out spontaneously.
- The most common clerk lines («Hvað má bjóða þér?», «Viltu poka?», «Viltu kvittun?») were
  not understood. That is the strongest evidence behind O2 and #134.
- The voice partner did not follow the script, turned into a teacher, and **produced
  transcripts that did not match what was said**. Nothing an LLM writes about a session
  counts as evidence.

### 5.6 What the requests after lesson 12 had in common

Within one day the owner raised several points:

- situation repeats shouldn't be capped;
- lessons lack context, and related items (já/nei, 1–5) aren't connected;
- «Sjáumst» should be extended with «á morgun»;
- já, nei and hæ keep coming back although reported 言えた;
- build patterns early (Má ég / Takk fyrir / Ég vil + fillings) to fill the time;
- only plausible scenes;
- numbers before languages the learner doesn't speak;
- no pause stretching;
- more trip scenes;
- colour words.

Answered one by one, they produced four issues and four PRs in a day, plus one in the bot. Read together, most
of them are one finding: **a lesson is assembled from an item count and an urgency queue,
not around anything the learner will do.** That is the gap behind H4 and #149. The
exceptions are content priorities (numbers, languages, colours, scenes) and two principles
(H7, and no pause stretching), which are recorded in §9.

### 5.7 The learner's answers (after lesson 12)

- **Why «迷った» is never used:** "Rather than hesitating to recall the right answer, I say
  'it's probably this!' without spending time, and I'm either right or wrong." The learner
  commits fast. The rating is binary in practice, and that suits an audio course whose
  answer pause is meant to be a natural one (O1). The scale works as designed; there is no
  "slow but right" category for this learner to report.
- **Short lesson or new material:** "Even somewhat new expressions: I want to get my ear used
  to them. In the end, language learning is time." With a caveat: long stretches of not
  understanding are hard. An occasional reminder that not everything has to be memorised
  would help. For example, when the previous review had many 言えなかった, say so in the
  lesson as reassurance.
- So spare time should become more to hear, not an early end. Hearing is meaning-focused
  input, the thinnest of the four strands (§4). It should come with a scene that carries
  the meaning (H8) and a word that full recall isn't expected (O5).

### 5.8 The first weekly read (lessons 7–12, the evening after lesson 12)

The first `/lesson-week` (site_update_notifier#59), read with §1's last checklist.

- **This week is the baseline.** No lesson in it was generated with #147, #148, #153, #154 or
  #157 (lesson 11 used language-learning-audio `f272343`, lesson 12 `8d8dfaa`). There is no
  prediction to check yet. The next reads compare with what follows.
- **Amount.** New items per lesson 7, 9, 5, 6, 8, 9, against paces 5, 4, 3, 4, 5, 6;
  lengths 28–31 minutes. The pace recovered from 3 to 6 over the week.
- **Next-day recall of new lines.** From lesson 9 on, every new item was answered: **19 of 19
  recalled** (lessons 9–11, five to eight new items each). In lesson 7 one new item failed
  (the other six have no stored answer), lesson 8 has no stored answers (per-item outcomes
  weren't stored before lesson 9), and lesson 12's await the next review. The report now
  tells these apart (site_update_notifier#62).
  - At five to eight new items, next-day recall is not what limits the learner: H9 shows no
    sign of overload. One of the two forms called the lesson light.
  - Two cautions. It may be a ceiling: the learner commits to an answer at once (§5.7), so
    the scale is lenient or the items are easy at this pace. And the pace had just been cut
    to 3–5 after the failures in lessons 3–7, so the items may be easier because there are
    fewer of them.
  - It doesn't say the pace should rise. The complaint is repetition and lack of context, not
    load (§5.3, §5.6). It does fit the learner's wish for more to hear (§5.7).
- **Long phrases.** Not recalled: 2 of 13 one-to-two-word items against 5 of 13 with three
  words or more. The earlier read (§5.2) counted every new item of lessons 3–7 and found 9 of
  24 against 2 of 27. The direction holds and the gap is smaller. All the failures are from
  lessons 3–7, the heavy early lessons (14, 11 and 11 new items), and there has been one
  since lesson 8, so phrase length and early load can't be told apart (G9). Too small to
  act on.
- **Scenario readiness.** Tier A, ten scenes: none ready, six practising, four untaught
  (café, public pool, essential signs, place names). Tier B, four scenes with cards: all
  untaught. Not alarming yet: the cards are shown three a day, a scene is ready only when
  every card was rated 言えた at its latest review, and most cards haven't been seen. The
  trip ordering began with lesson 12. This reading becomes informative after about two
  weeks (some thirty-five cards at three a day). If no scene is ready after three weeks,
  find out why.
- **Feedback.** Two forms: load "light" once and "about right" once; "repetitive" once; the
  note about two new items never heard (fixed in #147).
- **What the instrument couldn't show.** How often a well-known item came back, and how long
  a new item waited, were not in the report. It now has them (site_update_notifier#62). On
  the real lesson 12: isolated recall 64% of practice time, partner exchanges 10%; four
  reviewed items came back four times each (Allt gott, fimm, Góðan daginn, Takk); a new item
  (matseðilinn) waited 20 minutes between its early practice and the closing recall.

### 5.9 After the first lessons on the new version (reading cards, review length)

- **A reading card taught a rule with no example.** «Góða nótt · Sjáumst» stated the rule for
  *au*, but no listed word has one (the owner noticed it in the review). It was a data error
  that nothing could have caught: letters cards had no way to say which letters they teach.
  Fixed in language-learning-audio (split into ó and au cards; `validate` now checks that every
  rule has an example and every word a rule). Lesson for §11: a content check that only the
  learner can trigger is a missing check.
- **Review length (#133's "cards under three minutes").** The owner's estimate: the reading cards
  alone took under three minutes; the whole review took **six minutes or more**. Not timed
  (a felt duration), one day, and it includes scenario cards, which are spoken aloud. It is a
  lead for O5: about a fifth of the 30-minute lesson again, and the feedback must stay nearly
  effortless (§2). The bot doesn't record how long a review takes, so the next weekly reads
  can't say whether this is typical. Open question for the owner: is six minutes fine?

### 5.10 Lesson 13: the first lesson on the new version (replay of its export)

Lesson 13 was generated with bot `72be512` / LLA `9ef0933`, `--minutes 30`, no other lever, from
the trip profile. Figures are from the export's `script.json`, `plan.json` and
`learner.before.json`; the learner's remarks are from the feedback form.

- **The learner's words:** "the new expressions have no relation to each other, they are just
  lined up at random, so it is an Anki game." Also: the lesson was too short (about 24
  minutes); the failures of the last review got about one review each while every new
  expression, easy or hard, was repeated a great many times; «Hvenær?» came after
  «Hvenær leggjum við af stað?»; an English situation was given although the Icelandic
  question was already known; a line explained what the learner had just said. The form's
  "sooner" list named «Hvenær leggjum við af stað?», «hálka» and «matvörubúðin».
- **Length:** 1417 s = 23.6 minutes of the 30 requested (79%). `fit_max` is 1.0, so pauses only
  shrink, and nothing refills the lesson when the queue of useful items runs out (§5.7 asks for
  the time to go to hearing more).
- **Nine new items in five unrelated topics:** a shop, where one is from, asking the time,
  asking when one sets off, the weather and road ice. `pace` was 5 (§7, G4: the number of new
  items is not the pace). Each new item had 8–12 appearances and 77–199 s of the lesson.
- **Last review's failures had one or two:** the four items marked 言えなかった in lesson 12 got
  «kaupa miða» 2 appearances (21 s), «matseðilinn» 3 (25 s), «Get ég fengið …?» 4 (41 s) and
  «Má ég borga með korti?» 2 (24 s), against 8–12 appearances and 77–199 s for each new item.
  The same shape as lesson 12's "unheard" items, which had one early appearance each (§5.3).
  Practice follows the introduction and the stage ladder, not what the learner failed.
- **One scene text, said many times:** "Someone asks where you're from. Tell them you're from
  Japan." is narrated in at least seven exercises of the one lesson, and "You've said you're
  from Japan. Ask where she is from." in at least five. They are the authored `situation`
  texts of the items, played whenever the `situation` stage comes up. Neither is a lesson's
  theme; both stay English and in full however often they have been heard (the learner notes
  the same for the Icelandic question that is already known).
- **Sequencing:** «Hvenær?» is introduced at 597 s, the phrase «Hvenær leggjum við af stað?»
  at 303 s. The phrase's item has no `prereqs` entry for the word, though `hvenaer` is its
  first word. A data gap, not a planner choice.
- **Failures are forgotten after the next lesson (the learner's impression: "only the last
  review's 言えなかった come back").** In the model a confirmed failure sets the item back to
  tomorrow, with a lower ease (`learner.report`). From the next lesson on, every scheduled
  practice is *presumed* success again and the interval grows; nothing requires a confirmed
  recall before it does. Examples from `learner.before.json`: «Fyrirgefðu» failed in lessons 3
  and 4, and then had eight lessons of presumed success (17 successes, **0 confirmed recalls**),
  and is next due in eight days; «Hvað sagðirðu?» failed in 6 and 7 (18 successes, 1 confirmed
  recall); «Eigðu góðan dag.», «Gangi þér vel» and «Verði þér að góðu» failed in lessons 3–4 and
  have not been confirmed since either. None of the four appears in lesson 13. The Discord
  review asks about items due in its own queue and always the last lesson's new items, so an
  older failure is rarely asked again (G7). Confirmed evidence (§9, "Evidence") for these
  items is a failure and then silence.
- **What this says about H4:** the learner describes in their own words what the document
  calls G2: the lesson is a list of items, not an exchange they would have. It comes after a
  round of local fixes (§5.9) and the other remarks (allocation, scaffolds, order) have
  the same shape: each is a symptom of lessons built from items. It makes H4 the cause to
  fix first; the local patches are not the work.

Not yet measured: next-day recall of lesson 13's nine new items (the review comes with the next
`/lesson`), the length of the review (PR site_update_notifier#64 starts recording it), and what
fraction of the lesson's time the theme exchange would take.

### 5.11 Lesson 13 replayed after the fix-up batch (#162–#168)

Lesson 13 was bad enough that the changes after it were made as one batch, checked by replaying
lesson 13's export and continuing to lessons 14 and 15 before the learner's next lesson. They
are not separate experiments: the weekly read judges the batch as one change. The replay uses
the export's `learner.before.json` and arguments (the old code reproduces the real lesson: 128
exercises, 23.6 min). For lessons 14 and 15 it assumes every new item was recalled the next day,
and each open item with three or more words failed once more.

The batch also includes #170, which the weekly read judges with it: today's items come back by
time (not by exercise count); a short item is said alone at most three times and practised in
sentences (a pattern with a slot, else a known phrase that contains it); a lesson with nothing
else left lets the cap lapse; (until #218 b1) close variants of known items came in beyond the pace; a variant
is introduced as a form of one the learner has; `context` («Say: good, as in: This is good.») for
the 24 words of lessons 13–15; the same situation is narrated in full at most twice; asides are
about practised items only; and `max_listening_dialogues` is 4, not 2.

| | lesson 13 | lesson 14 | lesson 15 |
|---|---|---|---|
| length, before → after (min) | 23.6 → 28.6 | 28.9 → 29.3 | 26.7 → 28.3 |
| longest gap between introductions (min) | 4.9 → 4.7 | 7.4 → 2.7 | 9.1 → 2.8 |
| failed items practised (each) | – → 4–10 times, spread | → 4–8 | → 4–6 |
| most appearances of one new item | 12 → 12 | 12 → 10 | 10 → 8 |
| the same English situation, most narrations | 8 → 8 | 8 → 7 | 7 → 10 |

Fixed: the length, the failed items, the part before the whole, the recap of what the learner just
said. Not fixed in lesson 13: the repetition the learner named. Counted per new item of one or two
words, how often it was said **alone** against inside a sentence:

| item | alone | in a sentence | distinct sentences |
|---|---|---|---|
| Hvenær? | 9 | 0 | 0 |
| Klukkan hvað? | 9 | 1 | 0 |
| hálka | 7 | 4 | 1 |
| kalt | 6 | 4 | 2 |
| matvörubúðin | 6 | 4 | 1 |

«hálka» had seven recalls within about two minutes of its introduction, all at the same stage: today's
items are still reactivated by exercise counts (3, 5, 8, 13 exercises), the shape #162 removed for
open items. The owner, reading this: practising a word **alone** is what grates most; in a sentence it
is much better. A sentence may come five times or more, and the same word in slightly different
sentences might not be noticed even at ten. The same complaint came after lesson 6 («vegabréf»
drilled seven times as a bare word, §5.1), so it is a pattern, not one remark (G14).

### 5.12 Lesson 14: the first lesson heard on the batch (the baseline)

Lesson 14 was generated with LLA `175c76a`: #162–#174, not yet #175–#177. It is the first lesson
the learner heard on the post-lesson-13 batch. The figures are from its export, which a replay
reproduces exactly (145 exercises, 29.3 min); the lesson-13 column is the real lesson 13. This is the
reference for the next weekly read, which judges the batch as one change (§5.11).

| | lesson 13 | lesson 14 |
|---|---|---|
| length | 23.6 min | **29.3 min** |
| new items | 9 | 8 (one a cheap trip construction moved forward, «Klukkan er {hour}.») |
| a short new item said alone, most | 10 («Hvenær?») | **3** («peysu»: 3 alone, 5 in «Áttu peysu?») |
| most narrations of one English situation | 8 | 3 |
| «Quick review» announcements | 6 | 1 |
| longest gap between introductions | 4.9 min | 3.0 min |
| most appearances of one new item | 12 | 9 |
| generated sentences (plain / negative / question) | 21 (all plain) | 31 (27 / 4 / 0; the negative was taught in this lesson) |
| fitted open items | – | 5, practised ≥ 4 times each |
| listening dialogues | 0 | 2 |

- **The feedback form:** load «light» → **«about right»**; friction «repetitive, other» → «other»; "sooner":
  «Sérðu norðurljósin?», «Tekurðu kort?». The lesson-13 complaints (an Anki game, too short, failures
  barely reviewed, a part after its whole, English for a known question, a recap of what was just said)
  are not repeated.
- **The notes name three things, from two causes:**
  - «How do you say: It's {hour} o'clock.»: a mixed-review cue narrated a construction's raw template.
    A regression from #170 (#178).
  - «Say: A sweater, as in: Do you have a sweater?» at the close, after «Áttu peysu?» had been said five
    times. And a listening dialogue that told the learner «Það kostar fimm þúsund krónur.» and «Gætirðu
    talað hægar?», lines they can say. Both judge "can the learner say this?" per item from `knows()`,
    not per sentence from what they can produce (#179). It is the same shape as §5.10's «English for a
    known question».
- **Next-day review of lesson 13's nine new items:** 6 言えた, **3 迷った** («matvörubúðin», «Hvenær leggjum
  við af stað?», «Það er {weather}.»), 0 言えなかった. This is the first time «迷った» has been used at all
  (H10, §5.7).
- **Open items (#162):** the four failures of lesson 12 were asked the next day and recalled, so they
  are closed. The nine older ones («Fyrirgefðu», «Eigðu góðan dag», «Gangi þér vel»…) are still open:
  lesson 13 predates #162 and site_update_notifier#65, so they were neither practised nor asked. From
  lesson 14 on they are. How many close is a question for the next read.
- **Still open, structurally:**
  - the lesson's coherence (H4, #149 1b-ii: the theme exchange);
  - generative supply for this learner (G15). In replays of lessons 14–16 the learner meets one new
    construction a lesson at most. The core patterns the owner chose («Má ég …?», «Ég ætla að …»,
    «Viltu …?», `refresh`) are not reached on the trip ordering (#180).

### 5.13 Lesson 15: the first themed lesson the learner heard

Lesson 15 was generated with LLA `a82cbdc` (everything up to #195: the theme exchange and its variants,
parts against utterances, identical sentences counted). Its export reproduces exactly with
`tools/replay_lesson.py` (146 exercises, 29.1 min); the rows marked "transcript" are counted from the two
exported transcripts. Lesson 14 was generated before #186, so **this is the first lesson the learner heard
with a theme** (the supermarket, level 1, played twice).

| | lesson 14 | lesson 15 |
|---|---|---|
| length | 29.3 min | 29.1 min |
| new items | 8 | 9 |
| a short new item said alone, most | 3 | 3 («Varlega!» 3 alone + 3 in scenes, allowed for an utterance) |
| a part said alone after a sentence holding it (transcript) | 12 | 1 («skyr», held only by a theme line) |
| most times one sentence is said (transcript) | 10 | 9 |
| most narrations of one English situation | 3 | 2 |
| longest gap between introductions | 3.0 min | 3.5 min |
| generated sentences (plain / negative / question) | 31 (27 / 4 / 0) | 34 (19 / 11 / 4) |
| fitted open items | 5 | 5, practised ≥ 4 times each |
| theme | – | supermarket 1, twice (early assisted, late with the partner's line as the cue; since #210 the cue plays in both) |

- **The feedback form:** load «about right» (again); **friction: nothing ticked, the first time ever**;
  "sooner": «Er heitur pottur hérna?», «fallegt». Nothing in it describes the lesson as unrelated items.
- **The notes name two things:**
  - «heiti potturinn» / «heitur pottur»: the learner wanted the endings explained. Both forms came in
    the same lesson, two and a half minutes apart, and the only note on them is cultural (#198; the
    owner decided on a grammar note that pronounces the endings slowly, piece by piece).
  - «Now something you haven't heard yet» before each of «Klukkan er ekki þrjú / tvö / fjögur»: the
    novelty is announced per sentence, not per pattern, so every step of a substitution run is
    announced (#197; the owner also dropped «Klukkan er ekki …»).
- **Next-day review of lesson 14's eight new items:** 7 言えた, **1 迷った** («Sérðu norðurljósin?»), 0
  言えなかった. «迷った» comes back after lesson 14 (H10).
- **Open items:** the nine older ones from §5.12 are all still open. Not because the learner failed
  them: they were never asked. `plan.json` has never carried `open_items` / `open_not_fitted`, so the
  bot's check (site_update_notifier#65) never received its input (#199). One side effect in this lesson:
  «Gjörðu svo vel.», open, was framed as an unknown line («Try it.») in the theme exchange three minutes
  after the learner had said it.
- **A stale review question:** the review before this lesson asked «How do you say: It's {hour}
  o'clock.». The narration was fixed in #184, but the bot keeps the wording a question had when it was
  first queued (lesson 14) (site_update_notifier#73).
- **What this lesson says about the bets:**
  - H4: the first themed lesson is also the first with no friction ticked. One lesson is a lead, not a
    result (§6.2): read it again after three to five themed lessons.
  - The repetition rules hold on the real path, and "repetitive" stays absent; a new fixed phrase is
    still said about nine times identically (#192, open; the lever is #149 step 2).

### 5.14 Lessons 16–18, and the owner's remark on lesson 19

Lessons 16, 17 and 18 were generated with LLA `dc98102` (#207 and everything before it): the first lessons built
with step 2a–2c (§8). Each export reproduces exactly with `tools/replay_lesson.py`. The rows are the same measures
as §5.13's: rebuilt on its own revision, lesson 15 gives §5.13's figures (most times one sentence is said 9, most
narrations of one English situation 2, a part said alone after a sentence holding it 1). Lesson 19's feedback form
did not open at first: the lesson lists «miða» twice in `new_items` and Discord refuses a select with duplicate values
(#217, site_update_notifier#78). For it there was only the owner's remark at first; the form was sent later (§5.15).

| | lesson 16 | lesson 17 | lesson 18 |
|---|---|---|---|
| length | 28.6 min | 29.1 min | 29.1 min |
| new items | 8 | 8 | 8 |
| a short new item said alone, most | 3 | 3 | 3 |
| a part said alone after a sentence holding it | 6 | 2 | 4 |
| most times one sentence is said | 7 | 9 | 9 («Get ég fengið kvittun?») |
| most narrations of one English situation | 5 | 3 | 4 |
| longest gap between introductions | 3.4 min | 2.9 min | 2.8 min |
| generated sentences (plain / negative / question) | 45 (25 / 10 / 10) | 47 (27 / 10 / 10) | 40 (22 / 10 / 8) |
| fitted / waiting open items; fewest practices of a fitted one | 5 / 5; 6 | 5 / 2; 5 | 5 / 2; 6 |
| theme, played twice | tour 1 | museum 1 | supermarket 1 (replayed after its rest) |
| next-day review of the lesson's new items | 7 言えた, 1 言えなかった («eldfjall») | 6 言えた, 1 迷った, 1 言えなかった | 8 言えた of 8 (§5.15) |
| feedback form: load; friction | right; unclear, pacing, other | right; unclear | **light**; repetitive, other |

- **Two rows got worse than lesson 15** (1 → 6, 2 → 5), for one reason. «heiti potturinn» (4 of the 6) and
  «sturtan» (the 5 narrations of «The shower, as in: The shower isn't working.») failed lesson 15's review and
  are open. Their frames are not met, so an open part is practised as bare meaning recalls with the same
  narration (#215).
- **Next-day review of lesson 15's nine new items** (before lesson 16): 5 言えた, 4 言えなかった: «Ég ætla að …»,
  «sturtan», and both «heiti potturinn» and «Er heitur pottur hérna?», two forms of one word introduced in one
  lesson (#198, H5). The pace went from 6 to 5 (4 of 9 failed, over 20%).
- **What the learner wrote, grouped by cause:**
  - The guidance disappears on a later play. Lesson 16: after a partner's line, silences with no guidance on
    what to answer. Lesson 18: in the supermarket, the checkout starts right after asking about skyr, and
    the instructions are gone. One switch removes the intent, the setting change and the scaffold
    together (#210).
  - A construction's question and negative are asked before they are heard (lesson 16, «ég ætla að …»; #211).
  - Pronunciation: «eldfjall» and «jökull» worry the learner (lesson 16), who ticked them for "sooner".
    «eldfjall» failed the next day. Single words get no slow model (#212), "sooner" is stored but never acted
    on (G1), and these words are only ever said alone (#215).
  - Numbers. Lesson 17: a review question asked for a number 1–4 with no gender or scene. Lessons 16–18's plans
    ask numbers only in sentences, so the question most likely came from an entry queued in an early lesson
    that keeps its first wording (site_update_notifier#73). The same shape nearly came back through #206's
    first versions, a variant «þrjá» drilled bare, caught in review (§9 "One admission rule for a part").
    Also: only 1–5 after 18 lessons, while partner lines say «sex hundruð» and «tuttugu» (#213).
  - «Get ég fengið kvittun?» many times in a short time (lesson 18): a known pattern with a known part,
    introduced as a new phrase and taken through the whole ladder, 8 exercises in 8.5 minutes (#192, #206).
  - «pacing» (lesson 16) has no note of its own: ask (§1, step 6).
- **Lesson 19 (the owner, in chat): «too easy».** The pace has been 5 since lesson 16. `suggest_pace` raises it
  only when at most 10% of the last lesson's new items failed, counting a «迷った» as half a failure. With
  eight items that means all eight recalled. Lesson 16's items gave 1 failure (88% success, above the
  80–85% band H9 aims at) and lesson 17's gave 1.5 (one failure and one «迷った», 81%, inside it). The load
  rating is not an input, so the drift to «light» changed nothing. Owner's decision: a three-lesson window, and the
  load rating counts (#218; §9 "Pace", not built yet).
- **Changes merged since lesson 15, against their predictions (§1, step 3):**
  - #196, a theme in every lesson: held (tour, museum, a supermarket replay after its rest). Keep.
  - #201, new material for the theme's next level: the next levels lacked 0, 0 and 1 item, and the one was taken,
    so the theme chose 1 of the 24 new items and the rest came from the trip order. Kept, but barely tested; more
    theme data (§8) is what makes it bite.
  - #202, a part comes with its frame: not met for parts whose frame isn't known. The nature words came in
    bare (3 alone, 0 in sentences), and open parts are practised bare (above). Keep; the gap is #215.
  - #203, the generated sentence said fewest: no generated sentence was asked twice in lessons 16–18, as in
    lesson 15 before it. Kept, but barely tested: the case it fixes did not come up. The most-said sentence (9)
    is a fixed phrase, #192's concern.
  - #204 and #207, at most three new items of one set: held (3, 3, 0). Keep.
  - #205, open items asked: it worked. Of §5.12's nine, four closed in the review before lesson 16 (asked as
    lesson 15's ordinary questions: «Fyrirgefðu», «Gangi þér vel», «Hvað þýðir þetta?», «Verði þér að góðu») and four
    more in the next, through #205's open items; «Hvernig segir maður þetta …?» is still open. Another failure
    took the same path: «Fara heim» (lesson 7) failed before lesson 16 and closed two reviews later through #205.
    Lesson 15's four failures are all still open after
    three reviews: G11, and #220 (later checks get no slots).
  - #214 and #206 were merged after lesson 18: no lesson yet.

### 5.15 Lesson 19

Lesson 19 was generated with LLA `dc98102`, like lessons 16–18, so no merged change was heard yet (§1, step 3). Its
export reproduces exactly (163 exercises, 29.2 min). Lesson 18's next-day review (§5.14's table) let
the pace rise from 5 to 6. The feedback form opened once the bot's dedup (site_update_notifier#80) was in.

| | lesson 19 |
|---|---|
| length | 29.2 min |
| new items | 9 listed, 8 distinct («miða» embedded at 5:30, introduced again at 14:14, #217) |
| new components, weighted (#218) | 5 (sundföt, ótrúlegt, sótt, taka mynd, reyna) |
| a short new item said alone, most | 3 |
| a part said alone after a sentence holding it | 1 |
| most times one sentence is said | 10 («Einn miða, takk.»; #206's cap of 9 came after) |
| most narrations of one English situation | 3 |
| longest gap between introductions | 3.1 min |
| generated sentences (plain / negative / question) | 48 (27 / 11 / 10) |
| fitted / waiting open items; fewest practices of a fitted one | 5 / 2; 6 |
| theme, played twice | cafe 1 |
| next-day review of the lesson's new items | 8/8 recalled (§5.16) |
| feedback form: load; friction | **light**; other |

- **«Light» again, at a higher pace.** The item count was 8 every time. Counting new word forms (in no item met
  before) instead, lessons 16–19 had 7, 9, 4 and 6, against loads «right», «right», «light», «light»; the owner read
  lesson 19 as five new words, «taka mynd» being one. The pace's unit becomes weighted new *components* (§9
  "Pace", #218). Recounted, lessons 16–19 come to 8, 8, 5 and 5 (recounted by the planner's `component_cost` on the exports, #218 b3: 8, 9, 5, 5: «norðurljós» has its own vocab item, so it costs 1, and «farið» counts as a word, the form having no item of its own). The count was chosen on principle (a pattern is
  one learning step, like a chunk, which is also the owner's reading of «taka mynd»), not to fit four lessons: the
  other counts separate «right» from «light» too (a pattern as 1 plus its new words: 9 and 8.5 against 7 and 5–6;
  no weight for patterns: 7 and 7.5 against 4 and 5).
- **What the learner wrote, by cause:**
  - «How do you say: Sleep.» → «sofa» in the review: the imperative reading. The curriculum's `meaning_spoken` is
    «to sleep», and lessons 14–19's plans ask «sofa» only in sentences, so this is an early lesson's queued
    wording (site_update_notifier#73, the third case).
  - «miða» and the clock with 1–5: easy, yet repeated. «miða» is in 29 of the lesson's lines (taught twice, #217;
    «Einn miða, takk.» 10 times, #192/#206), and the clock can only cycle five hours («Klukkan eitt» 6 times),
    because the learner knows no other numbers (#213). Nothing learns from a 言えた that an item is easy for this learner (#220).
  - «Hvernig segir maður þetta á íslensku?»: long marked for review, never checked, and practised every lesson.
    It failed twice by lesson 15 and has had no confirmed outcome since. It is listed in every plan's `open_items`
    with a question, but the review never asked it, so it never closes. Owner: every open item is asked at the
    next review, like the new items' check (#220).
  - Numbers 1–5 only, the fourth remark. Owner: a number × noun track, with a fixed share of practice a lesson
    that covers 1–99 across prices, tickets, people and time, and that also makes the common nouns stick (#213).

### 5.16 Lesson 20: the first lesson on #229, #230, #231, #233 and #235

Lesson 20 was generated with LLA `5e99829`. It is the first lesson heard with these changes:
- the pace from three lessons and the load rating (#229);
- the pattern instance (#192, #231);
- the cue in every play (#210, #230);
- no form as filler (#233);
- weighted new components (#235).

Lesson 19's next-day review: all 8 new items recalled.

| | lesson 20 |
|---|---|
| length | 28.7 min, 146 exercises |
| new items; new components, weighted (#218) | 11; 9 of a target of 9 (3 of the items cost 0) |
| theme, played twice | tour 1, a replay |
| generated sentences | 36 exercises |
| feedback form: load; friction | **light**; pacing, repetitive, unclear, other |

What the learner wrote, by what the lesson did:

- **"From about 17 minutes, endless easy, random repetition; boring."** The target was reached by 14:50.
  - From 15:43 to 19:00 came 21 generated sentences in a row from known patterns: «Ég tala ekki ensku / japönsku /
    dönsku», «Það kostar … krónur» ×3, «Hvað kostar …?» ×3, «Hvar er …?» ×3, «klukkan …» ×3.
  - From 19:05 to 23:00 came one-shot reviews of known items.
  - None of it served a target expression or a scene.
- **"Expressions I reported as said in the review come back many times: «eldfjall», «Hvernig segir maður þetta á
  íslensku?», «sturtan»."** These had a one-day interval and were due that day. The audio asked them again hours after
  the morning's Discord review had (G7: the audio's learner model and the Discord review queue each schedule on their own). In the same stretch, items due only the next day («hraun»,
  «strönd», «norðurljós») filled time too.
- **"«Eigðu góðan dag» was announced as new, but it isn't."** The pattern «Eigðu {adj} {time}.» was introduced as a
  new pattern with that phrase, which the learner already knew. The pattern costs 1 by the rule, but it was presented
  as new rather than as a pattern of a phrase the learner knows.
- **"«hjálpina» 'for help' and «matinn» 'for food' feel half-taught; better the full sentence."** They are the fillers
  of «Takk fyrir {thing}.», drilled as words, with a gloss that only makes sense inside the sentence. The expressions
  the traveller needs are «Takk fyrir hjálpina.» and «Takk fyrir matinn.».
- **"Told to just listen, then told to say it, about the bus and getting off, which never came up, and nothing
  introduces them afterwards."** The bus dialogue (`straeto`) opened with "a conversation to listen to… you don't need
  to remember them". It then asked for «Fer þessi strætó í miðbæinn?» and «Hvar á ég að fara út?» with "Try it."
  (#183), although both were new to the learner, and nothing afterwards taught them.
- **"Sometimes no pause between the instructor's line and the example."** For example: "You can put other words in
  the same place." → the sentence; "You know this:" → the line; "Now the whole conversation, without pauses." → the
  first line.
- **"The review asked «the hot tub, as in where is the hot tub?» although I learned «Hvar er heiti potturinn?»."** The
  Discord review asked the part, not the whole the learner had learned.

**Reading.** The load is «light» again, now with the target met. The remarks share one cause. The lesson's time and
choices come from mechanisms: generation supply, the spacing schedule, part and whole, tried turns. Each is right by
its own rule, and none asks whether it helps a target expression come out or trains the ear. The owner's answer is the
concept in §3 and §9 "Good enough overall". The next work follows from it (§8).

### 5.17 Lesson 21: the first lesson on #247, #250, #251 and #252

Lesson 21 was generated with LLA `c5cbcb7`. It is the first lesson heard with the changes made after lesson 20:
- spare time serves the scene and the ear, and the morning's review is not asked again (#247);
- a listening scene asks only for taught lines (#250);
- a beat after every framing line (#251);
- the second-half rotation: pick out information, catch an unknown word (#252).

Lesson 20's next-day review: 8 of 10 new items recalled. The two not recalled are «hjálpina» and «matinn», the two
parts asked bare.

| | lesson 21 |
|---|---|
| length | 29.3 min, 126 exercises |
| new items; new components, weighted | 13; 10 of a target of 10 (4 of the items cost 0) |
| target reached | 20:11 |
| theme, played twice | supermarket 2; heard again: museum 1, café 1 |
| generated sentences | 24 exercises, longest run 2 |
| second half | 8 pick-outs, 1 unknown word caught |
| daily-read rows | unserved after the target 0 s; asked after the morning's review 0; untaught lines asked 0 |
| feedback form: load; friction | **right**; other |
| marked under-practised | 4 of 13: «án sykurs», «Er þetta sæti laust?», «til að taka með», «kaffihúsið» |

What the learner wrote, by what the lesson and the review did:

- **The review, "for the help → «hjálpina»: shouldn't it be «fyrir hjálpina»?", and the same for «matinn».** The parts
  of «Takk fyrir {thing}.» were asked bare, and the learner answered with what they would say. Both items failed.
- **The review, "day → «dag»; «dagur» would also fit".** «dag» is the accusative part of «Eigðu góðan dag.», asked bare
  as "Day."; its form is only right inside the whole.
- **The review, "«two adults» and «two adults, please» both come".** The part `tvo_fullordna` and the construction
  `partei_takk`, whose situation fills it with that part, were in the same review. «Eigðu góðan dag.» was asked twice
  too, through `eigdu_godan_dag` and `eigdu_godur`.
- **The review, "«Það er svo kalt í dag!» two days running".** This is a scene card. The card queue brings a card
  answered well back after one day (site_update_notifier#95).
- **The lesson, "a price or a time is said, then I'm asked for the number: just parroting, too obvious".** The 8
  pick-outs were «Það kostar N krónur.» and «Klukkan er N.». The line is a known frame plus the answer, and the answer
  is said back in Icelandic.

**Reading.**
- **What did not come back.** None of lesson 20's remarks returned: no boring stretch, nothing untaught asked, no
  missing pause, no re-asking of the morning's review. The load is «right». For each of §8's built "Now" items this is
  the first of the three feedbacks its "done" needs.
- **One cause behind the review remarks.** Four of the five review remarks share the cause #239 names: a part taught
  and asked outside its target expression. The review is where it shows most, every morning. The next review's plan
  repeats it:
  - «hjálpina», «matinn» and «kaffihúsið» are asked bare, and «kaffihúsið» in three more sentences;
  - «hraun», «strönd», «norðurljós» and «samloku» are asked bare (#215).
- **The pick-outs.** They have the shape of concept 2 but not its work. Nothing has to be found when the answer is the
  only new thing in the line. The line must hold more than the answer: the learner finds one piece among others.
- **The under-practised items.** All four had no recall of their own for 7–12 minutes of the second half
  («kaffihúsið» only inside generated sentences) while the rotation played. One lesson, below the heavy share: watch
  it; no change yet.

### 5.18 Lesson 22: the first lesson on #254–#260

Lesson 22 was generated with LLA `923553b`, with the bot's queue pass (site_update_notifier#96/#97) and the 3-day first
showing of a scene card (#95/#98). It is the first lesson heard with:
- a part introduced inside its whole and asked through it (#254, #256), and the review's questions refined (#258);
- a home for every part (#257);
- pick-outs from a scene's line with two pieces of information (#255);
- an aside read a sentence at a time (#260).

**Lesson 21's next-day review.** 4 of the 11 new items asked were recalled; 2 were not asked. By question, about 5 of
10 failed:
- «Ég vil frekar te.» and «Ég ætla að fá mjólk án sykurs.», each a question carrying several items since #239;
- «Er þetta sæti laust?», «Þetta er allt.» and «Til að taka með, takk.».

Lesson 20's was 8 of 10. The pace held at 10: over three lessons the failures are 7 of 33, inside the 15–25% band.

| | lesson 22 |
|---|---|
| length | 27.7 min, 135 exercises |
| new items; new components, weighted | 13; 12 of a target of 10 |
| target reached | 15:31 |
| second half | 2 pick-outs (both two-piece lines), 3 unknown words caught, 4 scenes heard again |
| daily-read rows | unserved after the target 54 s; longest generated run 3; longest run of one kind 4; echo pick-outs 0 |
| uses of each new item before the closing | 4.2 on average (lesson 20: 6.3; lesson 21: 5.8) |
| feedback form: load; friction | **right**; other |
| marked under-practised | «Gleðilega hátíð!» |

What the learner wrote, by what the lesson did:

- **"I was made to say «the toilet is what?», which is odd."** «klósettið» ("The toilet.") was introduced and asked
  bare at 05:34, before «Hvar er klósettið?» at 06:20 (#262). #254's whole-first introduction only looks at a
  construction whose authored example names the part. «klósettið»'s whole is a phrase.
- **"In the conversations, expressions I learned long ago were not mine to say; I was told the answer, maybe ten
  times."**
  - The rotation played four scenes the learner has done as heard plays (#218 b1).
  - In a heard play every learner line is "«Here you would say:» → the line", with no pause. That was 12 lines the
    learner can say.
  - Each play opened with "it has a few new expressions in it", and none were new (#263).
- **The owner, on the transcript: «köku» ("a piece of cake") was introduced bare, with no hint of its case.** The
  ordinary form is «kaka»; «Ég ætla að fá köku.» should come first (#262).
- **The owner: "One word was new. Say it, and ask what it means." makes guessing the word the task.** "He said
  *something* is closed: ask what it is" would be clear (#248).

**Reading.**
- **What did not come back.** None of lesson 21's remarks returned: no echo pick-outs, no review remark about parts
  asked bare or twice, no boring stretch, nothing untaught asked, no missing pause. The load is «right» for the second
  lesson running. For the work built after lesson 21 this is the first of the three feedbacks.
- **One cause behind the new remarks.** Both follow the shape of #239: a mechanism that puts a line outside the
  learner's own use.
  - A part introduced before its whole («klósettið», «köku»): the whole-first rule is too narrow.
  - A known line withheld in a scene heard again: the heard play was built for the ear, not for the lines the learner
    owns.
- **Watch, no change yet.**
  - Lesson 21's next-day recall fell to 4 of 11.
  - Lesson 22 gave each new item fewer uses before the closing (4.2).
  - Possible causes: the second half taking time from today's items, the review now asking whole sentences (harder
    than parts), or 13 café items close to each other.
  - It is one lesson. Lesson 22's next-day review will tell; if it is low again, this becomes a "Now" item.

### 5.19 Lesson 23: the first lesson on #262–#276

Lesson 23 was generated with LLA `bc8e5fa`. It is the first lesson heard with:
- one line-role rule for every play mode (#263, #267);
- a part taken out of the line that holds it, and the line kept across lessons for the review (#266, #268, #269);
- a catch task cued by the understood meaning (#271);
- conversation timing: a beat after the partner's line, known replies paused as single exercises (#272, #274);
- scene units every 4–5 minutes through the lesson (#273, #275);
- the noun pilot: a form named against its basic word, a pilot noun recalled in its sentence, the tour frame «Mig langar
  að sjá {…}.» (#270, #276).

**Lesson 22's next-day review.** 10 of its 13 new items were recalled. «Hvað heitir þetta fjall?» and «Gleðileg jól!» were
hesitated; «Gleðilega hátíð!» failed. Lesson 21's was 4 of 11. §8's 60% rule (revisit #235's zero cost below about
60%) does not fire: the pace unit stays as it is.

| | lesson 23 |
|---|---|
| length | 28.4 min, 125 exercises |
| new items; new components, weighted | 13; 11 of a target of 10 |
| target reached | 19:06 |
| longest stretch without a scene | 4.2 min (lesson 22, before #275: 12–16 min on the replays) |
| scene units | 3 unknown words caught after the target; pick-outs and scenes heard again through the lesson |
| uses of each new item before the closing | 4.8 on average (lesson 22: 4.2) |
| bare recalls of a pilot noun | «sturtan», «eldfjall» (no sentence exists yet for either) |
| feedback form: load; friction | **right**; other |

The rebuilt lesson 23 on main is identical to the export (125 exercises, 28.4 min), so the replay is the real path.

What the learner wrote, by what the lesson did:

- **"«A supermarket: the shelves, the dairy fridge, the till.» makes no sense read aloud."** A theme's `setting` is a written
  synopsis. It was spoken 10 times: as the scene line of each conversation and as the lead-in of every scene unit from
  another theme, which #275 made more frequent (#278).
- **"«Say: Akureyri. → Akureyri», «Say: Reykjavík. → Reykjavík» in the review are far too obvious."** When an item's
  meaning is its target, the cue says the answer. The lesson's own recall does the same, and the predicted lesson 24 has
  both again in the audio (#277).
- **"When I ask Speaker B what a word means, the Instructor answers in English and Speaker B only repeats the line."**
  The narrator answers a question put to the partner (#279).
- **"«nýtt ár», «flugið», «hættulegt» were hard to make out."** The phrase got a slow model, the hard word did not (#212).
- **"«Er þetta hættulegt?» came as a second new expression after «Þetta er hættulegt.»; the negative was light."** It is
  the `question` form of «Þetta er {adj}.», but the data has it as its own phrase, with a full ladder (#280).
- **"«þúsund» and «krónur» were each stressed on their own: redundant."** Each was taken out of «þúsund krónur» in its
  own exercise, 90 s apart (#280).
- **"«Say: Here.» is ambiguous: hér or hérna?"** «hérna» was asked bare although it came in «Það er hérna.»: the
  sentence rule of #276 covers only the pilot nouns (#277).

**Reading.**
- **What did not come back.** None of lesson 22's remarks returned: no part introduced before its whole, no known line
  withheld in a scene heard again, no "guess the word" catch task, no long stretch of drills. The load is «right» for
  the third lesson running. For #262, #263 and #248's catch task this is the first of the three feedbacks.
- **One cause behind three remarks.** A rule built for one path, missing in another: the sentence rule exists for pilot
  nouns only (hérna, lundi in lesson 24), nothing stops a question whose cue is its answer, and a written synopsis is
  spoken. The fixes widen a rule that exists (#277) or replace data meant for the eye (#278), not new mechanisms.
- **Recall recovered.** 10 of 13, with 4.8 uses per new item before the closing. The "watch" of §5.18 closes.

### 5.20 Lesson 24: the first lesson on #277–#293, after the speech-synthesis outage

Lesson 24 was generated with LLA `7976fa2`. It is the first lesson heard with:
- a part asked through its sentence, and no question whose cue is its answer (#277);
- a spoken scene line (#278), a catch task that reports the partner's answer (#279), light introductions (#280);
- the partner speaking word by word after «Gætirðu talað hægar?» (#261);
- no sentence asked twice within a minute (#273's spacing half);
- «Use it in a sentence.» only when true, and a new part applied in another sentence right after its retrieval (#287);
- a slow, split model for hard words (#212), and a frame brought forward for a stranded noun (#270).

**The bot's generations failed from 2026-10-12.** The free endpoint behind edge-tts refused connections from the bot's
location (403; upstream rany2/edge-tts#490 reports it from 2026-10-10). Every generation failed until Azure Speech's official API, with the
same voices, became the fallback (#296, #297, #299, #300). The key reached the bot through sealed repository secrets
(site_update_notifier#119). A failed generation is now retried without a second review (site_update_notifier#110, #116).

**Lesson 23's next-day review.** 10 of its 13 new items were recalled; «Gleðilegt nýtt ár!», «hérna» and «Ég er hér í
viku.» were hesitated, none failed. That is above §8's 60% rule for the second lesson running: the pace unit stays.

| | lesson 24 |
|---|---|
| length | 28.3 min, 116 exercises |
| new items; new components, weighted | 10; 11 |
| target reached | 19:12 |
| longest stretch without a scene | 5.5 min |
| a sentence asked again within a minute | 2 |
| trivial questions; bare nouns in the lesson's recall | 0; 0 |
| new words given the split model | none (no hard word among the new items) |
| speech segments touching with no pause between | 66 (43 English cue → Icelandic) |
| feedback form: load; friction | **right**; pacing, other |
| review queue | «確認待ち 146件» |

The rebuilt lesson 24 on main is identical to the export (116 exercises, 28.3 min), so the replay is the real path.

What the learner wrote, by what the lesson did:

- **"Some utterances came too fast, with no pause before them."** Two speech segments touched 66 times, and after the
  renderer's trim they play about 0.12 s apart: «Repeat.» → «Mig langar í kaffi.», «It starts with:» → «Ég». Nothing in
  the script decides what happens at a change of voice (#301).
- **"The explanation of verð að / vil / mig langar að had so little gap around the English that it was confusing."**
  The note cut one English sentence around five Icelandic fragments: 18 changes of voice in 30 seconds, none with a gap
  (#301).
- **"The word-by-word slow speech was very good. The ordinary introduction's slow model should work the same way."**
  The partner's reply after «Gætirðu talað hægar?» (#261) is the first merged change named and praised in a feedback.
  The introductions still stretch whole sentences at `slow_rate`, 11 times (#302).
- **(The owner, on the pick-outs.)** «When does it close?» after the opening-hours line is good, but here the
  information is what one goes to find, so the question belongs before the line (#303).

**Reading.**
- **What did not come back.** None of lesson 23's remarks returned: no setting read aloud, no obvious name question,
  no narrator answering for the partner. Load «right» for the fourth lesson running.
- **One cause behind both pacing remarks.** The script has no rule at a change of voice. It is one rule for all
  exercises (#301), not a pause added to each.
- **Gaps, not stretched sounds (H8).** The praised reply and the remarked introduction differ only in that: the same
  words at natural speed with gaps between them, against a stretched line. This supports H8's segmentation reading and
  #261's design; #302 applies it to the introductions.
- **The review queue is unread.** 146 due, with #109's cap able to defer only well-known entries. Which part is growing
  is unknown until site_update_notifier#123 shows it; #220's intake side is decided from that.

### 5.21 Lesson 25: the first lesson on #301–#308

Lesson 25 was generated with LLA `58e1b7a`. It is the first lesson heard with:
- a gap at every change of voice (#301);
- the «Slowly» model said word by word (#302);
- the pick-out naming what to listen for before the line (#303);
- the second-half guard (#294);
- ease learned from long-gap recalls (#298).

It is also the first export with the review backlog's breakdown (site_update_notifier#125).

**Lesson 24's next-day review.** All 10 of its new items were recalled. That is the third lesson running above §8's
60% rule.

**Retention by gap**, all of it so far, since the bot began reporting gaps (site_update_notifier#118):
- 3–6 days: 2 of 2;
- 7–13 days: 3 of 3;
- 14+ days: none yet.

| | lesson 25 |
|---|---|
| length | 28.5 min, 132 exercises |
| new items; new components, weighted | 9; 10 |
| target reached | 16:00 |
| longest stretch without a scene | 4.3 min |
| a sentence asked again within a minute | 1 |
| speech segments touching at a change of voice | **0** (64 gaps placed; lesson 24: 66 touching) |
| lines said word by word; pick-outs cued before the line | 11; 3 |
| new words given the split model | none (no hard word among the new items) |
| feedback form: load; friction | **right**; other |
| review queue | 151 due of 199: answered 言えた once 109, 言えた twice or more 18, 迷った/言えなかった 13, new-item check 9, never asked 2 |

The rebuilt lesson 25 on main is identical to the export (132 exercises, 28.5 min).

What the learner wrote, by what the lesson and the review did:

- **"Only one expression with úlpu came up, so I'm not sure it will stick. Widen it, to size or price."**
  - The lesson asked «Ég þarf úlpu.» in 8 exercises, always the same sentence.
  - «Ég þarf {thing}.» is known (lesson 22), but the item is not linked to it, so the planner sees a fixed sentence, not
    the pattern with a new filler. «úlpa» was never met as a word.
  - About 29 pattern instances in the curriculum are unlinked like this one (#311).
- **"In the review, the same scenes and readings come up again and again. I want new ones."**
  - The bot's cards put due cards first; unseen ones only fill the seats that are left.
  - A reading card's first 言えた brings it back the next day; a scene card's waits 3 days (site_update_notifier#95).
  - Fix filed as site_update_notifier#132.
- **"The review says «Put it together…». It needn't ask the way the lesson does."**
  - 17 of the 52 review questions carry a lesson cue: «In a sentence» 11, «Put it together» 3, «Use the pattern again» 2,
    «Your turn» 1.
  - These are instructions for a moment in the audio, copied into a written card (#312).

**Reading.**
- **What did not come back.** No remark on pacing, gaps or the slow models. This is the first of the three feedbacks
  §8 asks for after #301, #302 and #303. Load «right» for the fifth lesson running.
- **A word needs other frames, as a pattern needs other fillings (H6).**
  - The úlpu remark is not about «úlpu». A new word that arrives inside a known pattern is heard in one sentence only,
    because nothing tells the planner that the sentence is a pattern with a filler.
  - The fix is the link and the frames (#311), not more practice of the sentence. (Size and price were the owner's
    example of such connections, not a requirement: #326, 2026-10-14.)
- **The written review has no rules of its own.** Both review remarks have the same root:
  - it takes the lesson's wording, which is a cue for a moment in the audio (H3: the cue should resemble use);
  - it serves due cards before unseen ones, with no variety rule (H12).
  - #312 and site_update_notifier#132 give it its own wording and a seat for something new.
- **The backlog is the answered-once questions, not the intake.**
  - Only 2 of 151 were never asked; 109 were answered 言えた once, mostly the next-day check of a new item.
  - The ok ladder brings them back the next day, and the bound defers only entries with two confirmations.
  - This decides #220's open branch: site_update_notifier#133 (a first 言えた waits 3 days; the bound also defers
    answered-once entries). #220's ranking by lesson time saved remains the longer-term rule.

### 5.22 Lesson 26: the first lesson on #311–#332

Lesson 26 was generated with LLA `0eb8905`, the bot at site_update_notifier `c685d2d`. It is the first lesson heard with:
- a pattern-linked phrase with a new word taught in other frames (#311: #316, #318);
- the written review in its own words (#312: #314);
- the review backlog's first 言えた waiting 3 days (site_update_notifier#133: site_update_notifier#134), and a new card every
  review (site_update_notifier#132: site_update_notifier#135);
- the endings said piece by piece in a note (#323), new material grouped by scene (#327: #329), a hard item practised
  through its connections (#326: #330, #332), and a recall at a real gap extending the interval (#220: #331);
- no «Áttu leigubíl?» on the word's own sentence path (#334).

**Lesson 25's next-day review.** All 9 of its new items were recalled: the fourth lesson running above §8's 60% rule.

**Retention by gap**, all of it so far (site_update_notifier#118):
- 3–6 days: 3 of 3;
- 7–13 days: 5 of 5;
- 14+ days: none yet.

| | lesson 26 |
|---|---|
| length | 28.9 min, 119 exercises |
| new items; new components, weighted | 11; 10 |
| theme (level); new items inside the played scene | museum (1), a replay; 0 of 10 (the 11 less a variant of a known item) |
| target reached | 18.7 min |
| longest stretch without a scene | 4.8 min |
| a sentence asked again within a minute | **6** (lesson 25: 1) |
| speech segments touching at a change of voice | 0 (78 gaps placed) |
| new words given the split model | none (the rule flagged none, see below) |
| feedback form: load; friction | **right**; other |
| «sooner» | «Vegurinn er lokaður.», «Get ég fengið reikninginn?» |
| review queue | **114 due** of 207 (lesson 25: 151): answered 言えた once 75, twice or more 14, 迷った/言えなかった 13, new-item check 10, never asked 2 |

The rebuilt lesson 26 on main is identical to the export apart from pronunciation-note lines (119 exercises, 28.9 min).
The lesson-26 preview's findings (#333) were still in it: «Showing the address: To this hotel, please.» read as a cue
7 times, «Má ég sofa?», and «Get ég fengið reikninginn?» played as «a sentence from a pattern you know» two minutes after
it was taught. «Áttu leigubíl?» was not (#334).

What the learner wrote, by what the lesson did:

- **"reikninginn, vegurinn and lokaður were hard to remember, and I wasn't sure how to say them."**
  - None of the three got the slow, split model. `sounds.hard_sounds` flags one-word vocab items with ll, tt, fj or ý;
    «reikninginn» has none of those, and «vegurinn», «lokaður» are words inside phrases, which the rule never reads.
  - What they heard was the phrase word by word (#302), which places the words but doesn't model a long one.
  - #337: a word reported hard gets its split model again; the rule reads inside phrases and adds the sounds this
    learner has stumbled on («ei», «ng», «ð», «g» between vowels).
- **"The 'listen for yy' exercise flows oddly."** The learner wrote the target format themselves: «Listen and answer.»,
  the line, a pause, «the answer is», the answer and its meaning, «Now listen again.», the line.
  - The pick-out says «Listen.» but wants an answer, and the model answer and the replay come unannounced. The other
    exercises mark their turns; this one doesn't.
  - #335, wording only.
- **"«Ég elska» had many foods, which was good, but the bus only went to the town centre."** (The destinations they
  listed are examples.)
  - «Ég elska {food}.» is a construction, said with 7 foods. The transport set is all fixed phrases: «Fer þessi strætó í
    miðbæinn?» was said 8–9 times identically, and «Fer þessi strætó á flugvöllinn?» is a separate item for later.
  - #336: where a scene's line varies in use, author it as a pattern with the scene's fillers.
- **The owner, after lesson 26: "The 'ask what the missing word means' practice with sestu, kjötsúpa keeps repeating.
  Shouldn't the course's other new words take this form?"**
  - The catch task asked «sestu», «kjötsúpa» and «þarftu» in every lesson from 23 to 26, and the replay keeps them in
    27 and 28. The pick-outs «When do we leave?» and «When does it close?» come in every lesson from 25.
  - Only 8 partner lines carry a gloss, three of them qualify, and the rotation's memory lasts one lesson.
  - #339, with the owner's decision (2026-10-15): a word is caught about once, and some of the new words that come
    after are introduced through the catch (§9 "Conversation"). The pick-outs rotate across lessons.

**Reading.**
- **What did not come back.** No remark on gaps, the slow models, the review's wording, repeated review cards or the
  backlog; load «right» for the sixth lesson running. The changes heard first in lesson 24 have their three feedbacks (§8).
- **The «úlpu» shape, a third time.** Lesson 25's úlpu (#311), the preview's «Get ég fengið leigubíl?» (#333) and now
  the bus have one cause: a line the learner will need in several versions is authored as a fixed phrase, so the planner
  can only repeat it. #311 linked phrases to patterns that exist; #336 is the case where no pattern was written. The
  learner's own contrast, «Ég elska» against the bus, is H6 seen from the learner's side.
- **H13's first real test is a miss of the rule, not of the model.** The words the learner found hard were never
  flagged, so the slow model was not heard. The rule was built from earlier remarks (ll, tt, fj, ý) and is narrower than
  what this learner finds hard.
- **The backlog fell from 151 to 114 due** in one day of site_update_notifier#133, toward §8's «about 100».
- **Repetition across lessons is the theme of this round.** The bus phrase within a lesson (#336) and the same catch
  words and pick-outs in every lesson (#339) are one complaint at two scales: where variety was expected, the material
  had one version. The within-lesson rows (`asked_again_within_spacing`, the caps) could not see the second, because no
  row compares lessons; #339 adds one.
- **Watch:** 6 sentences asked again within a minute (lesson 25: 1). It is a soft preference, read as a trend; the
  transport phrases' repetition is where it comes from, which #336 addresses.
- **#327 on the real path:** the museum level was a replay, so none of the 10 new items came from the played scene. The
  replay rows for lessons 27–28 read 0 of 12 and 5 of 12, and no day's new material shares a topic: part 1 groups what
  the order offers, and part 2 (theme levels) and the scene line are what supply the rest.

### 5.23 Lesson 33: the first feedback on #365–#371

Lesson 33 was generated with LLA `fad041f`, the bot at site_update_notifier `2fc64d2`. Lessons 27–32 have no subsection:
their findings went into issues and PRs directly (#339, #337, #335, #336, #327). Lesson 33 is the first feedback on:
- small talk, the getting-to-know-you scene (#371), whose level 1 it played;
- the played level's goal said after the opening (#369) and the closing in the order of its turns (#370);
- a level played in the lesson that teaches its lines (#365).

| | lesson 33 |
|---|---|
| length | 29.2 min, 122 exercises |
| new items; new components, weighted (target) | 9; 8 (7) |
| theme (level); today's new items said as a turn of the played exchange | small talk (1); «Ég heiti Yuki.», «Hvað heitir þú?» |
| target reached | 18.7 min |
| longest stretch without a scene | 4.1 min |
| a sentence asked again within a minute | 0 |
| most narrations of one situation | 2 |
| hard items with no connection to practise them through, asked 3+ times | «Ég er með ofnæmi fyrir hnetum.» (open), said 6 times |
| feedback form: load; friction | **right**; other |
| «sooner» | «hringja heim» (hard to say) |
| review queue | **115 due** of 276: answered once 78, 迷った/言えなかった 22, new 8, never asked 3, 言えた twice or more 3, open 1 |
| retention by gap | 3–6 days 7 of 9; 7–13 days 10 of 10; 14+ days 4 of 4 |

What the learner wrote, by what the lesson did:

- **"In the review there was a question where it was unclear whether «svangur» or «svöng» was the answer."** The audio
  names the form before every gendered answer, and so did the lesson's own review questions. The bot's queue lost it:
  its wording refresh took a stored «As a woman: …» question for stale and wrote it again without the form, and a
  question kept as a whole sentence never had one. **Answered, in review:** every review question names the form its answer expects
  (#375; the owner: a voice that doesn't match is fine, the instruction must say which answer is expected).
- **"Choosing the right case after «með» and «án» is hard."** The four units («með sykri», «án sykurs», «með mjólk», «án
  mjólkur») were taught whole, and nothing said why the word changes; the practice after a milestone asked parts bare
  and could pair two «með». **Answered, in review:** a milestone names the two cases with the forms side by side, and the practice
  after any milestone contrasts its two examples, in sentences (#377).
- **No remark on the scene, its goal or the closing,** and no «repetitive» tick: the first of the three feedbacks for
  #365, #369, #370 and #371.

### 5.24 Lesson 34: the first feedback on #379–#384

Lesson 34 was generated with LLA `1c9ec29`, the bot at site_update_notifier `edc9128`. It is the first feedback on:
- the clothes shop (#372), whose level 1 it played;
- the allergy line's pattern «Ég er með ofnæmi fyrir {…}.» (#380): «hnetum» and «fiski» came in as its fillers;
- a phrase reported hard said whole, word by word and whole again (#337): «hringja heim», lesson 33's «sooner» item.

| | lesson 34 |
|---|---|
| length | 28.3 min, 117 exercises |
| new items; new components, weighted (target) | 12; 7.5 (7) |
| theme (level); today's new items said as a turn of the played exchange | the clothes shop (1); «húfu», «Það er of dýrt.», «Er afsláttur?» |
| target reached | 18.6 min |
| longest stretch without a scene | 5.0 min |
| a sentence asked again within a minute | 0 |
| most narrations of one situation | 3 |
| hard items with no connection to practise them through, asked 3+ times | none (lesson 33: «Ég er með ofnæmi fyrir hnetum.», 6 times) |
| feedback form: load; friction | **right**; other |
| «sooner» | none |
| review queue | **109 due** of 286: answered once 73, 迷った/言えなかった 22, new 10, never asked 3, 言えた twice or more 1 |
| retention by gap | 3–6 days 8 of 10; 7–13 days 13 of 13; 14+ days 4 of 4 |

What the learner wrote, by what the lesson did:

- **"The way «á þetta hótel» was taught was redundant."** «You know this: «Á þetta hótel, takk.» — This word is in it —
  In another sentence.» and then the same sentence: the only pattern that takes the part is the one the phrase was made
  from. **Answered, in review:** the other sentence is never the phrase the part is taken out of; with none, the part is
  taken out of the phrase as for «krónur» (#386).
- **"When «svangur» was the answer, it did not say to answer as a man."** The lesson named the form; the bot's stored
  question «Ég er svangur.» was kept with its pattern alone («Ég er {state}.»), so nothing told which form it expects.
  **Answered, in review:** the fillers of a pattern a question names decide its form too (#385); the bot rewrites its
  stored questions when its `REFINE_VERSION` is raised after the submodule carries it.
- **"Right after being told «hnetum» could be swapped, no swap came."** The pattern's introduction from a known example
  said «you can say it with other words», and the same sentence followed: no other filler was known yet. **Answered, in
  review:** the swap is promised only when one follows, else «You will meet them later.» (#388).
- **"After a pick-out and the line heard again, the switch to the next question always feels a little abrupt."** The
  pick-out ended on the partner's line, and the next drill's cue came after the usual gap. **Answered, in review:** a
  pick-out or catch that a drill follows ends with «Back to speaking.» (#387).
- **The shared cause of three:** a framing line said for the general case, without looking at what follows: «In
  another sentence» before the same sentence, «other words» before none, and a change of task with no line at all. The
  review's missing form is lesson 33's remark again, on the questions the bot had stored (§5.23).
- **No remark on the clothes shop, the allergy pattern's sentences or the slow «hringja heim»,** and no «repetitive»
  tick.

### 5.25 Lesson 35: the first feedback on #386, #387 and #394/#405

Lesson 35 was generated with LLA `abc1af2` (main with #392–#406), the bot at site_update_notifier `b8a0917`. It is the
first feedback on an embed's «other sentence» never being its own phrase (#386: «In another sentence» before «Ég verð að
borga með korti.»), «Back to speaking.» after a pick-out (#387, 4 times) and a transform's pair and instruction (#394, #405:
one transform, its instruction in full). The town's slower reply (#393) comes in lesson 38 on the replay.

| | lesson 35 |
|---|---|
| length | 29.5 min, 132 exercises |
| new items; new components, weighted (target) | 6; 7 (7) |
| theme (level); today's new items said as a turn of the played exchange | the clothes shop (2); «Má ég máta þetta?», «Hvar er mátunarklefinn?» |
| target reached | 15.2 min |
| longest stretch without a scene | 4.3 min |
| a sentence asked again within a minute | **2** (lesson 34: 0) |
| most narrations of one situation | **5**: the clothes shop's scene line (lesson 34: 3) |
| feedback form: load; friction | **light**; other |
| «sooner» | «Hvar er mátunarklefinn?», «Ég er södd.», «Ég er þyrst.» (to say) |

What the learner wrote, by what the lesson did:

- **"«Let's go back over today's new material», and then only part of it is covered."** The closing asked three of the
  six new items: the others had been said as often as a lesson allows. On the replay, lessons 35–37 all leave items out.
  **Answered, in review:** the announcement says «some of today's new material» when the built closing leaves a new item
  out (`meta.closing_left`, #407). The course-wide check of promising lines (#397) had listed the announcement as a line
  that promises nothing: the cause is the family of lesson 34, and the check's hole is closed with it.
- **"«latte» needs no slow, split pronunciation."** The sound rule reads letters (`tt`), so it split a loanword the learner
  already says; on the replay it would split «Tókýó» in lesson 37. **Answered, in review:** a loanword or a name said much
  as in English or Japanese is `sounds_familiar`, outside the rule (#407).
- **"«Hún er tólf» should do too" (the owner, outside the form).** It does: «hún» stands for «klukkan». Other answers
  existed only for fixed phrases. **Answered, in review:** a pattern's `alternatives` take its slots, the clock offers «Hún
  er {hour}.» after its sentence, and a note says why «hún» (#407). On the replay of lessons 35–40 the clock is asked once
  (lesson 37), so the note carries most of the answer.
- **No twenty-point remark, for the first time in the ledger** (lessons 24–35), and no remark on the fifteen changes merged
  the day before. Load «light» after three «right»: the target rises only after two in a row (§9 "Pace").
- **Done** (three feedbacks without their family): the town's first levels and the played level's goal and closing
  (#365, #369, #370, #371), the scene-matched rest (#329), the first contrast note (#323) and the hard items' connections
  (#330, #332).

### 5.26 Lesson 36: the first feedback on #407

Lesson 36 was generated with LLA `05490fe` (main with #407 and #408), the bot at site_update_notifier `535ddaa`. It is the
first feedback on the closing's announcement and the aside on «hún» (#407, the aside after a pick-out answered «klukkan
tíu»; the closing asked every new item, so it said «today's new material»), and on the dative place forms in their frames
(#368): «Ég er að leita að bankanum.», then «This word is in it: bankanum — You know it as: bankinn — This form comes after
leita að», then the sentence asked; «hótelinu» the same way. The lesson rebuilt from its export is identical.

| | lesson 36 |
|---|---|
| length | 29.5 min, 111 exercises |
| new items; new components, weighted (target) | 9; 8 (8: raised from 7 on recall, 2 of 27 new items failed over three lessons) |
| theme (level); today's new items said as a turn of the played exchange | the town (2); «bankanum», «Ég er að leita að …», «Er hægt að ganga þangað?» |
| target reached | 16.7 min |
| longest stretch without a scene | 4.1 min |
| a sentence asked again within a minute | 0 |
| most narrations of one situation | 4 |
| feedback form: load; friction | **light** (the second in a row); other |
| «sooner» | none |

What the learner wrote, by what the lesson did:

- **"A pick-out opens with «You want to know …», so I start building the question; only then comes «Listen and
  answer»."** All eight pick-outs opened with the need and named the task last («You want to know: When does the bank
  open? Listen and answer.»); elsewhere a cue that opens with what the learner wants is a speaking task («You want
  breakfast before the tour. Say: …»). **Answered, in review:** the cue says the action first, «Listen, then answer:
  When does it close?», «Listen for the price, then say it.» (#409: #411).
- **"«Your turn» sounded unnatural."** «Now the same form with another word. Your turn.», then the cue itself («In
  Icelandic, say: That isn't a waterfall.»): the turn given a line before its task. **Answered, in review:** «Your turn.»
  goes from the form model (#411). The cause of the two: a cue's first words do not say what the learner is to do.
- **"The same kind of situation is sometimes practised twice in a row (looking for something warm)."** Two pick-outs of
  the clothes shop's first level, 23 seconds apart, each with the scene line «You're in a clothes shop, looking for
  something warm.» and the same need; #273's spacing covers situations, not a theme's scene line. **Open:** #273,
  reopened.
- **No remark on the dative forms, the aside on «hún» or the closing.** Load «light» a second time: the target had already
  risen to 8 on recall; lesson 37's export shows what the rule did with the two answers.
- **The replay's pace:** the replay recomputes the pace and target every lesson without storing them, as `generate` does;
  on a replay that stores them, the played exchange stops holding new items in lesson 41 rather than 40 (#410).

---

### 5.27 Lesson 37: the first feedback on #411

Lesson 37 was generated with LLA `4261704` (main with #411–#414), the bot at site_update_notifier `0555fd5`; rebuilt from its
export it is identical. It is the first feedback on the cue that says the action first (#411: eight pick-outs, each opening
«Listen…»; the form model without «Your turn.») and on a loanword with no slow split («Tókýó», #407). Small talk 4 played with
a heard turn (#414) comes in lesson 40 on the replay.

| | lesson 37 |
|---|---|
| length | 29.1 min, 120 exercises |
| new items; new components, weighted (target) | 9; 8 (8) |
| theme (level); today's new items said as a turn of the played exchange | small talk (2); «Ég bý í Tókýó.», «Hvað gerir þú?», «Ég er kennari.» |
| target reached | 18.8 min |
| longest stretch without a scene | 4.1 min |
| a sentence asked again within a minute | 1 |
| most narrations of one situation | 4 |
| feedback form: load; friction | **light** (the third in a row); other |
| «sooner» | none |

What the learner wrote, by what the lesson did:

- **"The listening question always asks the time, and the time never changes; the other pick-outs have no variety
  either."** All eight pick-outs came from turns heard in the last three lessons, each one line with fixed values («Við
  stoppum hérna í tuttugu mínútur og förum svo klukkan hálf þrjú.» → «klukkan hálf þrjú»); the line's other piece
  («tuttugu mínútur») was never asked, its words not yet taught. The rotation worked on the turn; within it the line was
  drawn at random from one. On the replay of lessons 37–44, from lesson 38 4 to 10 pick-outs a lesson repeat a line and answer
  heard in the three lessons before. **Answered, in review:** each pick-out turn has lines with other values the learner can say,
  and within a turn the answer's value heard least recently comes first, then its line; on the replay of lessons
  37–44, a pick-out repeating a question and value of the three lessons before: 9 in all (main 56), and a line and
  answer: 5 (main 51); a turn never gives the same value on two draws in a row. The rest is turns with two to four values drawn
  every lesson (#339, reopened: #417).
- **"The «could you speak more slowly» dialogue has come back so often that I know it."** `tungumal`, played whole in
  lesson 37, its eighth play, every four lessons since it was played whole. **Open:** #416.
- **"After a conversation, the way back to speaking practice is sometimes unclear."** The café's first level heard again,
  then at once «Say: What do you do for a living?»; four such exits in lesson 37. #387 marked the way back after a pick-out
  only. **Open:** #415.
- **No remark on the cue's wording** (#409's remark, «You want to know …» read as a speaking task) or on «Tókýó».
  Load «light» a third time in a row.

### 5.28 Lesson 38: the first feedback on #417

Lesson 38 was generated with LLA `ef59bdd` (main with #417 and #418), the bot at site_update_notifier `edbf4c8`; rebuilt from its
export it says the same (the transcript's written pronunciation notes aside). It is the first feedback on pick-out lines with other
values (#417: ten pick-outs, drawn across values).

| | lesson 38 |
|---|---|
| length | 29.9 min, 109 exercises |
| new items; new components, weighted (target) | 9; 8 (8) |
| theme (level); today's new items said as a turn of the played exchange | the town (3); «Ég er týnd.», «Hvar er veitingastaðurinn?», «Til hægri?», «Hvað er langt þangað?», «Geturðu sýnt mér á kortinu?» |
| target reached | 14.5 min |
| longest stretch without a scene | 4.5 min |
| a sentence asked again within a minute | 1 |
| most narrations of one situation | 4 |
| feedback form: load; friction | **light** (the fourth in a row); other |
| «sooner» | none |

What the learner wrote, by what the lesson did:

- **"In the conversations I say «Nei, takk.» and «Takk.» so many times: I am made to say them too often."** Seven asks of
  four set replies, five of them in the supermarket's and café's levels heard again, two in the town's two plays; on the replay
  of lessons 38–44, 34. Every sayable line was asked (#263). **Answered (#422):** in an exchange played again, a named set reply
  the learner plainly knows is voiced, not asked, and the opening says so; on the replay, 34 asks fall to 5, each in the first
  play of the day's exchange. A limited exception to "sayable → asked" (§9).
- **"In the closing part that covers today's new material, a listening question started: it felt nested."** At 28:42 a
  clothes-shop pick-out inside the closing, put there by the rule that breaks long runs. **Open:** #421.
- **"«Mér finnst gaman að hringja heim» (I like calling home): does it mean I like talking to my parents?"** The meaning
  leaves open whom one calls. **Open:** #209 (the authored line and its meaning, with a fluent speaker).
- **No remark on the pick-outs' answers** (lesson 37's remark that the time never changed). Load «light» a fourth time.

### 5.29 Lesson 39: the first feedback on #422

Lesson 39 was generated with LLA `5b822c2` (main with #422), the bot at site_update_notifier `68036e1`; rebuilt from its export it
says the same (the written notes aside). It is the first feedback on set replies voiced in exchanges played again (#422: four
voiced, «Takk.», «Já, takk.» twice and «Takk kærlega.», none asked there) and the second on #417's pick-outs (ten, with one catch).

| | lesson 39 |
|---|---|
| length | 30.1 min, 115 exercises |
| new items; new components, weighted (target) | 5; 9 (9) |
| theme (level); today's new items said as a turn of the played exchange | small talk (3); «Ert þú íslensk?», «Ég er japönsk.», «Ég er í vinnuferð.», «Ég vinn hjá litlu fyrirtæki.» |
| target reached | 15.6 min |
| longest stretch without a scene | 4.5 min |
| a sentence asked again within a minute | 0 |
| most narrations of one situation | 7 |
| feedback form: load; friction | **light** (the fifth in a row); other |
| «sooner» | «Ég vinn hjá litlu fyrirtæki.», reason: hard to hear |

What the learner wrote, by what the lesson did:

- **"At the end of a conversation part, where I expect more of the same kind of question, a question of another kind comes
  abruptly."** At 25:13 small talk 3 ends «Gaman að heyra það.» and at 26:06 «The directions are getting long. Hand over your
  map…» follows; 11 of the lesson's 12 conversations were followed by a drill with no line between. Lesson 37's remark again
  (#415). **Answered (#425):** a conversation that a drill follows ends with «That's the end of the conversation.», built into
  the lesson's time (about 30 minutes on the replay).
- **"In the written review, every audio-check message I have not dismissed follows the review's progress."** The 🔊 reply held
  only `reading.mp3`; Discord's preview of the review message shows the card on screen now. **Answered
  (site_update_notifier#176):** each reply names its card and the text spoken, fixed when 🔊 is pressed; to be confirmed on Discord.
- **«Ég vinn hjá litlu fyrirtæki.» was hard to hear.** Its next practice opens with the retry cue of #424 («Let's try to say this
  sentence in Icelandic again: …»), its first real case.
- **No remark on set replies** (#422's first feedback) **or on the pick-outs.** Load «light» a fifth time.

### 5.30 Lesson 40: the first feedback on #424, #425 and site_update_notifier#176

Lesson 40 was generated with LLA `2d9c671` (main with #424 and #425), the bot at site_update_notifier `379104c` (with #176);
rebuilt from its export it is identical (102 exercises, 29.5 minutes). It is the first feedback on the line that ends a
conversation (#425: «That's the end of the conversation.» eight times), on the retry cue (#424: «Ég vinn hjá litlu
fyrirtæki.», reported hard after lesson 39) and on the review's 🔊 replies named by card (site_update_notifier#176), and the
second on set replies voiced in exchanges played again (#422). Small talk's fourth level was the day's exchange. The owner's
notes on the transcript, sent with the feedback, count as remarks of this round.

| | lesson 40 |
|---|---|
| length | 29.5 min, 102 exercises |
| new items; new components, weighted (target) | 8; 11 (10) |
| theme (level); today's new items said as a turn of the played exchange | small talk (4); «Hvað ertu gömul?», «Ég er tuttugu ára.», «Ég er giftur.» |
| target reached | 17.6 min |
| longest stretch without a scene | 4.2 min |
| a sentence asked again within a minute | 2 |
| most narrations of one situation | 8 |
| feedback form: load; friction | **right** (after five «light»); other |
| «sooner» | none |

What the learner wrote, and what the owner found in the transcript and asked for, by what the lesson did:

- **"Is it normal in Iceland to ask someone's age out of the blue, or to introduce yourself as single and living alone?"**
  Small talk 4 opened «Someone sits down next to you and says hello.», then «Ask how old she is.», and the partner went on
  «Ég er einhleyp og bý ein. En þú?». The scene check reads generated sentences; nothing read an authored level's order.
  **Answered (#433):** the level opens with «Ég á afmæli í dag!», so the age has a reason, and the partner's line
  before «Ég er gift.» is her own marriage, in words the learner knows: «Ég er gift. En þú?».
- **The owner: a cue its answer does not answer, and a partner's reply in the wrong form.** «She asks if you're here with
  your family. Say you're married.» («Ég er gift» does not say whether you came with your family), and «Velkomin!», the
  woman's form, said twice in `kynning` to the learner's line in a man's voice. **Answered (#433):** the cue asks
  whether you're married; «Velkomin!» after the learner's own line becomes «Frábært!». A `validate` rule for gendered partner
  replies is not built.
- **The owner: a conversation played from its middle opens on a line that needs what came before.** In lesson 40 a catch on
  small talk's closing line followed with no scene named; on the replay of the export, a hard item's scene line opens on «Nú
  já! Hvar vinnur þú?» with nothing for «Oh, I see!» to answer. **Answered (#433):** every listening task opens with
  its scene line, and a scene line cut from the middle leads in with the learner's line its partner answers.
- **The owner: «Thank her.» → «Takk.» and «Say: no, thanks.» → «Nei, takk.» are still asked as tasks** in the authored
  dialogues (exercises 12 and 28), and familiar dialogues are still played whole. #422 voiced known set replies in theme
  exchanges only; lesson 38's remark recurs in another play mode. **Answered after the lesson:** authored dialogues voice them
  too (#430), and a fixed dialogue played whole four times is not played whole again (#431). #416 keeps what is left.
- **The owner: a listening question asks what the conversation just said.** The tour's first level, heard again at 22:52,
  says «Hér stoppum við í tuttugu mínútur.»; the pick-out at 23:27 asks «How long do we stop?». **Open:** #339, with #273.
- **The owner asked for optional help apart from the review's outcomes:** pronunciation or grammar help on the expressions the
  learner chooses, with no failure and no extra practice (pronunciation: «einhleyp», «afsláttur»). Nothing is explained where it
  is not needed: «tuttugu» is comfortable, and the age pattern is plain. **In review (site_update_notifier#180):** a request button
  on the feedback form, for pronunciation and grammar, outcome and load unchanged; the same during the review's recall check,
  and kinds for listening and use, are left.
- **The owner's ideas, as issues:** the learner's own name and age in lessons and the review (#428); instructions moved to
  Icelandic gradually, from two commands (#429).
- **No remark on the way back from a conversation** (#425's first feedback; lessons 37 and 39 remarked it) **or on the
  review's 🔊 replies** (site_update_notifier#176). Lesson 40's closing held no listening task (#421; on the replay, lesson 44
  does). Load «right» after five «light»; the ledger does not count the lesson settled (one twenty-point remark, four new
  families).

### 5.31 Lesson 41: the first feedback on #430, #432, #433 and #435–#437

Lesson 41 was generated with LLA `2df0e37` (main with #430–#437), the bot at site_update_notifier `c72150b` (with #180 and #183);
rebuilt from its export it is identical (127 exercises, 29.5 minutes). It is the first feedback on known replies voiced in an
authored dialogue (#430), the batch for lessons 41–50 (#432: arranging to meet), every listening task naming its scene (#433), the
closing as one block (#435, #437) and no pick-out on an answer just heard (#436).

| | lesson 41 |
|---|---|
| length | 29.5 min, 127 exercises |
| new items; new components, weighted (target) | 10; 10 (10) |
| theme (level); today's new items said as a turn of the played exchange | arranging to meet (1); «Ég fer á morgun.», «Það hentar vel.» |
| target reached | 16.1 min (3.8 min after it serving neither a target expression nor a scene) |
| longest stretch without a scene | 4.2 min |
| a sentence asked again within a minute | 1 |
| most narrations of one situation | 4 |
| feedback form: load; friction | **light** (after «right» in lesson 40); other |
| «sooner» | «lögreglustöðin», reason: hard to hear |

What the learner wrote, by what the lesson did:

- **"The four combinations of kem/fer and í kvöld/á morgun are mere substitutions: as learning, the four together feel very
  light."** `á morgun`, `í kvöld`, «Ég fer {time}.» and «Ég kem {time}.» cost 3 weighted components (1 + 0 + 1 + 1), and got 19
  exercises and 20 model answers on four sentences («Ég fer á morgun.» 6, «Ég fer í kvöld.» 4, «Ég kem á morgun.» 5, «Ég kem í
  kvöld.» 5): each item ran its own ladder although one sentence practises two of them, and two time words make only four
  sentences. **Open:** #439 (practice shared across the items a sentence says; not a change of the components' weights).
- **"The guide that simple replies are played, not asked, is repeated too often."** «Short replies like yes, no and thanks are
  played for you.» at 02:00, 17:38 and 21:13, about 19 s. Not a recurrence of lesson 38's remark: the replies voiced stay voiced.
  **Answered, in review (#440):** the guide once a lesson, then «The conversation again.».
- **The closing held nothing but today's new material** (nine recalls), and no pick-out asked an answer heard in the five minutes
  before (nine pick-outs and catches). The stretch before the closing was 17 recalls of known material, with no listening task
  (#437 found none to give there): the 3.8 minutes after the target that serve neither a target expression nor a scene.
- **«lögreglustöðin» hard to hear:** a «sooner» report; listening help apart from the review is site_update_notifier#179's.
  Load «light» after one «right»: H9's rule does not raise the pace on one rating.

### 5.32 Lesson 42: the first feedback on #440 and #448

Lesson 42 was generated with LLA `90122e1` (main with #442, #447 and #448), the bot at site_update_notifier `b74ccf3`; rebuilt
from its export it is the same (129 exercises, 29.4 minutes; the written notes aside). It is the first feedback on the voiced-reply
guide said once a lesson (#440: once, then «The conversation again.» three times) and on the goal narrowed to the lines the exchange
asks (#448: «Say you'll come this evening and say see you this evening. Listen for how to say you can't tomorrow.»). #442 had no
pattern taught with its filler to share practice across, and #447 had no report with its reason yet.

| | lesson 42 |
|---|---|
| length | 29.4 min, 129 exercises |
| new items; new components, weighted (target) | 10; 9 (9, lowered from 10: 53 items due against about 64 review slots) |
| theme (level); today's new items said as a turn of the played exchange | arranging to meet (2); none (2 of 10 in the played scene) |
| target reached | 19.3 min |
| longest stretch without a scene | 4.4 min |
| a sentence asked again within a minute | 1 |
| most narrations of one situation | 4 |
| confirmed recall by gap, 3–6 / 7–13 / 14+ days | 28/30 · 39/43 · 9/9 |
| feedback form: load; friction | **light** (a second time, after lesson 41); other |
| «sooner» | «regnhlíf», reason: hard to say |

What the learner wrote, by what the lesson did:

- **"Still odd to talk about marriage and age with another customer at a café, out of the blue."** Small talk 4 heard again at 24:40:
  «Someone sits down next to you and says hello.», a stranger's birthday, her age, then «Ég er ekki gift. En þú?». #433 had made
  «En þú?» ask the right thing, and the birthday gave the age a reason; nothing gave marriage one, and the scene line named no one
  the learner knew. A recurrence of lesson 40's remark (§5.30), so the lesson is not settled. **Answered, in review (#458, a data PR):**
  a coffee with Anna, the friend made at the guesthouse, said by the level's own scene line; her birthday leads to «Til hamingju! Hvað
  ertu gömul?», her remark on your ring to «Takk! Ég er gift.», and the level ends on «Skál!». On the replay of the export the
  level is heard whole in lessons 44 and 46, every line with its reason.
- **«regnhlíf», hard to say:** the request was saved and nothing could model it: no authored split, none of the sound rules, a single
  word. The replay shows two earlier requests dropped the same way, «vatnsglas» and «versla». **Answered, in review (#459, #457):** a
  one-word item reported hard is its own word, and «regnhlíf» is split («regn · hlíf»); on the replay lesson 43 plays it.
- **The owner's review of the export.**
  - A catch line answered something never heard: «You're in town.» → «Frábært. En pósthúsið?» (07:33). Open in #427.
  - The day's new material was not what the played exchange lets the learner do: directions, the umbrella and being late around an
    exchange about this evening (#327). On the replay from current main, today's new items said as a turn are 0, 3, 1, 0, 0, 2 in lessons
    42–47.
  - Easy substitutions still take many answers: «Ertu með regnhlíf?» 9 model answers, «Ég er sein/seinn.» 5 + 5 (#439, read again after #442).
- Load «light» a second time. Two «light» ratings raise the target by H9's rule when the window's failures are at most 25% and the
  review backlog is small (fewer due than half the review slots). The failures hold (2 of 29); the backlog does not: on the replay
  with lesson 42 rated «light», 47 items are due against about 64 slots before lesson 43, so its target stays at 9.

### 5.33 Lesson 43: the first feedback on #455, #458 and #459

Lesson 43 was generated with LLA `a466b6e` (main with #455 and #458–#460), the bot at site_update_notifier `42d9676`; rebuilt from its
export with the trip profile it is the same (115 exercises, 29.4 minutes; the written notes aside). It is the first feedback on the
«Listen.» way in (#455: once), a level's own scene line (#458: the coach ride's) and a word asked for always modelled (#459: «vatnsglas»
and «versla», dropped before, modelled). «Takk og bless!» (#450) is among its new items.

| | lesson 43 |
|---|---|
| length | 29.4 min, 115 exercises |
| new items; new components, weighted (target) | 11; 9 (9) |
| theme (level); today's new items said as a turn of the played exchange | small talk (5, the coach ride); «Ég bý í Ósaka.», «Hvar býrð þú?», «læknir» |
| longest stretch without a scene | 4.2 min |
| pick-outs heard in the last three lessons | 10 of 11 |
| feedback form: load; friction | **right** (after «light» in 41 and 42); other, unclear |
| «sooner» | «bílastæðið», «langt í burtu»; reasons: hard to hear, hard to remember |

What the learner wrote, by what the lesson did (the learner's remarks; the reviewer's measurements and diagnoses after them, labelled):

- **"«Same change» is said again and again with gaps in between; that it means «turn ég into hún» is too high-context."**
  *Reviewer:* «Say it about her:» in full twice (15:19, 16:18), then «Same change:» six times between other tasks, once more than four
  minutes after the last transform. The builder said it whenever the transform asked last had the same instruction (#405): G12 again,
  information cut that the learner needed. **Answered, in review (#463, #461):** «Same change:» only right after the same transform.
- **"The audio of «Ask where she lives.» is broken and cuts off midway."** *Reviewer:* the transcript has the full text three times
  (04:11, 23:15, 24:02), one cached clip; the export holds no audio. **Open (#462):** the clip is checked on the server, regenerated if
  cut off; a guard only once the failure is known.
- **"«hef komið» and «hingað» were never explained; one place asks only the answer, with no translation."** *Reviewer:* the coach ride
  asks «Hefurðu komið hingað áður?», translated in the first play, not in the late one (24:02); its reply «Ég hef verið hér áður.» is
  known, so the level is ready, and nothing asks whether the question is understood. **Answered in part, in review (#464, a data PR):**
  one note sets «komið hingað» against «verið hér», after the coach ride; the general check is #327's, with #265.
- *Reviewer:* the scene coherence improves to three of today's new items said as a turn; the replay from current main reads 1, 0, 0 in
  lessons 44–46 (#327). Ten of eleven pick-outs had been heard in the three lessons before (#339, with #451).
- Load «right» after two «light», with no remark on repetition: evidence against changing the components' weights (#439, kept for
  selective cases). One «right» does not settle the pace.

### 5.34 Lesson 44: the first feedback on #464 and #466

Lesson 44 was generated with LLA `122b7a1` (main with #463, #464, #466 and #467), the bot at site_update_notifier `1a85272`; rebuilt from
its export with the trip profile it is identical (106 exercises, 29.5 minutes). It is the first feedback on the aside that sets «komið
hingað» against «verið hér» (#464, before the coach ride's question) and on the guard against cut-off clips (#466, #467: «Ask where she
lives.» three times). No transform was asked, so «Same change:» (#463) is not heard yet. The owner's notes on the transcript, and on
lesson 45 as generated from this export, count as remarks of this round.

| | lesson 44 |
|---|---|
| length | 29.5 min, 106 exercises |
| new items; new components, weighted (target) | 11; 10 (9) |
| theme (level); today's new items said as a turn of the played exchange | arranging to meet (3, the late call); «Ég kem eftir tíu mínútur.» |
| target reached | 17.5 min |
| longest stretch without a scene | 4.4 min |
| a sentence asked again within a minute | 2 |
| pick-outs heard in the last three lessons | 4 of 4 |
| feedback form: load; friction | **right** (a second time); other |
| «sooner» | «á horninu», «hinum megin við götuna», «alltaf», «stundum», «aldrei»; reason: hard to remember |

What the learner wrote, and what the owner found and asked for, by what the lesson did:

- **"When the part that says a hard word piece by piece began, it did not say which word («regnhlíf»)."** The slow model opened
  «This word is hard to say.» and went to the pieces. The owner's flow: the word asked from its meaning, the answer, then the
  breakdown. **Answered (#468):** «Do you remember how to say this? An umbrella.», an answer pause, «regnhlíf», «Let's break down the
  pronunciation. Repeat each part.», the pieces and natural speed.
- **"The four-word expression new as one («hinum megin við götuna») was not practised enough"**, and the owner asked why it was not
  practised piece by piece. *Replay:* introduced at 03:48, then asked twice; its rungs after the first were dropped, because the bare cap
  counted its own sentence as said alone and no other sentence holds it; and a part introduced inside its sentence had no build-up.
  **Answered (#469):** a part that one frame alone holds keeps its four rungs (5 asks in all on the replay), and a part of three words
  or more is built up from its end. Cost: on the replay generated sentences go 18 → 7 and situations 19 → 10 in lesson 44; lesson 45 as
  generated from main after this round reviews 27 of its 53 due items (19 carried over), against 47 before it, the three build-ups and
  the café's new phrase included. The review backlog (§5.32) grows by them.
- **The owner: «Ask if she …» is answered «Ert þú …», not «Er hún …».** 53 cues asked a person with no one named after «ask», and the
  same wording served a real third-person question («Ask what her name is.» → «Hvað heitir hún?»). **Answered (#470):** «Ask her if
  she's Icelandic.», «Ask the receptionist if …», «Ask what the girl is called.»; `validate` fails a cue that asks a person with no one
  named.
- **The owner on the scenes:** the café server warned of nuts unprompted and answered an allergy with «Ekkert mál» (**answered, #471:**
  the learner asks «Get ég fengið köku án hnetna?» and says why); the late call opened with the theme's «Anna … wants to meet again.»,
  so the cue had to say that the meeting was arranged and that you were late (**answered, #475:** its own scene line).
- **The owner on lesson 45 as generated:** a conversation followed by another had no end line and the next opened «Now a short
  conversation.» (**answered, #473:** «Now another short conversation.»; #415's rule kept); a scene line opened with the learner's
  «Já, ég hef verið hér áður.» before any question (**answered, #472:** #427's lead-in comes after the question it answers); and
  «In a sentence.» named nothing once every part is asked through a sentence (**answered, #474:** the plain meaning cue).
- **The owner: «Ég er …», «Ég er ekki …», «Ertu …» bring nothing extra**, no gender and no other case. A task for later, recorded on
  #439 with #270.
- Load «right» a second time. The ledger counts the lesson settled: its twenty-point remarks are of two new families (`part-ladder`,
  `cue-addressee`). The owner classed #468 and #469 as bug fixes, not behaviour changes; with #470, #472–#474 lesson 45 will be the
  first built with six behaviour PRs, past the advisory two (§9 "Governance").

### 5.35 Lesson 45: the first feedback on #469, #471, #474 and #475

Lesson 45 was generated with LLA `fc0b69c` (main with #468–#476), the bot at site_update_notifier `f18c7c6`; rebuilt from its export with
the trip profile it is identical (117 exercises, 29.0 minutes). It is the first feedback on a part's rungs kept and a long part built up
from its end (#469: «við hliðina á bankanum», «fyrir framan hótelið»), the café's new request (#471, played twice), a part's generated
sentence cued by its meaning (#474: nine times, «Use it in a sentence.» once) and the late call's own scene line (#475). #468, #470,
#472 and #473 had nothing to play. It is the first lesson built with six behaviour PRs (§9 "Governance"; the owner classed #468 and #469 as
bug fixes).

| | lesson 45 |
|---|---|
| length | 29.0 min, 117 exercises |
| new items; new components, weighted (target) | 12; 9 (9) |
| theme (level); today's new items said as a turn of the played exchange | café (4); «Get ég fengið köku án hnetna?» |
| target reached | 21.2 min |
| due reviews asked / carried over | 19 / 23 of 48 |
| longest stretch without a scene | 4.3 min |
| a sentence asked again within a minute | 0 |
| feedback form: load; friction | **light** (after «right» in 43 and 44); none |
| «sooner» | «við hliðina á bankanum», «hinum megin við götuna»; reasons: hard to remember, hard to say |

What the learner wrote, and what the owner found and asked for, by what the lesson did:

- **No remark, load «light».** *Reviewer:* the lesson asked 19 of its 48 due reviews and carried 23 over (the written review's queue
  has 128 due), while today's new sentences came back four to six times: «Get ég fengið köku án hnetna?» 6, the two long parts 4 each
  after their introduction. The pace rule lowers the next target (9 → 8) after such a lesson; inside it, every new item kept its four
  rungs. **Answered, in review (#478):** when the due reviews cannot fit, each new item gives up its second rung; on the replay 34 of 48
  reviewed, 10 carried over, each new item asked at most once less.
- **«við hliðina á bankanum» and «hinum megin við götuna», hard to remember and to say**, after #469 gave them four rungs and a
  build-up: more asks in one lesson did not make them stick. The «say» reason owes the sentence's retry from its meaning, word by
  word (#424), in lesson 46: its first real case for a part. Read next-day recall before adding practice.
- **The owner: after «Það tekur svona tíu mínútur.» the time is «svona tíu mínútur», not «tíu mínútur».** The pick-out's answer was the
  bare value; «svona» was not a word the learner knew, and the answer would have been most of the line. **Answered, in review (#477, a
  data PR):** «svona tíu mínútur» is a duration filler of its own, and the town's duration lines answer with it.
- No remark on the build-ups, the café scene or the cues (#469, #471, #474, #475, first heard). The ledger counts the lesson settled.

### 5.36 Lesson 46: the first feedback on #478 and #480

Lesson 46 was generated with LLA `1cf6716` (main with #477–#480), the bot at site_update_notifier `15e4975`; rebuilt from its export with
the trip profile it is identical (132 exercises, 29.9 minutes). It is the first feedback on the due reviews keeping their time when they
cannot fit (#478) and on a part reported hard tried as its sentence, then built up from its end (#480: «hinum megin við götuna», «við
hliðina á bankanum»). «svona tíu mínútur» (#477) was introduced as a new item and asked twice from its meaning; no pick-out played on it.
It is the first lesson built with two behaviour PRs (#478, #480).

| | lesson 46 |
|---|---|
| length | 29.9 min, 132 exercises |
| new items; new components, weighted (target) | 10; 8 (8) |
| theme (level); today's new items said as a turn of the played exchange | town (4); 0 |
| target reached | 19.2 min |
| items reviewed / due | 42 / 64 (lesson 45: 19 / 48); each new item gave up its middle rung (#478) |
| recall confirmed by gap, 3–6 / 7–13 / 14+ days | 29/31, 42/46, 9/9 |
| written review's queue | 130 due |
| longest stretch without a scene | 4.2 min |
| a sentence asked again within a minute | 0 |
| feedback form: load; friction | **light** (after «light» in 45); other (the note below) |
| «sooner» | «Til að taka með, takk.», «Mér finnst leiðinlegt að …»; reason: hard to remember |

What the learner wrote, by what the lesson did:

- **The grammar note on «heitur pottur» / «heiti potturinn» is careful, but recognising it by ear takes effort: «ur», «pottur», «inn»,
  «urinn», «potturinn» play in a row at one even gap.** *Reviewer:* the note's text is fine; its pieces (#198: #323) were five fragments
  at a 0.4 s gap, with no task and no word of what each group builds, while every other piece-by-piece model in a lesson asks the learner
  to repeat each part and ends on the whole at natural speed (`_slow_model`). **Answered, in review (#481):** a note's pieces follow
  that convention, and each group is led by what it builds («First a hot tub, from its end.»); the note is 32 s longer, and the replay
  loses two exercises.
- **Two older lines, hard to remember:** «Til að taka með, takk.» (last asked in lesson 34) and «Mér finnst leiðinlegt að …» (lessons 39
  and 41). Both were recalled at a long gap for the first time; the «sooner» report already brings them back at half their interval.
- **Another learner (15-minute lessons), after their lesson 26: the same conversation comes lesson after lesson, «skyr» in the fridge and
  «… costs 500 kr» every time; they ask for other things.** It reached us through the feedback sync (site_update_notifier#197). Their
  records: the supermarket's first level was heard again in 19 of their lessons 11–30, and its price pick-out, about skyr and milk only,
  in 8 of 11 lessons from 20. A level heard again (#218 b1) rests only within a lesson, and a path with few levels done draws the same
  ones every lesson; the owner's path, with 27 levels, does not show it. **Open (#483):** a level heard again rests across lessons, and
  the supermarket's lines name other things (#336).
- **No remark on the reviews (#478) or on the two long parts (#480).** The lesson reviewed 42 items, rated «light». Both long parts were
  tried as their sentence and built up from their end (02:50, 04:07) and asked again at 06:27 and 28:01. Their next-day recall is the
  read. The ledger does not count the lesson settled: the other learner's remark is a twenty-point part (#483).

### 5.37 Lesson 47: the first lesson built with #481

Lesson 47 was generated with LLA `127f73d` (main with #481 and #482), the bot at site_update_notifier `1459026`; rebuilt from its export with
the trip profile it is identical (125 exercises, 29.9 minutes). It is the first lesson built with #481 (a grammar note's pieces led and
repeated); neither note with pieces played, so #481 has had no feedback yet. It is the first lesson whose feedback arrived through the
feedback sync (site_update_notifier#197), with no manual export.

| | lesson 47 |
|---|---|
| length | 29.9 min, 125 exercises |
| new items; new components, weighted (target) | 6; 8 (8) |
| theme (level); today's new items said as a turn of the played exchange | town (5); 0 |
| target reached | 18.6 min |
| items reviewed / due | 57 / 73 (lesson 46: 42 / 64); the capacity estimate did not trigger the rung reduction (#478) |
| written review's queue | 125 due |
| longest stretch without a scene | 4.2 min |
| a sentence asked again within a minute | 0 |
| feedback form: load; friction | **light** (the third in a row); other (the remark below) |
| «sooner» | none |

What the learner wrote, by what the lesson did:

- **«kem» / «að koma» and «rigning» / «rignir» are hard to tell apart from the English.** *Reviewer:* the cues gave two answers one
  meaning. «It's raining.» asked for «Það rignir.» in lesson 46 and for the weather pattern's «Það er rigning.» in lesson 47 (`rigning`
  glossed «raining»); «Shout that you're coming.» asked for «Ég er að koma!» and «I'm coming now.» / «I'm coming later.» for «Ég kem …».
  No check read the meanings against each other (the meaning-gloss family, after «hringja heim» in lesson 38). **Answered (#484, merged):**
  `validate` fails for a cue meaning, written or spoken, in any of the file's languages, that two different sentences share. It found nine
  on `main`, and each is told apart: «It's rainy.», «I'll come later.» (and no «Ég kem núna.»), «Do you have an umbrella with you?», «私は寒い
  です。», «私は暑いです。», «…を見てみたいです。», and the six dative place forms spoken «the airport, as after to or for». On the replay of
  the export the lesson keeps its length and asks «It's rainy.» and «I'll come later.».
- **No remark on the reviews.** The lesson reviewed 57 of 73 due, rated «light». The capacity estimate did not trigger the rung
  reduction (#478, `reviews_starved` false); why the other 16 were not reviewed is not established. The written review's queue is 125 due.

### 5.38 Lesson 48: the first feedback on #484

Lesson 48 was generated with LLA `588c646` (main with #484), the bot at site_update_notifier `4f970b6`; rebuilt from its export with the trip
profile it is identical (123 exercises, 30.0 minutes). It is the first feedback on two answers never sharing a cue meaning (#484): «I'll come
soon.» asked for «Ég kem fljótlega.» and «Tell her it's raining.» for «Það rignir.», with no remark. #486 (the levels heard again take turns)
and #487 (the supermarket's other items) were merged after it was built.

| | lesson 48 |
|---|---|
| length | 30.0 min, 123 exercises |
| new items; new components, weighted | 9; 7 |
| theme (level); today's new items said as a turn of the played exchange | weather (1); «Hvernig verður veðrið á morgun?» |
| target reached | 20.2 min |
| items reviewed / due | 42 / 47 (lesson 47: 57 / 73); the capacity estimate did not trigger the rung reduction (#478) |
| written review's queue | 125 due |
| longest stretch without a scene | 4.3 min |
| a sentence asked again within a minute | 0 |
| feedback form: load; friction | **light** (the fourth in a row); other (the remark below) |
| «sooner» | «Hvernig verður veðrið á morgun?»; reasons: hard to remember, to hear and to say |
| help asked | how «ð» sounds in it, when it is heard and when it fades, and how it links to its neighbours |

What the learner wrote, by what the lesson did:

- **The goal at the start runs together and is hard to follow.** *Reviewer:* the goal was one narration of three sentences,
  «Today's goal: Ask about tomorrow's weather and say you need an umbrella. Listen for how to say the weather is good today.», the second
  and third each naming a part of the exchange. A note's prose is said sentence by sentence with a beat between them (#259); the goal,
  said in every lesson with a theme, was not. **Answered, in review (#488):** the goal is said sentence by sentence, a beat between them,
  in both languages; the narrowed goal said again keeps them. The replay is otherwise identical.
- **«Hvernig verður veðrið á morgun?», hard to remember, hear and say**, with a help request on «ð». It was introduced built up from its end
  and said as a turn of the played exchange, the first lesson since 45 to say a new item as one. The «sooner» report brings it back at
  half its interval, and the help request is answered by the bot's explanation. Read its next-day recall before adding practice.

### 5.39 Lesson 49: the first lesson built with #486 and #488

Lesson 49 was generated with LLA `9bace0d` (main with #486–#489), the bot at site_update_notifier `4347129`. Rebuilt from its export with the
trip profile it is identical (107 exercises, 29.5 minutes). It is the first lesson built with:
- the levels heard again taking turns (#486);
- the supermarket's third level, for lamb, and its other price lines (#487, data);
- the goal said sentence by sentence (#488).

The learner state held no record of when a level was last heard before this lesson, so #486's turns read from lesson 50 on. Lesson 49 heard
small talk 5 and town 4 again, as lesson 47 had. The goal, one sentence after «Today's goal:», drew no remark. No note with pieces played (#481).

| | lesson 49 |
|---|---|
| length | 29.5 min, 107 exercises |
| new items; new components, weighted (target) | 12; 7 (7) |
| theme (level); today's new items said as a turn of the played exchange | supermarket (3); 0 |
| target reached | 21.2 min |
| items reviewed / due | 27 / 43 (lesson 48: 42 / 47); the capacity estimate did not trigger the rung reduction (#478) |
| recall confirmed by gap, 3–6 / 7–13 / 14+ days | 32/34, 44/49, 11/12 |
| written review's queue | 125 due |
| longest stretch without a scene | 4.2 min |
| a sentence asked again within a minute | 2 |
| feedback form: load; friction | **light** (the fifth in a row); other (the note below) |
| «sooner» | «í fyrramálið»; no reason given |

What the learner wrote, by what the lesson did:

- **«fyrramálið» could have had syllable-by-syllable practice; the fine pronunciation practice of numbers was not needed; numbers asked
  the same way as other words feels wrong.**
  - *Reviewer, the numbers:* once the trip ordering ran out (181 of its 182 items met), the course order reached the numbers module.
    Lessons 47–49 introduced nine numbers as words: 40 and 50; 13, 14, 15 and 16; «fimmtán hundruð», «tvö þúsund» and «þrjú þúsund krónur».
    Each got the introduction, «Say: …» recalls and recombination («Ertu fimmtíu ára?»). Number exercises went from 5–13 a lesson in
    41–46 to 19, 19 and 22.
  - *Reviewer, the easy items:* the new items with no new word (component cost 0) took 308 s together: «Veðrið er gott í dag.» 105 s,
    «í dag» 63 s, the two prices 62 and 57 s, «fimmtán» 21 s. Each item with a new word took 58–88 s.
  - *Reviewer, the hard word:* «fyrramálið», a four-syllable compound inside a two-word item, took 58 s, word by word with no split. The
    hard-word rule reads one-word items only.
  - *The owner, on the cause:* a plain number needs no word's practice, «you learnt 50, now use 50 in another sentence» included. What is
    hard to retain, a hard concept, an idiom or a compound earns repetition from several sides. The forms of 1–4, and of the numbers ending
    in 1–4 («tuttugu og einn / ein / eitt»), are the reverse: their practice is short. The learner has each form through one frame
    (counting, prices and hours, tickets, living alone). No exercise asks for the form a noun's gender and case choose, and the feminine
    «tvær», «þrjár», «fjórar» have not come.
  - *The owner's lead of lessons 44/45 is the same cause:* substitutions that teach no gender or case. Lesson 41's «only substitution» is
    too. Ranked «later» then, it is now the first item of «Now».
  - **Open (#439, rewritten):** practice follows what is hard in an item, not its kind, in steps. Step 1 is numbers: plain ones introduced
    in the expression that needs them, with no ladder of their own; the forms of 1–4 practised as the choice a noun's gender and case make.
    Then adjective gender, then case through #270's frames, then the hard side (a compound inside a phrase split by its parts). #451 now
    keeps the larger numbers to the ear. No local fix was made for «fyrramálið» (owner).
- **«Hvernig verður veðrið á morgun?» was played slowly twice** (the owner, after the lesson). Lesson 48's report gave three reasons: hard
  to remember, to hear and to say. «say» owed the slow model and «hear» the listening support, and each played its own exercise (03:16 and
  04:00). Both said the sentence, word by word and at natural speed. **Answered, in review (#490):** a slow model that already plays the line
  by ear settles the listening support too. On the replay of the export the lesson drops the second exercise and fits two others (109
  exercises, 29.3 minutes). A single word reported both ways keeps both, since its listening support finds it in a sentence.
- **No remark on the reviews.** The lesson reviewed 27 of its 43 due items, rated «light». The capacity estimate did not trigger the rung
  reduction (#478), while the items with no new word took five minutes.
- **Another learner's lessons 29 and 30** were built before #486 and #487, rated «light», with no remark. Their lesson 31, built with
  `588c646`, has no feedback yet.

### 5.40 Lesson 50: the first lesson built with #490 and #492–#496

Lesson 50 was generated with LLA `ffaac54` (main with #490–#496), the bot at site_update_notifier `5479f96`. Rebuilt from its export with the trip
profile it is identical (120 exercises, 29.7 minutes). Before it was played, the owner reviewed a draft of it from main `13f3a71` and the lesson-49
record; the remarks are lesson 49's round in the ledger, and three were answered before the lesson was built (#494, #495, #496).

| | lesson 50 |
|---|---|
| length | 29.7 min, 120 exercises |
| new items; new components, weighted (target) | 6; 7 (7) |
| theme (level); today's new items said as a turn of the played exchange | clothes (3); 4 of 6 («jakka», «Þetta er of lítið.», «Áttu þetta í stærra?», «Áttu þetta í öðrum lit?») |
| target reached | 18.3 min |
| items reviewed / due | 61 / 58, 46 of them due (lesson 49: 27 / 43, 26 due) |
| written review's queue | 126 due |
| pick-outs whose line was heard in the three lessons before | 8 of 8 |
| feedback form: load; friction | **light** (the sixth in a row); none |
| «sooner» | «Áttu þetta í stærra?», «Áttu þetta í öðrum lit?»; reason: hard to say |

What the lesson played, by change, and what the learner wrote:

- **No remark.** The form carried no note.
- **Played:** «í fyrramálið», reported after lesson 49, was asked from its meaning and broken down as fyrr · a · mál · ið (#496). The number
  choice set «Þrjá miða, takk.» against «Það kostar þrjú þúsund krónur.», naming the accusative: «þrír» becomes «þrjá» (#493, #495). «Þetta
  reddast» was cued with the full café (#494). No new number came, so #492 had nothing to change. No line was reported both ways, so #490 did
  not act.
- **The scene:** four of the six new items were said as turns of the played exchange, after one in lesson 48 and none in 49, against the
  criterion of two (#327).
- **The pace.** The target fell from 9 to 7 over lessons 45–50 while every lesson was rated «light». The rule of §9 "Pace" is doing what it
  says: a lesson whose due reviews do not fit lowers the pace (lesson 49 asked 26 of its 43 due), and «light» raises it only with a small
  backlog. Lesson 50 asked 46 of 58 due, with the time #492 freed. Read whether the pace rises once the reviews fit, before any change to the
  rule.
- **The listening.** All eight pick-outs had been heard in the three lessons before (#339, the owner's remark on the draft). The time freed in
  lesson 49's replay went partly to pick-outs, so the pool's sameness weighs more now.
- **Another learner** sent no new feedback.

### 5.41 Lesson 51: the first lesson built with #498 and #499

Lesson 51 was generated with LLA `1ed8830` (main with #498 and #499), the bot at site_update_notifier `f5bf9e1`. Rebuilt from its export with the
trip profile it is identical (122 exercises, 29.8 minutes).

| | lesson 51 |
|---|---|
| length | 29.8 min, 122 exercises |
| new items; new components, weighted (target) | 11; 9 (8) |
| theme (level) | supermarket (3), played again |
| target reached | 17.3 min |
| items reviewed / due | 40 / 40: 35 of the 40 due, and 5 not due; one more due item practised in another exercise, 4 not practised (lesson 50: 46 of 58 due) |
| written review's queue | 132 due |
| pick-outs whose line was heard in the three lessons before | 5 of 6 |
| feedback form: load; friction | **light** (the seventh in a row); other |
| «sooner» | none |

What the lesson played, by change, and what the learner wrote:

- **Played without a remark:** the number choice «Einn miða, takk.» / «Eina pylsu með öllu.» (#493); «Ég vil herbergi fyrir tvær nætur.»
  brought forward for the feminine side of 2 (#498); a gendered word said of him and of her, «Hann er týndur.» / «Hún er týnd.» (#499); «átján»
  introduced plainly in «Ég er átján ára.» (#492).
- **The prices.** «fimm þúsund krónur» and «tíu þúsund krónur», every word known (component cost 0), were announced «Something new.» and «A
  new expression.» and asked four times each. The owner: being treated as new expressions feels wrong. #492 had made them light but still
  new; lesson 49's «tvö / þrjú þúsund krónur» came the same way. Four of the eleven new items were numbers (17, 18, 5,000, 10,000).
  **Answered, in review (#502):** a plain number made only of known words is asked as a use of them («Made of words you know.»), the model
  after it, once more later, and not in the closing. On the replay each is asked twice instead of four times.
- **A cue that leaves its answer open.** The written review asked «Your neighbour complains about the snow. Say you think it's beautiful.» for
  «Mér finnst snjórinn fallegur.»; «Mér finnst það fallegt.» answers it too. Eight situations said «it» for what their answer names.
  **Answered, in review (#500):** each instruction names it, and `validate` lists any that does not.
- **«Sjáumst í dag!»**, asked for agreeing in the morning to meet after lunch: the learner asked whether it is natural. One says «Sjáumst á
  eftir!». **Answered, in review (#501, data):** «í dag» is no fill of «Sjáumst {time}!».
- **The clip of «lin»** in the split vett · lin · ga is broken. The owner's run of `tools/cut_off_clips.py` on the server's cache found it at
  0.06 s against an estimate of 1.18 s: the margins the trimmer keeps around a clip with no sound. The service had answered silence, and the
  cut-off check (#462) left out lines of one or two words. **Answered, in review (#503):** a clip shorter than 0.15 s looks cut off whatever its
  words. The cached clip is renamed by hand on the server for the next render to synthesize it again.
- **The pace.** The target rose from 7 to 8 before lesson 51 was built, by §9 "Pace": lesson 50 left 12 of its 58 due reviews unasked, under
  the quarter that lowers the pace, and the last two lessons were rated «light» (the recorded reason). Lesson 51 asked 35 of its 40 due items;
  four («ein króna», «jakka», «Mér finnst snjórinn fallegur», «Þetta er of lítið») were not practised at all, yet the lesson recorded no due
  review as not fitted (`due_not_fitted` empty), so the rule will read lesson 51 as fitting every due item. Why the four were left, and the
  record with them, is not established. Lessons 52 and 53 are read before any change to the rule.
- **The listening.** Five of the six pick-outs had been heard in the three lessons before (#339; lesson 50: 8 of 8).
- **Another learner** sent no new feedback.

### 5.42 Lesson 52: the first lesson built with #502–#512

Lesson 52 was generated with LLA `dbe39f1` (main with #502–#513), the bot at site_update_notifier `4e01489`. Rebuilt from its export with the
trip profile it is identical (113 exercises, 30.2 minutes).

| | lesson 52 |
|---|---|
| length | 30.2 min, 113 exercises |
| new items; new components, weighted (target) | 9; 8 (8) |
| theme (level) | bus (1), new (#511) |
| target reached | 15.2 min |
| items reviewed / due | 36 / 45: 30 of the 45 due, and 6 not due. Of the 15 others, 14 had been asked by the learner's own written review that morning (#238: the audio does not ask them again), and one, «ein króna», is no longer in the course |
| written review's queue | 130 due |
| pick-outs whose line was heard in the three lessons before | 11 of 16 |
| feedback form: load; friction | **light** (the eighth in a row); other |
| «sooner» | none |

What the lesson played, by change, and what the learner wrote:

- **The long run, first played:** «Endurtaktu.» introduced, then said before «Repeat.» in the day's introductions (#507); the bus at the stop,
  «Númer sex …» and «Sex hundruð og þrjátíu krónur» heard (#511); «Það eru mínus þrjár gráður.» introduced whole, «mínus» and «gráður» never
  asked bare (#512); «korter í fjögur» in a partner's listening line (#509); «þrjár» met in the temperature, not by course order (#508). The
  hot-dog stand and family tickets (#510) and the tour desk (#513) did not play.
- **Played without a remark:** the number choice «Tvo miða, takk.» / «Það kostar tvö þúsund krónur.» (#493); «Hann er japanskur.» / «Hún er
  japönsk.» (#499); the weather opener the reply agrees with, «Það er kalt í dag!» (#506); «Say you think the snow is beautiful.» (#500).
  «Made of words you know» (#502) did not play: no plain number was new.
- **The endings.** «Getting used to the changing endings, «nafninu», «bókun», is hard.» Both came new inside the hotel's lines, «Á nafninu
  Yuki.» and «Ég er með bókun.», modelled and split word by word, with no word on their form: «nafninu» is «nafn» with «-inu», «the name»
  after «á»; «bókun» has no ending at all. The family (a form without why it is so, form-why) was answered for the number choice in lesson
  50 (#495) and recurs here, a twenty-point part. The course names why a form changes only for a known noun's other form (#270), and «nafn»
  was not known. **Open:** #439 step 3, case through #270's frames, covers a new noun met in a form other than its nominative.
- **«mínus þrjár gráður», always three.** The owner, after the lesson: far too often, always three. The sentence came new for weather 2 (#512)
  and was heard 19 times and said 9, all with «þrjár» (the introduction, two clozes, a hint, three meaning recalls, two situations); on the
  replay the learner says it again in lesson 54 (a situation) and 56 (a meaning recall, and the number choice of 3, whose only feminine line
  it is). The value is fixed in a line the learner says, the cause of the «þúsund» remark after lesson 51 (the
  family one-version), and its pattern, which would vary it, comes only once the sentence is known, with 2–4 only. #451 step 3 rotates the
  numbers the learner hears, not the ones they say. **Open:** #451 step 3b, a number line the learner says is practised over the values they
  know once introduced.
- **The pace and the due reviews.** §5.41 left open why lesson 51 left four due items unpractised and recorded none as not fitted. Read on
  lessons 51 and 52: three of lesson 51's four, and 14 of lesson 52's 15, had been asked by the written review the same morning, and the
  fourth each time is «ein króna», gone from the course after lesson 29 yet still counted due. Both lessons asked every due item they could,
  so `due_not_fitted` empty is right; `due_at_start` counts items the lesson cannot ask, so the rule's quarter is read against a larger
  number than the lesson had. Lesson 51's new items in the written review: 8 recalled, «vettlinga» hesitated, «fyrir tvær nætur» not
  recalled (lesson 52 asked it three times, a hard item with no other sentence to practise it through, #326).
- **The numbers.** «þúsund» 16 times, «tíu» 2, «fimm» 4. Every «þúsund» is in an older line with a fixed value: the number choice's «Það
  kostar tvö þúsund krónur.», «þúsund krónur» reviewed, and the scenes heard again with their pick-outs (the café's «Tvö þúsund krónur,
  takk.», the clothes shop's «átta þúsund» and «fjögur þúsund», the supermarket's lamb at «tvö þúsund»). That is #451 step 3's work.
- **The listening.** Eleven of the sixteen pick-outs had been heard in the three lessons before (#339; lesson 51: 5 of 6).
- **Another learner** sent no new feedback.
