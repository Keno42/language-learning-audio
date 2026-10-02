# Design notes

What a contributor, human or AI, needs before changing the planner or the curriculum:
where things are, what the tests hold in place, and why the big decisions went the way
they did. Why the project exists, what it is betting on and how to decide what to change
next are in `docs/LEARNING-DESIGN.md`; read that first. Open work is tracked in GitHub
issues; the full history of how each of these came about is in `docs/history/sessions.md`.

## Where things are

| concern | code |
|---|---|
| items, dialogues, notes, loading, `validate()` | `audiolesson/content.py` |
| stage ladder per item kind | `audiolesson/stages.py` |
| what to practise when: `Planner.build` (steps 0–5 are commented), `select_new` | `audiolesson/planner.py` |
| exercise shapes: intro, recall, recombine, `connect`, `dialogue`, notes | `audiolesson/exercises.py` (`Builder`) |
| spacing, durable learning, pace | `audiolesson/learner.py` |
| pause and speech-length model | `audiolesson/timing.py` |
| instructor phrasing | `audiolesson/phrasing/<lang>.toml` |
| script → audio, respellings for TTS | `audiolesson/render/` |
| written review questions for `plan.json` (`review`) | `audiolesson/script.py` (`Script.review_questions`) |
| post-lesson feedback candidates for `plan.json` (`review_candidates`, #128) | `audiolesson/script.py` (`Script.review_candidates`) |
| travel can-do scenarios and their coverage report (#131) | `curricula/is-en/cando/travel.toml`, `audiolesson/cando.py`, `validate --cando`; see `docs/TRAVEL-CANDO.md` |
| trip ordering from a private profile (#132) | `audiolesson/trip.py`, `cando.priority_items`, `PlanConfig.priority`, `generate --trip` |
| scenario cards for the Discord review (#129) | `curricula/is-en/cando/scenes.toml`, `audiolesson/scenes.py`, `audiolesson scenes` |
| reading deck for the Discord review (#133) | `curricula/is-en/reading/deck.toml`, `audiolesson/reading.py`, `audiolesson reading` |
| loading those record files (`cando/`, `reading/`) | `audiolesson/records.py` |
| what the instructor says for a meaning (`meaning_spoken`, #143) | `Item.spoken_meaning` in `audiolesson/content.py` |
| planner levers, off by default (#136) | `PlanConfig.late_unhinted_recall`; see `docs/LEVERS.md` |
| diagnostics | `audiolesson validate` (gloss coverage, dialogue sequencing report, part-before-whole report `--parts`), `tools/phrase_families.py` |

## Invariants the tests pin

Each of these was a real regression once; `docs/history/sessions.md` has the details.

- **Durable learning (#27).** `LearnerState.knows()` means two recalls on or after a due
  date. Recalls minutes apart in one lesson don't count. Dialogue eligibility is
  `knows(i) or i in builder.in_lesson` for every required item, never `has_met`.
- **Open failures (#149, 1a).** An item whose latest confirmed outcome is 言えなかった is
  open (`LearnerState.is_open`) until a later confirmed recall; presumed success neither adds
  a durable success nor lengthens its interval (it is due again tomorrow). Each lesson practises
  up to `max_open_items` of them, five times at fractions of the lesson time (`open_item_times`, by time not exercise count); the ones that failed last lesson go first, then the longest without an open practice (`ItemState.open_practiced`), and lists them in
  `plan.json` (`open_items`, `open_not_fitted`) so the bot can ask them.
- **Scaffolds fade (G12).** A situation recall of an item with `prompt_by` is cued by the
  prompting item's line in Icelandic, said by `native_b` (`Builder.prompt_item`): bare when the
  learner knows it and it isn't open, with its meaning on the first two hearings in the lesson
  when it was only introduced this lesson, met, or open, and the authored situation when it was
  never met. «Reply.» frames each cue unless the exercise before was one; the review question
  for it is the line itself (or its meaning). No authored situation starts by restating what the
  learner said.
- **Listening dialogues (#149 step 3).** With nothing else left (step 5, before today's items
  are repeated, or as the last drill-streak relief), a dialogue lacking one or two required
  items (`Planner.listening_dialogue`) plays whole: the turn for a missing item is «Here you
  would say:», the line, its meaning, with no pause for the learner. The missing items are never
  recorded (they stay unmet, never in the review) and a dialogue so heard rests six lessons
  (`dialogues_listened`).
- **Embedded parts (#149).** A vocab word with a slot to go in (`Builder.generate_with` finds the
  sentence) whose words sit inside an item the learner has met (not open), or met earlier in the
  lesson, is not introduced on its own (`Planner.embed_source`, the shortest such item):
  «You know this:» the phrase, «This word is in it:» the part, «In another sentence. Listen, then
  repeat.», the sentence, its meaning, the sentence again, a pause to repeat (`embed`). Nothing is
  recorded: `LearnerState.embedded` holds it until the review asks the sentence (`review_questions`,
  stage `embed`; the plan lists the part in `new_items` and `embedded_items`). Said back it is
  its first recall on a due date (one durable success, next in three days; `knows()` still takes
  two, §9); not said, `embed_failed` and the usual introduction later. `select_new` skips a
  pending one; `simulate_reach` counts it reached.
- **New material is spread over the lesson.** The k-th introduction waits until k/N of
  `intro_span` (0.75) of the lesson's time (N: the pace plus a later arc), so new items come
  every two or three minutes instead of all in the first half; a second arc starts on the same
  schedule (step 2b) instead of only when the lesson is idle. When the drill streak reaches its
  limit the relief is a dialogue, a note, a connect, a listening dialogue and last the next new
  item; an idle lesson still introduces early (steps 5), so a lesson with nothing else to do
  doesn't end short.
  An embedded part counts as an introduction on this schedule.
- **Generated sentences use only available parts.** A fill is known or introduced earlier
  in the lesson. A construction's `situation_fill` makes its situation wait for that fill.
  A dialogue turn's `expect_fill` binds every slot, so every spoken part is a required item.
- **No skipped stages.** `connect()` records a situation exposure only for an item that is
  at most one step short of `situation` on its own ladder (`_ready_for_situation`).
- **A drill streak never falls through to another isolated recall.** Step 0 tries a
  dialogue, then a note (with a small separate relief allowance), then `connect()`, and
  otherwise ends the lesson.
- **`connect()` is honest about what it is.** It's an `exchange` only with an authored
  bridge (`partner_cue_after`), played as one scene whose wording differs from both items'
  standalone situations. Otherwise it's mixed review (stage `recombine`, label
  `mixed review:`): `mixed_review_intro`, a neutral transition, never "put together" or
  "and then". It never replays a pair within a lesson.
- **Situations rotate (#77).** Every narration of an item's own cue, `connect()` included,
  advances its rotation, so a lesson repeats a cue only once every authored variant has
  been used.
- **Novelty is claimed only when true.** `recombine_new` requires `is_new_utterance()`:
  not presented this lesson, in an earlier lesson (`heard_utterances`), or as a met item's
  target.
- **A recombine exercise makes a new sentence (#105).** Its target was not presented
  earlier in the lesson. With only heard sentences possible, the planner practises the item
  at the hardest stage it already reached today instead (`recombine_or_instead`), so stages
  still never go down; a recombine already done today moves on to a usable situation, or
  else to a meaning recall. A new item is never dropped from a reactivation or the closing
  block: repeating it is fine (lesson 12 feedback), and the learner update takes the
  hardest stage reached, so the repeat is not a demotion.
- **Today's items come back by time, and a short one is said alone at most three times
  (G14, §9 "Repetition").** The recalls of a new item are scheduled at `intro_recall_times`
  (fractions of the lesson's time after its introduction, about 1, 3, 8 and 15 minutes of 30:
  `intro_timeline`, like `open_timeline`), played when due and never as the fifth recall in a
  row; an idle lesson pulls them early (step 5). An item of at most `short_item_words` words
  (not a construction or transform) introduced today has `max_bare_uses` bare uses
  (introduction, one early recall, the closing recall); every other practice of it is a
  sentence (`sentence_practice`): a known pattern with a slot for it (`recombine`), else a known
  phrase whose words contain it (`containing_items`), else nothing, and the recall is dropped.
  The one early bare recall is at `meaning` at least. When nothing else is left to fill the lesson
  (step 5, after the listening dialogues), the cap lapses and the dropped recalls come back
  (`bare_cap_lapsed` in `plan.json`), so a lesson never ends short for this alone. A drill
  streak is also broken by a substitution or a sentence for a short item before it ends the
  lesson.
- **A situation is narrated in full twice a lesson.** After two narrations of the same authored
  situation (`SITUATION_FULL_MAX`) the cue is the meaning, short (or the partner's line, G12);
  «Quick review: two separate situations.» is said once. A pairing that narrates both
  situations (connect, the contrast after a note) takes `situation_cue_ok`.
- **Notes.** Milestones fire deterministically once their `items` are met or exposed, and
  are followed by discrimination practice over examples whose situation is usable now. A
  note waits for what it recommends saying (`requires`). As filler, an aside is about met
  material or material within `note_lookahead` items; an unheard note about distant
  material is never spent early, and a heard one rests `note_repeat_gap` lessons (#81).
  All notes share one lesson total (`max_notes_total`, one per 10 minutes, at least 2):
  milestones are never blocked by it, but asides and streak relief stop once it is used.
  A note heard in a learner file older than `notes_last_heard` dates to the latest lesson.
- **Content guards.** `progressive_inf` holds only verbs audited for «vera að» + infinitive
  («sofa» is excluded). Dialogue partner lines use only taught words. No fill-borne
  parenthetical leaks into a sentence prompt (`meaning_forms.in_sentence`).

## Decisions (and why)

- **Python 3.11+, zero required deps.** TOML via `tomllib`, audio via `wave`; ffmpeg only
  for mp3 and for decoding non-WAV TTS output.
- **Three-stage pipeline with a serialized script in the middle** (`script.json`), so
  voices, pauses and providers can change without re-planning.
- **Presumed success.** Audio can't hear the learner, so every retrieval counts as a
  success. `report --failed` corrects it afterwards.
- **A ladder per item kind** (`stages.py`). Stages an item can't support are skipped, not
  faked.
- **Slot fills are verbatim `target`s; no morphology engine.** Tag discipline keeps
  generated sentences grammatical: case-tagged pools (`acc_orderable`, `nom_place`),
  `agreement` for gender, `meaning_forms` for gloss variants.
- **Sequencing problems are fixed in the curriculum, not with gates bolted on** (#25 →
  #29). The dialogue sequencing report stays advisory.
- **Instructor phrasing is data** (`audiolesson/phrasing/<lang>.toml`), so another
  instructor language is one file plus glosses.
