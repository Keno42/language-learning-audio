# Handoff note — audiolesson

_Last updated 2026-09-23. Keep this file true to the current state: whoever picks the
project up next, human or AI, should be able to continue from here without re-deriving
decisions. The full history (sessions 2–40: what was tried, what review rejected and why)
is in `docs/history/sessions.md`._

## What exists

`audiolesson generate` plans a lesson from a curriculum and a learner state, writes a timed
script, plan and transcript, renders audio through a pluggable TTS layer, and updates the
learner model. Usage and layout are in `README.md`; the curriculum format is in
`docs/CURRICULUM.md`.

- **Curricula:** `curricula/is-en/` (Icelandic, 26 modules: 1012 items, 32 dialogues,
  53 notes, English and Japanese instructor glosses), `curricula/fr-en-a1.toml` and its
  derived Japanese-instructor twin `fr-ja-a1.toml` (small French sample; most tests use it).
  None of the content is native-reviewed.
- **Tests:** `python -m unittest` (166 tests; one skips without espeak-ng/ffmpeg). CI also
  validates `curricula/is-en` and renders short espeak lessons from each curriculum.
- **TTS:** only `stub` and `espeak` run in CI. `edge`, `openai` and `say` are exercised only
  by hand.

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
| diagnostics | `audiolesson validate` (gloss coverage, dialogue sequencing report), `tools/phrase_families.py` |

## Invariants the tests pin

Each of these was a real regression once; the history file has the details.

- **Durable learning (#27).** `LearnerState.knows()` means two recalls on or after a due
  date. Recalls minutes apart in one lesson don't count. Dialogue eligibility is
  `knows(i) or i in builder.in_lesson` for every required item, never `has_met`.
- **Generated sentences use only available parts.** A fill is known or introduced earlier
  in the lesson. A construction's `situation_fill` makes its situation wait for that fill.
  A dialogue turn's `expect_fill` binds every slot, so every spoken part is a required item.
- **No skipped stages.** `connect()` records a situation exposure only for an item that is
  at most one step short of `situation` on its own ladder (`_ready_for_situation`).
- **A drill streak never falls through to another isolated recall.** Step 0 tries a
  dialogue, then a note (with a small separate relief allowance), then `connect()`, and
  otherwise ends the lesson.
- **`connect()` is honest about what it is.** It's an `exchange` only with an authored
  bridge (`partner_cue_after`), played as one scene. Otherwise it's `recombine`, with a
  neutral transition. It never replays a pair within a lesson.
- **Novelty is claimed only when true.** `recombine_new` requires `is_new_utterance()`:
  not presented this lesson, in an earlier lesson (`heard_utterances`), or as a met item's
  target.
- **Notes.** Milestones fire deterministically once their `items` are met or exposed, and
  are followed by discrimination practice. A note waits for what it recommends saying
  (`requires`). No aside repeats while an ordinary one is unheard.
- **Content guards.** `progressive_inf` holds only verbs audited for «vera að» + infinitive
  («sofa» is excluded). Dialogue partner lines use only taught words. No fill-borne
  parenthetical leaks into a sentence prompt (`meaning_forms.in_sentence`).

## Open issues

Only #29 and #48 are open. Their status tables live in the audit files; keep those current.

- **#29 — curriculum around reusable concepts and capabilities.** `docs/AUDIT-29.md` has
  the fixed-phrase family scan with dispositions, the grammatical-dimension table and the
  suggested order. Keep *sequencing finding addressed* separate from *capability modeled*.
  - Modeled so far: gender (`godur_gender` + transfer onto `godur_noun` and
    `eigdu_godur`), aspect (`eg_er_ad_inf` over `progressive_inf`) and modality
    (`ma_eg_inf`). Case (dative «mér») is named and contrasted, but not productive.
  - Remaining: a productive case construction (`Mér líður {how}.`); tense and person
    pilots; category-2 families (`Takk fyrir`, `Hvenær fer`, `… virkar ekki`, `Ég á`);
    growing the `inf` pool so the constructions absorb their fixed siblings.
  - Also remaining: owner confirmation of the capability-aware arc boundaries
    (`select_new`) on real generated output.
  - Deliberately unmodeled: number (hundrað/hundruð), and `X, held ég`. The latter needs
    a clause slot the construction IR doesn't have.
  - `audiolesson validate curricula/is-en` currently reports 10 advisory dialogue/word
    pairs.
- **#48 — from isolated recall to end-to-end conversation.** `docs/AUDIT-48.md` has the
  per-dialogue audit and the 26 authored bridges (modules 01–03).
  - Remaining: bridges beyond module 03; shorter scene cues once a bridge is familiar
    (only the partner gloss fades now).
  - Also remaining: partner lines that still quote hundreds or teen amounts as fixed
    text; five dialogues whose learner turns are all `expect_text`.

## Other known gaps

- `do_discriminate()` gives two contrast recalls only when a milestone has at least three
  items with a situation. Every current milestone does. Before adding a smaller one,
  either validate that minimum or give `Note` an explicit strategy, and test it.
- Two dialogue asks from issue #22 are still undecided: a line announcing that a
  dialogue starts, and dialogues that need no translation at all.
- Lesson 1 opens with two or three introductions in a row, because nothing exists to
  review yet.
- `between_exercises` and `beat` pauses haven't been tuned by listening. `answer_pause`
  and `repeat_pause` have.

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

## How to check your change

```sh
python -m unittest -v
python -m audiolesson.cli validate curricula/is-en
python - <<'EOF'
# ten-lesson simulation: one line per lesson, letters = exercise kinds
# o opening, i intro, r recall, g generative, c connect/closing, d dialogue, n note
from datetime import date, timedelta
from audiolesson.content import load_curriculum
from audiolesson.learner import LearnerState
from audiolesson.prompts import Prompts
from audiolesson.timing import Timing
from audiolesson.planner import Planner, PlanConfig, apply_to_learner
cur = load_curriculum("curricula/is-en"); ls = LearnerState("is", "en"); d = date.today()
for _ in range(10):
    sc = Planner(cur, ls, Prompts.load("en"), Timing(level="A1"), PlanConfig(minutes=20), today=d).build()
    apply_to_learner(sc, ls, d); s = sc.summary(); d += timedelta(days=1)
    print(f"L{sc.lesson_number}: {s['duration_s']/60:.1f}min new={len(sc.meta['new_items'])} "
          f"rev={len(sc.meta['reviewed_items'])} partner={sc.meta['partner_exchanges']} " + "".join(e.kind[0] for e in sc.exercises))
EOF
```

For a change meant to be behaviour-neutral, dump a few simulated courses' scripts to JSON
before and after, and compare them.
