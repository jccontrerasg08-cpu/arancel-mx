from __future__ import annotations

import pytest

from arancel_mx.pipeline.nico_coverage import nico_coverage_report


IDENTITIES = (
    {
        "dataset_key": "ligie",
        "document_role": "ligie_snapshot",
        "source_url": "https://example.test/ligie.xlsx",
        "sha256": "a" * 64,
    },
    {
        "dataset_key": "nico",
        "document_role": "nico_snapshot",
        "source_url": "https://example.test/nico.xlsx",
        "sha256": "b" * 64,
    },
)


def test_nico_coverage_separates_confirmed_totoaba_lag_from_unclassified_gaps():
    report = nico_coverage_report(
        (
            {"level": "fraccion8", "code": "03028902"},
            {"level": "fraccion8", "code": "03029904"},
            {"level": "fraccion8", "code": "01012101"},
            {"level": "fraccion8", "code": "99999999"},
            {"level": "nico10", "code": "0101210100"},
        ),
        IDENTITIES,
    )

    assert report["counts"] == {
        "fraccion8": 4,
        "with_nico_descendant": 1,
        "missing_nico_descendant": 3,
        "known_upstream_lag": 2,
        "unclassified_missing": 1,
    }
    assert report["known_upstream_lag"] == {
        "evidence_url": "https://www.dof.gob.mx/nota_detalle.php?codigo=5763398&fecha=21/07/2025",
        "published_at": "2025-07-21",
        "codes": ("03028902", "03029904"),
    }
    assert report["unclassified_missing"] == ("99999999",)
    assert report["source_identity"] == IDENTITIES


def test_nico_coverage_requires_both_structured_source_identities():
    with pytest.raises(ValueError, match="LIGIE and one NICO"):
        nico_coverage_report(({"level": "fraccion8", "code": "01012101"},), ())
