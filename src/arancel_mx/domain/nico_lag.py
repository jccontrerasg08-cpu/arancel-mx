"""Known upstream NICO publication lag. Shared by the pipeline and the CLI.

The official SNICE NICO workbook can lag fractions already present in the
current LIGIE snapshot. These constants name that lag with a primary source.
They do not authorize synthetic NICO codes.
"""

from __future__ import annotations

from collections.abc import Iterable


POLICY_VERSION = "nico-coverage-v1"
TOTOABA_EVIDENCE_URL = "https://dof.gob.mx/nota_detalle.php?codigo=5763398&fecha=21/07/2025"
TOTOABA_PUBLISHED_AT = "2025-07-21"
KNOWN_UPSTREAM_LAG_CODES = frozenset(
    {
        "03028902",
        "03029904",
        "03038902",
        "03039904",
        "03048901",
        "03048902",
    }
)
NOTE = (
    "Missing NICO descendants reflect the published official NICO source. "
    "No synthetic codes are created."
)


def classify_missing_nico(
    codes: Iterable[str],
    *,
    dataset_version: str | None = None,
) -> dict[str, object]:
    """Split missing fraccion8 codes into known upstream lag and everything else."""

    missing = tuple(sorted({str(code) for code in codes}))
    known = tuple(code for code in missing if code in KNOWN_UPSTREAM_LAG_CODES)
    unclassified = tuple(code for code in missing if code not in KNOWN_UPSTREAM_LAG_CODES)
    return {
        "policy": POLICY_VERSION,
        "dataset_version": dataset_version,
        "counts": {
            "missing_nico_descendant": len(missing),
            "known_upstream_lag": len(known),
            "unclassified_missing": len(unclassified),
        },
        "known_upstream_lag": {
            "evidence_url": TOTOABA_EVIDENCE_URL,
            "published_at": TOTOABA_PUBLISHED_AT,
            "codes": known,
        },
        "unclassified_missing": unclassified,
        "note": NOTE,
    }
