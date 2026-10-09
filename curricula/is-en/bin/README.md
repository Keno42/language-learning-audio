# BÍN lookups for the Icelandic course

`forms.json` is a cache of lookups in **BÍN** (Beygingarlýsing íslensks nútímamáls), made by `tools/bin_lookup.py` from BÍN's **downloadable
language-technology data** (the form list `SHsnid.csv`), not from the website or its API. It lets `audiolesson validate` check, offline, that
every close variant (`variant_of`) and its base are forms of the same lemma (#218). The check **advises and never blocks**: `validate` warns
when this file is missing, when a form is not in it, or when a pair disagrees (about one line in ten that a native wouldn't quite say is
acceptable for this learner; LEARNING-DESIGN §9 "Good enough overall"). Nothing from BÍN is copied into the curriculum's TOML.

## Licence and attribution

BÍN's language-technology data is distributed under **CC BY-SA 4.0** (https://creativecommons.org/licenses/by-sa/4.0/); copying the
inflection tables shown on the website is not allowed, and the API's terms are stricter, which is why the cache is built from the
downloaded data only. This directory is kept apart from the rest of the curriculum, and `forms.json` is shared under the same licence.

> Beygingarlýsing íslensks nútímamáls. Stofnun Árna Magnússonar í íslenskum fræðum. Höfundur og ritstjóri Kristín Bjarnadóttir.
> https://bin.arnastofnun.is

## What was changed

- A **subset**: only the forms of the curriculum's variant items and their bases, not BÍN's paradigms.
- **Fewer fields**: `lemma`, `guid` (the data file's word id), `ofl` (word class), `tag` (the form's grammatical tags, e.g. `ÞFET`), `source`
  (the file the row came from) and `checked_on` (the date of the lookup).
- An **ambiguous form** (e.g. «miða» is a form of mið, miða and miði) was resolved by hand: the author chose the id.

## Adding a form

Download the form list from BÍN's download page (`SHsnid.csv.zip`). Do not commit it.

```sh
python tools/bin_lookup.py --data SHsnid.csv.zip --variants                      # every variant_of item and its base not yet cached
python tools/bin_lookup.py --data SHsnid.csv.zip kaffið                          # one form
python tools/bin_lookup.py --data SHsnid.csv.zip miða --ofl no --pick <id>       # an ambiguous one
```

The tool reads the file's columns as `lemma; id; word class; domain; form; tag` (`audiolesson/binform.py` `COLUMNS`): check that against BÍN's
"Sjá skýringar" on the first run. No network is used. A warning from `validate` about a pair is a prompt to check the item, not a failure.
