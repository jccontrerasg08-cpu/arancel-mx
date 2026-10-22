"""Capture primary LIGIE instrument documents for research (read-only).

Local backfill tool; new instruments are detected through SIDOF (decision 0001).

Downloads the Cámara de Diputados LIGIE 2022 ledger, every document it links on
an allowed official host, and optional DOF daily indexes and SIDOF notes. It
writes the bytes plus a manifest with URL, SHA-256, media type and retrieval
time. It never builds, changes or publishes dataset artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

from arancel_mx.sources.diputados import parse_ligie_ledger
from arancel_mx.sources.http import (
    FetchedDocument,
    build_official_session,
    decode_fetched_text,
    fetch_official_document,
)

LEDGER_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"
ALLOWED_HOSTS = (
    "www.diputados.gob.mx",
    "diputados.gob.mx",
    "www.dof.gob.mx",
    "dof.gob.mx",
    "sidof.segob.gob.mx",
)
MEDIA_TYPES = (
    "text/html",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
DOF_EDITIONS = ("MAT", "VES")

Fetcher = Callable[[str], FetchedDocument]


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def page_links(html: str, base_url: str) -> list[tuple[str, str]]:
    parser = _LinkParser()
    parser.feed(html)
    return [(urljoin(base_url, href), label) for href, label in parser.links]


def _allowed(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme in {"http", "https"}
        and (parsed.hostname or "").lower() in ALLOWED_HOSTS
    )


def _https(url: str) -> str:
    return "https://" + url[len("http://") :] if url.startswith("http://") else url


def _safe_name(url: str, media_type: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    parsed = urlparse(url)
    stem = re.sub(
        r"[^A-Za-z0-9._-]+", "_", (parsed.path.rsplit("/", 1)[-1] or "index")
    )[:80]
    extension = (
        ".pdf"
        if media_type == "application/pdf"
        else ".html"
        if media_type == "text/html"
        else ""
    )
    if extension and not stem.lower().endswith(extension):
        stem += extension
    return f"{digest}_{stem}"


_DOF_TERMS = re.compile(
    r"impuestos generales de importaci|tarifa de la ley|nomenclatura|nico|"
    r"promoci[oó]n sectorial|prosec|immex|cupo|cuota compensatoria|"
    r"canasta b[aá]sica|regla octava",
    re.IGNORECASE,
)


class Capture:
    def __init__(self, out_dir: Path, fetch: Fetcher, max_documents: int) -> None:
        self.out_dir = out_dir
        self.fetch = fetch
        self.max_documents = max_documents
        self.records: dict[str, dict[str, object]] = {}

    def get(self, url: str, *, origin: str, label: str = "") -> FetchedDocument | None:
        url = _https(url)
        if url in self.records:
            return None
        if not _allowed(url):
            self.records[url] = {
                "url": url,
                "origin": origin,
                "label": label,
                "status": "skipped_host",
            }
            return None
        if (
            sum(1 for r in self.records.values() if r["status"] == "ok")
            >= self.max_documents
        ):
            self.records[url] = {
                "url": url,
                "origin": origin,
                "label": label,
                "status": "skipped_limit",
            }
            return None
        try:
            document = self.fetch(url)
        except (
            Exception
        ) as exc:  # recorded per document; one failure must not hide the rest
            self.records[url] = {
                "url": url,
                "origin": origin,
                "label": label,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}"[:500],
            }
            return None
        name = _safe_name(url, document.media_type)
        (self.out_dir / "documents" / name).write_bytes(document.content)
        self.records[url] = {
            "url": url,
            "final_url": document.final_url,
            "origin": origin,
            "label": label,
            "status": "ok",
            "media_type": document.media_type,
            "bytes": len(document.content),
            "sha256": hashlib.sha256(document.content).hexdigest(),
            "retrieved_at": document.retrieved_at.isoformat(),
            "path": f"documents/{name}",
        }
        return document

    def follow_dof_page(self, document: FetchedDocument, origin: str) -> None:
        """Keep PDFs and full-text views linked from a DOF note page."""
        if document.media_type != "text/html":
            return
        for url, label in page_links(decode_fetched_text(document), document.final_url):
            path = urlparse(url).path.lower()
            if (
                path.endswith(".pdf")
                or "nota_to_doc" in path
                or "nota_to_imagen" in path
            ):
                self.get(url, origin=origin, label=label)


def run(
    out_dir: Path,
    fetch: Fetcher,
    *,
    dof_dates: list[date],
    sidof_notes: list[str],
    max_documents: int,
) -> dict[str, object]:
    (out_dir / "documents").mkdir(parents=True, exist_ok=True)
    capture = Capture(out_dir, fetch, max_documents)
    ledger_summary: dict[str, object] = {}

    index = capture.get(LEDGER_URL, origin="diputados_index", label="LIGIE 2022 ledger")
    if index is None:
        ledger_summary["error"] = capture.records[LEDGER_URL].get(
            "error", "not fetched"
        )
    else:
        html = decode_fetched_text(index)
        try:
            ledger = parse_ligie_ledger(html, index.final_url)
            ledger_summary = {
                "last_law_reform": ledger.last_law_reform.isoformat(),
                "latest_tariff_modification": ledger.latest_tariff_modification.isoformat(),
                "documents": [
                    {
                        "category": item.category,
                        "ordinal": item.ordinal,
                        "title": item.title,
                        "displayed_date": item.displayed_date.isoformat()
                        if item.displayed_date
                        else None,
                        "links": [
                            {
                                "role": link.role,
                                "url": _https(link.url),
                                "label": link.label,
                            }
                            for link in item.links
                        ],
                    }
                    for item in ledger.documents
                ],
            }
        except ValueError as exc:
            ledger_summary["parse_error"] = str(exc)
        # Every link on the page, not only rows the parser recognizes.
        for url, label in page_links(html, index.final_url):
            if urlparse(url).path.lower().endswith(
                (".pdf", ".doc", ".docx", ".xls", ".xlsx")
            ) or ("dof.gob.mx" in (urlparse(url).hostname or "")):
                document = capture.get(url, origin="diputados_ledger_link", label=label)
                if document is not None and "dof.gob.mx" in (
                    urlparse(url).hostname or ""
                ):
                    capture.follow_dof_page(document, origin="dof_note_attachment")

    dof_matches: list[dict[str, str]] = []
    for day in dof_dates:
        for edition in DOF_EDITIONS:
            url = (
                f"https://www.dof.gob.mx/index.php?year={day.year}"
                f"&month={day.month:02d}&day={day.day:02d}&edicion={edition}"
            )
            document = capture.get(
                url, origin="dof_daily_index", label=f"{day} {edition}"
            )
            if document is None or document.media_type != "text/html":
                continue
            for link_url, label in page_links(
                decode_fetched_text(document), document.final_url
            ):
                if "nota_detalle" in link_url and _DOF_TERMS.search(label):
                    dof_matches.append(
                        {
                            "date": day.isoformat(),
                            "edition": edition,
                            "title": label,
                            "url": _https(link_url),
                        }
                    )
                    note = capture.get(link_url, origin="dof_daily_match", label=label)
                    if note is not None:
                        capture.follow_dof_page(note, origin="dof_note_attachment")

    for note_id in sidof_notes:
        for url in (
            f"https://sidof.segob.gob.mx/notas/{note_id}",
            f"https://sidof.segob.gob.mx/notas/imagenes/{note_id}",
        ):
            capture.get(url, origin="sidof_note", label=note_id)

    records = sorted(capture.records.values(), key=lambda r: str(r["url"]))
    manifest = {
        "kind": "arancel-mx/instrument-research-capture",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_url": LEDGER_URL,
        "ledger": ledger_summary,
        "dof_matches": dof_matches,
        "counts": {
            status: sum(1 for r in records if r["status"] == status)
            for status in sorted({str(r["status"]) for r in records})
        },
        "documents": records,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = ["# sha256  path"] + [
        f"{r['sha256']}  {r['path']}" for r in records if r["status"] == "ok"
    ]
    (out_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def _parse_dates(value: str) -> list[date]:
    return [
        date.fromisoformat(item.strip()) for item in value.split(",") if item.strip()
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--dof-dates",
        default="",
        help="Comma-separated ISO dates of DOF editions to scan",
    )
    parser.add_argument(
        "--sidof-notes", default="", help="Comma-separated SIDOF note ids"
    )
    parser.add_argument("--max-documents", type=int, default=400)
    args = parser.parse_args(argv)

    session = build_official_session()

    def fetch(url: str) -> FetchedDocument:
        return fetch_official_document(
            session, url, ALLOWED_HOSTS, MEDIA_TYPES, timeout_s=90.0
        )

    manifest = run(
        args.out,
        fetch,
        dof_dates=_parse_dates(args.dof_dates),
        sidof_notes=[n.strip() for n in args.sidof_notes.split(",") if n.strip()],
        max_documents=args.max_documents,
    )
    print(
        json.dumps(
            {
                "counts": manifest["counts"],
                "ledger_ok": "documents" in manifest["ledger"],
            }
        )
    )
    return 0 if "documents" in manifest["ledger"] else 1


if __name__ == "__main__":
    sys.exit(main())
