#!/usr/bin/env python3
"""Evaluate the HFST analyzer against an editable exact-set gold corpus."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from persian_morphology.analyzer import Analysis, Analyzer  # noqa: E402

DEFAULT_GOLD = PROJECT_ROOT / "tests" / "data" / "gold_verbs.tsv"
ANALYSIS_SEPARATOR = "|"
NO_ANALYSIS = "∅"
REQUIRED_COLUMNS = (
    "case_id",
    "surface",
    "expected_analyses",
    "category",
    "source",
    "pages",
    "status",
    "notes",
)
CASE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class AnalyzerLike(Protocol):
    def analyze(
        self,
        text: str,
        *,
        normalize_input: bool = True,
        max_analyses: int = 100,
    ) -> list[Analysis]: ...


@dataclass(frozen=True, slots=True)
class GoldCase:
    case_id: str
    surface: str
    expected: frozenset[str]
    category: str
    source: str
    pages: str
    status: str
    notes: str


@dataclass(frozen=True, slots=True)
class CaseEvaluation:
    case: GoldCase
    actual: frozenset[str]
    missing: frozenset[str]
    unexpected: frozenset[str]

    @property
    def passed(self) -> bool:
        return not self.missing and not self.unexpected


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    cases: int
    passed: int
    failed: int
    correct_analyses: int
    expected_analyses: int
    actual_analyses: int
    precision: float
    recall: float
    f1: float


def _row_error(path: Path, line_number: int, message: str) -> ValueError:
    return ValueError(f"{path}:{line_number}: {message}")


def read_gold(path: Path = DEFAULT_GOLD) -> list[GoldCase]:
    """Load and validate the editable TSV corpus."""

    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        missing_columns = [
            column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or ())
        ]
        if missing_columns:
            raise ValueError(f"{path}: missing columns: {', '.join(missing_columns)}")

        cases: list[GoldCase] = []
        seen_ids: set[str] = set()
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise _row_error(path, line_number, "too many tab-separated fields")

            values = {column: (row.get(column) or "").strip() for column in REQUIRED_COLUMNS}
            case_id = values["case_id"]
            surface = values["surface"]
            raw_expected = values["expected_analyses"]

            if not case_id:
                raise _row_error(path, line_number, "case_id may not be empty")
            if not CASE_ID.fullmatch(case_id):
                raise _row_error(
                    path,
                    line_number,
                    "case_id must contain only lowercase ASCII letters, digits, and hyphens",
                )
            if case_id in seen_ids:
                raise _row_error(path, line_number, f"duplicate case_id {case_id!r}")
            if not surface:
                raise _row_error(path, line_number, "surface may not be empty")
            if raw_expected == NO_ANALYSIS:
                analyses: list[str] = []
            else:
                if not raw_expected:
                    raise _row_error(
                        path,
                        line_number,
                        f"expected_analyses may not be empty; use {NO_ANALYSIS!r} for rejection",
                    )
                analyses = [item.strip() for item in raw_expected.split(ANALYSIS_SEPARATOR)]
                if any(not item for item in analyses):
                    raise _row_error(path, line_number, "empty analysis around '|' separator")
                if NO_ANALYSIS in analyses:
                    raise _row_error(
                        path,
                        line_number,
                        f"{NO_ANALYSIS!r} must be the only expected value",
                    )
                if len(analyses) != len(set(analyses)):
                    raise _row_error(path, line_number, "duplicate expected analysis")

            seen_ids.add(case_id)
            cases.append(
                GoldCase(
                    case_id=case_id,
                    surface=surface,
                    expected=frozenset(analyses),
                    category=values["category"],
                    source=values["source"],
                    pages=values["pages"],
                    status=values["status"],
                    notes=values["notes"],
                )
            )

    if not cases:
        raise ValueError(f"{path}: gold corpus contains no cases")
    return cases


def evaluate_cases(
    cases: list[GoldCase],
    analyzer: AnalyzerLike,
    *,
    normalize_input: bool = True,
) -> list[CaseEvaluation]:
    """Return exact-set evaluations for all selected cases."""

    evaluations: list[CaseEvaluation] = []
    for case in cases:
        actual = frozenset(
            result.value
            for result in analyzer.analyze(
                case.surface,
                normalize_input=normalize_input,
                max_analyses=1_000,
            )
        )
        evaluations.append(
            CaseEvaluation(
                case=case,
                actual=actual,
                missing=case.expected - actual,
                unexpected=actual - case.expected,
            )
        )
    return evaluations


def summarize(evaluations: list[CaseEvaluation]) -> EvaluationSummary:
    """Compute case accuracy and micro analysis precision/recall."""

    passed = sum(evaluation.passed for evaluation in evaluations)
    correct = sum(len(evaluation.case.expected & evaluation.actual) for evaluation in evaluations)
    expected = sum(len(evaluation.case.expected) for evaluation in evaluations)
    actual = sum(len(evaluation.actual) for evaluation in evaluations)
    precision = correct / actual if actual else 0.0
    recall = correct / expected if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return EvaluationSummary(
        cases=len(evaluations),
        passed=passed,
        failed=len(evaluations) - passed,
        correct_analyses=correct,
        expected_analyses=expected,
        actual_analyses=actual,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def _evaluation_json(evaluation: CaseEvaluation) -> dict[str, object]:
    return {
        "case_id": evaluation.case.case_id,
        "surface": evaluation.case.surface,
        "category": evaluation.case.category,
        "source": evaluation.case.source,
        "pages": evaluation.case.pages,
        "status": evaluation.case.status,
        "notes": evaluation.case.notes,
        "expected": sorted(evaluation.case.expected),
        "actual": sorted(evaluation.actual),
        "missing": sorted(evaluation.missing),
        "unexpected": sorted(evaluation.unexpected),
        "passed": evaluation.passed,
    }


def _print_analysis_set(label: str, analyses: frozenset[str]) -> None:
    print(f"  {label}:")
    if not analyses:
        print("    ∅")
        return
    for analysis in sorted(analyses):
        print(f"    {analysis}")


def print_text_report(
    evaluations: list[CaseEvaluation],
    summary: EvaluationSummary,
    *,
    show_passes: bool = False,
) -> None:
    for evaluation in evaluations:
        if evaluation.passed and not show_passes:
            continue
        label = "PASS" if evaluation.passed else "FAIL"
        print(f"{label}  {evaluation.case.case_id}  {evaluation.case.surface}")
        if evaluation.passed:
            _print_analysis_set("analyses", evaluation.actual)
        else:
            _print_analysis_set("expected", evaluation.case.expected)
            _print_analysis_set("actual", evaluation.actual)
            _print_analysis_set("missing", evaluation.missing)
            _print_analysis_set("unexpected", evaluation.unexpected)

    print(f"Cases: {summary.passed}/{summary.cases} passed")
    print(
        "Analyses: "
        f"precision={summary.precision:.4f} "
        f"recall={summary.recall:.4f} "
        f"f1={summary.f1:.4f}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate analyzer outputs as exact sets against a TSV gold corpus."
    )
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument(
        "--status",
        action="append",
        help="evaluate only this status; repeat to select more than one",
    )
    parser.add_argument(
        "--category",
        action="append",
        help="evaluate only this category; repeat to select more than one",
    )
    parser.add_argument("--no-normalize", action="store_true")
    parser.add_argument("--show-passes", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        cases = read_gold(args.gold)
        if args.status:
            statuses = set(args.status)
            cases = [case for case in cases if case.status in statuses]
        if args.category:
            categories = set(args.category)
            cases = [case for case in cases if case.category in categories]
        if not cases:
            parser.error("the selected filters match no gold cases")

        evaluations = evaluate_cases(
            cases,
            Analyzer(),
            normalize_input=not args.no_normalize,
        )
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    summary = summarize(evaluations)
    if args.json:
        payload = {
            "gold": str(args.gold),
            "summary": {
                "cases": summary.cases,
                "passed": summary.passed,
                "failed": summary.failed,
                "correct_analyses": summary.correct_analyses,
                "expected_analyses": summary.expected_analyses,
                "actual_analyses": summary.actual_analyses,
                "precision": summary.precision,
                "recall": summary.recall,
                "f1": summary.f1,
            },
            "cases": [_evaluation_json(evaluation) for evaluation in evaluations],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_text_report(evaluations, summary, show_passes=args.show_passes)
    return 0 if not summary.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
