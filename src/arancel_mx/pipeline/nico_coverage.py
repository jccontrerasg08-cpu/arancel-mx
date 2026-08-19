"""Evidence-bound NICO descendant coverage diagnostics for official releases."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


_POLICY_VERSION = "nico-coverage-v1"
_TOTOABA_DOF_URL = "https://www.dof.gob.mx/nota_detalle.php?codigo=5763398&fecha=21/07/2025"
_TOTOABA_DOI_DATE = "2025-07-21"
_KNOWN_UPSTREAM_LAG_CODES = frozenset(
    {
        "03028902",
        "03029904",
        "03038902",
        "03039904",
        "03048901",
        "03048902",
    }
)


def _rows_at_level(
    classifications: Iterable[Mapping[str, Any]], level: str
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(row["code"])
                for row in classifications
                if str(row.get("level", "")) == level
            }
        )
    )


def nico_coverage_report(
    classifications: Iterable[Mapping[str, Any]],
    source_identity: Iterable[Mapping[str, Any]],
) -> dict[str, object]:
    """Describe published NICO descendant coverage without repairing source gaps.

    The only known upstream-lag classification is the six Totoaba fractions added
    by the DOF decree dated 2025-07-21. All other missing descendants remain
    explicitly unclassified until another primary source supports a category.
    """
    rows = tuple(classifications)
    fractions = _rows_at_level(rows, "fraccion8")
    nico_prefixes = {code[:8] for code in _rows_at_level(rows, "nico10")}
    missing = tuple(code for code in fractions if code not in nico_prefixes)
    known_upstream_lag = tuple(
        code for code in missing if code in _KNOWN_UPSTREAM_LAG_CODES
    )
    unclassified = tuple(code for code in missing if code not in _KNOWN_UPSTREAM_LAG_CODES)
    inputs = tuple(
        sorted(
            (
                dict(item)
                for item in source_identity
                if item.get("dataset_key") in {"ligie", "nico"}
                and item.get("document_role")
                in {"ligie_snapshot", "nico_snapshot"}
            ),
            key=lambda item: (str(item["dataset_key"]), str(item["document_role"])),
        )
    )
    if {str(item["dataset_key"]) for item in inputs} != {"ligie", "nico"}:
        raise ValueError("NICO coverage requires one LIGIE and one NICO source identity")

    return {
        "policy_version": _POLICY_VERSION,
        "source_identity": inputs,
        "counts": {
            "fraccion8": len(fractions),
            "with_nico_descendant": len(fractions) - len(missing),
            "missing_nico_descendant": len(missing),
            "known_upstream_lag": len(known_upstream_lag),
            "unclassified_missing": len(unclassified),
        },
        "known_upstream_lag": {
            "evidence_url": _TOTOABA_DOF_URL,
            "published_at": _TOTOABA_DOI_DATE,
            "codes": known_upstream_lag,
        },
        "unclassified_missing": unclassified,
    }
