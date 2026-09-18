# Handoff note — audiolesson

_Last updated 2026-09-18 (session 6: halló respelled for the TTS, on request)._
Keep this current: whoever picks the project up next, human or AI, should be
able to continue from here without re-deriving decisions._

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

### Addendum: the owner asked for a citation on halló specifically, not just the general rule

Fair challenge — session 5's case rested on the general `ll` rule plus an
espeak cross-check, not on a source about this specific word. Searched for
one (`WebSearch`; **could not fetch and read the raw pages myself** — this
sandbox's egress proxy blocks `en.wiktionary.org`, `en.wikipedia.org`,
`wikiwand.com` and a jina.ai text-proxy alike, so this is the search tool's
own extraction, corroborated across two independently-phrased queries
returning the identical string, not a page I read first-hand):

- **English Wiktionary, Icelandic section for "halló"**: gives the IPA
  transcription **/ˈha.tl̥ou̯/** — <https://en.wiktionary.org/wiki/hall%C3%B3>.
  The `tl̥` is exactly the pre-aspirated voiceless lateral cluster (the
  ring diacritic marks the `l` voiceless), transcribed for this word
  specifically, not inferred from the general rule. This is the citation
  the owner asked for.
- **Forvo** (crowd-sourced native-speaker recordings) has an Icelandic
  recording of "halló" by a listed native speaker
  (<https://forvo.com/word/hall%C3%B3/>) — real first-hand evidence if
  anyone can actually listen to it; not accessible from this sandbox.
- Complication worth keeping in view: several casual, tourist-facing
  pronunciation pages (not dictionaries) gloss "halló" simply as sounding
  like English "hello" and don't mention pre-aspiration for it at all —
  e.g. thecognitio.com's guide, gocarrental.is's guide. That's weaker
  evidence than a transcribed dictionary entry (these pages are aimed at
  travellers, not phonology, and may just be simplifying), but it's a real
  second data point *for* the espeak-ng behaviour, not just noise: loanword
  interjections resisting a native gemination rule that inherited
  vocabulary follows strictly is a real, attested pattern cross-
  linguistically, so "the dictionary-cited/careful pronunciation has it,
  casual usage may not consistently" is a coherent middle reading, not a
  contradiction to paper over.
- Net effect on the earlier call: the Wiktionary transcription is real,
  specific evidence for the native/careful pronunciation, stronger than
  what session 5 had. It does not, by itself, revisit the render-layer
  override — that was the owner's explicit request in the message right
  before this one, and stands unless they say otherwise now that the fuller
  picture is in front of them.

## Session 5: "halló" sounds like [hatlo] on edge-tts — is that wrong?

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

1. **Test `edge` provider on a real network** (see above). If edge-tts's
   `rate="+N%"` sounds off for slow renditions, clamp `slow_rate` to ~0.8.
2. **Listen to a real lesson and tune timing.** Numbers in `Timing` are
   reasoned defaults, not listened-to ones. Likely tweaks: `between_exercises`,
   `repeat_factor`, the A1 multiplier.
3. ~~`alternatives` never spoken~~ — done: at meaning+ stages, once per
   lesson per item, 50% chance: "You could also say:" + alternative.
4. **Lesson-1 intro bunching.** With nothing to review, the first lesson opens
   with 2–3 introductions in a row (nothing else exists yet). Acceptable but a
   short "listen to this conversation" opener, as some audio courses do,
   would be nicer.
5. **Dialogue partner translation** is always narrated (`--no-translate` to
   disable). Could become level-dependent (off from A2).
6. **Curricula.** `fr-en-a1.toml` and its Japanese-instructor twin
   `fr-ja-a1.toml` (generated by `tools/derive_fr_ja.py` from a translation
   table; a test asserts the ids stay in sync). The Japanese strings were
   written by an AI, not reviewed by a native speaker — read them once.
   Numbers/plurals are deliberately absent (no morphology). Other target
   languages need a new curriculum file; no code changes.
7. ~~Cross-lesson dialogue difficulty~~ — done: a dialogue plays
   `dialogue_first_turns` (2) turns on first encounter and one more turn each
   later time, replayed without pauses once it is complete.
8. ~~Parallel TTS~~ — done: providers flagged `parallel` (edge, openai) are
   warmed into the cache with `workers` threads (profile key, default 4).
   Untested against a real network, like the providers themselves.
9. **Wheel install** verified to include `audiolesson/phrasing/*.toml`.

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
