# Travel can-do list (issue #131)

The course's near-term outcome is travel readiness, not item counts:

- reading signs, menus and place names, and enjoying it;
- greeting, shopping, ordering and paying, and handling simple conversation;
- showing respect for the people and the culture.

The scenarios that define it live in `curricula/is-en/cando/travel.toml`. It sits in a
subdirectory, so `load_curriculum` never reads it as a module. The weekly calibration
(#129) measures these scenarios, and the planner's trip ordering (#132) aims at them.

## Tiers and milestones

Milestones are relative to departure, with one lesson a day:

| tier | meaning | items met by |
|---|---|---|
| A | must: greetings incl. the season's, thanks, supermarket, café, bar, public pool, staying in the conversation, excuse me / toilet, essential signs, place names | T−7 weeks, before tutor session 1 |
| B | should: museum, day tours, small talk, taxi and bus, numbers by ear, winter talk and safety | T−4 weeks |
| C | nice to have: place-name parts, holiday traditions, restaurant basics, emergencies, farewell | no milestone |

The default tiers suit a budget traveller: supermarket and café before restaurant.

## Scenario fields

| field | meaning |
|---|---|
| `id`, `tier`, `title`, `title_ja` | identity |
| `setting`, `success` | where it happens; an observable success criterion (what a weekly check or the tutor looks for) |
| `items` | curriculum ids the scenario needs. They are validated: an unknown id fails loading |
| `missing` | what the scenario needs that the curriculum lacks, pointing at the issue that adds it |
| `reading` | texts to read. They feed the reading track (#133) |
| `clerk_lines` | lines to understand. They feed the listening track (#134). They stay candidates until the native tutor checks them |
| `respect` | respect markers the scenario checks: `greet`, `thanks`, `farewell`, `stayed_icelandic`, `shower_rule`, … |

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
ordering. With `departure` set, the final 14 days halve the new items for each lesson;
the learner's pace itself is not changed.

Simulated at pace 6 over 84 daily lessons, the trip ordering (164 items) meets every
Tier A item by lesson 35 and every Tier B item by lesson 56. Without it, both tiers miss
their milestone. The total reached stays about the same (~720 items).

Profile keys, all optional: `departure` (a date), `boost` (scenario ids), `places` (the
learner's own place names, for the reading track, #133), `season`.

## Privacy

Personal trip details are never written here, in issues, or in exports: dates, itinerary,
lodging, and how the scenarios are weighted. They belong in a private profile next to the
learner file on the machine that generates lessons (#132).

- `generate` prints only that a trip ordering is in use, and how many items it holds.
- `plan.json` records only that count (`priority_items`).
- A lesson record may keep the profile's sha256 (`TripProfile.digest`) and nothing else.
- Tests check that no date appears in the scenario files, and that the profile's places,
  date and boost ids never reach the output or the plan.
