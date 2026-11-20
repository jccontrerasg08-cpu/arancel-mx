from arancel_mx.domain.rate_diagnostics import summarize_rate_validity


def test_rate_validity_summary_counts_dated_and_basis_without_inventing_dates():
    report = summarize_rate_validity(
        (
            {"code": "01012101", "rate_effective_from": "2026-01-01", "validity_basis": "instrument"},
            {"code": "01012101", "rate_effective_from": "2026-01-01", "validity_basis": "instrument"},
            {"code": "03028902", "rate_effective_from": None, "validity_basis": None},
        ),
        dataset_version="2026.11.09",
    )
    assert report["counts"] == {"fraccion8": 2, "dated": 1, "undated": 1}
    assert report["validity_basis"] == {"instrument": 1, "unknown": 1}
    assert "does not invent dates" in str(report["note"])
