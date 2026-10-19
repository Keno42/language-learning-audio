# Learning design: purpose, bets and evidence

This document says what the project is for, what we believe about how the learner gets
there, what the learner's data has shown so far, and how to decide what to change next. It
exists because the way this project goes wrong is drift: each request or finding gets a
local fix, and the fixes stop adding up to a plan (owner: "#80 looks like a very short-sighted fix; I
want the overall learning plan to stay in a sensible order", and again after lesson 12).

**Read it before opening an issue, before implementing one, and after every round of
learner feedback.** For a routine task start from the two short briefs, `docs/CURRENT-POLICY.md` (what always holds)
and `docs/CURRENT-STATUS.md` ("Now", copied from §8, and where to look for the rest), and read the sections they point
at; read all of this for
a change to learning policy or to the structure of the lessons or the review. If a brief disagrees with this document,
this document wins and the brief is fixed. Section 1 is the checklist; the rest is what the checklist points at.
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

1. **Concept and outcome.** Which of the four things in §3 "The concept" does it serve, and how (and which outcome,
   O1–O5)? Will the learner notice? If §8 "Now" still lists a twenty-point part, why does this come first (§9 "Good
   enough overall")?
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

### After each round of learner feedback (daily while the design is moving)

While the lessons are still being reshaped (§9 "Governance": the fix-up phase), this is done
after **every** lesson, the next day; once they settle, weekly.

1. Replay the export of the lesson just heard: `python tools/replay_lesson.py <lesson-NNN>
   --trip <profile> --lessons 3`. The first column is that lesson rebuilt with the current code
   (exact on the export's own revision); the next two continue it under a stated assumption.
   Compare with the previous day's table.
2. Read the signals in §6: review outcomes, scenario readiness, reading cards, feedback
   forms, owner notes. A fault the learner heard, or the table shows, becomes an issue the
   same day.
3. Compare them with the predictions of the changes merged since the last round. Keep a
   change, revert it or give it more time; write down which and why.
4. **Two speeds.** What one lesson shows (length, a word said alone, a repeated narration, a
   bug, the form's load and friction) is read daily. What needs volume (next-day recall rates,
   long phrases against short, «迷った», scenario readiness) is read once three to five lessons
   have added up. **The slow reads gate the decisions that depend on them, never the work:**
   development and merges go on while they accumulate.
5. Record the lesson's evidence in a new §5 subsection (a dated record: later edits fix only its references). Rewrite the status column
   in §4 and §8 to say where things stand, not extended (§10 "Documents"); re-rank §8 if the evidence moved it.
6. Ask the learner when a signal is ambiguous (§6.2). Don't guess from the data alone.
7. **Sort each remark into one of three** (§9 "Good enough overall"):
   - **A twenty-point part.** The learner names something boring, confusing or contradictory. It goes into §8
     "Now", which holds three or four items at most.
   - **A precision problem.** A line not quite right, a rare case. It becomes a named exception, or it waits.
   - **A mechanism idea.** It waits as an issue, outside "Now" (§8 "Not now" lists the kinds), unless it fixes a
     twenty-point part.

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
  - Lessons are generated on a home server that can be reached only through Discord. Secrets reach it sealed
    through the repository (site_update_notifier#119).

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

### The concept (owner, after lesson 20)

This is not an app for producing any natural Icelandic sentence. The learner learns the expressions a traveller will
use, and gets familiar with the basics of Icelandic on the way. So each scene has **target expressions**. Around each
one come a few **parallel expressions**, only as many as help the target come out quickly. Grammar and generation
serve the targets; they are not ends in themselves.

What the lessons should leave the learner able to do:

1. **The ear is used to Icelandic, and the set scenes get an answer** (O1, O2).
2. **Find the information they need** in what is said: the price, the time, the stop (O2).
3. **Pin down the part they don't understand,** to look it up or ask about it (O2, repair).
4. **Keep enjoying it,** day after day (O5).

Greetings, thanks and farewells (O4) are target expressions of their scenes, so they come under 1. Reading (O3) is
its own track, in Discord (the reading cards, #133), and is not judged by these four.

Every finer decision asks which of these it serves, and how; when none, it waits. §9 "Good enough overall" says how
much precision that takes.

### The daily dose (owner, after lesson 13)

The routine is a daily dose of Icelandic that the brain can work on, with sleep between doses.
In the owner's words: a load too light is no learning at all (wasted time), and a lesson that
doesn't reach its 30 minutes is a day short of time; the reserved time has to be used fully to
stimulate the language areas of the brain and build the circuits, and sleep is part of how
the brain consolidates, so a day with a light lesson is a real loss. "Number of new items" is a
means of a means of a means, and not what to hold on to. The owner wants a proper learning
plan, and the 言えなかった answers respected: at the time only the last lesson's failures seemed to
come back in review (§5.10; since then an open item is practised and asked until recalled, §9 "Evidence").

What this fixes: the *time* of each lesson is a requirement, filled with things that load the
learner (new material to hear, exchanges, failed items brought back until recalled), never with
repetition of what is known (H11) and never by stretching pauses (§9). What it doesn't fix:
a number of new items, or a length for its own sake (§11).

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
| O2 | `respond` and `repair` cards with a partner line heard first | Whether variants of the partner lines in the daily audio (themes, #134) are understood; they come with a gist, not a check |
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
| **H4** | **A lesson built around one scene's exchange beats a lesson built from an item count.** In such a lesson, today's lines are spread across the lesson and used together in a coherent exchange, again with other fillings, at rising resolution over lessons. The result is more lines said at the right turn, and less felt repetition. | H1 + H3, thematic grouping (H5), and the owner's experience of lesson 12 (§5.6). | Built (#149): the theme exchange played twice, early with the translation and late without it, the cue in both and the partner's lines in variants (#186, #189, #210); a theme in every lesson, a played level replaying after a rest (#196); new material from the theme's next level, and grouped by scene when it has none (#201, #329); a part with its frame, caps on a semantic set (#202, #204, #207); a fixed phrase linked to its pattern (#206, #311). Numbers are heard and picked out in scene lines (#213, folded into #248). `cando/themes.toml` has 4 themes, 9 levels. Not built: the scene line for new items whose topic has no theme and more theme levels (#327), colours through their scenes, the closing block on the theme's lines | Themed scenes don't reach readiness faster than unthemed ones, or the learner finds themed lessons no less repetitive | **bet: the main one.** The theme frames every lesson, and the «Anki game» remark of lesson 13 has not come back (§5.10; history in `docs/history/evidence.md`). New material rarely comes from the scene, and the levels run out at lesson 28 (G2, #327) |
| **H5** | Group new material by **scene** (bun, coffee, bag, card), not by **semantic set** (numbers 1–10, colours, yes/no). Similar items introduced together get confused; contrasting them pays off once each is known. | Semantic clustering slows L2 vocabulary learning and thematic clustering doesn't (Tinkham 1993, 1997; Waring 1997). Interleaving helps when the task is telling similar things apart (Brunmair & Richter 2019). Lesson 8: "numbers 1–4: masculine and neuter can't be told apart in the English prompts" (§5.2). | Partly: milestone notes contrast known items; #150 plans contrasts for known pairs and series; at most three new items of one semantic set come in a lesson, except the items the theme's next level wants and a filler a construction's slot pulls in, although the curriculum lists numbers, colours and languages next to each other (#204, #207; G5) | Items introduced as a set fail no more often than others | bet (research-backed). Lesson 15's two forms of one word, introduced together, both failed the next day (§5.14). The other side, a set every scene needs that never moves forward: #213 |
| **H6** | Chunks first, patterns next, transfer last. A fixed chunk said often becomes fluent (token frequency). A pattern used with many different fillings becomes productive (type frequency). Teach a pattern when two fillings are known, then move it to new words. | Usage-based learning (Bybee 2006); formulaic language (Wray 2002); #29's "capabilities outward". | Constructions with slots and `meaning_forms`; milestones with `transfer_items`; recombination; substitution runs (PR #153) | Substitution drills don't help the learner produce combinations they haven't heard (scenario cards with new fillings) | adopted (principle); testing (substitution). By the concept, patterns serve target expressions, and moving a pattern to new words is limited to the parallel expressions a target needs (§9 "Good enough overall"). The converse holds for words and for lines that vary in use: a word heard in one sentence only («úlpu», lesson 25, #311) and a line authored as a fixed phrase (the bus, lesson 26, #336) are repeated where the learner expected variety (§5.21, §5.22). A form is modelled before it is asked (#211) |
| **H7** | Every generated sentence must be plausible in its scene. An implausible one teaches less than it costs. | Owner (after lesson 12: never produce "order a passport at the café"); H3. | Case- and meaning-tagged slots; `opens` (PR #155); scene templates (#152) | — | adopted |
| **H8** | Natural-speed partner lines with some unknown words (the owner suggests 10–20%), in a familiar scene, build the tolerance needed to get through real exchanges. | The owner's hypothesis, and their preference for more listening time over shorter lessons (§5.7); the #129 pilots (common clerk lines were not understood). **Caveat:** detailed comprehension needs about 95% of the words to be known when listening and 98% when reading (van Zeeland & Schmitt 2013; Hu & Nation 2000). At 80–90%, expect gist from context, not learning of the unknown words. So the scene must carry the meaning. | Scenario cards (partner lines may go beyond the course); partner turns in themes, in variants (#155, #189); the second half: a heard scene, *pick out* the information and *catch the unknown word* through the meaning (#252, #271, #303) | Respond and repair cards with unknown words stay at 言えなかった, or the learner finds them discouraging rather than useful | bet. No discouragement so far, and the partner slowing down word by word was praised (lesson 24, #261). The remarks are about the exercises: pick-outs too easy (lesson 21), the unknown word pointed to through the meaning (lesson 22, #271), the need named before the line (lesson 25, #303), the turns marked (lesson 26, #335). The unknown words were the same three in every lesson from 23 to 26: by the owner's decision a word is caught about once, and some new words are introduced through the catch (#339; §5.22) |
| **H9** | The amount of new material, counted in weighted new components (§9 "Pace", #218), throttled by recall reports (over the last three lessons) and by the learner's load rating, keeps the load right. It aims at about 8 a lesson to start (#218) and about 80–85% next-day success. | README "Pacing"; desirable difficulties (Bjork 1994): too easy wastes time, too hard fails. | `suggest_pace` | The load rating drifts to "heavy", or next-day failures stay above 25% (the top of the pace's hold band, §9 "Pace"), at the pace actually used | **revised (#218):** the pace's unit is weighted new components over a three-lesson window, with the load rating as an input (§9 "Pace"; #229, #233, #235; #234, the BÍN check, open). The number of new items was not the pace: lessons 18–19 were «light» at 81–100% next-day success. Since then the load has been «right» for six lessons running, and next-day recall has stayed at 10 of 13 or better since lesson 22 (§6.3) |
| **H10** | Self-reports are informative when they are made the next day, with the answer hidden until the learner has tried. They are noisy, lean towards success and must never be produced by an LLM. | Delayed judgements of learning are far more accurate than immediate ones (Nelson & Dunlosky 1991); #129 (GPT transcripts did not match what was said). | The bot's review (answer revealed only after trying; 3-point scale); the feedback form | The ratings stop telling recalled lines from guessed or failed ones | **revised:** «迷った» is a third value. The learner usually commits at once (§5.7), and uses «迷った» in some reviews: for 2 and 3 new items after lessons 22 and 23, none after lessons 24 and 25, when all were recalled (§5.19–§5.22). The pace counts it as half a failure |
| **H11** | Practice spent on items the learner plainly knows is waste, and the learner notices it. A known item should wait for its date, and is taken early only as the exception in §9 "Repetition" allows. | Spacing (H1); #94; the owner after lesson 12 (já, nei, hæ every lesson although reported 言えた). | Not-due items wait (#94); stable items never fill (PR #153) | — | adopted. Not-due items wait, with the one exception in §9 "Repetition" (#94), stable items never fill (#151, #153), an open item is asked at every review until recalled (#205, #220), and a recall at a real gap extends the interval and raises the ease (#298, #331). Retention so far: 3 of 3 at 3–6 days, 5 of 5 at 7–13, none yet at 14+; the review queue fell from 151 to 114 due once a first 言えた began waiting 3 days (site_update_notifier#133; §5.22) |
| **H12** | Variety, coherence and visible progress keep a daily routine alive. Boredom ("a game of memorizing") is the biggest threat to every other outcome. | Owner, #12 and after lesson 12; Nation's four strands (Nation 2007), whose message is that a course should not be all drill. | Dialogues, exchanges, notes, scenes, reading cards | The routine continues and the learner reports no boredom with a drill-heavy lesson | adopted (value). Boredom came from easy recombination and reviews filling the time (lesson 20, §5.16) and from the same cards and lines coming back (lessons 25–26: site_update_notifier#132, #336, #339). A pattern's varied fillers are praised (lesson 26, §5.22) |
| **H13** | Hearing a hard-to-say word slowed and split by syllable, once at its introduction and once more when the learner reports it hard, lowers pronunciation anxiety at little cost in time. | The learner's requests after lessons 15 and 16 (§5.13, §5.14); no study cited. | `Item.syllables`: an authored split, said slowly piece by piece at the introduction (#212: #292). Again for a word reported hard, and for words inside phrases: #337, not built | Anxiety remarks continue on words that got the slow model, or those words fail next day no less than others | bet, **not yet heard.** The rule flagged none of the words the learner found hard in lesson 26 (§5.22); #337 widens it. Lesson 27's «sooner» items get both #326's connections and #337's split: read pronunciation remarks for #337 and next-day recall for #326 |

### What the hypotheses imply for a lesson

Read together, H1–H13 describe a lesson that is still the target:

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
7. Time is not spent on what is plainly known (H11). Spare time goes to the scene and the
   ear (§3 "The concept"), to today's lines, and to a not-due item early only as §9 "Repetition" allows; not to
   padding, and not to recombining known patterns for their own sake (lesson 20, §5.16).
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

One subsection per lesson, read from its feedback export replayed. Sources: the owner's reviews of real transcripts,
the report history in `learner.json`, the feedback forms and exports, and replays and simulations. The subsections are
a dated record: a statement about what was built or open holds for its lesson; §4, §7 and §8 say where things stand now.

**Older lessons are in `docs/history/evidence.md`** (§10 "Documents"), under their own numbers, so a reference such as
"§5.14" finds its subsection there.

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

---

## 6. Signals: what each can and cannot tell us

### 6.1 Inventory

| signal | where it is | what it tells us | what it cannot tell us |
|---|---|---|---|
| **Review ratings** (言えた / 迷った / 言えなかった) for each question | The bot's `pending_review.json` → `audiolesson report` → `learner.json` (`recalled`, `hesitated`, `failures`, history `outcome`) | Next-day recall of a specific line, cued the way the lesson cued it. Since site_update_notifier#118, also recall after a gap of 3 days or more, reported with the gap (the daily read's retention row, #298) | Production in a real exchange or under time pressure. Which item failed when a question holds several. It is self-judged after the answer is shown |
| **Scenario cards** | `scene_queue.json`; the weekly readiness summary in the lesson post | Saying the line in a stated scene, sometimes after hearing a partner's line (O1, O2) | Unscripted exchanges. It is self-rated too, and it is not reported to `learner.json` (by design) |
| **Reading cards** | `reading_queue.json` | Decoding and meaning of written words (O3) | Reading in context |
| **Feedback form** (#128) | `lesson_feedback.jsonl` | How usable, heavy or repetitive the lesson felt; candidates the learner confirms; a free note | Causes. It is given immediately after a long lesson, so the early parts are half forgotten. One form after every lesson since lesson 12 |
| **Lesson records** | `lesson_manifests/` (plan, script, transcript, `learner.before.json`, arguments; the review backlog's breakdown, `review_backlog.json`) | Exactly what was practised and when. Replays can reproduce a lesson | What the learner noticed («I didn't hear "kaupa miða"») |
| **Owner observations** | Issues, chat, transcript reviews | The richest qualitative signal: what felt wrong and why | Whether a single remark is a pattern. Check it against the data and §9 |
| **Simulations and replays** | `tools/replay_lesson.py` (an export's lesson rebuilt and continued; the daily table), other scripts in `tools/`, tests | Planner behaviour under stated assumptions; cheap before/after comparisons | Anything about learning. A simulation from scratch can differ from the real path (§5.4) |
| **Native corrections** | When they come (#129) | Correctness and naturalness | — |
| *Not a signal* | LLM transcripts or assessments | — | Everything (#129) |

### 6.2 Reading the signals

- **Small numbers.** One learner and about twenty-five lessons. Look for patterns that repeat
  across items or weeks before changing a lever (§10). One lesson is a lead.
- **Time confounds everything.** The learner keeps learning, the curriculum gets harder and
  several things change at once. When a number moves, list the other changes made in the
  same window before crediting one of them.
- **A measure stuck at the ceiling says nothing.** All 言えた means either "fine" or "too easy
  to discriminate". Look at the harder instruments (scenario cards, new fillings, partner
  lines) or ask the learner. Asking is how «迷った» never being used got its explanation
  (§5.7).
- **Delayed beats immediate.** The next-day review is the honest one. Same-lesson success
  and immediate impressions overestimate (H2, H10).
- **Candidates are prompts, not diagnoses.** "Same situation twice" was confirmed, but the
  cause was something else (§5.3). Ask what the learner meant before building a fix.
- **Replay the real path.** Reproduce the lesson from its `learner.before.json` and
  arguments before trusting a simulated course (checklist in §1).
- **Proxies drift from the outcome.** Retention, item counts and candidate counts are
  diagnostics. The readiness of scenes (O1–O4) and the routine (O5) are the outcome.
- **«Light» with «repetitive» or «pacing» is first about content.** When the form marks the load «light» together
  with «repetitive» or «pacing», suspect what filled the lesson's spare time before the amount of new material.
  Lesson 20 was «light» at its full target, with an eight-minute stretch of recombination and reviews (§5.16). The
  two-«light» rise (#229) stays as decided. Lessons 21–26 were «right» six times running, but the content and the amount
  changed together: the spare time went to things to hear (#247, #252), and the target rose from 9 to 10 at lesson 21
  after two «light» (#229). The two can't be told apart ("Time confounds everything" above).

### 6.3 Questions the next weeks of data can answer

| question | hypothesis | where to look |
|---|---|---|
| Does next-day recall of new lines stay at about 80% or better at the pace actually used? Lessons 15–25's new items: 5/9, 7/8, 6.5/8, 8/8, 8/8, 8/10, 4/11, 10/13, 10/13, 10/10, 9/9 (§5.14–§5.22; earlier 19 of 19, §5.8) | H9 | Review outcomes for the previous lesson's new items |
| ~~If next-day recall stays near 100%, is the limit now boredom rather than load? Would the learner take more new items?~~ Answered: lessons 18 and 19 «light» at 81–100% next-day success; the pace rule changes (#218) | H9, H12 | — |
| After the bump to #153: does any reviewed item come back three times or more in a lesson, and do the forms still say "repetitive"? | H11 | `/lesson-week` «レッスンの中身»; the forms |
| Do phrases of three or more words keep failing more often than short ones? | G9 | Failures by phrase length |
| Does the learner use «迷った» when unsure? At first no (§5.7); since lesson 14 it is used, though not in every review (§5.12–§5.20) | H10 | Review outcomes per lesson |
| Is recall confirmed after a real gap (7 and 14 days) about as good as next-day recall? 8 of 8 so far at 3–13 days, none yet at 14+ (§5.22) | H1, H2 | The daily read's retention row by gap (#298) |
| Are lines practised in situations rated better in scenario cards than lines practised only from meanings? | H3 | Scenario cards against each line's stage history |
| Once lessons are built around a scene, does "repetitive" go away, and do themed scenes reach readiness sooner? | H4 | Feedback forms; readiness per scenario, themed or not |
| Do respond cards with unknown partner words improve over the weeks, and does the learner find them useful or discouraging? | H8 | Scenario cards; ask |
| Do items introduced in the same lesson as a set (numbers, colours) fail more often than others? | H5 | Failures by introduction context |
| ~~Is a lesson that ends a few minutes short better than one filled with new material?~~ Answered: fill it, with things to hear, and say that not everything has to be memorised (§5.7) | O5, H9 | — |

---

## 7. Where the design falls short today

The gaps as found, with where each stands now. A closed gap stays listed: the evidence column says why it was a gap,
and a regression would show up as the same symptom.

| id | gap | evidence | outcome / hypothesis | now |
|---|---|---|---|---|
| **G1** | **We don't read our signals routinely.** Decisions follow single remarks; there is no weekly comparison of predictions with data, and the readiness summary isn't used in decisions. | §5.3, §5.6 (at the time: one feedback form) | all; §10 | Mostly closed: the daily read after every lesson (§1, `tools/replay_lesson.py`) and `/lesson-week`; «sooner» moves the schedule (#222). Open: retention after a gap has only just started to be measured (#298) |
| **G2** | **Lessons are assembled from an item count and an urgency queue.** Practice is bunched after each introduction, reviews have no shared scene, and the only coherent chunks are dialogues and exchanges. | §5.4; the owner after L12 | O1, O5; H4 | Closed for the lesson's exchange: a theme in every lesson (#149), scene units through it (#273), expression first (#265). **Open for new material:** the day's new items are grouped and the played scene matched where a theme has a level for them (#329), but the levels run out at lesson 28 and items whose topic has no theme get no scene line; lessons 23–26 took 0, 4, 0 and 0 new items from the played scene (#327; §5.22) |
| **G3** | **No natural-speed listening in the daily audio.** Partner lines come at one speed and in one wording (since #134 the theme exchange's partner lines vary: each play uses other words). | §5.5; #134 ("now the top pre-trip gap") | O2; H8 | Closed in the audio: partner lines in variants (#189), heard scenes, pick-outs and catch tasks in the second half (#252, #255, #271, #303) |
| **G4** | **The pace isn't the number of new items.** Extra arcs add up to half the pace again, and before PR #153, without limit when the fillers ran out. The load seems to follow weighted new components (a lead from four lessons, #218). | §5.2, §5.15 | O5; H9 | Closed: weighted new components are the pace's unit (#218, #235) |
| **G5** | **Semantic sets can arrive together.** The trip ordering and curriculum order can put a whole set (numbers 6–19, colours, languages) into one lesson. | Lesson 8 (numbers); a replay from lesson 12 with a scenario holding numbers 6–19 boosted: five numbers in lesson 12, nine more in lesson 13 (an experiment from PR #154's first version, not in the repository) | O1; H5 | Bunching capped (#204, #207). Numbers come through the pick-outs (#213, folded into #248) |
| **G6** | **Plausibility rests on slot tags.** Implausible or ungrammatical sentences can still be generated: «Hvenær opnar ísskápurinn?» before PR #155, and «Ég vil blár.» (the colour should be accusative). | Found after L12 | O1; H7 | Open; read on generated sentences in the replays |
| **G7** | **Three schedulers.** The audio's learner model, the Discord review queue (its own 1→3→7→14→30-day steps) and the card queues each decide what comes back, and their combined effect has never been examined. They are separate kinds of evidence by design (#129), but the learner experiences their sum. | Bot README | O5; H10, H11 | Open: the written review's own rules (site_update_notifier#132, #133, #312) and #220's ranking |
| **G8** | ~~The self-report scale may not discriminate.~~ Mostly binary (§5.7), but «迷った» is used in some reviews and counts as half a failure in the pace: a third value, read as such (H10). | §5.2, §5.7, §5.14, §5.15 | H10 | Read as a third value |
| **G9** | **Long phrases fail most.** Three-word-plus formulas get the same treatment as short ones. | §5.2 (9/24 vs 2/27); §5.8 (5/13 vs 2/13), all failures in the heavy early lessons | O1; H1, H9 | Open: watch |
| **G10** | **Content isn't native-reviewed.** All the scene lines, partner lines and glosses are candidates. | README | O1–O4 | Open (#209) |
| **G11** | **Practice is allocated by stage, not by need, and a failure is forgotten fast.** Each new item gets the same ladder and about the same time whether it is easy or hard; items marked 言えなかった last review get one or two practices; older failures return to presumed success with no confirmed recall in between. | §5.10 (21–41 s each against 77–199 s for new items; «Fyrirgefðu»: failed twice, then 0 confirmed recalls in 8 lessons); §5.3 | O1, O5; H1, H2, H11 | Partly closed: open items are practised every lesson and asked at the next review (#162, #205, #220); ease rises from recalls after a long gap (#298). Not built: less practice for an easy new item than a hard one |
| **G12** | **Scaffolds don't fade.** The English situation and the "you've said…" line are played in full every time, in at least five exercises of one lesson, although the learner knows the line; only the partner's line has a limit on how often its meaning is given. | §5.10 | O5; H3, H8 | Partly closed: a situation narrated in full at most twice (#170); the cue in every play (#210) |
| **G13** | **Nothing checks that a part is taught before the whole.** «Hvenær leggjum við af stað?» can come before «Hvenær?». | §5.10 | O1; H5 | Superseded for parts: a part is now introduced inside its whole, never first (§9 "Parts against utterances", #254, #262). For an utterance such as «Hvenær?» the `prereqs` data check is not built |
| **G14** | **Short items are drilled alone.** A new item of one or two words is recalled by itself six to nine times in a lesson, often within minutes, and rarely inside a sentence; when it is, it is the same sentence. | §5.11 (lesson 13 replayed after the batch); §5.1 (lesson 6, «vegabréf») | O1, O5; H3, H6, H12 | Closed: parts live in sentences (#170, #187, #239, #262, #277) |
| **G15** | **Generative supply is tiny.** After 12 lessons the learner knows 3 constructions; known constructions × known fillers give 6 sentences. A lesson that has run out of sentences repeats words, and the cap on bare repeats (G14) lapses. The course has no negation operation, and questions exist only as a late transform. | #171 (counts from lesson 13's export); #170's replay (cap lapsing in lesson 13, 7 of 9 short items without a sentence in lesson 15) | O1, O5; H6, H12. Revised by the concept (owner, after lesson 20; §3, §9 "Good enough overall"): supply matters only as parallels of target expressions; more generation is not a goal (lesson 20's boring stretch was generated sentences, §5.16) | Revised: see the outcome column |
| **G16** | **Concept 2 and 3 have no exercise.** Finding the information in what is said, and pinning down the unknown word, are two of the four things the lessons should leave the learner able to do (§3), and no exercise trains them; the time after the target went to recombination and reviews instead. | §5.16; #247's replay of the lesson-20 export (3.5–4 unserved minutes, runs of 8 and 17 generated sentences) | O2, O5; H8, H3 (#248) | Closed: #252, #255, #271, #303 |
| **G17** | **Material with one version repeats, within a lesson and across lessons.** The learner state records what was heard (`heard_utterances`) and the lines taught (`learned_wholes`), but no rule uses that record to limit repetition across lessons, and a listening task's memory ends with its lesson (#339), and a line authored as a fixed phrase has only one wording to give. The catch task asked the same three words in every lesson from 23 to 26, the same two pick-outs came in every lesson from 25, and «Fer þessi strætó í miðbæinn?» was said 8–9 times identically in lesson 26. | §5.22 (the owner after lesson 26; the bus); the replay of lessons 27–28 | O5; H8, H12, H6 | Open: #339 (a word caught once, pick-outs rotate), #336 (lines that vary as patterns) |

---

## 8. Roadmap by expected impact

The long run below is ordered by the expected effect on the outcome, adjusted for cost and for what depends on what;
"Now" is ranked as its heading says. Re-rank both when the evidence moves.

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

**Built, waiting for three feedbacks without the same remark** (the rule for "done" is below the table). What each
change does is in the §5 subsection of the lesson it was first heard in. Done this way since lesson 25: the changes built after
lessons 21–23 (§5.18–§5.20) have had their three.

| built (issue: PR) | first heard | feedbacks without its remark |
|---|---|---|
| a hard word's slow, split model (#212: #292) | not yet: the words the learner found hard in lesson 26 were not flagged (#337) | – |
| a gap at every change of voice (#301: #304) | lesson 25 | 2 (25, 26) |
| the «Slowly» model word by word (#302: #307) | lesson 25 | 2 |
| the pick-out names what to listen for first (#303: #306) | lesson 25 | 1; lesson 26 remarked on the pick-out's flow, the turns after the line (#335) |
| a pattern-linked phrase with a new word teaches the word in other frames; no phrase introduced twice (#311: #316, #318) | lesson 26 | 0: the same family came back as the bus with one destination, a phrase with no pattern to link (#336) |
| the written review in its own words, no lesson cue (#312: #314, with the bot's `REFINE_VERSION` 3, site_update_notifier#137) | lesson 26 | 1 (26) |
| the review backlog: a first 言えた waits 3 days, answered-once entries deferred (site_update_notifier#133: site_update_notifier#134) | lesson 26 | 1; due 151 → 114 |
| a new scene or reading card every review (site_update_notifier#132: site_update_notifier#135) | lesson 26 | 1 |
| a grammar note's endings said piece by piece; no lone «.» narrated (#198: #323) | lesson 26 | 1 |
| new material grouped by scene, the played scene matched (#327 part 1, without its scene line: #329) | lesson 26 (a replayed level: 0 of 10 inside it) | 1 |
| a hard item practised through its connections; «sooner» marks it hard (#326: #330, #332) | lesson 27: the «sooner» items of lesson 26 are its first real case (lesson 26 had one hard item, practised once) | – |
| a recall at a real gap extends the interval (#220: #331); the bot's ranked seats, at most a third (site_update_notifier#139) | lesson 26 | 1 |
| gender and form for every case-tagged noun (#270 step 1: #317) | no remark expected; read in the nouns row | – |

Read from rows, not from remarks: the second half kept when an item counted toward the target is not taught (#294: #308);
ease learned from long-gap recalls (#220: #298, with site_update_notifier#118, #128); the review backlog's breakdown
(site_update_notifier#125).

**To check on the next lessons:**
- A split hard word: the «sooner» items of lesson 26 (#337).
- The review backlog: 114 due after one day of site_update_notifier#133; about 100 expected, and the 3–6 day retention
  count growing.
- A sentence asked again within a minute: 6 in lesson 26 (lesson 25: 1), a trend to read, not a 0.

**Decided by the evidence:** the pace unit stays. **The 60% rule** (revisit #235's zero cost for a new phrase made of known words if
next-day recall fell below about 60%) was set for lesson 22, after lesson 21's 4 of 11 (#264). It never fired (§6.3 has
the series), and the owner closed it on 2026-10-15: the zero cost stays without further review.

A change is done when its row in the daily read (`tools/replay_lesson.py`) reads its target on the replay (0, except
where a row says otherwise: rows 8, 10 and 12), and three feedbacks
after it carry no remark of the same kind (the table above). The rows:
1. minutes after the target that serve neither a target expression nor a scene (`spare_unserved_s`, #238);
2. lines a listening scene asks for that were never taught (`listening_untaught`, #240);
3. items the audio asks that the same morning's review asked (`asked_after_review`, #238);
4. framing lines followed by an example without a beat (#241);
5. review questions whose answer is a part beside its whole, or that share an answer with another question (#239);
6. pick-outs whose line holds nothing but a drilled frame and the answer (#255: `pick_out_echo_count`);
7. review questions asking a part bare although it has a home (#262: `bare_parts_with_a_home`), and nouns asked bare in
   the lesson's own recall (#270: `bare_noun_recalls`, widened to every vocab part with #277: a part's sentence is asked, `do_recall` no longer keys on `noun`);
8. the longest stretch without a scene, at most about 5 minutes (#273: `longest_without_scene_s`);
9. questions whose cue is their answer, in the lesson and in the review (#277: `trivial_questions` in the lesson, `trivial` in `review_refined`);
10. a sentence asked again within a minute (#273: `asked_again_within_spacing`, keyed by the answer; a soft preference, so
    read it as a trend, not a 0);
11. recombine prompts promising a link that is not there (#287: `unkept_links`);
12. lessons whose target is not delivered, and whether the second half started through the guard (#294: `meta.target_delivered`,
    `meta.rotation_guard`; a row of `replay_lesson.py`: «yes», «guard» or «no», #310);
13. speech segments that touch at a change of voice (#301: `meta.touching_switches`, 0 expected; a row of `replay_lesson.py`, with the count of gaps inserted next to it, #310).

**Open issues after "Now", in order:**
- #333, the lesson-26 preview's findings. None of them is in the replay of lesson 27: the transport phrases come back
  at their reviews. Small. «Má ég sofa?» waits for the owner's call (a named exception or a slot tag).
- #209: when a fluent speaker is available (G10). It is worth more now that #255, #257, #276, #292, #317 (genders and
  forms) and #323 (a grammar note) added authored Icelandic, and it holds #279's step 2; #327 part 2, #336 and #337 will add more.
- #236: a one-off reply gets several example answers (owner: low priority).

#265 (expression first), #149 (themes) and #270 (a noun with its gender and forms; its step 2 is what the tags already
do, #317, #324) are the umbrellas the items above belong to; #220 stays open for its ranking
(the bot's review on its own, site_update_notifier#124, waits for it); #326 for the connections across lessons.

**The long run: the bets in order.** What each step has built is listed here; the rules it settled are in §9.

1. **Make the loop measurable and use it (G1).** Built: `/lesson-week` (site_update_notifier#59, #62), the daily read
   after every lesson (§1, `tools/replay_lesson.py`), and retention by gap (#298). Ask the learner when a signal is
   ambiguous (as with «迷った», §5.7).
2. **Build lessons around a scene (G2, G5, and G3 through partner turns), in steps (#149).** It is the main bet (H4),
   and since 2026-10-03 the frame of every lesson (§9 "Themes"): the theme comes first, and items, reviews and spare time
   serve it. Built:
   - the theme exchange played twice, the cue in both plays, the partner's lines in variants at natural speed (#186,
     #189, #210); a theme in every lesson, a played level replaying after a rest (step 1); the theme's next level first
     for new material (step 2a, #201), and the day's new material grouped by scene with the played scene matched when
     the level has none (#327 part 1, without its scene line: #329);
   - a part with its frame and inside its whole (#202, #254, #262, #293); a fixed phrase linked to its pattern (#192,
     #206); a cap on new items of one semantic set (#204, #207; its exceptions in H5); `prereqs` across items (G13) is not
     checked;
   - words in sentences, and today's items coming back by time (#170, #187, #239; the rules in §9 "Repetition");
   - spare time as more to hear, and the second half's scene units (#247, #252, #273);
   - an open item practised every lesson and asked at the next review until it is recalled (#162, #205, #220).

   **Next** (#149): a scene line for new items whose topic has no theme, and more theme levels for café, directions and
   town, taxi and bus, small talk, and winter talk with #142 (#327, the long run alongside "Now"); the colours through
   their scenes; the closing block taking the theme's lines. Still
   open from this step: less practice for an easy new item than for a hard one (G11); the English situation dropped
   once the partner's line is known (G12); a word that hearing counts when the previous review had many 言えなかった
   (§5.7, O5).
3. **Plausible substitution inside the scenes (G6).** Patterns serve the theme's exchange; scene templates keep
   fillings plausible (H6, H7).
4. **Content priorities, as data for the scenes.** Numbers: heard and picked out in scene lines (#213, folded into #248).
   Colours where signs and warnings use them (gul / rauð viðvörun, agreeing with the noun). The scene catalogue
   reviewed by the owner, and by a native speaker when one is available (G10, #209).
5. **Long phrases (G9).** Watch whether the pattern holds as more data comes in. If it does, give long formulas more
   scaffolding (the components unit, #218, already counts a phrase's new words).

**Not now:**

- more planner levers;
- content that no mechanism uses yet;
- new instruments before the existing ones are read;
- local fixes to symptoms that step 2 will remove;
- precision work (refining the unit, form checks, scheduling edge cases) while a twenty-point part is open in "Now".

---

## 9. Decisions already made

Don't reopen these without new evidence; when you do, say what changed. Each rule is stated as it stands. Several were
revised by the owner after lesson 20 to fit the concept (§3) and "Good enough overall" below; their earlier forms are in
§5, `docs/history/evidence.md` and git.

- **Good enough overall (owner, after lesson 20).** The learner's experience of the whole lesson is what counts.
  - Eighty points across the whole lesson beat a hundred on one part. A part that scores twenty, a stretch that bores
    or a contradiction the learner hears, is fixed first, ahead of any precision work.
  - Rules (tags, frames, schedules) cover about nine cases in ten. The tenth is declared by name, not met with a new
    mechanism: «Áttu leigubíl?» is a `false` of the scene check below while «leigubíl» keeps its tag (#192).
  - About one line in ten that a native speaker wouldn't quite say is acceptable. For a traveller from the other side
    of the world it costs almost nothing. Checks of linguistic detail (the BÍN form check, #234) advise and never block.
  - A lesson is about 30 minutes. Nothing is designed for other lengths (#218 b3).
  - Before a change, weigh what the learner will notice against the development time it takes.
  - **The scene check (owner, 2026-10-16).** A sentence a pattern makes must have a scene the learner can picture;
    grammatical is not enough. «Ég nenni ekki að sofa.» (lesson 27), «Má ég sofa?» (#333), «Áttu leigubíl?» (#192) and the
    bus «to the bus stop» (#336) were each found by chance, one at a time. Each fill of a pattern gets a verdict once, all
    in one place (`[scenes.<pattern>]`, `curricula/is-en/95-scenes.toml`): a scene in one line, which the lesson uses as
    the cue for that sentence under the rule of any situation ("Repetition" below), or `false`, never generated. A sentence with no verdict is still generated; `validate`
    counts them, and `audiolesson scene-check` prints the sheet to judge, the patterns the learner has met first
    (`docs/SCENE-REVIEW.md`). It replaces the named exceptions to generation, which were this check done by chance.
  - **Named exceptions** are listed here, in one place, so they can be read together and don't grow into mechanisms:
    - «Ertu með regnhlíf?» is not an instance of «Ertu með {condition}?» (`not_instance`, #333): the same words, not the same meaning.

- **Pace.**
  - It never depends on the departure date. Lessons go on at the same best-effort pace before and during the trip,
    throttled only by what the learner reports (owner; #129, #131): recall over the last three reported lessons (up at
    ≤ 15% failures, down above 25%) and the feedback form's load rating (`report --load`; #218 part a, built).
  - **The unit is weighted new components, not new items** (#218 part b, owner, 2026-10-08; built, #235). An item costs
    the sum of its new components: a new word, a chunk the curriculum treats as one item («taka mynd») or a new pattern,
    its frame's new words included, 1; a new form of a known word w (fitted from next-day failures, 0.5 to start); a
    combination of known parts 0. A pattern counts 1 the first time even when all its words are known («Hvað kostar
    {item}?» after «Hvað kostar þetta?»); a frame inside a known pattern is a known part («klukkan {hour}» after
    «Klukkan er {hour}.»). From #218 b3 a variant counts at w against the target, like any other new form («þrjá» after
    «þrír»).
  - The pace is throttled by what needs review: a learner with much to review gets less new material because the
    lesson is full.
  - **Close variants** (`Item.variant_of`: another case, another gender of something the learner knows) no longer fill
    spare time (#218 b1, owner 2026-10-09; before, up to four came in beyond the pace, #170). A form comes in only
    when the theme's next level wants it (#201) or a frame or phrase pulls it (#202); the trip and course orders don't
    take it. They are listed apart in `plan.json` (`variant_items`).
  - A heard-only play of a played theme level (spare time) takes any variant of a partner line, untranslated, as
    natural-speed exposure (H8); a replay's early play still takes only wordings heard with their meaning (#196).
- **Evidence.**
  - Presumed success is kept apart from confirmed outcomes (#119).
  - The last lesson's new items are reviewed before the next lesson is generated (bot).
  - Every open item the plan lists (`open_items`, `open_not_fitted`) is asked at the next review, like the new items' check
    (#220; owner, 2026-10-08). The plan carries a question for each (`cli._plan`); the bot makes one question per item required.
  - `knows()` means two recalls on or after a due date (#27).
  - A recall confirmed after a real gap is the evidence of retention: one after 7 days or more raises the ease and
    extends the interval, so what is easy for this learner is learned from their answers, not guessed (#220, #298).
- **Daily dose.** A lesson uses its full requested time, with material that loads the learner
  (owner, after lesson 13: a light lesson wastes a day's consolidation). The number of new
  items is a means, not the plan. An item the learner failed is respected until it has been
  recalled again, not for one lesson only.
- **Sequencing.**
  - Sequence from capabilities outward. High-value reusable material comes early (#29).
    The owner: teaching "the high-value words that come up in conversation and should be
    usable" is "the top priority of the whole app".
  - No prerequisite gates bolted onto dialogues (#25).
  - Never an exact dialogue line as a memory item, just because the representation can't
    yet express the pattern behind it («held ég», #54 review). The test is whether the
    learner gains a reusable model, not whether a diagnostic comes out clean.
- **Themes (owner, 2026-10-03; #149).** Every lesson after the first is built around a theme: a
  scene of the trip as an exchange, at rising levels. The theme ranks above the item count and
  above the trip order of single items: new material is chosen for the theme's next level, and
  a lesson with no new level ready replays one already done rather than going without. Why:
  words, sentences and exchanges are more enjoyable, and easier to place, once the learner can
  picture the whole conversation (O5; the "Anki game" of lesson 13, §5.10). This settles H4's
  place in the plan; whether it works is still read from the signals in H4's row. Reopen it if
  themed lessons are still felt as unrelated items, if next-day recall of new lines drops, or
  if themed scenes don't reach readiness sooner than unthemed ones.
  - **Exception: numbers (#213, folded into #248; owner, 2026-10-09).** Whatever the theme, prices, times and counts
    are *heard* at natural speed in scene lines and picked out (#248's *pick out the information*, concept 2). Saying
    them is limited to the target expressions that need them («Tvo fullorðna, takk.»). A spoken number track, a fixed
    share of every lesson, was dropped: lesson 20's boring stretch held «Það kostar … krónur» ×3 and «klukkan …» ×3,
    the shape such a track repeats (§5.16).
- **Conversation.**
  - **Catching an unknown word (owner, 2026-10-15; #339).** A word is asked about with «Hvað þýðir …?» about once,
    not in every lesson. About one new word in ten is introduced in this form, in place of its usual introduction, the one
    inside its whole included (owner, 2026-10-15): the partner's line in the word's scene (else the sentence its
    introduction would have taught it in), the learner asks, the meaning, the line again, then the word's usual practice.
    The others keep the usual introduction.
  - An exchange's target-language turns must form a plausible conversation with the
    instructor lane removed (#48).
  - `connect` without an authored bridge is mixed review, and says so (#78).
- **Repetition.**
  - New items may repeat within a lesson and are never dropped (#147).
  - Situation variety is welcome (#148), but a situation, authored or a scene check's line, is narrated in full at
    most twice in a lesson; after that the cue is the meaning, or the partner's line (G12; #170). One just narrated
    (among the last three, #273) is avoided whenever the cue has another way: another variant, or for a scene line the
    sentence's meaning; an item practised at the situation stage has none and hears it again. One rule for both: a
    scene line shared by many sentences was read 14 times in a lesson before it counted (review of #361).
  - **Parts against utterances (#187, #190, the owner's decision; revised after lesson 20).** What is not a complete
    utterance is a *part*, whatever its length: «peysu», «kaupa miða», «fara á safnið». The data draws the line: every
    slot filler has `kind = "vocab"` and no `phrase` is one.
    - A part is introduced inside the target expression that holds it: «Takk fyrir hjálpina.», not «hjálpina» 'for
      help' (lesson 20). It may be said alone afterwards, never first (#239: `Builder.whole_home`, `_intro_in_whole`).
    - The line a part was taught in is kept across lessons (`learned_wholes`). The lesson's own recall and the review ask
      the part through a sentence (a pattern with a slot, its `context` sentence, or a phrase that holds it) wherever
      one exists, the closing included (#269, #270, #276, #277; `review_wholes.refine_review`; DESIGN.md "A part lives
      inside its whole"). Bare is the fallback only when no sentence exists yet, and then the bare cap below applies.
    - A question whose cue says its answer (a name, «krónur») is never asked.
    - An utterance («Hvenær?», «Vá!», «Takk.») is a complete thing to say, so a scene that calls for it is its proper use
      and may repeat: situation turns and mixed review don't count against its cap, only a meaning-cued bare recall
      does; it still prefers a sentence that holds it when there is one.
  - **Identical sentences are counted too (#192).** The owner's rule is that a sentence may come five times or more, and a
    word about ten times in all *if the sentences differ a little*. The word-level rules (the bare cap, the situation
    narration, the pattern ceiling) never counted a fixed sentence that is said identically. `Builder.said` now counts every
    model answer (the repeat after the model included), an introduction once and a dialogue's partner lines. The repeat after
    the model teaches only for a line's first asking in a lesson (`echo_asked`). A sentence said `max_sentence_utterances`
    (6) times is practised in another sentence that holds it where there is one (a preference, not a cap: dropping the
    practice leaves the lesson idle and lapses the caps, G15), and a mixed-review pair avoids the item just practised and
    sentences past that count.
  - **A fixed phrase that is an instance of a pattern is linked to it (owner, 2026-10-04; #192).** «Þrjá miða, takk.» is
    «{count} miða, takk.» with «þrjá», «Einn fullorðinn, takk.» is «{party}, takk.» with «einn fullorðinn»; the link is data
    (`instance_of`, `instance_fill`, checked to make the phrase exactly). Once the pattern is known, a phrase past
    `max_sentence_utterances` is practised in another sentence of the pattern with other fillers («Tvo miða, takk.»). **Credit
    goes one way only:** the variant is credited to the pattern and its fillers, never to the phrase, whose own review is
    checked in its own form. The patterns and their accusative number forms are candidates without native review (G10). The
    party fillers are whole units («tvo fullorðna»), since the noun's form follows the count and the pattern has no
    agreement machinery. **The introduction too (owner, after lesson 18; #192, the rest):** a linked phrase whose pattern and fillers are *known* (`knows()`, not the weaker `_frame_available`) is not introduced as a new item with a ladder (8 exercises for «Get ég fengið kvittun?» in lesson 18): it is played once as a sentence of its pattern, credited to the pattern and its fillers, kept in `new_items` and decided by the next day's check, like an embedded part.
  - **Never ten identical (owner, 2026-10-04; #192).** A fixed phrase is said at most `max_sentence_hard` (9) times in a lesson, while the
    caps are on: its practice is handed to the pattern's other instances where it is linked, and dropped where no other sentence holds it.
    A new item keeps its closing recall, unless an earlier sentence of the closing has just said it. Repetition inside a scene is still fine up to the cap. On lessons 14–25 of the replay the most-said
    sentence was 9–11 and is at most 9 throughout; a linked phrase whose pattern is known stops at 7.
    **The hard cap and the bare cap conflict whenever both bind** (owner review of #206, lesson 23 of the lesson-18 path: two phrases at 9,
    and the freed practice went to a bare part past the bare cap). The freed time is not given back to bare words: a lesson under
    180 s short because of the hard cap ends there. A cap value per path would only hide it (8 lapsed on the lesson-14 path, 9 did not).
  - **One admission rule for a part (owner review of #206).** A part is not introduced alone when a frame or a phrase that holds it can
    come with it, on every path (theme target, trip order, extras, variants) — a variant part (`þrjá`) was drilled bare through the
    extras path, the same shape as the lesson-17 feedback about numbers 1–4 asked without gender or scene.
  - **Not-due items wait for their date (#94),** with one exception: a not-due item may come early to fill spare time,
    or to space out the introductions of a later arc of new material. Those rested at least half their interval come
    first, and the scene's own items before others; never a stable item (#151) or one the morning's review asked
    (#238). Time on an item outside the scene counts as unserved (§8, row 1). The order of these fillers is in
    DESIGN.md "Spare time serves the scene and the ear".
  - **Exception: `refresh` (#175; revised after lesson 20).** A known construction that carries `refresh` comes back as a
    light sentence with *changing* parts when it is a parallel of a target expression in the lesson's scene, not as a
    standing share of every lesson. It is not the #94 / H11 bug (já, nei, hæ coming back unchanged): the owner wants
    the pattern with different fillers, and what is unwelcome is the bare repeat.
  - **A construction's question or negative is modelled once before it is asked (#211).** A generated sentence takes a form of
    construction c only when the learner knows c and the form was modelled to them, in an earlier lesson or this one («You know this
    one:» the plain sentence, «As a question:» the same sentence, then another filler, asked without being spoken first). The teaching note alone
    unlocks nothing; one or two forms are modelled a lesson, by trip priority. `learner.forms_modelled` is the state; a file from before
    it is seeded from `heard_utterances` (accepted by the owner on the review of #232, also for constructions not yet known; a clean start would lock every form used since lessons 14–15). If the
    generated-sentences row does not recover over three lessons, relax the gate to «met in an earlier lesson» (the issue's own fallback).
  - **`refresh` constructions are taught as trip items once cheap (#180, owner's choice of
    traveller-core patterns).** A cheap one (every slot has ≥ 2 known fillers, prerequisites known)
    competes with the cheap trip constructions on the same terms and goes to the front of the trip order,
    one a lesson, taking one new-item place.
    A prerequisite that is only a filler of the construction's own slot is covered by the slot's known
    fillers; «Má ég {inf}?» no longer waits for «Ég verð að» (the modal family stays in its milestone, and
    similar items are better met apart, H5).
  - **A pattern is not a lesson's whole supply (#180).** A word's sentences rotate through its homes, the
    pattern with the fewest this lesson first, and a construction has at most about ten generated sentences
    in a lesson (the owner's «about ten times» in «Identical sentences are counted too» above, extended to patterns).
  - A short item (a word, or a one-word question such as «Hvenær?»; sentences and full
    questions of two words are not short items) is said alone at most **three** times in a lesson (for a part: only
    while no sentence holds it, see "Parts against utterances" above); the rest of its practice is inside sentences,
    preferably different ones, up to about **ten** uses in all (owner, after replaying lesson
    13, §5.11). The numbers are a starting guess, not evidence: tune them with the learner's
    remarks.
  - **Order of the two rules (#170).** When even listening dialogues, heard-only plays of a
    played theme level (#218 b1: spare time is more to hear, not a filler form), open
    practices and substitutions leave the lesson short, the cap lapses and the dropped recalls
    come back (`bare_cap_lapsed`): the daily dose above ranks over "alone at most three". A
    graded lapse (4, then 5…) would keep more of the cap; it is the owner's call. A substitution fills time only as a
    parallel of a target expression of the lesson's scene, never as a run of known patterns (revised after lesson 20).
  - **"Can the learner say it?" is judged per line (#179).** A line is sayable if its item is
    met and not open, was practised this lesson, or the line is covered, in order, by chunks the learner can say
    («Það kostar | fimm | þúsund krónur.»); `knows()` is a scheduling notion, not "can produce". A sayable line in a listening
    dialogue is asked with its pause (a heard line has no task cue), and a short item already said
    in a sentence this lesson is asked in a sentence at the closing, not as a bare part.
  - **A listening scene asks only for lines that were taught (#183, revised after lesson 20; #240).** A line the learner
    can say in full is asked with its pause. A line with an untaught part is heard, with its meaning, and not tried
    (lesson 20's bus scene, §5.16); the same holds in a theme's play (owner, 2026-10-09: an untaught line can't be said
    at all). #183's tried lines and their next-day bonus questions are retired; the daily read's row stays at 0.
- **Generation and audio.**
  - Only plausible sentences in plausible scenes (owner after L12).
  - No pause stretching to fill a short lesson (owner after L12).
- **Instruments.**
  - No LLM partner or grader (#129).
  - Native corrections are applied when they come, untracked. Outside learning is not
    tracked (owner).
- **Governance.**
  - At most two lever changes a week, and only on a pattern across three or more items or
    two consecutive weeks. **Suspended during the fix-up phase (owner, after lesson 14):**
    while lessons are being reshaped after the lesson-13 failure, each lesson is read the next
    day (§1), faults are fixed in batches and checked by replaying the latest export, and the
    batch is judged as one change (§5.11). A change merges when the daily replay shows nothing
    already fixed coming back (length, a short item alone at most three times, open items
    practised). Slow signals (recall rates, phrase length, readiness) gate only the decisions
    that depend on them, not development. Back to the weekly rule once the lessons settle.
  - **Priorities (owner, 2026-10-14).** About 80% of the work goes to the next lesson and 20% to the long run. §8
    "Now" is ranked by the effect on the next lesson, checked on the replay of the latest export; the owner approves a
    re-ranking by merging the PR that makes it.
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
  The lever rule in §9 applies to behaviour changes generally, not only to levers, except in
  the fix-up phase (§9 "Governance"), where a batch is judged as one change.
- **Waiting is not a task.** A read that needs several lessons of data never sits in the queue
  of work ahead of development; it accumulates alongside the daily read (§1).
- **An owner request is evidence of a need.** Restate the need in terms of §3 and §4, look
  for the cause shared with other recent requests, and fit it into §8. If it is a principle
  ("never implausible"), record it in §9. If the request conflicts with a hypothesis or the
  evidence, say so before building it. Agreement is not the goal; the learner's outcome is.
- **Acceptance criteria describe the learner's experience** and are checked on the real
  path (§1).
- **Keep this document true.** §1 says when §4, §5 and §8 are updated; §9 changes when a decision is made. Write
  lesson numbers and issue numbers, never trip dates.
- **Documents: replace, don't append (owner, 2026-10-15).** Left to one writer, an LLM in particular, these documents
  grew from a first version of 569 lines to 1701 in two weeks (1722 lines added after it, 590 deleted), and the additions left contradictions
  standing. So:
  - A change to a statement rewrites it; it doesn't add a sentence after it. The history is in §5, the archive
    (`docs/history/evidence.md`) and git.
  - A PR that changes a document names what it replaced or deleted (the PR template asks). Net growth needs a reason.
  - §5 keeps the last three lessons; "Now" holds three or four items (§1).
  - An independent review, by a model from another company, reads the documents for contradictions, stale statements
    and duplicates (`docs/DOC-REVIEW.md`). It reports and doesn't edit; the fixes are a PR, and the owner settles a
    disagreement. Run it after every five lessons or so, or when the owner asks.

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
- **Polishing parts while the whole disappoints.** After twenty days of daily feedback loops, lesson 20 still had
  about eight minutes of easy, random repetition, and a listening scene that asked for lines never taught (§5.16).
  Development time had meanwhile gone to the pace's unit, form checks and scheduling edge cases. The owner: a strict
  hundred on a part is worse than eighty overall (§9 "Good enough overall").
- **An example taken for the requirement.** The owner illustrated a point with one kind of line (an announcement heard
  by chance), and the issue first wrote that example in as the rule, instead of the need it showed (#303, rewritten from
  concept 2). An example in a remark is evidence of a need; restate the need (§10) and check the example against it.

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
