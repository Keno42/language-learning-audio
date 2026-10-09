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
| a single item's review question, fresh from the course (#73, #220) | `audiolesson questions --ids …` (`prompt`, `answer`, and `cues`: every current way to ask the bare item) (`cli._review_cue`, shared with `_plan`) |
| romanized Japanese outside «ja:…» is rejected (#219): notes, every glossed English field of items, examples, dialogues and turns, themes; not the reading deck («gufuba») | `content.unmarked_japanese` (`ROMAJI_DENIED`, `ROMAJI_ALLOWED`), called from `validate` and `themes._check` |
| reading deck for the Discord review (#133) | `curricula/is-en/reading/deck.toml`, `audiolesson/reading.py`, `audiolesson reading` |
| loading those record files (`cando/`, `reading/`) | `audiolesson/records.py` |
| what the instructor says for a meaning (`meaning_spoken`, #143) | `Item.spoken_meaning` in `audiolesson/content.py` |
| planner levers, off by default (#136) | `PlanConfig.late_unhinted_recall`; see `docs/LEVERS.md` |
| BÍN check of the variants (#218 b2) | `audiolesson/binform.py`, `tools/bin_lookup.py` (reads BÍN's downloaded form list, no network), `curricula/is-en/bin/` (cache + licence); `validate` only warns (advises, never blocks) when the cache or a form is missing or a `variant_of` item and its base are not one BÍN lemma |
| diagnostics | `audiolesson validate` (gloss coverage, dialogue sequencing report, part-before-whole report `--parts`), `tools/phrase_families.py`, `tools/replay_lesson.py` (a feedback export's lesson rebuilt and continued: the daily-read table, LEARNING-DESIGN §1) |

## Invariants the tests pin

Each of these was a real regression once; `docs/history/sessions.md` has the details.

- **Durable learning (#27).** `LearnerState.knows()` means two recalls on or after a due
  date. Recalls minutes apart in one lesson don't count. Dialogue eligibility is
  `knows(i) or i in builder.in_lesson` for every required item, never `has_met`. One deliberate
  exception (#179): the listening route plays an ordinary dialogue (pauses, no listening) whose lines
  the learner can say though only met (`Planner.can_say_turn`, strict: today's practice doesn't count
  there); the regular route keeps the rule.
- **Open failures (#149, 1a).** An item whose latest confirmed outcome is 言えなかった is
  open (`LearnerState.is_open`) until a later confirmed recall; presumed success neither adds
  a durable success nor lengthens its interval (it is due again tomorrow). Each lesson practises
  up to `max_open_items` of them, five times at fractions of the lesson time (`open_item_times`, by time not exercise count); the ones that failed last lesson go first, then the longest without an open practice (`ItemState.open_practiced`), and lists them in
  `plan.json` (`open_items`, `open_not_fitted`, written by `cli._plan`; #199 found they never were) so the bot can ask them. An open item
  practised without a written question (only a cloze, a hint or a dialogue) gets one from its situation or meaning, `stage: "open"`; so does one that did
  not fit the lesson (`open_not_fitted`, #220), because the bot asks every open item. The cue is the lesson's own (`exercises.meaning_prompt`, with the item's
  `context`); constructions have no single answer and are skipped. An open
  item is *met*: a theme or listening turn that lacks only an open item is asked, not heard (`Planner._untaught_turns`, `classify_turns`).
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
  **A line is "missing" when the learner can't say it (#179), not when `knows()` says so**
  (`Planner.can_say_item`/`can_say_turn`): said if its item is met and not open, practised this
  lesson, or the filled line is covered, in order, by chunks they can say (a sayable item's target, a sayable construction's fixed text). A heard
  turn has no task cue. A dialogue with no missing line is ordinary (asked, with its pauses, not
  counted in `dialogues_listened`); `listening_asked` in `plan.json` lists the turns asked
  because the line can be said although `knows()` is false.
  **A framing line is followed by a beat (#241).** A line that introduces an example or a scene (`embed_*`, `instance_sentence`,
  `variant_*`, `construction_slot`, `also`, `form_model_*`, `milestone_intro` / `aside`, a turn's `scene` / `partner_scene`,
  `listening_line`, `dialogue_replay`) is said by `Builder._frame` (a narration with role `frame`, then a beat). A cue for the
  learner's own action («Repeat.», «Slowly.», the reply cue, cloze and hint cues) joins its line at once; Icelandic inside a note's
  prose stays inline. A turn's opener after the first has a beat before it (the previous turn's partner meaning has just ended). The daily read counts any instructor narration followed straight by speech, whatever its role, except the action cues and a note's prose (0). `bare_cap_lapsed_short_s` in the
  meta says how short the lesson would have ended when the bare cap lapsed.
  **A listening scene asks only for taught lines (#240).** A turn the learner can't say in full is heard
  («Here you would say:», the line, its meaning), whether or not they can say a chunk of it
  (`Planner.can_say_part`; `classify_turns` keeps the two kinds apart for the daily read). The scene opens with
  `listening_intro` ("just hear how it goes") only when nothing is asked; when some lines are asked it opens with
  `listening_intro_some_asked`. `listening_untaught` in the script's meta lists any line a listening scene asked
  that the learner was never taught (the daily read's Now row 2; 0 by construction).
  **Tried lines (#183) are gone (#240):** no scene asks for a line that wasn't taught, a theme's play included (the
  owner: an untaught line can't be said at all). What follows describes the bonus path, which has nothing feeding
  it now; it stays so `plan.json` and the bot keep their shape. Nothing is recorded for a tried
  line's unknown items (the parts they have are credited as practised); they go into
  `LearnerState.tried` (item → lesson, like `embedded`, never met, `select_new` ignores it). Up to
  `max_bonus_questions` (2) tried lines go into `plan.json` `review` as `"bonus": true` questions
  (`Planner._bonus_review`; the trip ordering's lines first, then the latest; `prompt` is the turn's
  cue, `answer` the line). A bonus question reported 言えた makes its tried items met with one
  durable success and the usual first interval (`knows()` still needs a second recall); a miss is
  not reported by the bot, and if it were, `report` ignores it for a tried item. `listening_tried` and
  `listening_asked` are in `plan.json`.
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
  **Last-resort extras are spread (#187).** A cheap construction beyond the limit or a variant (`try_variant`) used to come
  after the whole idle stretch (substitution drills, replayed reviews), so a lesson heard ten minutes with nothing new and
  a new item two minutes before the end. `Planner.build` now builds a lesson that took such an extra a second time with
  those ids known (`PlanConfig.planned_extras`, internal; at most two rebuilds): the idle ladder takes a planned extra once
  `idle_intro_slack` (2) spacings have passed since the last introduction, before the substitution drills. Only an extra the
  first build took is moved (within the limits and the time the first build had, so the later ones follow a spacing
  apart rather than another `idle_intro_slack`), so the lesson's items are the same and only their timing changes; a lesson that never runs
  idle takes no extra and is built once. The planned extras stay out of `new_queue`: a non-empty queue blocks `start_arc`
  and the extra item of a lesson with nothing to review, and shortened a lesson from 20 to 13.7 minutes.
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
  target. It is claimed once per construction and form in a lesson (`Builder.novelty_announced`, #197): what is new is the
  pattern or its form, not each filler, so a substitution run announces its first step only.
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
  A short item introduced today that has been said inside a sentence in this lesson is asked in a
  sentence from then on, the closing recall included (#179: `ask_a_sentence`, `Builder.sentence_recall`
  with its `context` sentence first), not as a bare part; a short item with no sentence yet keeps the
  bare recall.
  **Parts and utterances (#187, #190).** The cap is keyed to `Item.kind`, not to length: a *part* (`vocab`: every slot
  filler in the course, whatever its length: «peysu», «fara á safnið») is said alone only at its introduction and its
  early recall (`max_bare_uses`, any bare practice counts, a mixed-review turn included) and otherwise in a sentence
  (`is_part`, `counts_alone`). An *utterance* (a `phrase` of at most `short_item_words` words: «Hvenær?», «Vá!», «Takk.») is
  a complete thing to say: a scene calling for it is its proper use, so only its meaning-cued bare practices
  (`cloze`, `hinted`, `meaning`) count against the cap, not situation turns or mixed review. The cap holds on every
  path: `_connect_pair` skips a capped part; and a part or short utterance *due for review* (not introduced today, not
  open: `short_review`) is asked as a sentence that holds it when one can be said (`ask_a_sentence(review=True)`: a
  pattern with a slot, its `context` sentence, a known or earlier-practised phrase that contains it), else it keeps
  the bare recall; mixed review also skips such an item when `holds_sentence`. A stable whole is never the
  sentence for another item (it is practised on its own dates); neither is the whole just asked or one asked twice
  already: the part was just said inside it, so its review counts as done through that exercise (the item is credited)
  and nothing more is played; nor is a whole that negates the part
  («Ég skil ekki.» for «Ég skil.»: `NEGATION`), and a whole asked as a sentence is credited with the item.
  **Identical sentences (#192).** `Builder.said` counts each sentence said in the lesson (model answers with the repeat after
  the model, an introduction once, a dialogue's partner lines); `Builder.produced` counts how often a line was asked, and the
  repeat after the model (`echo_asked`, 1) comes only for the first asking of a line. `PlanConfig.max_sentence_utterances` (6) is a
  preference: past it `do_recall` practises the item in another sentence that holds it (`sentence_practice`) when one exists,
  holders are tried under-count first, and `_connect_pair` takes a pair whose items are neither the one just practised nor past
  the count, falling back to any pair. `replay_lesson.py` reports "most times one sentence is said".
  Once every combination of a construction's fills was used, `generate` takes the one whose sentence was said fewest times (`Builder.said`).
  A generated sentence is not the one the learner just said or the one before (`Builder.recent_answers`), and `sentence_recall`
  marks its combination used, so a part's closing and its pattern's closing do not say the same sentence back to back.
- **Constructions have authored negative and question forms (#171).** `Item.negative` /
  `question` (with meanings) are alternatives of a construction's target template, never derived;
  `validate` checks slots, «ekki», «?» and the meanings. `Builder.generate(forms=True)` may pick
  one for a recombination, sentence practice or substitution run, but only once the note that
  teaches it (`Note.teaches`) has been heard (`Builder.forms_taught`: the learner's `notes_heard`
  plus `notes_taught` of this lesson). `Planner.forms_note_due` plays the teaching note once the
  learner knows two constructions with the form (negative first, one a lesson) and
  `do_forms_practice` follows it by *modelling* the form on two known constructions (below); the note is neither
  a milestone nor an aside (it draws on neither ration). A form is a different sentence
  (`_combo_key` carries it) with its own meaning as the cue; the exercise is credited to the
  construction. `forms_taught` in `plan.json`.
  **A form is modelled before it is asked (#211).** `Builder.generate` offers a form of construction c only when `knows(c)` and `c:form` is in
  `learner.forms_modelled` (or modelled earlier in this lesson, `Builder.forms_modelled`): the note alone unlocks nothing. `Builder.model_form`
  (kind `model`, stage `form`, after `_intro_variant`) plays «You know this one:» the plain sentence, «As a question:» the same in the form,
  repeated, then the form with another filler, asked without being spoken first (the form is first produced there). `do_forms_practice` models the first un-modelled known constructions right after
  the note; `form_model_due_now` models one more at 35% / 65% of a later lesson (at most `PlanConfig.forms_models` = 2 a lesson), the trip
  profile's priority items first. `apply_to_learner` saves `meta["forms_modelled"]`; a file from before #211 (`forms_modelled` None) is
  seeded in `Builder.__post_init__` from `heard_utterances` (a form sentence already said or heard counts as modelled, also for a construction not known yet: the owner accepted that on the review of #232, since it only affects a learner already past lessons 15–16, whose «ætla» forms skip their model step; a new learner starts with nothing heard). `plan.json` has
  `forms_modelled_now`. Because of the gate, «Now something you haven't heard yet» (#197) only ever means a new filler in a form already heard.
  The mix is held (`Builder._form_order`): the plain sentence is at least half of a lesson's
  generated sentences and a form takes at most about a quarter (`FORM_SHARE`; hard stop at
  `FORM_HARD_CAP` of the lesson's sentences, once it has `FORM_CAP_FROM`), the form furthest below its
  share first; a form taught in this lesson takes `FORM_EXTRA_NEW` sentences beyond its practice
  right after the note; among a form's combinations, one whose plain sentence was heard comes
  first (variety, not replacement). When plain sentences run out the supply may run short rather
  than the newest form crowd them out. Japanese glosses of a form that depend on the fill's word
  class use a per-fill `meaning_forms_ja` (`neg`, `tai`, `tai_neg`).
- **A core construction gets a light review every lesson (#171).** `Item.refresh` sentences of a known,
  not open construction are scheduled across the lesson (`refresh_timeline`, constructions interleaved),
  each a recombination with fillers not heard this lesson (`_recombine`, `met_fills`, forms once taught);
  one whose time has come plays when the drill streak allows, an idle lesson and a streak with no relief
  pull them early (`play_refresh`), and a construction with no unheard sentence left is dropped for the
  lesson. `refresh_sentences` in `plan.json`. A construction that is open or unknown gets none: its own
  practice is the heavy one.
- **A `refresh` construction is a trip item for #174's reorder (#180).** In `select_new(cheap=True)` the
  candidates are the trip constructions and the constructions with `refresh`; the cheap one with the most
  sentences goes to the front of the trip order, one a lesson, taking one new-item place (the trip items behind
  it shift by one). Its prerequisites must still be known (`ready`), except one that is only a filler of the
  construction's own slot (#180 (b), `Planner._prereq_met`): it counts once the slot has `cheap_min_fillers`
  other known fillers, in `cheap_construction` and in `select_new`'s `ready()`.
- **The lesson's theme exchange (#149 1b-ii).** A theme (`audiolesson/themes.py`, `cando/themes.toml`) is a
  scene of a trip as an exchange, at rising levels (partner and learner turns; a learner turn lists the items it
  needs). `Planner.pick_theme` takes, among the themes whose next level the learner can say in all but a quarter of
  their turns (`theme_ready`: every item of a turn met and not open), the lowest level not yet played, the trip
  profile's boosted scenarios first (`theme_scenarios`, `scenario_order`), then Tier A, then Tier B, in file order. The level
  becomes a `Dialogue` (`level_dialogue`; the learner's lines are literal) played **twice**: at about 15% of the
  lesson's time with the partner's lines translated, and at about 85% without the translation (the cue, the intent,
  and a turn's `scene` line play both times, #210; `play_theme`, step 0g; a lesson that ran out of other material plays what is left before the closing). A
  turn with an item the learner has never met is heard, not asked (#240: `heard_turns`; its cue, then «Here you would
  say:», the line and its meaning; nothing recorded), in both plays. A learner turn keeps its cue in every play, whatever the partner just said: no turn of an exchange that goes on drops it (owner, #230 review: the partner's line never decides the reply; a one-off reply with several example answers is a separate change). `Turn.scene` (partner turns only) lands in `DialogueTurn.scene` / `partner_scene`, narrator lines played every time; a level's `partner_speaker`
  (`native_a`, female, where the cues say «her») voices the partner. The items of the turns they can say are credited
  as practised (stage `dialogue`). `plan.json` has `theme`: `{id, scenario, level, plays, lines, replay, heard}` (None only when no theme
  can be said at all; `replay`: a level already played, #149 step 1; `lines`: per play, the 1-based variant of each varying partner line,
  as in the exercise label `[lines 2,1]`); `LearnerState.themes_done` (theme → highest level played) makes the next lesson take the next level; when none is
  ready, `pick_theme` replays the last level done of the highest-ranked theme rested `theme_rest_lessons` (3) lessons
  (`LearnerState.themes_last`: theme → lesson that last played it), else the longest rested; a replay is not assisted, and its early play says only partner wordings already heard with their meaning
  (`LearnerState.themes_heard`: `theme:level` → `turn:line`, recorded from `theme.heard` of the assisted first play;
  none heard: the line as written). The fallback can replay a theme heard two lessons ago when none has rested enough.
  New material is chosen for the theme (#149 step 2): `Planner.theme_target()` is the theme and level `pick_theme` would
  rank first whether or not the learner can say it yet, `theme_wants()` the items its turns lack, each behind its unmet
  prerequisites, and `select_new` puts them first in its pool, ahead of the trip order (a promoted cheap construction keeps
  its place). The pace is unchanged: it decides how many, the theme which. `plan.json` has `theme_target`: `{id, level, wanted}`
  (the items the level lacked at the start).
  A semantic set is not introduced as a block (#149 step 2, H5): `select_new` skips an item when the lesson already has
  `PlanConfig.max_set_items` (3) new items of one set in `PlanConfig.semantic_sets` (number, colour, animal, acc_language,
  weather, nature_nom, day, job, and the adjectives: `adj_neut|adj_masc|adj_fem` counted as one set, `semantic_set_tags`), counting the lesson's earlier arcs (`exclude`) and what the call chose. The skipped item waits for
  another lesson and the pool goes on, so the pace is unchanged; a filler pulled in for a construction's slot is not counted. The items the target theme's next level wants (`theme_wants`) are a scene, not a bare set: they are neither stopped by the limit nor counted towards it.
  **Never ten identical (#192, owner).** `PlanConfig.max_sentence_hard` (9): a fixed phrase (`kind == "phrase"`) whose sentence has been
  said that often (`Builder.said`) is asked no more: `do_recall` plays nothing for it when no other sentence holds it, a mixed-review pair
  leaves it out, a sentence that holds another item is not taken from it, and `Builder.sentence_recall` (`said_cap`) offers no sentence at
  the cap. A new item keeps one place for its closing recall, so everything before the closing stops at the cap minus one, and a linked phrase (below) whose pattern is available stops at `max_sentence_utterances` (6) + 1 (7, then its closing recall); a short item
  whose every holder sentence is at the cap gets no bare part in its place at the closing. Like the bare cap it holds only while
  the caps do (`bare_cap_lapsed`: nothing else is left).
  A fixed phrase linked to a pattern (`Item.instance_of`, `instance_fill`, #192): in `sentence_practice`, past
  `max_sentence_utterances` and once the pattern is available (`Builder._frame_available`), the phrase is practised through
  `Builder._recombine(pattern, met_fills=True, exclude=<its own fills>)` (another sentence of the pattern), else `Builder.sibling_recall`
  (a plain meaning recall of the sentence of another filler said fewest times, a heard line may repeat). `_record` credits the
  pattern and its fillers (`ex.item_ids`), never the phrase.
  When the pattern and every filler pass `knows()` and the phrase is neither met nor in `embed_failed`, `do_intro` (`Planner.pattern_instance_of`)
  does not introduce the phrase: `Builder.pattern_instance` plays one sentence of the pattern (the `embed_sentence` / `embed_meaning` segments, so
  `review_questions` asks the phrase in its own form), `_record` credits the pattern and the fillers, and the phrase goes into `learner.embedded`
  and stays in `new_items`; `plan.json` `pattern_instances` lists them. The bot's next-day check decides: said back, it is met with one durable
  success; not said, it is in `embed_failed` and gets a normal introduction.
  A part comes with its frame (#149 step 2): when `select_new` takes a part (`kind == "vocab"`; an utterance such as
  «Hvenær?» is not one), one construction that lists it as a prerequisite (`Planner.frames_of`, «{thing} virkar ekki.» for
  «sturtan»; the ready one needing the fewest new fillers, then course order) goes in right after it, behind the fillers its
  slots still need. The group (part, fillers, frame) is budgeted against the count with at most one item over; a group that
  doesn't fit leaves the part for a lesson with room, as a part alone is how it was drilled bare. A part whose frame is already
  met or not ready, or that no construction lists, is unchanged.
  One admission rule for a part, whichever path introduces it (#206 review): `Planner.part_has_home` is the only question
  («will this part be said in a sentence in this lesson?»): a construction that lists it is met, in the lesson or just chosen
  (`introduced`), or a phrase that holds its words (`candidate_wholes`: the shortest phrase containing it, never one with a negation
  the part lacks) is in the lesson; or it has neither (a content gap, #215). A plain part also counts a phrase it knows (the embed
  path says the phrase), but a variant form (`variant_of`) does not: «þrjá» beside a «Þrjá miða, takk.» met long ago and not
  scheduled was drilled bare. Every path asks it: `select_new` (theme target, trip order, cheap). When it is false,
  `select_new` brings the ready frame, else the ready unmet phrase that holds it (`frame_group`), within the one-over budget, and
  neither is the place given up for a cheap construction (`pulled`); a variant with no frame that can come waits
  (`part_waits_for_home`). Waiting every part for a blocked frame starved the course (a part and its frame each waiting for the
  other: the gendered-noun milestone moved by 20 lessons), and moved the price chain four lessons later, which broke #80's
  «said in a sentence within two lessons»: a plain part whose frame is blocked is introduced as before and is listed in the replay
  table's «short items» row.
  The two caps (hard cap, bare cap) conflict whenever both bind: a recall the hard cap keeps out frees time that bare words would fill
  past their own cap. `over_hard_cap` records that it held (`hard_cap_held`), and a lesson whose remaining time is under
  `PlanConfig.hard_cap_short_max` (180 s) then ends there instead of lapsing the bare cap (the lapse stays for a lesson that is short
  for another reason).
  A partner turn may carry `variants` (#134): `pick_variants` picks one line per turn for the early,
  translated play (heard with its meaning); the late play says the lines as written, which are also the ones the review
  cards ask. Every partner line is spoken at natural speed (rate 1.0), and each variant must fit the learner's reply
  that follows. A replay's early play takes only wordings already heard with their meaning (#196); a heard-only play (spare time, #218 b1) takes any variant, untranslated, as listening exposure (H8), on purpose. Without `themes` in `PlanConfig` (the CLI loads them from the curriculum's `cando/themes.toml`) nothing changes.
- **Rotation and a ceiling (#180).** `Builder.generate_with` orders a word's homes by the sentences each
  construction has had this lesson (`construction_counts`), least first, random tie-break; substitution runs
  pick the pattern with the fewest likewise. A construction takes at most `CONSTRUCTION_CEILING` (10) generated
  sentences in a lesson, a word's and its own recombinations alike (`construction_full`); its introduction and
  timed recalls aren't generated sentences. A form is not chosen if it would leave the forms together above
  `FORM_ALL_HARD_CAP` (0.5) or one form above `FORM_HARD_CAP`: the cap is tested on the share after the sentence.
  Open practices never run on past three in the review queue (`open_run()`).
- **Cheap constructions come early (#171 B).** A construction is cheap when it is unmet, its prerequisites
  are known and every slot has `cheap_min_fillers` known fillers (`Planner.cheap_construction`, the
  one adding the most sentences first). `select_new(cheap=True)`, for the lesson's own new items, puts
  one in place of the last **non-trip** item (`cheap_place`): a trip item is never displaced. With a trip
  ordering the cheap *trip* construction (the best one) moves to the front of the remaining trip order
  instead: every item is still a trip item, only the order changes (H6). A lesson whose new items are all
  trip items and has no cheap trip construction takes none this way. A lesson with time left takes up to
  `max_cheap_extra` more beyond the new-item limit, (`try_extra`);
  `cheap_constructions` in `plan.json`. The worked example of a construction's introduction uses a known
  filler of the slot when the authored one isn't known.
- **No close variant as filler (#218 b1).** `try_extra` (streak relief, an idle planned extra #187, before the cap lapses) takes only a
  planned extra or the cheap construction. `select_new` keeps a `variant_of` item out of the pool unless the theme's next level wants it
  (#201) or an unmet item lists it as a prerequisite (#202; a frame's filler is found in `fill_pool`); the trip and course orders do not
  take variants. Spare time goes to listening dialogues, then to up to `heard_theme_plays` (2) heard-only plays of a theme level already
  played (`Builder.dialogue(heard_only=True)`, label `heard: theme:…`: partner lines in variants, the cues kept, «Here you would say:» and
  the line, nothing asked; `heard_themes` in `plan.json`), then the consolidation, then the cap lapses. `variant_items` in `plan.json`
  lists the variants the lesson did introduce, which a theme or frame asked for.
- **A variant is introduced as a form of one they have, and a word says its sentence.** A
  `variant_of` item whose base was met is introduced «You know this one: tveir. Here is another
  form of it: …», said and repeated, a sentence it goes in when a pattern takes it, then the usual
  first retrieval (`_intro_variant`). An item with a `context` is recalled at the meaning stage
  as «Say: good, as in: This is good.» (`meaning_in_context`); the introduction is unchanged.
- **A situation is narrated in full twice a lesson.** After two narrations of the same authored
  situation (`SITUATION_FULL_MAX`) the cue is the meaning, short (or the partner's line, G12);
  «Quick review: two separate situations.» is said once. A connect() turn whose situation has no room
  is cued by the item's meaning instead of dropping out of the pairing (`Builder._cue`); for a
  construction that is the meaning of the sentence it asks for, filled with the answer's fills
  (`_connect_turn`, #178), never its template. **No narrated or spoken segment of a built lesson contains
  a slot placeholder** (`NoSlotLeakTests`, a 20-lesson course).
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
- **`report --hesitated` is a next-day outcome; `report --sooner` is a learner's request about the schedule (#222).** `--hesitated` counts
  (`hesitated`, ease −0.1, a history outcome), consumes an embedded item as failed and marks the lesson reported, so it belongs to the review
  that decides them. `--sooner` (the feedback form's «not enough / don't remember», filled right after listening) only moves `due` to at most
  half the interval from today: nothing is counted, `ease`, `interval_days` and the history are untouched, an embedded or tried item is
  `sooner_skipped` (its next-day review decides it), and the lesson is not marked reported, so the pace still waits for evidence (H2).
- **The pace reads three lessons and a load rating (#218, part a).** `recall_rate()` sums weak/new items over the last three
  `lessons[]` entries in `reported` (each item's entry is found by lesson number, never `history[-1]`; an embedded item in `embed_failed`
  is weak). `suggest_pace`: up at ≤ 15% with a small backlog, hold to 25%, down above. `report --load light|right|heavy` stores
  `lessons[k]["load"]`; like `--sooner` alone it does not mark the lesson reported. Two «light» lessons raise it at ≤ 25% with the same small-backlog condition (< 0.5) as the recall-based rise; an unrated lesson is skipped (it neither breaks nor extends the run); a «heavy» in the
  window blocks a rise; one step a lesson. `report --load` for a lesson not in `lessons[]` warns on stderr.
- **Spare time serves the scene and the ear (#238, Now 1).** `ItemState.last_reviewed` (set by `report` for failed / hesitated / recalled, not by `--sooner`)
  is the day the learner's own review asked an item; `Planner.reviewed_today` keeps it out of `select_reviews`, `select_early_reviews`, the
  connect pool, substitutions and `refresh`. `Planner.scene_constructions(theme_pick)` = the constructions the learner's turns of the lesson's
  theme level use (and the pattern of a linked phrase): `pick_substitution` and the `refresh` timeline take only those (a parallel of a target
  expression of the scene), unless the lesson has no theme. In the step-5 chain the order of spare time is: the scene's parallels, a fresh arc,
  the not-due early tiers and the second pass (kept, as before), the lesson's own theme level heard again (`heard_theme_plays` = 4 in all, own
  level first), listening dialogues, today's new lines again, and last a substitution outside the scene before the bare cap lapses. A closing
  recall skips a new item just asked as the holder of another new item's sentence.
  A run of generated sentences is cut at `generated_run_max` (3) while something to hear is left (a theme level to hear again, a listening
  dialogue): a construction's review waits and the ear comes between. The not-due early tiers list the scene's own items
  and patterns first (`select_early_reviews(prefer=…)`).
  `meta`: `longest_generated_run`, `target_reached_at` (end of the last introduction that costs a component), `spare_unserved_s` (seconds after it that serve neither
  a target expression nor the scene: generated sentences outside the scene, recalls of items taken as filler; due reviews are not counted),
  `asked_after_review` (items the learner's review asked today that the lesson asks again; open items' repair excepted); two rows in `replay_lesson.py`.
- **The second half is a rotation (#248, concept 2 and 3, O2, O5, G16).** Once the lesson has taught what the target asked for
  (`mark_delivered_target`, after every introduction, an embed and a pattern instance included: `target_reached_at` in the meta is that time)
  and nothing is left in `new_queue`, `audiolesson/listening_tasks.py::SecondHalfRotation` takes the filler time round *hear the scene (a theme
  level at natural speed) → pick out information × 2 → catch an unknown word → use one of today's expressions*; a kind that cannot be added passes
  to the next. It sits ahead of the not-due reviews, the second pass, a substitution outside the scene and `try_extra` (step 4b), and the
  substitution run (0c) and refresh sentences (0f) wait while it is on; scheduled work (open items, the theme, today's timed recalls, due
  reviews) is unchanged, but after three exercises of one kind the rotation comes in between. A short pick-out or unknown-word exercise also follows
  every third recall of the closing block when time allows (`closing_cost` keeps the seconds; on the lesson-20 replay it did not fire, the closing's
  room being too small).
  - *Pick out information* (step 2, #248: the learner has to **find** it; the answer stays Icelandic): a line of a scene's partner with `Turn.probes`
    (`{kind, answer, meanings, ask}`; `answer` a stretch of the line, `kind` price / time / count / place / duration) or a `listen` line of the turn (never played in the
    exchange: wording for the ear, two pieces of information, each probe with its own `ask`: «How much is the sandwich?»). `partner_pick_out`; the learner must be
    able to say the answer (every word of it known), the rest of the line may hold unknown words. Two-piece lines come first, then a single piece in undrilled
    wording; the lesson's own scene before the others (named aloud). `plan.json` `second_half.pick_out_echo_count` and the replay's row 6 count a pick-out
    whose line is only a drilled frame plus its answer (0: the planner takes none). `generated_pick_out` (a sentence of a construction with
    `Item.information_probes`) stays for sentences that hold more than the frame (#213), and is not used by the planner.
    *(Step 1, kept for the question wording:)* built from words the learner knows
    (`known_at_start` plus the words of what was taught today), heard from the scene's partner voice; the instructor asks the question of
    `pick_out_<kind>` (plain: «How much is it?»; with a scene named, `pick_out_<kind>_scene`: «How much does he say it costs?»), the learner
    pauses, the answer fragment, its meaning and the sentence again follow. At most `max_pick_outs_per_pattern` (3) a lesson from one construction,
    and one unknown word caught once, whichever line it came from (#248 review: the same two frames and «Þarftu» five times). The scene's constructions come first, then a
    played scene's (named aloud), then the rest. The question is never guessed from a slot's name.
  - *Catch an unknown word* (`catch_unknown`): a partner line (or variant) of the lesson's scene or a played one whose words hold exactly one
    the learner does not know (counted by occurrence), with an authored meaning in `Turn.word_glosses` (also a variant's); only once
    `hvad_thydir_thetta` can be said. The learner says the word and asks what it means; the model answers in the other voice.
  - Both are exercise kinds of their own (`pick_out`, `catch_unknown`), not in `PRACTICE_KINDS`, and nothing is `_record`ed: what was only heard
    is not practised, and the next day's review does not ask it. No new item is introduced for them.
  - `meta` / `plan.json` `second_half`: `pick_out_count`, `catch_unknown_count`, `longest_kind_run_after_target` (counted from the target to the closing block, which has its own run of recalls);
    three rows in `replay_lesson.py`.
- **Named exceptions to the tags (#192, owner after lesson 20).** `Item.exclude_fills` (a construction): `Curriculum.items_with_tag(tag, construction)` leaves those fills out, so `generate`, `generate_with`, a substituted worked example and `example_fill` never take them; authored fills are untouched. It is the way to declare the tenth case in ten the tags don't explain, instead of retagging (LEARNING-DESIGN §9 "Good enough overall"). The general rule beside it (#251 review): `Builder._product` drops any combination in which two fills of a sentence share a word (exact casefolded tokens of their targets, short function words excepted), so «Ég ætla að fá mjólk með mjólk.» is never built; inflected repeats are not caught.
- **`--order new-first` (#243, a user option outside the design).** `PlanConfig.order` (`spread` by default, today's planner). `new-first` sets `intro_spacing` to 0 and the gap between introductions to 1, drops the later arcs (step 2b) and, while `new_queue` still has items, skips the steps that play known material: the streak breaker's dialogue / connect / listening, substitution (0c), open items (0d), the theme (0g, its early play comes right after the block), refresh (0f), reactivations of items not introduced today (1), dialogue (3) and review (4). Inside the block stay an arc's connected use (0b) and today's timed recalls (0e). `plan.json` `config.order`.
- **The pace's unit is weighted new components (#218 b3).** `PlanConfig.new_target` (from `learner.new_target`, a rate per `NEW_TARGET_MINUTES` = 30 minutes, via `suggest_target`, whose rules run at 30 minutes; a lesson of m minutes plans `max(1, rate × m/30)` and `generate` saves the rate, #242;, which
  runs the same rules as `suggest_pace`, `LearnerState._pace_rules`; None counts items) is the lesson's target. `Planner.component_cost`:
  `variant_of` item `form_weight` (0.5); construction 1, or 0 when every fixed word is known and a known pattern holds them all; vocab
  1 if any word is new; phrase 1 per new word; a #192 pattern instance 0. A word is known when it is in an item the learner has met, has
  heard embedded (also failed), or was charged earlier in the lesson. One running total (`components_total`) over every path:
  `select_new` charges what it returns and stops once the total reaches the target (the last item may go over), as do the extra arcs
  and the cheap extra; the extras a first build took are charged at the start of the rebuild (#187). The last pick may carry the total over the target by one item at most (`OVERSHOOT` = 1: a part whose frame or phrase would pass it by more waits for a lesson with room). `new_items_ceiling` is a cap on *load*: only items that cost something count against it (a 0-cost item adds lesson time, which the time check bounds; owner's decision on the review of #235), and it is tunable (`PlanConfig.item_ceiling`; raise it if lessons stay «light» with the target reached). A run of new words the curriculum treats as one vocab item («taka mynd») counts once in a phrase. The backlog rule for the target reserves review slots for the *item* pace, not for components. `meta["new_components"]` = {total, forms, target, by_item} (also in `plan.json`); `status` shows the target.
- **An item is taught once in a lesson (#217).** Every `select_new` call in the lesson loop excludes `taught()` (introduced ∪ embedded this
  lesson), so an arc start does not spend a pick on an item already taught, which would be a lost slot. The first selection
  (`new_queue = deque(self.select_new(...))`) runs before anything is taught and has nothing to exclude. `do_intro`, where every path to an
  introduction ends (the planned queue, the extra arcs, variants, cheap constructions), keeps a guard as the backstop: it skips an item
  already introduced or embedded this lesson, records it in `meta["intro_skipped"]`, and counts the skipped turn down its arc's target as
  an embed does. The course property asserts `intro_skipped` stays empty, so it pins the source; the mocked test pins the guard.
  `meta["new_items"]` is built without duplicates. Before, an item embedded in a sentence and queued again was introduced as new nine
  minutes later and listed twice (lesson 19's «miða»), which also broke the bot's feedback form (a select with a repeated value).
- **A transient edge-tts error is retried per clip (#77).** `EdgeProvider._retrying`: any `EdgeTTSException` (looked up by name in the MRO,
  so edge-tts is not imported: `NoAudioReceived`, `WebSocketError`, `UnexpectedResponse`, …), aiohttp's `ClientError`, a timeout or a
  connection error is retried after 5, 20 and 60 s (one stderr line per retry, so the bot's status shows it). A malformed argument (a
  `ValueError` or `TypeError`, e.g. a malformed voice name) fails at once; an unknown but well-formed voice comes back as `NoAudioReceived`, so it
  is retried and then fails with that message. An error that keeps coming fails with its own message. Only the failing clip is redone.
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
