# Dialogue and partner-interaction audit for issue #48

As of session 33. The narrative is in `docs/HANDOFF.md`.

## The bar

With the instructor lane stripped away, the target-language turns (partner and learner)
must form one plausible interaction (#48). Instructor cues may stay wherever they make
the task checkable. A cue is part of the instructor lane, so it must also read cleanly.

## Per-dialogue audit

Each dialogue was read with its learner and partner lines only, in curriculum order of
its requirements (`base` = the latest required item's order). "Partner opens" is whether
the partner speaks first. Learner-initiated dialogues (asking a stranger, ordering) are
fine as long as at least some dialogues are fully partner-driven, and 26 of 32 are.

| dialogue | base | turns | partner opens | item turns / text turns | finding |
|---|---|---|---|---|---|
| `nagranni` | 11 | 3 | no | 1 / 2 | coherent; learner-initiated |
| `tungumal` | 54 | 4 | yes | 2 / 2 | coherent (cluster D fix, session 23) |
| `kaffihus` | 118 | 4 | yes | 2 / 2 | coherent; partner price is a fixed hundreds amount (hundruð unmodeled, session 26) |
| `veitingastadur` | 160 | 5 | yes | 2 / 3 | **fixed**: «Hérna er matseðilinn» used the accusative after «er»; clause dropped (nominative «matseðillinn» not taught) |
| `sundlaug` | 205 | 3 | no | 1 / 2 | coherent; learner-initiated |
| `tynd` | 216 | 5 | no | 3 / 2 | coherent; learner-initiated |
| `kynning` | 228 | 4 | yes | 2 / 2 | coherent |
| `leigubill` | 263 | 4 | yes | 3 / 1 | coherent |
| `stefnumot` | 294 | 4 | yes | 3 / 1 | coherent |
| `vedur` | 314 | 2 | yes | 0 / 2 | coherent; only 2 turns, both expect_text |
| `gonguferd` | 342 | 4 | no | 3 / 1 | coherent; «held ég» hedge unmodeled (session 27) |
| `solubas` | 365 | 3 | yes | 3 / 0 | **new**: learner as seller; price generated from `thad_kostar_big` via `expect_fill` |
| `markadur` | 373 | 5 | no | 4 / 1 | **fixed**: seller answered the ATM question with «Ég er með peysu fyrir þig» (copied from gonguferd) |
| `peysubud` | 424 | 4 | yes | 1 / 3 | coherent |
| `straeto` | 439 | 4 | no | 4 / 0 | **fixed**: «Hvar á ég að fara út?» was answered «Allt í lagi.» |
| `flugvollur` | 451 | 4 | yes | 4 / 0 | coherent |
| `innritun` | 481 | 4 | yes | 3 / 1 | coherent |
| `vandamal` | 486 | 3 | yes | 2 / 1 | coherent |
| `apotek` | 512 | 4 | yes | 2 / 2 | coherent |
| `laeknir` | 529 | 3 | yes | 1 / 2 | coherent |
| `myndir` | 557 | 4 | yes | 2 / 2 | **fixed** (instructor lane): the cue corrected itself mid-sentence; «Hún er lítil» dodges the age question (acceptable) |
| `dagurinn` | 595 | 3 | yes | 0 / 3 | coherent; all learner turns expect_text |
| `ahugamal` | 613 | 3 | yes | 0 / 3 | **fixed**: «Viltu sjá eina?» → «Já, mér líkar það» (wrong response) and a self-correcting cue → «Já, endilega!» |
| `heimsokn` | 663 | 2 | yes | 0 / 2 | **fixed**: roles inverted — the guest told the host «Farðu úr skónum», host replied «Nákvæmlega» |
| `kvoldmatur` | 708 | 4 | yes | 4 / 0 | coherent |
| `spurningar` | 788 | 3 | yes | 1 / 2 | coherent |
| `vidtal` | 838 | 4 | yes | 2 / 2 | coherent («Segðu mér…» advisory, #29) |
| `simabud` | 870 | 4 | yes | 3 / 1 | coherent |
| `hvalaskodun` | 904 | 3 | yes | 2 / 1 | coherent |
| `spjall` | 940 | 4 | yes | 3 / 1 | coherent |
| `ferdaskrifstofa` | 954 | 4 | yes | 3 / 1 | coherent |
| `kvedja` | 1004 | 2 | yes | 0 / 2 | coherent |

Six dialogues had a real problem (four target-language lanes, one role inversion and
two garbled cues); all are fixed. The `heimsokn` fix also removes the
`dialogue_sequencing_report` finding for «nákvæmlega» (11 → 10 advisory pairs).

## Partner exchanges outside dialogues

Early lessons can't reach a dialogue: #27's durable gate needs its items *learned*, not
just met. Partner interaction there comes from authored `connect()` bridges: learner
A → `partner_cue` → learner B. 26 exist now: 13 in modules 01–02 (one from session 25,
twelve from session 30) and 13 more in modules 02–03 (session 33), e.g. `get_eg_fengid_reikninginn` → «Auðvitað. Það
eru fjögur þúsund krónur.» → `ma_eg_borga_med_korti`. Connect bridges may use untaught
words (a half-understood partner line is realistic); dialogue partner lines may not
(`test_dialogue_lines_stay_within_taught_vocabulary`).

Simulated coverage (lessons with no partner exchange at all):

| run | session 30 | session 33 |
|---|---|---|
| 60 × 20 min | L1, L8 | L1 only (six items, nothing to pair yet) |
| 30 × 30 min | L5, L6 | none |

## Numbers inside a partner-driven transaction

Session 26's number constructions were only ever *safe* inside `connect()`. A dialogue
turn can now expect a construction with the fill its cue names (`expect_fill`). The
fill counts as a required item, so the dialogue waits until it is learned. `solubas`
(learner as a market-stall seller) uses this:

    P: Góðan daginn. Hvað kostar þetta?
    L: Það kostar fimm þúsund krónur.        ← thad_kostar_big + fimm, generated
    P: Fimm þúsund? Það er of dýrt. Fjögur þúsund?
    L: Allt í lagi.
    P: Frábært. Má ég borga með korti?
    L: Ekkert mál.
    P: Takk fyrir! Bless.

A simulated 20-minute course reaches it at lesson 87 (first encounter, 2 of 3 turns) and
plays it in full at lesson 92.

## Still open

- Partner lines in `kaffihus` / `markadur` / `apotek` still quote hundreds or teen
  amounts as fixed text: hundreds are unmodeled (session 26) and teens are outside
  `big_count`.
- `vedur`, `dagurinn`, `ahugamal`, `heimsokn`, `kvedja` have no item-linked learner
  turns (all `expect_text`). They are coherent, but their turns aren't retrieval of
  taught items.
- Bridges beyond module 03, where later lessons still rely on dialogues plus
  recombination-only connects.
- None of the new partner lines (sessions 30 and 33) are native-reviewed.
