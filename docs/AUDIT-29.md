# Curriculum audit for issue #29 — fixed-phrase families and grammatical dimensions

Scope: the `is-en` course (1008 items, 26 modules). This file covers #29's item (2), the
curriculum-wide audit, and item (3), the grammatical-dimension pilots, as of session 32.
Status lives here; `docs/HANDOFF.md` holds the narrative.

Re-run the family scan with `python tools/phrase_families.py` (default path
`curricula/is-en`, `--min N` for the smallest family). The scan groups phrases that
share a two-word opening or closing frame. Treat it as a candidate list, not a
verdict: "covered by" only means some construction shares that frame. It does not
mean the members can be generated from it. For example, the 64 `ég er …` phrases are
mostly unrelated predicates, not fills of `Ég er að læra {language}.`.

## Dispositions

The owner's three categories (#29 comment on the real Lesson 3):

1. **Lexicalised chunk** — memorise whole. Decomposing it would teach nothing reusable.
2. **Structure can later become productive** — keep the phrase for now. A construction
   can take it over once its parts, or a representation for them, exist.
3. **Shared dimension** — explicitly teaching the shared grammatical dimension reduces
   the number of independent strings.

"Sequencing finding addressed" and "capability modeled" are tracked separately
throughout. The first does not imply the second.

## Grammatical dimensions (item 3)

| dimension | status | where |
|---|---|---|
| gender | **modeled**: milestone + transfer + productive construction | `godur_gender`, `godur_gender_nominative`, `godur_noun` (session 23) |
| aspect (progressive «vera að» + inf) | **modeled**: milestone `vera_ad_progressive` → construction `eg_er_ad_inf` over the `inf` pool | session 32 |
| modality (want / have to / may + inf) | **modeled**: milestone `modal_infinitive` → construction `ma_eg_inf`; `eg_vil` / `eg_verd_ad` gained bound situations for a minimal-pair contrast | session 32 |
| case (dative experiencer «mér») | **named and contrasted, not productive**: milestone `dative_subject` («Ég er svöng» vs «Mér er kalt / heitt»), transfer onto «Mér líður vel / illa» | session 32 |
| number (hundrað/hundruð, ein/króna) | **deliberately unmodeled**: amounts in hundreds stay fixed phrases | session 26 |
| tense (past «var», «var að») | **not started**: «Ég var að borða», «Ég var í Reykjavík í gær», «Ég var rænd» stay separate phrases | — |
| person (ég er / við erum …) | **not started**: «Við erum fjögur / gift / frá Japan» stay separate phrases | — |

Two mechanisms were added so these pilots don't have to fake productivity:

- **`meaning_forms` + `{slot:form}`.** A fill can carry alternative known-language
  renderings, e.g. "going home" / 「家に帰って」, which a construction's meaning asks
  for. The Icelandic fill never changes; only the gloss does. This removes the
  session-27 blocker ("I'm go home.").
