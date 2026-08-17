from pathlib import Path

import pytest

from arancel_mx.pipeline.reconcile import (
    DiscoveredDocument,
    discover_registered_sources,
    reconcile_legal_instruments,
    select_current_document,
)
from arancel_mx.sources.diputados import parse_ligie_ledger
from arancel_mx.sources.registry import load_source_registry


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


class DiscoveryResponse:
    def __init__(self, text=""):
        self.text = text

    def raise_for_status(self):
        return None


class DiscoveryClient:
    def __init__(self, pages=None):
        self.pages = pages or {}
        self.calls = []

    def get(self, url, timeout=None):
        self.calls.append((url, timeout))
        return DiscoveryResponse(self.pages.get(url, ""))


def test_registered_discovery_uses_configured_timeout():
    entry = load_source_registry()["ligie"]
    client = DiscoveryClient()

    discover_registered_sources({"ligie": entry}, client, timeout_s=17.5)

    assert client.calls == [
        (entry.canonical_page, 17.5),
        (entry.corpus_index_pages[0], 17.5),
    ]


def test_shared_corpus_index_is_fetched_once():
    registry = load_source_registry()
    client = DiscoveryClient()

    discover_registered_sources(
        {"ligie": registry["ligie"], "nico": registry["nico"]}, client
    )

    assert client.calls.count((registry["ligie"].corpus_index_pages[0], 30.0)) == 1


def test_corpus_discovery_promotes_unique_newer_dated_candidate():
    entry = load_source_registry()["ligie"]
    canonical = "https://www.snice.gob.mx/~oracle/SNICE_DOCS/FRACCIONESARANCELARIAS_20260420.XLSX"
    promoted = "https://www.snice.gob.mx/~oracle/SNICE_DOCS/FRACCIONESARANCELARIAS_20260820.XLSX"
    undated = "https://www.snice.gob.mx/~oracle/SNICE_DOCS/FRACCIONESARANCELARIAS_VIGENTE.XLSX"
    client = DiscoveryClient(
        {
            entry.canonical_page: f'<a href="{canonical}">Current LIGIE</a>',
            entry.corpus_index_pages[0]: (
                f'<a href="{promoted}">Newer LIGIE</a>'
                f'<a href="{undated}">Undated candidate</a>'
            ),
        }
    )

    selected = select_current_document(
        discover_registered_sources({"ligie": entry}, client),
        "ligie",
        "ligie_snapshot",
    )

    assert selected.source_url == promoted
    assert selected.discovery_url == entry.corpus_index_pages[0]
    assert selected.discovery_kind == "corpus_index"


def test_registered_discovery_rejects_non_positive_timeout_before_network_access():
    entry = load_source_registry()["ligie"]
    client = DiscoveryClient()

    with pytest.raises(ValueError, match="timeout_s must be positive"):
        discover_registered_sources({"ligie": entry}, client, timeout_s=0)

    assert client.calls == []


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


def test_snapshot_selection_rejects_dated_candidate_when_competing_url_is_undated():
    dated = discovered(
        "https://www.snice.gob.mx/FRACCIONESARANCELARIAS_20260810.XLSX",
        "Fracciones 20260810",
    )
    undated = discovered(
        "https://www.snice.gob.mx/FRACCIONESARANCELARIAS_VIGENTE.XLSX",
        "Fracciones vigentes",
    )

    with pytest.raises(ValueError, match="ambiguous official snapshot"):
        select_current_document((dated, undated), "ligie", "ligie_snapshot")


def test_snapshot_selection_rejects_missing_candidate():
    with pytest.raises(ValueError, match="missing official snapshot"):
        select_current_document((), "ligie", "ligie_snapshot")
