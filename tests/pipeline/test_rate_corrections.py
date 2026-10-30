from datetime import date
from decimal import Decimal
import json

import pytest

from arancel_mx.pipeline.rate_corrections import (
    apply_rate_corrections,
    date_corrected_rates,
    load_rate_corrections,
)
from arancel_mx.pipeline.rate_validity import load_registry, rate_validity

MAIZE = {
    "code": "10059004",
    "duty": "ige",
    "snapshot": "50",
    "corrected": "Ex.",
    "rate_effective_from": "2024-01-01",
    "evidence": "DOF",
    "sources": [{"title": "DOF", "source_url": "https://www.diputados.gob.mx/x.pdf", "sha256": "a" * 64}],
}


def _registry(*corrections):
    return json.dumps({"kind": "test", "version": "test", "corrections": list(corrections)}).encode()


def _row(ige_text="50"):
    return {
        "code": "10059004",
        "igi_text": "20",
        "igi_kind": "ad_valorem",
        "igi_value": Decimal("20"),
        "ige_text": ige_text,
        "ige_kind": "ad_valorem",
        "ige_value": Decimal("50"),
        "rate_effective_from": None,
    }


def test_corrects_every_field_of_the_matching_duty_and_reports_it() -> None:
    rows = [_row(), {**_row(), "code": "10059099"}]

    report = apply_rate_corrections(rows, _registry(MAIZE))

    assert (rows[0]["ige_text"], rows[0]["ige_kind"], rows[0]["ige_value"]) == (
        "Ex.",
        "exento",
        Decimal("0"),
    )
    assert rows[0]["igi_text"] == "20"
    assert rows[1]["ige_text"] == "50"
    assert [item["code"] for item in report["applied"]] == ["10059004"]
    assert report["stale"] == []


def test_new_official_rate_wins_and_the_correction_is_reported_stale() -> None:
    rows = [_row("30")]

    report = apply_rate_corrections(rows, _registry(MAIZE))

    assert rows[0]["ige_text"] == "30"
    assert report["applied"] == []
    assert report["stale"] == ["10059004:ige"]


def test_snapshot_literals_compare_by_meaning() -> None:
    rows = [_row("50 %")]

    apply_rate_corrections(rows, _registry(MAIZE))

    assert rows[0]["ige_text"] == "Ex."


def test_documented_start_only_fills_an_undated_corrected_row() -> None:
    rows = [_row(), {**_row(), "rate_effective_from": date(2022, 12, 12)}]
    report = apply_rate_corrections(rows, _registry(MAIZE))

    assert date_corrected_rates(rows, report) == 1
    assert rows[0]["rate_effective_from"] == date(2024, 1, 1)
    assert rows[1]["rate_effective_from"] == date(2022, 12, 12)


@pytest.mark.parametrize(
    "corrections",
    [
        (MAIZE, MAIZE),
        ({**MAIZE, "corrected": "50 %"},),
        ({**MAIZE, "corrected": "50"},),
        ({**MAIZE, "duty": "iva"},),
        ({**MAIZE, "sources": []},),
        ({**MAIZE, "rate_effective_from": "2024-13-01"},),
    ],
)
def test_registry_rejects_invalid_corrections(corrections) -> None:
    with pytest.raises(ValueError):
        load_rate_corrections(_registry(*corrections))


def test_packaged_corrections_restore_the_rate_the_legal_instruments_set() -> None:
    _, corrections = load_rate_corrections()
    legal = load_registry()

    assert [(item["code"], item["duty"]) for item in corrections] == [("10059004", "ige")]
    for item in corrections:
        # After the correction, the snapshot agrees with the governing legal text.
        rows = [_row(item["snapshot"])]
        apply_rate_corrections(rows)
        result = rate_validity(
            legal, item["code"], rows[0]["igi_text"], rows[0]["ige_text"], date(2026, 10, 30)
        )
        assert result != "snapshot_disagrees"
        for source in item["sources"]:
            assert source["source_url"].startswith("https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022/")
            assert len(source["sha256"]) == 64
