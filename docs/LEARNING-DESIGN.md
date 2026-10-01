# Learning design: purpose, bets and evidence

This document says what the project is for, what we believe about how the learner gets
there, what the learner's data has shown so far, and how to decide what to change next. It
exists because the way this project goes wrong is drift: each request or finding gets a
local fix, and the fixes stop adding up to a plan (owner: "#80 looks like a very short-sighted fix; I
want the overall learning plan to stay in a sensible order", and again after lesson 12).

**Read it before opening an issue, before implementing one, and after every round of
learner feedback.** Section 1 is the checklist; the rest is what the checklist points at.
`docs/DESIGN.md` covers the code; this document covers the learning.

Contents: [1 Checklists](#1-checklists) · [2 What the project is](#2-what-the-project-is) ·
[3 What we want to achieve](#3-what-we-want-to-achieve) ·
[4 What we believe](#4-what-we-believe-hypotheses) · [5 Evidence so far](#5-evidence-so-far) ·
[6 Signals](#6-signals-what-each-can-and-cannot-tell-us) ·
[7 Gaps](#7-where-the-design-falls-short-today) · [8 Roadmap](#8-roadmap-by-expected-impact) ·
[9 Decisions](#9-decisions-already-made) · [10 How we work](#10-how-we-work) ·
[11 Our failure modes](#11-our-own-failure-modes) · [References](#references)

---

## 1. Checklists

### Before opening an issue

Answer these in the issue. If one has no answer yet, say so; that is information too.

1. **Outcome.** Which outcome in §3 (O1–O5) does it serve? If none, why do it now?
2. **Gap.** Which gap in §7 does it close, or which new gap does it reveal? Is that gap the
   most limiting one right now (§8)? If not, what makes it worth doing first?
3. **Evidence.** What prompted it: learner data (which lesson or export, which numbers), an
   owner observation, a simulation, or a finding from research? A single remark or a single
   lesson is a lead, not a pattern (§10).
4. **Hypothesis.** Which belief in §4 does it rely on or test? Does it contradict a
   hypothesis, a decision in §9 or an invariant in `docs/DESIGN.md`? Then say so plainly and
   say why.
5. **Prediction.** What should change, in which signal from §6, and by when? What result
   would show it was wrong?
6. **Cost.** What does it take away? Lesson time is fixed, so anything added displaces
   something. Also count review time, learner effort and code complexity.
7. **Scope.** What is the smallest change that tests the hypothesis? Does it overlap open
   issues or PRs? Should it be folded into one of them rather than added?
8. **The underlying need.** When the request comes from the owner, restate the need behind
   it in learning terms. Check whether one deeper cause explains several recent requests.
   If it does, fix that cause (the requests after lesson 12 are the example in §5.6).
9. **Privacy.** No trip dates, itinerary, lodging or personal places (§9).

### Before implementing

1. The acceptance criteria are stated about the learner (what they hear, say, or can do),
   not only about code paths.
2. Check the change on **the real learner path**: replay the latest `learner.before.json`
   from a feedback export, with the same arguments (`manifest.json`). A simulated course
   from scratch is not enough. #94 was fixed in simulation and came back in the real path
   (§5.4).
3. Every default either reproduces today's behaviour, or the change of behaviour is the
   point and is stated.
4. The settings that produced a lesson stay recorded (`plan.json`, the manifest), so the
   feedback can be tied to them.
5. The tests pin the learner-facing behaviour, so it can't drift back silently.

### Before asking for a merge

1. The PR says which outcome and hypothesis it serves, what it predicts and how we will
   check it (the PR template asks).
2. It does one thing. A PR that bundles several behaviour changes makes their effects
   impossible to tell apart (§10).
3. "Done" means the issue's acceptance criteria hold, not that the planned steps were all
   taken (§11).

### After each round of learner feedback (at least weekly)

1. Read the signals in §6: review outcomes, scenario readiness, reading cards, feedback
   forms, owner notes.
2. Compare them with the predictions of the changes merged since the last round. Keep a
   change, revert it or give it more time; write down which and why.
3. Update §5 (evidence) and the status column in §4. Re-rank §8 if the evidence moved it.
4. Ask the learner when a signal is ambiguous (§6.2). Don't guess from the data alone.

---

## 2. What the project is

- **The product.** Audio-first lessons in the Pimsleur tradition (Pimsleur 1967): the
  instructor sets a task, a silence leaves room to *say* the answer, then a native voice
  gives it. Lessons are generated daily from a curriculum (TOML) and a learner model
  (`learner.json`). Nothing on screen is required during the audio.
- **The loop.** A Discord bot (Keno42/site_update_notifier) runs it. Before each lesson the
  learner answers a short review: the last lesson's new lines, due lines, a few scenario
  cards and a few reading cards. The answers are reported to the learner model. The bot then
  generates the next lesson, posts the audio and transcript, and offers a 30-second feedback
  form afterwards.
- **The learner.** One adult, a native Japanese speaker who is fluent in English and at A1 in
  Icelandic. They are preparing for a trip to Iceland a few months away; the dates and
  itinerary are private (#132). They do about 30 minutes of audio a day plus the review. The
  audio is currently instructed in English; Japanese glosses exist for every line. People
  going on the same trip may share the channel.
- **How it is built.** The owner directs; an AI writes the changes; the owner reviews and
  merges. The curriculum (`curricula/is-en`, about a thousand items) was written by an AI and
  has not been reviewed by a native speaker.
- **Hard constraints.**
  - The audio cannot hear the learner. Every retrieval is presumed successful until the
    review says otherwise.
  - There is one learner. Every comparison is within that learner and across time.
  - Giving feedback must stay nearly effortless. The owner has said they are not confident
    they can report accurately.
  - Lessons are generated on a home server that can be reached only through Discord.

---

## 3. What we want to achieve

### The north star

Travel readiness (#131): **on the trip, the learner can take part in the everyday scenes of
travel in Icelandic, enjoy reading what is around them, and show respect.** The owner's
framing: maximise the chance that the learner "can read the writing and enjoy it, can
greet, order and have simple conversations, and can express respect for the people and the
culture".

| | outcome | what it means in practice |
|---|---|---|
| **O1** | **Say it when it's needed** | Greet, order, pay, ask, thank, take leave and make small talk in the scene, at the right turn, within a natural pause. The owner's words: "not a memory game, but more expressions you can say when you need to say them". |
| **O2** | **Get through what locals say** | Catch the clerk's or guide's line at natural speed («Hvað má bjóða þér?», «Viltu poka?») and answer or repair («Ég skil ekki», «Gætirðu talað hægar?»), getting the gist even when some words are unknown. |
| **O3** | **Read, and enjoy it** | Signs, menus, shelf labels, place names. The audio never shows spelling, so reading is taught in Discord (#133). |
| **O4** | **Show respect** | Greeting, thanks and farewell in the right places; staying in Icelandic when the other person switches to English; cultural ease (#135). |
| **O5** | **Keep going** | The daily routine survives: not boring, not overloading, progress visible. Every other outcome depends on it. The owner, on day one: "just listing greetings is simply a game of memorizing. it is not only difficult but also boring" (#12). |

### Not the goal

- Item counts, curriculum coverage or a high retention number for their own sake. These are
  proxies. An improvement loop that optimises a proxy will keep raising it while the outcome
  stays flat (§11).
- A memorisation game. Isolated drilling is a means, never the shape of a whole lesson.
- Grammar terminology. Grammar is named when familiar examples make a contrast useful (#29).
- Pronunciation scoring, LLM role-play partners or LLM grading (#129: GPT Voice was tried
  and dropped).
- Tracking what the learner does elsewhere: other lessons, dictionaries, conversations
  (owner).
- Changing the pace because the trip is near. The pace is throttled only by what the
  learner reports (§9).

### How we would know

| outcome | observable now | not observable yet |
|---|---|---|
| O1 | Scenario cards for the scene rated 言えた on their latest review (the weekly readiness summary, #129); next-day recall of new lines in the review | Whether the line comes out at the right turn of a running exchange, inside the audio lesson |
| O2 | `respond` and `repair` cards with a partner line heard first | Natural-speed lines with variation in the daily audio (#134) |
| O3 | Reading cards | Reading in the wild |
| O4 | The `respect` markers of each scenario, as lines in the cards | Behaviour, in a real exchange |
| O5 | Load and friction in the feedback form; the owner's remarks; whether lessons are actually done | — |

---

## 4. What we believe (hypotheses)

These are the bets the design rests on. "Why" is the reason to believe it: research
(references at the end), the project's own evidence (§5) or an owner decision. "Wrong if" is
the observation that would make us drop or revise it.

Status: **adopted** (built in, strong prior, not re-tested here); **testing** (built in, and
a signal is being watched); **bet** (not built yet, or built but not yet measurable); **in
question** (the evidence so far points against it, not yet acted on); **revised** (evidence
changed it).

| id | we believe | why | where it lives | wrong if | status |
|---|---|---|---|---|---|
| **H1** | Producing a line from memory, after a real gap, builds durable recall better than hearing or repeating it. | Retrieval practice and spacing are among the best-supported findings on learning (Roediger & Karpicke 2006; Cepeda et al. 2006). | Answer pauses; the stage ladder; spacing across days (`learner.py`) | Next-day recall of new lines stays low even at a low pace | adopted |
| **H2** | Only success after a gap is evidence of learning. Success minutes after the first exposure is practice. | Performance during practice is a poor guide to learning (Soderstrom & Bjork 2015); #27. | `durable_successes`, `knows()`; the review comes the next day, before the lesson | — | adopted |
| **H3** | A line cued by a *situation* or a partner's line transfers to the real moment better than one cued by a translation. The closer practice is to use, the better. | Transfer-appropriate processing and encoding specificity (Morris et al. 1977; Tulving & Thomson 1973). | `situation` stage, `connect` exchanges, dialogues, scenario cards | Lines practised in situations do no better in scenario cards than lines practised from meanings | testing (no comparison made yet) |
| **H4** | **A lesson built around one scene's exchange beats a lesson built from an item count.** In such a lesson, today's lines are spread across the lesson and used together in a coherent exchange, again with other fillings, at rising resolution over lessons. The result is more lines said at the right turn, and less felt repetition. | H1 + H3, thematic grouping (H5), and the owner's experience of lesson 12 (§5.6). | Not built. #149 holds the design; `cando/themes.toml` (PR #155) holds a draft of the scenes | Themed scenes don't reach readiness faster than unthemed ones, or the learner finds themed lessons no less repetitive | **bet: the main one** |
| **H5** | Group new material by **scene** (bun, coffee, bag, card), not by **semantic set** (numbers 1–10, colours, yes/no). Similar items introduced together get confused; contrasting them pays off once each is known. | Semantic clustering slows L2 vocabulary learning and thematic clustering doesn't (Tinkham 1993, 1997; Waring 1997). Interleaving helps when the task is telling similar things apart (Brunmair & Richter 2019). Lesson 8: "numbers 1–4: masculine and neuter can't be told apart in the English prompts" (§5.2). | Partly: milestone notes contrast known items; #150 plans contrasts for known pairs and series. Nothing keeps a set from being introduced together: the curriculum lists numbers, colours and languages next to each other (§7, G5) | Items introduced as a set fail no more often than others | bet (research-backed) |
| **H6** | Chunks first, patterns next, transfer last. A fixed chunk said often becomes fluent (token frequency). A pattern used with many different fillings becomes productive (type frequency). Teach a pattern when two fillings are known, then move it to new words. | Usage-based learning (Bybee 2006); formulaic language (Wray 2002); #29's "capabilities outward". | Constructions with slots and `meaning_forms`; milestones with `transfer_items`; recombination; substitution runs (PR #153) | Substitution drills don't help the learner produce combinations they haven't heard (scenario cards with new fillings) | adopted (principle); testing (substitution) |
| **H7** | Every generated sentence must be plausible in its scene. An implausible one teaches less than it costs. | Owner (after lesson 12: never produce "order a passport at the café"); H3. | Case- and meaning-tagged slots; `opens` (PR #155); scene templates (#152) | — | adopted |
| **H8** | Natural-speed partner lines with some unknown words (the owner suggests 10–20%), in a familiar scene, build the tolerance needed to get through real exchanges. | The owner's hypothesis; the #129 pilots (common clerk lines were not understood). **Caveat:** detailed comprehension needs about 95% of the words to be known when listening and 98% when reading (van Zeeland & Schmitt 2013; Hu & Nation 2000). At 80–90%, expect gist from context, not learning of the unknown words. So the scene must carry the meaning. | Scenario cards (partner lines may go beyond the course); partner turns in themes (PR #155); #134 | Respond and repair cards with unknown words stay at 言えなかった, or the learner finds them discouraging rather than useful | bet |
| **H9** | The number of new items, throttled only by recall reports, keeps the load right. The pace design aims at about 6–10 new productive items per 30 minutes and about 80–85% next-day success. | README "Pacing"; desirable difficulties (Bjork 1994): too easy wastes time, too hard fails. | `suggest_pace` | The load rating drifts to "heavy", or next-day failures stay above 20%, at the pace actually used | **revised:** the actual number of new items is not the pace (§7, G4) |
| **H10** | Self-reports are informative when they are made the next day, with the answer hidden until the learner has tried. They are noisy, lean towards success and must never be produced by an LLM. | Delayed judgements of learning are far more accurate than immediate ones (Nelson & Dunlosky 1991); #129 (GPT transcripts did not match what was said). | The bot's review (answer revealed only after trying; 3-point scale); the feedback form | The three levels don't separate items: everything 言えた, nothing 迷った | **in question:** so far it reads exactly like that (§5.2) |
| **H11** | Practice spent on items the learner plainly knows is waste, and the learner notices it. A known item should wait for its date. | Spacing (H1); #94; the owner after lesson 12 (já, nei, hæ every lesson although reported 言えた). | Not-due items wait (#94); stable items never fill (PR #153) | — | adopted (#94); the recurrence is fixed in PR #153 |
| **H12** | Variety, coherence and visible progress keep a daily routine alive. Boredom ("a game of memorizing") is the biggest threat to every other outcome. | Owner, #12 and after lesson 12; Nation's four strands (Nation 2007), whose message is that a course should not be all drill. | Dialogues, exchanges, notes, scenes, reading cards | The routine continues and the learner reports no boredom with a drill-heavy lesson | adopted (value) |

### What the hypotheses imply for a lesson

Read together, H1–H12 describe a lesson that is still the target:

1. Each new line is retrieved after real gaps: minutes apart within the lesson, days apart
   across lessons. Practice is spread out, not bunched after the introduction (H1, H4).
2. Cues resemble use: a situation, or a partner's line, more than a translation (H3).
3. Lines come back inside a coherent exchange of the lesson's scene, with other fillings and
   at rising resolution (H4, H6).
4. The material that goes together is the material used together in a scene. Similar items
   (numbers, colours, opposites) are introduced apart and contrasted once known (H5).
5. Patterns grow from known chunks, and only plausible sentences are generated (H6, H7).
6. Natural-speed partner lines are part of practice, and the scene carries their meaning
   (H8).
7. Time is not spent on what is plainly known (H11). Spare time goes to the scene, to
   substitution and to today's lines, not to padding.
8. The learner's effort for feedback stays tiny, and their judgement is asked for the next
   day (H10).

A balance check, from Nation's four strands: meaning-focused input (listening), meaning-
focused output (saying things in scenes), language-focused learning (drills, notes) and
fluency (easy material, fast). Nation argues for roughly equal time on each. In the real
lesson 12, isolated recall took 62% of the exercise time (124 recalls) and introductions 12%.
Exchanges with a partner's line took 9%, mixed reviews 10%, new sentences 3% and notes 3%.
There was no dialogue. Listening at natural speed and fluency practice are the thin strands.

---

## 5. Evidence so far

As of lesson 12. Sources: the owner's reviews of real transcripts, the report history in
`learner.json`, the first feedback export, the GPT pilots, and replays and simulations.

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

---

## 6. Signals: what each can and cannot tell us

### 6.1 Inventory

| signal | where it is | what it tells us | what it cannot tell us |
|---|---|---|---|
| **Review ratings** (言えた / 迷った / 言えなかった) for each question | The bot's `pending_review.json` → `audiolesson report` → `learner.json` (`recalled`, `hesitated`, `failures`, history `outcome`) | Next-day recall of a specific line, cued the way the lesson cued it | Production in a real exchange or under time pressure. Which item failed when a question holds several. It is self-judged after the answer is shown |
| **Scenario cards** | `scene_queue.json`; the weekly readiness summary in the lesson post | Saying the line in a stated scene, sometimes after hearing a partner's line (O1, O2) | Unscripted exchanges. It is self-rated too, and it is not reported to `learner.json` (by design) |
| **Reading cards** | `reading_queue.json` | Decoding and meaning of written words (O3) | Reading in context |
| **Feedback form** (#128) | `lesson_feedback.jsonl` | How usable, heavy or repetitive the lesson felt; candidates the learner confirms; a free note | Causes. It is given immediately after a long lesson, so the early parts are half forgotten. One form so far |
| **Lesson records** | `lesson_manifests/` (plan, script, transcript, `learner.before.json`, arguments) | Exactly what was practised and when. Replays can reproduce a lesson | What the learner noticed («I didn't hear "kaupa miða"») |
| **Owner observations** | Issues, chat, transcript reviews | The richest qualitative signal: what felt wrong and why | Whether a single remark is a pattern. Check it against the data and §9 |
| **Simulations and replays** | Scripts in `tools/`, tests | Planner behaviour under stated assumptions; cheap before/after comparisons | Anything about learning. A simulation from scratch can differ from the real path (§5.4) |
| **Native corrections** | When they come (#129) | Correctness and naturalness | — |
| *Not a signal* | LLM transcripts or assessments | — | Everything (#129) |

### 6.2 Reading the signals

- **Small numbers.** One learner and about a dozen lessons. Look for patterns that repeat
  across items or weeks before changing a lever (§10). One lesson is a lead.
- **Time confounds everything.** The learner keeps learning, the curriculum gets harder and
  several things change at once. When a number moves, list the other changes made in the
  same window before crediting one of them.
- **A measure stuck at the ceiling says nothing.** All 言えた means either "fine" or "too easy
  to discriminate". Look at the harder instruments (scenario cards, new fillings, partner
  lines) or ask the learner. «迷った» never being used is a question to ask, not a fact
  about the learner.
- **Delayed beats immediate.** The next-day review is the honest one. Same-lesson success
  and immediate impressions overestimate (H2, H10).
- **Candidates are prompts, not diagnoses.** "Same situation twice" was confirmed, but the
  cause was something else (§5.3). Ask what the learner meant before building a fix.
- **Replay the real path.** Reproduce the lesson from its `learner.before.json` and
  arguments before trusting a simulated course (checklist in §1).
- **Proxies drift from the outcome.** Retention, item counts and candidate counts are
  diagnostics. The readiness of scenes (O1–O4) and the routine (O5) are the outcome.

### 6.3 Questions the next weeks of data can answer

| question | hypothesis | where to look |
|---|---|---|
| Does next-day recall of new lines stay at about 80% or better at the pace actually used? | H9 | Review outcomes for the previous lesson's new items |
| Do phrases of three or more words keep failing more often than short ones? | G9 | Failures by phrase length |
| Does the learner use «迷った» when unsure? If not, why: is it never true, or is the scale wrong? | H10 | Ask; then the outcome counts |
| Are lines practised in situations rated better in scenario cards than lines practised only from meanings? | H3 | Scenario cards against each line's stage history |
| Once lessons are built around a scene, does "repetitive" go away, and do themed scenes reach readiness sooner? | H4 | Feedback forms; readiness per scenario, themed or not |
| Do respond cards with unknown partner words improve over the weeks, and does the learner find them useful or discouraging? | H8 | Scenario cards; ask |
| Do items introduced in the same lesson as a set (numbers, colours) fail more often than others? | H5 | Failures by introduction context |
| When little is left to practise and a lesson ends a few minutes short, is that better for the learner than filling the time with new material? | O5, H9 | Ask; load ratings |

---

## 7. Where the design falls short today

| id | gap | evidence | outcome / hypothesis |
|---|---|---|---|
| **G1** | **We don't read our signals routinely.** Decisions follow single remarks; there is no weekly comparison of predictions with data, and the readiness summary isn't used in decisions. | §5.3, §5.6; one feedback form so far | all; §10 |
| **G2** | **Lessons are assembled from an item count and an urgency queue.** Practice is bunched after each introduction, reviews have no shared scene, and the only coherent chunks are dialogues and exchanges. | §5.4; the owner after L12 | O1, O5; H4 |
| **G3** | **No natural-speed listening in the daily audio.** Partner lines come at one speed and in one wording. | §5.5; #134 ("now the top pre-trip gap") | O2; H8 |
| **G4** | **The pace isn't the number of new items.** Extra arcs add up to half the pace again, and before PR #153, without limit when the fillers ran out. | §5.2 | O5; H9 |
| **G5** | **Semantic sets can arrive together.** The trip ordering and curriculum order can put a whole set (numbers 6–19, colours, languages) into one lesson. | Lesson 8 (numbers); a replay with numbers boosted: nine numbers in one lesson (PR #154) | O1; H5 |
| **G6** | **Plausibility rests on slot tags.** Implausible or ungrammatical sentences can still be generated: «Hvenær opnar ísskápurinn?» before PR #155, and «Ég vil blár.» (the colour should be accusative). | Found after L12 | O1; H7 |
| **G7** | **Three schedulers.** The audio's learner model, the Discord review queue (its own 1→3→7→14→30-day steps) and the card queues each decide what comes back, and their combined effect has never been examined. They are separate kinds of evidence by design (#129), but the learner experiences their sum. | Bot README | O5; H10, H11 |
| **G8** | **The self-report scale may not discriminate.** «迷った» has never been used. | §5.2 | H10 |
| **G9** | **Long phrases fail most.** Three-word-plus formulas get the same treatment as short ones. | §5.2 (9/24 vs 2/27) | O1; H1, H9 |
| **G10** | **Content isn't native-reviewed.** All the scene lines, partner lines and glosses are candidates. | README | O1–O4 |

---

## 8. Roadmap by expected impact

Ordered by the expected effect on the outcome, adjusted for cost and for what depends on
what. Re-rank it when the evidence moves.

1. **Make the loop measurable and use it (G1, G8). Cheap; everything else depends on it.**
   - A weekly read of the signals against the predictions of merged changes, written down
     (§1, last checklist).
   - Ask the learner about «迷った» and about what "repetitive" meant.
   - A small report that puts the week's numbers side by side: next-day recall of new lines,
     failures by item and phrase length, scenario readiness per tier, feedback forms. It
     should come from the data the bot already keeps (§6.1).
2. **Build lessons around a scene (G2, G5, and G3 through partner turns), in steps (#149).**
   It is the main bet (H4). Test it as a bet: first a theme exchange inserted into today's
   planner, run twice per lesson with other fillings, with time-based spacing for today's
   lines. Then reviews grouped by the theme's topics. A larger redesign only if the first
   steps pay off.
   - New material goes into a lesson by scene, and semantic sets are introduced across
     lessons and scenes, not in one block (H5). Today the curriculum lists numbers, colours
     and languages next to each other. #150's contrasts (yes and no back to back, a series as a
     run) fit H5 for items already known; they must not become a way to introduce a set
     together.
   - The theme's partner lines are where clerk-side listening enters the audio: natural
     speed, two or three variants (#134, H8). #134 should be designed together with #149,
     not after it.
3. **Plausible substitution inside the scenes (G6, #152).** Patterns serve the theme's
   exchange; scene templates keep fillings plausible (H6, H7).
4. **Content priorities, as data for the scenes.** Numbers through prices and times in
   scenes rather than as a block. Colours where signs and warnings use them (gul / rauð
   viðvörun, agreeing with the noun). The scene catalogue reviewed by the owner, and by a
   native speaker when one is available (G10).
5. **Long phrases (G9).** Watch whether the pattern holds as more data comes in. If it
   does, give long formulas more scaffolding or count them as more than one item in the
   pace.

**Not now:**

- more planner levers;
- content that no mechanism uses yet;
- new instruments before the existing ones are read;
- local fixes to symptoms that step 2 will remove.

---

## 9. Decisions already made

Don't reopen these without new evidence; when you do, say what changed.

- **Pace.** It never depends on the departure date. Lessons go on at the same best-effort
  pace before and during the trip, throttled only by recall reports (owner; #129, #131).
- **Evidence.**
  - Presumed success is kept apart from confirmed outcomes (#119).
  - The last lesson's new items are reviewed before the next lesson is generated (bot).
  - `knows()` means two recalls on or after a due date (#27).
- **Sequencing.**
  - Sequence from capabilities outward. High-value reusable material comes early (#29).
    The owner: teaching "the high-value words that come up in conversation and should be
    usable" is "the top priority of the whole app".
  - No prerequisite gates bolted onto dialogues (#25).
  - Never an exact dialogue line as a memory item, just because the representation can't
    yet express the pattern behind it («held ég», #54 review). The test is whether the
    learner gains a reusable model, not whether a diagnostic comes out clean.
- **Conversation.**
  - An exchange's target-language turns must form a plausible conversation with the
    instructor lane removed (#48).
  - `connect` without an authored bridge is mixed review, and says so (#78).
- **Repetition.**
  - New items may repeat within a lesson and are never dropped (#147).
  - Situation variety is welcome, with no cap (#148).
  - Not-due items wait for their date (#94).
- **Generation and audio.**
  - Only plausible sentences in plausible scenes (owner after L12).
  - No pause stretching to fill a short lesson (owner after L12).
- **Instruments.**
  - No LLM partner or grader (#129).
  - Native corrections are applied when they come, untracked. Outside learning is not
    tracked (owner).
- **Governance.**
  - At most two lever changes a week, and only on a pattern across three or more items or
    two consecutive weeks.
  - Every change states its hypothesis, lever, expected outcome and check week.
  - A human approves every change, and nothing changes the learner model or the planner
    automatically (#129, #136).
- **Privacy.** Trip dates, itinerary, lodging, personal places and scenario weights stay in
  the private profile. They never appear in the repository, issues, logs or exports (#131,
  #132).
- **Process.** One PR per change; the owner merges.

---

## 10. How we work

- **Every change is an experiment with a prediction.** State the hypothesis (§4), what
  should move in which signal (§6) and when it will be checked. At the check, keep the
  change, revert it or extend it, and write down which.
- **Few changes at a time.** With one learner, two simultaneous changes can't be told apart.
  The lever rule in §9 applies to behaviour changes generally, not only to levers.
- **An owner request is evidence of a need.** Restate the need in terms of §3 and §4, look
  for the cause shared with other recent requests, and fit it into §8. If it is a principle
  ("never implausible"), record it in §9. If the request conflicts with a hypothesis or the
  evidence, say so before building it. Agreement is not the goal; the learner's outcome is.
- **Acceptance criteria describe the learner's experience** and are checked on the real
  path (§1).
- **Keep this document true.** Update §5 and §4 at each weekly read, §8 when priorities
  move, §9 when a decision is made. Write lesson numbers and issue numbers, never trip
  dates.

---

## 11. Our own failure modes

Each of these has happened. Watch for them.

- **Local fixes for a global problem.** Answering each remark with its own issue: #80
  ("very short-sighted"), and the day after lesson 12 (§5.6).
- **Content before mechanism.** Writing data that no part of the system uses yet (the scene
  catalogue in PR #155 came before the planner can use it).
- **Optimising an invented metric.** Building a lever around a candidate type ("same
  situation twice") without asking what it meant (§5.3).
- **Trusting simulation over the real path.** #94 fixed in simulation, recurring for the
  learner (§5.4).
- **"Steps done" mistaken for "criteria met".** #34 closed on its pilot list while two of its
  acceptance criteria were still unmet (#44).
- **The wrong abstraction.** Prerequisite gates for dialogues (#25), whole dialogue lines as
  items («held ég»), a representation limit mistaken for a property of the language.
- **LLM output taken as evidence.** The GPT Voice transcripts (#129).
- **Bundling.** Several behaviour changes in one PR, so their effects can't be told apart.

---

## References

General findings, mostly from laboratory and classroom studies. For this learner they are
priors, not proof; the learner's own data decides.

- Bjork, R. A. (1994). Memory and metamemory considerations in the training of human beings.
  In J. Metcalfe & A. Shimamura (Eds.), *Metacognition: Knowing about knowing*. MIT Press.
- Brunmair, M., & Richter, T. (2019). Similarity matters: A meta-analysis of interleaved
  learning and its moderators. *Psychological Bulletin*, 145(11).
- Bybee, J. (2006). From usage to grammar: The mind's response to repetition. *Language*,
  82(4).
- Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006). Distributed
  practice in verbal recall tasks: A review and quantitative synthesis. *Psychological
  Bulletin*, 132(3).
- Hu, M., & Nation, I. S. P. (2000). Unknown vocabulary density and reading comprehension.
  *Reading in a Foreign Language*, 13(1).
- Karpicke, J. D., & Roediger, H. L. (2007). Expanding retrieval practice promotes short-term
  retention, but equally spaced retrieval enhances long-term retention. *Journal of
  Experimental Psychology: Learning, Memory, and Cognition*, 33(4). See also Nakata, T.
  (2015) in *Studies in Second Language Acquisition*, 37(4), for L2 vocabulary. Real gaps
  matter more than whether they expand.
- Morris, C. D., Bransford, J. D., & Franks, J. J. (1977). Levels of processing versus
  transfer appropriate processing. *Journal of Verbal Learning and Verbal Behavior*, 16(5).
- Nation, I. S. P. (2007). The four strands. *Innovation in Language Learning and Teaching*,
  1(1).
- Nelson, T. O., & Dunlosky, J. (1991). When people's judgments of learning (JOLs) are
  extremely accurate at predicting subsequent recall: The "delayed-JOL effect".
  *Psychological Science*, 2(4).
- Pimsleur, P. (1967). A memory schedule. *The Modern Language Journal*, 51(2).
- Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning: Taking memory tests
  improves long-term retention. *Psychological Science*, 17(3).
- Soderstrom, N. C., & Bjork, R. A. (2015). Learning versus performance: An integrative
  review. *Perspectives on Psychological Science*, 10(2).
- Tinkham, T. (1993). The effect of semantic clustering on the learning of second language
  vocabulary. *System*, 21(3).
- Tinkham, T. (1997). The effects of semantic and thematic clustering on the learning of
  second language vocabulary. *Second Language Research*, 13(2).
- Tulving, E., & Thomson, D. M. (1973). Encoding specificity and retrieval processes in
  episodic memory. *Psychological Review*, 80(5).
- van Zeeland, H., & Schmitt, N. (2013). Lexical coverage in L1 and L2 listening
  comprehension: The same or different from reading comprehension? *Applied Linguistics*,
  34(4).
- Waring, R. (1997). The negative effects of learning words in semantic sets: A replication.
  *System*, 25(2).
- Wray, A. (2002). *Formulaic language and the lexicon*. Cambridge University Press.
