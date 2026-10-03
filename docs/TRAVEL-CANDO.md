# Travel can-do list (issue #131)

The course's near-term outcome is travel readiness, not item counts:

- reading signs, shop words and place names, and enjoying it;
- greeting, shopping, ordering and paying, and handling simple conversation;
- showing respect for the people and the culture.

The scenarios that define it live in `curricula/is-en/cando/travel.toml`. It sits in a
subdirectory, so `load_curriculum` never reads it as a module. The planner's trip ordering
(#132) aims at these scenarios, and the scenario cards in the Discord review (#129) check
them.

## Tiers and milestones

Milestones are relative to departure, with one lesson a day:

| tier | meaning | items met by |
|---|---|---|
| A | must: greetings incl. the season's, thanks, supermarket, café, bar, public pool, staying in the conversation, excuse me / toilet, essential signs, place names | T−7 weeks |
| B | should: museum, day tours, small talk, taxi and bus, numbers by ear, winter talk and safety | T−4 weeks |
| C | nice to have: place-name parts, holiday traditions, restaurant basics, emergencies, farewell | no milestone |

The default tiers suit a budget traveller: supermarket and café before restaurant.

## Scenario fields

| field | meaning |
|---|---|
| `id`, `tier`, `title`, `title_ja` | identity |
| `setting`, `success` | where it happens; an observable success criterion (what a scenario card checks) |
| `items` | curriculum ids the scenario needs. They are validated: an unknown id fails loading |
| `missing` | what the scenario needs that the curriculum lacks, pointing at the issue that adds it |
| `reading` | texts to read. They feed the reading track (#133) |
| `clerk_lines` | lines to understand. They feed the listening track (#134) and the scenario cards. Wordings are candidates |
| `respect` | respect markers the scenario checks: `greet`, `thanks`, `farewell`, `stayed_icelandic`, `shower_rule`, … |

## Lesson themes (#149 1b-ii)

`curricula/is-en/cando/themes.toml` (`audiolesson/themes.py` documents the format) holds the scenes a lesson can
consolidate: per theme (`scenario`: the can-do scenario it serves), levels of an exchange, each a list of `partner`
turns (with their meaning) and `you` turns (a cue, the model line, the `items` it needs, optional `alts`). `validate`
checks every item and scenario. The lesson picks one (`Planner.pick_theme`; H4 in docs/LEARNING-DESIGN.md) and plays
its exchange twice; `plan.json` names the theme and level. General content only: the private trip profile decides which
scenarios come first and never appears here.

## Coverage report

```sh
python -m audiolesson.cli validate curricula/is-en --known ja --cando [--lessons 84] [--paces 6,8,10]
```

For each simulated pace, the report takes a new learner through `--lessons` daily lessons,
presuming every retrieval succeeds. That is optimistic, because real pace is lower. It then
lists for each scenario:

- its items;
- the latest curriculum order among them;
- the items not met by the tier's milestone at each pace (`late at pace …`);
- what is still `missing`.

It takes a few seconds per pace.

## Reading deck (#133)

The audio never shows spelling, so reading is taught by cards in
`curricula/is-en/reading/deck.toml` (a subdirectory, so it is not a module). The stages
run in this order:

1. `letters`: the sounds, anchored in words the audio already taught.
2. `signs`: doors, pools, roads, holiday opening hours.
3. `shop`
4. `places`: well-known sights, with the parts they're made of.
5. `parts`: foss, jökull, vík, …

Each card has the text, a meaning in English and Japanese, a katakana `hint_ja`, and
`parts` for compounds. A card listing several expressions with «·» may gloss each one in
`words` (`[[word, gloss], …]`, in the text's order). A `letters` card must: its `meaning`
is the spelling rule, so without `words` the words themselves would go unexplained. The
hint is an approximation: the Discord review's 🔊 plays the real pronunciation.

A `letters` card also names the letters or digraphs it teaches in `graphemes`, and `validate`
checks them: each must show in a listed word (a rule never goes without an example) and each
word must show one of them (a word never stands under a rule it doesn't illustrate). A card
once stated the rule for «au» under «Góða nótt · Sjáumst», where «sjáumst» is á + u.

`python -m audiolesson.cli reading curricula/is-en [--trip <profile>]` prints the deck as
JSON for the bot. With a profile, each of its `places` not already in the deck becomes a
card (`own: true`), built at run time and never stored.

Every can-do scenario's `reading` text is in the deck; a test pins this.

## Scenario cards (#129)

A scenario card is one scripted beat of a can-do scenario, for the Discord review. They
replace the GPT Voice role-play, which did not follow a script and whose transcripts did
not match what was said. Cards live in `curricula/is-en/cando/scenes.toml` (`load_cando`
reads only `[[scenarios]]`, so the files share the directory).

| field | meaning |
|---|---|
| `scenario` | the can-do scenario it belongs to (`A3`) |
| `kind` | `respond`: hear the partner, answer. `initiate`: no partner line, start the exchange. `repair`: a partner line beyond the learner; keep the conversation going |
| `situation`, `situation_ja` | the situation, shown as text before anything is heard |
| `partner`, `partner_meaning(_ja)` | the local's line: heard (🔊) before answering, shown with its meaning afterwards. Required for `respond` and `repair`, absent for `initiate` |
| `replies` | model replies, the first being the one `items` describes |
| `items` | curriculum items the first reply needs: the card is shown only once the learner has met them all |
| `note_ja`, `season` | an optional note; a seasonal card appears only for that trip-profile season |

A partner line may go beyond the course: clerks say «Viltu poka?» whether or not the
lesson taught it, and the clerk-side lines (#134) are exactly what these cards practise.
Its meaning is revealed with the answer.

`validate` checks every card's items and scenario, and that every Tier A scenario has a
card. `python -m audiolesson.cli scenes curricula/is-en [--learner <learner.json>]
[--trip <profile>]` prints, as JSON, the cards the learner can take now: every item met,
the season applied. Each card comes with its scenario's tier and title.

## Trip ordering and the private profile (#132)

```sh
python -m audiolesson.cli generate … --trip <LESSON_ROOT>/<name>/trip.toml
python -m audiolesson.cli validate curricula/is-en --cando --trip <profile>
```

`--trip` puts the can-do items (`cando.priority_items`) ahead of the rest of the
curriculum:

- the profile's `boost` scenarios first, then every Tier A item, then every Tier B item;
- curriculum order within each group;
- each item brings its prereqs along, ahead of it;
- the existing arc rules still apply (a construction waits for two fills, and so on).

Without `--trip`, the order is unchanged. An empty profile gives the default A-then-B
ordering. The pace never depends on the departure date: lessons go on at the learner's pace
up to and through the trip, throttled only by what the learner reports.

**Seasonal content** follows the profile's `season`:

- A scenario with `season = "…"` applies only in that season.
- A scenario's `seasonal = { "<season>" = [ids] }` items are added only for that season.

With no profile, or no season, seasonal content is left out of the ordering and the report.
So holiday greetings are Tier A for a winter-holidays trip and nothing for a summer one.

Simulated at pace 6 over 84 daily lessons, the trip ordering (169 items; 172 for a
winter-holidays season) meets every Tier A item by lesson 35 and every Tier B item by
lesson 56. Without it, both tiers miss
their milestone. The total reached stays about the same (~720 items).

Profile keys, all optional:

- `departure`: a date. It sets the horizon of `validate --cando --trip` when `--lessons` is
  not given.
- `boost`: scenario ids.
- `places`: the learner's own place names, for the reading track (#133).
- `season`: which seasonal content applies.

## Privacy

Personal trip details are never written here, in issues, or in exports: dates, itinerary,
lodging, and how the scenarios are weighted. They belong in a private profile next to the
learner file on the machine that generates lessons (#132).

- `generate` prints only that a trip ordering is in use, and how many items it holds.
- `plan.json` records only that count (`priority_items`).
- A lesson record may keep the profile's sha256 (`TripProfile.digest`) and nothing else.
- Tests check that no date appears in the scenario files, and that the profile's places,
  date and boost ids never reach the output or the plan.
