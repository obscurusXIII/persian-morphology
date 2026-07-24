import pytest

from persian_morphology.analyzer import Analyzer
from persian_morphology.generator import Generator


@pytest.fixture(scope="module")
def generator() -> Generator:
    return Generator()


def forms(generator: Generator, analysis: str) -> set[str]:
    return {result.value for result in generator.generate(analysis)}


@pytest.mark.parametrize(
    ("analysis", "surface"),
    [
        ("رو+V+Inf", "رفتن"),
        ("ساز+V+Past+Ind+P1+Sg", "ساختم"),
        ("بین+V+Pres+Ind+Prog+P1+Pl", "می‌بینیم"),
        ("رو+V+Pres+Ind+Perf+P1+Sg", "رفته‌ام"),
        ("رو+V+Past+Ind+Perf+Neg+P1+Sg", "نرفته بودم"),
        ("رو+V+Fut+Ind+Neg+P1+Sg", "نخواهم رفت"),
        ("رو+V+PV=در+Pres+Ind+Prog+Neg+P3+Pl", "درنمی‌روند"),
        ("نشین+V+Caus+Past+Ind+Prog+Neg+P1+Pl", "نمی‌نشاندیم"),
        ("خور+V+Imp+P2+Pl", "بخورید"),
        ("خور+V+Pres+Subj+P2+Pl", "بخورید"),
    ],
)
def test_generate_book_backed_forms(generator: Generator, analysis: str, surface: str) -> None:
    assert surface in forms(generator, analysis)


def test_obsolete_invented_analysis_is_rejected(generator: Generator) -> None:
    assert not forms(generator, "رف+V+Past+Ind+Pos+Act+P1+Sg")


@pytest.mark.parametrize(
    ("analysis", "surface"),
    [
        ("رو+V+Past+Ind+P1+Sg", "رفتم"),
        ("رو+V+Pres+Ind+Perf+P1+Sg", "رفته‌ام"),
        ("رو+V+PV=در+Pres+Ind+Prog+Neg+P3+Pl", "درنمی‌روند"),
        ("نشین+V+Caus+Past+Ind+Prog+Neg+P1+Pl", "نمی‌نشاندیم"),
    ],
)
def test_round_trip(analysis: str, surface: str, generator: Generator) -> None:
    analyzer = Analyzer()
    assert surface in forms(generator, analysis)
    assert analysis in {result.value for result in analyzer.analyze(surface)}
