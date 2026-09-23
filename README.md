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

# lesson 1: French for English speakers, 15 minutes, neural voices.
# --user names the learner; everything for them lands under out/yuki/ from now on.
audiolesson generate -u yuki -c curricula/fr-en-a1.toml -m 15 -p profiles/edge-fr-en.toml

# listen to out/yuki/lesson-001.mp3 … then, if some things would not come out:
audiolesson report -u yuki --lesson 1 --failed sil_vous_plait,au_revoir

# next day: lesson 2 is planned from what is due. -c/-p/-m are remembered, so
# only -u is needed from here on.
audiolesson generate -u yuki
audiolesson status -u yuki
```

Each `generate` writes into `out/yuki/` (or wherever `-o` points, if `--user`
is not used):

- `lesson-NNN.script.json` — the timed, machine-readable script (every segment, every pause)
- `lesson-NNN.plan.json` — what was introduced/reviewed, per-item exposures, exercise index
- `lesson-NNN.transcript.md` — readable transcript (supplementary)
- `lesson-NNN.wav` / `.mp3` and `lesson-NNN.cues.json` (timestamps per exercise)
- `learner.json` — the persistent learner state, and (with `--user`) `settings.json`

**Several learners.** `--user NAME` (`-u`) is a thin wrapper: it points
`--learner`/`--out` at `<root>/NAME/` (root defaults to `out/`, or
`$AUDIOLESSON_ROOT`) and remembers whatever `--curriculum`, `--known`,
`--profile`, `--provider`, `--minutes` and `--level` you passed the first
time in `<root>/NAME/settings.json`, so later calls need only `-u NAME`.
Feedback mode and pace are not duplicated there — they live in `learner.json`
as before. `--user` together with `--learner`/`--out` is refused rather than
silently overridden; the original flags work exactly as before when `--user`
is omitted, so nothing here is required.

```sh
audiolesson generate -u yuki -c curricula/fr-en-a1.toml -m 15 -p profiles/edge-fr-en.toml
audiolesson generate -u sota -c curricula/is-en --known ja -m 30 -p profiles/edge-is-ja.toml
audiolesson generate -u yuki       # tomorrow: French, 15 min, same profile — remembered
audiolesson generate -u sota       # tomorrow: Icelandic in Japanese, 30 min — remembered
```

Re-render the same lesson with other voices, speeds or pause lengths without
re-planning it:

```sh
audiolesson render out/yuki/lesson-001.script.json -p profiles/openai.toml --pause-multiplier 1.3
```

Useful flags for `generate`: `-t cafe,directions` (prefer topics), `--new 4`
(how many new items), `--level A0|A1|A2|B1|B2` (pause lengths), `--no-audio`,
`--dry-run` (don't touch the learner state), `--date YYYY-MM-DD`,
`--no-translate` (don't narrate what the dialogue partner said).

## Daily routine and pacing

One command a day; the tool decides how many new items to introduce.

```sh
AUDIOLESSON_USER=is-yuki CURRICULUM=curricula/is-en PROFILE=profiles/edge-is-en.toml \
MINUTES=30 AUTO=1 tools/daily.sh                  # → out/is-yuki/lesson-NNN.mp3
AUDIOLESSON_USER=is-yuki tools/daily.sh           # every day after: nothing else to pass

