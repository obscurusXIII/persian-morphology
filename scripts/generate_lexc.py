#!/usr/bin/env python3
"""Generate and compile the chapter-backed Persian verbal transducers.

The generated lexc is an explicit finite expansion of the DM rules recorded in
``fst/src/book_rules.tsv``.  Expansion keeps the runtime transducer simple while
the lexical representation remains root + morphosyntactic features.
"""

from __future__ import annotations

import argparse
import csv
import re
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "lexicon" / "verbs.tsv"
DEFAULT_LEXC = PROJECT_ROOT / "fst" / "generated" / "verbs.lexc"
DEFAULT_ARTIFACTS = PROJECT_ROOT / "fst" / "artifacts"
DEFAULT_PHONOLOGY = PROJECT_ROOT / "fst" / "src" / "phonology.twol"
ZWNJ = "\u200c"

# The chapter assigns number to م/ی/د and the past 3sg zero, but analyzes
# یم/ید/ند as person-marked and number-underspecified (printed pp. 657--664).
# A word-only analyzer returns their ordinary plural parse.  Contextually
# licensed singular readings require the external subject/syntax and are
# recorded in book_rules.tsv rather than guessed from an isolated token.
PAST_AGREEMENT = (
    ("P1", "Sg", "م"),
    ("P2", "Sg", "ی"),
    ("P3", "Sg", ""),
    ("P1", "Pl", "یم"),
    ("P2", "Pl", "ید"),
    ("P3", "Pl", "ند"),
)

PRESENT_AGREEMENT = (
    ("P1", "Sg", "م"),
    ("P2", "Sg", "ی"),
    ("P3", "Sg", "د"),
    ("P1", "Pl", "یم"),
    ("P2", "Pl", "ید"),
    ("P3", "Pl", "ند"),
)

PERFECT_AGREEMENT = (
    ("P1", "Sg", "ام"),
    ("P2", "Sg", "ای"),
    ("P3", "Sg", ""),
    ("P1", "Pl", "ایم"),
    ("P2", "Pl", "اید"),
    ("P3", "Pl", "اند"),
)

BASE_MULTICHAR_SYMBOLS = (
    "+V",
    "+Inf",
    "+Part",
    "+Past",
    "+Pres",
    "+Fut",
    "+Ind",
    "+Subj",
    "+Imp",
    "+Prog",
    "+Perf",
    "+Neg",
    "+Caus",
    "+P1",
    "+P2",
    "+P3",
    "+Sg",
    "+Pl",
    "Dvd",
    "Dvl",
)


def analysis(root: str, *tags: str) -> str:
    return root + "".join(f"+{tag}" for tag in tags)


def vowel_final(stem: str) -> bool:
    return stem.endswith(("ا", "آ"))


def with_agreement(stem: str, suffix: str) -> str:
    return stem + ("ی" if vowel_final(stem) and suffix else "") + suffix


def negative_initial(stem: str) -> str:
    """Realize negative nE- with the chapter's written hiatus alternations."""

    if stem.startswith("آ"):
        return "نیا" + stem[1:]
    if stem.startswith("ایست"):
        return "ن" + stem
    if stem.startswith("ا"):
        return "نی" + stem[1:]
    return "ن" + stem


def subjunctive_initial(stem: str) -> str:
    if stem.startswith("آ"):
        return "بیا" + stem[1:]
    if stem.startswith("ایست"):
        return "ب" + stem
    if stem.startswith("ا"):
        return "بی" + stem[1:]
    return "ب" + stem


