# Design notes

What a contributor, human or AI, needs before changing the planner or the curriculum:
where things are, what the tests hold in place, and why the big decisions went the way
they did. Open work is tracked in GitHub issues; the full history of how each of these
came about is in `docs/history/sessions.md`.

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

Each of these was a real regression once; `docs/history/sessions.md` has the details.

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
