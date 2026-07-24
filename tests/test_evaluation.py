from __future__ import annotations

import json

import pytest

from persian_morphology.analyzer import Analysis, Analyzer
from scripts.evaluate import (
    DEFAULT_GOLD,
    CaseEvaluation,
    GoldCase,
    evaluate_cases,
    main,
    read_gold,
    summarize,
)


class FixedAnalyzer:
    def __init__(self, analyses: list[str]):
        self.analyses = analyses

    def analyze(
        self,
        text: str,  # noqa: ARG002
        *,
        normalize_input: bool = True,  # noqa: ARG002
        max_analyses: int = 100,  # noqa: ARG002
    ) -> list[Analysis]:
        return [Analysis(value=value, weight=0.0) for value in self.analyses]


def test_gold_corpus_is_valid_and_has_stable_ids() -> None:
    cases = read_gold()
    assert len(cases) == 28
    assert len({case.case_id for case in cases}) == len(cases)
    assert sum(not case.expected for case in cases) == 1
    assert {"ambiguity", "causative", "normalization", "preverb", "rejection"} <= {
        case.category for case in cases
    }


def test_baseline_passes_complete_gold_corpus() -> None:
    evaluations = evaluate_cases(read_gold(), Analyzer())
    summary = summarize(evaluations)
    assert summary.cases == 28
    assert summary.failed == 0
    assert summary.precision == pytest.approx(1.0)
    assert summary.recall == pytest.approx(1.0)
    assert summary.f1 == pytest.approx(1.0)


def test_exact_set_evaluation_detects_unexpected_reading() -> None:
    case = GoldCase(
        case_id="exact-set",
        surface="رفتم",
        expected=frozenset({"رو+V+Past+Ind+P1+Sg"}),
        category="regression",
        source="test",
        pages="",
        status="test",
        notes="",
    )
    [evaluation] = evaluate_cases(
        [case],
        FixedAnalyzer(
            [
                "رو+V+Past+Ind+P1+Sg",
                "رو+V+Pres+Ind+Prog+P1+Sg",
            ]
        ),
    )
    assert isinstance(evaluation, CaseEvaluation)
    assert not evaluation.passed
    assert not evaluation.missing
    assert evaluation.unexpected == frozenset({"رو+V+Pres+Ind+Prog+P1+Sg"})


def test_duplicate_case_id_is_rejected(tmp_path) -> None:
    gold = tmp_path / "duplicate.tsv"
    gold.write_text(
        "\t".join(
            (
                "case_id",
                "surface",
                "expected_analyses",
                "category",
                "source",
                "pages",
                "status",
                "notes",
            )
        )
        + "\n"
        + "duplicate\tرفت\tرو+V+Past+Ind+P3+Sg\ttest\ttest\t\ttest\t\n"
        + "duplicate\tرفتم\tرو+V+Past+Ind+P1+Sg\ttest\ttest\t\ttest\t\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate case_id"):
        read_gold(gold)


def test_cli_json_report(capsys) -> None:
    assert main(["--gold", str(DEFAULT_GOLD), "--category", "ambiguity", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["cases"] == 3
    assert payload["summary"]["failed"] == 0
    assert all(case["passed"] for case in payload["cases"])
