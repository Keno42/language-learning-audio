# The documents' independent review (the brief)

The documents of this repository are written mostly by one LLM, in small additions after each lesson. Left like that,
they grow and keep contradictions (LEARNING-DESIGN §10 "Documents: replace, don't append"). So the owner has them read
by **a model from another company**, which reports what it finds and changes nothing. The fixes are a PR. The owner
settles a disagreement. Run it after every five lessons or so, or when the owner asks.

## How to run it

1. Bundle the documents into one file, each under a header with its path:

   ```sh
   for f in CLAUDE.md docs/CURRENT-POLICY.md docs/CURRENT-STATUS.md docs/LEARNING-DESIGN.md README.md \
            docs/DESIGN.md docs/CURRICULUM.md docs/TRAVEL-CANDO.md docs/LEVERS.md docs/history/evidence.md; do
     printf '\n\n===== %s =====\n\n' "$f"; cat "$f"
   done > doc-review-bundle.md
   ```

   That is about 310,000 characters. The last file holds the older §5 subsections that the current sections cite
   («§5.14»); it is a dated record, read only to check what a citation says. If the model's context is smaller, run
   two passes: the first five files with the last, then the other four with the first pass's report.
2. Optional, and worth it: add the list of open and recently closed issues, with their titles, so the reviewer can
   check what the documents say is open or built. Claude Code can produce it on request.
3. Give the model the prompt below and the bundle. Paste the report into an issue, or give it to Claude Code. Each
   finding is checked against the code and the issues, then fixed in one PR or answered with the reason it stands.

The bundle holds no trip profile, and the reviewer needs none. The documents never contain trip dates, itinerary,
lodging or personal places.

## The prompt

> You are reviewing the design documents of a small software project: a generator of daily audio lessons in
> Icelandic for one learner preparing for a trip. The documents are attached, each under a `===== path =====` header.
> They were written mostly by one AI assistant, adding a little after each lesson, and the owner suspects that later
> additions contradict earlier text that was never removed.
>
> **Your task is to report, not to rewrite.** Find:
>
> 1. **Contradictions:** two statements that cannot both be true now. They may be in one section (a later sentence
>    revising an earlier one), across sections, or across files. Example: one place says a mechanism is not built,
>    another says it was built in a given PR.
> 2. **Stale statements:** text written as current that the documents themselves show has changed, such as a status,
>    a count, a "next" or "not yet" that a later section reports done, or a pointer to a section or issue that says
>    something else.
> 3. **Duplicates:** the same rule or fact stated in two places, so that one copy will drift. Say which copy should
>    stay. "Now" has one home, CURRENT-STATUS.md; a copy of it elsewhere is a duplicate.
> 4. **Accretion:** a paragraph or table cell that has become a chain of dated additions, where one sentence saying
>    how things stand would do.
> 5. **Rules that conflict:** two decisions (LEARNING-DESIGN §9, DESIGN.md, CURRENT-POLICY.md) that would ask for
>    different behaviour in the same case.
>
> **Don't report:**
> - style, wording or English usage, unless it changes the meaning;
> - the Icelandic content;
> - the design choices themselves. Disagreeing with a decision is not a finding. A decision contradicting another one
>   is.
>
> LEARNING-DESIGN §5 is a dated record. A statement there holds for its lesson, and a later lesson may supersede it;
> that is not a contradiction. A §5 statement that a current section (§4, §7, §8, §9) copies or relies on as if still
> true is a finding.
>
> **Report format:** a numbered list, most important first. For each finding:
> - **kind:** contradiction, stale, duplicate, accretion or rule conflict;
> - **where:** each file and section, and a short exact quote from each place;
> - **why:** one or two sentences;
> - **suggested fix:** which text to keep, which to delete or rewrite. Prefer deleting and rewriting to adding.
>
> End with the three sections that would gain most from being rewritten from scratch, and why. If you are unsure
> whether something is a finding, list it at the end under "unsure", with the question that would settle it.

## After the review
- **Accepted findings:** fixed in one PR. The PR names, per finding, what it replaced or deleted.
- **Rejected findings:** answered in the issue with the reason. The owner settles a disagreement.
- **A finding that keeps coming back:** a rule gets a mechanical check in `tests/test_docs.py`, as "Now"'s home and size,
  the §5 references and the paths in `CLAUDE.md`'s reading table have now.
