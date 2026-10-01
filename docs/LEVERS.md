# Planner levers (issue #136)

Levers are changed by hand, at most two a week, on evidence from the post-lesson feedback
(#128) and the scenario cards (#129). Each lever is a setting, so a change never needs a code change. Every default reproduces
the behaviour from before the lever existed.

`plan.json` records the active levers under `config.levers`, alongside `new_items`,
`minutes` and `priority_items`. The bot's lesson manifest (#128) also keeps the generate
arguments. Together they tie every piece of feedback to the settings that produced it.

On the Discord bot, levers are set in the lesson channel's topic, in a `[levers]` section
(`late_unhinted_recall = true`, `pause_multiplier = 1.2`), or per
deployment with `LESSON_EXTRA_ARGS` in `config.py`; the topic wins.

## Available levers

| lever | CLI | default | metric that shows its effect |
|---|---|---|---|
| new-item budget | `--new N` (one lesson), `--pace N` (ongoing) | the learner's pace | new items per lesson; the reachability report (`validate --cando`) |
| guaranteed late unhinted recall for new items | `--late-unhinted-recall` | off | `review_candidates` of kinds `no_late_recall` and `early_last_appearance` |
| answer-time scale | `--pause-multiplier X` | 1.0 | feedback "pacing" |
| trip priority ordering | `--trip <profile>` | off | the can-do reachability report |

**Late unhinted recall.** The closing recall of a new item skips cloze and hinted prompts.
(A new item whose recombination finds no fresh sentence now always gets a meaning recall
instead of being dropped, with or without this lever.)

Over 12 simulated 30-minute lessons at pace 8, #147 alone already leaves no early last
appearance and no missing late recall; the lever makes sure that closing recall carries no
hint.

**Removed: max same situation.** A cap on how often one situation cue was narrated per item
per lesson (`--max-same-situation`, PR #141) turned further situation recalls into bare
meaning recalls. Hearing an item in its scene again is practice, not a fault, so the lever
and its `repeated_situation` feedback candidate are gone.

The pace never depends on the departure date. Lessons go on at the learner's pace up to and
through the trip, and the pace is throttled only by recall reports (言えた / 迷った / 言えなかった).

## Not yet levers

- Context variety beyond situation variants, such as preferring unused fills on repeats.
  Recombination already avoids sentences heard in the lesson.
- Dialogue and listening share. This waits for clerk-side listening (#134).
