from datetime import date
import json

import pytest

from arancel_mx.pipeline.rate_validity import (
    RateValidity,
    assign_rate_validity,
    load_registry,
    rate_validity,
)

AS_OF = date(2026, 10, 29)
SHA = "0" * 64


def _instrument(identifier, kind, entry, end, rows, dof="2022-06-07"):
    return {
        "id": identifier,
        "kind": kind,
        "title": identifier,
        "dof_date": dof,
        "entry_into_force": entry,
        "validity_end": end,
        "source_url": f"https://www.diputados.gob.mx/{identifier}.pdf",
        "sha256": SHA,
        "rows": rows,
    }


@pytest.fixture
def registry():
    payload = {
        "kind": "arancel-mx/ligie-rate-instruments",
        "version": "test",
        "instruments": [
            _instrument(
                "orig",
                "base",
                "2022-12-12",
                None,
                [
                    ["01010101", "10", "Ex."],  # never modified
                    ["02020202", "15", "Ex."],  # temporary rise that ended
                    ["03030303", "15", "Ex."],  # temporary rise renewed for good
                    ["04040404", "20", "Ex."],  # modified for good
                    ["05050505", "20", "Ex."],  # snapshot disagrees
                    ["06060606", "5", "Ex."],  # mentioned by an unmodeled decree
                    ["07070707", "5", "Ex."],  # unmodeled decree, then modified
                ],
            ),
            _instrument(
                "temp",
                "temporary_rate",
                "2024-04-23",
                "2026-04-23",
                [["02020202", "35", "Ex."], ["03030303", "35", "Ex."]],
            ),
            _instrument(
                "reform",
                "modify_rate",
                "2026-01-01",
                None,
                [
                    ["03030303", "35", "Ex."],
                    ["04040404", "25", "Ex."],
                    ["07070707", "10", "Ex."],
                ],
            ),
            _instrument(
                "exempt",
                "temporary_rate",
                "2026-10-14",
                "2031-10-14",
                [["08080808", "Ex.", "Ex."]],
            ),
        ],
        "unmodeled": [
            {
                "id": "staged",
                "reason": "staged rates",
                "codes": ["06060606", "07070707"],
            },
        ],
    }
    return load_registry(json.dumps(payload).encode())


def test_untouched_rate_applies_since_the_base_law(registry) -> None:
    assert rate_validity(registry, "01010101", "10", "Ex.", AS_OF) == RateValidity(
        date(2022, 12, 12), None, "orig"
    )


def test_base_rate_restarts_the_day_after_a_temporary_rate_ends(registry) -> None:
    assert rate_validity(registry, "02020202", "15", "Ex.", AS_OF) == RateValidity(
        date(2026, 4, 24), None, "orig"
    )


def test_rate_renewed_by_a_later_instrument_keeps_its_first_start(registry) -> None:
    assert rate_validity(registry, "03030303", "35", "Ex.", AS_OF) == RateValidity(
        date(2024, 4, 23), None, "reform"
    )


def test_modified_rate_applies_since_the_modifying_instrument(registry) -> None:
    assert rate_validity(registry, "04040404", "25", "Ex.", AS_OF) == RateValidity(
        date(2026, 1, 1), None, "reform"
    )


def test_temporary_rate_carries_its_last_day(registry) -> None:
    result = rate_validity(registry, "08080808", "Ex.", "Ex.", AS_OF)

    assert result == RateValidity(date(2026, 10, 14), date(2031, 10, 14), "exempt")


def test_duty_literals_compare_by_meaning(registry) -> None:
    assert isinstance(
        rate_validity(registry, "01010101", "10 %", "Ex", AS_OF), RateValidity
    )


def test_unknown_when_snapshot_disagrees_or_an_unmodeled_decree_may_govern(
    registry,
) -> None:
    assert (
        rate_validity(registry, "05050505", "20", "50", AS_OF) == "snapshot_disagrees"
    )
    assert (
        rate_validity(registry, "06060606", "5", "Ex.", AS_OF) == "unmodeled_instrument"
    )
    assert (
        rate_validity(registry, "09090909", "5", "Ex.", AS_OF) == "not_in_instruments"
    )


def test_unmodeled_history_limits_the_start_to_the_governing_instrument(
    registry,
) -> None:
    assert rate_validity(registry, "07070707", "10", "Ex.", AS_OF) == RateValidity(
        date(2026, 1, 1), None, "reform"
    )


def test_assign_fills_rate_rows_and_reports_discrepancies(registry) -> None:
    rates = [
        {"code": "04040404", "igi_text": "25", "ige_text": "Ex."},
        {"code": "05050505", "igi_text": "20", "ige_text": "50"},
        {"code": "06060606", "igi_text": "5", "ige_text": "Ex."},
    ]

    report = assign_rate_validity(rates, AS_OF, registry)

    assert rates[0]["rate_effective_from"] == date(2026, 1, 1)
    assert rates[0]["rate_effective_to"] is None
    assert "rate_effective_from" not in rates[1]
    assert report["dated"] == {"reform": 1}
    assert report["undated"] == {"snapshot_disagrees": 1, "unmodeled_instrument": 1}
    assert report["discrepancies"] == [
        {
            "code": "05050505",
            "snapshot": {"igi": "20", "ige": "50"},
            "instrument": "orig",
            "instrument_duties": {"igi": "20", "ige": "Ex."},
        }
    ]
    assert report["registry_sha256"] == registry.sha256


def test_packaged_registry_matches_each_instruments_declared_row_count() -> None:
    registry = load_registry()
    counts = {item.id: 0 for item in registry.instruments}
    for entries in registry.rows.values():
        for instrument, _, _ in entries:
            counts[instrument.id] += 1

    # Counts each decree declares about itself (see the instrument inventory).
    assert counts == {
        "orig": 8177,
        "tarifa07": 392,
        "tarifa09": 544,
        "tarifa10": 1,
        "tarifa11": 155,
        "tarifa13": 8,
        "ref02": 1463,
        "ref01": 11,
        "tarifa15": 185,
        "tarifa16": 1,
    }
    for item in registry.instruments:
        assert len(item.sha256) == 64
        assert item.source_url.startswith(
            "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022/"
        )
        assert item.validity_end is None or item.validity_end >= item.entry_into_force
    assert rate_validity(registry, "98030001", "Ex.", "Ex.", AS_OF) == RateValidity(
        date(2026, 10, 14), date(2031, 10, 14), "tarifa16"
    )
