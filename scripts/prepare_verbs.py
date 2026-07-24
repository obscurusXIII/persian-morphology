#!/usr/bin/env python3
"""Convert Shekar's formal verb pairs into a DM Vocabulary-Item table.

The source columns are conventionally called present and past "stems".  The
chapter rejects that synchronic analysis.  Here they are decomposed into an
abstract root, contextual root VIs, the dental exponent D, and (where the data
supports the relation) the causative exponent -an-.
"""

from __future__ import annotations

import argparse
import csv
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "source" / "shekar" / "verbs.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "lexicon" / "verbs.tsv"

PREFIXES = tuple(
    sorted(
        (
            "به‌در",
            "دربر",
            "پیش‌",
            "پیش",
            "پس‌",
            "پس",
            "فرو",
            "فرا",
            "باز",
            "بر",
            "در",
            "وا",
            "ور",
        ),
        key=len,
        reverse=True,
    )
)

# Lexical roots which merely begin like one of the productive preverbs.
PREFIX_EXCEPTIONS = {
    "بر",
    "برد",
    "برید",
    "درخش",
    "درخشید",
    "درخشان",
    "درخشاند",
    "درنگ",
    "درنگید",
    "فروش",
    "فروخت",
    "فروز",
    "فروزاند",
    "ورز",
    "ورزید",
}

# Chapter pp. 683--685: the abstract root is √رو and the VI رف is selected
# next to dental morphology.  The same logic identifies √آی behind آ/آمد.
ROOT_OVERRIDES = {"آ": "آی"}

FIELDS = (
    "root",
    "infinitive",
    "preverb",
    "elsewhere_vi",
    "before_d_vi",
    "causative",
    "d_surface",
    "formal_present_source",
    "formal_past_source",
    "source",
)


def canonical(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip()).replace("ي", "ی").replace("ك", "ک")


def matching_preverb(present_form: str, past_form: str) -> str:
    if present_form in PREFIX_EXCEPTIONS or past_form in PREFIX_EXCEPTIONS:
        return ""
    for prefix in PREFIXES:
        if (
            present_form.startswith(prefix)
            and past_form.startswith(prefix)
            and len(present_form) > len(prefix)
            and len(past_form) > len(prefix) + 1
        ):
            return prefix
    return ""


def read_source(path: Path) -> list[tuple[str, str]]:
    """Read only Shekar's formal columns; informal data is deliberately excluded."""

    rows: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8", newline="") as source:
        for line_number, row in enumerate(csv.reader(source), start=1):
            if len(row) != 4:
                raise ValueError(f"{path}:{line_number}: expected four columns, got {len(row)}")
            present, past, _informal_present, _informal_past = map(canonical, row)
            if not present or not past:
                raise ValueError(f"{path}:{line_number}: formal columns may not be empty")
            if not past.endswith(("د", "ت")):
                raise ValueError(f"{path}:{line_number}: past form lacks final D: {past!r}")
            rows.add((present, past))
    return sorted(rows, key=lambda row: (row[1] + "ن", row[0]))


def split_source(row: tuple[str, str]) -> dict[str, str]:
    present, past = row
    preverb = matching_preverb(present, past)
    return {
        "present": present,
        "past": past,
        "preverb": preverb,
        "present_base": present[len(preverb) :] if preverb else present,
        "past_base": past[len(preverb) :] if preverb else past,
    }


def causative_base(
    item: dict[str, str], available_elsewhere_vis: set[str]
) -> tuple[str, str] | None:
    """Return (abstract root, root VI) for source-supported -an- causatives.

    This deliberately does not guess from spelling alone.  A matching
    non-causative VI must occur in the source.  √نشین : نش-ان-D is the
    chapter's contextual-allomorph pattern and is the one explicit irregular
    mapping needed by these data.
    """

    present_base = item["present_base"]
    past_base = item["past_base"]
    if not (present_base.endswith("ان") and past_base.endswith(("اند", "انت"))):
        return None
    if present_base != past_base[:-1]:
        return None

    root_vi = present_base[:-2]
    if root_vi in available_elsewhere_vis:
        return (ROOT_OVERRIDES.get(root_vi, root_vi), root_vi)
    if root_vi == "نش" and "نشین" in available_elsewhere_vis:
        return ("نشین", root_vi)
    return None


def convert_rows(rows: list[tuple[str, str]]) -> list[dict[str, str]]:
    split = [split_source(row) for row in rows]
    available_elsewhere_vis = {item["present_base"] for item in split}
    converted: list[dict[str, str]] = []

    for item in split:
        present_base = item["present_base"]
        past_base = item["past_base"]
        causative = causative_base(item, available_elsewhere_vis)
        if causative:
            root, root_vi = causative
            elsewhere_vi = before_d_vi = root_vi
            causative_value = "ان"
        else:
            root = ROOT_OVERRIDES.get(present_base, present_base)
            elsewhere_vi = present_base
            before_d_vi = past_base[:-1]
            causative_value = ""

        converted.append(
            {
                "root": root,
                "infinitive": item["past"] + "ن",
                "preverb": item["preverb"],
                "elsewhere_vi": elsewhere_vi,
                "before_d_vi": before_d_vi,
                "causative": causative_value,
                "d_surface": past_base[-1],
                "formal_present_source": item["present"],
                "formal_past_source": item["past"],
                "source": "shekar",
            }
        )

    return converted


def prepare(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> int:
    converted = convert_rows(read_source(input_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(converted)
    return len(converted)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    count = prepare(args.input, args.output)
    print(f"wrote {count} unique formal verb rows to {args.output}")


if __name__ == "__main__":
    main()
