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

## How a lesson is built

1. **Selection.** Items already met are ranked by review urgency (overdue ×
   interval, failures, few successes). New items are taken in curriculum order,
   skipping anything whose prerequisites aren't yet solid; a construction pulls
   a second slot-filler along so the pattern can be shown with two fills.
   About one new item per three minutes by default.
2. **Timeline.** Each new item is introduced (listen, repeat; hard phrases are
   built backwards from the last word; a slow rendition is always followed by
   natural speed) and immediately retrieved once. Its reactivations are then
   scheduled after 3, 5, 8 and 13 intervening exercises, each at a harder stage.
   Reviews of older items fill the gaps, avoiding the same item or topic twice
   in a row. Every few exercises a dialogue is played if the learner knows all
   its lines; constructions are recombined with known vocabulary into
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

See `docs/CURRICULUM.md`. Two curricula ship:

- `curricula/fr-en-a1.toml` — French for English speakers: café, street, hotel,
  small talk; 47 items, 4 dialogues.
- `curricula/fr-ja-a1.toml` — the same material for Japanese speakers
  (日本語の指示でフランス語を学ぶ), derived by `tools/derive_fr_ja.py`.

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
curricula/      *.toml learning material (fr-en, fr-ja)
tools/          derive_fr_ja.py — keeps the Japanese curriculum in sync with the English one
profiles/       voice profiles (provider + voice per speaker)
tests/          python -m unittest
docs/           HANDOFF.md (status + next steps), CURRICULUM.md (format)
```

## Development

```sh
python -m unittest -v          # espeak-ng/ffmpeg optional; one test skips without them
python -m audiolesson.cli generate -c curricula/fr-en-a1.toml -l /tmp/l.json -m 5 --provider stub
```
