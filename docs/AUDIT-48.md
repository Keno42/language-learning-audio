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

### Bridges beyond module 03

With bridges only in modules 01–03, a simulated course had no partner exchange outside
dialogues from about L30 (30 min) or L45 (20 min) on: the bridges ran out once their items
were known. 40 more bridges cover modules 04–13 (orders ~209–566), written to the same
bar: one scene across both lanes, the partner's move named, partner lines glossed on the
first two hearings. Each partner line was checked for case and agreement («hjálpa þér»,
«aðstoða þig», «Heldurðu að það rigni», «Ert þú kínversk?» to a female learner).

| A → partner → B | scene (setup / partner's move / B's cue) |
|---|---|
| «Ég er týnd.» → «Æ. Get ég hjálpað þér?» → «Geturðu sýnt mér á kortinu?» | You've taken a wrong turn twice. A woman on the pavement looks at you. Tell her you're lost. / Oh. Can I help you? / She offered to help. Hand her your map and ask her to show you on it. |
| «Ég heiti Yuki.» → «Ég heiti Anna. Hvaðan ert þú?» → «Ég er frá Japan.» | At a party, a woman asks your name. Tell her your name is Yuki. / I'm Anna. Where are you from? / She told you her name and asked where you're from. Tell her you're from Japan. |
| «Ég er frá Japan.» → «Frá Japan! Ertu hér í vinnuferð?» → «Ég er í fríi.» | A man at the hotel bar asks where you're from. Tell him you're from Japan. / From Japan! Are you here on a business trip? / He asked if you're here for work. Tell him you're on holiday. |
| «Ert þú íslensk?» → «Já, ég er íslensk. Ert þú kínversk?» → «Ég er japönsk.» | The woman next to you on the plane speaks perfect Icelandic. Ask if she's Icelandic. / Yes, I'm Icelandic. Are you Chinese? / She said yes and guessed you're Chinese. Tell her you're Japanese. |
| «Hvað gerir þú?» → «Ég er kennari. Hvar vinnur þú?» → «Ég vinn hjá litlu fyrirtæki.» | You're chatting with a new acquaintance over coffee. Ask what she does. / I'm a teacher. Where do you work? / She's a teacher, and she asked where you work. Say you work at a small company. |
| «Ég er gift.» → «Áttu börn?» → «Ég á tvö börn.» | A new acquaintance asks about your family. Say you're married. / Do you have children? / She asked if you have children. Say you have two. |
| «Ég er hér í fyrsta sinn.» → «Velkomin! Hversu lengi verður þú hér?» → «Ég er hér í viku.» | In the taxi from the airport, the driver asks if you've been to Iceland before. Say it's your first time. / Welcome! How long will you be here? / He welcomed you and asked how long you're staying. Say a week. |
| «Mér finnst Ísland fallegt.» → «Takk! Ertu hér í fyrsta sinn?» → «Ég hef verið hér áður.» | A taxi driver asks how you like Iceland. Say you think it's beautiful. / Thanks! Is this your first time here? / He thanked you and asked if it's your first time. Say you've been here before. |
| «Klukkan hvað?» → «Klukkan sjö. Hentar það?» → «Það hentar vel.» | Anna suggests meeting for dinner. Ask at what time. / At seven. Does that suit you? / She suggested seven and asked if that suits you. Say that suits you well. |
| «Ég er sein.» → «Ekkert mál. Hvenær kemurðu?» → «Ég kem eftir tíu mínútur.» | You call your friend from the bus. You were meant to meet at seven. Tell her you're late. / No problem. When will you get here? / She said no problem and asked when you'll get there. Say you'll come in ten minutes. |
| «Það er svo kalt!» → «Já. Heldurðu að það rigni á morgun?» → «Ég held ekki.» | You step out into a freezing wind with a friend. Complain that it's so cold. / Yes. Do you think it'll rain tomorrow? / She agreed and asked if you think it'll rain tomorrow. Say you don't think so. |
| «Hvernig verður veðrið á morgun?» → «Það verður mikið rok.» → «Ég þoli ekki rokið.» | You're planning a hike with a friend. Ask what the weather will be tomorrow. / It's going to be very windy. / She says it'll be very windy. Say you can't stand the wind. |
| «Það snjóar.» → «Æ nei, ég þoli ekki snjó.» → «Mér finnst snjórinn fallegur.» | You look out of the window and see flakes. Tell your friend it's snowing. / Oh no, I can't stand snow. / She groaned that she can't stand snow. Say you think the snow is beautiful. |
| «Hvernig er veðrið?» → «Það rignir mikið.» → «Ertu með regnhlíf?» | Your friend just came in from outside, and you're about to go out. Ask how the weather is. / It's raining a lot. / She says it's pouring. Ask if she has an umbrella. |
| «Hvað kostar þetta?» → «Þrjátíu þúsund krónur.» → «Þetta er dýrt.» | In a wool shop you pick up a sweater you like. Ask how much it costs. / Thirty thousand krónur. / It costs thirty thousand. Say it's expensive. |
| «Tekurðu kort?» → «Nei, bara reiðufé.» → «Ég er ekki með reiðufé.» | At a small market stall you want to buy a scarf. Ask whether they take cards. / No, cash only. / The stall only takes cash. Say you don't have cash. |
| «Má ég borga með korti?» → «Já, auðvitað.» → «Get ég fengið kvittun?» | You're buying a work lunch and have no cash. Ask if you may pay by card. / Yes, of course. / You've paid by card and need the receipt for expenses. Ask for one. |
| «Hvað er þetta mikið samtals?» → «Tólf þúsund krónur.» → «Er afsláttur?» | You've put five things on the counter at a gift shop. Ask how much it is altogether. / Twelve thousand krónur. / It comes to twelve thousand. Ask if there's a discount. |
| «Góðan daginn.» → «Góðan daginn. Get ég aðstoðað þig?» → «Ég er bara að skoða.» | You walk into a wool shop in the morning. Greet the shop assistant. / Good morning. Can I help you? / She greeted you and asked if she can help. Say you're just looking. |
| «Má ég máta þetta?» → «Já, auðvitað.» → «Hvar er mátunarklefinn?» | You've found a sweater you like. Ask the assistant if you may try it on. / Yes, of course. / She said of course. Ask where the fitting room is. |
| «Þetta passar ekki.» → «Er það of lítið?» → «Þetta er of stórt.» | You come out of the fitting room shaking your head. Tell the assistant it doesn't fit. / Is it too small? / She guessed it's too small, but it hangs off your shoulders. Say it's too big. |
| «Er þetta ull?» → «Já, þetta er íslensk ull.» → «Áttu þetta í öðrum lit?» | An orange sweater looks handmade. Ask the assistant if it's wool. / Yes, it's Icelandic wool. / It's Icelandic wool, but you don't like the orange. Ask if she has it in another colour. |
| «Þetta passar.» → «Frábært! Ætlarðu að taka hana?» → «Ég ætla að hugsa málið.» | You come out of the fitting room in the sweater. Tell the assistant it fits. / Great! Will you take it? / She asked if you'll take it. It's lovely but expensive: say you'll think about it. |
| «Áttu þetta í stærra?» → «Já. Hvaða stærð notar þú?» → «Ég nota medium.» | The sweater on the rack is too small for you. Ask the assistant if she has it in a bigger size. / Yes. What size do you wear? / She has it and asked your size. Say you wear a medium. |
| «Hvenær fer strætó?» → «Eftir tíu mínútur.» → «Hvað kostar í strætó?» | At the bus stop there's no timetable. Ask the woman waiting next to you when the bus leaves. / In ten minutes. / It comes in ten minutes. Ask her how much the bus costs. |
| «Á flugvöllinn, takk.» → «Ekkert mál.» → «Hvað tekur þetta langan tíma?» | You get into a taxi in a hurry. Tell the driver: to the airport, please. / No problem. / He pulled away. Ask him how long it takes. |
| «Ég vil leigja bíl.» → «Ertu með bókun?» → «Ég á bókun.» | You walk up to the car rental counter. Say you want to rent a car. / Do you have a booking? / The clerk asked if you have a booking. Say you do. |
| «Ég er með bókun.» → «Á hvaða nafni?» → «Á nafninu Yuki.» | You arrive at the hotel reception with your suitcase. Say you have a reservation. / Under which name? / The receptionist asked which name the booking is under. Say: under the name Yuki. |
| «Hafið þið laust herbergi?» → «Já, við erum með eitt laust herbergi.» → «Hvað kostar nóttin?» | You walk into a guesthouse without a booking. Ask if they have a room. / Yes, we have one room free. / They have one room. Ask how much a night costs. |
| «Hvað kostar nóttin?» → «Tuttugu þúsund krónur.» → «Er morgunmatur innifalinn?» | At a guesthouse reception, they have a free room. Ask how much a night costs. / Twenty thousand krónur. / Twenty thousand seems high. Ask if breakfast is included. |
| «Get ég fengið lykilinn?» → «Hvað er herbergisnúmerið?» → «Herbergi númer tólf.» | You come back to the hotel after dinner. Ask the receptionist for your key. / What's the room number? / She asked your room number. Say: room number twelve. |
| «Er þráðlaust net hérna?» → «Já, og það er ókeypis.» → «Hvað er lykilorðið?» | At reception you need to check your email. Ask if there's Wi-Fi. / Yes, and it's free. / There's free Wi-Fi. Ask for the password. |
| «Hvenær er útritun?» → «Klukkan ellefu.» → «Get ég geymt töskuna hérna?» | You're leaving tomorrow and your flight is at night. Ask the receptionist when check-out is. / At eleven. / Check-out is at eleven, hours before your flight. Ask if you can leave your bag here. |
| «Mér líður illa.» → «Viltu fara til læknis?» → «Ég þarf lækni.» | You've gone pale at the dinner table. Tell your friend you feel unwell. / Do you want to see a doctor? / She asked if you want to see a doctor. Say you need one. |
| «Ég týndi vegabréfinu.» → «Þú þarft að fara í sendiráðið.» → «Hvar er sendiráðið?» | At the police station. Tell the officer you lost your passport. / You need to go to the embassy. / The officer said you need to go to the embassy. Ask where the embassy is. |
| «Ég datt.» → «Æ! Er allt í lagi?» → «Ég er í lagi.» | You slipped on the ice on a walk with a friend. Tell her you fell. / Oh! Are you all right? / She asked if you're all right. Nothing's broken: tell her you're OK. |
| «Áttu systkini?» → «Já, ég á einn bróður. En þú?» → «Ég á tvær systur.» | You're getting to know Anna. Ask if she has siblings. / Yes, I have one brother. And you? / She has one brother and asked about yours. Say you have two sisters. |
| «Hvað er hún gömul?» → «Hún er fimm ára. En þú, áttu börn?» → «Ég á engin börn.» | Anna shows you a photo of her daughter. Ask how old she is. / She's five. And you, do you have children? / She's five, and Anna asked if you have children. Say you have none. |
| «Áttu börn?» → «Já, ég á eina dóttur.» → «Hvað heitir hún?» | Over coffee, ask your new friend whether she has children. / Yes, I have one daughter. / She has a daughter. Ask what her name is. |
| «Hvað heitir hún?» → «Hún heitir Sóley.» → «Hvað er hún gömul?» | Anna mentions her daughter. Ask what her name is. / Her name is Sóley. / Her daughter is called Sóley. Ask how old she is. |

Simulated, same seed, before → after (connect exchanges per lesson, dialogues excluded):

| run | L1–30 | L31–60 | L61–100 |
|---|---|---|---|
| 20 min | 4.57 → 4.57 | 0.70 → 0.80 | 0.72 → 1.07 |
| 30 min | 5.67 → 5.70 | 0.37 → 0.73 | 0.53 → 1.00 |

By L100 at 30 minutes, 36 of the 40 new bridges have played at least once. At 20 minutes,
28 have played by L120. Items learned per lesson are unchanged. Later lessons reach a
connect exercise only once per arc, and the drill-streak breaker takes a dialogue first,
so the rate stays near one exchange per lesson. From L2 on, every lesson in both runs has
at least one partner line (a dialogue or an exchange).

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
- Bridges beyond module 13 (orders above ~566, reached after about L100 at 30 minutes).
- None of the new partner lines or bridge scenes (sessions 30, 33 and the modules 04–13 set) are native-reviewed.
- Only the partner gloss fades. The scene cues stay on every encounter, because they
  keep the task checkable. A later step could shorten them once a bridge is familiar.
