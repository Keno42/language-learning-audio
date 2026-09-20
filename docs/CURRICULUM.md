# Curriculum file format

A curriculum is one TOML file — or a directory of them, merged in filename
order, which is how the large Icelandic course is organised
(`curricula/is-en/00-curriculum.toml` carries the metadata, `01-…` to `26-…`
carry the modules). It holds metadata, an ordered list of `[[items]]`, and
optional `[[dialogues]]`. `audiolesson validate <file-or-dir>` checks it,
including duplicate ids and duplicate targets across modules.

```toml
[curriculum]
name = "French A1 — café, street, hotel"
target_lang = "fr"     # what is being learned (voice / speech-rate language code)
known_lang = "en"      # the learner's language; needs audiolesson/phrasing/<known_lang>.toml
level = "A1"           # default pause level for a new learner
```

## Items

Listed in the default order of introduction. The planner keeps this order but
skips anything whose `prereqs` the learner does not know yet.

| field | kinds | meaning |
|-------|-------|---------|
| `id` | all | unique, `snake_case`; used in learner state and `report --failed` |
| `kind` | all | `vocab`, `phrase`, `construction`, `transform` |
| `target` | all | the target-language text spoken by the native voice |
| `meaning` | all | known-language gloss the instructor reads out |
| `difficulty` | all | 1–5; ≥4 (or ≥5 words, or `chunks`, or a single word with 3+ syllables) triggers backward build; lengthens pauses |
| `topics` | all | free tags for `--topics`; first topic is used for interleaving |
| `tags` | vocab | which construction slots accept this item (e.g. `orderable`, `place`) |
| `prereqs` | all | ids that must be *learned* (≥2 successful recalls) first |
| `components` | all | ids this item is built from (documentation for now) |
| `situation` | phrase, construction | known-language cue for the *situation* stage, spoken as-is with nothing appended — end it with the actual instruction ("You walk into a bakery. Greet the baker."), not just a scene, so the prompt is complete on its own |
| `chunks` | vocab, phrase | explicit backward-build pieces, shortest first, last = full target — overrides the automatic word- or syllable-split |
| `alternatives` | all | other acceptable answers (stored in metadata, not yet spoken) |
| `pronunciation_notes` | all | printed once in the transcript, under the first exercise on that item; not spoken, and not per-language glossed (always shown as written, regardless of `--known`) |
| `slots` | construction | `{ slot = "tag" }`; `target` and `meaning` must contain `{slot}` |
| `example` | construction | `{ slot = "item_id" }` fill used when the pattern is introduced |
| `instruction` | transform | known-language prompt, e.g. `"Make it negative:"` |
| `examples` | transform | ≥2 pairs `{ source, source_meaning, result, result_meaning }` |

### Kinds

- **vocab** — a word or fixed noun phrase. Climbs intro → meaning → recombine
  (placed inside a known construction whose slot tag matches one of its
  `tags`) → dialogue.
- **phrase** — a fixed sentence. Climbs intro → cloze → hinted → meaning →
  situation → dialogue.
- **construction** — a reusable pattern with slots. Introduced with the
  `example` fill plus a second known fill; later stages fill it with other
  known vocabulary to produce sentences the learner has never heard
  ("generative practice"). Slot fills use the vocab `target` verbatim, so tag
  only items that are grammatical in that slot (article, gender, number).
- **transform** — a grammatical operation shown by example pairs, then
  practised: the native voice says `source`, the learner produces `result`.

## Dialogues

```toml
[[dialogues]]
id = "cafe_seat"
setting = "You are in a café. There is one free chair at a table where a woman is sitting."
topics = ["cafe", "social"]
requires = ["oui", "je_suis_en_vacances"]   # items the expect_text lines rely on
partner_speaker = "native_b"                # default

  [[dialogues.turns]]
  opener = "Bonjour. Vous désirez ?"        # optional: partner speaks first
  opener_meaning = "Hello. What would you like?"
  cue = "Ask whether this seat is free."    # narrator, known language
  expect = "cette_place_est_libre"          # item id … or:
  # expect_text = "Oui, je suis en vacances."   literal line
  # expect_meaning = "Yes, I'm on holiday."
  partner = "Oui, bien sûr. Vous êtes d'où ?"
  partner_meaning = "Yes, of course. Where are you from?"
```

A dialogue is eligible once every `expect` item and every `requires` item is
learned. It is replayed without pauses the second time it is practised. Items
that appear in a dialogue gain the *dialogue* stage at the top of their ladder.

## Several learner languages in one file

