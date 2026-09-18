#!/usr/bin/env sh
# One day of the routine: generate the next lesson (pace is adjusted automatically
# from your feedback and the review backlog), print where the audio is, and
# remind you how to report. Run it every day; nothing else is needed.
#
#   CURRICULUM=curricula/is-en LEARNER=learner-is.json PROFILE=profiles/edge-is-en.toml \
#   MINUTES=30 OUT=lessons/is AUTO=1 tools/daily.sh      # AUTO=1: no daily report needed
#
# After listening, record how it went (this is what lets the pace go *up*):
#   audiolesson report -l learner-is.json                     # everything came out
#   audiolesson report -l learner-is.json --failed id1,id2    # ids are in the lesson's .plan.json
set -eu
CURRICULUM=${CURRICULUM:-curricula/is-en}
LEARNER=${LEARNER:-learner.json}
PROFILE=${PROFILE:-profiles/edge-is-en.toml}
MINUTES=${MINUTES:-30}
OUT=${OUT:-lessons}
python3 -m audiolesson.cli generate -c "$CURRICULUM" -l "$LEARNER" -o "$OUT" -m "$MINUTES" -p "$PROFILE" ${AUTO:+--auto} "$@"
echo
echo "After listening: python3 -m audiolesson.cli report -l $LEARNER [--failed id,id]"
