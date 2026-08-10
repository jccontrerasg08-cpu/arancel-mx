"""Temporary live diagnostic for the Cámara de Diputados LIGIE ledger.

This file is intentionally diagnostic and must be replaced by a frozen regression
fixture before merge.
"""

import requests

from arancel_mx.sources.diputados import parse_ligie_ledger
from arancel_mx.sources.legal_evidence import required_dof_evidence


URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"


def test_live_ledger_exposes_current_required_dof_evidence():
    response = requests.get(URL, timeout=30)
    response.raise_for_status()
    snapshot = parse_ligie_ledger(response.text, URL)

    diagnostic = [
        {
            "category": document.category,
            "ordinal": document.ordinal,
            "displayed_date": document.displayed_date.isoformat() if document.displayed_date else None,
            "links": [
                {
                    "role": link.role,
                    "label": link.label,
                    "displayed_date": link.displayed_date.isoformat() if link.displayed_date else None,
                    "url": link.url,
                }
                for link in document.links
            ],
        }
        for document in snapshot.documents
    ]

    try:
        evidence = required_dof_evidence(snapshot)
    except ValueError as exc:
        raise AssertionError(
            f"{exc}; last_law_reform={snapshot.last_law_reform}; "
            f"latest_tariff_modification={snapshot.latest_tariff_modification}; "
            f"documents={diagnostic!r}"
        ) from exc

    assert {item.role for item in evidence} == {"law_reform", "tariff_decree"}