Any glossed field can carry per-language variants: `meaning_ja`,
`situation_ja`, `instruction_ja`, `source_meaning_ja` / `result_meaning_ja`
inside transform examples, `setting_ja`, `cue_ja`, `opener_meaning_ja`,
`partner_meaning_ja`, `expect_meaning_ja` on dialogues, `text_ja` on notes,
`name_ja` on the curriculum. `load_curriculum(path, known_lang="ja")` promotes
them; `audiolesson validate` reports coverage per language. Write the gloss
from the target-language text, not from the primary gloss — the point of
keeping them side by side is that each language gets the closest natural
rendering. `tools/gloss.py` inserts glosses from a JSON map keyed by id, so the
files stay reviewable line by line.

## Cultural asides

```toml
[[notes]]
id = "pylsa"
items = ["pylsu", "eina_pylsu_med_ollu"]   # play right after one of these
topics = ["food"]
text = "The Icelandic hot dog is mostly lamb, and 'með öllu' means …"
```

Notes are spoken by the instructor in the learner's language, never
required for the lesson, and rationed (about one per 12 minutes). Keep them
to two or three sentences, roughly 15–20 seconds of speech; the best ones
contrast the target culture with the learner's own. Notes with no `items`
are only used as filler.

## Languages with cases (Icelandic, German, Russian…)

Slot fills are inserted verbatim, so give each noun in the form the
construction needs and encode the case in the tag: `acc_orderable` for what
follows *Ég ætla að fá …*, `nom_place` for what follows *Hvar er …?*. A noun
that is needed in two cases is two vocab items (`supu` / `supa`) — or, if
the second use is rare, a phrase. Never tag a dictionary form into a slot that
takes an oblique case. See `curricula/is-en-a1.toml` for the pattern.

## Guidelines that make lessons good

- **Top priority (issue #29, session 15 — supersedes #23 and #25, both
  closed into it): design sequencing from learner capabilities outward,
  not from individual phrases or dialogues.** Decide communicative goals,
  introduce high-value reusable material deliberately, then write
  phrases/dialogues from what's already been taught — not the other way
  around. This applies at more than one level:
  - **Vocabulary/constructions**: a word or pattern that shows up
    constantly in real exchanges (`frábært`, `viltu`, `fara`, `og`,
    `líka`, …) is worth a dedicated early item — or, where the reusable
    unit is really a pattern rather than one word, a construction (e.g.
    "need/have to + infinitive") — precisely because it's generative: it
    combines into many later sentences, not just the one phrase that
    happened to introduce it. If a natural dialogue line needs material
    the curriculum hasn't deliberately taught yet, that's a sequencing
    gap to fix (move the concept earlier, or give it its own item/
    construction), not something to patch with a late prerequisite or a
    permanent translation. `audiolesson validate <dir>` prints an
    advisory (not blocking) report of exactly this signal — words in
    dialogue lines whose earliest teaching item sits far past what the
    dialogue otherwise needs; a word repeating across several dialogues
    in that report is a strong promotion candidate. Token occurrence is
    a signal, not proof of mastery — it's one input, not the mechanism.
  - **Grammatical dimensions** (case, gender, number, tense, person,
    mood, modality, agreement): introduce the dimension itself once
    enough familiar examples make the contrast visible, rather than
    leaving the learner to notice it unassisted or explaining it away
    per-pair. Worked example from the issue: `Góðan daginn` / `Góða
    nótt` / `Gott kvöld` are all already-taught items whose differing
    adjective endings are a systematic gender-agreement pattern — worth
    a deliberate "notice → name → practice → apply to new words" moment
    at the point enough of these examples exist, not three unrelated
    fixed phrases forever.

  See `docs/HANDOFF.md` sessions 14–15 for how this was found (via
  gating dialogue eligibility on comprehension, which broke down
  mechanically) and why it's now a sequencing/authoring project, not a
  single fixable bug.
- Introduce a construction right after (or together with) two things that fit
  its slot; the planner pulls one extra fill along automatically.
- Give every phrase a `situation` — it is the stage that makes recall
  communicative instead of translational.
- Keep `meaning` short and natural; it is read aloud as the prompt.
- Add `chunks` by hand for phrases with liaison or elision where a naive
  word split would sound wrong.
- Before writing `pronunciation_notes` or a `RESPELL_FOR_SPEECH` override
  (`audiolesson/render/renderer.py`), read the *whole* dictionary entry for
  the word, not just the first result that matches what you already expect.
  A spelling can be a homograph with an unrelated etymology and a different
  pronunciation (Icelandic "halló" the Danish-loan greeting vs. an unrelated
  slang adjective spelled the same way — see `docs/HANDOFF.md` session 6).
  Citing the general spelling rule isn't the same as citing the specific
  word; if in doubt, check other words with the same risk (e.g. "bolli",
  "galli") before asserting how any of them sound.
- No real personal data. Names in examples are fictional.
