from arancel_mx.domain.nico_lag import (
    KNOWN_UPSTREAM_LAG_CODES,
    classify_missing_nico,
)
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


def test_classify_missing_nico_splits_known_lag_and_keeps_order():
    report = classify_missing_nico(
        ["99999999", "03029904", "03028902", "03028902"],
        dataset_version="2026.11.09",
    )
    assert report["dataset_version"] == "2026.11.09"
    assert report["counts"] == {
        "missing_nico_descendant": 3,
        "known_upstream_lag": 2,
        "unclassified_missing": 1,
    }
    assert report["known_upstream_lag"]["codes"] == ("03028902", "03029904")
    assert report["unclassified_missing"] == ("99999999",)


def test_pipeline_report_uses_the_same_known_lag_set():
    report = nico_coverage_report(
        (
            {"level": "fraccion8", "code": "03028902"},
            {"level": "fraccion8", "code": "01012101"},
            {"level": "nico10", "code": "0101210100"},
        ),
        IDENTITIES,
    )
    assert report["known_upstream_lag"]["codes"] == ("03028902",)
    assert set(report["known_upstream_lag"]["codes"]).issubset(KNOWN_UPSTREAM_LAG_CODES)
    assert report["policy_version"] == classify_missing_nico(())["policy"]
