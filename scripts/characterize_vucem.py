"""Characterize VUCEM Clasificador pages without making them publication authority."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import time
import unicodedata
from collections.abc import Callable, Iterable, Mapping


VUCEM_BASE_URL = (
    "https://www.ventanillaunica.gob.mx/Clasificador/data/buildHojas1/{code}.html"
)
_TARIFF_CODE = re.compile(r"^[0-9]{8}$")


@dataclass(frozen=True)
class PageSnapshot:
    """Captured identity and decoded HTML for one VUCEM classifier page."""

    final_url: str
    media_type: str
    retrieved_at: str
    sha256: str
    byte_size: int
    html: str


class _StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: Counter[str] = Counter()
        self.ids: set[str] = set()
        self.classes: set[str] = set()
        self.text_parts: list[str] = []
        self.page_title_parts: list[str] = []
        self.headings: list[str] = []
        self._capture_title = False
        self._heading_tag: str | None = None
        self._heading_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized_tag = tag.lower()
        self.tags[normalized_tag] += 1
        attrs_dict = {str(key).lower(): str(value or "") for key, value in attrs}
        if attrs_dict.get("id"):
            self.ids.add(attrs_dict["id"])
        for value in attrs_dict.get("class", "").split():
            if value:
                self.classes.add(value)
        if normalized_tag == "title":
            self._capture_title = True
        if normalized_tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_tag = normalized_tag
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag == "title":
            self._capture_title = False
        if normalized_tag == self._heading_tag:
            heading = " ".join(" ".join(self._heading_parts).split())
            if heading:
                self.headings.append(heading)
            self._heading_tag = None
            self._heading_parts = []

    def handle_data(self, data: str) -> None:
        if not data:
            return
        self.text_parts.append(data)
        if self._capture_title:
            self.page_title_parts.append(data)
        if self._heading_tag is not None:
            self._heading_parts.append(data)


def build_vucem_url(code: str) -> str:
    """Build the known VUCEM classifier page URL for one MX8 tariff fraction."""
    normalized = str(code).strip()
    if _TARIFF_CODE.fullmatch(normalized) is None:
        raise ValueError("VUCEM characterization requires an 8-digit tariff fraction")
    return VUCEM_BASE_URL.format(code=normalized)


def select_sample_rows(
    rows: Iterable[Mapping[str, object]], sample_size: int
) -> list[dict[str, str]]:
    """Select deterministic MX8 rows round-robin across chapters."""
    if sample_size < 1:
        raise ValueError("sample_size must be positive")

    by_chapter: dict[str, list[dict[str, str]]] = {}
    seen: set[str] = set()
    for raw in rows:
        level = str(raw.get("level") or "").strip().lower()
        code = str(raw.get("code") or "").strip()
        if (
            level != "fraccion8"
            or _TARIFF_CODE.fullmatch(code) is None
            or code in seen
        ):
            continue
        seen.add(code)
        row = {str(key): str(value or "") for key, value in raw.items()}
        by_chapter.setdefault(code[:2], []).append(row)

    for values in by_chapter.values():
        values.sort(key=lambda row: row["code"])

    selected: list[dict[str, str]] = []
    chapters = sorted(by_chapter)
    index = 0
    while chapters and len(selected) < sample_size:
        remaining: list[str] = []
        for chapter in chapters:
            values = by_chapter[chapter]
            if index < len(values) and len(selected) < sample_size:
                selected.append(values[index])
            if index + 1 < len(values):
                remaining.append(chapter)
        chapters = remaining
        index += 1
    return selected


def _normalized_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value))
    without_marks = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(without_marks.casefold().split())


def _description_token_coverage(reference: str, page_text: str) -> float | None:
    reference_tokens = set(re.findall(r"[a-z0-9]+", _normalized_text(reference)))
    if not reference_tokens:
        return None
    page_tokens = set(re.findall(r"[a-z0-9]+", _normalized_text(page_text)))
    return round(len(reference_tokens & page_tokens) / len(reference_tokens), 4)


def analyze_vucem_html(
    code: str, html: str, snice_description: str = ""
) -> dict[str, object]:
    """Extract structural signals for characterization, not legal/tariff authority."""
    build_vucem_url(code)
    parser = _StructureParser()
    parser.feed(html)
    parser.close()

    page_text = " ".join(" ".join(parser.text_parts).split())
    normalized_page = _normalized_text(page_text)
    normalized_description = _normalized_text(snice_description)
    structure = {
        "tag_counts": dict(sorted(parser.tags.items())),
        "table_count": parser.tags.get("table", 0),
        "row_count": parser.tags.get("tr", 0),
        "cell_count": parser.tags.get("td", 0) + parser.tags.get("th", 0),
        "form_count": parser.tags.get("form", 0),
        "script_count": parser.tags.get("script", 0),
        "ids": sorted(parser.ids),
        "classes": sorted(parser.classes),
    }
    schema_fingerprint = hashlib.sha256(
        json.dumps(structure, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "page_title": " ".join(" ".join(parser.page_title_parts).split()),
        "headings": parser.headings,
        "text_chars": len(page_text),
        "code_present": code in re.sub(r"\D", "", page_text),
        "snice_description_present": bool(normalized_description)
        and normalized_description in normalized_page,
        "snice_description_token_coverage": _description_token_coverage(
            snice_description, page_text
        ),
        "structure": structure,
        "schema_fingerprint": schema_fingerprint,
    }


def run_characterization(
    rows: Iterable[Mapping[str, object]],
    sample_size: int,
    fetcher: Callable[[str], PageSnapshot],
) -> dict[str, object]:
    """Characterize a deterministic sample while keeping VUCEM non-blocking."""
    sample = select_sample_rows(rows, sample_size)
    results: list[dict[str, object]] = []
    fingerprints: set[str] = set()
    fetched = 0
    errors = 0
    code_matches = 0
    description_exact_matches = 0
    token_coverages: list[float] = []

    for row in sample:
        code = row["code"]
        url = build_vucem_url(code)
        base = {
            "code": code,
            "chapter": code[:2],
            "snice_description": row.get("description", ""),
            "requested_url": url,
        }
        try:
            snapshot = fetcher(url)
            analysis = analyze_vucem_html(
                code,
                snapshot.html,
                str(row.get("description") or ""),
            )
            fingerprints.add(str(analysis["schema_fingerprint"]))
            fetched += 1
            code_matches += int(bool(analysis["code_present"]))
            description_exact_matches += int(
                bool(analysis["snice_description_present"])
            )
            coverage = analysis["snice_description_token_coverage"]
            if isinstance(coverage, float):
                token_coverages.append(coverage)
            results.append(
                {
                    **base,
                    "status": "fetched",
                    "final_url": snapshot.final_url,
                    "media_type": snapshot.media_type,
                    "retrieved_at": snapshot.retrieved_at,
                    "sha256": snapshot.sha256,
                    "byte_size": snapshot.byte_size,
                    **analysis,
                }
            )
        except Exception as exc:
            errors += 1
            results.append(
                {
                    **base,
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error_message": " ".join(str(exc).split())[:500],
                }
            )

    mean_token_coverage = (
        round(sum(token_coverages) / len(token_coverages), 4)
        if token_coverages
        else None
    )
    return {
        "schema_version": "1",
        "source": "VUCEM Clasificador Arancelario",
        "reference": "arancel_mx.csv canonical MX8 rows",
        "source_role": "independent_operational_cross_check",
        "authoritative_for_tariff": False,
        "publication_gate": False,
        "sample_size_requested": sample_size,
        "sample_size_actual": len(sample),
        "summary": {
            "fetched": fetched,
            "errors": errors,
            "coverage_rate": round(fetched / len(sample), 4) if sample else 0.0,
            "code_match_rate": round(code_matches / fetched, 4) if fetched else None,
            "description_exact_match_rate": (
                round(description_exact_matches / fetched, 4) if fetched else None
            ),
            "mean_description_token_coverage": mean_token_coverage,
            "chapters_sampled": sorted({row["code"][:2] for row in sample}),
            "unique_schema_fingerprints": len(fingerprints),
        },
        "results": results,
    }


def load_public_csv(path: Path | str) -> list[dict[str, str]]:
    """Load the public arancel_mx CSV fields needed for VUCEM comparison."""
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        required = {"code", "level", "description"}
        missing = sorted(required - fields)
        if missing:
            raise ValueError(
                f"public CSV is missing required columns: {', '.join(missing)}"
            )
        return [
            {str(key): str(value or "") for key, value in row.items()}
            for row in reader
        ]


def _live_fetcher(
    timeout_s: float, max_bytes: int, delay_ms: int
) -> Callable[[str], PageSnapshot]:
    import requests

    from arancel_mx.sources.http import decode_fetched_text, fetch_official_document

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "arancel-mx-vucem-characterization/0.1 "
                "(+https://github.com/jccontrerasg08-cpu/arancel-mx)"
            )
        }
    )

    def fetch(url: str) -> PageSnapshot:
        document = fetch_official_document(
            session,
            url,
            allowed_hosts=("www.ventanillaunica.gob.mx", "ventanillaunica.gob.mx"),
            media_types=("text/html",),
            timeout_s=timeout_s,
            max_bytes=max_bytes,
        )
        html = decode_fetched_text(document)
        snapshot = PageSnapshot(
            final_url=document.final_url,
            media_type=document.media_type,
            retrieved_at=document.retrieved_at.isoformat(),
            sha256=hashlib.sha256(document.content).hexdigest(),
            byte_size=len(document.content),
            html=html,
        )
        if delay_ms:
            time.sleep(delay_ms / 1000)
        return snapshot

    return fetch


def _dry_run_report(
    rows: Iterable[Mapping[str, object]], sample_size: int
) -> dict[str, object]:
    sample = select_sample_rows(rows, sample_size)
    return {
        "schema_version": "1",
        "source": "VUCEM Clasificador Arancelario",
        "reference": "arancel_mx.csv canonical MX8 rows",
        "source_role": "independent_operational_cross_check",
        "authoritative_for_tariff": False,
        "publication_gate": False,
        "sample_size_requested": sample_size,
        "sample_size_actual": len(sample),
        "summary": {
            "fetched": 0,
            "errors": 0,
            "coverage_rate": 0.0,
            "code_match_rate": None,
            "description_exact_match_rate": None,
            "mean_description_token_coverage": None,
            "chapters_sampled": sorted({row["code"][:2] for row in sample}),
            "unique_schema_fingerprints": 0,
        },
        "results": [
            {
                "code": row["code"],
                "chapter": row["code"][:2],
                "snice_description": row.get("description", ""),
                "requested_url": build_vucem_url(row["code"]),
                "status": "planned",
            }
            for row in sample
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Characterize VUCEM Clasificador pages against a public arancel-mx CSV. "
            "This tool never changes source_registry or publication authority."
        )
    )
    parser.add_argument("--snice-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=120)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-bytes", type=int, default=2 * 1024 * 1024)
    parser.add_argument("--delay-ms", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    rows = load_public_csv(args.snice_csv)
    if args.dry_run:
        report = _dry_run_report(rows, args.sample_size)
    else:
        report = run_characterization(
            rows,
            sample_size=args.sample_size,
            fetcher=_live_fetcher(args.timeout, args.max_bytes, args.delay_ms),
        )
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["registry_review_ready"] = report["summary"]["fetched"] >= 100

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
