---
title: Persian Verbal Morphology
emoji: 🌿
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
suggested_hardware: cpu-basic
---

# Persian Morphology

An HFST analyzer/generator for the formal Persian verbal structures described
in the supplied chapter of *صرف در نحو* by Mazdak Anousheh.  Shekar contributes
formal lexical pairs only; it is not the source of the morphological analysis.

The central lexical distinction follows the book: the analysis uses an
abstract root, while contextual Vocabulary Items realize it.  Thus `رفتـ` is
the VI selected beside dental D, but the root in an analysis is `رو`:

```text
رفتم  →  رو+V+Past+Ind+P1+Sg
```

## Install and build

```bash
uv sync
uv run python main.py build
```

This pipeline:

1. converts Shekar's formal pairs into `data/lexicon/verbs.tsv`;
2. expands the rules in `fst/src/book_rules.tsv` into
   `fst/generated/verbs.lexc`;
3. compiles lexc and `fst/src/phonology.twol` with HFST;
4. writes optimized analyzer/generator transducers under `fst/artifacts/`.

Informal source columns are intentionally not compiled.

## Terminal use

```bash
uv run python main.py analyze رفتم
uv run python main.py analyze نمی‌روم
uv run python main.py analyze رفته‌ام
uv run python main.py analyze 'نرفته بودم'
uv run python main.py generate 'رو+V+Past+Ind+P1+Sg'
uv run python main.py normalize 'رفته ام'
```

Representative output:

```text
$ uv run python main.py analyze رفتم
رو+V+Past+Ind+P1+Sg    0

$ uv run python main.py analyze نمی‌روم
رو+V+Pres+Ind+Prog+Neg+P1+Sg    0

$ uv run python main.py analyze رفته
رو+V+Part    0
رو+V+Pres+Ind+Perf+P3+Sg    0
```

`رفته` is intentionally ambiguous: the chapter's present-indicative 3sg
enclitic of `√باش` is zero.  Likewise, forms such as `بخورید` retain distinct
imperative and subjunctive analyses.

## Analysis tags

The canonical order is:

```text
ROOT + V [+ PV] [+ Caus] + tense/mood/aspect [+ Neg] + person + number
```

- nonfinite: `+Inf`, `+Part`
- tense: `+Past`, `+Pres`, `+Fut`
- mood: `+Ind`, `+Subj`, `+Imp`
- aspect: `+Prog`, `+Perf`
- polarity: only negative is marked, with `+Neg`
- agreement: `+P1/+P2/+P3` and `+Sg/+Pl`
- `+PV=در` etc. is implementation notation for the book's separately merged
  preverb/nonverbal predicate

There are no invented `+Pos`, `+Act`, `+Simple`, or `+Impf` tags.  The volume
defers a full analysis of voice/passive and several complex aspect/mood
combinations, so those paradigms are not guessed here.

## Current formal coverage

- infinitive and participle as DAn and De;
- simple past and past progressive;
- present indicative progressive;
- present subjunctive and imperative;
- present perfect and past perfect;
- analytic future with `خواه`;
- negative forms;
- person/number agreement;
- source-supported preverbs;
- source-supported productive causatives with a separate `+Caus` node;
- root allomorphy and dental `د/ت` realization.

The analyzer is word/fixed-verbal-string based, not a sentence parser.  The
book's contextually singular uses of number-underspecified `ـیم/ـید/ـند`
therefore require a later syntactic layer; an isolated form receives its
ordinary plural analysis.

## Tests

```bash
uv run pytest
```

The test session rebuilds both transducers and checks book-cited golden forms,
ambiguities, rejected obsolete tags, normalization, generation, and round trips.

## Gold evaluation

The editable corpus at `tests/data/gold_verbs.tsv` stores one surface form and
its complete expected analysis set per row, together with its category, source
pages, review status, and notes. Separate legitimate analyses with `|`; use
`∅` when the expected result is no analysis.

Run exact-set evaluation with:

```bash
uv run python scripts/evaluate.py
```

An evaluation case passes only when the analyzer returns exactly the expected
set. This means both missing analyses and unjustified additional analyses are
failures. Useful options include:

```bash
uv run python scripts/evaluate.py --show-passes
uv run python scripts/evaluate.py --category ambiguity
uv run python scripts/evaluate.py --status professor-confirmed
uv run python scripts/evaluate.py --json
```

The linguistic cases in the initial corpus are book-derived; normalization and
rejection cases are marked `implementation-derived`. The `status` field can
later be changed to values such as `professor-confirmed` without modifying the
evaluator.

## Web interface

```bash
uv run python main.py serve --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000>. The single-page interface exposes both the
analyzer and generator and shows normalization changes, ambiguity, individual
feature tags, and HFST weights. FastAPI documentation is available at
<http://localhost:8000/docs>.

The public API is deliberately small:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | container liveness and application version |
| `GET` | `/api/capabilities` | implemented and deferred linguistic scope |
| `POST` | `/api/normalize` | conservative Persian Unicode normalization |
| `POST` | `/api/analyze` | surface form to all licensed analyses |
| `POST` | `/api/generate` | analysis to all licensed surface forms |

For example:

```bash
curl -s http://localhost:8000/api/analyze \
  -H 'content-type: application/json' \
  -d '{"text":"نمی‌روم"}'
```

## Docker

The production image contains only the application, static interface, and
precompiled analyzer/generator artifacts. It does not rebuild the grammar at
container startup.

```bash
docker build -t persian-morphology .
docker run --rm -p 7860:7860 persian-morphology
```

Then open <http://localhost:7860> or check
<http://localhost:7860/health>.

## Hugging Face Spaces

This repository is ready for a Docker Space. The metadata block at the top of
this README selects the Docker SDK and port `7860`; CPU Basic is sufficient.
No application secrets or persistent storage are required.

1. Create a new Hugging Face Space and choose **Docker** as its SDK.
2. Add the Space repository as another Git remote.
3. Push the reviewed `main` branch to the Space.

```bash
git remote add space https://huggingface.co/spaces/YOUR_NAME/YOUR_SPACE
git push space main
```

Use a Hugging Face write token when Git asks you to authenticate; do not store
the token in this repository. Every push to the Space triggers a rebuild.
