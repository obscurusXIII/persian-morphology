import pytest

from persian_morphology.analyzer import Analyzer


@pytest.fixture(scope="module")
def analyzer() -> Analyzer:
    return Analyzer()


def values(analyzer: Analyzer, word: str) -> set[str]:
    return {result.value for result in analyzer.analyze(word)}


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        # √رو and contextual VI رف: printed pp. 683--685 and 858.
        ("رفت", "رو+V+Past+Ind+P3+Sg"),
        ("رفتم", "رو+V+Past+Ind+P1+Sg"),
        ("رفتن", "رو+V+Inf"),
        ("می‌رفتم", "رو+V+Past+Ind+Prog+P1+Sg"),
        ("نمی‌روم", "رو+V+Pres+Ind+Prog+Neg+P1+Sg"),
        # Other roots verify that a D-adjacent VI is not used as the lemma.
        ("ساختم", "ساز+V+Past+Ind+P1+Sg"),
        ("دیدیم", "بین+V+Past+Ind+P1+Pl"),
        # Perfect, future, preverb, and causative derivations: pp. 855--864.
        ("رفته‌ام", "رو+V+Pres+Ind+Perf+P1+Sg"),
        ("نرفته بودم", "رو+V+Past+Ind+Perf+Neg+P1+Sg"),
        ("نخواهم رفت", "رو+V+Fut+Ind+Neg+P1+Sg"),
        ("درنمی‌روند", "رو+V+PV=در+Pres+Ind+Prog+Neg+P3+Pl"),
        ("نمی‌نشاندیم", "نشین+V+Caus+Past+Ind+Prog+Neg+P1+Pl"),
    ],
)
def test_book_backed_golden_analyses(analyzer: Analyzer, surface: str, expected: str) -> None:
    assert expected in values(analyzer, surface)


def test_bare_participle_has_book_internal_perfect_ambiguity(analyzer: Analyzer) -> None:
    # The √باش P3Sg enclitic is zero (printed pp. 678--680).
    assert values(analyzer, "رفته") == {
        "رو+V+Part",
        "رو+V+Pres+Ind+Perf+P3+Sg",
    }


def test_imperative_subjunctive_homography_is_preserved(analyzer: Analyzer) -> None:
    # Printed pp. 680--690 distinguish the structures despite identical 2pl output.
    analyses = values(analyzer, "بخورید")
    assert "خور+V+Imp+P2+Pl" in analyses
    assert "خور+V+Pres+Subj+P2+Pl" in analyses


def test_input_is_normalized_without_changing_morphology(analyzer: Analyzer) -> None:
    assert "رو+V+Pres+Ind+Prog+Neg+P1+Sg" in values(analyzer, "نمي روم")
    assert "رو+V+Pres+Ind+Perf+P1+Sg" in values(analyzer, "رفته ام")


def test_refam_is_only_simple_past_in_formal_grammar(analyzer: Analyzer) -> None:
    assert values(analyzer, "رفتم") == {"رو+V+Past+Ind+P1+Sg"}


def test_no_invented_features_or_d_adjacent_lemma(analyzer: Analyzer) -> None:
    forbidden = ("+Pos", "+Act", "+Simple", "+Impf")
    for surface in ("رفتم", "رفته‌ام", "نمی‌روم", "می‌رفتم"):
        analyses = values(analyzer, surface)
        assert analyses
        assert all(not any(tag in item for tag in forbidden) for item in analyses)
        assert all(not item.startswith("رف+") for item in analyses)


def test_contextual_number_impoverishment_is_not_guessed_word_internally(
    analyzer: Analyzer,
) -> None:
    assert "رو+V+Pres+Ind+Prog+Neg+P3+Sg" not in values(analyzer, "نمی‌روند")
