# Dialogue and partner-interaction audit for issue #48

First written in session 33. The narrative is in `docs/history/sessions.md`.

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

### Scene continuity and comprehensible scaffolding (owner comment on #48)

A real Lesson 4 showed the target-language test isn't enough on its own. The learner
was cued to greet *bakery staff* («Góðan daginn»). The partner then said «Má ég setjast
hérna?», and B's cue described someone asking to sit at *your table*. The turns fit,
but the instructor-described world jumped between two scenes. The partner line also
had untaught words with nothing saying what move it made.

Each bridge is now one authored scene on item B:

- **`partner_cue_setup`** replaces A's standalone situation when the pair plays. It
  sets the shared place, roles and reason, and asks for A.
- **`partner_cue_meaning`** says what the partner just said. It is narrated on the
  learner's first two hearings of that bridge (`LearnerState.bridges_heard`), then it
  fades.
- **`partner_cue_situation`** replaces B's standalone situation. It continues the same
  scene and names the partner's move ("She asked if she may sit here. Tell her: by all
  means.").

Validation requires all three with every `partner_cue`. All 26 bridges were audited
manually for target-language coherence and scene continuity, and each got its scene
in English and Japanese:

| A → partner → B | scene (setup / partner's move / B's cue) |
|---|---|
| «Hæ.» → «Hæ! Hvað segirðu gott?» → «Allt gott, takk.» | Your neighbour waves at you in the street. Greet her casually. / Hi! How are you? / She asked how you are. Say all good, thanks. |
| «Gaman að sjá þig.» → «Sömuleiðis! Hvernig hefurðu það?» → «Ég hef það gott.» | An old colleague walks into the café. Say it's nice to see her. / Likewise! How are you doing? / She asked how you're doing. Say you're doing well. |
| «Eigðu góðan dag.» → «Takk, sömuleiðis. Bless!» → «Bless.» | You're leaving the shop after paying. Wish the cashier a good day. / Thanks, you too. Bye! / She wished you the same and said bye. Say bye. |
| «Jæja.» → «Já, ég verð líka að fara. Bless!» → «Sjáumst!» | You've been chatting with a friend for an hour and it's time to go. Signal that the conversation is over. / Yes, I have to go too. Bye! / She has to go too, and you'll see her again soon. Say see you! |
| «Gjörðu svo vel.» → «Takk kærlega!» → «Ekkert að þakka.» | At dinner, your friend asks for the salt. Hand it to her. / Thank you very much! / She thanked you warmly. Say you're welcome. |
| «Hæ.» → «Hæ! Ég á afmæli í dag.» → «Til hamingju!» | Your colleague comes into the office smiling. Greet her casually. / Hi! It's my birthday today. / She told you it's her birthday. Congratulate her. |
| «Takk.» → «Gjörðu svo vel. Eigðu góðan dag!» → «Sömuleiðis.» | The cashier hands you your change. Thank her. / Here you are. Have a good day! / She wished you a good day. Wish her the same. |
| «Hæ.» → «Hæ! Fyrirgefðu, ég er of seinn.» → «Ekkert mál.» | You're waiting outside the cinema. Your friend finally arrives. Greet him casually. / Hi! Sorry, I'm late. / He apologised for being late. Tell him it's no problem. |
| «Ha?» → «Morgunmaturinn er á fyrstu hæð.» → «Ég skil.» | At hotel reception you asked where breakfast is, but the answer came too fast. Ask her to say it again, casually. / Breakfast is on the first floor. / She said it again. Tell her you understand. |
| «Góðan daginn.» → «Góðan daginn. Má ég setjast hérna?» → «Endilega.» | You're sitting at a shared table in a café. A woman comes over and greets you. Greet her back: good day. / Good day. May I sit here? / She asked if she may sit here. Tell her: by all means. |
| «Hvað segirðu gott?» → «Mér líður miklu betur, takk.» → «Gott að heyra.» | Your friend was ill last week. You bump into her. Ask how she is. / I feel much better, thanks. / She said she feels much better. Say good to hear. |
| «Góðan daginn.» → «Góðan daginn! Hvað má bjóða þér?» → «Gætirðu talað hægar?» | You walk into a busy café in the morning. Greet the barista: good day. / Good day! What can I get you? / She asked what you'd like, far too fast. Ask her to speak more slowly. |
| «Gætirðu talað hægar?» → «Auðvitað. Herbergið er númer tuttugu og þrjú.» → «Gætirðu endurtekið þetta?» | At hotel reception, the receptionist is speaking far too fast. Ask her to speak more slowly. / Of course. The room is number twenty-three. / She slowed down, but you still missed the room number. Ask her to repeat it. |
| «Afsakið.» → «Já? Get ég hjálpað?» → «Hvað þýðir þetta?» | There's a word on a street sign you don't know. Get the attention of a woman passing by. / Yes? Can I help? / She asked if she can help. Point at the sign and ask what it means. |
| «Gætirðu endurtekið þetta?» → «Já: Laugavegur tuttugu og þrír.» → «Geturðu skrifað það?» | A woman is telling you the address of your guesthouse, but you missed it. Ask her to repeat it. / Yes: Laugavegur twenty-three. / She repeated the address, but it's still hard to catch by ear. Ask her to write it. |
| «Góðan daginn.» → «Góðan daginn. Hvar er bankinn?» → «Ég veit ekki.» | You're waiting at a bus stop. A man greets you. Greet him back: good day. / Good day. Where is the bank? / He asked where the bank is. You have no idea: say you don't know. |
| «Hæ.» → «Hæ! Er safnið opið á mánudögum?» → «Ég er ekki viss.» | Your friend waves at you across the street. Greet her casually. / Hi! Is the museum open on Mondays? / She asked if the museum is open on Mondays. You're not sure: say so. |
| «Afsakið.» → «Já?» → «Geturðu hjálpað mér?» | At the station, the ticket machine won't take your card. Get the attention of the man behind you. / Yes? / He turned to you. Ask him if he can help you. |
| «Góðan daginn.» → «Góðan daginn. Hvað get ég gert fyrir þig?» → «Ég þarf hjálp.» | You walk up to the information desk with a problem. Greet the clerk: good day. / Good day. What can I do for you? / She asked what she can do for you. Say you need help. |
| «Takk.» → «Gjörðu svo vel. Verði þér að góðu!» → «Hvað er þetta?» | Your host puts a plate in front of you. Thank her. / Here you are. Enjoy your meal! / She wished you a good meal. There's a grey paste on the plate: ask what it is. |
| «Ég skil ekki.» → «Þú þarft bara að fylla út eyðublað á netinu.» → «Ég er útlendingur.» | At the town office, the clerk explains something quickly and you get lost. Tell her you don't understand. / You just need to fill in a form online. / She assumes you know how things work here. Explain that you're a foreigner. |
| «Borð fyrir tvo, takk.» → «Gjörðu svo vel. Ég mæli með lambinu.» → «Ég er grænmetisæta.» | You walk into a restaurant with a friend. Ask for a table for two. / Here you are. I recommend the lamb. / The waiter recommended the lamb. Tell him you're a vegetarian. |
| «Ég er södd.» → «Var þetta gott?» → «Þetta var gott.» | At a restaurant, the waiter offers you more. You couldn't eat another bite: say you're full. / Was it good? / He asked if it was good. Tell him it was good. |
| «Get ég fengið reikninginn?» → «Auðvitað. Það eru fjögur þúsund krónur.» → «Má ég borga með korti?» | You've finished eating at a restaurant. Ask the waiter for the bill. / Of course. That's four thousand krónur. / He told you the total. You have no cash: ask if you may pay by card. |
| «Meira kaffi, takk.» → «Gjörðu svo vel. Eitthvað fleira?» → «Þetta er allt.» | The waiter comes round with the coffee pot. Ask for more coffee. / Here you are. Anything else? / He asked if you'd like anything else. Say that's all. |
| «Hvað kostar þetta?» → «Níu hundruð krónur. Eitthvað fleira?» → «Ekkert meira, takk.» | At a bakery till, you pick up a sandwich. Ask the cashier how much it is. / Nine hundred krónur. Anything else? / She told you the price and asked if there's anything else. Say nothing more, thanks. |

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
- None of the new partner lines or bridge scenes (sessions 30 and 33) are native-reviewed.
- Only the partner gloss fades. The scene cues stay on every encounter, because they
  keep the task checkable. A later step could shorten them once a bridge is familiar.
