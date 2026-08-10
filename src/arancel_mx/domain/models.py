from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuarantinedRow:
    staging_row_id: str
    reason_code: str
    reason_detail: str
    blocking: bool = True


@dataclass(frozen=True)
class ValidationReport:
    publishable: bool
    valid_rows: int
    quarantined: tuple[QuarantinedRow, ...]


@dataclass(frozen=True)
class PromotionSummary:
    tariff_fractions: int = 0
    nicos: int = 0
    proposals: int = 0
    national_notes: int = 0
    indicators: int = 0
