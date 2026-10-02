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
| `prereqs` | all | ids that must be *learned* first (`knows()`: two recalls on or after a due date, not just within one lesson), unless the prerequisite is chosen in the same lesson's selection; a part that is met but not yet known makes the whole wait several days. When an item teaches a word or phrase that sits inside another item's text and is taught after it, choose per case (H6: a chunk first, then the part taken out of it, is a legitimate order; what the learner objected to is a part presented as *something new* after they already had it): (a) the part first, via `prereqs`, when it is high-value on its own (question words, as «Hvenær?» before «Hvenær leggjum við af stað?», #29); or (b) the chunk first, with the part introduced as taken out of the known phrase (a milestone note: "you already know it from …"). `validate --parts` lists the pairs as a prompt for that choice, not a count to bring to zero |
| `components` | all | ids this item is built from (documentation for now) |
| `situation` | phrase, construction | known-language cue for the *situation* stage, spoken as-is with nothing appended — end it with the actual instruction ("You walk into a bakery. Greet the baker."), not just a scene, so the prompt is complete on its own |
| `situations` | phrase, construction | alternative `situation` cues for the same target, glossed per-language the same way (`situations_ja`, …); when given, the planner rotates through them round-robin on the item's total exposures so far, so a high-repeat item's spaced reviews don't all replay the identical wording — overrides `situation` when non-empty |
| `chunks` | vocab, phrase | explicit backward-build pieces, shortest first, last = full target — overrides the automatic word split (a single word is never split automatically) |
| `alternatives` | all | other acceptable answers; past the hint stages one is sometimes offered ("You could also say …") |
| `pronunciation_notes` | all | printed once in the transcript, under the first exercise on that item; not spoken, and not per-language glossed (always shown as written, regardless of `--known`) |
| `slots` | construction | `{ slot = "tag" }`; `target` must contain `{slot}`, and `meaning` `{slot}` or `{slot:form}` (see `meaning_forms`) |
| `example` | construction | `{ slot = "item_id" }` fill used when the pattern is introduced |
| `situation_fill` | construction | `{ slot = "item_id" }` fill(s) the `situation` names ("Ask if she speaks English." → `{ language = "ensku" }`): any exercise narrating the situation (situation-stage recall, `connect()`) uses them; other stages still generate freely. The situation is only used once its bound fills are known (or introduced this lesson) — until then the item is practised at `meaning` and never paired in `connect()`, so a binding never forces an unlearned part. Required whenever the situation mentions one specific slot value; validated to name a real slot and an item carrying that slot's tag. Write a slot-independent situation instead when several fills fit |
| `meaning_forms` | vocab (slot fills) | `{ form = "gloss" }` alternative known-language renderings of `meaning`, glossed like it (`meaning_forms_ja`); a construction's `meaning` asks for one with `{slot:form}` — `"I'm {inf:ing}."` → "I'm going home.", `"{inf:te}もいいですか？"` → 「家に帰ってもいいですか？」. The target-language fill never changes. Validated: every possible fill of that slot must carry the form. The form named `in_sentence` is special: a construction's plain `{slot}` uses it instead of `meaning`. So an isolated-recall disambiguator ("English (the language)") stays out of sentence prompts ("Do you speak English?"). A bracketed `meaning` also needs `meaning_spoken` (next row) |
| `meaning_spoken` | any | what the instructor says when naming the item alone ("Say: …", intro, cloze, hint) and, for a construction, in every generated prompt. `meaning` stays the written gloss: "the hotel (after 'to' / 'for')" → "to the hotel", "Are you {state}? (to a woman)" → "to a woman: Are you {state}?", 「本（〜は・〜が）」→「本が」. Per language (`meaning_spoken_ja`); a glossed meaning never takes another language's spoken form. Validated: whatever is spoken (this, or `meaning` without it) has no brackets or 〜, and a construction's keeps its slots |
| `partner_cue`, `partner_cue_after` | phrase | a partner line spoken between item `partner_cue_after` (A) and this item (B) when `connect()` pairs them in that order |
| `partner_cue_setup` / `partner_cue_meaning` / `partner_cue_situation` | phrase | required with `partner_cue`, glossed per language: the bridge as **one scene**. The setup replaces A's standalone situation (shared place, roles, reason; asks for A), the meaning glosses the partner line on the learner's first two hearings of that bridge, and the situation replaces B's own (same scene, names the partner's move) |
| `context` | phrase, vocab | a short sentence in the known language the word is said in («This is good.» for «gott»; `context_ja`). The recall prompts after the introduction say «Say: good, as in: This is good.», so the answer is the form that sentence needs and not any form of the word's family (gott, góður, góðan…); the introduction keeps its own wording. Use the frame of a construction the learner has, with the case the word takes in it |
| `variant_of` | phrase, vocab | the item this one is a near form of: another case of a noun («bankanum» for «bankinn»), another gender of an adjective («góð» for «gott»), another gender of a number («tvær» for «tveir»). Items stay ordinary items and come in course order; in addition, when a lesson has run out of other material (§9 "Repetition") up to `max_variant_items` variants of something the learner knows (or met earlier that lesson) are introduced beyond the new-item limit, in course order. Name the form it varies, not another variant; the words must differ. Give it a `meaning` that tells it from its base ("good (of a man)", `meaning_forms.in_sentence` keeping sentence prompts plain) |
| `refresh` | construction | a number of sentences, 1 to 5: once the learner **knows** the construction and it isn't open, that many sentences of it come in every lesson as a light review, with the fillers changing (a sentence not heard this lesson, a form too once taught), spread over the lesson's time. Not a drill: for a pattern that is core to what a traveller says (asking permission, saying what you will do). The first lesson and a failed construction get the usual practice instead. |
| `negative`, `question` | construction | the construction's other forms, **authored** (never derived), each with the target template (`negative` / `question`) and its meaning (`negative_meaning` / `question_meaning`, with `_ja`): «Það er {weather}.» → «Það er ekki {weather}.» / «Er {weather}?»; «Ég vil {inf}.» → «Ég vil ekki {inf}.» / «Viltu {inf}?». The template uses the construction's slots (and the meaning its slots); an Icelandic `negative` contains «ekki»; a `question` ends with «?». A form that makes no sense for the construction is left out; a construction with `agreement` placeholders takes none. Generated sentences (recombination, sentence practice, substitution runs) may be a form, but only after the note that teaches it (`Note.teaches`) has been heard; the recall cue is the meaning («Say: I don't want to sleep.»). Where a form's gloss depends on the fill's word class («寒くありません» / «雨ではありません»), the template names a `{slot:form}` and every fill carries it in `meaning_forms` (validated). Wordings are candidates for a native speaker (G10) |
| `prompt_by` | phrase | the item whose line the partner says to prompt this one («Hvaðan ert þú?» for «Ég er frá Japan.»). When the learner knows that line and it isn't open (#149), it is this item's situation cue, said in Icelandic by the partner with no English; when it was introduced this lesson, is met but not yet known, or is open, the line is the cue and what it means follows on its first two hearings in the lesson; when it was never met, the authored `situation` is narrated. «Reply.» frames a cue unless the exercise before was one. G12: a scaffold the learner no longer needs fades. A `situation` states the scene and the task, never what the learner has just said |
| `partner_cue_speaker` | phrase | who says `partner_cue`: `native_a` (voiced female in every profile) or `native_b` (male, the default). Match the scene's he/she; the learner's model answers in that exchange take the other voice. A test checks it against the narration |
| `target_m` | phrase, vocab | what a man says when the words follow the speaker's gender (`target` "Ég er sein.", `target_m` "Ég er seinn."). The introduction presents both; recalls alternate between them and announce which ("As a man: …"), in the matching voice; in an exchange the learner takes the voice opposite the partner and that form. On a construction's fill («glöð» / «glaður») it makes the filled sentence gendered for that exercise; a fill with one form for both («einmana») has none |
| `instruction` | transform | known-language prompt, e.g. `"Make it negative:"` |
| `examples` | transform | ≥2 pairs `{ source, source_meaning, result, result_meaning }`; `source_m` / `result_m` give the man's form of a side whose words follow the speaker's gender (announced only when the learner's answer, `result`, changes). The result must not depend on anyone else whose gender the exercise leaves open: «Ég er þreytt. → Þú ert þreytt.» agrees with the unnamed listener, so it gets no `source_m` (listener agreement is not modelled) |

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
  A sentence that opens with a slot (`"{thing} virkar ekki."`) gets a capital
  first letter, so fills stay lowercase.
- **transform** — a grammatical operation shown by example pairs, then
  practised: the native voice says `source`, the learner produces `result`.

## Dialogues

```toml
[[dialogues]]
id = "cafe_seat"
setting = "You are in a café. There is one free chair at a table where a woman is sitting."
topics = ["cafe", "social"]
requires = ["oui", "je_suis_en_vacances"]   # items the expect_text lines rely on
partner_speaker = "native_a"                # the woman: native_a is the female voice (default native_b, male); the learner's lines take the other voice

  [[dialogues.turns]]
  opener = "Bonjour. Vous désirez ?"        # optional: partner speaks first
  opener_meaning = "Hello. What would you like?"
  cue = "Ask whether this seat is free."    # narrator, known language
  expect = "cette_place_est_libre"          # item id … or:
  # expect_text = "Oui, je suis en vacances."   literal line
  # expect_text_m = "…"                         its man's form, when the words follow the speaker's gender
  # expect_meaning = "Yes, I'm on holiday."
  partner = "Oui, bien sûr. Vous êtes d'où ?"
  partner_meaning = "Yes, of course. Where are you from?"
```

A turn may `expect` a construction when its cue names the fill:
`expect = "thad_kostar_big"` with `expect_fill = { count = "fimm" }` ("Tell him it
costs five thousand krónur.") speaks «Það kostar fimm þúsund krónur.», generated
from the known parts. `expect_fill` must bind **every** slot of the construction, and
the bound fills count as required items, so each spoken part is gated by #27's
durable-learning rule; nothing falls back to the worked example. Validation rejects an
unbound slot, a non-construction `expect`, an unknown slot, or an item that isn't a
fill for that slot.

A dialogue is eligible once every `expect` item, every `expect_fill` item and every
`requires` item is learned. It is replayed without pauses the second time it is practised. Items
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
are general and only used as filler. As filler, a note with `items` plays only
once one of them has been met, or is at most `note_lookahead` (100) items
ahead, so a note is heard when its topic is near rather than spent in the
first lessons. A heard note may play again after `note_repeat_gap` (20)
lessons.

`items` says what a note is *related to* (and triggers it). When a note recommends
an expression for the learner to *say* ("Saying «ég er að læra íslensku» usually makes
them switch back"), list the item(s) that teach it in `requires`. The note will not
play until each one is learned or introduced earlier in the same lesson. A word the
note only mentions or illustrates («tölva», «Vínbúðin») needs no entry.

Wrap any target-language word or phrase mentioned inside `text`/`text_ja` in
`«...»` so it is actually spoken by the target-language voice instead of
read aloud by the instructor: `In «Góðan daginn», «góðan» is…`. A word in a
third language takes a language code, and optionally a native spelling for the
TTS after `|`: `«ja:sate|さて»` shows "sate" in the transcript and speaks さて.
Validation rejects unpaired or misordered `«`/`»`.

`milestone = true` marks an instructional note that names a grammatical
pattern rather than an optional aside: it fires as soon as the learner has
met every id in `items`, before any plain aside, is never used as filler, and
is followed by two quick contrast recalls of its examples (from their
`situation`s, so give it at least three items that have one).
`transfer_items` lists items that apply the pattern to new words; once known,
the contrast recalls prefer them. They are never needed for the note to fire.

`teaches = "negative"` or `"question"` (#171) marks the note that teaches that form of
the constructions that carry it. It has no `items` and is not a milestone: it plays once the
learner knows two constructions that have the form (`forms_after_constructions`), the negative
first and the question in a later lesson, one a lesson, and is followed by the form on two known
constructions. Until it has been heard the form is not used in generated sentences. One note per
form.

## Languages with cases (Icelandic, German, Russian…)

Slot fills are inserted verbatim, so give each noun in the form the
construction needs and encode the case in the tag: `acc_orderable` for what
follows *Ég ætla að fá …*, `nom_place` for what follows *Hvar er …?*. A noun
that is needed in two cases is two vocab items (`supu` / `supa`) — or, if
the second use is rare, a phrase. Never tag a dictionary form into a slot that
takes an oblique case. See `curricula/is-en/03-cafe.toml` (`acc_orderable`) for the pattern.

A noun carries the tag of **every** pattern a person would plausibly say it in, so a new noun has
sentences to be practised in: a food or shop noun is `acc_orderable` («Ég ætla að fá …», «Mig langar í …»),
a shop good `acc_thing` («Áttu …?», «Ég þarf …») and a thing one asks the clerk for `acc_request`
(«Get ég fengið …?»). Judge it by whether the sentence is said at a counter: «Áttu ost?» and «Get ég
fengið mjólk?» are; «Áttu plokkfisk?» and «Get ég fengið humar?» are not, so the dishes are orderable only
(#171 C; a test pins the sets).

## Guidelines that make lessons good

- **Sequence from learner capabilities outward, not from individual phrases or
  dialogues** (issue #29). Decide the communicative goals, introduce high-value reusable
  material deliberately, then write phrases and dialogues from what has already been
  taught.
  - **Vocabulary and constructions.** A word or pattern that shows up constantly in real
    exchanges (`frábært`, `viltu`, `fara`) deserves an early item of its own, or a
    construction when the reusable unit is a pattern ("need to + infinitive"). If a
    natural dialogue line needs material that isn't taught yet, that is a sequencing gap:
    move the concept earlier or give it its own item. Don't patch it with a late
    prerequisite or a permanent translation. `audiolesson validate <dir>` prints an
    advisory report of this signal: words in dialogue lines whose earliest teaching item
    sits far past what the dialogue otherwise needs. A word that repeats across
    dialogues is a strong candidate. Token counts are one input, not proof of mastery.
  - **Grammatical dimensions** (case, gender, number, tense, person, mood, modality,
    agreement). Name the dimension once enough familiar examples make the contrast
    visible, using a `milestone` note (notice → name → discriminate). Then apply it to
    new words through a construction (`agreement`, `transfer_items`). Tell the learner a
    noun's gender before applying agreement to it. Only generate a form you can verify.
    `docs/AUDIT-29.md` tracks which dimensions are modeled.
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
  slang adjective spelled the same way — see `docs/history/sessions.md`, sessions 5–6).
  Citing the general spelling rule isn't the same as citing the specific
  word; if in doubt, check other words with the same risk (e.g. "bolli",
  "galli") before asserting how any of them sound.
- No real personal data. Names in examples are fictional.