- **`situation_fill`** (#57). A construction's situation can name the fill it
  requires, and it is used only once that fill is known. The modality minimal pair
  relies on it.

## Families found by the scan

Families of ≥3 phrases, with disposition and status.

| family | size | disposition | status |
|---|---|---|---|
| `Má ég …?` | 7 | 3 (modality) | **construction added** (`ma_eg_inf`) for `inf` verbs. The 7 fixed phrases use verbs outside the pool (borga með korti, máta, opna, loka, fá, taka mynd) and stay as-is; growing the `inf` pool (with `meaning_forms`) would let the construction take them over |
| `Ég er að …` (progressive) | 10+ | 3 (aspect) | **construction added** (`eg_er_ad_inf`). Existing fixed ones (elda, hugsa, grínast, senda tölvupóst, …) are the same growth case |
| `Mér líður …` | 4 | 3 (case) | milestone transfer only. **Next:** add `vel`/`illa`/`betur`/`ágætlega` as tagged vocab (`vel` also appears in «Gangi þér vel», «Það hentar vel») and a `Mér líður {how}.` construction; pair it with «Hvernig líður þér?» (the `mér`/`þér` dative pair) |
| `Mér er …` | 3 | 3 (case) | named by `dative_subject`. Only two temperature fills (+ «Mér er alveg sama», a chunk) are too few for a construction |
| `… þér` family (Gjörðu svo vel, Verði þér að góðu, Gangi þér vel, Eigðu góðan dag, + 7 more with `þér`) | 11 | mixed | «Gjörðu svo vel», «Verði þér að góðu»: **1**, lexicalised formulas. «Gangi þér vel»: **1/2**. «Eigðu góðan dag»: **2**, «Eigðu {adj+noun, accusative}» (gott kvöld, góða helgi) is a direct transfer target for `godur_gender`'s accusative forms, not yet authored. The shared `þér` (dative of `þú`) belongs with the case pilot |
| `Ég á …` | 8 | 2 | possession + accusative with gendered counts (tvö börn, tvær systur, einn bróður). Candidate construction once an accusative-count pool exists; overlaps number/case |
| `Takk fyrir …` | 4 | 2 | «fyrir» + accusative definite noun (dvölina, matinn, kvöldið); «Takk fyrir síðast» is a chunk (1). Candidate construction with an `acc_def` pool |
| `Hvað heitir …?` | 5 | 2 | «Hvað heitir þú / hún / hann» is a pronoun paradigm (person). «… þetta á íslensku / þetta fjall» are separate |
| `Hvenær fer …?` | 3 | 2 | nominative vehicles (strætó, flugið, ferjan). Construction over a `nom_vehicle` pool |
| `… virkar ekki` | 3 | 2 | nominative definite nouns (sturtan, ljósið, netið). Construction candidate |
| `Hvernig er …?` | 3 | 2 | nominative definite nouns; `hvar_er` already has a `nom_place` pool that could partly serve |
| `Áttu þetta í …?` | 3 | 1/2 | stærra / minna / öðrum lit: shopping formulas, fine as chunks |
| `Hvað er …?` / `Er þetta …?` / `Það er …` / `Þetta er …` | 8–17 | mostly 1 | frames shared, but the members are unrelated predicates. The scan over-groups them; no action |
| `Ég var …` | 3 | 3 (tense) | past tense not started (see table above) |
| `Við erum …` | 3 | 3 (person) | person paradigm not started |
| `… á morgun`, `… í lagi`, `… að fara` | 4–7 | 1 | shared adverbial/idiom tails, not a construction |

## Other findings

- **Fixed in session 36 — fill disambiguators leaked into generated glosses.** A fill's `meaning` can carry a
  parenthetical meant for isolated recall: "work (to work)", "Icelandic (the
  language)", "the hotel (after 'to' / 'for')". Constructions paste it in verbatim:
  "May I work (to work)?", "Do you speak Icelandic (the language)?". This predates
  session 32. Stripping parentheticals globally would be wrong, because some carry
  what the learner must produce ("my friend (male)" vs "(female)"). The fix is per
  item: a `meaning_forms` entry (e.g. `bare`) used by constructions. Not done yet.
- **`X, held ég`** (sentence-final hedge) needs a clause slot the construction IR
  doesn't have. It stays unmodeled (session 27, owner review on PR #54).
- **Dialogue sequencing report:** 11 advisory pairs remain; see the top of
  `docs/HANDOFF.md`. None were touched in session 32.

## Suggested order for what's left

1. Case: `Mér líður {how}.` + `vel`/`illa`/`betur`/`ágætlega`, paired with «Hvernig líður
   þér?», then extend `dative_subject` to `þér`.
2. The `Eigðu {góðan dag / gott kvöld / góða helgi}` transfer for `godur_gender`.
3. Grow the `inf` pool, with `meaning_forms`, so `ma_eg_inf` / `eg_er_ad_inf` absorb
   their fixed siblings; fix the leaking disambiguators at the same time.
4. Tense (past «var» / «var að») and person (`ég er` / `við erum` …) pilots.
5. Remaining category-2 families (`Takk fyrir`, `Hvenær fer`, `… virkar ekki`, `Ég á`).