def read_verbs(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def d_archisymbol(verb: dict[str, str]) -> str:
    if verb["d_surface"] == "د":
        return "Dvd"
    if verb["d_surface"] == "ت":
        return "Dvl"
    raise ValueError(f"unrecognized D realization in {verb['infinitive']!r}")


def forms_for_verb(verb: dict[str, str]) -> set[tuple[str, str]]:
    root = verb["root"]
    preverb = verb["preverb"]
    causative = verb["causative"]
    elsewhere = verb["elsewhere_vi"] + causative
    before_d = verb["before_d_vi"] + causative + d_archisymbol(verb)
    lexical_prefix = ["V"]
    if preverb:
        # +PV= is analyzer notation for the chapter's separately merged
        # nonverbal predicate/preverb; it is not part of the abstract root.
        lexical_prefix.append(f"PV={preverb}")
    if causative:
        lexical_prefix.append("Caus")

    forms: set[tuple[str, str]] = set()

    def add(surface: str, *tags: str) -> None:
        forms.add((analysis(root, *lexical_prefix, *tags), surface))

    # DAn and De: infinitive and participle (printed pp. 844--858).
    add(preverb + before_d + "ن", "Inf")
    add(preverb + before_d + "ه", "Part")

    # Past and past progressive.  Positive polarity has no exponent/tag.
    for person, number, suffix in PAST_AGREEMENT:
        add(preverb + before_d + suffix, "Past", "Ind", person, number)
        add(
            preverb + negative_initial(before_d) + suffix,
            "Past",
            "Ind",
            "Neg",
            person,
            number,
        )
        add(
            preverb + "می" + ZWNJ + before_d + suffix,
            "Past",
            "Ind",
            "Prog",
            person,
            number,
        )
        add(
            preverb + "نمی" + ZWNJ + before_d + suffix,
            "Past",
            "Ind",
            "Prog",
            "Neg",
            person,
            number,
        )

    # The chapter's general present indicative derivation contains ProgP/می-.
    # Bare stative presents require lexical/compound information not in this
    # source and are therefore not generalized to every verb.
    for person, number, suffix in PRESENT_AGREEMENT:
        add(
            preverb + "می" + ZWNJ + with_agreement(elsewhere, suffix),
            "Pres",
            "Ind",
            "Prog",
            person,
            number,
        )
        add(
            preverb + "نمی" + ZWNJ + with_agreement(elsewhere, suffix),
            "Pres",
            "Ind",
            "Prog",
            "Neg",
            person,
            number,
        )

        positive_subjunctive = (
            preverb + with_agreement(elsewhere, suffix)
            if preverb
            else with_agreement(subjunctive_initial(elsewhere), suffix)
        )
        negative_subjunctive = preverb + with_agreement(negative_initial(elsewhere), suffix)
        add(positive_subjunctive, "Pres", "Subj", person, number)
        add(negative_subjunctive, "Pres", "Subj", "Neg", person, number)

    # Imperative 2sg has zero agreement; 2pl ید is homophonous with the
    # corresponding subjunctive in forms such as بخورید (pp. 680--690).
    for number, suffix in (("Sg", ""), ("Pl", "ید")):
        positive = (
            preverb + with_agreement(elsewhere, suffix)
            if preverb
            else with_agreement(subjunctive_initial(elsewhere), suffix)
        )
        negative = preverb + with_agreement(negative_initial(elsewhere), suffix)
        add(positive, "Imp", "P2", number)
        add(negative, "Imp", "Neg", "P2", number)

    # Present perfect: De plus a present-indicative enclitic of √باش.  The
    # chapter gives zero for 3sg, so a bare participle is genuinely ambiguous.
    for person, number, clitic in PERFECT_AGREEMENT:
        separator = ZWNJ if clitic else ""
        add(
            preverb + before_d + "ه" + separator + clitic,
            "Pres",
            "Ind",
            "Perf",
            person,
            number,
        )
        add(
            preverb + negative_initial(before_d) + "ه" + separator + clitic,
            "Pres",
            "Ind",
            "Perf",
            "Neg",
            person,
            number,
        )

    # Past perfect: De followed by √باش + D + agreement (pp. 855--861).
    for person, number, suffix in PAST_AGREEMENT:
        add(
            preverb + before_d + "ه بود" + suffix,
            "Past",
            "Ind",
            "Perf",
            person,
            number,
        )
        add(
            preverb + negative_initial(before_d) + "ه بود" + suffix,
            "Past",
            "Ind",
            "Perf",
            "Neg",
            person,
            number,
        )

    # Analytic future: inflected خواه precedes the main verb's truncated
    # infinitive (Part-D in the chapter), e.g. نخواهد رفت (pp. 859--861).
    for person, number, suffix in PRESENT_AGREEMENT:
        add(
            preverb + with_agreement("خواه", suffix) + " " + before_d,
            "Fut",
            "Ind",
            person,
            number,
        )
        add(
            preverb + with_agreement("نخواه", suffix) + " " + before_d,
            "Fut",
            "Ind",
            "Neg",
            person,
            number,
        )

    return forms


def build_entries(verbs: list[dict[str, str]]) -> list[tuple[str, str]]:
    entries: set[tuple[str, str]] = set()
    for verb in verbs:
        entries.update(forms_for_verb(verb))
    return sorted(entries)


def lexc_escape(value: str) -> str:
    """Escape the lexc syntax characters that can occur in generated forms."""

    return value.replace("%", "%%").replace(" ", "% ")


def write_lexc(entries: list[tuple[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    preverb_symbols = sorted(
        {match.group(0) for lexical, _ in entries for match in re.finditer(r"\+PV=[^+]+", lexical)}
    )
    symbols = (*BASE_MULTICHAR_SYMBOLS, *preverb_symbols)
    lines = [
        "! Generated from data/lexicon/verbs.tsv and fst/src/book_rules.tsv.",
        "! Dvd/Dvl are orthographic classes of the chapter's single dental D.",
        "Multichar_Symbols",
        "    " + " ".join(symbols),
        "",
        "LEXICON Root",
    ]
    lines.extend(
        f"{lexc_escape(lexical)}:{lexc_escape(surface)} # ;" for lexical, surface in entries
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compile_phonology(path: Path):
    """Compile the dental twol layer and return it as an HFST transducer."""

    import hfst

    with tempfile.NamedTemporaryFile(suffix=".hfst") as output:
        status = hfst.compile_twolc_file(str(path), output.name, silent=True)
        if status != 0:
            raise RuntimeError(f"could not compile {path}")
        stream = hfst.HfstInputStream(output.name)
        try:
            return stream.read()
        finally:
            stream.close()


def write_optimized(transducer, path: Path) -> None:
    import hfst

    optimized = hfst.HfstTransducer(transducer)
    optimized.convert(hfst.ImplementationType.HFST_OLW_TYPE)
    stream = hfst.HfstOutputStream(filename=str(path), type=optimized.get_type())
    try:
        stream.write(optimized)
    finally:
        stream.close()


def compile_transducers(lexc_path: Path, phonology_path: Path, artifacts: Path) -> None:
    import hfst

    intermediate = hfst.compile_lexc_file(str(lexc_path), output=None)
    if intermediate is None:
        raise RuntimeError(f"could not compile {lexc_path}")

    generator = hfst.HfstTransducer(intermediate)
    generator.compose(compile_phonology(phonology_path))
    generator.minimize()
    analyzer = hfst.HfstTransducer(generator)
    analyzer.invert()
    analyzer.minimize()

    artifacts.mkdir(parents=True, exist_ok=True)
    write_optimized(generator, artifacts / "generator.hfstol")
    write_optimized(analyzer, artifacts / "analyzer.hfstol")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_LEXC)
    parser.add_argument("--phonology", type=Path, default=DEFAULT_PHONOLOGY)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()

    entries = build_entries(read_verbs(args.input))
    write_lexc(entries, args.output)
    print(f"wrote {len(entries)} analysis/surface pairs to {args.output}")
    if args.compile:
        compile_transducers(args.output, args.phonology, args.artifacts)
        print(f"wrote optimized transducers to {args.artifacts}")


if __name__ == "__main__":
    main()
