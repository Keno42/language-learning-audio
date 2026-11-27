# Word pairs looked up in Icelandic texts

`pairs.json` says, for each pair of neighbouring words the course says (`pairs`) and each word that stands alone in a line (`words`),
how many corpora of present-day Icelandic have it; 0 means none. It is made by `tools/attest_pairs.py` and read offline by
`audiolesson/trust.py` (the trust check; the owner's rule of 2026-11-28: a line whose every pair is found in texts Icelanders wrote counts
as checked).

## Where the counts come from

The corpora of the Árni Magnússon Institute for Icelandic Studies (Stofnun Árna Magnússonar í íslenskum fræðum), searched through their
public Korp service at https://malheildir.arnastofnun.is:

- Risamálheild, the Icelandic Gigaword Corpus: forums and blogs, news, books, journals, parliament and Wikipedia;
- Mörkuð íslensk málheild (the Tagged Icelandic Corpus): blogs, transcribed speech, e-mail, web texts, newspapers and books;
- the Icelandic side of the parallel corpora: subtitles.

A pair is looked up in everyday writing first (the forums, blogs, speech and subtitles above), then, when none of those has it, in every
corpus listed. Old texts, laws and court rulings are not searched. Only whether a corpus has the pair is asked (the search stops at its
first hit), so a count is a number of corpora, not of occurrences.

## What is kept, and what is not

Only the counts. No sentence or excerpt of any corpus is copied into this repository. The lookup sends the course's own words to the
service, one request at a time with a pause; please keep it so (`--pause`).

## How a line is cut

`audiolesson.trust.parts`: the line's words, lower-cased; punctuation, a digit or a hyphen ends a stretch, so no pair crosses it; a word
alone in its stretch is looked up as a word; a word with a capital letter that does not start a sentence is a proper name (the persona's
«Yuki», «Hekla») and is in no pair.
