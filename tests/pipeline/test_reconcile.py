from pathlib import Path

from arancel_mx.pipeline.reconcile import reconcile_legal_instruments
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
