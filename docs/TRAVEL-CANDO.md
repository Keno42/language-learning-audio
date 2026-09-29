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

## Privacy

Personal trip details are never written here, in issues, or in exports: dates, itinerary,
lodging, and how the scenarios are weighted. They belong in a private profile next to the
learner file on the machine that generates lessons (#132). A test checks that no date
appears in the scenario files.
