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
| the items `plan.json` describes (`id`, `target`, `meaning`, `kind`): `new_items`, `reviewed_items` (picked for review), `exercise_items` (every item an exercise names, once, in the order first named: the bot's form offers the learned items the lesson asked, site_update_notifier#151) | `audiolesson/cli.py` (`_plan`); `tests/test_plan_items.py` |
| travel can-do scenarios and their coverage report (#131) | `curricula/is-en/cando/travel.toml`, `audiolesson/cando.py`, `validate --cando`; see `docs/TRAVEL-CANDO.md` |
| trip ordering from a private profile (#132) | `audiolesson/trip.py`, `cando.priority_items`, `PlanConfig.priority`, `generate --trip` |
| scenario cards for the Discord review (#129) | `curricula/is-en/cando/scenes.toml`, `audiolesson/scenes.py`, `audiolesson scenes` |
| a single item's review question, fresh from the course (#73, #220) | `audiolesson questions --ids …` (`prompt`, `answer`, and `cues`: every current way to ask the bare item) (`cli._review_cue`, shared with `_plan`); an item with a `target_m` is asked «As a woman: …», its answer being `target`, and so are all its `cues`, so the bot rewords a stored question that lost the form |
| romanized Japanese outside «ja:…» is rejected (#219): notes, every glossed English field of items, examples, dialogues and turns, themes; not the reading deck («gufuba») | `content.unmarked_japanese` (`ROMAJI_DENIED`, `ROMAJI_ALLOWED`), called from `validate` and `themes._check` |
| reading deck for the Discord review (#133) | `curricula/is-en/reading/deck.toml`, `audiolesson/reading.py`, `audiolesson reading` |
| loading those record files (`cando/`, `reading/`) | `audiolesson/records.py` |
| what the instructor says for a meaning (`meaning_spoken`, #143) | `Item.spoken_meaning` in `audiolesson/content.py` |
| planner levers, off by default (#136) | `PlanConfig.late_unhinted_recall`; see `docs/LEVERS.md` |
| BÍN check of the variants (#218 b2) | `audiolesson/binform.py`, `tools/bin_lookup.py` (reads BÍN's downloaded form list, no network), `curricula/is-en/bin/` (cache + licence); `validate` only warns (advises, never blocks) when the cache or a form is missing or a `variant_of` item and its base are not one BÍN lemma |
| words and normalised lines | `audiolesson/text.py` | `WORD` (a run of letters, digits and underscores excluded), `words()` and `norm_utterance()` are defined once; the planner, builder, review, themes and `tools/replay_lesson.py` import them (#281). `timing.py` keeps `\w+` where digits count |
| diagnostics | `audiolesson validate` (gloss coverage, dialogue sequencing report, part-before-whole report `--parts`), `tools/phrase_families.py`, `tools/replay_lesson.py` (a feedback export's lesson rebuilt and continued: the daily-read table, LEARNING-DESIGN §1) |

## Invariants the tests pin

_Write each invariant as its own bullet, or its own line of a bullet, one topic per line; never append to an existing long line. Two PRs that touch different topics then do not conflict (#281)._

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
  never met. «Reply.» frames each cue unless the exercise before was one. An example answer follows the line, the reply's own meaning
  worded as one possible answer («For example: All good, thanks.», `reply_example`, role `example`): after a line heard often enough
  to go unglossed, nothing said what to answer (lesson 29). The partner's line itself is never put in English once known. The review
  question for it is the line itself (or its meaning), never the example (`Script.review_questions` skips the role). No authored
  situation starts by restating what the learner said.
- **An authored dialogue does not repeat the lesson's scene.** `Planner.repeats_scene`: two or more of a dialogue's learner lines are
  each a different line of the level the lesson plays (a dialogue turn says a level turn when the item it expects is one that turn
  asks, or its literal line is that turn's, `Planner.scene_turns`; each dialogue turn is paired with a level turn of its own, so one
  level turn such as «Nei, takk.» counts once however many dialogue turns it matches, review of #384). `eligible_dialogue` and `listening_dialogue` skip such a dialogue in that lesson: the scene's
  exchange already says those lines (lesson 34 of the lesson-33 replay played «kynning», Anna from Akureyri, two minutes before
  small talk 1, whose Anna is from Akureyri too). One shared line («Takk.») is not a repeat. `tests/test_scene_group.py`.
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
  learner's own action («Repeat.», «Slowly.», the reply cue, cloze and hint cues) is followed by its line after the
  switch gap only, not a beat (#301); Icelandic inside a note's
  prose stays inline. A turn's opener after the first has a beat before it (the previous turn's partner meaning has just ended). The daily read counts any instructor narration followed straight by speech, whatever its role, except the action cues and a note's prose (0). `bare_cap_lapsed_short_s` in the
  meta says how short the lesson would have ended when the bare cap lapsed.
  **A note's prose is read a sentence at a time (#259).** `Builder._speak_note_text` splits each stretch of prose at «. » «? » «! » «: » followed by a capital letter (and at «。» «！» «？» in
  Japanese), says each sentence as its own narration with a beat after it, and leaves a sentence that goes on into a «…» span inline («The / kennitala / is a ten-digit number.» is one
  sentence). The last sentence of the text has no beat of its own: `note` adds the one closing beat. «e.g.» and «vedur.is» don't split. A milestone or teaching note takes the same rule.
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
  repeat.», the sentence, its meaning, the sentence again, a pause to repeat (`embed`). The other sentence is never the phrase
  itself (lesson 34: «Á þetta hótel, takk.» is «{dest}, takk.» with the part, and was said again as «another sentence»); with no
  other, `embed` returns None and the part is taken out of the phrase (#262, below). Nothing is
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
  bare recall. The closing asks today's new items outside the lesson's scene first, hardest first, then the played level's items in the order of its
  turns, so the lesson ends on its exchange (`Planner.closing_order`, #327; with no theme, hardest first as before). A linked phrase taught as a
  sentence of its pattern (`embedded`) keeps no closing recall (#192); the exchange's late play asks it. It asks each sentence once: a new item that an earlier recall of the closing made the learner
  say (its holder, the pattern or the filler in that recall's `item_ids`, or its words inside that recall's sentence, not negated there:
  «Ég skil ekki.» is not a recall of «Ég skil.») is credited to that recall and not asked again (lesson 27: «Í miðbæinn, takk.» and «Ljósið virkar ekki.» twice in a minute).
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
- **A core construction gets a light review when the lesson's scene uses it (#171, #238).** `Item.refresh` sentences of a
  known, not open construction of the scene (`scene_constructions`; any, when the lesson has no theme), not asked in the
  morning's review, are scheduled across the lesson (`refresh_timeline`, constructions interleaved),
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
  needs; a gendered learner line has its man's form, `Turn.say_m`, which `level_dialogue` passes on as `expect_text_m`, so the line is
  said in the form of the learner's voice, opposite the partner's, and `Builder.dialogue` names it in the cue; `check_gendered_lines`
  requires it exactly on lines with a `target_m` item, `tests/test_theme_levels.py`). `Planner.pick_theme` takes, among the themes whose next level the learner can say in all but a quarter of
  their turns (`theme_ready`: every item of a turn met and not open, or queued to be introduced in this lesson, `coming`, #327:
  the level plays in the lesson that teaches its lines, heard early and asked late), a level whose lines this lesson teaches first (`waiting`:
  another ready level, all of it known, would leave today's lines without their scene), then the lowest level not yet played, the trip
  profile's boosted scenarios first (`theme_scenarios`, `scenario_order`), then Tier A, then Tier B, in file order. Its `goal`
  (`goal_ja`) is said right after the opening (`Builder.theme_goal`, «Today's goal: …»; `plan.json` `theme.goal`, #327). The level
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
  New material is chosen for the theme (#149 step 2): `Planner.theme_target()` is the lowest next level, then the scenario
  rank, whether or not the learner can say it yet (`pick_theme`'s order without its first key, a level whose lines are coming: the target decides which lines come), `theme_wants()` the items its turns lack, each behind its unmet
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
  `max_sentence_utterances` and once the pattern is available (`Builder._frame_available`) and the learner's review did not ask it today
  (`reviewed_today`, #238; the hard phrase's `pattern` connection goes through here too), the phrase is practised through
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
  played again (`Builder.dialogue(heard_play=True)`, label `heard: theme:…`: partner lines in variants; #263: the learner's lines they can say are **asked** with the cue,
  the pause and the model, and only a line with an untaught item is heard with «Here you would say:»; the opening follows: `listening_intro_known` when all are asked;
  `heard_themes` in `plan.json`).
  **A partner who slows down (#261):** `Item.slows_partner` (phrases only; set on `gaetirdu_talad_haegar`) makes the partner's next line word by word (an authored dialogue's turn through its item, a theme level's literal line through its `items`: the town's third level asks it, scenario A7's repair): `Builder._speak_spaced` says one `speak` segment per word at natural speed (role `spaced`) with a `Timing.word_gap` (0.3 s, role `word_gap`, floor = itself) between them, in `dialogue` (the reply or opener after that turn, and the replay) and in `connect`'s bridge. `Script.transcript` shows the line once (`(word by word)`, words joined by ·). If one-word synthesis sounds like a list, chunk by phrase instead (a one-function change in `_speak_spaced`).
  **Recombine wording keeps its promise (#287):** «Use it in a sentence.» (`recombine_vocab_again`) and «Use the pattern again.» (`recombine_again`) are said only when the exercise just before practised the same item or pattern (`Builder._recombine`, `linked`); otherwise a vocab recombine says «In a sentence.» (`recombine_vocab`) and a pattern one «Put it together yourself.» (`recombine`). `meta.unkept_links` lists any that promise a link that is not there (0 expected; `replay_lesson.py` row).
  **Apply it right away (#287 step 2):** the first timed recall of a vocab part introduced today (`first_rung`, `play_timed`) keeps its place and spacing, and the next exercise is a recombine of the same part when a known pattern takes it (`recombine_status == "novel"`), once per part, so the exercise before it practised the part and the cue's promise is true; `meta.apply_in_sentence_parts` lists them.
  **Hard-to-say words (#212, H13):** `audiolesson/sounds.py` flags a one-word vocab target of two or more syllables that holds a sound rule (`ll`, `tt`, `fj`, `ý`; `ll` and `ý` are cards of the reading deck, a test keeps them in step); `Item.syllables` (authored, checked to join to the target) gives the split. `Builder._slow_model` (generic intro, `_intro_in_whole`, `_intro_out_of`) adds «Slowly, in parts. Repeat each part.» (`split_slowly`) with each syllable at the pronunciation rate and repeated, then the word at natural speed; without syllables the whole word slowly. `meta.hard_words` lists today's flagged new words; `validate` lists flagged words with no `syllables` (none now). The rule in one sentence (the «ll» note) is not generated: notes carry it.
  **A phrase's hard words, and an item reported hard (#337):** `Item.word_syllables` (phrases; word → authored pieces, checked to join the word and keep a cluster whole) names a phrase's hard words; `Builder.phrase_word_models` says them after the phrase's own introduction (word by word, then each word's pieces slowly with a repeat pause, then natural). No letter rule decides at the introduction, so the flagged count is bounded by what is authored (`plan.json` `phrase_hard_words`). A reported item that names no hard word of its own is heard whole when it is a sentence (`Builder.hearing_sentence`: a phrase or word of two or more words, or a pattern's worked example in words the learner has, `worked_example_fills`, resolved for the model's voice so a gendered pattern says the woman's form in the woman's voice and no gender turn is taken; never its slot names): the sentence, word by word, and at natural speed again, each repeated (lesson 27: «Við erum fjögur.» and «Ég nenni ekki að …» were hard to *hear*, and the sound rule had picked «fjögur»). `sounds.REPORTED_SOUNDS` («ei», «ng» before a vowel, «ð», «g» between vowels; not introduction rules: «ð» alone is in a quarter of the vocabulary) pick the word only for a single word with nothing authored (`hard_words_of(reported=True)`). A report (the feedback form's «sooner», `report --hard`) sets `ItemState.slow_owed`, apart from `reported_hard`: a confirmed recall settles the connections of #326 but not how the word sounds, so only playing the model clears it (`apply_to_learner`, from `plan.json` `slow_models_reported`). A file saved before the field gets it from `reported_hard` on load, once (only when the item's saved dict has no `slow_owed` key), so the reports made before it still owe their model. A single word with authored `syllables` that `hard_sounds` does not flag («reikninginn») gets the model only when reported: the introduction rule stays the small one of #212, on purpose. Step 0h of the planner loop plays `Builder.slow_word_exercise` (kind `model`, stage `slow`: the phrase, then each authored hard word in pieces; else the sentence heard whole as above) for up to `slow_models_per_lesson` owed items, from `slow_model_from` of the lesson on, whether or not the item is practised in that lesson; a report older than `REPORTED_HARD_DAYS` is dropped. `tests/test_hard_word_again.py`.
  **Admission: a known noun's unmet frame comes forward (#270):** `Planner.stranded_frame` finds a met noun entry (`Item.noun`, not open) with a frame (`frames_of`) none of which is met and no known phrase that holds it; `select_new` puts that frame in its pool behind the theme's items and the trip order's items, so it takes only a new-item place that is left over (#293 review: first, it pushed the day's own line out), once per selection (`pulled`, so a cheap construction does not take its place); when the learner has met two fillers for each of its slots (`met_fills`) it brings no new noun with it, and `meta.stranded_frames` lists those placed. It is the "known noun, only frame unmet" case that left «sturtan» (`virkar_ekki`) and the tour nouns asked bare on the replays.
  **Ease learns from a long-gap confirmation (#220):** `LearnerState.report(gaps={item: days})` / `report --gaps a=14,b=7` takes the days since each item was last confirmed or practised when the answer was asked (the bot knows it). A `recalled` at `LONG_GAP_DAYS` (7) or more raises the ease by 0.1 (ceiling 3.0) and lifts the interval to at least gap × ease (the due date follows if later); failures and hesitations are handled as before, and an item with no gap too. Every outcome with a gap is counted in `LearnerState.retention` by the longest bucket it reached (3, 7, 14 days; `[recalled, tested]`, saved in the learner file); `retention_report` reads it and `replay_lesson.py` has the row.
  **A 言えた at a real gap extends the interval (#220, the owner's rule):** with a `gaps` entry of `REAL_GAP_DAYS` (1) or more but under 7, on an item that is due or on an interval under 3 days, `report` moves the interval to 3 days (from under 3) or to max(interval, gap) × ease, and the due date follows; `ItemState.gap_streak` counts such confirmations (and long-gap ones) in a row, a failure or hesitation resets it, and from the second the ease rises by 0.1. An early check of an item that is not due and on a longer interval changes nothing; no `gaps` entry, as before. The audio still fills spare time with early reviews of not-due items, so the time a check frees is reassigned there, not removed. `tests/test_retention.py` (`RealGapTests`).
  **Conversation timing (#272):** a partner line is always followed by a beat before the next narration (`_beat_after_partner`); a reply the learner has said before (every item met, none open, or any line asked in a scene heard again) is paused as a single exercise is (`_reply_pause`: no generative bonus, the items' successes and difficulty set the familiarity, the recall floor stays), a literal line (`expect_text`, no item) is known when every word belongs to a met, not open item (`_met_items_holding`); a first-time or open line keeps the longer pause; every heard play has one intro (no `dialogue_start`; `listening_intro_known` when every line is asked); the last beat of a scene gives way to the exercise gap, and no two beats follow each other. The catch task lower-cases a sentence-initial heard word (`word_as_asked`) and its pointer cue is one sentence («Ask what {pointer} means.»).
  **Scene units through the lesson (#273):** step 0b'' of the planner loop plays a scene unit (the second half's rotation without «today»: a scene heard again, a pick-out, a catch task) whenever `scene_unit_interval` (240 s) has passed since the last conversation, pick-out or catch task, at any point of the lesson after the first introduction. Before the target is delivered a unit takes only scenes already played (the lesson's own once its exchange has played, or when it is a replay).
  `plan.json` `second_half` carries `longest_without_scene_s` and `asked_again_within_spacing` (a sentence asked again under 60 s after it was asked, keyed by the answer the learner is asked to say: reported, and softly avoided since the spacing half of #273 — timed recalls and due reactivations prefer what was not asked in the last minute, a timed recall whose sentence was just asked waits a minute (twice at most), a part whose sentence was just asked is credited to that asking, and a situation is not narrated again while another variant has room), and `meta.target_delivered`; `replay_lesson.py` has the rows.
  **Noun entries (#270, pilot):** `Item.noun` / `form` / `noun_base` / `gender` group the forms of a noun (`Curriculum.nouns`, `noun_form(id)`); ids are unchanged, so per-form learner state and the bot's queue need no migration. `audiolesson/nouns.py` reads which forms each noun has met (`noun_forms`, `noun_report`); the daily read has rows for it and for nouns asked bare in the lesson's own recall (`meta.bare_noun_recalls`). A form that differs from its basic word is contrasted with it once at its introduction (`_form_contrast`).
  **The lesson's recall of a part goes through a sentence (#270, widened to every `vocab` item with #277):** for a `BARE_STAGES` recall of a vocab item `do_recall` asks the sentence from its meaning (`Builder.recall_whole`; the sentence is the one taught today, else `learner.learned_wholes`, else `review_wholes.whole_for`, the rule the written review uses); with no such sentence it is asked as before; the same holds for a `recombine` recall that finds no sentence to make and for the closing recall (`ask_part`), and a part whose sentence has been said as often as a lesson allows is not asked at all in its place (`part_sentence_capped`).
  **A trivial question is never asked (#277):** `cue_is_answer(item)` (the spoken meaning is the target: a name, «krónur») means the lesson asks the part through its sentence or not at all (`meta.trivial_questions`, 0 expected), and `refine_review` drops it as `trivial` when no whole exists.
  **Tour frame:** «Mig langar að sjá {thing}.» (`mig_langar_ad_sja`, slot tag `acc_sight`) takes the sights in the accusative: «eldfjall», «hraun», «foss» and «strönd» are unchanged, «jökul» (`jokull_acc`) and «norðurljósin» (`nordurljosin_acc`) are form items of their nouns (`variant_of`, so they come with the frame, not as general material); the tour theme's third level asks it. A frame taken by `select_new` brings the two sights it needs as fillers, which the set limit does not count.
  **One role rule (#263):** `Planner.line_role(items, turn)` → `ask`/`hear` decides every learner line in every play mode (`classify_turns`, `_untaught_turns`, `play_theme`, the scene heard again), judging *can say* through one policy, `Planner.can_say_line(items, text)`, for a dialogue turn and a theme turn alike: every item can be said (met and not open, or taught earlier in this lesson, `taught_today`: by its own introduction or inside a sentence, `embedded`, review of #365), or a construction is among them and its filled line is covered by chunks they can say; a phrase is a unit, never covered by its pieces. A dialogue exercise names the items it asked (`item_ids`) apart from those of lines only heard (`heard_ids`); a theme level's turns map to items through `turn_items`, then the consolidation, then the cap lapses. `variant_items` in `plan.json`
  lists the variants the lesson did introduce, which a theme or frame asked for.
- **A variant is introduced as a form of one they have, and a word says its sentence.** A
  `variant_of` item whose base was met, a near form that is no noun, is introduced «You know this one: tveir. Here is another
  form of it: …» (a form of a noun goes into its frame, #270), said and repeated, a sentence it goes in when a pattern takes it, then the usual
  first retrieval (`_intro_variant`). An item with a `context` is recalled at the meaning stage
  as «Say: good, as in: This is good.» (`meaning_in_context`); the introduction is unchanged.
- **A situation is narrated in full twice a lesson, and not right after itself when the cue has another way.** One rule
  for an authored situation and a scene check's line (`Builder.situation_rank`, counted by `_narrated`): no room after
  `SITUATION_FULL_MAX` (2) narrations this lesson, and then the cue is the meaning, short (or the partner's line, G12);
  one of the last `SITUATION_RECENT` (3) narrated (#273) is a preference to avoid. `_next_situation` takes a free variant
  before a recent one, in rotation; `situation_room` is whether any has room; a scene line is used only when free
  (`scene_line`: the sentence's meaning is its other way). Avoiding a recent authored situation always (tried in the review
  of #361) left a new item's recalls right after its introduction with no room, so they dropped out;
  «Quick review: two separate situations.» is said once. A connect() turn whose situation has no room
  is cued by the item's meaning instead of dropping out of the pairing (`Builder._cue`); for a
  construction that is the meaning of the sentence it asks for, filled with the answer's fills
  (`_connect_turn`, #178), never its template. **No narrated or spoken segment of a built lesson contains
  a slot placeholder** (`NoSlotLeakTests`, a 20-lesson course).
- **Notes.** Milestones fire deterministically once their `items` are met or exposed, and
  are followed by discrimination practice: two examples, by their situation when it is usable now, the second sharing no
  word with the first when one can («með sykri», then «án mjólkur»; lesson 33), a part asked in its sentence (`ask_part`,
  #270), never an item the learner's review asked this morning (#238). A
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
- **Spare time serves the scene and the ear (#238).** `ItemState.last_reviewed` (set by `report` for failed / hesitated / recalled, not by `--sooner`)
  is the day the learner's own review asked an item; `Planner.reviewed_today` keeps it out of `select_reviews`, `select_early_reviews`, the
  connect pool, substitutions (unless the pattern is taught in this lesson, `taught_today`; a part's sentence going through it does not unlock it, #270) and `refresh`. `Planner.scene_constructions(theme_pick)` = the constructions the learner's turns of the lesson's
  theme level use (and the pattern of a linked phrase): `pick_substitution` and the `refresh` timeline take only those (a parallel of a target
  expression of the scene), unless the lesson has no theme. In the step-5 chain the order of spare time is: the scene's parallels, a fresh arc,
  the not-due early tiers and the second pass (kept, as before), listening dialogues and the lesson's own theme level heard again (`heard_theme_plays` = 4 in all, own
  level first; the second half's rotation and a capped run of generated sentences reach both too), today's new lines again, and last a substitution outside the scene before the bare cap lapses. A closing
  recall skips a new item just asked as the holder of another new item's sentence.
  A run of generated sentences is cut at `generated_run_max` (3) while something to hear is left (a theme level to hear again, a listening
  dialogue): a construction's review waits and the ear comes between. The not-due early tiers list the scene's own items
  and patterns first (`select_early_reviews(prefer=…)`).
  `meta`: `longest_generated_run`, `target_reached_at` (end of the last introduction that costs a component), `spare_unserved_s` (seconds after it that serve neither
  a target expression nor the scene: generated sentences outside the scene, recalls of items taken as filler; due reviews are not counted),
  `asked_after_review` (items the learner's review asked today that the lesson asks again; open items' repair excepted); two rows in `replay_lesson.py`.
- **A part lives inside its whole (#239, concept 1; §9 "Parts against utterances").**
  - *In the lesson.* `Builder.whole_home(part)`: a vocab item that a construction's slot takes («hjálpina» in
    «Takk fyrir {thing}.»; #262: any such construction, the one whose authored fills name the part first, no authored example needed), with the other slots filled from what the learner has (the authored fills when available), at most one word of the frame
    they have never met, and a sentence not yet heard whole (`is_new_utterance`). `intro` then calls `_intro_in_whole`: «A new expression. Thanks for the help.»,
    the sentence said and repeated (slowly when the pattern is difficulty ≥ 2), «This word is in it:» the part, and a first retrieval of the whole from its meaning.
    The exercise stays an `intro` of the part (`item_ids = [part]`), so `Script.review_questions` asks the sentence next day. A part without such a home is introduced as before.
  - *A pattern whose example is known.* `_intro_construction` checks the worked example with `is_new_utterance`; when it is not new («Eigðu góðan dag.», or the
    sentence the part came in with) it says «You know this:», the sentence and `construction_of_known` («It is a pattern: you can say it with other words.») instead of «Here is a useful pattern».
    That line is said only when a second example with another known filler follows it; with none, the same sentence is asked next, so it says
    `construction_of_known_later` («It is a pattern: other words can go in its place. You will meet them later.»; lesson 34: «hnetum» was said
    to be swappable and no swap came for minutes, `tests/test_instance_filler.py`).
  - *In the review* (`audiolesson/review_wholes.py`, applied in `cli._plan` to `plan.json` `review`; the bot is unchanged). `refine_review(review, cur, met, prompts)`:
    (1) a part's question whose part sits in another question's answer is dropped and credited to that question (`beside_whole`); (2) a bare part with a whole
    the learner knows (a construction filled with the part and met fills, the one whose authored fill names it first, else the shortest phrase that holds it) is
    asked through it: the whole's meaning is the cue and the sentence the answer (`through_whole`, with `through` naming the item); a part with no home in the curriculum
    (#215's definition: no slot takes its tags, no construction lists it as a prerequisite, no phrase holds its words) comes out of the review (`no_home`); a part whose homes
    are all unmet stays bare, the fallback; (3) no two questions share an answer: the later one's items are credited to the first (`same_answer`). Bonus questions are left alone.
    `audiolesson refine-review CURRICULUM [-l LEARNER]` is the same rules for the bot's review queue (site_update_notifier#96): `{"review": [...]}` on stdin (optional `"met"`),
    `{"review": [...], "refined": [...]}` on stdout; what the learner has met comes from the learner file.
    *Homes (#215, data side).* `review_wholes.has_home(cur, part)` is the definition: a construction slot takes the part's tags, a construction lists it as a prerequisite, or a phrase
    holds its words (a long one-word part also in a longer form of itself, «norðurljós» in «norðurljósin»; `whole_for` uses the same match, so a part that counts as housed can be asked
    through that phrase). `validate` prints an advisory listing the vocab items with none (the sample curricula have a few; the course has none, and the tests pin it).
    The colours' home is `litur_noun` («Þetta er {colour} {noun}.», the colour taking the form of its noun: «Þetta er blár bíll.», «blá bók», «blátt hús»);
    `sjor` and `midnaetursol` are `nom_noun` (they fit «Þetta er {thing}.»); `hundrad`, `halfur`, `adeins`, `folk`, `af_thvi_ad` and `an` each have a short phrase;
    `tuttugu_og_einn` was removed (no scene needs it, and its age form is the genitive).
    `meta.met_items` is what the learner has met plus what this lesson taught; `meta.wholes_taught` maps each part to the sentence it was taught whole in (`through`, `answer`, `meaning`; the review asks it exactly as taught when its pattern is not met yet) (#262: per part, so a pattern taught around «peysu» does not make «vegabréf» askable through it). A new phrase that holds a part is introduced before it (`Planner.phrase_first`). A phrase taught earlier in the lesson that holds a part is the part's whole too: `Builder.phrase_home` / `_intro_in_phrase` («You know this: … This word is in it: …», then the phrase retrieved); `phrase_first` also accepts a phrase whose prerequisite is another new item of the lesson (`queued`: «Hundrað krónur, takk.» for «krónur»). The daily read lists parts still asked bare that have a home (`bare_parts_with_a_home`).
    **Pattern first (#262):** a queued single-slot pattern whose slot takes a new part is introduced before the part (`Planner.frame_first`), with the part as its worked example (`intro(…, worked_fills=)`); the sentence heard is recorded in `Builder.modeled_wholes`, and the part is then taken out of it (`_intro_out_of`, the same steps as `_intro_in_phrase`) and recorded in `wholes_taught`, so the next day's question asks the sentence.
    **Kept across lessons (#262):** `apply_to_learner` stores each taught part's `{through, answer, meaning}` in `LearnerState.learned_wholes` (saved in the learner file; an older file reads as empty), `plan.json` `meta.learned_wholes` snapshots it, and the review (`_plan`, and `refine-review -l` for the bot) asks that sentence for a part whose pattern is still unmet; today's `wholes_taught` takes precedence over a stored line. Knowing the line does not make its pattern met.
    **A near-copy gets a light introduction (#280):** a phrase that is the pattern's own `negative` / `question` form (`Item.instance_form`, with `instance_of` / `instance_fill`; `validate` checks that the pattern in that form with those fills makes the phrase exactly) costs `form_weight` (`component_cost`) and, when the pattern and fills are known *or taught earlier in the lesson* (`pattern_instance_of`), comes in as one `embed` exercise framed as the form («You know this one. As a question:», `instance_form_question`), no ladder (`Builder.pattern_instance(form=)`). Linked: «Er þetta hættulegt?», «Er þetta rétt?», «Ég tala ekki íslensku.».
    **Parts of one line together (#280):** when the part-from-a-known-line fallback fires, the lesson's other queued vocab parts of the same line that no known pattern can embed are taken out in the same exercise (`Builder.joint_parts`, `_intro_out_of`: «And this one:» `embed_part_also`); each is introduced and `wholes_taught` with the one line, and the next-day question is that line once.
    **A known line with no pattern (#262):** when a part's `embed_source` is a line the learner knows but no known pattern makes a new sentence of the part (`embed` returns None: «krónur» in «þúsund krónur»), the line becomes its `modeled_wholes` entry (`Builder.whole_of`) and the part is taken out of it the same way; `whole_for` asks the taught line when its search finds no pattern or phrase that holds the part. `plan.json` `review_refined` lists every change; `replay_lesson.py` row 5 counts a part beside its whole and a repeated answer (0).
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
    able to say the answer (every word of it known), the rest of the line may hold unknown words. Two-piece lines come first; a single piece is asked only when the words outside it outnumber it
    («Hér stoppum við í tuttugu mínútur.», not «Það gera tvö þúsund krónur.»: that is lesson 21's echo); one pick-out per partner turn a lesson (its variants and listening
    lines count as one, and a two-piece line gives one question: the other piece waits for another lesson); the lesson's own scene before the others (named aloud).
    The exercise's `stage` is `multi` or `single`. `plan.json` `second_half.pick_out_echo_count` and the replay's row 6 count a pick-out
    whose line is only a drilled frame plus its answer, or a single piece that is most of its line (`Planner._is_echo`, read from the script; 0: the planner takes none). `generated_pick_out` (a sentence of a construction with
    `Item.information_probes`) stays for sentences that hold more than the frame (#213), and is not used by the planner.
    *(Step 1, kept for the question wording:)* built from words the learner knows
    (`known_at_start` plus the words of what was taught today), heard from the scene's partner voice; the instructor asks the question of
    `pick_out_<kind>` (plain: «How much is it?»; with a scene named, `pick_out_<kind>_scene`: «How much does he say it costs?»), the learner
    pauses, the answer fragment, its meaning and the sentence again follow. At most `max_pick_outs_per_pattern` (3) a lesson from one construction,
    and one unknown word caught once, whichever line it came from (#248 review: the same two frames and «Þarftu» five times). The scene's constructions come first, then a
    played scene's (named aloud), then the rest. The question is never guessed from a slot's name.
  - *Catch an unknown word* (`catch_unknown`): a partner line (or variant) of the lesson's scene or a played one whose words hold exactly one
    the learner does not know (counted by occurrence), with an authored meaning in `Turn.word_glosses` (also a variant's); only once
    `hvad_thydir_thetta` can be said. The learner says the word and asks what it means; the model answers in the other voice. **The partner answers (#279):** the narrator reports it, not answers it: «He/She tells you:» (`catch_unknown_told`, from the line's speaker), the word in the partner's voice, «means: …» (`catch_unknown_means`), then «Now listen again.» (`catch_unknown_again`) before the line replays. A `paraphrase` in a gloss (the partner rewording it) is the later, data step and is not built.
  - Both are exercise kinds of their own (`pick_out`, `catch_unknown`), not in `PRACTICE_KINDS`, and nothing is `_record`ed: what was only heard
    is not practised, and the next day's review does not ask it. No new item is introduced for them.
  - `meta` / `plan.json` `second_half`: `pick_out_count`, `catch_unknown_count`, `longest_kind_run_after_target` (counted from the target to the closing block, which has its own run of recalls);
    three rows in `replay_lesson.py`.
- **The scene check (owner, 2026-10-16; LEARNING-DESIGN §9 "Good enough overall").** `[scenes.<pattern>]` tables (`curricula/is-en/95-scenes.toml`, merged by `load_curriculum`; `content._apply_scenes`) give each fill of a pattern a verdict: a line goes to `Item.fill_scenes` (the primary language, or a table per language read by the learner's language, never by its order, `content._scene_text`; a learner whose language has no line gets the meaning alone; a `""` left from the sheet is no verdict), `false` to `Item.exclude_fills`; the key `"*"` (`content.PATTERN_SCENE`) is the pattern's own line, `Item.pattern_scene`, for every fill without a verdict of its own (never `false`; review of #361: a fill-independent line had been copied to each fill, and a two-slot pattern left fills unjudged on purpose so as not to cancel the other slot's line); `Item.scene_verdicts` keeps which fills were judged (`"*"` for the pattern line; `content.scene_covered`: a fill judged by the pattern line alone, a fill tagged later included, without a review: LEARNING-DESIGN §9), and `validate` fails for a fill that is not one of the pattern's, or for `fill_scenes` authored on an item. `Curriculum.items_with_tag(tag, construction)` leaves the excluded fills out, so `generate`, `generate_with`, a substituted worked example and `example_fill` never take them; authored fills are untouched. A line is the cue when the sentence is asked, by whichever path asks it, while it is free under the rule of every situation (`situation_rank`, above; review of #361: a line shared by many sentences was read up to 14 times in a lesson); after that the sentence is asked from its meaning (`Builder.scene_line`; `fill_scene` is the verdict alone: the line of the one fill that has one, else the pattern's line; `_scene_say` formats prompt `scene_say`, the scene then «Say: {meaning}», and counts it; the label becomes `situation`): a construction's recall at `meaning` or `situation` (not when the pattern's own situation names the fill), a plain-form recombination (the line takes the place of its cue's «Say: …» only: a cue's news or link, «Now something you haven't heard yet.» (#197) or «Use the pattern again.» (#287), stays before it as its own line, `recombine_*_lead`; the written review, which takes the last line, asks from the scene), a sibling's sentence (`sibling_recall`), a short item's sentence (`sentence_recall`) and a part asked through its pattern's sentence (`recall_whole`); a several-slot sentence whose fills have two lines takes the pattern's line, or none. `content.scene_sheet` lists the sentences with no verdict (the other slots filled with the example; a fill the pattern line covers counts as judged): `validate`'s advisory counts them; `audiolesson scene-check` prints them as `[scenes.<pattern>]` TOML to fill in (an id with letters outside ASCII, «strætó», quoted) (`--learner`: only the patterns and fills the learner has met; `--pattern`; `--judged`: the verdicts given too, the `"*"` line first and each fill it covers as a comment, so the table pasted back is unchanged). `tests/test_scene_check.py`. **A reflexive fill agrees with the subject** (lesson 31 on the replay of the lesson-30 export: «Viltu hvíla mig?», «Ætlarðu að hvíla mig?»): `Item.reflexive` (a fill, «hvíla mig») never goes into a template that `Item.addressee` names (the person spoken to is the subject: `plain`, `negative`, `question`). `items_with_tag(tag, construction)` leaves it out when the plain template is addressed; `Curriculum.fits_form(construction, fills, form)` is checked by `generate` for every form it picks, and for the form `model_form` will say its plain sentence in (`shown_as`); `validate` checks both fields. `tests/test_reflexive.py`. The general rule beside it (#251 review): `Builder._product` drops any combination in which two fills of a sentence share a word (exact casefolded tokens of their targets, short function words excepted), so «Ég ætla að fá mjólk með mjólk.» is never built; inflected repeats are not caught.
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
- **A refusal of the speech service (HTTP 403 at the handshake) is one shared state (#296).** `EdgeProvider._refused` decides by `exc.status == 403`, not by a name. The first worker to meet it becomes the prober (`_wait_out_refusal`): it says `edge-tts: service refusing (403), waiting N min (k/m)` on stderr, waits 1, 2, 4, 8 … minutes (`refusal_budget_min`, 15 by default, a voice-profile key) and tries its own clip again; the other workers wait on a `threading.Condition`. When a probe gets through, all go on; when the budget is spent every worker fails at once with `SpeechRefused: speech service refused (403) for N min; cached clips kept` (the bot reads `speech service refused` / `service refusing`, site_update_notifier#111). Clips already synthesized stay in the cache, so the retry asks only for the rest. Other transient errors keep the per-clip retries. A fallback provider after the budget (`fallback = "openai"`) is not built: a second voice in one lesson is the owner's call.
- **Azure Speech as a provider and as the fallback (#299).** `AzureProvider` (`provider = "azure"`) posts SSML to the official REST API with plain `urllib`: the voices are edge's (`is-IS-GudrunNeural`…), the key (`AZURE_SPEECH_KEY`, with `AZURE_SPEECH_REGION`; `AZURE_SPEECH_ENDPOINT` overrides the URL) only in a header, never logged or in a URL or an error message. A 429 waits for `Retry-After` and retries (8 times), 5xx and dropped connections retry like edge's transient errors, 401/403 fail with a message that names the settings, not the value. A profile key `fallback = "azure"` makes the renderer hand the remaining clips to it the moment edge meets a 403 (`edge-tts: service refusing (403); using azure`, once, no wait); with a fallback that cannot run (no key) the #296 wait stays. Edge and Azure share one cache (`cache_family`: same voice, same audio): a clip made by either is reused by the other, and the edge cache keys are unchanged.
- **A grammar contrast outranks a cultural aside (#198).** `Note.contrast`: a note about two forms of the same words in its `items`. `Planner._pick_note` offers it only once every item is met or was introduced earlier in the lesson (`contrast_ready`: the second form is in front of the learner, H5), and among the unheard notes of a tier a contrast note comes before the others. `definite_weak_adjective` explains «heitur pottur» / «heiti potturinn»; the cultural `heiti_potturinn` aside plays in a later lesson. `tests/test_contrast_note.py`. `Note.parts` (groups of target-language pieces) are said after the text, once each, slowly (`slow_rate`) with a gap after each piece (`Builder.note`, prompt `note_pieces`), the last of a group the whole form. A sentence of a note's prose with no letter or digit (the «.» that follows a span at the end of a sentence) is a beat, never a narration (`_speak_note_text`; it applied to `kurteisi` and `tolur_kyn` too). `tests/test_contrast_note.py` (`SpokenNoteTests`).
- **A new noun form is named against the form the learner has (#270 step 3).** `Builder.basic_form_of(item)` gives `(word, kind)`: the authored `noun_base` or a met nominative is the basic word (`form_of_base`: «In this sentence the word changes. The basic word is:», «köku» ← «kaka», «bíl» ← «bíll»); another met form of the noun (the article form, the accusative) is only a known form (`form_known_as`: «You know it as:», «hótelinu» ← «hótelið»), never called the basic word. `_form_contrast` says it in every introduction that puts the form in a sentence: inside its frame (`_intro_in_whole`) and taken out of a sentence just heard (`_intro_out_of`); then, once a lesson per frame, the frame's `form_reason` («This form comes after «leita að».», the words that decide, never the translation). A form of a met noun (`variant_of` and `noun`: the dative place forms «bankanum», «hótelinu») has a home like any part (`whole_home`, `phrase_home`, and `frame_first` when the frame is still to come in the lesson's queue and has two new words), so `intro` teaches it in the frame that asks it, the worked example's sentence first when the frame was just introduced with it (`modeled_wholes`); the form it is named against may be one taught earlier in the same lesson (`in_lesson`); before, it went to `_intro_variant` and was said and asked alone («To the bank.», lesson 31 on the lesson-30 replay). `tests/test_form_contrast.py`.
- **Each scene's frames and the case each asks are read, not authored twice (#270 step 1).** `nouns.scene_frames` goes through the learner turns of every theme level that say a noun and gives the construction, its slot, the case of the slot's tag and the noun's form; `nouns.scene_syncretisms` lists the forms that stand for another case (the same word: «eldfjall» after «sjá»). `audiolesson nouns <curriculum> --scenes` prints both. `tests/test_scene_frames.py`.
- **What a 言えた at the review would save (#220).** `plan.json` `review_savings` (`cli.review_savings`) maps each older item to the seconds of this lesson's same-form recalls of it (`meaning`, `situation`, `hinted`, `cloze`; not `recombine`, which is transfer practice and supplies sentences for today's new items). New, embedded and open items are left out: their practice stays. The bot builds the next lesson as a dry run (`generate --dry-run --no-audio`) before the review, ranks the older items it could ask by this, and asks the ones that pay first; a third of the retention seats stay oldest-first for an unbiased sample (the owner's rule on #220). `tests/test_review_savings.py`.
- **When the theme's next level wants nothing, the day's new material is one scene (#327 part 1).** `Planner._group_by_scene` runs in `select_new` after the trip order and the theme's wants: the day's topic is the first item's topic if a theme that can be played again plays it (`themes_done` ≥ 1, rested `theme_match_rest`=2 lessons), else the topic of such a theme with most of the next `scene_window`=150 unmet items, else the first item's own first topic. Only once every theme has played all its levels (`themes_exhausted`) and with no `--topics`. At most `scene_share`=⅔ of a call's places go to items of the topic ahead of the course order (a topic no theme plays, numbers, still comes: the price listening needs it); the trip order's items stay first and a promoted cheap construction keeps its place; the topic is set by the first `select_new` of a lesson (`day_topic`, reset in `_build`). `pick_theme`'s fallback (every level played) prefers a theme whose `topics` hold `day_topic` after that rest (`matched`, ahead of the 3-lesson rest). `plan.json` `new_in_scene` {theme, inside, new, in_turns} and `day_topic`; the daily read prints them, `in_turns` as «today's new items said as a turn of the played exchange»: today's new items, the embedded ones included, that a play of the exchange asked (its `item_ids`; a turn only heard does not count) (a topic shared with the theme is not enough: the museum's ticket desk had `directions` until #327's town theme). The themes for the scenes that supply that material are the town (`town`, scenario A8; three levels, the third for the way itself), small talk (`smalltalk`, scenario B3; four levels, the third and fourth for nationality and work, age and married) and the clothes shop (`clothes`, scenario A3), two levels each; the other scenes' levels are authored as the path reaches them (#327). `tests/test_scene_group.py`.
- **A phrase that is a known pattern with a new word teaches the word (#311).** `content.unlinked_instances` finds a phrase whose target equals a one-slot pattern filled with an existing item of the slot's tag (30 in `is-en`, all now linked with `instance_of` + `instance_fill`); `audiolesson validate` fails (exit 1) for an unlinked one, so new data cannot add more.
  `Planner.new_filler_of`: when the linked phrase's pattern is known and exactly one filler is an unmet vocab item («Ég þarf úlpu.» of «Ég þarf {thing}.», `úlpu` new), `do_intro` introduces the *word* through its usual path (the pattern's sentence, `embed` / `whole_home`, then its ladder in other frames: «Áttu úlpu?», «Þarftu úlpu?», «Ég þarf ekki úlpu.») and covers the phrase once as a sentence of the pattern (`pattern_instance`, credited to the pattern and its fillers, in `meta.pattern_instances` and `embedded`, no ladder of its own). Not when the word is the item being introduced (`introducing`): no frame took it, so `phrase_first` (#262) brought the phrase in for it, and the phrase is introduced and the word taken out of it (handing the turn back looped until the recursion limit; `tests/test_instance_filler.py` `HandoffTests`).
  `plan.json` `repeated_new_sentences` (daily read, {} expected) names a new phrase asked as the same sentence in more than 3 exercises. The identical-sentence count in a thin early course is high for every phrase (the course has little to ask); the row is for lessons with material. `Planner.filler_taught_today` (lesson 26 of the replay, «Get ég fengið reikninginn?»): when the word was taught today inside this very phrase as its whole (#262), the phrase is not introduced again as «Something new» but covered once as a pattern sentence (an `embed` exercise, a next-day question).
  A word reported hard is practised through its other connections: #326, below. `tests/test_instance_filler.py`.
- **A word reported hard goes through its connections (#326).** `Planner.hard_items()` = the open items, those whose last confirmed outcome was `hesitated`, and those reported hard (below). In `build`, `do_recall` hands such an item to `connected_practice` (not for an item introduced today, not for `allow_cap=False`): its 1st practice of the lesson and those after the 4th (`hard_connection_turns`=3) are the ladder's own; the 2nd to 4th go through one connection each, in turn: `scene` (`scene_line_of`: a short exchange around the learner's line of a theme level that needs the item, scene first, partner lines translated, heard only when the turn's other items are not known (#240), named by the level it is from (`theme:<theme>:<level>`), the name the connection is logged under, so the daily read counts the scene once; a turn is not used twice for an item in a lesson; else an authored dialogue that holds it), `pattern` (`Builder._recombine(avoid=)`, `generate_with(avoid=)`: a pattern it was not in; a phrase uses `sentence_practice`) and, for a vocab part, `sibling` (`Builder.sibling_recall` of a pattern from `homes_of` with other words of the slot). A fourth kind, `form` (`Planner.related_items`: another form of the same noun, `noun`, and the phrases built on the item by `prereqs`, e.g. «Ég vil sjá lunda.» for «lundi»), practises the item's word in a sentence of its own, and the `scene` kind also takes an authored dialogue that holds a related item. `ItemState.reported_hard` (the day) is set by `report --hard ids` and by `--sooner`; both bring the item back sooner and record no outcome; `hard_items()` includes it for `REPORTED_HARD_DAYS` (14) days or until a confirmed recall clears it. Nothing connects it: the ladder goes on and the dose is not cut. `plan.json` `hard_connections` {item: practices, connections, kinds, same_sentence_max, connection_times_s} (`connection_times_s`: the start of each connection's first exercise, on the finished script's clock, switch gaps (#301) included, the clock of `Exercise.start`); the daily read prints practised / fewest connections, the most identical sentences, and the items asked 3+ times with no connection (content gaps, for authoring when they recur). `tests/test_hard_connections.py`.
- **A scene's fixed phrases that vary in use (#336).** `content.phrase_frames` finds, by text and not by slot tags, the fixed phrases of one scene (a shared topic) that share a frame of two or more words (and 40% of the shorter phrase) at the start and the end and differ in the stretch between; a frame made only of subjects, copulas and prepositions is ignored, and a group whose phrases are all instances of one pattern is not reported. `audiolesson validate` lists them as an advisory (73 today, many of them frames a pattern already covers or not frames a scene varies: only those need a pattern, §9 «Good enough overall»). The transport scene's two frames are patterns with whole-unit destinations (`fer_thessi_straeto_dest`, `dest_takk`; fillers `i_midbaeinn`, `a_flugvollinn`, `a_thetta_hotel`, `a_safnid`, `a_stoppistodina`, tag `dest`; the bus pattern excludes the bus stop and this hotel, a named exception, §9) and their four phrases are linked (`instance_of`). The patterns are in the B4 trip list, the fillers are not: `Planner.covered_units` — when a linked phrase whose pattern is not available is introduced, a filler that is part of the phrase and not yet met is met inside it (`embedded`, `wholes_taught` = the phrase), never introduced again out of it (the double introduction made the same sentence come 10 to 22 times). Once two of them are known, `cheap_construction` brings the pattern forward and the lesson says the bus and taxi lines with the other destinations. A covered unit is also usable as a filler for the rest of the lesson (`in_lesson`), so the pattern is not asked as its example alone, and no sentence of a pattern is asked more than `construction_asks_per_filling`=4 times a lesson, whatever path asks it (`Planner.sentence_asks`, also given to the `Builder` as `ask_count`: with every combination used, `generate` takes the filling asked fewest times in the lesson, not the one `said` counts fewest, which misses the pattern's own recalls; it counts the label of every recall, connection and generated sentence, so the ladder on the example, a linked phrase's own ladder and the generated sentences add up). Every path that can ask a pattern's sentence honours it: a construction's recall takes a filling asked fewer times when `generate`, drawing on learned fillers only, would repeat one, and a situation that names a filling whose sentence is at the cap asks another filling from its meaning (`_recall_construction`); `sibling_recall` (another word's practice through its pattern, `Builder.ask_cap`) and a part asked through its pattern's sentence (`ask_part`, `whole_spent`) do not take a sentence at the cap; a linked phrase is capped by its sentence's asks once its pattern is taught, today included: when every sentence the learner can be asked of the pattern (`Builder.filling_sentences`) is spent, the pattern is not asked again, and a linked phrase stops at the same count (two destinations: about eight bus questions). `plan.json` `units_covered`. `tests/test_phrase_frames.py`.
- **A word is caught once; some new words are introduced through the catch; pick-outs rotate across lessons (#339).** `LearnerState.caught_words` (lower case, saved) holds every word the learner has asked about; a file made before the log is seeded once (`caught_seeded`, `Planner.caught_seed`: the glossed words of the played levels' partner lines that held that word as their only unknown one under what the learner knows now; a line that does not qualify now never did, so its word was never asked and stays to come), so «sestu», «kjötsúpa», «þarftu» do not come again. `apply_to_learner` fills both from `plan.json` `caught_seed` and `caught_words`. The second half's catch skips every word in it. `listening_log` (a pick-out's *turn*, which the cap per lesson counts too, so its wordings are one question → the lesson it was last heard in; a log, not practice: the review and `knows()` do not read it) orders `pick_out_tasks`, least recently heard first. `Planner.catch_intro_task`: a new one-word vocab item that is a content word (a noun, or a filler of a pattern's slot; not «og») and not hard to say (`hard_sounds` or an authored `hard_words_of`: the plain introduction holds its slow, split model, #337) and not held by a longer new item of the lesson («þúsund» in «þúsund krónur»), that a partner line holds as its only unknown word, with the item's own meaning as the gloss — a line of the word's own scene first (a catch introduction names its scene aloud, so a scene the learner has not met yet is introduced as it is heard) (a theme or dialogue that shares a topic with the item), then the others (a theme level's lines, then an authored dialogue's opener or reply), and with no such line the sentence its introduction would have taught it in (`Builder.whole_home`: «Ljósið virkar ekki.», said by the partner, `home:` source) — and not a word already caught, in an earlier lesson or in this one; in `do_intro`, when `Builder.intro_catchable` (the plain introduction or the one inside the word's whole; not a form of a word met), at most `PlanConfig.catch_intros()` a lesson (`catch_intro_share`=0.1 of its target or count of new items: one in a 30-minute lesson; on a simulated 40-lesson course about one a lesson from lesson 18, when «Hvað þýðir þetta?» can be said), the introduction is `listening_tasks.introduce_by_catch` (an `intro` exercise: line, cue through the meaning, «Hvað þýðir …?», what is told as the learner asked it, the line again) and the item's usual ladder follows; the sentence the replaced introduction would have taught it in (`Builder.intro_whole`) stays its `wholes_taught`, so its practice and next-day question ask that sentence, not the bare word. `plan.json` `catch_introductions`, `catch_candidates` (new vocab items by outcome: where the supply runs out), `caught_before` (0 expected), `pick_outs_recent`, `pick_out_pool` (the distinct lines a pick-out can be made from now). `tests/test_catch_once.py`.
- **The lesson-26 preview's finds (#333).** `content.unlinked_instances` also sees a filler that has a tag of the slot's case but not the slot's own (`_same_case_tag`: `acc_thing` for `acc_request`), so «Get ég fengið leigubíl?» is linked (`leigubil` has `acc_request`); `Item.not_instance` declares a phrase that equals a pattern's sentence by coincidence of text («Ertu með regnhlíf?»). `filler_taught_today` does not play the pattern sentence again when the word was taught inside this very phrase (`wholes_taught` answer = the phrase): it is covered: the introduction of the word names the phrase too (`item_ids`), so the next-day question asks the phrase and the learner's answer settles it (without that it stayed `embedded` for ever, and the dialogues and drills that list it as a prerequisite waited). A cue never carries a stage direction (`meaning_spoken` of «Á þetta hótel, takk.» is gone; the situation says what is shown). «Má ég sofa?» is a named exception (`exclude_fills` on `ma_eg_inf`, LD §9). `tests/test_lesson26_finds.py`.
- **The written review asks in its own words (#312).** A `review` question's prompt came from the lesson exercise that practised the item; for a generated sentence that is the lesson's cue («Put it together yourself.», «In a sentence.», «Use the pattern again.», «Your turn.»), which tells a listener how the exercise relates to the one before.
  `review_wording.reword_review` (applied in `cli._plan` after `refine_review`, and in `refine-review` before it, so the bot's old queue questions are reworded too) turns a prompt that matches one of the cue templates (`LESSON_CUE_KEYS`: `recombine*`, `recombine_vocab*`, `recombine_again`, `recombine_new`, `hinted`, `cloze`, any language) into the meaning in the review's own form (the first `meaning` wording: «How do you say: …», ja 「…」は、何と言いますか？). A situation and any other prompt are kept. A cue behind the speaker's form («As a man: In a sentence. Say: …», `review_wording.speaker_form`) is reworded and keeps the form. **Every review question names the speaker's form its answer expects, as the lesson does:** `exercises.speak_as` (the lesson's `Builder._as` too) and `answer_gender` ("m" when the answer holds an item's `target_m`, "f" its `target`) are used by `cli._review_cue` / `_review_cues`, by `review_wholes.whole_for` (a part's sentence, the as-taught one included), and by `refine_review`'s last step, which names the form on every question whose answer has two forms, a stored one included (its items, its `through`, the fillers of a pattern among them, `review_wholes.made_of`, so a pattern sentence stored with the pattern alone is named too, lesson 34; its answer; a wrong form is corrected; report kind `speaker_form`). A pattern whose subject is the person spoken to (`addressee`, «Ertu {state}?», to a woman) agrees with that person, not the speaker: `Curriculum.speaker_agrees` is False for its template, so the lesson's `Builder._fills_gendered` asks it in the one form its meaning names, with no «A man says:», and the review's `speaker_items` reads no speaker's form from its fillers and takes a stale one off; the pattern is found from the answer (`_addressed`), since the bot stores no `through`, and an answer made before in the man's form («Ertu þreyttur?») takes the stored form (`addressee_answer`, report kind `addressee_form`; reviews of #385). The bot re-refines its queue when its `REFINE_VERSION` is raised. `tests/test_review_gender.py`. `plan.json` `review_lesson_cues` is the daily-read row (0).
  The bot re-runs `refine-review` over its queue when its `REFINE_VERSION` is raised. `tests/test_review_wording.py`.
- **The second half does not depend on the new-item arithmetic (#294).** `select_new` charges an item's components when it selects it; `mark_delivered_target` counts what was taught. An item selected and then not introduced (time ran out, a reordering) left them apart for the rest of the lesson, so `rotation_on()` stayed False and the pick-outs, catch tasks and scene replays never ran. The guard: when `components_total >= new_target` (nothing more can be selected) and the queue is empty or can no longer be afforded (`remaining_time() < need_for_new`), the rotation starts anyway. `meta.rotation_guard` is true when that happened with the target not counted as taught (`meta.target_delivered` False); both rows are in `plan.json`. `tests/test_rotation_guard.py`.
- **The «Slowly.» model is word by word at natural speed (#302, after #261).** `Builder._slow_line` says a line of two or more words through `_speak_spaced` with `Timing.intro_word_gap` (0.4 s) between the words, never at `slow_rate`: the introduction, the build-up chunks of a hard phrase, a part in its whole and a construction with difficulty ≥ 2. A single word with no authored syllables is said once more at natural speed (no slow/natural pair). `slow_rate` stays only on the pieces of an authored syllable split (#292, `Item.syllables`), where a stretched sound is the point. The transcript marks it «(word by word)» as for #261. `tests/test_slow_model.py`.
- **A pick-out marks its turns (#303, #335).** Concept 2 is finding the information one needs, so `listening_tasks._build` says the scene, then the need ending «… Listen and answer.» (`pick_out_need_<kind>`, e.g. «You want to know how much it costs. Listen and answer.»; a line holding several pieces says `pick_out_need_ask` with its authored question), then the line, the answer pause (the learner's turn: a recall's pause, not the generative one, since the answer is words just heard), «The answer:» (`pick_out_answer`, a framing line with its beat, #241), the answer in the other voice than the line's (the learner's turn, as the catch's question; lesson 28: the line's own voice sounded like the partner saying it again, and 4.2–4.5 s for «klukkan fimm» was long), the meaning, «Listen again.» (`pick_out_again`, framed with a beat) and the line again. The catch task keeps its own markers. A pick-out or catch that a drill follows then ends with «Back to speaking.» (`listening_back`, `Planner._close_listening`, run on the finished script where the next exercise is known; not before another listening exercise, a conversation, an aside or the closing, which open with their own line; `plan.json` `listening_closed`; lesson 34: the switch to the next question felt abrupt, `tests/test_listening_back.py`). The old question after the line is gone from the prompts. Not done: pointing back to a learner turn of the scene that asked for the same information (no data links a learner turn to a probe kind yet). `tests/test_pick_out_need.py`.
- **A change of voice always has a gap (#301).** `Script.separate_switches` is the last pass over a finished script (planner, before `retime`): wherever two speech segments (`narrate`/`speak`/`answer`) touch, a pause of role `switch` is put between them, `Timing.switch_gap` (0.4 s) at a change of voice or language and `switch_gap_same` (0.25 s) in the same voice, and `switch_gap_sentence` (0.6 s) in the same voice after a segment that ends a sentence (review: three lines in a row are three lines). It is its own floor, so fitting to length never shrinks it.
  `plan.json`/`script.json` `meta.switch_pauses` counts them and `meta.touching_switches` (`Script.touching_switches`, 0 after the pass) is the daily-read row. Notes say an English sentence whole and their examples as lines of their own: `content.notes_cutting_sentences` lists notes whose sentence holds more than one inline «…» fragment (an advisory in `validate`; a test pins that the count does not grow and that `modal_infinitive` is clean). The old #241 rule «a cue for the learner's action joins its line» is replaced: the cue, the gap, the line.
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
