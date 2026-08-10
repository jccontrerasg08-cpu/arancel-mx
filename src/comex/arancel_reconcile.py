from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from typing import Any, Mapping, Sequence
from urllib.parse import urljoin

from .arancel_registry import RegistryEntry, classify_candidate


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


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.href: str | None = None
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.href is not None:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join("".join(self.parts).split())))
            self.href = None


def discover_registered_sources(
    registry: Mapping[str, RegistryEntry], client: Any
) -> tuple[DiscoveredDocument, ...]:
    found: list[DiscoveredDocument] = []
    for key, entry in sorted(registry.items()):
        response = client.get(entry.canonical_page)
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        parser = _LinkParser()
        parser.feed(response.text)
        for href, title in parser.links:
            source_url = urljoin(entry.canonical_page, href)
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
