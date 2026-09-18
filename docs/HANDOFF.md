# Handoff note — audiolesson

_Last updated 2026-09-18 (session 8: resolved GitHub issue #12, reordering
the Icelandic course's opening module)._ Keep this current: whoever picks
the project up next, human or AI, should be able to continue from here
without re-deriving decisions._

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
