from pathlib import Path

import pytest

from arancel_mx.pipeline.reconcile import (
    DiscoveredDocument,
    reconcile_legal_instruments,
    select_current_document,
)
from arancel_mx.sources.diputados import parse_ligie_ledger


FIXTURE = Path(__file__).parents[1] / "fixtures" / "diputados" / "ligie_2022.html"


def ledger():
    return parse_ligie_ledger(
        FIXTURE.read_text(encoding="utf-8"),
        "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm",
    )


SNICE = (
    {"document_id": "nico-current", "role": "nico_agreement"},
    {"document_id": "proposal-1", "role": "nico_proposal"},
    {"document_id": "indicator-1", "role": "weighted_tariff_indicator"},
)


def discovered(url, title):
    return DiscoveredDocument(
        dataset_key="ligie",
        document_role="ligie_snapshot",
        discovery_url="https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html",
        source_url=url,
        title=title,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def test_missing_dof_evidence_blocks_publication():
    report = reconcile_legal_instruments(ledger(), (), SNICE)

    assert not report.publishable
    assert "missing_dof_evidence" in report.error_codes


def test_proposals_and_indicators_do_not_enter_legal_ids():
    dof = (
        {"document_id": "dof-law", "role": "law_reform", "published_at": "2025-12-29"},
        {"document_id": "dof-tariff", "role": "tariff_decree", "published_at": "2026-04-23"},
    )

    report = reconcile_legal_instruments(ledger(), dof, SNICE)

    assert report.publishable
    assert not set(report.legal_document_ids) & set(report.proposal_document_ids)
    assert not set(report.legal_document_ids) & set(report.indicator_document_ids)


def test_snapshot_selection_uses_unique_latest_valid_date():
    older = discovered(
        "https://www.snice.gob.mx/FRACCIONESARANCELARIAS_20260101.XLSX",
        "Fracciones 20260101",
    )
    latest = discovered(
        "https://www.snice.gob.mx/FRACCIONESARANCELARIAS_20260810.XLSX",
        "Fracciones vigentes",
    )

    selected = select_current_document(
        (older, latest), "ligie", "ligie_snapshot"
    )

    assert selected == latest


def test_snapshot_selection_collapses_duplicate_occurrences_of_same_url():
    url = "https://www.snice.gob.mx/FRACCIONESARANCELARIAS-LIGIE_20260420-20260420.xlsx"
    first = discovered(url, "Fracciones arancelarias")
    repeated = discovered(url, "Descarga las fracciones arancelarias")

    selected = select_current_document(
        (first, repeated), "ligie", "ligie_snapshot"
    )

    assert selected.source_url == url


def test_snapshot_selection_rejects_latest_date_tie():
    first = discovered(
        "https://www.snice.gob.mx/FRACCIONESARANCELARIAS_A_20260810.XLSX",
        "Fracciones A",
    )
    second = discovered(
        "https://www.snice.gob.mx/FRACCIONESARANCELARIAS_B_20260810.XLSX",
        "Fracciones B",
    )

    with pytest.raises(ValueError, match="ambiguous official snapshot"):
        select_current_document((first, second), "ligie", "ligie_snapshot")


def test_snapshot_selection_rejects_multiple_undated_candidates():
    first = discovered(
        "https://www.snice.gob.mx/FRACCIONESARANCELARIAS_A.XLSX", "Fracciones A"
    )
    second = discovered(
        "https://www.snice.gob.mx/FRACCIONESARANCELARIAS_B.XLSX", "Fracciones B"
    )

    with pytest.raises(ValueError, match="ambiguous official snapshot"):
        select_current_document((first, second), "ligie", "ligie_snapshot")


def test_snapshot_selection_rejects_missing_candidate():
    with pytest.raises(ValueError, match="missing official snapshot"):
        select_current_document((), "ligie", "ligie_snapshot")
