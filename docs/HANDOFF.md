# Handoff note — audiolesson

_Last updated 2026-09-21 (session 19: issue #44 resolved — see below;
session 18 close-out follows). **Issue #34** ("Improve
lesson orchestration and learner experience," opened session 16 from a
real Lesson 3 transcript) is **closed**: 12 pilots across sessions
16–18 (PRs #36–#43) — milestone notes that stay short and speak
Icelandic examples in the native voice with immediate contrastive
practice, near-synonyms explicitly contrasted, situation-prompt
variation on repeat retrieval, no fabricated backward-build chunking,
smoothed instructor-prompt templates, a `drill_streak` counter that
pulls a dialogue or note forward instead of running long isolated-recall
stretches, and a new-item cap that bounds one learning arc rather than
the whole lesson so a lesson doesn't stop far short of its target with
plenty of curriculum left. Full narrative in "Session 16" through
"Session 18" below; the pilot-by-pilot list is item #1a in "Known gaps."

**Correction on closing #34** (owner review): "no open pilots" had
quietly drifted from "acceptance criteria met." Two criteria weren't
actually satisfied — a high drill streak with neither an eligible
dialogue nor an available note still falls through to plain recall, and
no learning arc is guaranteed a connected-use (dialogue/mini-situation)
moment of its own. Split both into **issue #44** rather than continuing
to expand #34; see #1a's correction note for detail. Watch for this
failure mode again on future long-running issues: a "pilots done" tally
is not the same claim as "the issue's own acceptance criteria hold,"
and this file should track the latter.

**Issue #44** (the two residuals split out of #34) is **done** —
session 19, see "Session 19" below for both fixes, their real-lesson
verification, and the rejected first attempt at point 1 (an
unconditional budget bypass that measured 19 asides in one lesson
before being replaced with a small bounded allowance). 100 tests, all
passing.

**Next up, per the owner's priority order:** issue #29 ("Design
curriculum around reusable concepts and communicative capabilities") —
(1) triage all `dialogue_sequencing_report()` findings (9 repeat
offenders plus large single-item gaps like `heyra`) — **done**, posted
as a comment on #29, not yet acted on; (2) a curriculum-wide dependency
audit across all 26 modules for reusable concepts and late-introduced
high-value concepts — not started; (3) a pilot testing whether the
`godur_gender` gender-agreement pattern generalizes to case/tense/
modality — not started. #29 stays open until the curriculum-wide audit
completes a full pass._
Keep
this current: whoever picks the project up next, human or AI, should
be able to continue from here without re-deriving decisions._

## Session 16: issue #34 opened — lesson orchestration and learner experience

The owner reviewed a real generated Lesson 3 transcript (Icelandic
course) and opened #34 with 8 related findings. It reads as a sequel to
#29: where #29 is about *what* gets taught and *when*, #34 is about
*how a lesson built from correctly-sequenced material still feels* —
several of its examples are drawn straight from #29's own output,
including a direct critique of the `godur_gender` milestone note
(pilots 2/3, PR #32/#33): too many grammar terms delivered at once
(accusative, singular, masculine/feminine/neuter, plus a forward
reference to case/number) for a spoken explanation, and it shouldn't
close with "Back to the lesson." — "this *is* the lesson."

Like #29, this isn't one fix. Broke it into 7 pilots, ordered by risk
and how much design judgment each needs before touching code:

1. **Instructor-prompt template artifacts (#34 point 8). Done.** Two
   independent causes, both mechanical: `audiolesson/phrasing/en.toml`'s
   `meaning` prompt list had `"Say: {meaning} in {language}."`, which
   collides with `exercises.py`'s `_m()` — it guarantees every English
   `meaning` already ends in terminal punctuation, so anything the
   template appends right after `{meaning}` doubles up ("Say: Well
   then. in Icelandic."). Fixed by reordering rather than stripping
   anything: `"In {language}, say: {meaning}"` puts the language name
   *before* `{meaning}`, so `meaning`'s own punctuation is free to end
   the sentence — the same word order the Japanese template already
   used (`"{language}で「{meaning}」と言ってください。"`), just not yet
   ported to English. Added
   `test_meaning_prompt_never_doubles_up_terminal_punctuation`
   (`PromptsTests`) asserting every English `meaning` variant ends with
   `{meaning}` itself, so nothing can be appended after it again.

   Second cause was specific to one item: `curricula/is-en/01-greetings.toml`'s
   `jaeja` had `meaning = "Well then. (the all-purpose Icelandic
   word)"`. **Correction from the owner on the original plan:** the
   parenthetical is semantic/pragmatic information, not pronunciation —
   `pronunciation_notes` was the wrong destination. `jaeja` already has
   a dedicated `[[notes]]` entry (`90-notes.toml`) explaining exactly
   this ("does the work of several Japanese words at once... rising
   tone... falling..."), so the fix is simply to normalize `meaning`
   down to `"Well then"` and let that existing note carry the nuance,
   rather than duplicating it in two places. `meaning_ja` was already
   clean (`"さて。／やれやれ。"`, no parenthetical) and untouched.

   **Scope check, not touched:** a grep found dozens of other items
   with parenthetical asides in `meaning` (`"(to a woman)"`, `"(the
   language)"`, `"(o'clock)"`, …) — an established, intentional
   disambiguation convention in this curriculum, not a mistake to
   clean up. `jaeja` was only worth fixing because it duplicated a
   dedicated note; the general convention stays.
2. **Shorten the `godur_gender` milestone note; retire the aside
   framing for milestones specifically (#34 point 1, half of it). Done.**
   Rewrote the note to name gender as the dimension up front and
   demote case/number to one trailing clause, dropping "accusative"/
   "singular" entirely rather than just de-emphasizing them — #34 only
   asked for the *current* dimension to be named, not every dimension
   the three examples happen to also hold constant. Added a
   `milestone_end` prompt ("Let's continue." / 「では、続けましょう。」,
   `audiolesson/phrasing/{en,ja}.toml`) so `Builder.note()`
   (`exercises.py`) now picks `milestone_end` vs `aside_end` for the
   closing line the same way it already picked `milestone_intro` vs
   `aside` for the opening — a milestone note no longer says "Back to
   the lesson." Updated `test_milestone_note_is_not_framed_as_a_cultural_aside`
   to check both ends.

   **Correction from the owner on the first wording (PR #37):** the
   first draft opened "Góðan daginn, Góða nótt, and Gott kvöld aren't
   three separate words" — grammatically odd, since the subject of
   "aren't ... words" is three *phrases*, not the words being taught.
   What actually needs saying is narrower: it's `góðan`/`góða`/`gott`
   specifically that are forms of one adjective, not the phrases
   themselves. Rewrote to put that claim in the main clause directly:
   "In Góðan daginn, Góða nótt, and Gott kvöld, góðan, góða, and gott
   are forms of the same adjective, meaning 'good.'" — same content,
   sounder sentence structure, and matched in `text_ja`. (Also
   raised, but left as-is by choice, not fixed: `milestone_end` could
   arguably be dropped entirely rather than reworded, since `_gap()`
   alone may be enough separation for a note that's already part of
   the lesson proper — noted as a matter of preference, not acted on.)
   79 tests, all passing; validate unchanged (993 items, 47 notes, ja
   gloss still complete).

   **Deferred, not part of this pilot:** "target-language examples
   inside explanations should be spoken by a target-language voice
   where practical" (#34 point 1, other half). `Note.text` today is one
   instructor-language string with the Icelandic phrases embedded as
   text inside it — making `Góðan daginn` etc. actually spoken by the
   target voice mid-explanation needs the note to carry structured
   segments (narration / target-language speech / narration …), which
   `Builder.note()` doesn't support at all yet. That's a real
   mechanism change, not a content edit — worth its own design pass
   once pilot 2 above is in, not bundled with it.
3. **Contrastive discrimination right after a milestone (#34 point 2).
   Done.** Turned out to need no new exercise shape and no new
   content: `godan_daginn`/`goda_nott`/`gott_kvold` already each have a
   distinct `situation` (bakery morning / bedtime / evening restaurant)
   from way back when they were first authored, so "notice → name →
   discriminate" is just replaying two of those three `situation`
   stages back to back, right after the note — the issue's own
   fallback suggestion ("simply present two familiar situations close
   together so the learner has to switch between forms"), which needed
   no verification risk at all since nothing new is asserted.

   `Planner._maybe_note()` now returns the milestone `Note` it played
   (`None` for an ordinary aside or nothing played), instead of
   `None` unconditionally. `build()`'s loop checks that return value
   and, when it's a milestone, immediately calls a new `do_discriminate()`
   closure (next to `do_recall`/`do_intro`): it takes up to two of the
   milestone's `items` that weren't just touched (excluding whatever's
   in `recent`, the same de-dup the rest of the loop already uses) and
   plays each one's `situation` stage via the existing `do_recall`,
   consuming its own slice of the lesson's time budget like any other
   exercise. Two, not more, and only from items with a `situation` —
   both already true of all three `godur_gender` items. **Correction
   (owner, after #38 merged):** the mechanism only actually generalizes
   to a milestone with *at least three* suitable items (`situation` +
   not the trigger) — with exactly two, excluding the trigger leaves
   only one candidate, and "note → two discrimination recalls" can't
   hold. Both current milestones have three, so this was never a
   blocker, but the "generalizes to any future milestone note" framing
   above overstated it; see the Known-gaps note this correction adds
   for what a 2-item milestone would need before this mechanism could
   honestly claim to cover it.

   Depended on pilot 2 landing first only in the sense of building on
   the same `milestone`/`_eligible_milestone` mechanism, not on its
   specific wording.

   Added `test_milestone_note_is_followed_by_contrastive_discrimination`,
   simulating 15 real lessons: whenever `godur_gender` fires, the very
   next exercise must be a `situation`-stage recall of one of its three
   items, and if a second one immediately follows too, it must be a
   *different* item. (First draft of the test assumed exactly two
   discrimination exercises always follow — failed once run, because
   `recent` can already contain two of the three gate items when the
   milestone fires, leaving only one fresh candidate that lesson; fixed
   by asserting only what's actually guaranteed: at least one follows,
   and any second one differs from the first.) 79 → 80 tests, all
   passing; validate unchanged.

   **Owner review on #38: relaxing the test hid a real gap instead of
   closing it.** Two findings:
   1. Excluding everything in `recent` (not just the trigger item) can
      leave only one fresh candidate when the milestone fires with two
      of its three items already in `recent` — one recall is retrieval,
      not discrimination between forms, so the *implementation* should
      guarantee two, not have the test relaxed to tolerate one.
   2. A milestone only needs `remaining >= 40` to fire at all, but
      `do_discriminate()` separately re-checked the same 40-second floor
      before *each* recall — so a milestone could fire and then produce
      zero discrimination exercises if time ran out right after the
      note itself.

   Fixed both in code, per the owner's own suggested rule, rather than
   softening the test back down: `do_discriminate()` now excludes only
   `recent[-1]` (whatever was just exercised, i.e. the milestone's
   trigger) instead of the whole `recent` deque — with exactly three
   items per current milestone, that always leaves two distinct
   candidates. And the per-recall time check is gone entirely: once a
   milestone has committed to firing, its discrimination block is
   treated as one instructional unit and always completes, even if the
   lesson runs a little over its nominal target — preferable to a
   milestone with no follow-up practice. Tightened
   `test_milestone_note_is_followed_by_contrastive_discrimination` back
   to require exactly two different items every time (across all
   milestones, all 20 simulated lessons), not "at least one."
4. **Explicitly contrast near-synonyms: Afsakið / Fyrirgefðu / Því
   miður (#34 point 3). Done.** Verified before writing anything, per
   the "halló" mistake's discipline (session 6): searched dict.cc and
   Glosbe for `því miður` — "unfortunately / alas / sadly," a general
   regret marker, not itself negative-specific — and for
   `afsakið`/`fyrirgefðu`, confirming the curriculum's existing glosses
   ("Excuse me." / attention-getting; "Sorry." / apology for something
   you did) were already right, so only `Því miður`'s gloss needed a
   fix. The curriculum's own `thvi_midur_ekki` (module 24, "Því miður
   ekki." = "Unfortunately not.") independently corroborates this: it
   exists specifically to *add* "ekki" (not) for the negative sense,
   which only makes sense if the bare phrase isn't already negative on
   its own. Fixed `thvi_midur`'s `meaning` from "Unfortunately not. /
   I'm afraid so." (the only opposite-polarity `/`-joined meaning in
   the whole curriculum — every other one, checked by grep, pairs true
   synonyms like "Wait. / Hang on.") to "Unfortunately. / I'm afraid
   so." — same-polarity, matching the verified sense and the
   established convention.

   Same "notice → name" shape as the gender milestone, but for
   communicative function instead of grammar: added `three_kinds_of_sorry`
   (`90-notes.toml`), reusing `Note.milestone` directly rather than
   adding a sibling flag — the mechanism (`_eligible_milestone`, never
   filler, priority over budget) is generic on `items`, not specific to
   grammar, so a second milestone note needed no new abstraction. Also
   confirms pilot 3's own "generalizes to any future milestone note
   whose items are phrases with situations" claim: `afsakid`/
   `fyrirgefdu`/`thvi_midur` already each have a `situation`, so the
   contrastive-discrimination follow-up (pilot 3) fires for this note
   too, for free.

   **Two milestones existing at once surfaced a real budget bug,
   caught by the existing rationing test going red:** `_note_budget_left()`
   counted milestones toward the ~1-per-12-minutes aside cap, but
   milestones bypass that cap when *deciding whether to fire* — so one
   milestone firing could let a regular aside "spend" a budget slot
   that a second, later milestone would then push past the intended
   total (observed: 3 notes in one lesson against a cap of 2). Fixed by
   excluding milestones from what `_note_budget_left()` counts
   entirely: ordinary asides stay capped at the budget regardless of
   how many milestones also fire, and milestones stay uncapped
   regardless of how many asides already have. Updated
   `test_notes_follow_related_items_and_are_rationed` to check the
   corrected invariant (asides ≤ budget; milestones separate), and
   generalized the two milestone-behavior tests
   (`test_milestone_note_never_fires_before_all_its_items_are_known`,
   `test_milestone_note_is_followed_by_contrastive_discrimination`) to
   loop over every milestone note in the curriculum instead of
   hardcoding `godur_gender`, so they'll keep covering future ones too.
   80 tests, all passing (same count — existing tests generalized, not
   duplicated); validate: 993 items unchanged, 48 notes (was 47), ja
   gloss complete (2002 strings).

   **Owner review on #38 (pilot 4 landed on the same PR): two more
   fixes, plus housekeeping.**
   1. The budget-separation fix above was incomplete: the end-of-lesson
      "at least one aside per lesson" fallback still checked
      `if not self.notes_played`, and `notes_played` includes milestone
      ids too — so a lesson where a milestone fired but no *ordinary*
      aside had played would skip the fallback anyway, indirectly
      letting a milestone crowd out cultural asides through this second
      path. Extracted a `_aside_played()` helper (`planner.py`, next to
      `_note_budget_left()`) that only counts non-milestone notes, and
      switched the fallback to check it. Added a direct unit test
      (`test_milestone_does_not_suppress_the_end_of_lesson_aside_fallback`)
      against `_aside_played()` itself rather than simulated lesson
      output — a first draft tried asserting on `Planner.build()`
      output with `note_chance=0` forced, and it passed even with the
      bug still in place, because the loop's separate "nothing else
      fits" filler branch can independently supply an aside and masked
      the missing fix. Lesson: when a fix is one boolean expression
      buried inside a large method, test that expression directly
      rather than trusting a full-simulation assertion to isolate it.
   2. `three_kinds_of_sorry`'s text drew too sharp a line between
      `Afsakið` and `Fyrirgefðu` ("Afsakið gets someone's attention.
      Fyrirgefðu apologizes for something you did.") — reads as mutually
      exclusive, but `Fyrirgefðu` can also mean "excuse me." Rewrote
      using the owner's own suggested wording almost verbatim: `Afsakið`
      as the common "excuse me"/attention-getter, `Fyrirgefðu` as also
      meaning "excuse me" but especially suited to apologizing, `Því
      miður` framed as categorically different (regret about a
      situation, not an apology) rather than a third parallel case.
   3. Housekeeping: the PR title/body still described pilot 3's
      pre-fix behavior ("excludes `recent`" / "at least one follows").
      Updated to match what's actually in the PR now (both pilots 3 and
      4, with pilot 3's guarantee of exactly two discrimination recalls).

   81 tests (was 80 — the new direct unit test), all passing; validate
   unchanged.
5. **Situation-prompt variation for repeated retrieval (#34 point 4).
   Done.** Went with option (a) from the plan: `Item` gained
   `situations: list[str]` (glossed the same way as every other field —
   `situations_ja`, just added to `_GLOSSED_ITEM` — so per-language
   promotion at load time needed no special-casing for the list type).
   `Item.situation_for(exposures)` rotates round-robin through
   `situations` by the item's total exposures so far
   (`ItemState.exposures`, already tracked for other reasons — no new
   persisted state); falls back to the old singular `situation` when
   `situations` is empty, so every existing item needed zero changes.
   `Item.has_situation` replaces the old `bool(item.situation)` checks
   in three call sites (`exercises.py`'s `recall()`/`_recall_construction()`,
   `planner.py`'s `ladder()` and `do_discriminate()`) so both forms are
   recognized as "this item has a situation stage."

   Retrofitted the issue's own example, `velkomin` — "Friends arrive at
   your door. Welcome them in." repeated verbatim on every spaced
   review — with two more situations conveying the same welcoming
   function ("A guest has just arrived at your home...", "Someone is
   visiting you for the first time...").

   Added three tests: `situation_for`'s rotation and singular-fallback
   behavior directly (synthetic `Item`s, no curriculum needed), and a
   real 25-simulated-lesson integration test confirming `velkomin`'s
   narrated situation text actually varies across repeats, not just
   that it theoretically could. 81 → 84 tests, all passing; validate:
   993 items unchanged, ja gloss still complete (2002 strings — the
   coverage counter counts one glossable string per *field*, not per
   list element, so swapping `velkomin`'s `situation`/`situation_ja`
   for a 3-entry `situations`/`situations_ja` doesn't change the total).

   **Owner review on #39: the rotation only worked *between* lessons,
   not within one.** `ItemState.exposures` — the rotation index —
   updates only once a whole lesson is applied (`record_lesson()`), so
   every situation-stage recall of the same item *while a lesson is
   still being built* saw the same `exposures` value and picked the
   same variant. If a lesson's own reactivation ladder or a review pass
   recalled `velkomin` at the situation stage twice in one lesson, both
   would replay the identical cue — the exact within-lesson repetition
   from the issue's own example that this pilot exists to fix. The
   25-lesson integration test didn't catch this: it only required
   variety across the pooled total, which a lesson-internal
   `A, A, A` / next lesson `B, B` pattern would still satisfy.

   Fixed by giving `Builder` its own lesson-scoped counter,
   `_situation_uses: dict[str, int]` (reset fresh per lesson, since a
   new `Builder` is constructed per `Planner.build()` call): `_situation()`
   now starts from the persisted `exposures` base and adds this
   lesson's own use-count for that item before indexing into
   `situations`, then increments the counter. Strengthened the existing
   integration test to also assert no two *consecutive* narrations of
   `velkomin`'s situation stage within a single lesson are identical,
   and added a direct test that calls `Builder.recall(..., "situation")`
   three times in a row on one `Builder` instance (simulating three
   same-lesson recalls before any lesson is ever applied) and requires
   all three to differ.

   Noted but not acted on, per the owner's own "not necessarily a
   blocker for this pilot": `ItemState.exposures` counts *every*
   exercise stage for an item (`intro`, `meaning`, `hinted`, …), not
   just situation recalls, so which variant comes up next across
   lessons depends somewhat incidentally on what other stages that item
   happened to be exercised at — a dedicated `situation_uses` counter
   on `ItemState` would be the cleaner long-term signal if this
   mechanism needs more precision later. Left as `exposures` for now.
   84 → 85 tests, all passing; validate unchanged.
6. **Lesson shape: no long isolated-drill runs, prefer connected
   dialogue as vocab grows, allow ending early (#34 points 5–6). First
   of several small changes, done — done after pilot 7 at the owner's
   request.** Grouped together in the original plan — they're the same
   underlying planner rebalancing (how `build()`'s fallback ladder in
   `planner.py` decides what to do when nothing specific is due) seen
   from three angles. **Highest blast radius of the seven:** `build()`'s
   existing fallback order (recall due → intro new → pull a reactivation
   forward → extra new item → repeat → note → second review pass → stop
   short) is exactly what several current tests pin down
   (`test_length_close_to_requested`, `test_later_lessons_fill_the_requested_time`,
   `test_first_lesson_at_default_pace_is_short_not_padded`,
   `test_no_item_twice_in_a_row`), so per the plan's own guidance this
   proceeded as several small changes, each checked against the existing
   pacing tests, rather than one rewrite.

   Shipped the first: a `drill_streak` counter (`PlanConfig.drill_streak_limit`,
   default 5) tracking the length of the trailing run of consecutive
   `"recall"`-kind exercises with nothing else in between. Step 3 of
   `build()`'s fallback ladder — the periodic `since_dialogue >=
   dialogue_every` dialogue check — now also fires once `drill_streak`
   reaches the limit, pulling an eligible dialogue forward ahead of its
   usual schedule instead of waiting through however many more isolated
   recalls the periodic schedule would have allowed first. All existing
   pacing tests passed unchanged — the fixture curricula apparently
   don't hit long enough drill runs for this to move their numbers — so
   verified the mechanism itself with a dedicated synthetic-curriculum
   test (`curriculum_from_dict`, 10 known review items, one eligible
   dialogue, `dialogue_every` set unreachably high so only the streak
   could pull it forward): exactly 4 isolated recalls, then the
   dialogue.

   **Owner review on #40: the streak was counting loop iterations, not
   the actual exercise sequence.** The first cut incremented
   `drill_streak` by one whenever the loop iteration's *last* exercise
   was a recall, which is wrong whenever one iteration appends more
   than one exercise — the clearest case being a milestone note plus
   its two discrimination recalls (`_maybe_note`/`do_discriminate`):
   five recalls, then a note, then two more recalls has a true trailing
   streak of 2 (the note resets it), but the old code saw only that the
   iteration's last exercise was a recall and incremented the
   *previous* streak to 6 — able to pull a dialogue forward on stale
   evidence of monotony that the note had already broken. Fixed by
   extracting `Planner._trailing_drill_streak(sc)`, which recomputes the
   run length from the actual tail of `sc.exercises` every time rather
   than incrementing a carried-forward counter — exactly the owner's
   suggested fix, and now directly unit-testable. Added
   `test_trailing_drill_streak_resets_across_a_multi_exercise_iteration`,
   constructing the five-recalls/note/two-recalls sequence directly and
   asserting the trailing count is 2. Also removed a now-redundant
   manual `drill_streak = 0` after a dialogue plays — the recompute
   already gets that case right on its own. 87 → 88 tests, all passing;
   validate unchanged.

   **Not done, still open:** "the planner may finish below the nominal
   time target rather than adding low-value filler repetitions" (the
   other half of point 5) and "combine known items into mini-situation"/
   listening-comprehension alternatives (point 6's other suggested
   alternatives to another isolated drill) — these are separate design
   threads from the dialogue-preference change above, deliberately not
   bundled into the same pilot per the "several small changes, not one
   rewrite" guidance.
7. **Linguistically-meaningful backward-build chunking (#34 point 7).
   Done — the cheaper of the two options in the original plan.**
   Confirmed the pre-existing algorithm reproduced the issue's own
   examples exactly (`Fyrirgefðu` → `ðu, gefðu, irgefðu, Fyrirgefðu`;
   `Afsakið` → `ið, sakið, Afsakið`) before touching anything. Considered
   the other option — a real Icelandic syllabification/morphology
   reference to produce *correct* sub-word chunks — and rejected it for
   this pilot: even a linguistically correct split doesn't fully solve
   the problem, since the issue's actual concern is partly independent
   of correctness — "a standalone orthographic suffix may not have the
   same pronunciation it has inside the complete word" is about TTS
   synthesizing a fragment with no context that it's part of a longer
   word, which a better syllable boundary alone doesn't fix. Went with
   the issue's own explicitly-sanctioned fallback instead: no chunking,
   slow whole-word repetition.

   Removed `_syllable_pieces()` (`content.py`) entirely — `_VOWEL_RUN_RE`
   stays, since `is_hard()`'s use of it (counting vowel runs to gauge
   whether a single word is long enough to deserve extra practice) is a
   much smaller, safer claim than using the same boundaries to cut a
   word into chunks, and nothing else depended on the removed function.
   `Item.backward_chunks()` now returns just `[self.target]` for a
   single word with no author-supplied `chunks` (word-splitting for
   3+-word phrases — a real, pronounceable unit, the issue's own
   `"vel"/"svo vel"/"Gjörðu svo vel"` counter-example — is untouched).
   `Builder.intro()` (`exercises.py`) now checks `len(backward_chunks())
   > 1` rather than just `is_hard()` to decide whether to frame practice
   as "build it up from the end": a hard single word with no real split
   falls through to the same slow-then-natural whole-word repetition an
   easy multi-word phrase already gets, instead of either a fabricated
   split or silently skipping the extra practice `is_hard()` is there to
   provide.

   Zero curriculum content changes needed: 108 single-word items across
   the Icelandic course trigger `is_hard()`, none had author `chunks`,
   so all 108 (including the issue's own `afsakid`/`fyrirgefdu`) pick up
   the fix automatically. Author `chunks` remain fully supported for a
   word whose boundaries are genuinely verified — nothing here removes
   that escape hatch, only the automatic guess.

   Updated `test_long_single_word_is_hard_and_builds_backward_by_syllable`
   (renamed to `..._gets_no_synthetic_sub_word_chunks`) for the new
   behavior, and added a `Builder.intro()`-level test confirming a hard
   single word's narration includes "slowly"/"natural" but not
   "build_up". This shortened intros for those 108 items enough to
   drop `test_later_lessons_fill_the_requested_time`'s peak-lesson
   threshold from 24 to 23 minutes on the fr-en-a1.toml fixture (a real,
   expected side effect — less speech per hard-word intro than the
   removed synthetic build-up produced), which needed the threshold
   recalibrated rather than the fix reconsidered. 85 → 86 tests, all
   passing; validate unchanged.

No code or curriculum content changed this session — this is the same
"docs first" move session 15 made for #29, for the same reason: #34 is
a design-and-authoring/algorithm project touching several different
subsystems (content schema, note rendering, planner pacing, backward-
build) at different risk levels, not a single PR.

## Session 17: issue #34 pilot 8 — target-language speech inside notes

Picked up the "other half" of #34 point 1, deferred at pilot 2 above for
lack of a mechanism (`Note.text` was one instructor-language string with
Icelandic phrases embedded as plain text; making them actually spoken by
the target-language voice needed the note to carry structured segments,
which `Builder.note()` didn't support at all).

**Done.** Rather than restructure `Note`'s schema into arrays of typed
segments — a bigger schema change than the problem needs — marked
target-language phrases inline with `«...»` inside the existing single
`text`/`text_ja` strings: `In «Góðan daginn», «góðan» is…`. Added
`_NOTE_TARGET_RE` and `Builder._speak_note_text()` (`exercises.py`),
which splits a note's text on the marker and alternates `_narr` (the
surrounding prose, instructor voice/language) with `_speak` (each marked
phrase, target voice/language) — exactly the two existing primitives
every other exercise already uses to interleave instructor commentary
with native-voiced target speech, just newly wired into `note()` instead
of a single `_narr(note.text)` call. A note with no `«»` in its text
behaves exactly as before (one `_narr` call for the whole string), so
none of the other ~46 notes needed touching for the mechanism itself to
be safe.

Added a validation check (`content.py`, alongside the existing note
checks) rejecting a note whose `«`/`»` counts don't match, so a stray or
missing marker fails `audiolesson validate` instead of silently
mis-splitting at build time. Applied the markup to both existing
milestone notes — `godur_gender` (`Góðan daginn`/`Góða nótt`/`Gott
kvöld`, `góðan`/`góða`/`gott`, `dagur`/`nótt`/`kvöld`) and
`three_kinds_of_sorry` (`Afsakið`/`Fyrirgefðu`/`Því miður`) — in both
`text` and `text_ja`; no wording changed, only markup added around
already-verified Icelandic words, so no new pronunciation/usage claims
to verify. Documented the convention in `docs/CURRICULUM.md` alongside
the pre-existing (but previously undocumented) `milestone` flag.

The other ~46 cultural-aside notes also name Icelandic words inline and
could get the same markup, but that's now purely a content-authoring
task with no mechanism blocking it — left for a future pass rather than
bundled in here, per the same "small changes, not one rewrite" guidance
sessions 15–16 have been following.

91 tests (88 → 91: one for the split/alternation behavior on a
synthetic note, one confirming an unmarked note still narrates as a
single piece, one for the new validation error); `audiolesson validate
curricula/is-en` unchanged apart from the two notes' text (993 items, 48
notes, ja gloss still complete).

### Pilot 9: a high drill streak with no eligible dialogue now pulls a note forward instead

Pilot 6 (Session 16) only handled half of "prefer connected/varied
activity over another isolated drill": once `drill_streak` hits its
limit, step 3 of `build()`'s fallback ladder tries a dialogue — but if
`eligible_dialogue()` returns `None` (none exist yet, all are exhausted
for this lesson, or the learner doesn't know enough for any of them),
nothing happened: the streak check silently fell through to step 4
(another review pick, i.e. likely another isolated recall), with no
fallback logic at all.

**Done.** When the streak triggers step 3 and no dialogue fits, `build()`
now tries a note instead — a "varied activity," not another flashcard
drill — via `self._pick_note(None)`, subject to the same
`_note_budget_left()`/`remaining >= 40` checks the ordinary note path
uses, but bypassing the random `note_chance` roll (this is a deliberate
action to break up a monotony problem the streak just detected, not
optional filler subject to a coin flip — the same reasoning
`_eligible_milestone` already uses to bypass `note_chance` for a due
milestone). If no note fits either, behavior is unchanged: falls through
to step 4 exactly as before pilot 6 existed. `drill_streak` resets to 0
on its own the following iteration once a note plays, via the existing
`_trailing_drill_streak` recompute — no separate reset needed.

The issue's own "or stop" fallback needed no new code: it already exists
as step 5's cascade at the bottom of the loop, which stops the lesson
once genuinely nothing (due, new, review, or note) is left — see pilot
10 below for why that cascade's own weakest tier (a second review pass)
is a separate, much bigger change than this one.

Added `test_high_drill_streak_pulls_a_note_forward_when_no_dialogue_fits`:
a synthetic curriculum with 10 known items and *no dialogues at all* (so
`eligible_dialogue()` always returns `None`), `note_chance=0.0` (so a
note can only appear via this new fallback, not the ordinary per-exercise
random roll — isolates which mechanism produced it), `drill_streak_limit=3`.
Confirms exactly 3 isolated recalls, then a note. 91 → 92 tests, all
passing; `audiolesson validate` unchanged.

**Owner review on PR #41: the streak breaker ran too late — a due
scheduled reactivation could still win first.** The first cut put the
whole streak-triggered block at its original step-3 position, *after*
step 1 (a due scheduled reactivation). Step 1 sets `acted = True`
unconditionally whenever something is due, and step 3 was guarded by
`if not acted`, so on any turn where a reactivation happened to be due
*and* the streak was already at its limit, the reactivation fired —
another isolated recall — and the streak check never even ran. Exactly
the uninterrupted run this mechanism exists to break, just relocated
one step earlier in the ladder.

Fixed by moving the whole check to a new step 0, before step 1, so it
runs before *any* branch that would emit another recall — not only the
ordinary review path (step 4) the original test already covered. Step
1's due-reactivation loop is now itself guarded by `if not acted`, since
step 0 may have already consumed the turn. The periodic (non-streak)
dialogue check keeps its old step-3 position and lost the now-redundant
`or streak_triggered` in its condition — step 0 already tried both
dialogue and note for that case.

Added `test_high_drill_streak_wins_over_a_due_reactivation_too`:
introduces one new item immediately (scheduling a reactivation a few
exercises later) with `drill_streak_limit=2`, so the reactivation's due
turn coincides with the streak already being at the limit. Confirmed
against the pre-fix code first that this exact scenario reproduced the
bug (`['intro', 'recall', 'recall', 'recall', 'note', ...]` — the
reactivation winning at position 3, note pushed to 4) before fixing it
(`[..., 'note', ...]` at position 3). 92 → 93 tests, all passing;
`audiolesson validate` unchanged.

**Owner review on PR #41, second finding: `_speak_note_text()` could
narrate bare punctuation.** A note that marks a short list of phrases —
exactly `godur_gender`'s real shape, `In «Góðan daginn», «Góða nótt»,
and «Gott kvöld», ...` — splits into a "," fragment between two of the
marked phrases wherever the only text separating them is punctuation.
The first cut narrated every non-empty split fragment unconditionally,
so a bare `","` became its own meaningless instructor-language TTS call.
The existing test (`Say «halló» to greet someone, and «bless» ...`)
didn't expose it because none of its prose fragments happened to be
punctuation-only.

Fixed in `_speak_note_text()`: a prose fragment with no alphanumeric
characters now becomes a beat (`self._beat`) instead of a `_narr` call —
preserving the pause the punctuation implied without synthesizing it as
speech. A fragment with real words (e.g. `", and"`) is unaffected and
still narrates normally. Added
`test_note_text_does_not_narrate_bare_punctuation_between_marked_phrases`,
using the actual `"In «A», «B», and «C», ..."` shape, confirming the
bare `","` becomes a pause while `", and"` still narrates. 93 → 94 tests.

**Owner review on PR #41, smaller points, both fixed:** (1) validation
compared `«`/`»` *counts* only, which passes malformed markup with one
of each but not actually paired — `"»foo«"` (reversed order) or one real
pair plus a stray unmatched open. Moved the shared `NOTE_TARGET_RE` from
`exercises.py` into `content.py` (so validation can use the same regex
without a circular import) and changed the check to run the regex and
confirm nothing with a `«` or `»` is left over, instead of comparing
counts. Added `test_note_with_equal_but_malformed_guillemet_counts_is_rejected`
(`"»uh oh« then «real»"` — one of each character, still rejected). 94 → 95
tests. (2) `Builder.note()`'s docstring still said "instructor only," no longer
true after pilot 8 — reworded.

### Pilot 10, investigated: ending a lesson early instead of padding with a second review pass

The other half of point 5 (deferred at pilot 6): "the planner may finish
below the nominal time target rather than adding low-value filler
repetitions." The mechanism for this already exists and needed no new
code: `PlanConfig.max_review_passes` (added in session 3, "Fixed lesson
length") defaults to 2, and step 5's very last resort — reached only
once every other option (a due-later reactivation pulled early, an extra
new item, a plain repeat, a note) has failed — re-reviews everything
already reviewed *this same lesson*, one stage harder, purely to fill
remaining time. Setting `max_review_passes=1` disables exactly that: the
lesson then ends via step 5's existing `else: break` once real material
(new + due + one review pass + notes) runs out, instead of manufacturing
a second pass.

**Not done: left at the default (2), not flipped.** Tried flipping the
default to 1 and measured the actual effect on `course()` runs built from
the small fixture curricula (`fr-en-a1.toml`, 47 items) that several
existing tests use as their "does a lesson reach its requested length"
fixture:
- `course(8, minutes=30)`: lesson lengths went from needing ≥23 min at
  their peak (`test_later_lessons_fill_the_requested_time`'s existing
  threshold) to a peak of 18.1 min — every one of the 8 lessons fell
  well short of 30.
- `course(6, minutes=15)`: lesson 6's built content dropped from filling
  ~900s (with `fit()`'s pause-stretch bridging the small remaining gap)
  to ~519s of raw content — `fit()` would need to stretch pauses by 1.25×
  just to reach 649s, still 250s short of 900, breaking both
  `test_fit_lands_on_the_requested_length` and
  `test_fit_tolerance_leaves_pauses_alone_when_close`.

That's a 20–60% reduction in lesson length on this fixture, not the
modest shortfall "may finish below the nominal time target" suggests —
and it directly undoes a deliberate, tested guarantee from session 3
("Fixed lesson length": the second pass and `fit()`'s clamped pause
stretch were built *together* specifically so a requested lesson length
is reliably met). Flipping a foundational, already-tested guarantee like
that by default, for every existing and future curriculum, is a bigger
call than a single pilot should make unilaterally — unlike pilot 9 above
(additive, `elif` on an existing branch, zero test impact), this one
changes what "ask for a 15-minute lesson" *means* app-wide and nothing
here indicates the owner has weighed that specific tradeoff yet (the
issue's own wording reads as "don't force it," not "even a much shorter
lesson than requested is fine").

Left `max_review_passes` at its existing default (2) — this pilot's
actual code change was reverted back out after measuring the above — and
documented the finding here instead. Anyone who wants "end early, never
pad with a same-lesson repeat" today can already set
`max_review_passes=1` in `PlanConfig`; it just isn't the default, and
there is no `--` CLI flag for it yet either. **Open question for the
owner:** should the default change (accepting shorter lessons once
material runs thin), should it be a new CLI-exposed opt-in instead, or
should the second pass stay the default and this half of point 5 close
as "already possible, intentionally not defaulted"? No test or code
changed for this half; pilot 9 above is the only code change this
session made to point 5/6.

### Pilot 11: marked up the remaining cultural-aside notes with «...»

The one piece of pilot 8 explicitly left for later: the other 46 notes
in `90-notes.toml` (all but the two milestones) also name Icelandic
words and phrases inline, and none of them had `«...»` markup yet — the
mechanism existed but almost the entire note set still narrated its
Icelandic examples in the instructor's voice.

**Done.** Went through all 46 notes and added `«...»` around every
genuine Icelandic word or phrase actually named in `text`/`text_ja` —
24 notes had at least one (`tvo_l`, `pylsa`, `vedur_smalltalk`,
`thetta_reddast`, `jaeja`, `nofn`, `konur_nofn`, `takk_fyrir_sidast`,
`takk_fyrir_matinn`, `kennitala`, `bjor`, `straeto`, `hestar`, `kindur`,
`hakarl`, `skyr`, `fiskur`, `islenska`, `enska`, `tolur`, `kurteisi`,
`huldufolk`, `jolabokaflod`, `ull`); the rest either don't name a
specific Icelandic word in prose (most cultural asides, e.g. `skor`,
`heitt_vatn`, `kaffi`) or only reference one indirectly (place names
like Reykjavík, left unmarked and treated as already-anglicized, the
same way they read in the surrounding English prose everywhere else in
this file).

Three deliberate exclusions, to avoid marking things that either aren't
real spoken vocabulary or would mis-render:
- **Bare letters/digraphs discussed as sounds**, not words — `tvo_l`'s
  `'t'`, `'l'`, `'ll'`, `'nn'` and `islenska`'s `þ`/`ð`. `is_hard()`-style
  single graphemes aren't a "phrase" a TTS voice can meaningfully say in
  isolation, unlike the real words in the same notes (`fjall`, `gull`,
  `allt`, `tölva`, `tala`, `völva`), which are marked.
- **Japanese words used as the instructor's own reference point** for a
  Japanese-background learner — `sentō`, `genkan`, `keigo`, `nattō`,
  romanized asides like `'atsui desu ne'` or `'sate'`/`'yare yare'`/`'sō
  ka'`. These are the *known* language's own vocabulary, not the target
  language; marking them would hand Japanese text to the Icelandic
  voice.
- **`text_ja` fields that only carried a katakana transliteration** of
  the Icelandic term, rather than its actual spelling — see the owner
  review right below, which corrected the first cut's call to leave
  these as-is.

No wording changed anywhere, no new content or claims — every marked
term already existed in already-reviewed text; this pass only added
punctuation around it. `audiolesson validate` unchanged (993 items, 48
notes, ja gloss still complete) — the balanced-marker check added in
pilot 8 passed on the first attempt across all 46 edits, and the full
95-test suite (several of which load this exact curriculum) still
passes unchanged. No new tests: the mechanism itself
(splitting/alternating voices, punctuation handling, validation) is
already covered by pilot 8/9's tests against synthetic notes — this
pass is pure content, not a mechanism change.

**Owner review on PR #42: the katakana-only exclusion left the Japanese
track incomplete, contradicting the pilot's own claim.** The first cut
above reasoned that fixing `hestar`/`hakarl`/`skyr`/`fiskur`/
`huldufolk`/`jolabokaflod`/`ull`'s `text_ja` would mean "swapping the
katakana for the real Icelandic spelling, a content change bigger than
adding markup" and left them unmarked — but that directly contradicted
the top-of-file claim this same session wrote, "every note in the
curriculum that names a real Icelandic word now speaks it with the
native voice": true for `text`, not yet for `text_ja` on these seven.
For a Japanese-background learner, `skyr`'s note said only "スキール"
(the katakana approximation) and never actually heard "Skyr" from the
Icelandic voice — the whole point of pilot 8.

Fixed by keeping the katakana as a parenthetical reading gloss (so the
familiar approximation stays in the transcript) while adding the real
Icelandic spelling in `«...»` right before it, e.g. `スキール` →
`«Skyr»（スキール）`. Same pattern for all seven:
`hestar` → `«tölt»（トルト）`, `hakarl` → `«Hákarl»（ハウカルトル）` and
`«brennivín»（ブレニヴィン）` (`Þorrablót` was already marked),
`fiskur` → `«Plokkfiskur»（プロックフィスクル）`, `huldufolk` →
`«huldufólk»（フルドゥフォルク）`, `jolabokaflod` →
`«jólabókaflóð»（ヨウラボウカフロウズ）`, `ull` →
`«lopapeysa»（ロパペイサ）`. Casing matches each note's own `text`
field exactly. `audiolesson validate` and all 95 tests still pass
unchanged (pure content, no mechanism touched) — every note in the
curriculum that names a real Icelandic word now genuinely speaks it
with the native voice, in both instructor languages.

## Session 18: issue #34 pilot 12 — the new-item cap should bound an arc, not a lesson

The owner posted a real Lesson 3 output (30-minute request, plan/script/
transcript attached) reframing pilot 10's open question. The lesson
ended at ~15 minutes despite plenty of curriculum left (Lesson 3 of a
993-item course), and the shape wasn't "ran out of material" — it was:

```text
8 new items introduced (hits the per-lesson cap)
↓
16 consecutive isolated recalls
↓
"final review" block
↓
8 more isolated recalls
↓
lesson ends at ~15 min despite a 30 min request
```

The owner's diagnosis, reframed from "should `max_review_passes`
default to 1 or 2?" to a deeper question: **when the requested lesson
is substantially longer than one coherent learning arc, how should the
planner spend the remaining time?** Proposed model: a lesson can
contain more than one arc (introduce → practice → contrast → connected
use → review), with `new_items + 2` bounding *one arc*, not the whole
lesson — "the planner should prefer starting another coherent learning
block over padding the current block with low-value repeat review.
Finishing early remains acceptable when no worthwhile next block can be
formed, but a large shortfall … should not be the normal consequence of
a lesson-level new-item cap."

**Verified before touching code.** Reproduced the exact scenario two
ways: (1) a fresh 3-lesson simulation against the real curriculum
(seed=1), and (2) loading the owner's own actual `learner.json` after
lesson 2 and rebuilding lesson 3 directly. Both matched the real
output's structure (8 new items, 0 dialogues all lesson, notes
exhausted by exercise ~30). Instrumented `build()`'s final `else:
break` to print state at the exact moment it fires: **`idx=77,
duration=1039.7s, remaining=668.3s`** — the lesson stopped with over 11
minutes of its 30-minute budget still unused, because every fallback
tier was independently exhausted at the same time: `can_intro=False`
(new-item cap reached), `pending=0` (arc 1's own reactivations all
done), `note_budget_left=False` (both ordinary-note slots and both
eligible milestones already used), and `passes=2` already equal to
`max_review_passes` (a *second* review pass had already run and also
emptied out — not just the first). This is a stronger, more precise
version of the owner's own diagnosis: the mechanism doesn't just lack a
next step after *one* review pass, it lacks one after *every* available
fallback, with real budget sitting idle.

**Done.** Added a new fallback tier to `build()`'s step 5 cascade,
positioned *before* the second-pass branch (prefer new material over
re-reviewing this lesson's own material, per the owner's framing) and
*after* the repeat/note branches (still prefer those — they reuse
already-scheduled structure): once nothing else fits, `remaining >=
need_for_new`, `not new_queue` (arc 1 is fully drained, not mid-batch),
and `reviews_used` is non-empty (this lesson actually reviewed
something — see the first-lesson finding below), select a fresh batch
of `cfg.resolved_new_items()` new items, `do_intro()` the first
immediately and queue the rest for step 2 to drain at the normal pace.
`can_intro`'s original cap (`cfg.resolved_max_new_items()`) is left
untouched everywhere else — only this one explicit, budget-gated path
can start a new arc. `closing_reserve` (sized once at lesson start from
the *original* new-item count) is recomputed the same way whenever a
new arc starts, since the closing block recalls every introduced item,
not just arc 1's.

**Three real bugs found and fixed while building this, each caught by
the existing test suite or a new synthetic test:**

1. **Infinite loop.** The first cut used `continue` after queuing a new
   batch, matching the pre-existing second-pass branch's style — but
   unlike that branch (guarded by `passes < max_review_passes`, so it
   can only fire twice total), nothing stopped this branch from firing
   again at the *same* `idx` before `intro_gap` had elapsed, since
   `continue` skips the `idx += 1` at the loop's bottom. Fixed by
   calling `do_intro()` directly instead of queuing-and-continuing —
   every branch in the cascade must consume an `idx` tick, and this one
   hadn't been.
2. **Defeated `test_first_lesson_at_default_pace_is_short_not_padded`.**
   Without a gate, a genuinely first lesson (nothing to review at all)
   hit this same fallback path immediately and ballooned to 11 new
   items instead of the intended ≤5 — directly undoing session 3's
   deliberate "a lesson with nothing to review ends short" guarantee.
   Fixed by gating on `reviews_used` being non-empty: proof this lesson
   actually reviewed something and ran that pool dry, which is false
   for a true first lesson and stays false throughout it.
3. **Defeated `test_prerequisites_respected`.** The dedup fix for
   avoiding a duplicate item across two arc-starting calls in one
   lesson (excluding `new_queue`'s contents from `select_new`, not just
   `introduced`) had a side effect: `select_new`'s readiness check now
   treated an item still sitting *unintroduced* in the queue as
   satisfying another item's prerequisite, since both are folded into
   the same `chosen_ids` set. A construction whose slot-filler prereq
   was still queued (not yet actually taught) could get selected and
   `do_intro`'d immediately, jumping ahead of its own prerequisite.
   Fixed by gating on `not new_queue` instead (only start a new arc
   once the previous one is *fully* introduced, never mid-batch) and
   dropping `new_queue` from the exclude set — readiness now only
   trusts `introduced`, exactly like every other branch already did.

Added `test_a_spent_arc_with_substantial_time_left_starts_a_new_one`
(a synthetic 26-item curriculum, pace forced to `new_items=2` so the
cap is hit quickly: asserts more items get introduced than
`resolved_max_new_items()` allows, with no duplicates),
`test_a_spent_arc_does_not_start_a_new_one_on_a_genuinely_first_lesson`
(same curriculum, no learner history at all: asserts the cap still
holds), and `test_a_new_arc_still_respects_prerequisite_order` (a
20-item prerequisite chain, reproducing bug 3 directly — confirmed it
failed before the `not new_queue` fix and passes after). 95 → 98
tests, all passing; `audiolesson validate` unchanged.

**Real-world effect**, re-running the owner's own scenario from their
actual post-lesson-2 `learner.json`: lesson 3 went from stopping at
**1144.5s** (19.1 min, 656s/36% short of the 1800s target) to
**1689.1s** (28.2 min, 111s/6% short) — 14 items introduced instead of
8, no duplicates, prerequisites intact. A fresh 15-lesson simulation
against the real curriculum shows the mechanism self-moderates as
intended: lessons land within a couple of minutes of the 30-minute
target from lesson 2 onward, while lesson 1 (genuinely nothing to
review) correctly stays short at 694s; by lesson 10+, once the review
pool has matured enough to sustain a full lesson on its own, the extra
arcs stop firing and `new` settles back to the base pace of 6 — the
mechanism only engages when it's actually needed.

**Scoping note for whoever picks this up next:** this reuses the
existing per-item intro/reactivation/review machinery for "arc 2"
rather than introducing arcs as a first-class concept with their own
practice/dialogue/review sub-structure, as the owner's fuller diagram
sketched. It produces the intended practical effect (prefer more
teaching over repeat-review filler once genuinely nothing else fits,
while never exceeding one arc's cap without cause) with a small, safe
diff, but a "real" multi-arc redesign — explicit arc boundaries, a
connected-use moment per arc, per-arc dialogue preference — is a
bigger, separate design thread if the owner wants to take it further.

## Session 19: issue #44 — both residual gaps from #34's closure

The owner shared a real Lesson 2 transcript showing exactly the two
patterns #44 was opened for: eight consecutive `meaning: Já`/`meaning:
Nei` recalls back to back (11:03–11:49), and another eight consecutive
`situation` recalls right before "final review" (13:19–14:14) — neither
interrupted by a dialogue or a note.

### Point 1: a high drill streak with no dialogue/note available fell through to plain recall

**Root cause, verified before touching code.** Reproduced the
transcript's pacing (`new_items=8`, ~16-minute lesson) against the real
curriculum and instrumented step 0's note branch directly. Confirmed
`drill_streak` climbing unbroken from 5 to 15 while every single check
showed `dlg=None, note_budget_left=False` — the lesson's *one* allowed
ordinary aside (`max(1, minutes // 12)` — just 1 for a 16-minute lesson)
had already been spent by the ordinary per-exercise aside roll long
before the streak ever needed it, so `_note_budget_left()` stayed
`False` for the rest of the lesson and pilot 9's dialogue-or-note
fallback (session 17) became a permanent no-op.

**First cut, rejected by its own numbers:** simply not gating the
streak-triggered note branch by `_note_budget_left()` at all (mirroring
how a due milestone already bypasses it). Fixed the reproduction case,
but a 12-lesson `auto`-mode simulation on the real curriculum showed it
measured as high as **19 asides in one 30-minute lesson** — an
unconditional bypass doesn't just rescue the streak, it turns rationing
off entirely and recreates issue #21's original "asides feel like
non-sequiturs" complaint from the other direction.

**Done, with a bounded allowance instead.** Added
`PlanConfig.max_streak_relief_notes` (default 2): once the ordinary
ration (`_note_budget_left()`) is exhausted, up to this many *more*
notes may fire specifically to break a drill streak with no eligible
dialogue — not unlimited, a small separate budget spent only when the
streak genuinely needs it. Re-ran the 12-lesson simulation: consistently
2–4 asides per lesson (ration + relief), never runaway. Re-ran the
16-minute reproduction: longest unbroken recall run in the main
scheduling loop (excluding the deliberate end-of-lesson closing recap,
which isn't part of this problem) dropped from 15 to exactly
`drill_streak_limit` (5) for the portion covered by the ration+relief
budget; once both are spent, an occasional longer run can still occur
in a genuinely thin, packed lesson — a real resource limit, not a
regression, and the streak's "or stop" fallback still applies via step
5's existing cascade once nothing (due, new, review, or note) is left.

Updated `test_notes_follow_related_items_and_are_rationed`'s ceiling
from `2` (the bare ordinary ration) to `2 + max_streak_relief_notes`,
with its docstring explaining the new exemption alongside the existing
milestone one. Added
`test_streak_relief_notes_are_bounded_not_unlimited`: a synthetic
12-minute lesson (ration forced to exactly 1) with 30 review items and
no dialogues, confirming exactly `1 + max_streak_relief_notes` = 3
notes fire — not fewer (the relief mechanism must engage) and not more
(it must stay bounded even though the streak keeps retriggering and 7
more notes remain available).

### Point 2: no learning arc was guaranteed a connected-use moment

**Root cause.** `do_recall()`'s per-item dialogue-stage handling
(`stage == "dialogue"`, always an item's *last* ladder stage) only
attempted `eligible_dialogue(prefer_item=item)` when `since_dialogue >=
dialogue_every // 2` — a frequency-spacing gate meant to stop dialogues
clustering when several long-known review items happen to cycle back to
"dialogue" stage close together. Applied unconditionally, it also
silently skipped a *freshly introduced* item's own first (and only,
since "dialogue" is the ladder's last stage) attempt at connected use
whenever that item's own reactivation schedule reached "dialogue" before
`since_dialogue` had built back up — which is common, since a new item's
four reactivation gaps (`[3, 5, 8, 13]`) climb the ladder quickly.
Confirmed directly: a minimal synthetic scenario (one new item wired to
one dialogue, `dialogue_every` unreachably high, drill-streak disabled
to isolate this from pilot 9's mechanism) produced `dialogues: []` on
the pre-fix code — the dialogue never played at all, despite the item
being fully practiced and the dialogue being trivially eligible the
whole time.

**Done.** The spacing gate now applies only to items *not* introduced
this lesson (older material cycling back through ordinary review);
an item that's part of this lesson's `introduced` list always gets its
dialogue-stage attempt — that reactivation *is* its arc's connected-use
moment, and since "dialogue" never recurs later in the same lesson for
that item, skipping it meant losing the only chance entirely, not
just delaying it. Re-ran the same synthetic scenario post-fix:
`dialogues: ['d1']` fires reliably. A 15-lesson simulation against the
real curriculum shows dialogues now accumulate steadily as vocabulary
grows (`nagranni` from lesson 6, `tungumal` from lesson 9, `kaffihus`
from lesson 12) rather than being left entirely to the periodic
schedule's luck.

Added `test_a_freshly_introduced_items_own_dialogue_stage_is_not_skipped`,
confirmed against the pre-fix code to reproduce `dialogues: []` before
passing on the fix.

**Scoping note:** like pilot 12, this reuses existing per-item
machinery rather than modeling arcs explicitly — "this lesson's
`introduced` list" stands in for "the current arc." It guarantees a
connected-use *attempt* for any item that's part of *some* dialogue's
`required_items`; it does not (and cannot, without new curriculum
content) do anything for an arc whose items aren't wired into any
dialogue at all — a content gap, not a planner gap, and one #29's
curriculum-wide audit may surface incidentally.

100 tests (98 → 100), all passing; `audiolesson validate` unchanged.

## Session 15: #23 and #25 closed, consolidated into #29

The owner reorganized the open issues right after session 14: closed #23
("minimal-pair tips") and #25 ("dialogue eligibility should depend on
vocabulary already learned"), and opened #29, "Design curriculum around
reusable concepts and communicative capabilities," as one issue covering
both. This isn't a new problem — it's the same "curriculum sequencing
should be deliberate" thread session 14 already found running through
both issues, now written up as its own top-level design document instead
of living as an aside inside two separate ones.

#29 generalizes what #25 was reaching for (reusable vocabulary,
introduced early and deliberately) to the whole curriculum: choosing the
right teaching unit (word, construction, grammatical distinction, or
discourse pattern) for a high-value concept, and introducing grammatical
dimensions (case, gender, number, tense, person, mood, modality,
agreement) deliberately once familiar examples make a contrast visible —
its own worked example is `Góðan daginn`/`Góða nótt`/`Gott kvöld`, three
items every learner already knows, whose differing adjective endings are
a gender-agreement pattern nobody has ever pointed out as such. That
last point is #23's original ask, reframed: teach the dimension, not a
per-pair hint.

This session updated docs (`docs/HANDOFF.md`'s "Known gaps" #1,
`docs/CURRICULUM.md`'s top guideline) to point at #29 instead of the now-
closed #23/#25, and folded #23's old "Known gaps" entry into #1 rather
than leaving a stale line item for a closed issue. #29 is a design-and-
audit project scoped to the whole 993-item curriculum, not a single fix,
so it needs its own sequence of focused pilots rather than one PR — this
session then did the first of them.

### Pilot 1 — the `fara`/"want to, going to" cluster was already built, just mis-sequenced

Looked for a piece of #29 concrete enough to execute in one pass, matching
both the issue's own worked example (`fara`) and `dialogue_sequencing_report()`'s
empirical top findings (`viltu`, `fara` flagged as high-repeat, large-gap
words). Found that the reusable construction infrastructure the issue is
asking for already existed, in `curricula/is-en/14-daily.toml` — a `tags =
["inf"]` bare-infinitive vocab cluster (`fara_heim`, `sofa`, `borða`,
`fara_i_sund`, `fara_ut`, `hvíla mig`, `versla`, `kaupa_mida`,
`hringja_heim`, `fara_a_safnid`, `drekka_kaffi`) feeding four generative
constructions (`eg_vil` "Ég vil {inf}.", `eg_aetla_ad` "Ég ætla að
{inf}.", `viltu` "Viltu {inf}?", `eg_nenni_ekki` "Ég nenni ekki að
{inf}.") — it was simply sequenced at module 14 of 26, item order ~400 of
993, far later than its everyday-conversation value justifies. No design
work was needed, only relocation: this is exactly the "recombination
engine" #29 asks for, already correctly shaped.

Moved the whole cluster (all 11 vocab items and all 4 constructions,
unedited) from the end of `14-daily.toml` to the end of
`02-clarifying.toml` (module 2 of 26), just before that file's own
`[[dialogues]]` — with a comment explaining the mismatch between the
items' `topics = ["daily", …]` tags and the file's "clarifying" theme:
sequencing value outweighed topic-file purity here, and `topics` (not the
filename) is what actually drives `--topics` filtering, so nothing about
that split is lost. Checked first that none of the 11 vocab items'
`target` text collides with an existing item elsewhere (`grep` across
`curricula/is-en/`) and that nothing outside module 14 depends on the
constructions' *old* position — module 15 already reuses `fara_i_sund`
and `versla` as fills for its own "inf"-tagged constructions, and moving
the definitions earlier only helps that (module 15 still merges after
module 2).

Effect on `dialogue_sequencing_report()`'s advisory output: before this
pilot, `fara` and `viltu` were both in the top repeat-offender list;
after, neither appears — `audiolesson validate curricula/is-en` now
reports only `frábært, og, líka, sjáðu, vegabréf, góð, ferð, bara,
krónur, hundruð` as words repeating across dialogues whose earliest
teaching item sits far past what those dialogues otherwise need. Full
validate output unchanged otherwise (993 items, no new errors); full test
suite (72 tests) still green.

Two more `fara`-shaped constructions turned up during the grep for
collisions — "Ég fer {time}." and "Ég fer {frequency} í sund." in
`06-time.toml` — outside the 4-construction/inf-vocab cluster this pilot
touched. Left alone; worth a look in a later #29 pass but not part of
this one's scope.

**Follow-up (session 15, pilot 3 below): investigated, no action
needed.** Both are `eg_fer`/`fer` present-tense-plus-slot patterns
("I'm leaving {time}" / "I {frequency} go swimming"), grammatically
unrelated to pilot 1's "bare infinitive + vil/ætla að/viltu/nenni ekki
að" cluster despite the shared verb — not duplicates, not something
pilot 1 should have absorbed. They already live in module 6 of 26,
which isn't a sequencing gap on the scale `dialogue_sequencing_report()`
flags. Closing this out rather than leaving it as an open thread.

### Pilot 2 — naming the góðan/góða/gott gender-agreement pattern

The issue's second worked example. `godan_daginn`, `goda_nott`, and
`gott_kvold` were already all early items in module 1 (introduced within
the first ~20 items of 993) — so, unlike pilot 1, there was no
sequencing gap to fix, only the "notice → name" moment itself, which
didn't exist: three fixed phrases sat there with no one ever pointing
out that `góðan`/`góða`/`gott` is the same adjective (`góður`, "good")
taking a different accusative ending for each noun's grammatical gender
(`dagur` masc. → `góðan`, `nótt` fem. → `góða`, `kvöld` neut. → `gott`).

Added a `[[notes]]` entry (`godur_gender`, `curricula/is-en/90-notes.toml`)
rather than a `kind = "transform"` item. `transform` fits an operation
practised on new material — the planner's transform intro shows two
worked examples then asks the learner to produce a third from the
`examples` pool (`exercises.py`'s `_intro_transform`/`_recall_transform`),
which means every pair in `examples` has to itself be a correct,
independently-verified Icelandic phrase. There are only three verified
nouns here (all three already exist solely as fixed accusative forms
inside these greetings — no bare nominative `dagur`/`nótt`/`kvöld` vocab
item exists anywhere in the curriculum to check against), and Icelandic
noun case morphology varies enough by declension class that inventing a
fourth noun+greeting pair to reach `transform`'s usual 3+ examples would
mean asserting new grammar without the way to verify it against an
existing item — precisely the risk `docs/CURRICULUM.md` already warns
about (the "halló" homograph mistake, session 6). A note only speaks
English/Japanese explanation over phrases the learner already knows are
correct, so it teaches "notice, name" safely; it doesn't attempt
"practice, apply to new words."

**Left undone on purpose:** the generative "apply the pattern to a new
noun" half of the issue's ask. That needs either a native-speaker check
or a verified noun-declension reference before adding new Icelandic
content, which this pass didn't have — flagged in "Known gaps" #1 below
rather than guessed at.

Validate: 993 items unchanged, 47 notes (was 46), ja gloss coverage
still complete (2001 strings, +1 for the new note). Full test suite (72
tests) unchanged.

#### Owner review on #32: a plain note doesn't guarantee the moment it's for

The owner reviewed the PR before merging and found the first cut relied
on coincidence in three places, plus one overclaim in the text:

1. Attaching the note to `gott_kvold` alone and reasoning from file
   order doesn't actually gate anything — `_pick_note(None)`'s generic
   filler path (used when nothing else fits, or when a lesson would
   otherwise end without any note played) can hand out *any* unheard
   note regardless of `items`, so `godur_gender` could fire before the
   learner had reached `gott_kvold` at all. And even when triggered via
   the "related to what was just exercised" path, `_maybe_note()` still
   subjected it to the same `note_chance` coin flip as a cultural aside,
   so reaching the right item was no guarantee of actually hearing the
   explanation there.
2. Modeling it as an ordinary `Note` conflated an optional cultural
   aside ("A quick aside. … Back to the lesson.") with a deliberate
   instructional moment — exactly the framing #23 originally objected
   to, recreated one level down.
3. The note's English/Japanese text overclaimed: "Icelandic adjectives
   always change to match the gender of the noun" is true here but
   omits that case and number matter too, and that these three phrases
   are a clean example precisely *because* they hold case (accusative)
   and number (singular) constant while only gender varies.

Fixed all three rather than replying that the scope was intentionally
small — the owner's own suggested fix (a `milestone` flag on the
existing `Note`, not a new abstraction) was the right-sized answer, and
implementing it was no larger than the review comment itself:

- `Note` gained a `milestone: bool` field (`audiolesson/content.py`).
  `Planner._eligible_milestone()` (`planner.py`) is a new, separate path
  from `_pick_note()`: a milestone note fires only when *every* id in
  its `items` has been met (`learner.has_met`, checked fresh each time —
  no reliance on introduction order) and it has never been heard before
  (`learner.notes_heard`); `_maybe_note()` checks this first and, when it
  finds one, plays it unconditionally — no `note_chance` roll. `_pick_note()`
  (both the related-item and the generic-filler call sites) now excludes
  every milestone note from its pool unconditionally, so one can never be
  handed out as an unrelated aside. `godur_gender`'s `items` now lists
  all three phrases, not just the last one — the gate no longer depends
  on which order they were taught in.
- Fixing the ordinary-`_pick_note` exclusion above surfaced a second,
  latent bug during testing: without it, nothing stopped
  `_eligible_milestone` itself from firing the *same* milestone note
  again in a later lesson every time one of its items came up for
  review — caught by the existing `test_notes_follow_related_items_and_are_rationed`
  test going red once the new tests below were added. Fixed by also
  checking `learner.notes_heard` inside `_eligible_milestone`, the same
  "never repeat" guard `_pick_note` already had.
- `Builder.note()` (`exercises.py`) now opens a milestone note with a
  new `milestone_intro` prompt ("Here's a pattern worth noticing." /
  「気づいてほしいパターンがあります。」, added to both
  `audiolesson/phrasing/en.toml` and `ja.toml`) instead of "A quick
  aside." — the closing line is unchanged; only the framing that matters
  ("this is optional trivia" vs. "you're ready for this") changed.
- Rewrote `godur_gender`'s text to name case and number as held
  constant and flag that they, too, affect adjective endings and will
  come later — the owner's own suggested wording, adapted to keep the
  concrete dagur/nótt/kvöld → góðan/góða/gott mapping.
- Added three tests (`tests/test_audiolesson.py`): the milestone note
  never fires before all three phrases are known (run across 15
  simulated lessons on the real curriculum — this is what would have
  caught problem 1 directly), it's never handed out by `_pick_note(None)`
  as filler, and `Builder.note()` uses the new intro line for a
  milestone note.

Validate and full test suite unchanged in outcome (993 items, 47 notes,
ja complete); test count rose from 72 to 75.

#### Second round: milestone eligibility still had two timing gaps

The owner re-reviewed the fix above and found the "guarantee" from
point 1 was still incomplete, plus a smaller side effect:

1. `_eligible_milestone()` checked `learner.has_met(x)`, but a newly
   introduced item isn't written into `LearnerState` until
   `apply_to_learner()` runs after the *entire* lesson script is built —
   so a lesson that introduces the third of the three phrases wouldn't
   count it as met yet, and the note would only fire one lesson later
   than intended, on some future incidental review of one of the three.
2. `_maybe_note()` checked `_note_budget_left()` before even looking for
   an eligible milestone, so an earlier cultural aside using up that
   lesson's note budget (or a `max_notes` of 0) could silently suppress
   a milestone that was actually due.
3. Smaller: `_pick_note()`'s "are there any unheard notes?" scan
   (`any(heard.get(n.id, 0) == 0 for n in self.cur.notes)`) still
   iterated over milestone notes too. An ineligible milestone is
   permanently "unheard" from `_pick_note`'s point of view since it
   never picks one anyway, so counting it could wrongly force the "only
   offer unheard notes" restriction and block repeats of ordinary notes
   that had all genuinely been heard.

Fixed all three (`planner.py`):

- `_eligible_milestone()`'s gate is now `learner.has_met(x) or x in
  self.exposures` — `Planner.exposures` (already existed, used for the
  reactivation ladder) tracks every item touched so far in the
  *current*, still-being-built lesson, so the milestone becomes eligible
  the moment its last item is exercised, same lesson, not the next one
  that happens to touch one of the three again.
- `_maybe_note()` now checks `_eligible_milestone()` first, gated only
  on there being enough time left to fit a note (`remaining >= 40`) —
  the ordinary `_note_budget_left()`/`note_chance` checks now only apply
  to the non-milestone path below it. A due milestone can no longer be
  crowded out by an earlier aside or a tight budget.
- The "any unheard notes?" scan in `_pick_note()` now excludes milestone
  notes (`if not n.milestone`), so an ineligible one no longer
  suppresses repeats of ordinary notes that are all actually heard.

Added three more tests: `_eligible_milestone` becomes eligible via
`planner.exposures` alone (without touching `LearnerState`), a milestone
fires even with `max_notes=0`, and `_pick_note` still returns an
already-fully-heard ordinary note when the only unheard note is an
ineligible milestone. Also had to rewrite the first round's "never fires
before all items are known" test: it was asserting `has_met` *before*
`Planner.build()`, which is now provably too early a checkpoint by
design (that's exactly the gap point 1 fixed) — it now checks `has_met`
*after* `apply_to_learner()` for the same lesson, i.e. "a lesson that
played the note must end up knowing all three," which the old,
one-lesson-later behavior also happened to satisfy but for the wrong
reason. 75 → 78 tests, all passing; validate unchanged.

### Pilot 3 — `frábært` was the report's own top repeat offender

PR #32 (pilot 2) merged; picking the next pilot directly from
`dialogue_sequencing_report()`'s own output rather than the issue's
worked examples this time. Its "words repeating across dialogues"
list had `frábært` first: a partner says "Frábært!" (great!) as an
early reaction in **seven** dialogues — `tungumal` (module 2, the
curriculum's second dialogue overall), then modules 6, 9, 15, 21, 23,
25 — but the word itself wasn't taught as a vocab item until module 18.
Textbook case for the pattern pilot 1 and pilot 2 both established:
find it, don't invent it, just move it earlier.

Relocated the existing `frabaert` vocab item (`kind = "vocab"`, `tags =
["adj_neut"]`, unedited) from `curricula/is-en/18-adjectives.toml` to
the end of `01-greetings.toml`, right before that module's own dialogue
— the same "before dialogues" placement pilot 1 used in module 2.
Checked first that nothing in module 18 depends on its *former*
position: the only other reference is `prereqs = ["frabaert"]` on a
later phrase in the same file, which only gets easier to satisfy by
moving the prerequisite earlier; and `adj_neut` has dozens of other
tagged items, so no construction's "at least two fills" invariant
depends on this one.

Chose module 1 over module 2 (where the first dialogue needing it
actually is) because `01-greetings.toml` already ends with two other
single-word discourse-reaction phrases (`endilega` "Please do.",
`audvitad` "Of course.") right before its own dialogue — `frábært` is
the same kind of item, so it fits the existing shape there rather than
starting a new "promoted items" pile in module 2 on top of pilot 1's.

Effect: `dialogue_sequencing_report()`'s advisory pair count dropped
from 53 to 49, and `frábært` no longer appears in the "words repeating
across dialogues" list (now: `og, líka, sjáðu, vegabréf, góð, ferð,
bara, hundruð, krónur`). Validate: 993 items unchanged; full test suite
(78 tests) unchanged. Also closed out the "two other `fara`-shaped
constructions in `06-time.toml`" open thread from pilot 1 — see the
note added to pilot 1's writeup above; they turned out to be a
different grammatical pattern, already early, not a sequencing gap.

## Session 14: issues #25–#27, starting with #27 (durable learning)

Three new issues arrived together, all written by the owner as substantial
design proposals with explicit acceptance criteria but a deliberately open
implementation schema — a different scale from the one-line bugs earlier in
this batch. Reported all three, flagged that #27 underlies #25 (dialogue
"already known" gating is only meaningful if "known" means durably known,
not same-lesson presumed success) and arguably #26 too, and got a decision:
implement in dependency order #27 → #25 → #26, and for #25, one
dialogue-level list rather than a per-turn field. This entry covers #27.

### Issue #27 — same-lesson recalls were counted as durable learning

`ItemState.is_learned` (`successes >= 2`) gates everything downstream:
`LearnerState.knows()`, which gates prereqs (`planner.py`'s `all(...)`
checks), construction-slot fills (`exercises.py`), and dialogue eligibility.
`successes` was incremented by `len(climbed)` — every non-intro stage
reached *that lesson* — so an item introduced this lesson, reactivated
twice more at expanding gaps in the same sitting (a real, intentional
feature — see the ladder in `stages.py`), already had `successes == 2` and
counted as "learned" before the lesson even ended. Presumed-success mode
(the default) never distinguishes "recalled five minutes apart" from
"recalled after an actual multi-day gap."

The fix reuses machinery that already existed for exactly this
distinction: `_schedule_success()`'s interval math already refuses to grow
an item's spacing interval on an early review — "no new evidence about
long-term retention" is a comment already in that function, one paragraph
above where this bug lived.

- Added `ItemState.durable_successes`, a second counter alongside
  `successes`. `is_learned` now checks `durable_successes >= 2`, not
  `successes >= 2` — `successes` is untouched and keeps its other jobs
  (the `unfamiliar_multiplier`/`familiar_multiplier` split in `Timing`,
  `review_priority`'s scoring, `review_stage`'s climb-or-repeat call —
  none of those are about cross-item unlocking, so none of them needed to
  change).
- `record_lesson()` now calls a new `_is_durable_review()` (factored out of
  `_schedule_success`'s own early/fresh check, called *before*
  `_schedule_success` mutates `due`/`interval_days`) and increments
  `durable_successes` by exactly 1 — once per lesson, however many stages
  were climbed that lesson — only when this review is neither the item's
  first (intro) lesson nor early against its due date.
- `report()`'s failure path now demotes `durable_successes` alongside
  `successes`, so explicit "I got this wrong" feedback can revoke durable
  status, not just lower the raw count.
- `cli.py status` gained a `dur` column next to `ok` so the two counters
  are both visible when debugging pacing/eligibility.

**Consequence, expected and real:** items now take genuinely longer to
become usable as prereqs/construction fills/dialogue dependencies — around
two real spaced reviews after intro, not one lesson. `test_lessons_form_a_
sequence` needed its `course(6)` bumped to `course(10)`: the first dialogue
in the sample French curriculum now appears at lesson 9 rather than
somewhere in lessons 3–6, which is the intended behavior change working,
not a regression to paper over (same category as the `hallo`-position and
`new_items` fixture updates in earlier sessions).

Test added: `test_durable_successes_need_a_review_on_or_after_its_due_date`
in `tests/test_audiolesson.py::PacingTests`, driving `LearnerState.
record_lesson()`/`report()` directly through same-lesson repeats, an early
reactivation, a genuine due-date review, and a reported failure.

**Next:** issue #25 (dialogue eligibility keyed on comprehension of the
partner's actual lines, via a per-dialogue `comprehension_requires` list)
now has a meaningful "already known" to build on.

### Issue #25 — investigated, blocked on a scope decision

Chose the schema (one `comprehension_requires` list per dialogue, sibling
to the existing `requires`) before writing any code, and checked what it
would actually contain by computing it: for every dialogue, tokenize its
`opener`/`partner` lines and, for each word, find the earliest-`order`
item anywhere in the curriculum whose `target` contains that exact word
form — the same word-matching #22's audit already used, just resolving to
a specific item instead of "does one exist at all."

Every word resolved to *some* item (proper names aside), but "earliest"
is sometimes nowhere near the dialogue. `nagranni` — the very first
dialogue in the curriculum, today gated on 5 basic items — has a partner
line, "Gott að heyra. Jæja, ég verð að fara." ("Good to hear. Well, I have
to go."), where `heyra`/`verð`/`fara` don't have an early item at all:
the earliest is #926, #788, and #398 of 993. Those three words are only
ever taught as parts of fixed idiomatic phrases much later in the
curriculum, not as freestanding vocabulary, so there's no early item to
point at — literal word-level gating would push `nagranni`'s eligibility
from "5 basic items" to "essentially the whole curriculum." Checked a few
other dialogues too; this is the general pattern, not one bad case.

Posted this finding as a comment on #25 rather than guessing at scope or
picking between "content-words-only" and "hand-curated per dialogue"
unilaterally — both are real options with different costs (the former
needs a judgment call about what counts as a content word; the latter is
a bigger authoring pass than #22's, which only needed *a* replacement
wording, not a decision about what's prerequisite-worthy). No code
changes for #25 this session; `Dialogue.requires` is unchanged.

### Issue #25, reframed by the owner: this was never a gating problem

The owner's reply rejected the whole premise, not just the two options
above: *treating dialogue dependencies as something to fix by adding
prerequisites was the wrong abstraction from the start.* Their point,
condensed — a dialogue needing `nagranni`'s three words isn't evidence
that those words need a prerequisite gate; it's evidence the curriculum
never gave `fara` (to go) the dedicated, early, reusable item its actual
generativity (combines with destinations, intentions, obligations, plans,
transport, leave-taking) deserves. Fix the *sequencing*, and the
dependency problem mostly dissolves on its own. They also drew the line
between this issue and #26 explicitly: **#25 is what the learner should
have been taught and when; #26 is how scaffolding fades once that
knowledge genuinely exists** — #26's fade (done, see above) only pays off
once #25's sequencing is actually fixed, not before.

Asked directly what to do next; got two answers:

1. Ship the diagnostic now. Done: `dialogue_sequencing_report()` in
   `content.py`, wired into `audiolesson validate`. It's advisory, not
   gating — confirmed by `test_dialogue_sequencing_report_is_advisory_
   not_gating` explicitly asserting the flagged item never enters
   `Dialogue.required_items`. It reports, per dialogue, the word whose
   earliest teaching item sits furthest past what the dialogue already
   requires, plus which words repeat across multiple dialogues — that
   repetition is the real signal (a word several *different* dialogues
   independently need is a strong "this should have been an early,
   reusable item" candidate, not a coincidence). Current top repeaters
   in the Icelandic course: `frábært`, `og`, `viltu`, `líka`, `sjáðu`,
   `fara` — `fara` among them, matching the owner's own example exactly.
2. Elevate this to the project's actual top priority, not a bounded
   pilot fix: *"そもそも会話に出てくる&使えるべき高価値語を教え込む、のはこの
   アプリ全体の最優先事項にして欲しい"* ("teaching high-value words that
   show up in conversation and should be usable — I want that to be this
   app's overall top priority"). Recorded as item **#1** in "Known gaps"
   below (previously items were only reordered within their own issue's
   scope; this is the first time an item has been placed ahead of
   everything else project-wide) and as the first guideline in
   `docs/CURRICULUM.md`'s "Guidelines that make lessons good."

**Not done this session:** the actual re-sequencing — moving/adding early
items for `frábært`/`viltu`/`fara`/etc. and rewiring the dialogues that
depend on them. The report finds the gaps; closing them is real
curriculum-authoring work, sized more like #22's 27-dialogue rewrite than
anything smaller. That's the next concrete step whenever this is picked
back up, guided by the report's repeat-word list.

### Issue #26 — scaffolding now fades on repeat encounters

`Builder.dialogue()` always narrated a translation of every partner line
(`dialogue_partner_said`, when `translate_partner`) and an explicit "say
X" cue (`turn.cue`) for every turn — so answering correctly never
actually required understanding the partner's target-language line. The
existing `dialogues_done` repetition counter (already used to grow how
many turns a dialogue plays, and to add a natural, narrator-free replay
pass once a dialogue is fully learned) turned out to be exactly the
"encounter count" signal issue #26 asked for — no new state needed.

- `Builder.dialogue()` gained `assisted: bool = True`. Translation now
  only narrates when `assisted`. The per-turn cue now narrates when
  `assisted` **or** the learner hasn't heard the partner say anything yet
  this dialogue (`heard_partner`, true once any opener or partner line
  has been spoken) — a turn that opens the dialogue with no `opener` has
  nothing to react to, so it always keeps its cue regardless of
  `assisted`, rather than leaving the learner with zero information.
- `Planner._play_dialogue()` passes `assisted=(times == 0)`: full
  scaffolding on the first encounter, comprehension-driven from the
  second encounter on. The existing fully-natural replay pass (once a
  dialogue is complete and has been played before) is untouched — it
  already matched the issue's "stage 3."
- Deliberately binary, not the full three-tier gradient the issue
  sketched (assisted / responsive / natural): `times == 0` vs. `times >
  0`, plus the pre-existing replay-once-complete pass as the natural
  stage. A finer gradient (e.g. keeping the cue but dropping only the
  translation for one encounter in between) is possible later if this
  turns out too abrupt in practice — nothing here forecloses it, `times`
  is still the only signal read.

Test added: `test_dialogue_scaffolding_fades_on_later_encounters` in
`tests/test_audiolesson.py::LessonStructureTests`, checking both the
assisted and unassisted narration sets directly, including the
no-opener-turn-keeps-its-cue exception.

## Session 13: issue #22, the content half — dialogues used untaught words

Asked the owner how to proceed on issue #22's open question (was it: add
the missing words as new vocab items, reword the dialogues to stay inside
taught vocabulary, or just fix the literal English-word typo and leave the
rest). They picked rewording — the translation should become unnecessary
because the dialogue only ever says things the learner has already been
taught, not because new vocabulary got backfilled in to justify it.

**The audit.** Collected every word form that appears in any item's
`target` across `curricula/is-en/` (950 distinct forms) and checked every
dialogue's `opener`/`partner` lines against that set. 27 of 31 dialogues
used at least one word that appears nowhere else in the curriculum — 71
distinct word types in total. Concretely: the country name "Ísland" isn't
taught in *any* case (yet three dialogues used inflected forms of it);
"bjóða" (offer), "hittast" (meet), "kostur" (option) and dozens more never
appear in any vocab/phrase item; and `peysubud`'s "Já, hérna er large."
had a literal English word sitting in Icelandic dialogue text — an actual
typo, not a vocabulary gap. Also caught, while cross-checking: `veitinga
stadur`'s dialogue spelled the menu "matseðillinn" (double *l*) where the
taught vocab item is "matseðilinn" (single *l*) — same fix, since matching
the taught spelling exactly is the whole point here.

**The rewrite, line by line.** For each flagged line, found a replacement
built only from word forms already attested in some item's `target` —
not just the same lemma in a different case, the *exact* surface form,
since a different case ending is just as untaught as a different word.
Concretely this meant things like:
- Reusing whole existing item phrasings verbatim where the fit was exact:
  "Allt fínt, takk." → "Allt gott, takk." (the existing `allt_gott` item);
  "Fínt. Góða nótt!" → "Gott. Góða nótt!"; "Góðan bata!" (get well soon,
  untaught) → "Bless bless!" (an existing alternative farewell).
- Finding an existing construction that already takes the word in the
  case a new sentence needed: `ahugamal`'s "Ég elska kvikmyndir" problem
  (accusative "kvikmyndir" untaught) became "Ég hef gaman af kvikmyndum."
  — reusing the *dative* form the curriculum already teaches, inside the
  exact construction (`eg_hef_gaman_af`, "gaman af" + dative) that takes
  it. Similarly `kvoldmatur`'s "kjötsúpa" (nominative, untaught) became
  "ég er með kjötsúpu" — "vera með" + accusative, and only the accusative
  "kjötsúpu" is taught.
- Where no known form could carry the sentence without inventing
  grammar (2nd-person "þarft"/"vaknar"/"eruð", imperatives like
  "hvíldu"/"drekktu", technical loanwords like "gígabætum"), simplifying
  the line rather than guessing at a conjugation: `gonguferd`'s "you need
  a better jacket" became "it's cold" (still motivates the learner's next
  line, "I need a parka"); `laeknir`'s flu-and-rest medical advice
  dropped to "I see."; `simabud` lost the brand-name "frelsiskort" and
  the gigabyte spec entirely.
- One exception, deliberately: `myndir`'s partner is named "Sóley," which
  isn't in any item's target and was left as is. A person's name isn't
  vocabulary that needs teaching — it's a label, understood without
  translation the way "Anna" or "Yuki" already are throughout this
  course.

Every replacement was checked against the known-word set before being
written, not guessed and hoped for — same discipline as session 6's
"halló" lesson, just applied to grammar coverage instead of pronunciation
this time.

**Result:** 26 of 27 previously-flagged dialogues are now fully within
taught vocabulary (the 27th's only remaining flag is "Sóley," the
exempted name). Full details are in the diff across `curricula/is-en/
{01-greetings,02-clarifying,03-cafe,05-self,06-time,07-weather,08-numbers-
money,09-shopping,10-transport,11-accommodation,12-health,13-family,14-
daily,15-likes,17-food,19-questions,21-work,22-practical,23-nature,24-
discourse,25-travel,26-feelings}.toml` — 18 module files, one commit.

Added `test_dialogue_lines_stay_within_taught_vocabulary` in
`tests/test_audiolesson.py::CurriculumTests`, right after the existing
full-course simulation test: every dialogue's opener/partner words must
appear in some item's target, with "sóley" as the one named exception. A
future dialogue edit that reintroduces an untaught word will fail this
test immediately, rather than surfacing as a listener complaint again.

**Left open:**
- Issue #22's other ask — telling the learner a dialogue is starting,
  before a different voice speaks — is still undecided (see "Known gaps"
  below, unchanged from session 12).
- The sample French curriculum (`curricula/fr-en-a1.toml`, 4 dialogues)
  has the same pattern (all 4 dialogues use words outside its own vocab
  list) — not audited or fixed this session, since the reported issue and
  every other one this batch concerned the Icelandic course specifically.
  The regression test above only covers `curricula/is-en`.

## Session 12: issues #20, #21, and the easy half of #22

Four new issues came in together (#20–#23, oldest first as usual). Did the
three straightforward ones; #22 also raised two open design questions
(and #23 is a new feature, not a fix) — see "Known gaps" below rather than
this session's write-up, since nothing was decided about them yet.

### Issue #20 — "In Icelandic: Halló." isn't clearly an instruction

The `meaning` prompt has three variants for the "meaning" recall stage;
two are explicit ("How do you say: {meaning}", "Say: {meaning}") and the
third, "In {language}: {meaning}", reads as a label/statement, not a
request to speak — reasonable to mistake for the instructor just telling
you a fact rather than asking you to produce it. Reworded to `"Say:
{meaning} in {language}."` (en) / `"{language}で「{meaning}」と言ってくださ
い。"` (ja) — still names the language for variety, now unambiguously an
instruction like its siblings. Test added: `PromptsTests::
test_meaning_prompt_is_always_an_explicit_request_to_speak`, checking
every variant of the prompt in both languages for an explicit "say"/「言」
marker, so a future added variant can't reintroduce this.

### Issue #21 — a cultural aside, then a jarringly unrelated question

`Builder.note()` announces the start of an aside ("A quick aside.") but
never announced its end, so the very next (unrelated) exercise came right
after the story with nothing marking the return to the lesson. Added a
symmetric `aside_end` line ("Back to the lesson." / "では、レッスンに戻りましょ
う。") after the note text, with a `_beat()` before it. Didn't chase the
reporter's other suggested fix (make the note topically relevant to
*both* the exercise before and after it, or move all notes to the end of
the lesson) — the note is already chosen to relate to the exercise before
it, which is real signal; enforcing relevance to whatever comes next too
would need the scheduler to know the note's topic before picking the next
exercise, a much bigger change for the same problem an end-marker already
solves at low risk.

### Issue #22, the easy half — no beat between a dialogue line and its translation

Same shape of bug as issues #8 and #17's cousins: `Builder.dialogue()`
spoke a partner's line and then narrated its translation
(`dialogue_partner_said`) with no `_beat()` between them — two different
voices/languages running together. Added the beat at both call sites
(`turn.opener`/`turn.opener_meaning` and `turn.partner`/`turn.partner_meaning`).

The reporter also raised two things this session did **not** touch,
because they're design decisions, not bugs — see "Known gaps" below:
whether the translation should exist at all if dialogue vocabulary stayed
within what the lesson already covers or will cover soon, and whether the
learner should be told a dialogue is starting before a different voice
speaks.

Tests added in `tests/test_audiolesson.py::LessonStructureTests`:
`test_note_is_bookended_so_the_next_exercise_is_not_confused_for_part_of_it`
and `test_dialogue_partner_line_and_its_translation_have_a_beat_between`.

## Session 11: issue #17 — "Say bye. What do you say?"

> "It sometimes says '... say . what do you say?' which is obviously
> redundant."

The `situation` recall stage narrated `item.situation` (the curriculum
author's scene, e.g. "You're leaving the shop. Say bye.") and then
*always* followed it with a fixed `situation_ask` line, "What do you
say?" — telling the learner what to say and then asking them what to say,
back to back.

Checked whether this was only sometimes redundant (i.e. only for
situations that happen to end in their own "Say X" instruction) before
touching anything: grepped every `situation =` line in `curricula/is-en/`
and `curricula/*.toml`. Every single one already ends with its own
complete instruction — "Say X.", "Tell her Y.", "Ask Z.", "React: really?",
"Shout for help.", "Decline politely." — there is no situation in this
curriculum that is scene-only and actually needs a generic "what do you
say?" to know it's the learner's turn. So this isn't a per-item wording
problem to fix in content; the generic follow-up prompt was unconditionally
redundant, and every other recall stage (`meaning`, `hinted`, `cloze`)
already gets away with exactly one instructor line before the pause — the
`situation` stage was the only one doing two.

Fix: removed the `situation_ask` narration from both places that had it
(`Builder.recall()` and `Builder._recall_construction()` in
`exercises.py`), and deleted the now-unused `situation_ask` key from
`audiolesson/phrasing/en.toml` and `ja.toml`. No curriculum content
changed — `item.situation` is now the entire prompt, same shape as every
other stage. Updated `docs/CURRICULUM.md`'s `situation` field row to say
so explicitly, since it's now an authoring requirement (already true of
every existing situation) rather than a nice-to-have.

Test added: `test_situation_stage_does_not_ask_twice` in
`tests/test_audiolesson.py`, asserting the situation stage narrates
exactly one thing — `item.situation` itself, nothing appended.

## Session 10: issue #16 — pauses waited for perfect recall, not just recall

> "It waits too long after asking for saying the word." — "to wait long
> likely increases the chance to remember, however, it is not necessary to
> let the learner to remember words 100% correctly. probably 1 sec to
> remember and enough time to pronounce the word or the phrase is enough."

This is the gap "Known gaps / next steps" #2 (below) already flagged:
*"Numbers in Timing are reasoned defaults, not listened-to ones."* The
owner listened and confirmed it: too long.

The old `answer_pause` picked a base from a hand-tuned bucket table
(`word`/`short_phrase`/`sentence`/`long_sentence`: 2.5–8.5s by word count)
that had **no connection at all** to `speech_estimate()` — the method
right below it that already computes, from the actual per-language
speaking rate, how long the exact answer text takes to say. The bucket
values were sized to comfortably outlast that real speaking time by a wide
margin (e.g. a 1-word Icelandic answer takes ≈0.85s to say; the old bucket
gave it 2.5s *before* the ×1.2 A1 multiplier), which is exactly the
"waiting for confident recall" the issue says isn't the point.

Rewrote both pause methods around the issue's own formula — a moment to
recall (fixed) *plus* however long the answer actually takes to say
(computed from the real text via `speech_estimate`, not guessed from a
bucket):

- `answer_pause` = `think_time` (new field, default 1.0s — "1 sec to
  remember") × the existing level/familiarity/difficulty multipliers, +
  `speech_estimate(answer_text, lang)`. The multipliers still scale *only*
  the recall side — a beginner or an unfamiliar item needs more time to
  decide what to say, not more time to say it once decided.
- `repeat_pause` = `repeat_delay` (new field, 0.5s — no recall needed, just
  a reaction beat) + `speech_estimate(...)`. Previously `repeat_factor`
  (0.7) multiplied the same oversized bucket base, which happened to still
  clear real speaking time only because the base was already inflated;
  with pauses now grounded in the real estimate, multiplying it down would
  have cut a long answer off mid-sentence, so this is additive, not
  multiplicative.
- Removed the now-dead `word`/`short_phrase`/`sentence`/`long_sentence`/
  `repeat_factor` fields and the `_base_for`/`_units` helpers — net fewer
  moving parts, and one less place for the pause math and the speech-time
  math to silently disagree.

Sample pauses after the change (`Timing(level="A1")`): a 1-word Icelandic
answer ≈2.2s on first exposure, tightening to ≈1.9s once familiar; "Allt
gott, takk." ≈3.2s; a genuinely long sentence ≈5.8s; repeats track speaking
time closely (≈1.5s / ≈4.8s for the same two). Down from roughly 3–10s+
before, without ever landing below the time the phrase actually takes to
say.

One test needed updating, not because of a logic bug but because it was
tuned against the old (inflated) pause sizes: `LessonStructureTests`'
shared fixture forced `new_items=8` to get "a full first lesson" long
enough to test various invariants against; with shorter, more realistic
pauses, 8 new items for a from-scratch learner no longer summed to ~15
minutes on their own (nothing to review yet, so the planner's fill-to-
budget loop had nothing left to add). Raised it to `new_items=12`, which
lands the fixture back at ≈15.5 minutes — still "a full first lesson," just
under the corrected timing model. This is the same kind of expected
side-effect as session 8's `hallo`-position test fix: a test result moving
because the change it's guarding against is real and observable.

Marked the "Known gaps" item below as done.

## Session 9: issue #14 — "it starts with takk" is the answer, not a hint

> "It says 'it starts with takk' as a hint when asking for guessing 'takk'
> from 'thanks'" — "that is not a hint but an answer!"

Real bug, not a design question this time. The `hinted` stage
(`Builder.recall()` in `exercises.py`) always speaks `target.split()[0]` as
the hint — the item's first word. For a multi-word phrase that's a genuine
partial hint ("Allt" for "Allt gott, takk."); for a **one-word** item like
`takk` (`kind = "phrase"`, target `"Takk."`), the first word *is* the whole
target. The stage was unconditionally giving the answer away.

`audiolesson/stages.py`'s `ladder_for()` already had exactly this shape of
guard for `cloze` (`word_count < 3: continue`, since there's nothing left
to complete after removing the last word of a 1–2 word phrase) — added the
same kind of guard for `hinted`: `word_count < 2: continue`. `vocab`-kind
items were never affected (their ladder doesn't include `hinted` at all);
this only ever hit `phrase`/`construction`/`transform` items with exactly
one word, where `hinted` was reachable unconditionally. In the Icelandic
course, 25 single-word `phrase` items (e.g. `takk`, `bless`, `hae`, `ja`,
`nei`) had this stage silently spoiling the exercise.

No content or renderer change needed — this lives entirely in the ladder
that decides which stages an item climbs, which every recall path already
goes through (`Planner.ladder()` → `ladder_for()`), so fixing it in one
place fixes every code path that reaches "hinted" for a one-word item.

Test added: `test_hinted_stage_skipped_for_one_word_items` in
`tests/test_audiolesson.py`, next to the existing `cloze`/word-count test
it mirrors.

## Session 8: issue #12 — the first lessons were only single-word greetings

> "in the first few lessons, it needs more full sentences in target
> language. just listing greetings is simply a game of memorizing. it is
> not only difficult but also boring."

Checked this empirically before touching anything: lesson 1 introduces at
most 8 new items (pace 6 + the "short first lesson" +2 cap, `test_first_
lesson_at_default_pace_is_short_not_padded`), and `curricula/is-en/01-
greetings.toml`'s first 8 items — before this session — were `Góðan
daginn.`, `Gott kvöld.`, `Góða nótt.`, `Hæ.`, `Halló.`, `Bless.`, `Takk.`,
`Takk kærlega.`: one to two words each. The owner's complaint is a direct,
deterministic consequence of file order, since `Item.order` isn't an
authored field — `content.py` just assigns it by each item's position in
the TOML list (`curriculum_from_dict`'s `enumerate(raw.get("items", []))`).
The planner then walks new items in that order by default (topic
interleaving is opt-in via `--topics`), so "the first few lessons" really
does mean "however the module happened to be typed out."

Considered three approaches (asked the owner, who picked this one over
turning on topic-interleaving by default or writing new lesson-1-only
content): **reorder `01-greetings.toml` itself.** No code change — this
confirmed it's purely a content/ordering problem, not a planner bug — and
it reuses sentences that were already written and already exercised by the
test suite, so it doesn't add new Icelandic content to get wrong (see
issue #10's guideline, three sessions ago).

- Checked every item for `prereqs` before moving anything: all of module
  1 is prereq-free except `allt_gott` (`prereqs = ["takk"]`) and
  `sjaumst_seinna` (`prereqs = ["sjaumst"]`) — both easy to satisfy by
  keeping their prereq a few slots earlier in the new order, which the
  planner needs anyway (it silently skips an item whose prereqs aren't
  learned yet and moves on, so getting this slightly wrong wouldn't have
  broken anything, just deferred an item further than intended).
- New order for the first 10 items: `Góðan daginn.` → `Takk.` → `Hvað
  segirðu gott?` (How are you?) → `En þú?` (And you?) → `Hæ.` → `Halló.` →
  `Allt gott, takk.` (All good, thanks.) → `Hvernig hefurðu það?` (How are
  you doing?) → `Ég hef það gott.` (I'm doing well.) → `Gaman að sjá þig.`
  (Nice to see you.). Four of the first eight are now full sentences
  instead of zero, and lesson 2 (items 8–15ish) is *mostly* full sentences.
  The rest of the module keeps its original relative order — this is a
  targeted interleave, not a full reshuffle, to keep the diff reviewable
  and the remaining sequencing decisions (already presumably considered)
  untouched.
- The rest of the curriculum is unaffected: `order` for every item in
  module 2 onward is still just "how many items came before it," and
  module 1 still has exactly 38 items, so nothing downstream shifts except
  which id sits at which of module 1's own 38 slots.
- One test needed a matching content change of its own to catch a
  regression, not a code fix: `test_pronunciation_notes_reach_the_
  transcript` builds a 30-minute lesson 1 and expects `hallo`'s note in
  the transcript. An earlier draft of this reorder put `Halló.` at
  position 9, one slot past the 8-item introduction cap for that test's
  exact config — moved it to position 5 instead. That failure is a useful
  sanity check in itself: it confirms the reorder is real and observable,
  not just index bookkeeping.

Added `test_early_icelandic_lessons_mix_full_sentences_with_greetings` in
`tests/test_audiolesson.py::CurriculumTests` so a future edit can't quietly
slide this module back to all-single-word without a test catching it.

`audiolesson validate curricula/is-en` and the full suite (63 tests) both
still pass — same 993 items, same ids, same dialogue requirements, just a
different order for 38 of them.

## Session 7: working through the open GitHub issues, oldest first

The owner filed four issues (#7–#10, all with self-explanatory titles and no
body) and asked for them to be resolved one at a time, in order.

### Issue #7 — "/" is read aloud as "slash" instead of "or"

Curriculum authors write `"A / B"` (and, in the Japanese glosses, the
fullwidth twin `"A／B"`) to show two acceptable phrasings at a glance — e.g.
`meaning = "Excuse me. / Sorry."` or `meaning_ja = "もしもし。／ハロー。"`. Read
aloud literally by the TTS voice, that character is pronounced as its own
name ("slash"), which is not what it's there to mean.

Grepped every `curricula/is-en/*.toml` for `/` and `／` first, to make sure
the fix could be scoped safely: the character only ever shows up in narrated
known-language fields (`meaning`, `meaning_ja`, and their kin) as this
alternative-phrasing convention, or inside `#`-comments. No `target =` field
(the actual Icelandic speech text) contains one, so there is no risk of the
fix reaching into target-language audio.

Fixed at the same render layer as session 6's `RESPELL_FOR_SPEECH` — the
right layer for anything that should change what the TTS hears but not what
the transcript/cues.json/curriculum record: `audiolesson/render/renderer.py`
now also has `NARRATION_SLASH_AS_SPOKEN`, a small per-language regex table
(`"en": "/" → " or "`, `"ja": "／" → "または"`), applied in `request_for()`
right after `_respell()`. English uses a whitespace-flexible regex so both
`"A / B"` (spaced) and `"yes/no"` (bare) come out right; the Japanese fullwidth
slash needs no such flexibility since it's never surrounded by ASCII spaces
in this curriculum.

Deliberately not a curriculum-content change: rewriting every `meaning`
field to spell out "or" would touch dozens of lines across many files for a
purely cosmetic fix, and the written "/" is genuinely useful there (a reader
scans it faster than a written-out "or"). The render layer is the one place
that already exists specifically to make audio and record diverge on
purpose (see session 6) — reusing it here is the smaller change.

Tests added in `tests/test_audiolesson.py::RenderTests`:
`test_narration_slash_is_spoken_as_a_word_not_read_as_slash` (unit-tests the
regex table directly, English and Japanese, plus the guard that it doesn't
touch `is`) and `test_narration_slash_reaches_the_tts_but_the_record_keeps_the_slash`
(end-to-end: renders a script, spies on what the stub provider actually
receives, confirms the transcript and cues.json still show the "/").

### Issue #8 — no breathing room between the meaning and the new word

On a brand-new item's first exposure, `Builder.intro()` narrated the
known-language meaning (e.g. "Something new. Hello.") and then spoke the
target-language word immediately after, with no pause segment between them
— unlike every other join point in that same method, which already has a
`_beat()`. The two clips ran together as one, making it hard to tell where
the known language ends and the target language starts on the one exposure
where that boundary matters most.

Fix: one `self._beat(sc, ex)` call each in `Builder.intro()` (before the
first `item.target` speak) and `Builder._intro_construction()` (same spot,
for a new sentence pattern). `_beat` is already the same 0.8s gap used
between every other segment pair in this file (`timing.py`'s `beat`), so
this isn't a new timing concept — just one missing insertion of an existing
one, at the one place a first-time listener needs it most.

Left `_intro_transform()` untouched: its first narration is generic
instructions ("Here's how this works"), not the item's meaning, so it isn't
the same "known-language words butting up against target-language words"
case the issue describes.

Test added in `tests/test_audiolesson.py::LessonStructureTests`:
`test_intro_pauses_between_meaning_and_target_word`, which drives `Builder`
directly (bypassing the planner) on the sample curriculum's first plain
item and asserts a `pause` segment sits on both sides of the narrate/speak
boundary.

### Issue #9 — long words are hard to hold in memory; break them down

The existing "hard phrase" build-up (`Item.is_hard()` /
`Item.backward_chunks()`, used by `Builder.intro()`) already grows a
multi-word phrase backward from the end, one word at a time. It never
applied to a single long word, though, because `word_count` is 1 regardless
of how many syllables that one word has — so something like Icelandic
"flugvöllurinn" (airport, the) or "hjúkrunarfræðingur" (nurse) got no
build-up at all, which is exactly the case the issue describes.

Considered hand-authoring `chunks =` overrides on the specific long words
already flagged as hard elsewhere in this repo's own notes — that's the
existing, already-correct escape hatch, and costs zero new code — but it
only fixes the handful of words someone remembers to tag, and the
Icelandic course alone has ~370 single-word vocabulary items (of which
about 108 are long enough to want this). Went with a general fix instead:

- `audiolesson/content.py` adds `_syllable_pieces()`: split a word at the
  boundary before each vowel-run's onset, leaving one consonant with the
  following syllable when more than one precedes it. **This is a mechanical,
  vowel-anchored heuristic, not a phonological syllabifier** — say so
  explicitly in the code comment, because after session 6's mis-cited "halló"
  claim, this file is not going to assert linguistic authority it doesn't
  have again. Icelandic in particular allows onset clusters the heuristic
  doesn't know about (`verkfræðingur` splits as `verkf-ræð-in-gur` here, where
  a real syllabification keeps `fr` together: `verk-fræð-ing-ur`). What it
  reliably does is land next to a vowel, so every piece is still something a
  learner can say as one unit and the pieces still concatenate back to the
  exact word — good enough for "build it up gradually," not offered as a
  pronunciation authority.
- `Item.is_hard()` now also returns `True` for a single word with 3+ vowel
  runs (an approximate syllable count) — the same threshold used to size the
  build-up, not a separate guess.
- `Item.backward_chunks()` routes a single word through `_syllable_pieces()`
  and joins the growing tail with no separator (`""` instead of `" "`),
  since there's no space to rejoin on within one word; multi-word phrases
  are unaffected.

Checked the blast radius before committing to this being "general, not
sprawling": across the Icelandic course's 993 items, 108 single-word items
(~11%) newly qualify for build-up; the French sample curriculum flags one
(`Enchanté.`, genuinely three syllables). Full test suite (`test_full_course_
over_the_icelandic_set` et al.) still passes, so the extra build-up doesn't
blow the lesson-length budget.

Test added in `tests/test_audiolesson.py::CurriculumTests`:
`test_long_single_word_is_hard_and_builds_backward_by_syllable` — a short
two-syllable word stays "easy," a long compound is flagged hard and its
chunks are genuine, space-free tails of the word that reassemble into it.

### Issue #10 — watch for homographs like "bolli"/"galli" the way "halló" needed

Neither "bolli" nor "galli" is in any curriculum yet, so there is no live
bug here — this issue is the owner asking, in the direct aftermath of the
"halló" citation mistake earlier in this session (see the "Correction"
under session 6), for future curriculum work to actually watch for that
failure mode instead of repeating it. That's a process gap, not a code one,
so the fix is a documented guideline rather than a change to any word.

Added to `docs/CURRICULUM.md`'s "Guidelines that make lessons good": before
writing `pronunciation_notes` or a `RESPELL_FOR_SPEECH` override, read the
whole dictionary entry for the specific word being taught, not just the
first result that confirms an existing hypothesis — a spelling can be a
homograph with an unrelated etymology and a different pronunciation, and
citing the general rule for a language isn't the same as citing the
specific word. Named "bolli" and "galli" explicitly, since the owner raised
them, as words worth that check if/when they're added.

Also fixed two lines in `docs/CURRICULUM.md`'s field table left stale by
session 7's own issue #9 fix: `difficulty`'s row didn't mention that a
single long word now also triggers backward build, and `chunks`'s row said
it only applied to `phrase`-kind items when `vocab` items use it too (the
Icelandic vocabulary words this session added syllable chunking for are all
`kind = "vocab"`).

No test to add — this is documentation only. Ran the full suite anyway to
confirm the doc-only change didn't touch anything.

This closes out issues #7–#10, in the order they were filed.

## Session 6: owner overrode session 5's "leave it, it's correct" call

Session 5 (below) judged the `[hatlo]`-ish sound *very likely* correct
Icelandic and recommended explaining it rather than changing it. The owner
heard the reasoning and asked anyway for `halló` specifically not to have
that sound — a legitimate product call once the tradeoff is on the table,
and theirs to make. Implemented as a **narrowly scoped respelling at the
render layer**, not a reversal of the linguistic explanation:

- `audiolesson/render/renderer.py`: `RESPELL_FOR_SPEECH = {"is": [("Halló",
  "Haló")]}`, applied inside `request_for()` — the one place that decides
  what string actually reaches `provider.synthesize()`. Single 'l' sidesteps
  Icelandic's gemination rule entirely (re-checked with `espeak-ng -v is -x`:
  `Halló` → pre-aspirated `h'alloU`→`…tl#`-shaped when geminated elsewhere,
  `Haló` → plain long-vowel `h'a:loU`, no click), rather than trying to hand
  the TTS an IPA/phoneme override.
- Deliberately **not** threaded through `Item`/`Segment`/the planner. A
  string substitution at the exact point where text becomes TTS input covers
  every code path that ever speaks "Halló" (intro, the single-word hinted-
  stage hint, any future dialogue or review reuse) with about 20 lines,
  because it doesn't care which stage produced the string — confirmed with a
  real `generate --provider espeak` run: espeak received both `"Haló."` (the
  intro line) and `"Haló"` (the hinted-stage hint, `target.split()[0]`)
  without either being special-cased. Threading an `Item.speak_as` field
  through every call site in `exercises.py` would have cost far more for the
  same result — the "hundreds of net new lines means the design is probably
  wrong" line in this file's own conventions applied here.
- `cues.json`/the transcript are unaffected on purpose: `request_for()`'s
  return value feeds only `_cached()`/`provider.synthesize()`; the
  `cues.append(...)` line still reads `seg.text` directly. Answer matching,
  spaced repetition and everything else still key off the correct native
  spelling; only the audio changed.
- Follow-on content fix, necessary for consistency: the `hallo` item's
  `pronunciation_notes` and the `tvo_l` aside used to say "listen for the
  click on *halló*" — no longer true once the audio for that one word
  stopped making the click. Reworded `pronunciation_notes` to say this
  course reads it close to "hello" on purpose, and moved `tvo_l`'s examples
  to `fjall`/`eldfjall`/`jokull` (still genuinely pre-aspirated, unmodified).
  Same failure mode to watch for with any future per-word override: the
  written material has to keep matching what the audio actually does.
- Extending this to another word/language: add an entry to
  `RESPELL_FOR_SPEECH` keyed by the *target* language code (never a known/
  instructor language — `request_for`'s `lang` already tells them apart, so
  a collision with an unrelated known-language string, e.g. English "Shall"
  containing "hall", can't happen); pick a respelling by checking
  `espeak-ng -v <lang> -x` before and after, the way this one was chosen,
  since guessing at orthography-to-phonology rules for a language you don't
  speak is exactly the kind of thing worth a cheap empirical check first.

### Correction: the earlier citation was for the wrong word, and it flipped the answer

The owner asked for a citation on halló specifically. `WebSearch` (still
could not fetch the raw Wiktionary page myself — egress-blocked, same as
`en.wikipedia.org`, `wikiwand.com`, a jina.ai text-proxy) returned an IPA
string, **/ˈha.tl̥ou̯/**, which I reported as confirming the clicked
pronunciation for the greeting. **That was wrong, and it was wrong in the
specific way the owner called out: I read a result that matched what I
already believed and did not check whether it was even about the same
word.** Wiktionary's "halló" page (owner pasted the actual entry) has two
unrelated etymologies under one spelling:

```
Etymology 1 — Interjection, borrowed from Danish "hallo" (in use since the 1600s)
  IPA(key): [ˈhal(ː)ou]        ← the greeting; the "(ː)" is an optional plain-l length, no t
  "hello, good day; ... hello, a greeting used when answering the telephone"

Etymology 2 — Adjective, clipping of "hallærislegur" + "-ó" (slang: cheesy, uncool)
  IPA(key): [ˈhatlou]          ← the click is here, on an unrelated word
```

The click belongs to the slang adjective (which inherits it honestly from
the native compound *hallæri* it's clipped from); the greeting — a direct
Danish loan, the word this curriculum item and every prior session's
argument was actually about — is documented as a **plain `l`, no
pre-aspiration**. This matches both the casual pronunciation pages ("sounds
like hello") and espeak-ng's own output, which two sessions in a row I'd
been treating as the anomaly to explain away rather than the correct
signal. It does not match my session-5 prediction from the general native
`ll` rule, because that rule is about inherited vocabulary; a Danish loan
interjection has no reason to follow it, and per the dictionary, doesn't.

**Consequence for the code:** `RESPELL_FOR_SPEECH`'s `("Halló", "Haló")`
entry stays, but its justification changes. It was written as "the owner's
preference against a likely-correct native pronunciation." It is now
better understood as "correcting edge-tts toward the greeting's actual
documented pronunciation" — the original bug report was very likely right
on the merits, not merely accommodated. Reworded the code comment and
`hallo`'s `pronunciation_notes` (it used to say some Icelandic speakers
click on *this word*; they don't — that click is on the unrelated slang
adjective) to stop asserting the opposite of what the dictionary says.
`tvo_l`'s examples (fjall/eldfjall/jökull, genuine native `ll` words) were
already correct and untouched.

**For the next session, human or AI: this is a two-strikes pattern, not a
one-off.** Two sessions in a row, evidence that contradicted a
confidently-held phonological prediction (espeak's plain-l output, then
casual pronunciation guides) got explained away as "probably a gap in the
weaker source" instead of updating the prediction. Read a cited source in
full before extracting the one fact that confirms what you already expect
to find, especially under a homograph-prone spelling — the failure mode
here was not "no citation," it was "picked the citation that agreed with
me out of one that, read whole, didn't."

## Session 5: "halló" sounds like [hatlo] on edge-tts — is that wrong?

**Superseded — kept for the record, not as current guidance.** Session 6's
"Correction" section (above) found the greeting sense of "halló" has no
pre-aspiration at all (it's a Danish loan, IPA `[ˈhal(ː)ou]`); the
"very likely correct Icelandic" conclusion below turned out to be wrong,
built on the general native `ll` rule applied to a word that, per its own
dictionary entry, doesn't follow it. Read this section for how a plausible-
looking chain of reasoning went wrong, not for the answer.

The owner reported edge-tts's `is-IS-*` voices rendering "halló" with what
sounded like a "t" in the middle. **Could not verify by ear in this sandbox**
(the proxy still 403s the edge-tts websocket, same as every earlier session)
— this is reasoned from Icelandic phonology and a cross-check, not confirmed
by listening. Judgement call, not certainty:

- Icelandic geminate `ll`/`nn` after a short stressed vowel is regularly
  **pre-aspirated**: a brief voiceless click before the `l`/`n`. This is one
  of the most-cited "gotchas" for learners precisely because spellings like
  "halló" look identical to a word the learner already knows. It applies to
  native words (fjall, gull, kalla) and, as far as I can tell, to this
  fully-nativized loan interjection too.
- Cross-checked with `espeak-ng -v is -x`: it renders `allt`, `fjall`, `gull`
  as `…tl#` (the same "t + l" shape the owner heard), which matches the rule
  — but it renders `halló` itself as plain `h'alloU`, *not* pre-aspirated.
  That's the one data point against my read; I judged it more likely an
  espeak-ng Icelandic-module gap (it is one of the thinner language modules)
  than evidence that this specific word is an exception, but I could be
  wrong, and said so rather than picking a side silently.
- Consequence: **did not** try to force a different pronunciation. edge-tts's
  public `Communicate(text=…)` API XML-escapes the input before building
  SSML anyway (checked `edge_tts.communicate` source), so an SSML
  `<phoneme>` hint isn't reachable through it without depending on
  undocumented internals — and even if it were, overriding a *correct*
  native pronunciation to match a learner's mistaken expectation would be
  the wrong fix for a course whose whole point is training the ear.
- What was actually fixed: `pronunciation_notes` was a documented-but-dead
  field — `docs/CURRICULUM.md` said "for the transcript" but no code ever
  rendered it (checked: zero references outside `content.py`'s own
  definition). `Script.transcript()` now takes an optional
  `{item_id: note}` dict (kept as a plain dict, not a `Curriculum`
  reference, so `script.py` stays independent of `content.py`) and prints
  each note once, under the first exercise that touches that item;
  `cmd_generate` passes it. Added the note itself to `hallo`, and a spoken
  `[[notes]]` aside (`tvo_l`, English+Japanese) tied to `hallo`/`fjall`/
  `eldfjall`/`jokull` explaining the rule in plain terms, framed as "not a
  bug" — that note is probabilistic like every other aside (may not fire in
  a given lesson), so the transcript note is the reliable copy.
- If a native speaker ever confirms "halló" is *not* pre-aspirated in
  practice: delete the `pronunciation_notes` line on `hallo` and the `tvo_l`
  note's mention of it (keep the note for fjall/gull/allt, which are not in
  question), and consider whether the espeak-ng data point was right after
  all.

## Status: working end to end

`audiolesson generate` plans a lesson from a curriculum + learner state,
writes a timed script/plan/transcript, renders audio through a pluggable TTS
layer, and updates the learner model. 58 unit tests pass
(`python -m unittest`). A 10-lesson simulated course on the sample French
curriculum behaves as intended (new items reactivated at expanding gaps,
reviews interleaved, dialogues and recombination appear once material is
known, lesson ends on today's items).

Verified in this session:
- `stub` and `espeak` providers, WAV + MP3 output (ffmpeg), exact pauses.
- `edge` provider code is complete but **untested**: the sandbox proxy
  refused the websocket (HTTP 403). Test it first thing on a normal network:
  `pip install edge-tts && audiolesson generate ... -p profiles/edge-fr-en.toml -m 3`.
- `openai` and `say` providers are straightforward but also untested here.

## Session 4 additions: --user/--root wrapper

- `generate/report/status --user NAME` (`-u`; `--root`, default `out/` or
  `$AUDIOLESSON_ROOT`): resolves `--learner`/`--out` to `<root>/NAME/` and,
  for `generate`, reads/writes `<root>/NAME/settings.json` for whichever of
  `--curriculum`/`--known`/`--profile`/`--provider`/`--minutes`/`--level`
  were not passed this time — so after the first call, only `-u NAME` is
  needed. Implemented as pure request rewriting in `cli._apply_user`, called
  once at the top of `main()`; the command functions never see `--user`
  directly, only the resolved `--learner`/`--out`/etc., so this is a wrapper
  in the literal sense, not a parallel code path.
- Deliberately **not** duplicated in settings.json: feedback mode (auto vs.
  manual) and pace. Those already persist in `learner.json`
  (`LearnerState.feedback_mode`/`.pace`, since session 2); an earlier draft
  shadowed them in settings.json too and that redundancy was removed rather
  than kept "for symmetry" — one place to track a fact beats two.
- `--user` together with `--learner` or `--out` is a refused conflict, not a
  silent override — the two ways of pointing at a learner should not both be
  live at once. `--user` also rejects path-like names (`a/b`, `..`) since it
  becomes a directory component verbatim.
- `tools/daily.sh` grew an `AUDIOLESSON_USER` env var that delegates to
  `-u`/`--root` (named that, not `USER`, to avoid the shell's own login-name
  variable); the original `CURRICULUM=…/LEARNER=…/OUT=…` interface is
  untouched when it is unset.
- Not done: `fr-ja-a1.toml` still needs `-l`/`-c` spelled out explicitly
  every time even with `--user`, same as any other curriculum — no gap
  there, just noting the wrapper is curriculum-agnostic and was exercised
  mainly against `fr-en-a1.toml` and `curricula/is-en`.

## Session 3 additions (continued): Japanese instructor for the Icelandic course

- Design: per-language gloss fields side by side in the same curriculum
  (`meaning_ja` …), promoted at load time by `known_lang`; not a derived
  copy (as fr-ja was), so ids/structure never drift and the Japanese is
  written from the Icelandic, not from the English gloss. Missing glosses
  are an error at `generate` unless `--allow-fallback`.
- 1,999 Japanese strings written for `curricula/is-en` (all 993 items,
  31 dialogues, 45 asides rewritten natively for Japanese readers).
  Written by an AI: natural to a native reader in my judgement, but a
  Japanese speaker should skim the situations for tone, and the
  construction glosses with slots (`{inf}のがいいです` for *Ég vil …*,
  `泳ぎに行く頻度：{frequency}` for the frequency pattern) are the
  compromises worth a second look — Japanese cannot inflect a slot.
- `tools/gloss.py` inserts glosses from JSON keyed by id; the `_<lang>`
  suffix rule is "2–3 letters after an underscore on a glossable field".
- `fr-ja-a1.toml` still uses the older derived-copy approach; migrating it
  to side-by-side glosses would let `fr-en-a1.toml` be the single source.

## Session 3 additions (continued): cultural asides, fit tolerance

- `[[notes]]` in a curriculum (`content.Note`): instructor-only asides.
  Planner: after each exercise, 70% chance to play an unplayed note tied to
  that exercise's items; also used as filler before the second review pass;
  budget one per 12 minutes; `learner.notes_heard` keeps them rotating.
  45 notes for Icelandic in `curricula/is-en/90-notes.toml`, written for a
  Japanese learner (contrasts with Japan). Facts are from general knowledge;
  a quick check of dates and numbers by a local would not hurt.
- Renderer `fit_tolerance` (60 s default): within it, pauses are untouched;
  beyond it, scaled only to the nearer edge of the band.
- Trademark hygiene: no commercial course names in docs or CLI output.

## Session 3 additions (continued): Icelandic course, 993 items

- `curricula/is-en/` — 26 modules, 993 items, 31 dialogues, directory
  loading added to `content.load_curriculum` (one `[curriculum]`, items and
  dialogues concatenated; duplicate ids/targets rejected across files).
- **Needs a native read-through.** Highest-risk areas, in order: (1) case
  forms in vocab meant for slots — accusatives in 03/09/12/17, datives in
  04/05/15, `dat_town` in 05; (2) feminine predicate forms in 26 and the
  `Ég er …` phrases (masculine given in `pronunciation_notes`); (3) idioms in
  24 (discourse) and 07 (weather); (4) the transform examples in 20 (past
  tense, plural). Grammar patterns chosen are conservative: `Ég ætla að fá`
  + acc, `Hvar er` + nom, `Hvernig kemst ég að` + dat, `Ég er með` + acc,
  `gaman af` + dat, `Ég vil` + bare infinitive, `Ég ætla að` + infinitive.
- Planner: at most one dialogue per 10 minutes (`max_dialogues`); pacing
  slows when >25% of due reviews did not fit the last lesson.
- 90-day auto-mode simulation over the full set: 30 ± 1 min from lesson 5,
  3 dialogues/lesson, 40–70 reviews/lesson, 641 of 993 items met by day 90.
- Not done: a Japanese-instructor twin (`is-ja`) — same recipe as
  `tools/derive_fr_ja.py`, but ~1200 strings to translate.

## Session 3 additions

- **Auto feedback mode** (`generate --auto`, persisted): unreported lessons
  count as "all good"; pace steps up once every 3 lessons (`AUTO_STEP_EVERY`)
  while the backlog is small; `report --failed` still slows it.
- **Fixed lesson length**: (1) `LearnerState.speech_calibration` — per-language
  measured/planned ratio, multiplicative update with weight 0.7, fed into
  `Timing.speech_ratio`; (2) planner second review pass
  (`PlanConfig.max_review_passes`) when material runs out; (3) renderer
  `fit`: one pause scale factor clamped to 0.85–1.25 to hit `target_seconds`.
  Verified with espeak: 30:00 exactly from lesson 5, pause scale ≈ 1.00 once
  calibrated. Lessons 1–4 are content-bound and short by design.
- The closing reserve is now `8 + 14 s × new items` instead of 12% of the
  budget, and short lessons (< 5 min) can still introduce an item.
- Planner-side estimates are only as good as the last calibration; switching
  provider or voices means one or two lessons of re-calibration (the fit
  factor absorbs most of it, so the file length is still right).

## Session 2 additions

- **Adaptive pace** (`LearnerState.suggest_pace`): new items per lesson move
  within 3–10 from the learner's `report` feedback and the due backlog; it
  never rises without feedback. Rules and rationale are in README "Daily
  routine and pacing". `report` with no ids means "all good" and defaults to
  the latest lesson.
- **Scheduler bug fixed**: intervals used to multiply on every touch, so a
  daily learner hit 100 000-day intervals in two weeks (found by simulating
  the routine, `tools/daily.sh` × 40 days). Now only a review at/after its
  due date grows the interval, capped at 180 days.
- **First lessons are short on purpose**: extra new items beyond the pace are
  limited to +2; the CLI prints a note. Review-only lessons (curriculum
  exhausted) also end early rather than drilling twice.
- **Icelandic starter curriculum** `curricula/is-en-a1.toml` (61 items):
  written by an AI with care for case forms after *fá* (accusative) and
  *Hvar er* (nominative), **not reviewed by a native speaker**. Have someone
  read it before relying on it, especially `súpu`/`samloku`, `án sykurs`,
  `Gætirðu talað hægar?`, `stoppistöðin`. edge-tts voices:
  is-IS-GudrunNeural / is-IS-GunnarNeural (`profiles/edge-is-en.toml`).
- **Content is now the bottleneck.** At pace 6 the 61 items last ~9 days. A
  three-month course needs ~450–500 items; the planner and pacing need no
  change for that, only more `[[items]]` and dialogues in the same style
  (see docs/CURRICULUM.md "Languages with cases").

## Decisions (and why)

- **Python 3.11+, zero required deps.** Curricula in TOML via stdlib
  `tomllib`; audio via `wave`; ffmpeg only for mp3/decoding non-WAV TTS.
- **Three-stage pipeline with a serialized script in the middle**
  (`script.json`) so voices/pauses/providers can change without re-planning.
- **Presumed success.** Audio can't hear the learner; every retrieval counts
  as a success, `report --failed` corrects afterwards. Simplest honest model.
- **Ladder per item kind** (`stages.py`) rather than one global ladder; stages
  an item can't support are skipped, not faked.
- **Slot fills are verbatim vocab `target`s.** No morphology engine. Tag
  discipline in the curriculum keeps generated sentences grammatical
  (that is why `les toilettes` became a phrase, not a `place` vocab).
- **Instructor phrasing in `prompts/<lang>.toml`**, not in code, so a
  Japanese-speaking learner gets a Japanese instructor by translating one
  file (ja provided).

## Known gaps / next steps, in priority order

1. **Design curriculum sequencing from learner capabilities outward — top
   priority, per the owner directly** (issue #29, session 15; supersedes
   and consolidates #23 "grammatical dimensions" and #25 "reusable
   vocabulary," both closed into this one issue — see `docs/CURRICULUM.md`'s
   "Guidelines that make lessons good" for the authoring rule this sets).
   Genesis: session 14 tried to fix "dialogues sometimes use untaught
   words" by gating dialogue eligibility on comprehension prerequisites.
   That broke down mechanically (the first dialogue in the course,
   `nagranni`, would need item #926 of 993 for one word in one line) —
   and the owner rejected the *category* of fix, not just that schema:
   a dialogue needing an untaught word is a curriculum-sequencing bug,
   not a dialogue bug, so the fix belongs in how material is ordered and
   chosen, not in a prerequisite gate bolted onto dialogues afterward.
   Issue #29 generalizes this beyond vocabulary to the whole curriculum:
   - Sequencing should weigh **frequency, communicative utility,
     generativity, dependency value (how much it unlocks), and
     cross-context reuse** together — not just "does this word occur a
     lot."
   - The curriculum should pick the **right teaching unit** for a
     high-value concept — a reusable verb (`fara`), a construction
     ("need/have to + infinitive"), a grammatical distinction, or a
     discourse pattern — rather than defaulting every useful surface word
     to its own standalone vocab item.
   - **Grammatical dimensions** (case, gender, number, tense, person,
     mood, modality, agreement) should be introduced *deliberately* once
     enough familiar examples exist to make a contrast visible — the
     issue's own worked example: `Góðan daginn` / `Góða nótt` / `Gott
     kvöld` are all already-known items whose differing adjective endings
     (`góðan`/`góða`/`gott`) are a systematic gender-agreement pattern
     nobody has ever pointed out as such. This is exactly the "goðan
     after goða" tip #23 originally asked for, reframed as "teach the
     dimension," not "patch each pair with a hint."
   - The `dialogue_sequencing_report()` diagnostic (issue #25, session 14,
     still in `audiolesson validate`) is *one input* to this, not the
     mechanism — token occurrence is a signal, not equivalent to concept
     mastery, and the report should stay advisory.
   This is a design-and-authoring project scoped to the whole 993-item,
   26-module curriculum, not a single fixable bug, so it's proceeding as
   a sequence of focused pilots rather than one PR. **Done (session
   15):** pilot 1 — the `fara`/"want to, going to" cluster — an
   already-built `tags = ["inf"]` vocab set plus 4 generative
   constructions — moved from module 14 to module 2;
   `dialogue_sequencing_report()` no longer flags `fara`/`viltu`. Pilot
   2 — named the `góðan`/`góða`/`gott` gender-agreement pattern with a
   new grammar note (`godur_gender` in `90-notes.toml`) after the third
   of the three already-early greeting phrases. On review (PR #32) the
   owner found a plain `Note` didn't actually guarantee that moment (it
   could surface as generic filler before all three phrases were known,
   or get skipped by the same random `note_chance` roll a cultural aside
   uses) and read as an optional aside rather than deliberate
   instruction; fixed by adding `Note.milestone` and a dedicated,
   deterministic `Planner._eligible_milestone()` path — see "Pilot 2"
   above for the mechanism and the review response subsection right
   after it. **Architectural finding from that review, not yet acted
   on:** there's a real gap between the curriculum's existing units
   (vocab, phrase, construction, transform, note) and "introduce a
   grammatical concept once the learner has enough examples to notice
   it" — `milestone` notes cover the "notice, name" half for this one
   case, but nothing yet generalizes it into a reusable content kind for
   future grammatical-dimension pilots. Pilot 3 — `frábært` (dialogue
   partner reaction word in 7 dialogues starting with module 2, untaught
   until module 18, and `dialogue_sequencing_report()`'s own top
   repeat-offender) — moved to module 1; the report's advisory pair
   count dropped 53 → 49. The "two other `fara`-shaped constructions in
   `06-time.toml`" thread from pilot 1 is closed: investigated, and
   they're a different grammatical pattern, already early — not a
   sequencing gap, no action needed (see pilot 1's writeup above for
   the follow-up note). **Not started:** the generative half of pilot 2
   (practising the gender-agreement pattern on a *new* noun — deferred
   for lack of a verified noun-declension reference, see "Pilot 2"
   above), the rest of `dialogue_sequencing_report()`'s current list
   (`og, líka, sjáðu, vegabréf, góð, ferð, bara, hundruð, krónur` — each
   a candidate pilot 3-style pass), and the broader curriculum-wide
   audit.
1a. **Improve lesson orchestration and learner experience** (issue #34,
   **closed session 18** — see the correction below the pilot list;
   session 16 — a sequel to #29: where #29 decides *what* gets taught
   and *when*, #34 is about how a lesson built from correctly-sequenced
   material still *feels*). Genesis: the owner reviewed a real
   generated Lesson 3 transcript and found 8 related problems,
   including a direct critique of the `godur_gender` milestone note
   pilots 2/3 just shipped (too many grammar terms delivered at once;
   shouldn't close with "Back to the lesson." — "this *is* the
   lesson"). See "Session 16" above for the full write-up. Broken into
   7 pilots, ordered by risk/design-judgment needed. **Done:**
   1. instructor-prompt template artifacts — the English `meaning`
      prompt's "in {language}" variant now puts the language name
      *before* `{meaning}` instead of after, so it can't collide with
      `meaning`'s own terminal punctuation; and `jaeja`'s redundant
      parenthetical was normalized out of `meaning` (not moved to
      `pronunciation_notes` — the owner corrected that part of the
      plan: it's semantic/pragmatic, and `jaeja` already has a
      dedicated note covering it).
   2. shortened `godur_gender`'s text and retired the "aside" closing
      framing for milestone notes. Text now directly identifies
      góðan/góða/gott as forms of the same adjective before naming
      gender as the current dimension, and demotes case/number to one
      trailing clause instead of listing "accusative"/"singular" up
      front too — dropped those two labels entirely, since #34 only
      asked the *current* dimension (gender) to be named, not every
      dimension the examples happen to also hold constant. (An earlier
      draft opened "aren't three separate words," which the owner
      caught as a subject/predicate mismatch — see "Pilot 2" above.)
      Added a `milestone_end` prompt ("Let's continue."
      / 「では、続けましょう。」) so a milestone note's closing line no
      longer says "Back to the lesson." — `Builder.note()` now picks
      `milestone_end` vs `aside_end` the same way it already picked
      `milestone_intro` vs `aside`. Target-language speech *inside* a
      note's narration was deferred here — see pilot 8 below, done in
      session 17 via `«...»` markup rather than a structured-segments
      schema change.
   3. a contrastive discrimination exercise right after a milestone
      note. Needed no new content: `godan_daginn`/`goda_nott`/
      `gott_kvold` already each have their own distinct `situation`, so
      `Planner._maybe_note()` now returns the milestone it played and
      `build()` immediately replays up to two of the other items'
      `situation` stages via a new `do_discriminate()` closure.
      **Known limitation, not a blocker today (owner, post-merge):**
      `do_discriminate()` guarantees two discrimination recalls only
      when a milestone has *at least three* items with a `situation`
      (excluding the trigger still leaves ≥2 candidates); a future
      2-item milestone would silently fall back to one recall, quietly
      breaking "notice → name → discriminate" rather than erroring.
      Both current milestones (`godur_gender`, `three_kinds_of_sorry`)
      have three, so nothing to fix now — but before adding a milestone
      note with fewer than three suitable items, either (a) enforce a
      "≥3 contrast items" invariant on milestone notes in
      `curriculum_from_dict`'s validation, or (b) give `Note` an
      explicit discrimination strategy/count instead of `do_discriminate()`
      silently assuming three. Whichever is picked should come with a
      test that actually constructs a 2-item milestone and checks the
      chosen behavior, not just the 3-item cases that exist today.
   4. explicitly contrast near-synonyms `Afsakið`/`Fyrirgefðu`/`Því
      miður`. Verified `því miður` against dict.cc/Glosbe first (general
      regret marker, not negative-specific) before fixing its
      opposite-polarity gloss and adding a second milestone note
      (`three_kinds_of_sorry`) reusing the same mechanism. Two
      milestones existing at once surfaced a real budget-accounting bug
      (fixed) — see "Pilot 4" above for both.
   5. situation-prompt variation for repeated retrieval. `Item` gained
      `situations: list[str]`, glossed like any other field
      (`situations_ja`); `Item.situation_for(exposures)` rotates
      round-robin using `ItemState.exposures`, already tracked, so no
      new persisted state. Falls back to the old singular `situation`
      when absent, so no existing item needed migration. Retrofitted
      `velkomin` (the issue's own repeated-cue example) with two more
      situations.
   7. linguistically-meaningful backward-build chunking. Took the
      cheaper of the plan's two options: removed the confirmed
      vowel-run-only `_syllable_pieces()` heuristic entirely rather than
      replacing it with a "verified" one, since even a linguistically
      correct split doesn't solve the issue's real concern (TTS
      mis-synthesizing an isolated fragment with no context it's part
      of a longer word). A hard single word with no author `chunks` now
      gets slow whole-word repetition instead of a fabricated split —
      zero curriculum edits needed, all 108 affected items (incl. the
      issue's own `afsakid`/`fyrirgefdu`) pick it up automatically.
   6. lesson shape, first of several small changes (done after pilot 7,
      at the owner's request — **highest blast radius**, so taken last):
      a `drill_streak` counter now pulls an eligible dialogue forward
      once too many isolated recalls have run in a row, instead of
      waiting for the periodic `dialogue_every` schedule. Recomputed
      from the actual trailing exercise sequence
      (`Planner._trailing_drill_streak`), not incremented per loop
      iteration — the first cut got this wrong for a milestone-note
      iteration (adds several exercises at once), fixed on review.
      **Not done, still open:** ending a lesson early rather than
      padding with low-value repeats, and mini-situations/listening-
      comprehension as alternatives to another isolated drill —
      separate design threads, deliberately not bundled into this same
      change.
   8. target-language speech inside a note's narration (#34 point 1,
      other half; session 17). `«...»` inside a note's `text`/`text_ja`
      now marks a phrase that `Builder.note()` hands to the
      target-language voice instead of narrating it as instructor-
      language text (see "Session 17" above). Applied to both existing
      milestone notes. Owner review on PR #41 caught a
      bare-punctuation-narration bug (fixed: a punctuation-only split
      fragment is now a beat, not a `_narr` call) and a count-only
      validation gap (fixed: validation now runs the matching regex
      instead of comparing counts). The other 46 cultural asides also
      named Icelandic words inline; marked those up too in pilot 11
      below — every note in the curriculum that names a real Icelandic
      word now speaks it natively.
   9. alternative-activity-or-stop fallback for a high `drill_streak`
      with no eligible dialogue (#34 point 6, other half; session 17).
      **Done.** `build()`'s step 0 (moved earlier on owner review — see
      below) pulls a note forward instead when the streak is high and no
      dialogue fits, instead of silently falling through to another
      isolated recall; the "or stop" half needed no new code since step
      5's existing cascade already ends the lesson once genuinely
      nothing is left. See "Pilot 9" above. Owner review on PR #41 found
      the first cut ran this check *after* step 1 (a due scheduled
      reactivation), so the reactivation could still win and continue
      the run — fixed by moving the whole check to run first, before any
      branch that emits another recall.
   10. ending a lesson early instead of padding with a second review
       pass (#34 point 5, other half; session 17). **Superseded by pilot
       12 (session 18) — see below.** The original framing ("should
       `max_review_passes` default to 1 or 2?") turned out to be the
       wrong question, per the owner's own reframing from a real
       generated lesson: the real problem wasn't the second pass
       specifically, it was that *every* fallback tier — new-item cap,
       pending reactivations, note budget, both review passes — could
       become exhausted at once with substantial budget still unused and
       no next step. `max_review_passes` itself was left at its default;
       pilot 12 addresses the actual problem instead.
   11. marked up the remaining 46 cultural-aside notes with `«...»`
       (pilot 8's remainder; session 17). **Done.** See "Pilot 11" above
       for the full note-by-note list and the two deliberate exclusions
       that stand (bare letters discussed as sounds, Japanese reference
       words). Owner review on PR #42 caught that the first cut also
       excluded `text_ja` fields carrying only a katakana
       transliteration, leaving the Japanese track without native-voice
       speech for 7 notes' Icelandic terms — fixed by keeping the
       katakana as a parenthetical gloss and adding the real spelling in
       `«...»` alongside it (e.g. `«Skyr»（スキール）`).
   12. the new-item cap should bound one learning arc, not the whole
       lesson (#34 point 5, reframed by the owner from a real Lesson 3
       output; session 18). **Done.** See "Session 18" above for the
       full investigation (a real lesson stopping ~11 minutes short of a
       30-minute request with 985 of 993 curriculum items untouched),
       the fix (a new step-5 fallback tier that starts a fresh arc once
       the current one is fully spent and substantial budget remains,
       ordered to prefer this over a low-value second review pass), the
       3 real bugs found and fixed while building it (an infinite loop,
       and regressions against the first-lesson-stays-short and
       prerequisite-order guarantees), and the real-world result on the
       owner's own scenario (1144.5s → 1689.1s of a 1800s target). Noted
       as a scoping choice, not a gap: this reuses the existing per-item
       machinery for "arc 2" rather than modeling arcs as a first-class
       concept with their own practice/dialogue/review sub-structure — a
       fuller redesign remains available as a separate thread if wanted.

   **Not started:** none — every pilot from the original 7 through
   pilot 12 has a concrete, done step.

   **Correction (session 18, owner review): "no open pilots" is not the
   same claim as "acceptance criteria met."** This entry previously
   closed with "#34 has no open pilots left," which is true of the
   pilot list but had quietly drifted from the issue's own acceptance
   criteria. Two of them are not actually satisfied: "the planner
   avoids long uninterrupted runs of isolated situation/answer
   exercises" (pilot 9's streak-triggered dialogue-or-note fallback does
   nothing, and execution falls through to ordinary recall, whenever
   *both* are unavailable — common once a lesson's note budget is spent
   and no dialogue has unlocked yet) and "connected dialogues or
   mini-situations are preferred when enough known material exists"
   (pilot 12's arcs get practice and review but no deliberate
   connected-use step of their own; a lesson can run several arcs with
   zero connected use if `eligible_dialogue()` never happens to unlock
   one on its own). Split both into **issue #44**, closed #34 rather
   than continuing to expand it, per the owner's explicit direction —
   see #44 for the two gaps' acceptance criteria. `docs/HANDOFF.md`'s
   own "Keep this current" promise applies to this kind of drift too:
   a pilot-list summary that silently stops tracking the issue's actual
   acceptance criteria is exactly the failure mode to watch for on
   future long-running issues.
2. **Test `edge` provider on a real network** (see above). If edge-tts's
   `rate="+N%"` sounds off for slow renditions, clamp `slow_rate` to ~0.8.
3. ~~Listen to a real lesson and tune timing~~ — partially done (session
   10): `answer_pause`/`repeat_pause` were rewritten around real
   per-language speech estimates instead of a hand-tuned bucket table, on
   the owner's direct feedback that pauses ran long. `between_exercises`
   and `beat` haven't been listened-to yet.
4. ~~`alternatives` never spoken~~ — done: at meaning+ stages, once per
   lesson per item, 50% chance: "You could also say:" + alternative.
5. **Lesson-1 intro bunching.** With nothing to review, the first lesson opens
   with 2–3 introductions in a row (nothing else exists yet). Acceptable but a
   short "listen to this conversation" opener, as some audio courses do,
   would be nicer.
6. ~~Dialogue partner translation always narrated~~ — done for the
   scaffolding-fade half (issue #26, session 14): translation and the
   explicit "say X" cue are now only there on the *first* encounter
   (`Builder.dialogue(..., assisted=...)`, driven by the same
   `dialogues_done` repetition count that already grows how many turns
   play). `--no-translate` still disables translation outright regardless
   of encounter count, for whoever wants that. Two asks from issue #22
   (session 12) are still open and undecided: (a) dialogue vocabulary
   should ideally need no translation at all because it stays within
   what the lesson covers — this is item #1 above now (issue #29,
   session 15; the #25 gating approach it grew out of was closed once
   the owner reframed it as a curriculum-sequencing problem, not a
   dialogue one); (b) the learner should be told a dialogue is starting
   (a different voice is about to speak) before the first partner line,
   not just given the scene-setting `dlg.setting` narration — nobody has
   picked this back up yet.
7. **Curricula.** `fr-en-a1.toml` and its Japanese-instructor twin
   `fr-ja-a1.toml` (generated by `tools/derive_fr_ja.py` from a translation
   table; a test asserts the ids stay in sync). The Japanese strings were
   written by an AI, not reviewed by a native speaker — read them once.
   Numbers/plurals are deliberately absent (no morphology). Other target
   languages need a new curriculum file; no code changes.
8. ~~Cross-lesson dialogue difficulty~~ — done: a dialogue plays
   `dialogue_first_turns` (2) turns on first encounter and one more turn each
   later time, replayed without pauses once it is complete.
9. ~~Parallel TTS~~ — done: providers flagged `parallel` (edge, openai) are
   warmed into the cache with `workers` threads (profile key, default 4).
   Untested against a real network, like the providers themselves.
10. **Wheel install** verified to include `audiolesson/phrasing/*.toml`.

(Issue #23's "minimal-pair tip" ask is folded into item #1 above — issue
#29 reframes it as "introduce the grammatical dimension deliberately,"
not a per-pair hint. #23 is closed; don't re-open a separate line item
for it.)

## Where things are

See README "Layout". The planner loop is `Planner.build` in
`audiolesson/planner.py` (branches 1–5 are commented). Exercise shapes are in
`audiolesson/exercises.py`. Pause math is `Timing.answer_pause`.

## How to check your change

```sh
python -m unittest -v
python - <<'EOF2'
# ten-lesson simulation: one line per lesson, letters = exercise kinds
# o opening, i intro, r recall, g generative, d dialogue, c closing
from datetime import date, timedelta
from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing
from audiolesson.planner import Planner, PlanConfig, apply_to_learner
cur = load_curriculum("curricula/fr-en-a1.toml"); ls = LearnerState("fr", "en"); d = date.today()
for _ in range(10):
    sc = Planner(cur, ls, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=15), today=d).build()
    apply_to_learner(sc, ls, d); s = sc.summary(); d += timedelta(days=2)
    print(f"L{sc.lesson_number}: {s['duration_s']/60:.1f}min active={s['active_ratio']} new={len(sc.meta['new_items'])} rev={len(sc.meta['reviewed_items'])} " + "".join(e.kind[0] for e in sc.exercises))
EOF2
```
