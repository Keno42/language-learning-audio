# Planner levers (issue #136)

The weekly calibration (#129) may change at most two levers a week, with human approval.
Each lever is a setting, so a change never needs a code change. Every default reproduces
the behaviour from before the lever existed.

`plan.json` records the active levers under `config.levers`, alongside `new_items`,
`minutes` and `priority_items`. The bot's lesson manifest (#128) also keeps the generate
arguments. Together they tie every piece of feedback to the settings that produced it.

On the Discord bot, levers are set per deployment with `LESSON_EXTRA_ARGS` in
`config.py`, for example `["--max-same-situation", "1", "--late-unhinted-recall"]`.

## Available levers

| lever | CLI | default | metric that shows its effect |
|---|---|---|---|
| new-item budget | `--new N` (one lesson), `--pace N` (ongoing) | the learner's pace | new items per lesson; the reachability report (`validate --cando`) |
| max identical situation cue per item per lesson | `--max-same-situation N` (N ≥ 1) | no limit | `review_candidates` of kind `repeated_situation` |
| guaranteed late unhinted recall for new items | `--late-unhinted-recall` | off | `review_candidates` of kinds `no_late_recall` and `early_last_appearance` |
| answer-time scale | `--pause-multiplier X` | 1.0 | feedback "pacing", weekly check stalls |
| trip priority ordering | `--trip <profile>` | off | the can-do reachability report |

**Max same situation.** Once an item's cue has been narrated N times, a further situation
recall becomes a meaning recall. An item with another situation variant uses that variant
instead.

**Late unhinted recall.** The closing recall of a new item skips cloze and hinted prompts.
A new item whose recombination finds no fresh sentence gets a meaning recall instead of
being dropped from the closing block.

Over 12 simulated 30-minute lessons at pace 8, the two levers together took the candidates
from 68 repeated situations, 7 early last appearances and 1 missing late recall down to
none. Lesson length did not change.

The pace never depends on the departure date. Lessons go on at the learner's pace up to and
through the trip, and the pace is throttled only by recall reports (言えた / 迷った / 言えなかった).

## Not yet levers

- Context variety beyond situation variants, such as preferring unused fills on repeats.
  Recombination already avoids sentences heard in the lesson.
- Dialogue and listening share. This waits for clerk-side listening (#134).
