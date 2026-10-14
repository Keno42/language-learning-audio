# Current status (the short brief)

What is built, what is being evaluated, what is planned. As of 2026-10-14, after lesson 25's feedback. The learning policy is
in `docs/CURRENT-POLICY.md`; the reasons, hypotheses and the lesson-by-lesson evidence are in `docs/LEARNING-DESIGN.md` (LD):
§4 hypotheses, §5 evidence, §7 gaps, §8 the roadmap. When this file and LD §8 differ, LD is the record and this file is
brought back in line. Issues and PRs are `Keno42/language-learning-audio` unless prefixed `bot` (`Keno42/site_update_notifier`).

## Implemented
- **Lessons built around a scene (H4, #149):** a theme in every lesson; the exchange played twice (early with the translation,
  late with only the cue); the partner's lines in variants at natural speed; new material for the theme's next level; scene
  units through the lesson (#273).
- **Expression first (#265):** a part introduced inside its whole (#239, #262); one rule for the role of a learner line in
  every play mode (#263); a part asked through its sentence everywhere, no question whose cue is its answer (#277, #283); a
  near-copy of what was just taught introduced lightly (#280); a fixed phrase linked to its pattern, with `validate`
  failing for an unlinked one (#192, #311); a known pattern with a new word teaches the word in other frames (#311, #316,
  #318).
- **The second half is a rotation of the ear (#248):** heard scene, pick-out, catch the unknown word (#252, #255, #271); the
  pick-out names what to listen for first (#303); the rotation starts even when an item counted toward the target was
  not taught (#294).
- **Speech and timing:** a gap at every change of voice (#301); the slow model word by word at natural speed (#261, #302);
  a hard word's slow, split model (#212, #292); conversation timing (#272); Azure Speech as a provider and as the fallback
  when edge-tts refuses (#299), with sealed secrets for the bot (bot #119).
- **Pace and evidence:** weighted new components as the pace's unit (#218, #235); open items practised every lesson and asked
  at the next review (#162, #205, #220); ease learned from recalls after a long gap, retention counted by gap (#298, bot #118,
  #128); the review backlog's breakdown (bot #123, #125).
- **Nouns:** noun entries with gender and form for every case-tagged noun (#270 step 0 #276, step 1 #317); a known noun's
  unmet frame brought forward (#293); a form named against its basic word.
- **The written review:** asks in its own words, no lesson cue (#312, #314); a first 言えた waits 3 days and the bound also
  defers answered-once entries (bot #133); every review shows a new scene or reading card while the deck has one (bot #132).
- **Tools:** `tools/replay_lesson.py` (the daily read). Open PRs when this was written: rows for the second half and for speech
  touching at a change of voice (#310: #319); `docs/DESIGN.md` split into one topic per line (#281: #320); `audiolesson/text.py` for
  words (#281: #321).

## Being evaluated (built; waiting for three feedbacks without the same remark, LD §8)
- A gap at every change of voice (#301), the «Slowly» model word by word (#302), the pick-out cue (#303), a word met inside a
  known pattern (#311), the review's own wording (#312): first heard in lesson 26 onward; none yet has its three.
- The review backlog (bot #133): the next posts should read about 100 due, and the 3–6 day retention count should grow; the
  14+ day bucket gets its first answers 2–4 weeks after the merge.
- A hard word's slow, split model (#212): no hard word has been new yet.
- Ease from long-gap recalls (#298): read from the retention rows, not from remarks.
- The pace unit stays (decided by the evidence: next-day recall 10/13, 10/13, 10/10 after lessons 22–24).

## Planned, in order (LD §8)
1. **#220's ranking:** choose the review's checks by the lesson time a 言えた would save; the bot's review on its own
   (bot #124) waits for it.
2. **#270 steps 2–3:** a slot asks for a case and the noun gives the form the learner has or is being taught; each scene
   lists its frames and the case each asks; the size and price frames of #311; #198 («heiti potturinn»).
3. **#281 refactoring, behaviour unchanged:** one place for «which sentence holds this part», one for «can the learner say
   this line», then the planner's build loop; each step needs the lesson-21–23 exports replayed byte-identical.
4. Later: #236 (a one-off reply gets several example answers; low priority), #142 (nature and winter safety inside a theme),
   #209 (a fluent speaker reviews the scene content, G10), #208 (this brief).

## Open gaps worth knowing (LD §7)
G6 plausibility rests on slot tags; G7 three schedulers whose sum nobody has examined (the written review's rules are the
current work); G9 long phrases fail most (watch); G10 content is not native-reviewed (#209); G11 less practice for an easy new
item than a hard one is not built.
