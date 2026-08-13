from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from arancel_mx.sources.html_pages import extract_links
from arancel_mx.sources.registry import RegistryEntry, classify_candidate


@dataclass(frozen=True)
class ReconciliationReport:
    publishable: bool
    error_codes: tuple[str, ...]
    discrepancies: tuple[str, ...]
    legal_document_ids: tuple[str, ...]
    proposal_document_ids: tuple[str, ...]
    indicator_document_ids: tuple[str, ...]


@dataclass(frozen=True)
class DiscoveredDocument:
    dataset_key: str
    document_role: str
    discovery_url: str
    source_url: str
    title: str
    media_type: str


def _value(item: Any, key: str, default: Any = None) -> Any:
    return item.get(key, default) if isinstance(item, Mapping) else getattr(item, key, default)


def _document_id(item: Any) -> str:
    return str(_value(item, "document_id", _value(item, "source_document_id", _value(item, "url", ""))))


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _snapshot_dates(document: DiscoveredDocument) -> tuple[date, ...]:
    basename = PurePosixPath(urlparse(document.source_url).path).name
    tokens = re.findall(r"(?<!\d)(\d{8})(?!\d)", f"{document.title} {basename}")
    parsed: set[date] = set()
    for token in tokens:
        try:
            parsed.add(date(int(token[:4]), int(token[4:6]), int(token[6:8])))
        except ValueError:
            continue
    return tuple(sorted(parsed))


def select_current_document(
    documents: Sequence[DiscoveredDocument],
    dataset_key: str,
    document_role: str,
) -> DiscoveredDocument:
    """Select one current registered snapshot, failing on ambiguity."""
    matching = [
        document
        for document in documents
        if document.dataset_key == dataset_key and document.document_role == document_role
    ]
    by_url: dict[str, list[DiscoveredDocument]] = {}
    for document in matching:
        by_url.setdefault(document.source_url, []).append(document)
    candidates = [
        min(
            occurrences,
            key=lambda item: (item.title, item.discovery_url, item.media_type),
        )
        for _, occurrences in sorted(by_url.items())
    ]
    if not candidates:
        raise ValueError(f"missing official snapshot: {dataset_key}:{document_role}")
    if len(candidates) == 1:
        return candidates[0]

    dated: list[tuple[date, DiscoveredDocument]] = []
    for document in candidates:
        dates = _snapshot_dates(document)
        if dates:
            dated.append((max(dates), document))
    if len(dated) != len(candidates):
        raise ValueError(f"ambiguous official snapshot: {dataset_key}:{document_role}")

    latest_date = max(item[0] for item in dated)
    winners = [document for candidate_date, document in dated if candidate_date == latest_date]
    if len(winners) != 1:
        raise ValueError(f"ambiguous official snapshot: {dataset_key}:{document_role}")
    return winners[0]


def reconcile_legal_instruments(
    ledger: Any,
    dof_documents: Sequence[Any],
    snice_documents: Sequence[Any],
) -> ReconciliationReport:
    discrepancies: list[str] = []
    required = {
        "law_reform": _value(ledger, "last_law_reform"),
        "tariff_decree": _value(ledger, "latest_tariff_modification"),
    }
    dof_evidence = {
        (str(_value(document, "role", "")), _as_date(_value(document, "published_at")))
        for document in dof_documents
    }
    for role, displayed_date in required.items():
        if (role, displayed_date) not in dof_evidence:
            discrepancies.append(f"missing_dof_evidence:{role}:{displayed_date}")

    proposal_roles = {"nico_proposal", "nico_proposals"}
    indicator_roles = {"weighted_tariff_indicator", "indicator", "analytics"}
    proposal_ids = tuple(sorted(filter(None, (_document_id(item) for item in snice_documents if _value(item, "role") in proposal_roles))))
    indicator_ids = tuple(sorted(filter(None, (_document_id(item) for item in snice_documents if _value(item, "role") in indicator_roles))))
    excluded = proposal_roles | indicator_roles
    legal_ids = {
        _document_id(item) for item in (*dof_documents, *snice_documents)
        if _value(item, "role") not in excluded and _document_id(item)
    }
    for document in _value(ledger, "documents", ()):
        for link in _value(document, "links", ()):
            if _value(link, "url"):
                legal_ids.add(str(_value(link, "url")))
    codes = tuple(sorted({item.split(":", 1)[0] for item in discrepancies}))
    return ReconciliationReport(
        publishable=not discrepancies,
        error_codes=codes,
        discrepancies=tuple(discrepancies),
        legal_document_ids=tuple(sorted(legal_ids)),
        proposal_document_ids=proposal_ids,
        indicator_document_ids=indicator_ids,
    )


def discover_registered_sources(
    registry: Mapping[str, RegistryEntry],
    client: Any,
    timeout_s: float = 30.0,
) -> tuple[DiscoveredDocument, ...]:
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")

    found: list[DiscoveredDocument] = []
    for key, entry in sorted(registry.items()):
        response = client.get(entry.canonical_page, timeout=timeout_s)
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        for url, title in extract_links(response.text, entry.canonical_page):
            if title == "iframe":
                continue
            source_url = url
            suffix = source_url.rsplit("?", 1)[0].rsplit(".", 1)[-1].lower()
            media_type = {
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "xls": "application/vnd.ms-excel",
                "pdf": "application/pdf",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "doc": "application/msword",
            }.get(suffix, "application/octet-stream")
            role = classify_candidate(entry, entry.canonical_page, source_url, media_type)
            if role:
                found.append(DiscoveredDocument(key, role, entry.canonical_page, source_url, title, media_type))
    return tuple(sorted(found, key=lambda item: (item.dataset_key, item.document_role, item.source_url)))
