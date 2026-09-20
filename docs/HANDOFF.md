# Handoff note — audiolesson

_Last updated 2026-09-20 (session 15: the owner closed #23 and #25,
folding both into #29 — one consolidated top-priority issue for
designing curriculum sequencing from learner capabilities outward,
covering both reusable vocabulary and grammatical dimensions. Docs
updated to point at #29, then a first concrete pilot: the `fara`/"want
to, going to" construction cluster moved from module 14 to module 2 —
see item #1 in "Known gaps" for what's still open)._ Keep this current:
whoever picks the project up next, human or AI, should be able to
continue from here without re-deriving decisions._

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
   15):** the `fara`/"want to, going to" cluster — an already-built
   `tags = ["inf"]` vocab set plus 4 generative constructions — moved
   from module 14 to module 2; `dialogue_sequencing_report()` no longer
   flags `fara`/`viltu` (see "Pilot 1" above). **Not started:** the
   `góðan`/`góða`/`gott` gender-agreement teaching moment, the two other
   `fara`-shaped constructions in `06-time.toml` noticed but out of
   scope for pilot 1, and the broader curriculum-wide audit.
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
