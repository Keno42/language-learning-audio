# Handoff note — audiolesson

_Last updated 2026-09-22 (session 33). Recent sessions, oldest first:
22 closes out issue #44; 23 is issue #29's triage and generative agreement
pilot; 24 is issue #49 (embedded third-language examples, pronunciation
pacing); 25 is issue #48's first partner line inside connect(); 26 is #29
cluster A (numbers/money); 27 is #29 cluster B's sequencing findings (PR
#54); 28 is issue #55 (connect() pair history); 29 is #29's
capability-aware arc boundaries; 30 is #48's partner exchanges in early
lessons (28–30 were PR #56, merged); 31 is issue #57 (situation-bound
construction fills, PR #58); 32 is #29's audit and grammatical-dimension
pilots (aspect, modality, case; PR #60, merged); 33 is #48's per-dialogue audit,
more bridges, bridge scenes and a partner-driven number transaction (PR #61);
34 is issue #59's cloze prompts (PR #62, merged). **Issue #34** ("Improve
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

**Issue #44** (the two residuals split out of #34) is **done** — four
review rounds on the same PR (#46), each one closing exactly what the
previous round left open. Session 19's first fix was judged
**request-changes equivalent**: each of its two points stopped one step
short of #44's acceptance criteria (note fallback could still rarely
fall through to plain recall; dialogue-stage fix only reached items
wired into an authored dialogue). Session 20 added a dialogue-independent
recombination fallback (`do_connect()`) and a real deliberate stop as the
cascade's last resort — the owner confirmed that shape was right, but
session 20's `connect()` itself was still just two independent flashcard
recalls under a shared header, was only ever reached as a side effect of
the drill-streak breaker (not guaranteed per arc), and could pull
material from the wrong arc. Session 21 rebuilt `connect()` as one
exercise with an explicit bridging line, added a real per-arc guarantee
independent of the streak breaker, and fixed the arc-scoping and an
`idx` off-by-one. Session 22 closed the last gap: `connect()` could
record a multi-word item at `"situation"` stage regardless of how far it
had actually climbed its own ladder, silently skipping stages it never
practised. See "Session 22" through "Session 19" below for the full
history (104 tests at the time).

**Open issues — current state** (keep this block true; details live in
the session sections):

- **#55** (connect() replayed one fallback pair all lesson) — fixed in
  session 28 (PR #56): per-lesson pair history, authored-bridge-first
  ranking, per-arc pairs must include the arc's own item, exhaustion
  stops instead of looping. PR #56, merged.
- **#57** (construction situation vs generated fill) — fixed in session
  31: `situation_fill` binds the fill a situation names; situation-stage
  recall and connect() honour it, other stages generate freely (follow-up
  PR after #56).
- **#48** (isolated recall → end-to-end conversation) — **partially
  addressed**. Session 25 added authored `partner_cue` bridges to
  connect(); session 30 made early lessons reach partner interaction
  through authored connect() exchanges (13 bridges in modules 01–02, not
  native-reviewed; connect() labelled `exchange` vs `recombine`;
  `partner_exchanges` in lesson meta) — with #27's durable dialogue gate
  deliberately left intact (a first cut loosened it; reverted on review).
  Session 33 (`docs/AUDIT-48.md`): every dialogue's target-language lane
  audited — six fixed (a case error, an unanswered question, a copied line,
  a role inversion, two garbled cues); 13 more bridges (26 total, modules
  01–03), so only L1 lacks a partner exchange at 20 minutes and none at 30;
  and `expect_fill` lets a dialogue turn generate from a construction —
  the new `solubas` stall dialogue has the learner produce «Það kostar
  fimm þúsund krónur.» from `thad_kostar_big` mid-haggle. Still open:
  bridges beyond module 03; hundreds/teen amounts in partner lines are
  still fixed text; five dialogues have no item-linked learner turns.
- **#29** (curriculum around reusable concepts and capabilities) — **in
  progress**. What "done" means below is deliberately split into
  *sequencing finding addressed* vs *capability modeled*; don't merge them.
  - (1) Triage of `dialogue_sequencing_report()` findings (posted on
    #29): clusters C and D and `verð að + infinitive` (session 23),
    cluster A numbers/money (session 26, with three corrections), cluster
    B remainder (session 27). The flagged *sequencing* gaps of those
    clusters are addressed; not every concept became a reusable
    capability — `X, held ég` (sentence-final hedge) and `vera að +
    infinitive` (progressive) are **unmodeled** representation gaps, and
    singular/plural agreement (`hundrað`/`ein`, session 26) is
    deliberately unmodeled. **11 advisory pairs remain** at the default
    threshold (`tungumal` gert/tölum/bara/fyrir, `leigubill` lengi, `tynd`
    hvert/bara, `flugvollur` farangur, `heimsokn` nákvæmlega, `dagurinn`
    vinnu, `vidtal` segðu) — not individually triaged beyond session 23
    judging `tungumal`'s gert/tölum/bara on-topic content; they belong to
    item (2).
  - Owner-added criteria: **transfer** — `godur_gender` discriminates on
    new nouns via `Note.transfer_items`, and `godur_noun` generates
    unauthored gender-agreed phrases (session 23); **capability-aware arc
    boundaries** — `select_new()` pulls a nearby construction in once two
    fillers exist, holds further fillers, caps them at two per arc
    afterwards, and keeps an arc boundary from falling between fillers
    and their construction (session 29). Implemented and simulated; not
    yet confirmed by the owner on a real generated lesson.
  - (2) Curriculum-wide audit — **first pass done** (session 32):
    `docs/AUDIT-29.md`, reproducible with `tools/phrase_families.py`, puts
    every fixed-phrase family of ≥3 into the owner's three dispositions
    (lexicalised / later-productive / shared dimension) with status and a
    suggested order. Acted on so far: `Má ég …` and `Ég er að …` (below).
    Most category-2 families (`Takk fyrir`, `Hvenær fer`, `… virkar ekki`,
    `Ég á`) are listed, not converted.
  - (3) Grammatical-dimension pilots generalizing `godur_gender` —
    **aspect and modality modeled, case named** (session 32): milestones
    `vera_ad_progressive` → `eg_er_ad_inf`, `modal_infinitive` →
    `ma_eg_inf` (both productive over the `inf` pool via the new
    `meaning_forms`/`{slot:form}` mechanism), and `dative_subject` (ég vs
    mér, contrast + transfer, no construction yet). Tense and person not
    started; `X, held ég` still unmodeled (no clause slot).
  - #29 stays open until the audit's remaining dispositions are acted on
    (or explicitly accepted as chunks), the case pilot becomes productive,
    tense/person are addressed, and the arc-boundary behavior is confirmed
    on real output. See `docs/AUDIT-29.md` "Suggested order"._
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

## Session 20: issue #44, round 2 — owner rejected PR #46 as "one step short" on both points

The owner reviewed PR #46 (session 19's fix, above) and called it
**request-changes equivalent**, not because either fix was wrong, but
because each stopped one step before #44's own acceptance criteria —
explicitly saying the good parts (the bounded relief-note allowance, the
fresh-item dialogue-stage bypass, both existing regression tests) should
be **kept, not discarded**, with one more finishing pass on top.

**Blocker 1 — the relief-note allowance still had a silent fallthrough.**
Session 19's own writeup admitted it: "once both [the ordinary ration and
the relief budget] are spent, an occasional longer run can still occur."
That is exactly the fallthrough #44 rules out, just rarer. The owner
specified the required cascade explicitly: dialogue → note → a genuine
connected mini-activity → and only if *that's* also impossible, a
deliberate stop, never one more isolated recall.

**Blocker 2 — the dialogue-stage fix only reaches items wired into some
dialogue's `requires`.** Session 19's own "scoping note" called this "a
content gap, not a planner gap" and punted it to #29's curriculum audit.
The owner rejected that reclassification: #44's acceptance criteria
explicitly ask for "dialogue **or recombination**," and its acceptance
test is specifically "an arc whose material never gets a connected-use
moment" — an authored-dialogue-shaped fix can never close that gap by
construction, however #29's audit turns out. This needed a mechanism
that doesn't depend on dialogue content existing at all.

**Also flagged:** PR #46's branch had drifted from `main` again
(`ahead_by: 2, behind_by: 1`, same pattern as #45) — rebased onto latest
`main` (`bb5d008`) before starting this round's work.

### Fix: a dialogue-independent recombination fallback, plus a real stop

Added `do_connect()` / `Builder.connect()` (new exercise kind
`"connect"`), modeled directly on the existing `do_discriminate()`
(session 16 pilot 2): frame two already-known items with a brief
connective narration, then recall each by its `situation` cue in
succession. Candidate selection prefers this lesson's own `introduced`
items first (falling back to any other known item with a situation cue),
so an arc gets its own material recombined rather than two unrelated
review items — and it needs no `Dialogue.required_items` wiring at all,
closing blocker 2 directly.

Step 0's streak-triggered cascade is now a real three-tier fallback
ending in a deliberate stop, not a two-tier `if/elif`:

```
dialogue → note (ration, then bounded relief) → do_connect() → break
```

Each tier only runs if the previous one didn't act (`if not acted:
...`); if all three fail — no eligible dialogue, no note budget left at
all, and fewer than two known items with a situation cue — the lesson
stops there rather than emitting one more isolated recall. This is rare
in practice (it needs all three to fail at once) but is now a real
branch, not a theoretical one addressed only in a docstring.

**Regression caught before it shipped:** the first cut of `do_connect()`
had the new `"connect"` frame exercise list its two item ids in the same
order they were about to be recalled, so the frame's own `item_ids[0]`
equalled the very next exercise's item — tripping
`test_no_item_twice_in_a_row` even though the learner never actually
repeated an item back to back. Fixed by listing the frame's item ids in
the reverse of recall order.

Added the two regression tests the owner specified verbatim, each
confirmed to reproduce the bug on the pre-fix code before passing on the
fix:
- `test_streak_with_no_dialogue_and_no_notes_does_not_fall_through_to_more_recall`
  — no dialogues, no notes, `note_chance=0`, plenty of known
  situation-capable items: pre-fix, the streak just kept emitting
  `"recall"` past the limit; post-fix, exercise 4 is `"connect"`.
- `test_connected_use_reaches_an_arc_whose_items_are_wired_into_no_dialogue`
  — a curriculum with **no dialogues at all**, a fresh two-item arc plus
  unrelated review material: pre-fix, no `"connect"` exercise ever fired;
  post-fix, one does, and it covers the arc's own items specifically
  (not just any known item), confirming the "prefer this lesson's own
  material" ordering, not only that *something* fired.

102 tests (100 → 102), all passing; `audiolesson validate` unchanged.

## Session 21: issue #44, round 3 — the connect() mechanism itself needed real content, not just structure

The owner reviewed session 20's push and confirmed the cascade shape and
per-item fixes were right (rebase clean, the three-tier fallback closed
point 1's silent fallthrough, the dialogue-independent path reached
material with no authored dialogue) but flagged four remaining problems,
all in `do_connect()`/`Builder.connect()` itself:

1. **`connect` wasn't actually connected use.** The exercise narrated a
   shared frame, then ran two ordinary `situation`-stage recalls back to
   back — structurally two independent flashcards under a header, no
   semantic link between them. The owner's own reproduction picked
   "leaving a shop" next to "raising a glass for a toast." The new
   regression test's `assertTrue(connect_exercises)` only checked the
   label existed, not that the *content* was connected — testing the
   fix's structure, not its substance.
2. **Connected use was a side effect of the streak breaker, not part of
   an arc's own lifecycle.** `do_connect()` was only ever reached from
   step 0 (drill-streak triggered), so an arc practiced at a normal pace
   — never running the streak past its limit — could finish, and the
   lesson could move on or end, with no connected-use attempt at all.
   #44's own criteria don't make this conditional on a streak.
3. **Candidate selection pulled from `introduced` as a whole, in intro
   order** — not the specific arc being served. With two arcs in one
   lesson, a later arc's "connected use" could end up reusing an earlier
   arc's items instead of its own.
4. **An off-by-one in `idx`.** `do_connect()` incremented `idx` once per
   sub-exercise it emitted (3 total) *and* the main loop's own trailing
   `idx += 1` still ran once more on top — 4 increments for 3 exercises,
   silently skewing when later reactivations came due and when the next
   intro was allowed.

### Fix 1: `connect()` became one exercise with a real bridge, not three

`Builder.connect()` now builds a single `Exercise`: intro frame →
item 1's situation cue → answer → an explicit connecting line
(`connect_then`, "And then —") → item 2's situation cue → answer. The
second retrieval reads as a continuation of the same moment, not a new
unrelated prompt — the same reason `dialogue()` keeps a whole exchange's
turns inside one `Exercise` instead of splitting them apart. `do_connect()`
also now prefers a same-topic pair over an arbitrary one (falling back to
any two eligible items only if no topic pair exists), so the two halves
of the exchange are at least topically related to begin with.

Being a single exercise also resolves fix 4 for free: `do_connect()` no
longer touches `idx`/`since_dialogue` itself at all, the same as every
other single-exercise branch (`do_recall`, `do_intro`, dialogue) — the
main loop's own trailing increment is the only one that ever fires.

### Fix 2 & 3: a real per-arc guarantee, scoped to that arc's own material

Added step 0b, run every iteration (not gated on the streak breaker):
once every item introduced in an arc has had at least one touch beyond
its own intro, that arc gets one deliberate `do_connect()` attempt —
scoped to `arc_items[that_arc]` specifically, falling back to other
material only if the arc alone can't supply two eligible items. Arc
membership is tracked via a new `arc_items: dict[int, list[Item]]` /
`arc_order` / `arc_target` (the arc's own intended item count, fixed at
creation — without it, the readiness check could fire the instant an
arc's *first* item got its first reactivation, before the arc had even
finished being introduced, confirmed empirically with `intro_gap=3`).
Marked "attempted" once tried regardless of outcome, so a genuinely thin
arc isn't retried forever.

**Two bugs found and fixed while building this, both via direct
reproduction:**
- The arc's own most-recently-touched item is typically the one whose
  reactivation just completed the arc's readiness check — excluding it
  from candidacy (the same exclusion `do_discriminate` uses) left only
  one real member for a 2-item arc and forced a fallback to unrelated
  material, exactly the cross-arc contamination fix 3 exists to prevent.
  Fixed by ordering it *second* in the pair instead of excluding it —
  keeps both real members available while still avoiding an *immediate*
  repeat.
- A bounded "don't reuse an item already spent in a connect() this
  lesson" guard (added for a different reason, see below) combined with
  the *general* (non-arc) streak-tier fallback retriggering every
  `drill_streak_limit` recalls for an entire pure-review lesson with no
  dialogues — together they ran the pool of eligible situation-capable
  items dry mid-lesson, tripping the "genuinely nothing left" deliberate
  stop far earlier than intended. Caught by `test_fit_lands_on_the_requested_length`
  and both `PacingTests` cases dropping lesson length 40-60% below
  target. The reuse guard was the wrong tool for that other problem (see
  below) and was reverted rather than papered over with a budget cap.

### A regression along the way: situation-cue rotation and connect() don't mix

`test_situations_rotate_across_repeated_retrieval_of_the_same_item`
(session 16 pilot, owner review on #39) started failing once `connect()`
began narrating real situation cues via the shared, rotating
`_situation()` — an item swept into a `connect()` exercise silently
consumed a rotation step invisible to any later plain recall of that same
item; with a 2-cue item, an *even* number of such hidden steps across a
lesson landed a later recall back on the exact cue an earlier recall had
already used. Tried excluding already-connected items from later
candidacy first — this is what caused the pool-exhaustion bug above, so
it was reverted. **Fix:** `connect()` now reads an item's current
situation cue via a new `_situation_readonly()` that never advances
`_situation_uses`, fully decoupling the two mechanisms — pairing an item
into a connected moment no longer perturbs what an unrelated recall of it
elsewhere in the lesson shows.

### Tests

Strengthened `test_connected_use_reaches_an_arc_whose_items_are_wired_into_no_dialogue`'s
assertion from "the arc's items intersect the connected items" (passable
with just one of the two) to "both of the arc's own two items are in
there" — the weaker version could pass even with material pulled in from
outside the arc.

Added `test_each_arc_gets_its_own_connected_use_moment_without_a_drill_streak`:
two arcs, `drill_streak_limit` set unreachably high so the streak breaker
never trips, confirming (a) each arc still gets its own connected-use
exercise and (b) each one's `item_ids` is *exactly* that arc's own two
items, not a mix with the other arc's — both directly requested by the
owner's review, confirmed to fail against the pre-fix code (arc 2 got
none at all in one version, and got contaminated with arc 1's material in
an earlier iteration of this fix, before landing on the "order second,
don't exclude" design above).

103 tests (102 → 103; `test_connected_use_reaches_an_arc_whose_items_are_wired_into_no_dialogue`
strengthened, not counted as new), all passing; `audiolesson validate` unchanged.

## Session 22: issue #44, round 4 — connect() could skip a multi-word item's own stage progression

The owner's last blocker: `do_connect()` recorded *any* has-situation
candidate at stage `"situation"` regardless of how far it had actually
climbed its own ladder — harmless for a short item, whose ladder goes
straight from `meaning` to `situation`, but a multi-word item's ladder
also has `cloze`/`hinted` in between. Since `LearnerState.record_lesson()`
never lowers a stage once raised (`st.stage = max(candidates, key=...
stage_index)`), sweeping such an item into a connect() exercise could
jump its persisted stage straight to `situation`, permanently skipping
stages it had never actually practised.

**Fix.** Added `_ready_for_situation(item)`: true only if the item's
*current* stage (its persisted `ItemState.stage` for already-known
material, or this lesson's own `exposures` for something introduced
today) is already at `situation` or one step short of it — i.e.
recording a `situation` exposure now continues its natural climb rather
than skipping stages. `_connect_pair()`'s candidate filter now requires
this alongside `has_situation`. Also had to tighten the per-arc
readiness check (step 0b, session 21) to use the same per-item gate,
not just "some post-intro touch" — otherwise an arc could be judged
"ready" before any of its own items individually were, and its
guaranteed connect() attempt would find nothing eligible in its own
material and silently fall back to unrelated review items instead
(caught by `test_each_arc_gets_its_own_connected_use_moment_...`
regressing when the per-item gate was added without this).

**Test.** `test_connect_never_skips_a_multi_word_items_own_stage_progression`:
a known multi-word item stuck at `hinted` (several stages short of
`situation`) alongside plenty of fully-progressed short items, so every
connect() this lesson has an alternative pairing that doesn't need it.
Confirmed against the pre-fix code that the multi-word item got swept
into a connect() exercise anyway. The test's second half is the general
guarantee the owner asked for ("monotonic-stage regression test"): for
every item exposed this lesson, its recorded stage sequence — starting
from wherever it stood *before* the lesson — never skips a ladder stage.
Stronger than the existing `test_stages_get_harder_within_lesson`, which
only checks the sequence doesn't go backward, not that it doesn't jump
ahead.

104 tests (103 → 104), all passing; `audiolesson validate` unchanged.

## Session 23: issue #29 — acting on the triage, second pass

With #44 merged, back to #29's own priority order: item 1 (triage of all
`dialogue_sequencing_report()` findings) was posted as a comment in
session 21 (see that comment on #29 for the full cluster breakdown —
A: numbers/money, B: reusable verbs/constructions embedded in fixed
phrases, C: general repeat-offender vocabulary, D: a one-dialogue
content bug). This session acted on the two lowest-risk, highest-value
items from that triage: cluster D (a content bug, one dialogue) and the
`nagranni` half of cluster B (the issue's own worked example, resolved
properly rather than patched). 49 → 41 advisory findings.

**Cluster D — `tungumal`'s partner line reached into an unrelated
module's vocabulary.** The dialogue's actual purpose is asking someone
to slow down; its second line volunteered full walking directions to a
pool ("Sundlaugin er beint áfram og svo til vinstri, rétt hjá
bankanum"), pulling in `beint`/`áfram`/`vinstri`/`bankanum`/`og` from a
directions module the learner hasn't reached yet. Not a sequencing
problem — a content mismatch. Trimmed both the line and its "repeat
that more slowly" callback down to the dialogue's own actual sentence
("Tölum við bara íslensku."), matching the plain-repeat style
`kaffihus`'s own "speak more slowly" turn already uses elsewhere in the
curriculum. Left `gert`/`tölum`/`bara`/`við` alone — those are the
dialogue's genuine on-topic content, not a detour, and resequencing them
is a broader question for the ongoing audit (item 2), not a one-line fix.

**Cluster B, `nagranni`'s two words — the issue's own worked example,
for real.** `nagranni` (module 1, order ~11) has a neighbour say "Gott
að heyra. Jæja, ég verð að fara." (Good to hear. Well, I have to go.) as
a natural leave-taking line — and #29's own issue body names `Ég verð
að fara` explicitly as the example of what *not* to do: turning one
dialogue's sentence into a special-cased prerequisite. It hadn't become
a prerequisite; it just sat unresequenced 777 items later (`heyra` was
worse still, 915 items later, as its own separate fixed phrase).

- `gott_ad_heyra` ("Good to hear.") is a short, complete, prereq-free,
  nothing-depends-on-it phrase — safe to relocate outright. Moved from
  module 24 to module 1, right before `nagranni`, following the same
  pattern session 16 already used for `frábært` (see the comment there).
- `verð að + infinitive` is exactly the "reusable construction embedded
  in a fixed phrase" case #29 asks to fix at the source. Module 2
  already has the machinery for this: an `"inf"`-tagged slot-fill
  vocabulary (`fara_heim`, `sofa`, `borða`, ...) built for `eg_vil`/
  `eg_aetla_ad`/`viltu`/`eg_nenni_ekki` — the same shape of construction,
  already scaffolded. Added `eg_verd_ad` ("Ég verð að {inf}.") to that
  same chain (`prereqs = ["fara_heim", "eg_aetla_ad"]`), reusing existing
  vocabulary rather than authoring new content. Verified by building a
  real lesson out to the point it's introduced: it recombines correctly
  with every `"inf"` item in later recalls ("Ég verð að borða.", "...fara
  í sund.", "...sofa.", "...hringja heim.", ...), and both English and
  Japanese slot substitution resolve correctly (`resolve_slots()` on
  both `meaning`/`meaning_ja`). Left the original `eg_verd_ad_fara`
  fixed phrase (module 20) in place rather than deleting it — nothing
  depends on it and it's still a legitimate review item, just a
  redundant one now; not worth the risk of an unrequested content
  deletion in the same pass.

**Test:** `test_dialogue_sequencing_report_is_advisory_not_gating`
hardcoded `nagranni`/`heyra` as the report's worst finding — now stale
by construction, since the whole point of the ongoing audit is to keep
moving that worst finding elsewhere. Generalized the test to check the
*mechanism* (advisory, never gates eligibility, gap stays large) rather
than which dialogue currently tops the list, so it won't need a
one-line update every time the audit fixes another finding.

**Second pass, same PR: the rest of cluster C.** `líka` (also, 3
dialogues), `sjáðu` (look!, 2 dialogues), `vegabréf` (passport, 2
dialogues), and `Það er góð hugmynd` (that's a good idea, 2 dialogues)
were all repeat offenders sitting in modules 19–25, well past where
several early dialogues already use them.

- `lika` and `thad_er_god_hugmynd`: short, prereq-free, nothing depends
  on them — relocated outright to module 1 (the `lika`/`frábært`/
  `thad_er_god_hugmynd` moves are now the same established pattern).
- `vegabref`: also prereq-free and already the example fill for the
  later `eg_er_med_have` construction — relocated to module 2.
- `sjáðu`: previously existed *only* embedded inside a whale-watching
  phrase (`sjadu_hvalinn`, module 23), gated behind a whale-specific
  prereq. Relocating that phrase alone would only have moved its
  `order` field — the whale prereq would still block it from actually
  being taught any earlier in a real lesson, a hollow fix that games
  the diagnostic without changing the learner experience. Added a new
  standalone, prereq-free `sjadu` phrase ("Sjáðu." / "Look.") instead,
  the same shape as the already-existing `biddu` ("Bíddu." / "Wait.").
- `ferð` (a trip): existed only inside `eg_vil_boka_ferd` (module 25),
  a fixed phrase that just spells out the `eg_vil` ("Ég vil {inf}.")
  construction by hand instead of using it — another instance of
  cluster B's "reusable construction embedded in a fixed phrase"
  pattern, this time for a noun rather than a verb. Added `boka_ferd`
  ("bóka ferð" / "book a tour") to module 2's `"inf"` vocabulary instead
  of just relocating the phrase, so `eg_vil` (and anything later built
  on that vocabulary) can recombine with it like any other `"inf"` item.

Verified with a 15-lesson simulation that all five surface as expected
new items early on, and that `eg_vil` correctly resolves to "Ég vil
bóka ferð." / "I want to book a tour." with `boka_ferd` filled in.

`dialogue_sequencing_report()`: 41 → 30 advisory findings; the
repeat-offender list is now down to `og`, `bara`, `krónur`, `hundruð` —
all cluster A (numbers/money) or the one deliberately-left-alone word
in `tungumal`.

**Scope note.** Cluster A (numbers/money — money amounts are taught as
whole fixed phrases like "fimm hundruð krónur" rather than a
number+currency construction, and the base digits 5–12 are taught
inside the *time* module, after cafe dialogues already need them for
prices) is the one real, higher-effort item left from the original
triage — it touches Icelandic's gendered number forms (`fjórir`/
`fjögur`, `tveir`/`tvær`/`tvö`, ...) and deserves the same "construction,
not more fixed phrases" treatment `godur_gender` already modeled, not a
quick relocation. Left for a dedicated follow-up rather than rushed in
this pass. #29 stays open; items 2 (curriculum-wide audit) and 3
(case/tense/modality pilot) are still not started.

104 tests (still 104 — one updated, none added), all passing;
`audiolesson validate` 49 → 30 advisory findings across the two passes.

**Third pass, same PR: a real transfer step for `godur_gender`.** The
owner reviewed a real Lesson 3 run and raised a design point beyond
resequencing: `godur_gender`'s discrimination practice (`do_discriminate`)
only ever switches between the milestone's own three founding examples
(`góðan daginn` / `góða nótt` / `gott kvöld`) — noticing the gender
contrast is not the same as being asked to apply it to a noun the
learner hasn't seen it with before, and #29's own progression diagram
explicitly ends in "apply it to new vocabulary and situations," not
"replay the same three phrases forever." The owner proposed adding this
— whether reusable material gets an actual *transfer* opportunity, not
just a favorable `order` — to #29's own completion criteria going
forward.

**Fix.** Added `Note.transfer_items: list[str]` — extra items
`do_discriminate` may reach for once *known*, distinct from the
milestone's gating `items`. Critically, `transfer_items` never gates
when the milestone *fires* (`_eligible_milestone` only ever checks
`items`) — requiring the transfer material known first would be
circular, since introducing it is the whole point. `do_discriminate` now
checks `transfer_items` the same "met, or exposed this lesson" way
`_eligible_milestone` already checks its own gating items, so it never
asks for something never introduced, and prefers them over `items` when
available.

Wired `godur_gender` to one already-known-gender noun per gender it
didn't already have: `thad_er_god_hugmynd` (feminine, "hugmynd" — this
is the very phrase relocated in the second pass above) and `gott_vedur`
(neuter, "veður" — already existed as a `weather`-slot vocabulary item,
just needed a `situation` field added to make it a discrimination
candidate). No masculine example existed anywhere in the curriculum, so
added one: `godur_matur` ("Góður matur." / "Good food.", module 17) —
"matur" is masculine (confirmed via the existing `maturinn_er_tilbuinn`,
whose `-inn` suffix is the masculine definite article).

Verified directly (not just via the test suite): built a lesson with
only the three gating items known — the milestone fires and discriminates
between two of its own three examples, exactly as before. Built another
with `thad_er_god_hugmynd` also already known — the discrimination step
right after the note now includes it, applying the pattern to a genuinely
different noun.

**Tests:** `test_milestone_fires_without_any_of_its_transfer_items_being_known`
and `test_discrimination_prefers_a_known_transfer_item_over_replaying_the_same_examples`,
both confirmed to fail against the pre-`transfer_items` code (the first
with an `AttributeError`, since the field didn't exist yet; the second on
the discrimination set not containing the transfer item). Also widened
`test_milestone_note_is_followed_by_contrastive_discrimination`'s allowed
id set to `items | transfer_items` — it was checking discrimination
candidates against only the gating `items`, which this change makes too
narrow (currently passed anyway across its own 20-lesson simulation, but
only because no transfer item happened to already be known at firing
time in that particular run — not a guarantee).

**Scope note, from the owner's review.** The second half of that review —
Lesson 3 introduces `Gjörðu svo vel`, `Verði þér að góðu`, `Gangi þér vel`,
and `Eigðu góðan dag` close together, useful phrases that currently behave
as unrelated memorized strings despite sharing morphology — is explicitly
framed by the owner as a question for the still-not-started curriculum-wide
audit (item 2), not an immediate fix: distinguishing lexicalized chunks
worth memorizing whole from families where a shared grammatical dimension
would reduce memorization load is exactly the kind of judgment call that
audit exists to make, module by module, not something to guess at in
isolation for four phrases.

106 tests (104 → 106), all passing; `audiolesson validate` unchanged
by this pass (transfer material is content depth, not a sequencing gap
the report measures).

**Fourth pass, same PR: the transfer trio was correct gender, wrong case
too — blocker.** The owner's review of the third pass caught a real
Icelandic grammar error: `godur_gender`'s own three examples (`Góðan
daginn`, `Góða nótt`, `Gott kvöld`) are all **accusative** case, but the
transfer trio wired into `transfer_items` (`Góður matur`, `Það er góð
hugmynd`, `Gott veður`) are all **nominative**. Masculine and feminine
adjective endings differ by case as well as gender (BÍN: `góður`
masc. nom., `góðan` masc. acc.; `góð` fem. nom., `góða` fem. acc.) — only
neuter happens to look identical in both. Silently pairing them as if
gender were the only thing varying directly contradicted the note's own
text ("the ending changes with the noun's grammatical gender," said of
three examples that all share one case) and would have taught the
learner an incorrect paradigm: `masc: góðan → góður` reads as if that
were a gender change, when it's actually gender *and* case at once.

**Fix.** Removed `transfer_items` from `godur_gender` entirely — pairing
examples across cases isn't a same-case gender transfer, so it doesn't
belong there. Split the nominative trio into its own milestone,
`godur_gender_nominative`, explicit in its own text about which case
these are (nominative) and how the endings differ from `godur_gender`'s
accusative ones — not silently folded in as if it were the same
paradigm slot with only gender varying. Being its own milestone (gated
on all three of `godur_matur`/`thad_er_god_hugmynd`/`gott_vedur`) also
resolves the owner's non-blocking second point from the third pass more
thoroughly than `transfer_items` on its own could: an ordinary milestone
is *guaranteed* to fire once its items are known (same mechanism every
other milestone in the curriculum already relies on), where
`transfer_items` only helped if the material *happened* to already be
known at firing time.

The `Note.transfer_items` mechanism itself stays — the owner's review
was explicit that the concept (separating a milestone's gating examples
from material it can reach for once known, without letting the latter
delay the former) fits #29 well; the problem was this specific content
pairing, not the mechanism. Rewrote the two mechanism tests
(`test_milestone_fires_without_any_of_its_transfer_items_being_known`,
`test_discrimination_prefers_a_known_transfer_item_over_replaying_the_same_examples`)
against a small synthetic curriculum instead of the real
`godur_gender`, so their validity no longer depends on a specific
curriculum-content decision that turned out to need correcting — a
better test design independent of this fix. Added
`test_godur_gender_nominative_is_explicit_about_case_not_just_gender`,
checking directly that `godur_gender` carries no `transfer_items` and
that the new note's own text names both cases.

**Knock-on fix:** the new milestone's gating items are deeper in the
curriculum (`godur_matur` at item order ~688) than any existing
milestone, so the two broad "every milestone must fire" tests — which
simulated 20 lessons at `auto`-pace, reaching only item order ~72 —
needed a faster, fixed-pace config (`new_items=10`, 30-minute lessons,
early-exit once satisfied) to actually reach it in a reasonable test
runtime; auto-pace escalation was never the point of either test, just
a convenient way to run several lessons.

**Also addressed (non-blocking):** the owner questioned whether
`godur_matur` — a new fixed phrase authored specifically to have a
masculine transfer example — runs against #29's own "reusable capability
over more fixed phrases" thrust. Left as-is for now (it's grammatically
safe, harmless content), but noted for the curriculum-wide audit: a
generative adjective-agreement construction (a noun slot tagged by
gender, resolving the correct `góður`/`góð`/`gott` ending automatically)
would fit #29's spirit better than one more fixed phrase, and is a
bigger feature than this fix's scope.

107 tests (106 → 107), all passing; `audiolesson validate` unchanged
by this pass.

**Fifth pass, same PR: a genuine generate-from-parts pilot — the owner's
final requirement before #29 can close.** Confirming the fourth pass
mergeable, the owner added a new, explicit acceptance criterion for
closing #29 itself (not a blocker for this PR): "at least one
grammar/construction pilot where the learner generates a novel
combination rather than recalling a pre-authored phrase." Worked example:
a learner who already separately knows (1) the `góður`/`góð`/`gott`
gender distinction and (2) that `bíll`/`bók`/`hús` are masc/fem/neut
should be able to produce "Góður bíll."/"Góð bók."/"Gott hús." as
combinations that were never authored as their own phrase items — making
#29's own "notice → model → apply to new vocabulary" pipeline actually
true, rather than `godur_matur`'s "author a complete phrase → memorize it
→ explain post-hoc that it fits a pattern" (flagged as still
fixed-phrase accumulation at the end of the fourth pass above, and the
owner reiterated that discomfort persisted through it).

**What was missing.** The recombination machinery this criterion needs
already existed (`Builder.generate()`/`_recombine()` in `exercises.py`
picks a combo of learner-known fills for a construction's slot(s) and
computes the sentence via `Curriculum.resolve_slots()` — nothing about
the *result* is ever stored as its own item). What no construction had
ever needed before is a slot fill that changes the **construction's own
other wording**, not just which word is named: every existing
`slots`/`example` mechanism does plain text substitution into a fixed
template, so a noun slot could vary which noun appeared, but never make
the adjective *next to it* agree.

**Fix.** Added `Item.gender: str | None` (masc/fem/neut, for nouns) and
`Item.agreement: dict[str, dict[str, str]]` (construction: `{slot}` name
→ `{gender: surface form}`). `Curriculum.resolve_slots()` now resolves
agreement placeholders first, from the `.gender` of whichever filled item
carries one, before the ordinary per-slot substitution — so
`{adj} {noun}.` with `agreement = {adj: {masc: "Góður", fem: "Góð", neut:
"Gott"}}` genuinely generates three different surface strings from one
authored template, driven entirely by which independently-known noun
fills `{noun}`. `validate()` exempts an agreement placeholder from the
usual "must have a `[slots]` tag and appear in `meaning`" checks (it's
never filled by picking an item) but requires its form dict cover all
three genders, and requires at least one of the construction's real
slots to be tagged with gendered items at all — so a construction can't
declare agreement it can never actually resolve.

**Content.** Added `godur_noun` (module 18, `curricula/is-en/
18-adjectives.toml`): `{adj} {noun}.` / `Good {noun}.`, slot `noun`
tagged `gendered_noun`, `agreement` as above, `example = {noun: "hus"}`,
gated on the three items behind `godur_gender_nominative` plus `hus`
itself. Three gendered nouns back it: `bill` (masc, "bíll"/"car", module
10) and `bok` (fem, "bók"/"book", module 15) are new; `hus` (neut,
module 16, already existed) was tagged `gendered_noun` and had its
meaning trimmed from "a house" to "house" (matching the article-free
"Good X." style `godur_matur`/`gott_vedur` already use, and needed
because a bare-noun `{noun}` slot inside "Good {noun}." would otherwise
double up the article: "Good a house."). `hús` being nominative/
accusative-identical for neuter (the same fact `godur_gender_nominative`
already explains) is also what let `hus` be reused directly as the
construction's own worked example rather than adding a fourth new item.

**Verified directly:** `cur.resolve_slots(godur_noun, {"noun": item})`
for `bill`/`bok`/`hus` produces exactly `"Góður bíll."`/`"Góð bók."`/
`"Gott hús."` — the owner's own worked example, character for character
— and none of those three strings exists anywhere else in the curriculum
as its own item's `target` (checked directly, not just by construction:
if some future edit ever adds one as a fixed phrase, `validate()`'s
existing duplicate-target check catches it too). Also ran
`Builder.generate()` against a learner who knows only `godur_noun`'s
prereqs (not `bill`/`bok`, which stay learnable independently later) —
it produces `"Gott hús."`, proving the same machinery every other
construction uses for lesson-time recombination already picks this one
up with zero changes beyond the new fields.

**Tests:** three new ones against a synthetic curriculum (isolated from
real content decisions, same reasoning as `_transfer_curriculum` above)
cover the agreement mechanism itself: resolves correctly per gender,
rejects an `agreement` dict missing a gender, rejects a construction with
no gendered slot to resolve from. A fourth, against the real curriculum,
pins the exact three generated strings and that none is a pre-authored
item. A fifth exercises `Builder.generate()` end-to-end. Also widened
`test_icelandic_course_has_complete_japanese_glosses`'s per-slot
Japanese-gloss check to skip agreement placeholders (they're never filled
from an item's own meaning, so have no reason to appear in it).

112 tests (107 → 112), all passing; `audiolesson validate` unchanged
(a new construction and gendered nouns, not a sequencing change).

**Still open for #29 itself** (this pilot satisfies the owner's new
criterion for a *single* construction; #29's own remaining items are
unaffected): item 2 (curriculum-wide dependency audit) and item 3 (piloting
whether the pattern generalizes to case/tense/modality) are still not
started; cluster A (numbers/money, gendered number forms) is still the
one deferred triage item; the `Gjörðu svo vel`/`Verði þér að góðu`/
`Gangi þér vel`/`Eigðu góðan dag` family is still explicitly deferred to
the audit.

**Sixth pass (PR #50 review): the mechanism resolved gender, but the
learner was never actually told it.** The owner reviewed the fifth pass
as opened on a fresh PR (#47 had merged mid-session) and raised three
points, all fixed in the same PR.

1. **The system knew each noun's gender; the learner never did.**
   `Item.gender` was read by `resolve_slots()` but never surfaced in any
   exercise — `Builder.intro()` doesn't read `item.gender` or
   `pronunciation_notes`, so a learner could reach `godur_noun` having
   memorized "bíll = car" without ever being told "bíll is masculine."
   That made the pilot genuine *machine-side* recombination but not yet
   *learner-side* generation from known parts. Fixed with a new note,
   `gendered_nouns_bill_bok_hus` (90-notes.toml), naming all three
   genders and tying them back to the already-known `dagur`/`hugmynd`/
   `veður` examples — the same "aside" mechanism `godur_gender`/
   `godur_gender_nominative` already use for exactly this job, not a
   change to the shared `Builder.intro()` path every item goes through.
   `godur_noun`'s own prereqs were widened from just `hus` (its worked
   example) to all three gendered nouns, so the note has always fired —
   and the learner has actually been told each gender — before the
   construction is reachable. (Discovered a knock-on gap while writing
   the regression test: `bill`/`bok`/`hus` had no `situation` field, so
   `do_discriminate` — which only offers situation-eligible items — had
   nothing to discriminate between after the note fires. Added one to
   each, matching the existing "short scene ending in a one-word
   instruction" style `frábært`/`gott_vedur` already use.)
2. **`agreement`'s controlling slot was inferred, not named.**
   `resolve_slots()` picked "whichever filled item happens to carry a
   `.gender`" — correct for `godur_noun` (exactly one gendered slot) but
   silently ambiguous for any future construction with more than one.
   `Item.agreement`'s per-placeholder dict now carries an explicit
   `"from": "<slot name>"`, and resolution is `fills[rule["from"]].gender`
   — unambiguous regardless of how many other slots exist.
3. **Validation allowed a runtime `KeyError`.** The old check only
   required *some* item behind an agreement construction's slot tag to
   have a gender — a same-tagged but ungendered item, or a typo like
   `gender = "masculine"`, would pass validation and only fail the day
   it was actually picked (`forms[None]`/`forms["masculine"]`).
   `validate()` now checks `Item.gender` (when set) is one of
   `masc`/`fem`/`neut` for every item in the curriculum; that every
   candidate behind an agreement's controlling slot has a gender, not
   just one of them; and that the agreement table covers every gender
   those candidates can actually produce (no longer hardcoded to require
   all three regardless of what the controller's candidates offer).

**Tests:** three new validation-rejection tests (missing `from`, missing
a form the controller's candidates actually need, an ungendered
candidate slipping through) plus `test_item_gender_must_be_a_known_value`
mirror the owner's three-item checklist directly. A new
`test_gendered_nouns_note_actually_teaches_the_genders_godur_noun_relies_on`
checks the note names all three words and genders, and that
`godur_noun`'s prereqs *include* the note's gating items — necessary for
the ordering guarantee below, though (see the seventh pass) not
sufficient on its own, which is exactly what that pass caught. Widened
`test_godur_noun_construction_is_reachable_once_its_prereqs_are_known`
to accept any of the three correct generated sentences (all three
gendered nouns are prereqs now, so which one `Builder.generate()` picks
first is no longer pinned to a single outcome).

115 tests (112 → 115), all passing; `audiolesson validate` unchanged.

**Also, unrelated to the review:** PR #47 merged mid-session before this
pass was pushed, and the branch had gone stale under it — rebuilt the
commit cleanly on top of the merged `main` and opened a fresh PR (#50)
for this work rather than force-pushing over a diverged branch.

**Seventh pass (PR #50 review): the note firing wasn't actually
guaranteed before the construction — reproduced and fixed.** The owner's
follow-up review named the sixth pass's overstated claim directly:
`godur_noun`'s prereqs including the note's gating items proves the note
*can* fire first, not that it *does*. Asked for the guarantee to be real,
plus a regression test of the shape "all noun items already known, note
unheard → next lesson must play the note before `godur_noun`'s intro."

**Reproduced first, on a synthetic curriculum** (isolated from
`godur_noun`'s own content, same convention as this file's other
mechanism tests): a learner who already knows a milestone's three
gating items, with the note unheard, entering a lesson whose only new
thing to introduce is a construction whose own worked-example fill
(`Curriculum.example_fill`) happens to be one of those same three items.
The construction was introduced *first*. Root cause: `Builder.
_intro_construction` plays the construction's own example fill as part
of its intro exercise, and the only place a milestone note gets checked
is the post-exercise `Planner._maybe_note(sc, sc.exercises[-1].item_ids,
...)` call — which runs *after* that intro exercise completes, once it's
too late. In the ordinary case (a plain vocab item slowly reaching
"known" over many separate lessons) this race never has room to open,
since every earlier touch of the item is itself a chance for the check
to fire the note well before anything downstream needs it — the exact
"fires the very lesson its last example is introduced" guarantee
`_eligible_milestone`'s own docstring already describes. A construction
example-filling on its very first exposure is the one case that check
runs too late for.

**Fix.** `do_intro()` now checks `self._eligible_milestone(item.prereqs)`
*before* calling `b.intro()`, not just after — reusing the exact same
eligibility check the reactive path already relies on, just moved one
step earlier for the one case that needed it. If a milestone gating this
item's own prereqs is due, it (and its discrimination step) plays first.
`_eligible_milestone` already excludes notes in `notes_played`, so this
never double-fires alongside the reactive check that still runs after
every exercise. General by construction (checks any item's prereqs, not
`godur_noun` specifically or anything agreement-related) rather than a
narrow one-off hack — and, being a strict tightening of an existing
"fires no later than X" guarantee, is unlikely to change behavior for
any *other* milestone, confirmed by the full suite staying green
unchanged.

**Test:** `test_milestone_fires_before_a_construction_whose_own_example_fill_would_complete_it`,
built on the same synthetic reproduction, checked to fail against the
pre-fix code (confirmed directly: `git stash` the fix, rerun, watch it
fail with the construction's intro one exercise ahead of the note) before
being folded into the suite as a permanent regression guard.

116 tests (115 → 116), all passing; `audiolesson validate` unchanged.

**Eighth pass (PR #50 review): the seventh pass only drained the first
due milestone, not every one.** The owner caught it by reading
`godur_noun`'s own prereqs closely: they span *two* independent
milestones at once — `godur_gender_nominative`'s trio and
`gendered_nouns_bill_bok_hus`'s — but the seventh pass's fix called
`self._eligible_milestone(item.prereqs)` exactly once per intro, and
`_eligible_milestone` only ever returns the *first* eligible note it
finds. If both milestones were simultaneously due and unheard, the first
fired before the intro as intended, but the second still only fired via
the old reactive post-exercise path — too late, the exact failure mode
the seventh pass exists to prevent, just for the second milestone
instead of the only one.

**Fix**, exactly as small as the owner's own sketch: the single `if`
became a `while (milestone := self._eligible_milestone(item.prereqs))
is not None:` loop, draining every currently-due milestone among the
item's prereqs before its intro plays. `notes_played` (already checked
inside `_eligible_milestone`) rules out looping on the same note twice.

**Test:** `test_all_due_milestones_fire_before_an_intro_not_just_the_first_one_found`,
two independent synthetic milestone groups both already known and
unheard, gating one construction — confirmed to fail against the
pre-loop code (the second group's note landed one exercise after the
construction's intro) before folding it in.

117 tests (116 → 117), all passing; `audiolesson validate` unchanged.

## Session 24: issue #49 — embedded third-language examples, and rushed pronunciation scaffolding

A real Icelandic Lesson 3 listening run surfaced two audio-delivery problems, filed as
#49: (1) Japanese example words embedded in English instructor notes (`sate`, `yare
yare`, `sō ka`, `onigiri`) were read with English TTS pronunciation, since they were
just part of ordinary instructor narration; (2) pronunciation scaffolding — the `slow`
demo, and backward-build chunking for hard multi-word phrases (`Gjörðu svo vel`, `Verði
þér að góðu`, `Eigðu góðan dag`) — still felt too fast even where it existed.

**Part 1: a third-language span inside a note.** The existing «...» markup
(`NOTE_TARGET_RE`, issue #34 point 1) already solves "target-language phrase inside
instructor narration," but a note can legitimately mention a language that's neither —
an English note naming a Japanese word is talking about a *third* language, not the
course's Icelandic. Extended the same markup rather than inventing a new one: a «...»
span may now open with an explicit `"xx:"` language code — `«ja:sate»` — while a bare
span keeps meaning "target language," unchanged. `Curriculum.split_note_span()` (new,
content.py, next to `NOTE_TARGET_RE`) parses it; `Builder._speak_note_text()` passes the
explicit language through to `_speak()` (which gained a `lang` parameter, defaulting to
`self.tl` so every existing call site is unaffected).

That alone wasn't enough at the render layer: `VoiceProfile.voice_for()` looks up a
speaker's voice by role name (`"instructor"`), and if a profile configures a *fixed*
voice for that role (typical for a real deployment, not just the default-per-language
fallback this repo's own tests mostly exercise), a Japanese-language segment would still
get that fixed English voice — `lang` only chooses the voice when nothing overrides it.
Fixed in `render_script()`'s `request_for()`: a segment whose language is neither the
script's own known nor target language is now looked up under a profile key
(`f"{speaker}:{lang}"`) the profile was never configured for, so it falls straight
through to `provider.default_voices(lang)` — no `VoiceProfile` schema change needed.

Applied the markup to the only two notes issue #49 actually named
(`curricula/is-en/90-notes.toml`, `jaeja` and `pylsa`): `«ja:sate»`, `«ja:yare yare»`,
`«ja:sō ka»`, `«ja:onigiri»`. Their `text_ja` (Japanese-narrated) versions already write
these words as ordinary Japanese prose with no romanization at all, so they needed no
change — the third-language problem only exists when the *narration* language differs
from the *example* language, which only happens in the English-narrated version.

Verified directly: built the two real notes with `Builder.note()` and confirmed each
Japanese word became its own `speak` segment with `lang="ja"`; rendered them with the
real `espeak` provider end to end (no crash — espeak-ng accepts `-v ja`) alongside the
existing Icelandic/English segments in the same note.

**Part 2: pronunciation scaffolding was still too fast.** Two separate, both objective,
bugs — not just a "make it feel slower" request:

1. **Backward-build chunks never actually went slow.** `Builder.intro()`'s three
   pronunciation-teaching branches (single hard word, difficulty≥2 multi-word, and
   backward-build) are the *only* three places `Timing.slow_rate` is used anywhere in
   this codebase — except the backward-build chunk loop itself never actually passed
   `rate=self.timing.slow_rate` to `_speak()`, unlike the other two branches. Each chunk
   played at natural rate, which is exactly what issue #49 reported ("backward-building
   also moves through chunks quickly"). Fixed by adding the missing `rate=` argument.
2. **`slow_rate` itself (0.72) still read as rushed**, confirmed by the owner's own
   listening pass on `Fyrirgefðu`/`Sömuleiðis` — both single hard words that *already*
   go through the slow-rate branch, so this wasn't the chunk bug; the rate value itself
   needed to drop further. Lowered to 0.6. Since every one of `slow_rate`'s three call
   sites is a deliberate pronunciation demo (there is no competing "ordinary slow
   narration" use to protect), issue #49's "define a pronunciation-teaching rate
   separately from ordinary slow speech" turned out to already be true structurally —
   there was only ever one meaning for "slow" in this codebase.

Also added one `_beat()` after each backward-build chunk's repeat pause — acoustic
separation before the next chunk starts, distinct from the repeat pause itself (which is
sized for the *learner's* own natural-speed imitation, not for marking the chunk
boundary) — directly matching the acceptance criteria's "enough playback/repetition time
to distinguish and imitate each chunk comfortably."

**Tests:** `split_note_span()` unit tests (bare span, `ja:` prefix, optional space after
the colon, a false-positive guard for something colon-shaped but not a language code
like a clock time); `_speak_note_text()` now speaking a `«ja:...»` span in Japanese while
a bare span is unaffected; a `StubProvider`-based render test with a lang-distinct
`default_voices()` and a *fixed* profile voice configured for `"instructor"`, confirming
a Japanese segment's actual `synthesize()` call never receives that fixed voice.
`test_hard_phrase_is_built_backwards` (pre-existing) updated: it now expects
`"Speaker A (slow):"`, not the old unmarked natural-rate label — confirming the chunk-
rate fix directly, since the transcript's `(slow)` marker comes from the segment's own
rate.

120 tests (117 → 120), all passing; `audiolesson validate` unchanged (no sequencing
change); smoke-generated both the `is-en` and `fr-en-a1` courses with real `espeak`
audio end to end.

**Second pass (PR #51 review): routing by `lang` alone doesn't make pronunciation
provider-independent.** The owner caught a real weak spot in part 1's design: passing
the *romanized* display text ("sate") to the provider with `lang="ja"` still puts
correct pronunciation at the mercy of the provider actually reading transliterated text
well — and `OpenAIProvider.synthesize()` (`render/tts.py`) doesn't even look at `lang`
at all, it just sends whatever `text` it's given straight to the API. The robust fix is
to send the provider *native orthography* directly, not lean on `lang` to somehow fix up
romanized text.

**Fix.** If the transcript should keep the familiar romanization (as it does here — an
English reader recognizes "sate," not necessarily さて), the note markup needs to carry
both forms. Extended `«xx:...»` once more: after the language code, an optional
`"display|speech"` pair — `«ja:sate|さて»` shows "sate" in the transcript but sends "さて"
to the provider. A bare `«ja:onigiri»` (no `|`) still means display and speech are the
same text, unchanged. `split_note_span()` now returns a 3-tuple `(lang, display,
speech)` instead of 2. `Segment` gained one new optional field, `speech_text: str |
None` (defaults to `None` = "speak `text` as-is," so every existing segment
construction anywhere in the codebase — tests included — is unaffected; `to_dict()`
already drops `None` fields, so old scripts/cues.json serialize identically). The
renderer's `request_for()` now sends `seg.speech_text or seg.text` to the provider,
while `seg.text` alone still drives the transcript and cues.json — mirroring how
`RESPELL_FOR_SPEECH`/`_respell()` already keeps the *correct* spelling in `Segment.text`
and only substitutes at the last possible moment before synthesis, for the same reason
(the "Halló" → "Haló" fix). Deliberately *not* folded into that table, though: it's
scoped to "known TTS mispronunciation quirks in this project's own target/known
languages," a global per-language substitution; a romanized-example's native form is
authored per instance, at the point of writing the note, which is far harder to forget
than remembering to also edit a lookup table in a different file. `Timing.
speech_estimate()` (used for lesson-length budgeting) is computed from `speech_text`
when set, not `text` — otherwise a Japanese duration estimate would count Latin
characters instead of the kana that will actually be spoken.

Not Japanese-specific by construction: the owner named pinyin → Hanzi, Korean
romanization → Hangul, and Arabic transliteration → Arabic script as the same shape of
problem this generalizes to.

Applied to both real notes: `«ja:sate|さて»`, `«ja:yare yare|やれやれ»`, `«ja:sō ka|そう
か»`, `«ja:onigiri|おにぎり»`.

**Tests:** `split_note_span()`'s 3-tuple return updated across its existing tests, plus
a new one pinning the `display|speech` split itself (including a non-Japanese example,
`zh:pinyin|漢字`, to keep the mechanism visibly general). `_speak_note_text()` gained a
test that a `«ja:sate|さて»` span's segment carries `text="sate"` (transcript) separately
from `speech_text="さて"`, and that the transcript itself contains "sate," never "さて".
Most directly answering the owner's own ask: a new render-level test with a
`StubProvider` spy pins the *exact* `(text, lang)` tuple reaching `synthesize()` as
`("おにぎり", "ja")` — proving the provider receives native orthography regardless of
whether it uses `lang` for anything, not just that *a* Japanese-appropriate voice got
selected (which the existing routing test from the first pass already covered, and
still passes unchanged).

Verified directly again: rebuilt the two real notes and confirmed each Japanese
example's segment now carries the romanized `text` and native `speech_text` separately;
rendered with real `espeak` end to end (still no crash); printed the actual `cues`
returned by `render_script()` and confirmed they show "sate"/"yare yare"/"sō ka" (the
romanization), not the kana, matching what a reader following along should see.

123 tests (120 → 123), all passing; `audiolesson validate` unchanged.

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

## Session 25: issue #48 — from isolated recall toward end-to-end conversation

Opened alongside #49 from the same real Lesson 3 listening run: a lot of the
active work still has the shape "English instruction/situation → retrieve
one Icelandic phrase → hear the answer," with the learner rarely
experiencing a full communicative episode (native opener → response →
partner reaction → continuation → natural close).

**Investigated first, before writing anything**, since much of what #48 asks
for sounded like it might already exist from issue #26 (dialogue scaffolding
fade) and #44 (connected-use guarantee). Simulated 60 real lessons on the
full `is-en` curriculum and inspected the actual generated scripts:

- `nagranni` (the neighbour-greeting dialogue) by lesson 6 already plays as:
  first turn keeps its English cue (nothing to react to yet, no partner line
  before it), but turns 2 and 3 have **no English cue at all** — the
  partner's own Icelandic line is the retrieval cue — and the whole thing
  ends with `Builder.dialogue()`'s `replay` block: the complete 3-turn
  exchange spoken start to finish by `native_a`/`native_b` alone, zero
  instructor narration. 11 distinct dialogues got played across the 60
  lessons (`nagranni` 16 times), and no lesson with substantial known
  material (>50 items) ever came up with zero dialogue activity.
- This already satisfies several of #48's acceptance criteria directly:
  multi-turn interactions, later encounters requiring comprehension of the
  partner's line rather than an English cue, and progression from
  scaffolded first encounter to a minimally-scaffolded full replay.

**The one clear, concrete gap found**: `do_connect()` (issue #44's
recombination fallback for connected use when no authored dialogue covers
the current material). Its `Builder.connect()` narrates situation A, takes
the answer, then narrates `connect_then` ("And then —") and situation B,
takes the second answer — entirely instructor-narrated, no partner voice
anywhere. Exactly the shape #48 names directly, just wrapped inside one
exercise instead of two.

Brought this specific gap to the owner rather than guessing at a fix for
all of #48 at once (a genuinely open design question, not an objective
bug): first proposal was a short partner "reaction" between the two
retrievals; the owner's actual preference was more substantive — keep both
instructor-narrated situations, but have the partner speak a real line
*between* answer A and situation B, so the exercise reads as one connected
scene: `instructor situation A → answer A → partner line → instructor
situation B → answer B`.

**Fix.** `connect()` gained an optional `connector: Item | None` parameter.
When given, `native_b` speaks the connector's own `target` text between the
two retrievals, replacing the `connect_then` English narration entirely;
`None` (no eligible item — e.g. the small fr-en-a1 sample curriculum, which
has no discourse-topic items at all) falls back to the original English
bridge, unchanged. The connector itself, `_connector_line()` (new,
planner.py), is drawn from the learner's own **already-known** vocabulary —
a short (`word_count <= 2`), `topics=["discourse"]` item — rather than
authored per pairing: `_connect_pair`'s two recombined items are arbitrary
and unrelated in general, so nothing could be *written* to fit every
possible pairing anyway, and reusing a known discourse marker (`Jæja.`,
`Frábært.`, `Því miður.`, ...) both avoids new fixed-phrase content (the
same "reuse over more fixed phrases" thrust as #29) and gives that item a
small passive-exposure credit via the existing `support` bookkeeping (its
id is added to the exercise's `item_ids`, which `_record()` already counts
as exposure for anything not in `primary`).

Verified directly against the real curriculum, not just synthetic tests: a
lesson 7 `connect()` exercise on `gætirðu_talað_hægar` (ask to speak more
slowly) and `gætirðu_endurtekið_þetta` (ask to repeat) picked `Því miður.`
("Unfortunately.") as the connector — a genuinely plausible bridge between
"the barista's too fast, ask her to slow down" and "you missed the room
number, ask her to repeat it."

**Tests:** `test_connect_uses_a_partner_line_instead_of_narrating_and_then`
(synthetic curriculum, a known discourse item available) checks the exact
shape the owner asked for — narrate → answer → `native_b` speak → narrate →
answer, `connect_then` absent, the connector's id present in the exercise
for exposure credit. `test_connect_falls_back_to_the_english_bridge_without_a_known_discourse_item`
(no discourse item known at all) checks the original behavior is preserved
exactly, unchanged — the fr-en-a1 sample curriculum most other tests use
falls into this path, which is why the full suite needed no other changes.

125 tests (123 → 125), all passing; `audiolesson validate` unchanged;
smoke-generated both courses with real `espeak` audio.

**Second pass (PR #52 review): the connector needed to be curated, not
selected.** The owner agreed with the overall shape but flagged a real
blocker in `_connector_line()`'s selection rule, `"discourse" in
item.topics and item.word_count <= 2`: `discourse` is a much broader
category than "can stand alone as a natural partner turn here" — it also
catches short function words (`og` "and", `en` "but", `eða` "or", `með`
"with") that read as nonsense alone ("Partner: Og."), and even among
genuine standalone reactions (`Frábært`/`Því miður`/`Auðvitað`/`Jæja`),
none is a guaranteed fit for an arbitrary pairing. The owner also
clarified something usefully: keeping the *second* item's own English
situation cue is fine — a partner utterance rarely implies one uniquely
correct response, so the instructor's instruction still earns its keep
by narrowing the task to something self-checkable. What actually matters
is that the *target-language* turns alone — answer A → bridge → answer B
— read as one coherent exchange once the English scaffolding is stripped
away, and that can't come from an algorithm picking among unrelated
already-known vocabulary; it has to be authored.

**Fix.** Replaced the generic selection entirely with `Item.partner_cue:
str = ""` (new field, content.py) — a target-language line a curriculum
author curates specifically to lead naturally into *that* item as a
response. `connect()` now checks `items[1].partner_cue` directly: when
authored, `native_b` speaks it between the two retrievals (replacing
`connect_then` as before); empty (the default — most items have no
authored bridge) falls back to the original English narration, unchanged.
`_connector_line()` and its discourse-topic filtering are gone entirely
— no more picking from *any* known item, algorithmically, at build time.
Authored one for real: `gaetirdu_endurtekid_thetta` ("Could you repeat
that?", already gated by a `situation` that presumes the learner missed
something the partner said) got `partner_cue = "Auðvitað. Herbergið er
númer tuttugu og þrjú."` — the owner's own worked example, verbatim:
"Gætirðu talað hægar?" → "Auðvitað. Herbergið er númer tuttugu og þrjú."
→ "Gætirðu endurtekið þetta?" holds together as a real exchange with no
instructor narration at all.

**Tests:** `test_connect_speaks_the_second_items_own_authored_partner_cue`
(a synthetic curriculum where every item authors a `partner_cue`, so the
test is robust to exactly which two items `_connect_pair` happens to
choose) replaces the old discourse-topic-item test; checks the same
shape as before (situation A → answer A → partner line → situation B →
answer B, `connect_then` absent) but now asserts the spoken line is
specifically *item B's own* `partner_cue`, not an unrelated known item.
`test_connect_falls_back_to_the_english_bridge_without_an_authored_partner_cue`
(no item authors one) confirms the fallback is unchanged — this is also
what the small fr-en-a1 sample curriculum exercises, so the rest of the
suite needed no changes. Verified again against the real curriculum: a
forced `connect()` on `gaetirdu_talad_haegar`+`gaetirdu_endurtekid_thetta`
now plays exactly the owner's worked example.

125 tests, all passing (replaced, not net new); `audiolesson validate`
unchanged; smoke-generated `is-en` again with real `espeak` audio.

**Third pass (PR #52 review): the cue was tied to B, but not to the pair.**
The owner agreed the blocker from the second pass was fixed, then found a
narrower one still open: `partner_cue` only proves the line is good
context *for B* — nothing stopped `_connect_pair()` from choosing a
completely different, unrelated A and still playing B's cue after it. For
the real authored example, `gaetirdu_endurtekid_thetta`'s cue is written
specifically to follow `gaetirdu_talad_haegar`; paired after some
unrelated item instead ("Hvað þýðir þetta?" → "Auðvitað. Herbergið er
númer tuttugu og þrjú." → ...), the exchange stops making sense, even
though "the cue fits B" was still technically true. The documented
invariant — "A → partner_cue → B reads as one real exchange" — was not
actually encoded anywhere; only "partner_cue fits B" was.

**Fix.** Added `Item.partner_cue_after: str = ""` — the one item id a
`partner_cue` is written to follow. `Builder.connect()` now uses the cue
only when `second.partner_cue_after == first.id`; anything else falls
back to the ordinary English bridge, exactly as if no cue existed.
`validate()` requires the two fields set together (or neither) and that
`partner_cue_after` names a real item, so an author can't accidentally
leave a cue with no declared predecessor (which would otherwise just go
permanently unused, a silent dead end rather than a caught mistake).
`gaetirdu_endurtekid_thetta` got `partner_cue_after = "gaetirdu_talad_haegar"`.
Left `_connect_pair()`'s own selection logic untouched — its existing
same-topic preference (both items share `topics = ["clarifying"]`)
already makes this specific pairing likely without needing to teach it
about cue compatibility too; the owner was explicit either approach
(prefer compatible pairs, or select as before and check after) was fine,
and the simpler one carries less risk to the rest of `_connect_pair()`'s
already-delicate heuristics.

**Tests**, matching the owner's own requested shape: rewrote the "cue
used" test to call `Builder.connect()` directly with two cases — `[a,
b]` (compatible: `b.partner_cue_after == a.id`) uses the cue; `[c, b]`
(same `b`, unrelated `c`) does not, falling back to `connect_then`
instead. Calling `Builder.connect()` directly (not through the whole
planner, as the second pass's test did) gives full control over which
item lands in which slot — the planner alone can't guarantee that.
Added `test_connect_plays_the_owners_real_curriculum_worked_example`,
which pins the exact real-content exchange the owner gave, verbatim.

126 tests (125 → 126), all passing; `audiolesson validate` unchanged;
smoke-generated `is-en` again.

**Still open for #48 itself**: the investigation above covers most of the
acceptance criteria already via #26/#44, and this pass closes the
`connect()` gap specifically, but #48 as a whole stays open — no attempt
yet at auditing whether *every* dialogue's progression is as good as
`nagranni`'s, whether "recent vocabulary reused in complete interactions"
holds broadly (only `do_connect`'s own two items were addressed here, not
whether dialogues get preferentially wired to freshly-introduced material
as reliably as the owner would want), or the 6 of 31 dialogues whose first
turn has no partner `opener` (so their very first exposure is still
learner-initiated, cued by English, even at full replay) — noted, not
touched, since having *some* learner-initiated dialogues (asking a
stranger for directions, ordering food) isn't necessarily wrong and #48's
own criteria only ask for *at least one* fully native-initiated episode,
which the other 25 already provide.

## Session 26: issue #29 resumed, cluster A (numbers/money) — with #48's conversational lens applied

The owner asked to resume #29's one remaining item (cluster A, numbers/money —
flagged at the end of session 23 as needing its own dedicated pass) and,
explicitly, to newly weigh each piece of new content against whether it meets
#48's conversational bar (partner-voiced, coherent exchanges — session 25),
not just #29's own "generate from parts" bar. Gave a five-phase roadmap;
this session is phase 1 (numbers/money vertical slice) only.

**Basic cardinal numbers, repositioned.** 1–12 were split across two modules
that both come *after* module 03 (the café dialogues, which already mention
prices in free text) — 1–4 lived with the clock-hour items in module 06, 5–12
lived in module 08 itself. Relocated all twelve into module 02, ahead of
their first real use, in counting order. Relocation is id-based everywhere
that matters (prereqs, tags, dialogue `requires`), so this only changes
`order`, confirmed by grepping every cross-module reference before moving
anything. Picked up one small pre-existing bug opportunistically while
touching the four neuter clock-hour items for reuse (see next paragraph):
`klukkan_er` resolved to "It's three (o'clock) o'clock." — the hour word's
own `meaning` carried a redundant "(o'clock)" the wrapper sentence already
supplies. Trimmed to "one"/"two"/... to match how 5–12 were already worded.

**Gendered forms.** Icelandic's 1–4 (only) inflect for the gender of the noun
they count; 5–12 don't. The existing `godur_noun`-era digits (module 06's
neuter clock hours: eitt/tvö/þrjú/fjögur) are also the correct neuter forms
for counting neuter nouns, so they were reused directly — adding
`gender = "neut"` and a `big_count` tag — rather than authored a second time
under new ids (`validate()` rejects two items sharing a `target`). Added the
missing feminine set (`ein`/`tvær`/`þrjár`/`fjórar`, tag `small_count`) since
króna (Iceland's currency) is feminine and nothing feminine existed yet. The
already-existing masculine set (einn/tveir/þrír/fjórir) stays as counting
words on their own (an isolated `[[notes]]` entry is their only reference)
but doesn't participate in either money construction below — money is never
counted in the masculine form.

**Amount constructions — and where gender agreement stopped short of a real
model.** Two of the curriculum's seven "price" items used to be whole
fixed-phrase amounts (`fimm_hundrud_kronur`, `tvo_thusund_kronur`, ...) —
exactly the pattern #29 exists to fix. Two real constructions now generate
amounts from independently-known parts instead, mirroring `godur_noun`'s own
shape (session 23) applied to numbers:

- `thad_kostar_big`: `"Það kostar {count} þúsund krónur."`, `count` tagged
  `big_count` (5–12 plus the neuter 1–4) — 12 possible fills, all verified
  correct by direct `resolve_slots()` comparison against the pre-existing
  fixed phrases they overlap with.
- `einn_tvo_thrjar` (upgraded from a fixed phrase, same id/situation/
  meaning framing as the phrase-to-construction pattern session 23 used for
  `godur_matur` → `godur_noun`): `"{count} krónur."`, `count` tagged
  `small_count` (the new feminine set) — bare nominative label, deliberately
  *not* wrapped in "Það kostar" (see below).

Two real agreement gaps surfaced while building these, both caught by
direct `resolve_slots()` inspection before they could reach a test, both
handled by **descoping the unsafe case rather than modeling it**, matching
this project's standing preference for correctness over completeness:

1. **"hundrað" doesn't pluralize like "þúsund".** Icelandic pluralizes
   "hundrað" → "hundruð" for any count but one ("fimm hundruð", not "fimm
   hundrað") — a genuine number-agreement dimension distinct from the
   `Item.gender`/`Item.agreement` mechanism (hardcoded to
   masc/fem/neut), which can't represent it without a new mechanism.
   `thad_kostar_big` was first drafted as a *two*-slot construction
   (`{count} {unit} krónur`, `unit` = hundrað or þúsund); resolving it for
   "hundrað" produced "Það kostar tvö hundrað krónur." — wrong. Rather than
   build singular/plural modeling under this pass's scope, dropped "hundrað"
   from the pool entirely and folded "þúsund" into the fixed template text
   instead of a slot — amounts in hundreds stay the pre-existing fixed
   phrases. This also matters structurally: a `unit` slot with only one safe
   filling would have failed `test_directory_curriculum_loads_and_is_large`'s
   standing invariant that every construction slot have at least two possible
   fills (so recombination is never a false promise) — caught by that test
   directly, not just reasoned through.
2. **"ein" (feminine "one") needs a singular noun, but the construction's
   text is plural-fixed.** `einn_tvo_thrjar`'s target is the fixed text
   `"{count} krónur."` (plural); "one" specifically would need "Ein króna."
   (singular), not "Ein krónur." — the same number-agreement gap as above,
   on the noun this time instead of the hundreds word. Fix: "ein" carries no
   `small_count` tag, so it's never chosen as this construction's fill; kept
   as an ordinary vocab item (still useful — the point of teaching gendered
   forms at all is recognizing "ein" belongs with feminine nouns generally,
   not only as this one construction's slot filler).
   A third, unrelated grammar risk was caught and designed around before it
   ever became content: `"Það kostar {count} krónur."` (wrapping the
   feminine counts in the case-governing "Það kostar" frame, as `thad_kostar_
   big` does) would need the *accusative* forms (accusative "eina" differs
   from nominative "ein" for exactly the singular) — not modeled, and not
   worth adding for one construction. `einn_tvo_thrjar` sidesteps this
   entirely by staying a bare nominative label ("{count} krónur.", no
   "kostar" frame) — the same shape its original fixed-phrase form already
   safely used ("A toy coin game with a child: say 'two krónur'.").

**Novel amount generation — verified, not just structurally assumed.**
Simulated 150 lessons on the real `is-en` curriculum (`apply_to_learner()`,
matching session 25's own verification method). Both constructions get
introduced (lesson 84 and 86 respectively at a 20-minute pace) and then hit
recall's `hinted`/`meaning`/`situation` stages and the `generative`/
`recombine` stage repeatedly, producing genuinely distinct never-authored
sentences across the lessons that followed — "Það kostar sjö þúsund
krónur.", "tólf krónur.", "fjórar krónur.", and so on — all independently
grammar-checked by eye against the reasoning above (never "ein", never
"hundrað" in a generated amount).

**Applying the #48 lens — a real latent bug caught, and a claim to keep
honest.** Applying #48's own bar (does this read as a coherent voiced
exchange, not just isolated recall) surfaced a genuine, previously-latent
bug in
`do_connect()` itself, not just a gap in new content: `_connect_pair()`
(planner.py) picks `connect()` candidates by `Item.has_situation` alone —
it never filtered by `kind`, and a construction can have a `situation` the
same as any phrase (`einn_tvo_thrjar` always did, even as a plain fixed
phrase, before this session's upgrade). `Builder.connect()` spoke
`item.target` directly — for a construction that's an *unfilled template*
("{count} krónur."), never resolved. `recall()`/`_recall_construction`
always resolves a construction's slots before speaking it; `connect()`
never did, because until this session no construction with a `situation`
had ever been built. Fixed by adding `Builder._connect_target()`, mirroring
`_recall_construction`'s own `generate()` → `example_fill()`+`resolve_slots()`
fallback chain, and calling it for both halves of a `connect()` pair. Caught
before it could ship by directly exercising `Builder.connect()` on
`einn_tvo_thrjar` paired with `hvad_kostar_thetta` ("Hvað kostar þetta?" →
"tvær krónur.", the correct feminine form, entirely voiced, no raw
template) — and confirmed the same fix also silently repairs a pre-existing
exposure for `talar_thu` (`"Talar þú {language}?"`, already in the
curriculum from an earlier pilot and already eligible for `connect()` before
this session touched anything), which would have spoken the raw template
had `_connect_pair()` ever actually picked it. Added
`test_connect_resolves_a_construction_instead_of_speaking_its_raw_template`
(synthetic curriculum, isolated from real-content specifics) pinning the
general mechanism.

**What this proves, and what it doesn't (owner review on PR #53):** the
worked example above ("Hvað kostar þetta?" → "tvær krónur.") is two
learner-produced answers inside `connect()`, separated by instructor
scaffolding — it proves the new construction is *safe to use in connected
practice* (no raw template leaks), not that it's *already exercised inside
a coherent partner-driven café/payment transaction* (a real dialogue turn,
with a partner reacting to a price). Those are different claims; only the
first is established here. The second — the new number constructions
actually wired into a partner exchange, not just safely reachable by one
— is a real, useful next step for a future #48/#29 integration pass, not
something this session's work already delivers.

**Not done, out of this pass's scope:** singular/plural (as opposed to
gender) agreement remains unmodeled — "hundrað" stays a fixed-phrase-only
word, and nothing generates amounts under 100 with "ein" or over 100 with
"hundrað". Phase 1's own roadmap treats this as acceptable descoping, not a
gap to close now; revisit only if a future #29 pass specifically wants
hundreds-scale generation.

127 tests (126 → 127); `audiolesson validate` unchanged (1006 items, 25
advisory dialogue-sequencing pairs, same as entering this session — this
pass touched grammar correctness and positioning, not sequencing).

**Correction (owner review on PR #53): "triage item (1) fully closed" was
premature.** The first pass above repositioned the *general* number system
but never re-ran the original cluster A checklist (`og`, `hundruð`/`krónur`,
`þúsund`, `sex`, `tvær`, `fjögur`, `erum`) against it — four of those seven
were still genuinely late, all catchable by `dialogue_sequencing_report()`
itself once checked directly rather than assumed fixed by association:

- **`fjögur`** (neuter "four" — the form module 03's own restaurant
  dialogue actually speaks, "Fjögur þúsund og fimm hundruð krónur.") was
  never relocated — only `fjórir` (masculine) was. The neuter clock-hour
  items (`eitt`/`tvö`/`þrjú`/`fjögur`) got their `gender`/`big_count` tag
  added *in place* in module 06 rather than moved, an oversight in the
  first pass's own relocation work, not a new gap. Fixed by moving all
  four into module 02 alongside the rest, id-based and risk-free exactly
  like every other relocation this session made — `klukkan_er` (module 06)
  is unaffected.
- **`og`** ("and") — a bare, no-prereq, difficulty-1 word sitting in module
  19, needed as early as `tuttugu og einn` (twenty-one) and this same
  restaurant line. Relocated to module 02.
- **`hundruð`** (the irregular plural of hundrað this pass's own
  `thad_kostar_big` note already explains isn't generated) — its only
  source was the seven fixed whole-amount price phrases
  (`fimm_hundrud_kronur` etc.), still sitting in module 08. Relocated six
  of the seven to module 02, unchanged otherwise — deliberately *not*
  solved by inventing a new decontextualized "hundruð" vocab item, which
  would have been exactly the shape of fix `dialogue_sequencing_report()`'s
  own docstring warns against (a patch instead of fixing the sequencing at
  the source); the fixed phrases already are the source, just badly
  placed. (The seventh, `fimmtan_hundrud_kronur`, stayed in module 08 —
  see the correction right below; this bullet already reflects that
  fix, not the original all-seven move.)
- **`erum`** ("we are") — flagged specifically via the `tynd` (lost)
  dialogue's "Já, sjáðu: við erum hérna..." partner line. The narrow gap
  (this dialogue's own earliest exposure to the word) is closed by
  relocating `vid_erum_fjogur` ("Við erum fjögur.", a café party-size
  phrase, itself topically part of cluster A and zero-prereq) to module
  02. The owner separately raised a broader question — a genuinely
  reusable "to be" conjugation paradigm, not just this one fixed phrase —
  which stays **explicitly out of scope**: `vid_erum`/`vid_tolum`/etc.
  (module 20) are a real, bigger, bigger-than-numbers grammar question,
  for #29's still-not-started items 2 (curriculum-wide audit) or 3
  (case/tense/modality pilot), not this cluster's relocation-only fix.

All four re-verified directly against `dialogue_sequencing_report()`
(`gap_threshold=0`, not just the default-100 summary) rather than assumed
fixed: none of `fjögur`/`og`/`hundruð`/`erum` appear in its findings
anymore. 25 → 18 advisory pairs (default threshold); the repeat-offender
word list is down to `bara` alone (unrelated to cluster A). 127 tests,
unaffected — every fix here is a pure relocation, same as the rest of this
pass. The general lesson, not just this specific fix: "the general shape of
a class of items moved" is not the same claim as "every specific named item
in the original list was re-checked" — re-verify against the literal
original findings before declaring a triage item closed, not just against
the class of problem it named.

**Second correction, same session (owner review): moving all seven price
phrases as one block was the same mistake at a smaller scale.** The
`hundruð` fix above relocated all seven fixed whole-amount phrases to
module 02 together, checked only as a class ("these are all cluster A
vocabulary") rather than item by item. `fimmtan_hundrud_kronur`
("fimmtán hundruð krónur", fifteen hundred krónur) names "fimmtán"
(fifteen) — a teen number outside the 1–12 range this pass moved, still
taught in module 08. Moving the phrase to module 02 taught it *before*
the standalone "fimmtán" it's built from: exactly the ordering #29's
capability-first principle rules out, on a smaller item than the
`fjögur`/`og`/`erum` mistakes above but the identical failure mode —
treating a group of similar-looking items as one relocatable unit instead
of checking each one's own components against what's already taught by
that point. Left `fimmtan_hundrud_kronur` in module 08, right after
`fimmtan` itself; the other six phrases (`fimm_hundrud_kronur`,
`thusund_kronur`, `tvo_thusund_kronur`, `thrju_thusund_kronur`,
`fimm_thusund_kronur`, `tiu_thusund_kronur`) use only count words already
in module 02's 1–12 range plus `þúsund`/`hundruð`/`krónur`, so they stay —
now with that check made explicit in the comment rather than assumed.
`hundruð`'s own sequencing fix is unaffected: `fimm_hundrud_kronur` (still
in module 02) remains its earliest exposure, so the gap stays closed.
18 advisory pairs, unchanged; 127 tests, unaffected. Same lesson as the
correction above, one level more specific: a relocation is only as sound
as the check behind *each* item moved, not the check behind the group it
was pattern-matched into.

**Third correction, same session (owner question): the "other six stay"
call above was still the group check, just a smaller group.** The owner
asked directly whether `thusund_kronur`/`tvo_thusund_kronur`/
`thrju_thusund_kronur`/`fimm_thusund_kronur`/`tiu_thusund_kronur` could
also move back to module 08. Checked each one's actual necessity in
module 02 directly against `dialogue_sequencing_report`'s own
`word_to_items` table (not the "these six pass the capability-first
check" reasoning the second correction stopped at): every word these five
contain — þúsund, tvö, þrjú, fimm, tíu, krónur — already has an *earlier*
standalone source in module 02 regardless of where these five phrases
themselves sit (e.g. "þúsund"'s earliest item is the standalone `thusund`
at order 112, not `thusund_kronur` wherever it lives). Only
`fimm_hundrud_kronur` is actually load-bearing — it's the sole source of
"hundruð" anywhere in the curriculum, which is exactly why the `hundruð`
gap existed in the first place. Moved all five back to module 08, in
their original ascending-amount order alongside `fimmtan_hundrud_kronur`;
`fimm_hundrud_kronur` is now the *only* one of the original seven price
phrases living in module 02. 18 advisory pairs, unchanged (as expected —
none of these five were closing anything); 127 tests, unaffected. The
lesson compounds across all three corrections this session: "passes a
check" is not the same as "needs to be here" — a relocation should
answer the second question specifically, not stop at the first.

## Session 27: issue #29 — cluster B remainder (hef verið / er að / leggja af stað / held ég)

Resumed #29's own priority order, phase 2 of the owner's roadmap: the four cluster B items
still open after `verð að + infinitive` closed in PR #47/session 23 (`eg_verd_ad`). Source of
truth was #29's own triage comment (not re-derived): `gonguferd` needs `leggjum`/`stað`
("leggjum af stað", let's set off) and `held` ("held ég", I think); `leigubill` needs
`áður`/`verið` ("hef verið hér áður", have been here); `stefnumot` needs `koma` ("er að koma",
I'm coming). Re-ran `dialogue_sequencing_report(gap_threshold=0)` directly against current
state first (module positions had shifted since the original triage from sessions 26's cluster
A work) rather than trusting the original gap numbers — all four still genuinely open, 517–611
gap.

Per item, following the "construction if the content genuinely supports it, plain relocation
with the reasoning written down if not" discipline cluster A established:

- **`leggja af stað`**: relocated `hvenaer_leggjum_vid_af_stad` (module 25 → 06, right after
  `hittumst_klukkan`, which the same dialogue turn pairs it with). Not a construction — "leggja
  af stað" conjugates by person, but this is the only instance of it anywhere in the curriculum;
  a one-fill slot would fail the same "≥2 possible fills" invariant `thad_kostar_big` hit in
  cluster A.
- **`held ég`**: the one item that took real investigation. The flagged item, `eg_held_thad`
  ("Ég held það.", I think so), doesn't actually match `gonguferd`'s own usage —
  the dialogue's line is a sentence-*final* hedge tacked onto a statement ("Rigning og rok, held
  ég.", rain and wind, I think), not the standalone initial-position answer `eg_held_thad`
  teaches. Relocated `eg_held_thad`/`eg_held_ekki` (module 24 → 07) for their own sake
  (genuinely useful, zero-prereq, no reason to sit at order 917). That closes the *token* gap for
  "held" in `dialogue_sequencing_report`, but not the *capability*: the reusable thing is the
  relation "X, held ég." (any statement + hedge), and the construction mechanism fills a slot
  from a tagged pool of words/short phrases — it can't yet slot a whole clause.

  **Correction (owner review on PR #54):** the first cut added `rigning_og_rok_held_eg`
  ("Rigning og rok, held ég." — the dialogue's own line, verbatim) as a new fixed phrase. Removed:
  that is the exact direction #29 exists to avoid — dialogue line → find what's missing → pre-teach
  that finished sentence as a memory item. It cleans up the diagnostic without giving the learner
  any reusable model. "The current IR can't represent the capability yet" is a representation gap,
  not evidence the hedge is lexicalised, and must not be papered over as if it were. So, stated
  separately and honestly:

  - sequencing gap for the `held` token: **improved** (gone from the findings);
  - reusable `X, held ég` capability: **not yet modeled** — left open for #29's grammar /
    construction pilot (item 3), alongside "vera að + inf" below. A smaller alternative the owner
    noted, treating `held ég` itself as a discourse chunk, is also possible but not attempted.
- **`hef verið`**: relocated `eg_hef_verid_her_adur` (module 20 → 05, right before `leigubill`).
  Checked whether this was a genuine construction candidate (per #29's own triage: "hef verið...
  a reusable 'have been' construction") and concluded no: the only other "hef + participle"
  example in the curriculum, `eg_hef_aldrei_smakkad_thetta` ("I've never tasted this"), takes a
  direct object where this one takes a place adverbial — too little shared shape for one clean
  template without forcing it.
- **`er að koma`**: relocated `eg_er_ad_koma` (module 20 → 06, right before `stefnumot`).
  This one got the deepest look, since #29's triage explicitly flagged it as construction-shaped
  and the curriculum already has real precedent — `eg_er_ad_laera`/`eg_er_ad_leita_ad` are
  themselves single-slot "vera að" constructions, and module 02's "inf"-tagged vocabulary pool
  (built for `eg_verd_ad`) has 14 candidate fills that are all grammatically valid after "er að"
  too (Icelandic uses the same bare infinitive after both "verða að" and "vera að" — no separate
  gerund). The blocker is English, not Icelandic: that pool's `meaning` fields are worded for
  "have to {inf}"/"want to {inf}" ("go home", "sleep", "buy a ticket" — bare infinitive), and
  `resolve_slots()` only does literal string substitution, so filling a progressive template
  ("I'm {inf}.") with them reads as "I'm go home." — broken English, not a shortcut worth taking.
  A real fix needs either new gerund-shaped meaning fields or a second English form per `inf`
  item, which is a real mechanism question, not a relocation — left for #29's still-open
  case/tense/modality grammar pilot (phase 4 of the owner's own roadmap) rather than attempted
  here. Also found, via the same word-matching audit, that `eg_er_ad_leita_ad_vinnu`
  (`dagurinn`/"vinnu", gap 245) has the same shape — deliberately **not** touched: the original
  #29 triage explicitly filed this under "remaining singles — lower priority... not flagged for
  action now," and cluster B's own scope (per the owner's phase list) is the four items above,
  not everything sharing a word with "er að". Left for the curriculum-wide audit.

Verified all four directly against `dialogue_sequencing_report(gap_threshold=0)`: `leggjum`/
`stað`/`held` gone entirely from the findings; `áður`/`verið` down from 538 to 2; `koma` down
from 517 to 16 (both now comfortably inside the dialogue's own base, not zero only because
another item in the same small gap band pushed order by a couple of positions — not a concern).
`eg_er_ad_leita_ad_vinnu`/`vinnu` unchanged at 245, as intended. 18 → 11 advisory pairs; 127
tests, unaffected (every change here is a pure relocation, no mechanism changes).
`audiolesson validate`: 1006 items, unchanged (after the correction above removed the one new
item the first cut added).

**Status, stated plainly:** cluster B's *sequencing findings* are addressed (all four tokens'
gaps closed or near zero), but not all of cluster B's *capabilities* are: `leggja af stað` and
`hef verið` stay fixed phrases (reasoned above), and `X, held ég` (sentence-final hedge) and
`vera að + infinitive` (progressive) are reusable patterns that remain **unmodeled** — both are
representation gaps left for #29 item 3, not closed cases.

## Session 28: issue #55 — connect()'s fallback pair was replayed all lesson

A real Lesson 4 played `connect: ha+eg_skil` ("Ha?" → "And then —" → "Ég
skil.") over and over. Mechanism: `_connect_pair()` always took the first
eligible same-topic pair and had no lesson-level history, so every time the
drill streak tripped, `do_connect()` re-picked the identical pair — "monotony
detected → play the same canned exchange → monotony detected again". A
10-lesson `is-en` simulation before the fix showed the same pair up to 11
times in one lesson (`godan_daginn+takk`, `eg_heiti+hvad_heitir_thu`, ...).

**Fix (planner.py, `build()`'s connect helpers).**
- `connect_pairs_used` (unordered pairs) and `connect_item_uses` are kept per
  lesson; `_connect_pair()` never returns a pair already played. Unordered on
  purpose: "A then B" vs "B then A" is the same two recalls to the learner.
- Among unused pairs it ranks: (0) an authored `partner_cue` pair
  (`b.partner_cue_after == a.id`, played in authored order — a coherent
  exchange per #48), (1) a shared first topic, (2) anything else; ties broken
  by fewest earlier connect() appearances of the two items, so "fresh pair"
  doesn't just mean the same item with a new partner.
- `do_connect(prefer=arc)` widening beyond the arc's own items now passes an
  `anchor`: the widened pair must still contain one of that arc's items.
  Previously a same-topic pair of unrelated review items could outrank the
  arc's own item and be replayed for every arc, "satisfying" each arc's
  connected-use guarantee without touching what it taught.
- Exhaustion needs no new branch: `do_connect()` returns `False`, and the
  streak breaker's existing cascade (dialogue → note → connect → deliberate
  stop) ends the lesson rather than looping back to a used pair.

Measured on the same simulation after the fix: zero repeated pairs, lesson
lengths within ±0.5 min of before (20- and 30-minute runs). A 30-minute lesson
can still play many connect() exercises (one had 22, all distinct) — that is
the streak breaker's existing frequency, not a repeat; left as is.

**Tests** (all four fail on the pre-fix code): the real Lesson 4 failure on
`is-en` (`ha`+`eg_skil` the only situation-ready items: played once, then no
loop-back, streak stays bounded); variety while unused pairs exist (all
distinct, first three pairs share no item); an authored pair beats an
earlier same-topic generic pair; each arc's connected use includes that arc's
own item. 131 tests, all passing.

## Session 29: issue #29 — capability-aware arc boundaries

The owner's latest #29 comment (real Lesson 4): the curriculum now models
reusable parts correctly, but an arc could still end *between* the parts
and the capability they unlock — six `acc_language` fillers (íslensku,
ensku, japönsku, þýsku, frönsku, dönsku) drilled as isolated words, lesson
ends, «Talar þú {language}?» never reached. New completion criterion:
parts → construction → novel generation → situated use, with only enough
fillers before the construction to make it recombinable and later fillers
arriving as transfer through it.

Measured first: 53 constructions; most families have the same shape (7–14
fillers, then the pattern — `inf` 12→`eg_vil`, `direction` 12, `time` 13,
`job` 9, `colour` 8, ...). Fixed generically in `Planner.select_new()`
rather than hand-reordering ~50 families:

- **Payoff** (`payoff()`): walking the pool, a filler whose slot already has
  two fillers met-or-chosen, with a construction for that slot within
  `PlanConfig.capability_window` (15) items after it, swaps in that
  construction when it's ready (prereqs learned or chosen, two usable fills).
- **Hold**: if that construction isn't ready yet (its fills/prereqs are met
  but not yet learned), the filler waits. Deadlock-free by construction: a
  hold only ever waits on a construction whose own prereqs are already met
  or chosen and don't include the held filler; a distant construction
  (outside the window) never holds anything. Verified no holes behind the
  frontier after 80 simulated lessons.
- **Transfer cap** (`transfer_capped()`): once a slot's construction is met,
  at most two of its remaining fillers per arc — otherwise the held block
  just came back later as a block of four.
- **Boundary**: if an arc's last pick is a filler whose nearby construction
  is now ready, the construction joins the arc (one over `count`); if it
  isn't ready (a lone filler), that filler is dropped to start the next arc
  with its siblings — only when the pattern is genuinely next and the arc
  isn't left empty. Step 5's single-extra path now queues anything
  `select_new(1)` returns beyond the first item, since a filler can come
  back with its payoff construction.

Real is-en course, 20-minute lessons: L6 now introduces `islensku ensku
talar_thu` and plays intro → "Talar þú íslensku?"/"Talar þú ensku?"
(generative) → situation within the lesson; later languages come two per
arc (`japonsku eg_tala ...`, `thysku fronsku ...`) and each is immediately
recombined through the known patterns ("Ég tala þýsku.", "Talar þú
þýsku?", "Ég er að læra þýsku."). `inf` verbs now arrive with `eg_vil` /
`eg_aetla_ad` rather than as a 12-verb block. Throughput unchanged (80
lessons: 336 vs 342 items met; 30-minute: 276 vs 268; fr-en-a1 identical).

Left alone deliberately: the masculine count words (einn/tveir/þrír/fjórir)
still arrive as a block — no construction uses them, so there's no payoff
to reach; and number fillers whose construction is far away (`big_count` →
`thad_kostar_big`, ~250 items later) are outside the window by design.

Tests (4 of 5 fail on the pre-fix code): synthetic payoff arc (`f0 f1 pat`,
no further fillers), boundary append/trim, hold-then-transfer-cap, a
no-starvation course guard, and the real `acc_language` → `talar_thu`
lesson with a novel generated sentence. 136 tests, all passing.

#29 still open for: (2) the curriculum-wide audit (fixed-phrase families
such as Gjörðu svo vel / Verði þér að góðu, `vid_erum` paradigm, `bara`),
and (3) the case/tense/modality pilot.

## Session 30: issue #48 — partner interaction in early lessons

Measured first (60 simulated 20-minute is-en lessons): lessons 1–8 — up to
52 items met, including the owner's real Lesson 4 — contained **no partner
target-language line at all**. Two causes:

1. The first dialogue (`nagranni`) needs `allt_gott`, whose prereq `takk`
   must be *learned* (durable) before `allt_gott` is even introduced, and
   `eligible_dialogue()` requires every item *learned* (or introduced
   earlier in the same lesson). That is #27's durable gate, working as
   intended — **not** changed (see the correction below).
2. The connect() fallback that does fire early had exactly one authored
   `partner_cue` in the whole course, so every early connect was English
   "And then —" narration.

**Content.** Authored 12 more `partner_cue`/`partner_cue_after` bridges (13 with
session 25's; the PR #56 text said "11" — a miscount, corrected in session 33)
among modules 01–02, each chosen so *both* lanes hold: target-language
turns form one exchange, and B's existing English situation still fits the
scene. E.g. `takk` → «Gjörðu svo vel. Eigðu góðan dag!» → `somuleidis`;
`eigdu_godan_dag` → «Takk, sömuleiðis. Bless!» → `bless`; `gaman_ad_sja_thig`
→ «Sömuleiðis! Hvernig hefurðu það?» → `eg_hef_thad_gott`; and the issue's
own pair, `ha` → «Morgunmaturinn er á fyrstu hæð.» → `eg_skil` (B's
situation is the receptionist explaining where breakfast is). Some partner
lines use words not yet taught (`morgunmaturinn`, `afmæli`) — deliberate: a
partner saying something the learner half-catches is the realistic case,
and B's instructor cue carries the meaning. Not native-reviewed.

**Planner.**
- `do_connect()` first looks for an authored exchange that includes at least
  one of its scope's own items (this lesson's, or the arc's), with the
  other half from any known material; only then the #55 ranking within the
  scope. Without this the scope-first search never reached `takk` (met two
  lessons earlier) while this lesson's items had any generic pair.
- `Builder.connect()` labels its exercise stage `exchange` (authored bridge
  used) or `recombine` (none) — #48's "recombination fallback ≠ coherent
  exchange". `sc.meta` gains `partner_exchanges` (dialogues + exchange
  connects) and `recombinations`.

**Correction (owner review on PR #56): the dialogue gate was a #27
regression, reverted.** The first cut also widened `eligible_dialogue()`
from `knows(i) or in_lesson` to `has_met(i) or in_lesson`, reasoning that
same-lesson items already counted and first encounters are assisted. But
that distinction is deliberate: #27 exists to stop "one presumed-successful
retrieval → treated as learned → dependencies unlock", and its acceptance
criteria put prerequisite/dialogue eligibility on durable evidence.
`knows() or in_lesson` already expresses exactly the intended rule — older
material needs durable evidence; material introduced earlier *this* lesson
is the same-lesson exception #25 allows. Widening it let an item introduced
once yesterday (`durable_successes == 0`) unlock today's dialogue, and the
first cut's test even asserted that. Reverted; the test now pins the gate
(met-but-not-durable → no dialogue; durable → yes; same lesson → yes).
Early partner interaction comes from the authored connect() exchanges
instead, which unlock nothing.

Result on the same simulation, with the durable gate intact: L2–L7 each
have 1–3 partner exchanges (L4 plays three: `hae+til_hamingju`,
`eigdu_godan_dag+bless`, `takk+somuleidis`); no dialogue plays in L1–L8.
**Not every lesson gets one:** L1 (six items) and L8 have none at 20
minutes, L5 and L6 none at 30 minutes — lessons whose own new items have
no authored bridge, once the scope-anchored exchanges are used up. More
bridges (beyond modules 01–02) are the lever for that, not the gate.
Throughput unchanged (80 lessons: 336 items met).

Tests (all fail on the pre-fix code except the gate test, which pins
existing behavior): exchange/recombine labelling, every authored cue
playable (both items have situations), L2–L6 of a real 20-minute course
each with a partner exchange plus the `ha+eg_skil` exchange shape, and the
durable dialogue gate. 140 tests, all passing.

Still open for #48: wiring session 26's number constructions into a real
partner-driven payment exchange; auditing each dialogue's progression the
way `nagranni` was audited; more authored bridges beyond modules 01–02.


## Session 31: issue #57 — a construction's situation and its generated fill disagreed

A real Lesson 4 narrated `talar_thu`'s situation ("You're not sure the
receptionist understands you. Ask if she speaks English.") inside connect()
and expected «Talar þú íslensku?» — grammatical, but not an answer to the
task. A construction's `situation` and its slot generation were independent:
nothing recorded that the situation names one specific fill.

**Fix.** `Item.situation_fill` (`{ slot = "item_id" }`, construction only):
the fill(s) the authored situation names. `Builder.generate()` takes
`fixed=` to pin slots; `_recall_construction` pins them at the `situation`
stage, and `_connect_target()` always does (connect() always narrates the
situation). Every other stage (hinted/meaning/recombine) generates freely, so
«Talar þú íslensku?» etc. still come up there — the issue's non-goal of not
collapsing to the worked example. `validate()` rejects a binding on a
non-construction, without a situation, to an unknown slot, to an unknown item,
or to an item lacking the slot's tag. Audited every construction with a
situation (only two in is-en, none elsewhere) — both name a fill and are now
bound: `talar_thu` → `ensku`, `einn_tvo_thrjar` ("say 'two krónur'") → `tvaer`.
Documented in `docs/CURRICULUM.md`.

**Tests** (the two behaviour tests fail on the pre-fix code): situation-stage
recall always «Talar þú ensku?» across 12 seeds while meaning/recombine vary;
connect() with `talar_thu` always «Talar þú ensku?» (the Lesson 4 path);
validation of bad bindings; and an authoring guard — a construction whose
situation mentions a fill's meaning ("English", "two") must bind that slot
(confirmed to fail with `talar_thu`'s binding removed). 143 tests, all
passing.

**Correction (owner review on PR #58): `fixed` bypassed the known-parts
invariant.** `generate()` only ever fills a slot from items the learner has
(`knows()` or introduced this lesson); the first cut's `fixed` path skipped
that check, so a situation bound to an unlearned fill ("Ask if she speaks
German." → `thysku`) could force «Talar þú þýsku?» — situation and answer
consistent, but built from a part the learner doesn't have. Fixed with
`Builder.situation_usable(item)`: a situation is usable only when every
bound fill is available. Otherwise `recall()` drops the situation stage to
`meaning` (as for an item with no situation) and generates from known fills;
the planner's `_connect_pair` never picks the item; and `Builder.connect()`
raises if handed one, rather than silently speaking an unlearned part. The
real bindings (`ensku`, `tvaer`) are both prereqs of their constructions, so
they are always available and nothing changes for them in practice. Tests
(both fail on the first cut): an unknown bound fill → `meaning` stage with no
þýsku generated, `connect()` refuses, and once þýsku is known the situation
and its fill are used; a streak-heavy planned lesson never pairs the
German-bound construction. 146 tests, all passing.

## Session 32: issue #29 — curriculum-wide audit, aspect / modality / case pilots

Picked up #29's two open items. Full status table and dispositions:
`docs/AUDIT-29.md`; this section is the narrative.

**Audit (item 2).** `tools/phrase_families.py` groups phrase items sharing a
two-word opening/closing frame and flags which frames a construction already
covers. Read as candidates, not verdicts (the 64 `ég er …` phrases share a
frame, not a pattern). Every family of ≥3 is sorted into the owner's three
dispositions — lexicalised chunk / later-productive / shared dimension — in
the audit doc, including the owner's own «Gjörðu svo vel / Verði þér að
góðu / Gangi þér vel / Eigðu góðan dag» family (no shared frame; checked by
hand: two lexicalised formulas, «Eigðu {adj+noun acc.}» a real transfer
target for `godur_gender`'s accusative, `þér` the dative pair of `mér`).

**Mechanism: `meaning_forms` + `{slot:form}`.** Session 27 found the
progressive blocked only on English: the `inf` pool's glosses are bare
infinitives ("go home"), and a progressive needs "going home". A fill can
now carry `meaning_forms = { ing = "going home" }` (glossed:
`meaning_forms_ja = { te = "家に帰って" }`), and a construction's meaning
asks for it with `{inf:ing}`. The Icelandic fill never changes (same bare
infinitive after «er að», «má», «vil»). `validate()` requires every possible
fill of that slot to carry the form. All 14 `inf` fills got `ing` and `te`.

**Pilots (item 3)**, each following `godur_gender`'s "familiar examples →
notice → name → discriminate → transfer":

- **Aspect:** milestone `vera_ad_progressive` over «Ég er að koma!», «Ég er
  að fara» (relocated module 11 → 06 as a third familiar example), «Ég er að
  læra íslensku», gating the new construction `eg_er_ad_inf` («Ég er að
  {inf}.» / "I'm {inf:ing}." / 「今、{inf:te}いるところです。」).
  `eg_er_ad_laera` gained a situation (bound to `islensku`) so the milestone
  discriminates between two different familiar examples.
- **Modality:** milestone `modal_infinitive` over `eg_vil`, `eg_verd_ad`,
  «Má ég borga með korti?», gating `ma_eg_inf` («Má ég {inf}?» / "May I
  {inf}?" / 「{inf:te}もいいですか？」). `eg_vil` / `eg_verd_ad` gained
  situations bound to `fara_heim`, so the discrimination right after the note
  is a real minimal pair: «Ég vil fara heim.» / «Ég verð að fara heim.», then
  «Má ég fara heim?».
- **Case:** milestone `dative_subject` — «Ég er svöng» (ég) vs «Mér er kalt /
  heitt» (mér, dative) — with «Mér líður vel / illa» as transfer items. Named
  and contrasted only; a productive `Mér líður {how}` needs new adverb vocab
  (audit doc, suggested order #1).

Verified on a simulated 110-lesson course (20 min): L31 plays `modal_infinitive`
→ «Ég vil fara heim.» / «Ég verð að fara heim.» → intro «Má ég {inf}?» →
hinted/meaning/recombine on other verbs → situation; the progressive milestone
fires at L72 and `eg_er_ad_inf` arrives at L77, then generates unauthored
sentences («Ég er að versla.», «Ég er að kaupa miða.»); `dative_subject`
fires at L80 followed by «Ég er svöng.» / «Mér er kalt.». Throughput unchanged
(80 lessons: 336 items met), no stranded items.

**Found, not fixed:** fill disambiguators leak into generated glosses — "May I
work (to work)?", "Do you speak Icelandic (the language)?" (pre-existing;
stripping globally would break "my friend (male)"/"(female)"; the per-item fix
is a `meaning_forms` entry, audit doc #3).

**Tests:** the `{slot:form}` mechanism (render, ja gloss, validation); every
`inf` fill reads correctly through both new constructions in both instructor
languages; the modality milestone precedes `ma_eg_inf` with the minimal pair and
novel verbs follow; the aspect milestone precedes `eg_er_ad_inf`. Two existing
tests widened for the new shapes (ja-gloss slot check accepts `{slot:form}`;
milestone discrimination accepts a construction recall carrying its fill as
support) — the discrimination test now also covers the three new milestones.
150 tests, all passing.

## Session 33: issue #48 — per-dialogue audit, more bridges, numbers in a transaction

Took #48's three open items from session 30. Status table: `docs/AUDIT-48.md`.

**Per-dialogue audit.** Printed every dialogue's target-language lane with the
instructor stripped and read all 31. Six had real problems, all fixed:
`veitingastadur` («Hérna er matseðilinn» — accusative after «er»; the nominative
isn't taught, so the clause was dropped), `straeto` («Hvar á ég að fara út?» →
«Allt í lagi.» didn't answer; now «Eftir fimm mínútur, við hliðina á bankanum.»),
`markadur` (the seller answered the ATM question with a line copied from
`gonguferd`), `heimsokn` (roles inverted: the guest said «Farðu úr skónum», the
host replied «Nákvæmlega» — the host says it now, the learner agrees with
«Hæ! Já, auðvitað.»), `ahugamal` («Viltu sjá eina?» → «Já, mér líkar það» was the
wrong response; now «Já, endilega!») and `myndir` (a self-correcting cue). All
replacement partner lines use only taught words, as
`test_dialogue_lines_stay_within_taught_vocabulary` requires. The `heimsokn` fix
also drops the «nákvæmlega» sequencing finding (11 → 10).

**More bridges.** 13 more authored `partner_cue` bridges in modules 02–03, chosen
where B's existing situation already fits (e.g. `hvad_kostar_thetta` → «Níu hundruð
krónur. Eitthvað fleira?» → `ekkert_meira_takk`). Lessons with no partner
exchange: 20-min L1 only (was L1, L8); 30-min none (was L5, L6). While counting,
found session 30 had added 12 bridges, not the 11 its PR text said — corrected.

**Numbers inside a partner-driven transaction.** `DialogueTurn.expect_fill`
(slot → item id, the dialogue counterpart of `situation_fill`) lets a turn expect a
construction: the line is resolved from the bound fill, the fill joins
`required_items` (so #27's durable gate covers it), and validation rejects bad
bindings. `Builder.dialogue()` also now resolves any construction turn instead of
speaking a raw template. New dialogue `solubas`: the learner minds a flea-market
stall and generates «Það kostar fimm þúsund krónur.» from `thad_kostar_big` + `fimm`;
the partner haggles back with «Fjögur þúsund?». A simulated course reaches it at
L87 (2/3 turns) and plays it in full at L92.

**Follow-up, same session (owner comment on #48):** target-language coherence is
necessary but not sufficient — a real Lesson 4 cued «Góðan daginn» as greeting bakery
staff, then played «Má ég setjast hérna?» and a cue about someone at *your table*: one
scene in the target lane, two in the instructor lane, and an untaught partner line with no
stated communicative move. Every bridge is now one authored scene on item B —
`partner_cue_setup` (replaces A's standalone situation), `partner_cue_meaning` (glosses
the partner line on the learner's first two hearings, tracked in the new, persisted
`LearnerState.bridges_heard` via `sc.meta["bridges"]`), `partner_cue_situation` (replaces
B's, naming the partner's move) — required together by `validate()`. All 26 bridges (13
already on main + 13 from this session) were audited by hand for both lanes and authored
in en/ja; several were re-scened (e.g. `endilega`: a shared café table instead of a
bakery counter; `eg_veit_ekki`: a stranger at a bus stop, not bakery staff, asks where the
bank is). The table is in `docs/AUDIT-48.md`. Tests: the owner's failure shape as a
fixture (both lanes pinned, no bakery narration inside the bridge), gloss fading plus the
planner's `bridges_heard` bookkeeping, and scene-field validation (all fail pre-change).
154 tests, all passing; throughput and partner-exchange coverage unchanged.

**Tests:** `expect_fill` (resolution, required items, three validation failures);
the real `solubas` lane pinned verbatim; no dialogue on the course ever speaks a
`{slot}` placeholder (all three error on the pre-fix code). 153 tests, all
passing. Throughput unchanged (80 lessons: 336 items met).

## Session 34: issue #59 — cloze prompts didn't say what to complete

A real lesson played "Complete the sentence." + «Ég skil…» — but «Ég skil.» is itself a
complete, known utterance, so nothing told the learner the target was «Ég skil ekki.»;
«Gott að…» likewise left several completions open. The prompt gave only the partial surface
form, never the communicative intent, turning the task into a test of remembering the
course's sentence inventory.

**Fix.** The `cloze` phrasing now takes `{meaning}`, like `hinted` already did: "Complete the
sentence to say: I don't understand." / 「「わかりません」と言うように、文を完成させてください。」,
then the partial phrase. Only the narration changed — the partial, the answer and every pause
(and its duration) are identical to before, checked segment by segment on the two real cases.
Cloze practice itself stays (the issue's non-goal).

**Tests:** the two real cases (`eg_skil_ekki`, `gott_ad_heyra`) in both instructor languages,
meaning narrated before the partial; and a course-wide guard that every cloze-eligible phrase's
prompt contains its meaning (both fail on the pre-fix code). 148 tests, all passing.

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
   *(Superseded, kept as history: the generative half of pilot 2 was done
   in session 23 (`godur_noun`), and that word list in sessions 23 and 26
   except `bara`. Current #29 status is the "Open issues" block at the top
   of this file.)*
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
