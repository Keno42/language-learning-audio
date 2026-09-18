# language-learning-audio

Generates **audio-first language lessons** you can follow while walking, driving or
cooking: the instructor prompts you, there is a deliberate silence for you to
*say* the answer, then a native speaker gives the model answer. New material is
reactivated at expanding intervals inside the lesson and scheduled into later
lessons by a persistent learner model.

Nothing on screen is ever required. Transcripts and plans are written as
supplementary files only.

```
curriculum (TOML) ─┐
                   ├─► planner ─► script (JSON) ─► renderer (TTS + exact silences) ─► lesson.mp3
learner state ─────┘        │
                            └─► learner state update (what to review next time)
```

## Quick start

Python 3.11+ and no required packages. For real voices you need **one** of:

| provider | quality | needs | notes |
|----------|---------|-------|-------|
| `edge`   | neural, many languages | `pip install edge-tts`, network, ffmpeg | free; recommended |
| `openai` | neural | `OPENAI_API_KEY`, network | paid |
| `say`    | good | macOS, ffmpeg | built-in Mac voices |
| `espeak` | robotic | `espeak-ng` | offline; fine for checking a lesson |
| `stub`   | tones only | nothing | structure/timing checks, tests |

```sh
pip install -e ".[edge]"          # or just run `python -m audiolesson.cli`

# lesson 1: French for English speakers, 15 minutes, neural voices
audiolesson generate -c curricula/fr-en-a1.toml -l my-learner.json -m 15 -p profiles/edge-fr-en.toml

# listen to out/lesson-001.mp3 … then, if some things would not come out:
audiolesson report -l my-learner.json --lesson 1 --failed sil_vous_plait,au_revoir

# next day: lesson 2 is planned from what is due
audiolesson generate -c curricula/fr-en-a1.toml -l my-learner.json -m 15 -p profiles/edge-fr-en.toml
audiolesson status -l my-learner.json -c curricula/fr-en-a1.toml
```

Each `generate` writes into `out/`:

- `lesson-NNN.script.json` — the timed, machine-readable script (every segment, every pause)
- `lesson-NNN.plan.json` — what was introduced/reviewed, per-item exposures, exercise index
- `lesson-NNN.transcript.md` — readable transcript (supplementary)
- `lesson-NNN.wav` / `.mp3` and `lesson-NNN.cues.json` (timestamps per exercise)

and updates the learner state file.

Re-render the same lesson with other voices, speeds or pause lengths without
re-planning it:

```sh
audiolesson render out/lesson-001.script.json -p profiles/openai.toml --pause-multiplier 1.3
```

