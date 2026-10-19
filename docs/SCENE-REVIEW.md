# The scene check (the brief)

A pattern («Ég nenni ekki að {inf}.») makes a sentence with every word its slot takes. Grammatical is not enough: the
learner must be able to picture someone saying it. «Ég nenni ekki að sofa.» ("I can't be bothered to sleep") was hard
to picture in lesson 27. «Má ég sofa?» (#333), «Áttu leigubíl?» (#192) and a bus «to the bus stop» (#336) were found
the same way, by chance, one at a time. The check judges every sentence once, before the lessons reach it
(LEARNING-DESIGN §9 "Good enough overall").

Each verdict is on one word (fill) of one pattern, in `curricula/is-en/95-scenes.toml` (format: `docs/CURRICULUM.md`
"The scene check"):

- **a scene in one line**: the sentence is something a traveller would say there. The lesson uses the line as the cue
  («It's raining hard, and your friend suggests a walk. Say: I can't be bothered to go out.»);
- **`false`**: no scene a traveller is in. The sentence is never generated.

When the scene does not depend on the word («Your friend asks what time it is.» for every hour), it is written once for
the pattern, as `"*"`. A word's own verdict overrides it. A word without one takes it, a word tagged later included, so
nobody reviews those sentences again: `audiolesson validate` counts them, and the sheet below lists them.

A sentence with no verdict is still generated, as before. `audiolesson validate` counts them.

## How to run it

1. Print the sheet. The patterns and words the learner has met first, since those are what the lessons generate now:

   ```sh
   python -m audiolesson.cli scene-check curricula/is-en --learner LEARNER.json > scene-sheet.toml
   ```

   Without `--learner`, every pattern; `--pattern ID` for one. Each line is a fill with its sentence and meaning as a
   comment, and an empty verdict (`""`) to write. A fill its pattern's `"*"` line covers is not on it.
   `--judged` prints the verdicts already given too: the pattern's `"*"` line first, and each fill it covers as a comment
   (`# kaffi: the pattern's line`), so the table pasted back leaves them covered.
2. Give the sheet and the prompt below to a reviewer: the owner, or a model (another company's, as for
   `docs/DOC-REVIEW.md`, so the author of the patterns does not judge its own sentences).
3. Paste the filled tables into `95-scenes.toml` in one PR. `validate` checks that each fill is one of the pattern's.
   Lines left `""` are dropped; they stay unjudged.

The sheet holds no trip profile: only course sentences.

## The prompt

> You are checking sentences for a course of daily audio lessons in Icelandic, for one adult learner preparing for a
> trip to Iceland. Each line of the attached TOML is one sentence a pattern makes, as a comment: the Icelandic and its
> English meaning.
>
> For each line, decide whether a traveller in Iceland (or someone talking with Icelanders) could plausibly say this
> sentence, and where:
>
> - If yes, replace `""` with **one short line describing the scene** in English, where the sentence would be said, in
>   the second person and present tense, without saying the sentence itself. Example: for «Ég nenni ekki að fara út.»
>   ("I can't be bothered to go out"): `"It's raining hard, and your friend suggests a walk."`
> - If no scene comes to mind that a learner would recognise, write `false`. Examples: «Má ég sofa?» ("May I sleep?":
>   a traveller does not ask permission to sleep); «Fer þessi strætó á stoppistöðina?» ("Does this bus go to the bus
>   stop?").
> - Add a short comment after a `false` saying why.
> - A line `"*" = "…"` is the scene for every sentence of the table without a line of its own; the sentences it covers are
>   listed as comments (`# kaffi: the pattern's line`). If the scene does not fit one of them, write that one's own line or
>   `false` in place of the comment.
>
> Don't correct the Icelandic or the meanings; report a wrong one in a comment instead. Keep the TOML valid: one
> verdict per line, the table headers unchanged.
