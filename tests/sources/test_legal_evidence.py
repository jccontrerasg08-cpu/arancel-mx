from datetime import date

import pytest

from arancel_mx.sources.diputados import LedgerDocument, LedgerLink, LedgerSnapshot
from arancel_mx.sources.legal_evidence import required_dof_evidence


LAW_DATE = date(2025, 12, 29)
TARIFF_DATE = date(2026, 4, 23)
LAW_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/reforma02.pdf"
TARIFF_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/tarifa15.pdf"


def document(category, displayed_date, *links):
    return LedgerDocument(
        category=category,
        ordinal="1",
        title=f"{category} fixture",
        displayed_date=displayed_date,
        links=tuple(links),
    )


def dof_link(url, displayed_date, media_type="application/pdf"):
    return LedgerLink(
        role="dof",
        url=url,
        label=f"DOF {displayed_date.isoformat()}",
        displayed_date=displayed_date,
        media_type=media_type,
    )


def snapshot(*documents):
    return LedgerSnapshot(
        base_url="https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm",
        last_law_reform=LAW_DATE,
        latest_tariff_modification=TARIFF_DATE,
        documents=tuple(documents),
        page_sha256="a" * 64,
    )


def test_missing_latest_law_reform_dof_link_is_rejected():
    ledger = snapshot(
        document(
            "law_reform",
            LAW_DATE,
            LedgerLink("word", LAW_URL.replace(".pdf", ".doc"), "Word"),
        ),
        document("tariff_decree", TARIFF_DATE, dof_link(TARIFF_URL, TARIFF_DATE)),
    )

    with pytest.raises(ValueError, match="missing DOF evidence: law_reform"):
        required_dof_evidence(ledger)


def test_missing_latest_tariff_decree_dof_link_is_rejected():
    ledger = snapshot(
        document("law_reform", LAW_DATE, dof_link(LAW_URL, LAW_DATE)),
        document(
            "tariff_decree",
            TARIFF_DATE,
            LedgerLink("word", TARIFF_URL.replace(".pdf", ".doc"), "Word"),
        ),
    )

    with pytest.raises(ValueError, match="missing DOF evidence: tariff_decree"):
        required_dof_evidence(ledger)


def test_required_dof_evidence_extracts_exact_required_roles_and_deduplicates_urls():
    law = dof_link(LAW_URL, LAW_DATE)
    tariff = dof_link(TARIFF_URL, TARIFF_DATE)
    ledger = snapshot(
        document("law_reform", LAW_DATE, law, law),
        document("tariff_decree", TARIFF_DATE, tariff, tariff),
        document(
            "law_reform",
            date(2024, 1, 1),
            dof_link("https://www.diputados.gob.mx/old.pdf", date(2024, 1, 1)),
        ),
    )

    evidence = required_dof_evidence(ledger)

    assert [(item.role, item.published_at, item.url, item.media_type) for item in evidence] == [
        ("law_reform", LAW_DATE, LAW_URL, "application/pdf"),
        ("tariff_decree", TARIFF_DATE, TARIFF_URL, "application/pdf"),
    ]


def test_multiple_different_dof_urls_for_same_required_role_are_ambiguous():
    ledger = snapshot(
        document(
            "law_reform",
            LAW_DATE,
            dof_link(LAW_URL, LAW_DATE),
            dof_link("https://www.diputados.gob.mx/other.pdf", LAW_DATE),
        ),
        document("tariff_decree", TARIFF_DATE, dof_link(TARIFF_URL, TARIFF_DATE)),
    )

    with pytest.raises(ValueError, match="ambiguous DOF evidence: law_reform"):
        required_dof_evidence(ledger)
