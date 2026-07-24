import csv
from pathlib import Path

from scripts.prepare_verbs import DEFAULT_INPUT, read_source

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERBS = PROJECT_ROOT / "data" / "lexicon" / "verbs.tsv"


def lexical_rows() -> list[dict[str, str]]:
    with VERBS.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source, delimiter="\t"))


def test_every_formal_source_pair_is_preserved_by_dm_decomposition() -> None:
    rows = lexical_rows()
    assert len(rows) == len(read_source(DEFAULT_INPUT)) == 351
    for row in rows:
        assert (
            row["preverb"] + row["elsewhere_vi"] + row["causative"] == row["formal_present_source"]
        )
        assert (
            row["preverb"] + row["before_d_vi"] + row["causative"] + row["d_surface"]
            == row["formal_past_source"]
        )
        assert row["d_surface"] in {"د", "ت"}


def test_book_root_allomorphs_are_not_flattened() -> None:
    rows = lexical_rows()
    by_infinitive = {row["infinitive"]: row for row in rows}
    assert (
        by_infinitive["رفتن"]
        | {
            "root": "رو",
            "elsewhere_vi": "رو",
            "before_d_vi": "رف",
            "d_surface": "ت",
        }
        == by_infinitive["رفتن"]
    )
    assert by_infinitive["ساختن"]["root"] == "ساز"
    assert by_infinitive["دیدن"]["root"] == "بین"


def test_causative_and_preverb_are_separate_from_root() -> None:
    rows = lexical_rows()
    by_infinitive = {row["infinitive"]: row for row in rows}
    assert by_infinitive["نشاندن"]["root"] == "نشین"
    assert by_infinitive["نشاندن"]["causative"] == "ان"
    assert by_infinitive["دررفتن"]["root"] == "رو"
    assert by_infinitive["دررفتن"]["preverb"] == "در"


def test_lookalikes_are_not_misparsed_as_preverbs() -> None:
    rows = lexical_rows()
    by_infinitive = {row["infinitive"]: row for row in rows}
    for infinitive in ("درخشیدن", "درنگیدن", "ورزیدن"):
        assert by_infinitive[infinitive]["preverb"] == ""