# after listening — optional in auto mode (AUTO=1), required for the pace to rise otherwise:
audiolesson report -u is-yuki                       # everything came out
audiolesson report -u is-yuki --failed takk,bless   # ids are in lesson-NNN.plan.json
audiolesson status -u is-yuki
```

(`AUDIOLESSON_USER` just sets `-u`/`--user` for `tools/daily.sh`; it is named
that way, not `USER`, to avoid the shell's own login-name variable. The
original `CURRICULUM=… LEARNER=… OUT=…` form still works unchanged — see
`tools/daily.sh` for both.)

**Pacing rules** (`LearnerState.suggest_pace`), based on what spaced-retrieval
research and the established audio courses of the prompt–pause–answer type
converge on: about 6–10 productive items per 30 minutes, retrieval success
around 80–85%.

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
3. *Fit at render* — if the file would still miss the target by more than a
   minute (`fit_tolerance`, default 60 s), every pause is scaled by one
   factor within 0.85–1.25 (`fit`, `fit_min`, `fit_max` in the profile;
   `--no-fit`, `--fit-tolerance`). Inside the tolerance, pauses stay exactly
   as the timing model set them. Speech is never altered.

**Cultural asides.** A curriculum can carry `[[notes]]`: short remarks in
the learner's language (for the Icelandic course, written for someone from
Japan — hot dogs and onigiri, pools and sentō, first names and -san). The
planner plays one right after an exercise on a related item, at most one
per 12 minutes, and uses them to fill a gap when there is nothing due. As
filler it only takes a note about material already met, or coming up within
about a module; unheard notes come first, and a heard one returns only after
20 lessons, so asides keep appearing across the course.

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
   sentences never heard verbatim. Each batch of new items also gets a
   *connect* exercise: a short exchange with a partner line between two of
   its items when one is authored, otherwise a quick mixed review of two
   separate situations. A long run of isolated recalls is
   broken up by a dialogue, a note or a connect.
   When the last example of a grammatical pattern arrives, a *milestone* note
   names the pattern and two quick contrast recalls follow.
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
- `curricula/is-en/` — Icelandic for English speakers, **1012 items, 32
  dialogues and 53 notes in 26 topic modules** (greetings, café, directions, self, time,
  weather, numbers/money, shopping, transport, accommodation, health, family,
  daily routine, hobbies, home, food, adjectives, question words, verb forms,
  work, practical life, nature, discourse, travel, feelings). Nouns are tagged
  by the case each construction needs. About five months at the default pace.
  Written by an AI and not yet reviewed by a native speaker.

A curriculum can be one file or a directory of modules merged in filename
order (`audiolesson validate curricula/is-en`).

**Japanese instructor for the Icelandic course.** The same files carry
Japanese glosses next to the English ones (`meaning_ja`, `situation_ja`,
`cue_ja`, `text_ja` …), written from the Icelandic directly rather than
translated from the English, so e.g. *Takk fyrir síðast* is 「先日はどうも」
and *Verði þér að góðu* is 「どうぞ召し上がれ」. Select them with `--known ja`:

```sh
audiolesson generate -c curricula/is-en --known ja -l watashi.json -m 30 -p profiles/edge-is-ja.toml
KNOWN=ja PROFILE=profiles/edge-is-ja.toml tools/daily.sh
audiolesson validate curricula/is-en            # reports gloss coverage per language
```

Generation refuses to mix languages: if a gloss is missing in the chosen
language it stops and names the entries (`--allow-fallback` overrides).
Adding another learner language means adding `<field>_<lang>` lines
(`tools/gloss.py` inserts them from a JSON map) and a
`audiolesson/phrasing/<lang>.toml`.

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
  cli.py        commands, incl. the --user/--root wrapper (out/<user>/, settings.json)
curricula/      learning material: fr-en-a1, fr-ja-a1 (files), is-en/ (26 modules)
tools/          daily.sh (one day of the routine), derive_fr_ja.py (keeps fr-ja in sync with fr-en),
                gloss.py (inserts <field>_<lang> glosses), phrase_families.py (fixed-phrase audit)
profiles/       voice profiles (provider + voice per speaker)
tests/          python -m unittest
docs/           DESIGN.md (code map, invariants, decisions), CURRICULUM.md (format),
                AUDIT-29.md / AUDIT-48.md (audit tables behind #29 and #48), history/ (session log)
```

## Development

Open work, known gaps and design discussion live in the GitHub issues. `docs/DESIGN.md`
has the code map, the invariants the tests pin and the decisions behind them.

### How to check your change

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

`python -m audiolesson.cli generate -c curricula/fr-en-a1.toml -l /tmp/l.json -m 5 --provider stub`
renders a quick lesson without any TTS dependency; espeak-ng/ffmpeg are optional (one test
skips without them).
