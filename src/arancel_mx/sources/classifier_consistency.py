"""Cross-check tariff classifier pages expose consistent fraction data."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from arancel_mx.sources.siicex import SiicexFractionDocument
from arancel_mx.sources.vucem import VucemFractionSheet


REFERENCE_FRACTION_CODE = "90014002"


@dataclass(frozen=True)
class ClassifierRecord:
    source: str
    code: str
    description: str
    import_duty: str | None
    export_duty: str | None


def _fold(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", " ".join(str(value or "").split()))
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def normalize_duty(value: str | None) -> str:
    if value is None:
        return ""
    folded = _fold(value).replace(".", "")
    if folded in {"ex", "exento", "exenta"}:
        return "ex"
    match = re.search(r"(\d+(?:[.,]\d+)?)", folded)
    return match.group(1).replace(",", ".") if match else folded


def description_tokens(value: str) -> set[str]:
    stopwords = {
        "de",
        "la",
        "el",
        "los",
        "las",
        "y",
        "o",
        "a",
        "en",
        "para",
        "con",
        "sin",
        "del",
        "al",
        "por",
        "un",
        "una",
        "que",
        "se",
        "su",
    }
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", _fold(value))
        if len(token) > 2 and token not in stopwords
    }
    return tokens


def descriptions_consistent(left: str, right: str) -> bool:
    left_folded = _fold(left)
    right_folded = _fold(right)
    if left_folded in right_folded or right_folded in left_folded:
        return True
    left_tokens = description_tokens(left)
    right_tokens = description_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    overlap = left_tokens & right_tokens
    minimum = min(len(left_tokens), len(right_tokens))
    return len(overlap) >= max(2, minimum // 2)


def classifier_record_from_vucem(sheet: VucemFractionSheet) -> ClassifierRecord:
    return ClassifierRecord(
        source="vucem",
        code=sheet.code,
        description=sheet.description,
        import_duty=sheet.import_duty,
        export_duty=sheet.export_duty,
    )


def classifier_record_from_siicex(document: SiicexFractionDocument) -> ClassifierRecord:
    return ClassifierRecord(
        source="siicex",
        code=document.code,
        description=document.description,
        import_duty=document.import_duty,
        export_duty=document.export_duty,
    )


def compare_classifier_records(
    left: ClassifierRecord,
    right: ClassifierRecord,
) -> list[str]:
    """Return human-readable discrepancies when two classifier records disagree."""
    discrepancies: list[str] = []
    if left.code != right.code:
        discrepancies.append(f"code mismatch: {left.source}={left.code} {right.source}={right.code}")
    if not descriptions_consistent(left.description, right.description):
        discrepancies.append(
            "description mismatch: "
            f"{left.source}={left.description!r} {right.source}={right.description!r}"
        )
    if normalize_duty(left.import_duty) != normalize_duty(right.import_duty):
        discrepancies.append(
            "import duty mismatch: "
            f"{left.source}={left.import_duty!r} {right.source}={right.import_duty!r}"
        )
    if normalize_duty(left.export_duty) != normalize_duty(right.export_duty):
        discrepancies.append(
            "export duty mismatch: "
            f"{left.source}={left.export_duty!r} {right.source}={right.export_duty!r}"
        )
    return discrepancies


def compare_vucem_and_siicex_fractions(
    vucem: VucemFractionSheet,
    siicex: SiicexFractionDocument,
) -> list[str]:
    return compare_classifier_records(
        classifier_record_from_vucem(vucem),
        classifier_record_from_siicex(siicex),
    )
