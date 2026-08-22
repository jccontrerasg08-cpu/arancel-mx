"""Evaluation contracts for evidence-bound tariff classification hypotheses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re


_TARIFF_CODE = re.compile(r"^\d{8}(?:\d{2})?$")
_DECISION_SCOPE = "classification_hypothesis"


def _nonblank(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-blank string")
    return value.strip()


def _tariff_code(value: str, field: str) -> str:
    code = _nonblank(value, field)
    if not _TARIFF_CODE.fullmatch(code):
        raise ValueError(f"{field} must be an 8- or 10-digit tariff code")
    return code


@dataclass(frozen=True)
class ClassificationBenchmarkCase:
    case_id: str
    release_tag: str
    query: str
    gold_tariff_code: str
    evidence_urls: tuple[str, ...]
    reviewed_by: str
    reviewed_at: date

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _nonblank(self.case_id, "case_id"))
        release_tag = _nonblank(self.release_tag, "release_tag")
        if not re.fullmatch(r"data-\d{4}\.\d{2}\.\d{2}", release_tag):
            raise ValueError("release_tag must reference an immutable data release")
        object.__setattr__(self, "release_tag", release_tag)
        object.__setattr__(self, "query", _nonblank(self.query, "query"))
        object.__setattr__(self, "gold_tariff_code", _tariff_code(self.gold_tariff_code, "gold_tariff_code"))
        if not self.evidence_urls or any(not isinstance(url, str) or not url.startswith("https://") for url in self.evidence_urls):
            raise ValueError("evidence_urls must contain HTTPS evidence")
        object.__setattr__(self, "reviewed_by", _nonblank(self.reviewed_by, "reviewed_by"))
        if not isinstance(self.reviewed_at, date):
            raise ValueError("reviewed_at must be a date")


@dataclass(frozen=True)
class ClassificationPrediction:
    case_id: str
    candidate_codes: tuple[str, ...]
    abstained: bool
    evidence_urls: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _nonblank(self.case_id, "case_id"))
        if not isinstance(self.abstained, bool):
            raise ValueError("abstained must be a boolean")
        codes = tuple(_tariff_code(code, "candidate_codes") for code in self.candidate_codes)
        if len(set(codes)) != len(codes):
            raise ValueError("candidate_codes must be unique")
        if self.abstained and codes:
            raise ValueError("abstained predictions cannot include candidate codes")
        if not self.abstained and not codes:
            raise ValueError("non-abstained predictions require candidate codes")
        if any(not isinstance(url, str) or not url.startswith("https://") for url in self.evidence_urls):
            raise ValueError("prediction evidence_urls must use HTTPS")
        if not self.abstained and not self.evidence_urls:
            raise ValueError("prediction evidence_urls are required for non-abstained hypotheses")
        object.__setattr__(self, "candidate_codes", codes)


def evaluate_classification_benchmark(
    cases: list[ClassificationBenchmarkCase],
    predictions: list[ClassificationPrediction],
    *,
    top_k: int,
) -> dict[str, object]:
    """Evaluate ranked hypotheses while preserving abstention as a first-class result."""
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise ValueError("top_k must be a positive integer")
    if not cases:
        raise ValueError("cases must not be empty")
    case_ids = [case.case_id for case in cases]
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("case_id values must be unique")
    by_case_id = {prediction.case_id: prediction for prediction in predictions}
    if len(by_case_id) != len(predictions) or set(by_case_id) != set(case_ids):
        raise ValueError("predictions must contain exactly one result per case")

    answered = 0
    top_k_hits = 0
    for case in cases:
        prediction = by_case_id[case.case_id]
        if prediction.abstained:
            continue
        answered += 1
        if case.gold_tariff_code in prediction.candidate_codes[:top_k]:
            top_k_hits += 1
    total = len(cases)
    return {
        "decision_scope": _DECISION_SCOPE,
        "total_cases": total,
        "answered_cases": answered,
        "abstentions": total - answered,
        "coverage": answered / total,
        "top_k_recall": top_k_hits / total,
        "selective_top_k_recall": top_k_hits / answered if answered else 0.0,
    }
