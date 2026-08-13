"""Discovery of official SNICE tariff documents."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from urllib.parse import urlparse

from arancel_mx.domain.normalization import fold_text
from arancel_mx.sources.html_pages import extract_links


@dataclass(frozen=True)
class DownloadTask:
    identifier: str
    url: str
    relative_path: str
    media_type: str
    kind: str
    provenance: dict[str, str]


def _official_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return (
        host == "snice.gob.mx"
        or host.endswith(".snice.gob.mx")
        or host == "dof.gob.mx"
        or host.endswith(".dof.gob.mx")
    )


def _document_links(html: str, base_url: str, context: str) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    for url, title in extract_links(html, base_url):
        if title == "iframe":
            continue
        if not _official_host(url):
            continue
        searchable = fold_text(f"{title} {url}").upper()
        suffix = Path(urlparse(url).path).suffix.lower()
        if suffix in {".xls", ".xlsx"} and "NICO" in searchable:
            kind = "nico"
        elif context == "ligie" and (
            suffix in {".xls", ".xlsx"}
            and re.search(r"LIGIE|TIGIE|FRACCIONESARANCELARIAS", searchable)
            and not re.search(
                r"ARANCEL.CUPO|NIVELESARANCELARIOS|TABLASDECORRELACION|DECRETO|IMMEX|PROSEC|FRONTERA|CHETUMAL|VEHICULOSUSADOS",
                searchable,
            )
        ):
            kind = "ligie"
        elif context == "modification" and (
            suffix in {".xls", ".xlsx", ".pdf"} or "DOF.GOB.MX" in searchable
        ):
            kind = "modification"
        else:
            continue
        documents.append(
            {"kind": kind, "title": title or Path(url).name, "source_url": url}
        )
    return documents


def _year_pages(html: str, base_url: str, context: str) -> list[str]:
    if context == "nico":
        pattern = re.compile(r"ligie\.nico\d+\.mod(\d{2})\.html$", re.I)
        minimum_year = 22
    elif context == "modification":
        pattern = re.compile(r"ligie\.info\d+\.mod(\d{2})\.html$", re.I)
        minimum_year = 23
    else:
        return []
    pages: set[str] = set()
    for url, title in extract_links(html, base_url):
        if title == "iframe":
            continue
        match = pattern.search(urlparse(url).path)
        if _official_host(url) and match and int(match.group(1)) >= minimum_year:
            pages.add(url)
    return sorted(pages)


def _discover(
    client,
    ligie_index_url: str,
    nico_index_url: str,
    modifications_index_url: str,
    timeout_s: float,
) -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    seen: set[str] = set()
    for kind, index_url in (
        ("ligie", ligie_index_url),
        ("nico", nico_index_url),
        ("modification", modifications_index_url),
    ):
        response = client.get(index_url, timeout=timeout_s)
        response.raise_for_status()
        page_documents = _document_links(response.text, response.url, kind)
        for year_url in _year_pages(response.text, response.url, kind):
            year_response = client.get(year_url, timeout=timeout_s)
            year_response.raise_for_status()
            page_documents.extend(
                _document_links(year_response.text, year_response.url, kind)
            )
        for document in page_documents:
            if document["source_url"] in seen:
                continue
            seen.add(document["source_url"])
            documents.append(document)
    missing = {"ligie", "nico", "modification"} - {
        document["kind"] for document in documents
    }
    if missing:
        raise ValueError(
            "Official discovery did not find: " + ", ".join(sorted(missing))
        )
    return documents


def _extension(url: str) -> tuple[str, str]:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix == ".xlsx":
        return ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if suffix == ".xls":
        return ".xls", "application/vnd.ms-excel"
    if suffix == ".pdf":
        return ".pdf", "application/pdf"
    return ".html", "text/html"


def discover_snice_documents(
    client,
    ligie_index_url: str,
    nico_index_url: str,
    modifications_index_url: str,
    timeout_s: float = 30.0,
) -> list[DownloadTask]:
    documents = _discover(
        client,
        ligie_index_url,
        nico_index_url,
        modifications_index_url,
        timeout_s,
    )
    counters: dict[str, int] = {}
    tasks: list[DownloadTask] = []
    for document in documents:
        kind = document["kind"]
        counters[kind] = counters.get(kind, 0) + 1
        extension, media_type = _extension(document["source_url"])
        identifier = hashlib.sha256(document["source_url"].encode("utf-8")).hexdigest()
        tasks.append(
            DownloadTask(
                identifier=identifier,
                url=document["source_url"],
                relative_path=f"{kind}-{counters[kind]:03d}{extension}",
                media_type=media_type,
                kind=kind,
                provenance={
                    "source_url": document["source_url"],
                    "title": document["title"],
                },
            )
        )
    return tasks
