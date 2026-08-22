from datetime import date

from arancel_mx.benchmark.classification import (
    ClassificationBenchmarkCase,
    ClassificationPrediction,
    evaluate_classification_benchmark,
)


def test_benchmark_reports_top_k_coverage_and_abstention_without_a_legal_decision():
    cases = [
        ClassificationBenchmarkCase(
            case_id="ligie-85171301",
            release_tag="data-2026.08.17",
            query="Teléfonos inteligentes",
            gold_tariff_code="85171301",
            evidence_urls=("https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html",),
            reviewed_by="reviewer-1",
            reviewed_at=date(2026, 8, 22),
        ),
        ClassificationBenchmarkCase(
            case_id="ligie-85171401",
            release_tag="data-2026.08.17",
            query="Aparatos telefónicos para redes celulares",
            gold_tariff_code="85171401",
            evidence_urls=("https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html",),
            reviewed_by="reviewer-1",
            reviewed_at=date(2026, 8, 22),
        ),
    ]
    predictions = [
        ClassificationPrediction(
            case_id="ligie-85171301",
            candidate_codes=("85171301", "85171401"),
            abstained=False,
            evidence_urls=("https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html",),
        ),
        ClassificationPrediction(
            case_id="ligie-85171401",
            candidate_codes=(),
            abstained=True,
            evidence_urls=(),
        ),
    ]

    result = evaluate_classification_benchmark(cases, predictions, top_k=2)

    assert result == {
        "decision_scope": "classification_hypothesis",
        "total_cases": 2,
        "answered_cases": 1,
        "abstentions": 1,
        "coverage": 0.5,
        "top_k_recall": 0.5,
        "selective_top_k_recall": 1.0,
    }


def test_benchmark_rejects_non_abstained_hypotheses_without_evidence():
    try:
        ClassificationPrediction(
            case_id="ligie-85171301",
            candidate_codes=("85171301",),
            abstained=False,
            evidence_urls=(),
        )
    except ValueError as error:
        assert "evidence_urls" in str(error)
    else:
        raise AssertionError("a non-abstained hypothesis must require evidence")
