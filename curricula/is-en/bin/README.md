# BÍN lookups for the Icelandic course

`forms.json` is a cache of lookups in **BÍN** (Beygingarlýsing íslensks nútímamáls), made by `tools/bin_lookup.py`. It lets
`audiolesson validate` check, offline, that every close variant (`variant_of`) and its base are forms of the same lemma (#218).
Nothing from BÍN is copied into the curriculum's TOML.

## Licence and attribution

BÍN's data is licensed under **CC BY-SA 4.0** (https://creativecommons.org/licenses/by-sa/4.0/). This directory is therefore
kept apart from the rest of the curriculum, and `forms.json` is shared under the same licence.

> Beygingarlýsing íslensks nútímamáls. Stofnun Árna Magnússonar í íslenskum fræðum. Höfundur og ritstjóri Kristín Bjarnadóttir.
> https://bin.arnastofnun.is

## What was changed

- A **subset**: only the forms of the curriculum's variant items and their bases, not BÍN's paradigms.
- **Fewer fields**: `lemma`, `guid`, `ofl` (word class), `kyn` (gender), `tag` (the form's grammatical tag, e.g. `ÞFET`), and
  `checked_on` (the date of the lookup).
- An **ambiguous form** (e.g. «miða» is a form of mið, miða and miði) was resolved by hand: the author chose the `guid`.

## Adding a form

```sh
python tools/bin_lookup.py kaffið                    # one form
python tools/bin_lookup.py miða --ofl no --pick <guid>   # an ambiguous one
python tools/bin_lookup.py --variants               # every variant_of item and its base not yet cached
```

One request at a time, with a pause between requests. The network is used only by this tool; `validate` and the tests are offline.
If BÍN says a variant and its base are not one lemma, fix the item; do not skip the check.
