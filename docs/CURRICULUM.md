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
| `difficulty` | all | 1–5; ≥4 (or ≥5 words, or `chunks`) triggers backward build; lengthens pauses |
| `topics` | all | free tags for `--topics`; first topic is used for interleaving |
| `tags` | vocab | which construction slots accept this item (e.g. `orderable`, `place`) |
| `prereqs` | all | ids that must be *learned* (≥2 successful recalls) first |
| `components` | all | ids this item is built from (documentation for now) |
| `situation` | phrase, construction | known-language cue for the *situation* stage: "You walk into a bakery. Greet the baker." The instructor adds "What do you say?" |
| `chunks` | phrase | explicit backward-build pieces, shortest first, last = full target |
| `alternatives` | all | other acceptable answers (stored in metadata, not yet spoken) |
| `pronunciation_notes` | all | for the transcript |
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

- Introduce a construction right after (or together with) two things that fit
  its slot; the planner pulls one extra fill along automatically.
- Give every phrase a `situation` — it is the stage that makes recall
  communicative instead of translational.
- Keep `meaning` short and natural; it is read aloud as the prompt.
- Add `chunks` by hand for phrases with liaison or elision where a naive
  word split would sound wrong.
- No real personal data. Names in examples are fictional.
