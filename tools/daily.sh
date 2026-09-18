#!/usr/bin/env sh
# One day of the routine: generate the next lesson (pace is adjusted automatically
# from your feedback and the review backlog), print where the audio is, and
# remind you how to report. Run it every day; nothing else is needed.
#
# Two ways to point it at a learner:
#
# 1. AUDIOLESSON_USER (recommended): everything lands under out/<name>/ (or
#    $AUDIOLESSON_ROOT/<name>/), and the curriculum/profile/minutes/known you pass
#    the FIRST time are remembered — later calls need only AUDIOLESSON_USER.
#
#     AUDIOLESSON_USER=is-yuki CURRICULUM=curricula/is-en PROFILE=profiles/edge-is-en.toml \
#     MINUTES=30 AUTO=1 tools/daily.sh              # → out/is-yuki/lesson-NNN.mp3
#     AUDIOLESSON_USER=is-yuki tools/daily.sh        # every day after: nothing else to pass
#     AUDIOLESSON_USER=is-yuki KNOWN=ja PROFILE=profiles/edge-is-ja.toml tools/daily.sh  # Japanese instructions
#
#    After listening (this is what lets the pace go *up* — skip if AUTO=1):
#     audiolesson report -u is-yuki                     # everything came out
#     audiolesson report -u is-yuki --failed id1,id2    # ids are in the lesson's .plan.json
#
# 2. Explicit LEARNER/OUT (the original interface; still works exactly as before):
#
#     CURRICULUM=curricula/is-en LEARNER=learner-is.json PROFILE=profiles/edge-is-en.toml \
#     MINUTES=30 OUT=lessons/is AUTO=1 tools/daily.sh
#     audiolesson report -l learner-is.json --failed id1,id2
set -eu

if [ -n "${AUDIOLESSON_USER:-}" ]; then
  # settings.json under the user's directory remembers CURRICULUM/PROFILE/MINUTES/KNOWN
  # after the first call, so later calls can omit whichever of these were already set.
  set -- -u "$AUDIOLESSON_USER" ${AUDIOLESSON_ROOT:+--root "$AUDIOLESSON_ROOT"} \
    ${CURRICULUM:+-c "$CURRICULUM"} ${PROFILE:+-p "$PROFILE"} ${MINUTES:+-m "$MINUTES"} \
    ${KNOWN:+--known "$KNOWN"} ${AUTO:+--auto} "$@"
  python3 -m audiolesson.cli generate "$@"
  echo
  echo "After listening: python3 -m audiolesson.cli report -u $AUDIOLESSON_USER [--failed id,id]"
else
  CURRICULUM=${CURRICULUM:-curricula/is-en}
  LEARNER=${LEARNER:-learner.json}
  PROFILE=${PROFILE:-profiles/edge-is-en.toml}
  MINUTES=${MINUTES:-30}
  OUT=${OUT:-lessons}
  KNOWN=${KNOWN:-}          # e.g. ja for Japanese instructions (curriculum must carry *_ja glosses)
  python3 -m audiolesson.cli generate -c "$CURRICULUM" -l "$LEARNER" -o "$OUT" -m "$MINUTES" -p "$PROFILE" ${AUTO:+--auto} ${KNOWN:+--known "$KNOWN"} "$@"
  echo
  echo "After listening: python3 -m audiolesson.cli report -l $LEARNER [--failed id,id]"
fi
