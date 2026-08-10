"""Typed results for independent production certification checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CertificationReport:
    """Successful certification result.

    Certification failures raise ``ValueError`` at the first fail-closed boundary;
    a returned report therefore represents a fully successful certification pass.
    """

    passed: bool
    checks: tuple[str, ...]
    row_count: int