Useful flags for `generate`: `-t cafe,directions` (prefer topics), `--new 4`
(how many new items), `--level A0|A1|A2|B1|B2` (pause lengths), `--no-audio`,
`--dry-run` (don't touch the learner state), `--date YYYY-MM-DD`,
`--no-translate` (don't narrate what the dialogue partner said).

## Daily routine and pacing

One command a day; the tool decides how many new items to introduce.

```sh
CURRICULUM=curricula/is-en LEARNER=learner-is.json PROFILE=profiles/edge-is-en.toml \
MINUTES=30 OUT=lessons/is AUTO=1 tools/daily.sh   # → lessons/is/lesson-NNN.mp3

# after listening — optional in auto mode (AUTO=1), required for the pace to rise otherwise:
audiolesson report -l learner-is.json                       # everything came out
audiolesson report -l learner-is.json --failed takk,bless   # ids are in lesson-NNN.plan.json
audiolesson status -l learner-is.json -c curricula/is-en
```

**Pacing rules** (`LearnerState.suggest_pace`), based on what spaced-retrieval
research and Pimsleur-style courses converge on: about 6–10 productive items
per 30 minutes, retrieval success around 80–85%.

- Start at one new item per 5 minutes (30 min → 6), clamped to 3–10.
- If the last *reported* lesson had more than 20% of its new items fail, pace − 1.
- If the items due for review exceed ~80% of the lesson's review slots, pace − 1.
- Pace + 1 only on evidence: the last lesson was reported with ≤ 10% failures
  and the backlog is small. In manual mode, without `report` the pace never rises.
- **Auto mode** (`--auto`, persists; `AUTO=1` for `tools/daily.sh`): an unreported
  lesson counts as "all good", and the pace steps up once every 3 lessons while
  the backlog stays small. `report --failed …` still slows it down whenever you
  bother to file one. `--manual` switches back.
- `--new N` overrides one lesson; `--pace N` resets the ongoing pace.

**Fixed length.** A lesson lands on the requested minutes (30:00 for `-m 30`)
by three mechanisms, all automatic:

1. *Calibration* — after every render the measured speech length per language
   is folded into the learner state, so the next plan's time estimates match
   the actual voices (espeak, edge and OpenAI all speak at different rates).
2. *Second review pass* — if the material runs out before the time does, items
   reviewed earlier in the lesson come back once more, one stage harder,
   most urgent first.
3. *Fit at render* — the remaining difference is absorbed by scaling every
   pause by one factor within 0.85–1.25 (`fit`, `fit_min`, `fit_max` in the
   profile; `--no-fit` to disable). Speech is never altered.

The first few lessons still come out short: with nothing to review yet there
is simply not 30 minutes of honest work, and `generate` says so rather than
padding. From roughly lesson 5 on, the length is exact.

## How a lesson is built

1. **Selection.** Items already met are ranked by review urgency (overdue ×
   interval, failures, few successes). New items are taken in curriculum order,
   skipping anything whose prerequisites aren't yet solid; a construction pulls
   a second slot-filler along so the pattern can be shown with two fills.
   The number of new items is the learner's pace (see "Daily routine and pacing").
2. **Timeline.** Each new item is introduced (listen, repeat; hard phrases are
   built backwards from the last word; a slow rendition is always followed by
   natural speed) and immediately retrieved once. Its reactivations are then
   scheduled after 3, 5, 8 and 13 intervening exercises, each at a harder stage.
   Reviews of older items fill the gaps, avoiding the same item or topic twice
   in a row. Every few exercises a dialogue is played if the learner knows all
   its lines — two turns the first time, one more turn on each later
   encounter; constructions are recombined with known vocabulary into
   sentences never heard verbatim.
3. **Closing.** The lesson ends by retrieving today's new items once more,
   hardest first so the last thing you do is succeed.
4. **Learner update.** Every retrieval counts as a presumed success (audio
   cannot hear you). Intervals grow 1 → 3 → ×ease days. `report --failed`
   demotes an item and brings it back tomorrow.

The retrieval ladder per item kind (see `audiolesson/stages.py`):

| kind | stages |
|------|--------|
| vocab | intro → meaning → recombine (inside a known pattern) → dialogue |
| phrase | intro → cloze (finish the last word) → hinted (first word given) → meaning → situation → dialogue |
| construction | intro → hinted → meaning → recombine (new fills) → situation → dialogue |
| transform | intro → hinted → meaning → recombine (new example) |

Stages that an item can't support (no situation text, not in any dialogue,
nothing to recombine) are skipped.

**Timing.** Pause lengths are computed, never hard-coded: base window by
answer length (word 2.5 s, short phrase 4 s, sentence 6.5 s, long 8.5 s) ×
level (A0 1.4 … B2 0.75) × familiarity (few successes 1.15, many 0.85) ×
difficulty, plus a bonus for generative prompts. Everything is a field of
`Timing` (`audiolesson/timing.py`); `--pause-multiplier` and the profile's
`pause_multiplier` scale the result at plan or render time.

## Writing a curriculum

See `docs/CURRICULUM.md`. Three curricula ship:

- `curricula/fr-en-a1.toml` — French for English speakers: café, street, hotel,
  small talk; 47 items, 4 dialogues.
- `curricula/fr-ja-a1.toml` — the same material for Japanese speakers
  (日本語の指示でフランス語を学ぶ), derived by `tools/derive_fr_ja.py`.
- `curricula/is-en/` — Icelandic for English speakers, **993 items and 31
  dialogues in 26 topic modules** (greetings, café, directions, self, time,
  weather, numbers/money, shopping, transport, accommodation, health, family,
  daily routine, hobbies, home, food, adjectives, question words, verb forms,
  work, practical life, nature, discourse, travel, feelings). Nouns are tagged
  by the case each construction needs. About five months at the default pace.
  Written by an AI and not yet reviewed by a native speaker.
- `curricula/is-en-a1.toml` — the 61-item starter the module set grew out of
  (kept for quick tests).

A curriculum can be one file or a directory of modules merged in filename
order (`audiolesson validate curricula/is-en`).

The instructor's own phrasing lives in `audiolesson/phrasing/<known_lang>.toml`
(English and Japanese provided), so teaching to speakers of another language
means translating that one file plus the `meaning`/`situation`/`cue` strings
of a curriculum.

```sh
audiolesson generate -c curricula/fr-ja-a1.toml -l watashi.json -m 15 -p profiles/edge-fr-ja.toml
```

## Layout

```
audiolesson/
  content.py    items, dialogues, curriculum loading + validation
  stages.py     retrieval ladder per item kind
  timing.py     pause / speech-length model (all knobs live here)
  learner.py    persistent learner model + spacing
  prompts.py    instructor phrasing loader (data: audiolesson/phrasing/<lang>.toml)
  exercises.py  (item, stage) → segments; backward build, recombination, dialogues
  planner.py    what to practise when; interleaving; closing block; learner update
  script.py     the intermediate timed script + transcript
  render/       audio.py (PCM/ffmpeg), tts.py (providers), renderer.py (script → file)
  cli.py
curricula/      learning material: fr-en, fr-ja (files), is-en/ (26 modules)
tools/          daily.sh (one day of the routine), derive_fr_ja.py (keeps fr-ja in sync with fr-en)
profiles/       voice profiles (provider + voice per speaker)
tests/          python -m unittest
docs/           HANDOFF.md (status + next steps), CURRICULUM.md (format)
```

## Development

```sh
python -m unittest -v          # espeak-ng/ffmpeg optional; one test skips without them
python -m audiolesson.cli generate -c curricula/fr-en-a1.toml -l /tmp/l.json -m 5 --provider stub
```
