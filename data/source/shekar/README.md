# Shekar verb data

`verbs.csv` is the verb-stem inventory distributed with the Shekar Persian NLP
project. This snapshot has 365 source rows and four columns:

```text
present_stem,past_stem,informal_present_stem,informal_past_stem
```

Upstream repository: <https://github.com/amirivojdan/shekar>

The project keeps this source snapshot unchanged. `scripts/prepare_verbs.py`
normalizes and deduplicates it into `data/lexicon/verbs.tsv`.
