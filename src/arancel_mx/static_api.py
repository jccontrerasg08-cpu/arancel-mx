"""Static, read-only data API generated from one verified release.

The export uses the same response models as HTTP ``/v1`` and splits the data
by HS2 chapter. Every record of a chapter shares the chapter prefix, so lookup,
ficha, parent and children all resolve from one chapter file. ``StaticApi``
answers from the exported files with the semantics of ``arancel_mx.consumer``.
It is the reference that the browser client reproduces and the parity tests
check (decision 0002).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from arancel_mx import __version__
from arancel_mx.api import API_VERSION
from arancel_mx.api.models import (
    FichaResponse,
    NationalNoteResponse,
    ProvenanceResponse,
    SearchResponse,
    SectionResponse,
    SuggestResponse,
    TariffResponse,
)
from arancel_mx.consumer.dataset import Dataset
from arancel_mx.consumer.errors import QueryError, RecordNotFoundError
from arancel_mx.consumer.hs_sections import hs_sections, section_for_chapter
from arancel_mx.consumer.query import (
    _CHILD_LEVEL,
    _ROW_SELECT,
    _normalize_text,
    _row_to_tariff_record,
    _search_code_candidate,
    SCORER_VERSION,
    SUGGEST_DISCLAIMER,
    format_code,
    national_notes,
    normalize_code,
)

STATIC_FORMAT = "1"

_PROVENANCE_SELECT = """
    SELECT c.code, d.source_document_id, p.role, p.is_primary,
           d.authority, d.publication_venue, d.title, d.source_url, d.sha256,
           d.published_at, d.effective_from, d.effective_to
    FROM canonical_record c
    JOIN record_provenance p ON p.record_id = c.record_id
    JOIN source_document d ON d.source_document_id = p.source_document_id
    WHERE c.is_current = TRUE
    ORDER BY c.code ASC, p.is_primary DESC, d.source_document_id ASC, p.role ASC
"""
_SOURCE_FIELDS = (
    "authority",
    "publication_venue",
    "title",
    "source_url",
    "sha256",
    "published_at",
    "effective_from",
    "effective_to",
)


def _dump(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
        + "\n"
    ).encode("utf-8")


def _model(value: Any) -> Any:
    return value.model_dump(mode="json")


def build_static_api(
    dataset_path: Path,
    out_dir: Path,
    *,
    dataset_tag: str,
    release_verified: bool,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Write the static API for one release and return its manifest."""

    dataset = Dataset.open(dataset_path)
    info = dataset.info
    files: dict[str, bytes] = {}

    with dataset.connect() as connection:
        rows = connection.execute(
            _ROW_SELECT + " WHERE is_current = TRUE ORDER BY code ASC, description ASC"
        ).fetchall()
        records = [_row_to_tariff_record(row) for row in rows]
        by_chapter: dict[str, list[dict[str, Any]]] = defaultdict(list)
        index: list[list[str]] = []
        for record in records:
            by_chapter[record.code[:2]].append(
                _model(TariffResponse.from_record(record))
            )
            index.append([record.code, _normalize_text(record.description)])

        sources: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        links: dict[str, dict[str, list[list[Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for row in connection.execute(_PROVENANCE_SELECT).fetchall():
            code, source_id, role, is_primary, *document = row
            chapter = str(code)[:2]
            response = ProvenanceResponse(
                source_document_id=str(source_id),
                role=str(role),
                is_primary=bool(is_primary),
                **{field: value for field, value in zip(_SOURCE_FIELDS, document)},
            )
            dumped = _model(response)
            sources[chapter][str(source_id)] = {
                field: dumped[field] for field in _SOURCE_FIELDS
            }
            links[chapter][str(code)].append(
                [str(source_id), str(role), bool(is_primary)]
            )

        chapters = sorted(by_chapter)
        for chapter in chapters:
            files[f"records/{chapter}.json"] = _dump(by_chapter[chapter])
            files[f"provenance/{chapter}.json"] = _dump(
                {"sources": sources.get(chapter, {}), "links": links.get(chapter, {})}
            )
            files[f"national-notes/{chapter}.json"] = _dump(
                [
                    _model(NationalNoteResponse.from_note(note))
                    for note in national_notes(connection, chapter)
                ]
            )

    files["chapters.json"] = _dump(
        [
            record
            for chapter in chapters
            for record in by_chapter[chapter]
            if record["level"] == "hs2"
        ]
    )
    files["sections.json"] = _dump(
        [_model(SectionResponse.from_section(section)) for section in hs_sections()]
    )
    files["search-index.json"] = _dump(
        {"scorer_version": SCORER_VERSION, "entries": index}
    )
    files["meta.json"] = _dump(
        {
            "api_version": API_VERSION,
            "package_version": __version__,
            "dataset_tag": dataset_tag,
            "dataset_version": info.dataset_version,
            "schema_version": info.schema_version,
            "read_only": True,
            "release_verified": release_verified,
            "structural_valid": info.structural_valid,
            "static_format": STATIC_FORMAT,
        }
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        target = out_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    manifest = {
        "static_format": STATIC_FORMAT,
        "dataset_tag": dataset_tag,
        "dataset_version": info.dataset_version,
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "record_count": len(records),
        "files": {
            name: {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
            for name, content in sorted(files.items())
        },
    }
    (out_dir / "manifest.json").write_bytes(_dump(manifest))
    return manifest


def verify_static_api(root: Path) -> list[str]:
    """Return the files whose bytes do not match the manifest (empty when valid)."""

    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    for name, expected in manifest["files"].items():
        path = root / name
        if not path.is_file():
            problems.append(f"missing: {name}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
            problems.append(f"sha256 mismatch: {name}")
    return problems


class StaticApi:
    """Answer ``/v1`` questions from an exported static tree."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._cache: dict[str, Any] = {}

    def _json(self, name: str) -> Any:
        if name not in self._cache:
            path = self.root / name
            self._cache[name] = (
                json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
            )
        return self._cache[name]

    def _chapter_records(self, chapter: str) -> list[dict[str, Any]]:
        return self._json(f"records/{chapter}.json") or []

    def _find(self, code: str) -> dict[str, Any] | None:
        return next(
            (item for item in self._chapter_records(code[:2]) if item["code"] == code),
            None,
        )

    def lookup(self, code: str) -> TariffResponse:
        normalized = normalize_code(code)
        record = self._find(normalized)
        if record is None:
            raise RecordNotFoundError(f"tariff record not found: {normalized}")
        return TariffResponse.model_validate(record)

    def parent(self, code: str) -> TariffResponse | None:
        record = self.lookup(code)
        return None if record.parent_code is None else self.lookup(record.parent_code)

    def children(self, code: str) -> list[TariffResponse]:
        record = self.lookup(code)
        level = _CHILD_LEVEL[len(record.code)]
        if level is None:
            return []
        width = {"hs4": 4, "hs6": 6, "fraccion8": 8, "nico10": 10}[level]
        return [
            TariffResponse.model_validate(item)
            for item in self._chapter_records(record.code[:2])
            if item["level"] == level
            and len(item["code"]) == width
            and item["code"].startswith(record.code)
        ]

    def ficha(self, code: str) -> FichaResponse:
        record = self.lookup(code)
        section = section_for_chapter(record.code[:2])
        return FichaResponse(
            record=record,
            formatted_code=format_code(record.code),
            section=SectionResponse.from_section(section)
            if section is not None
            else None,
            hierarchy=[
                self.lookup(record.code[:width])
                for width in (2, 4, 6, 8, 10)
                if width <= len(record.code)
            ],
            children=self.children(record.code),
        )

    def provenance(self, code: str) -> list[ProvenanceResponse]:
        record = self.lookup(code)
        data = self._json(f"provenance/{record.code[:2]}.json") or {
            "sources": {},
            "links": {},
        }
        return [
            ProvenanceResponse(
                source_document_id=source_id,
                role=role,
                is_primary=is_primary,
                **data["sources"][source_id],
            )
            for source_id, role, is_primary in data["links"].get(record.code, [])
        ]

    def national_notes(self, chapter: str) -> list[NationalNoteResponse]:
        if len(chapter) != 2 or not chapter.isascii() or not chapter.isdigit():
            raise QueryError("chapter must be exactly two digits")
        return [
            NationalNoteResponse.model_validate(item)
            for item in self._json(f"national-notes/{chapter}.json") or []
        ]

    def search(self, text: str, *, limit: int = 20) -> list[SearchResponse]:
        if limit <= 0:
            raise ValueError("search limit must be greater than zero")
        if not isinstance(text, str) or not text.strip():
            raise QueryError("search text must not be empty")
        tokens = tuple(token for token in _normalize_text(text).split(" ") if token)
        code_candidate = _search_code_candidate(text.strip())
        hits: list[tuple[str, int, str, float]] = []
        for code, description in self._json("search-index.json")["entries"]:
            if code_candidate is not None and code == code_candidate:
                hits.append((code, 1000, "exact_code", 1.0))
            elif code_candidate is not None and code.startswith(code_candidate):
                hits.append((code, 700, "code_prefix", 0.85))
            else:
                matched = sum(1 for token in tokens if token in description)
                if matched:
                    score = 300 + 25 * matched + (5 if matched == len(tokens) else 0)
                    hits.append((code, score, "description", matched / len(tokens)))
        if code_candidate is None:
            best: dict[str, int] = {}
            for code, score, _, _ in hits:
                best[code[:2]] = max(score, best.get(code[:2], score))
            hits.sort(key=lambda hit: (-best[hit[0][:2]], -hit[1], hit[0]))
        else:
            hits.sort(key=lambda hit: (-hit[1], hit[0]))
        return [
            SearchResponse(
                record=self.lookup(code),
                score=score,
                match_kind=kind,
                scorer_version=SCORER_VERSION,
                confidence=confidence,
            )
            for code, score, kind, confidence in hits[:limit]
        ]

    def suggest(self, text: str, *, limit: int = 5) -> list[SuggestResponse]:
        if limit <= 0:
            raise ValueError("suggest limit must be greater than zero")
        ranked = self.search(text, limit=2**31 - 1)
        chosen = [item for item in ranked if item.record.level == "fraccion8"] or ranked
        return [
            SuggestResponse(
                search=item,
                ficha=self.ficha(item.record.code),
                national_notes=self.national_notes(item.record.code[:2]),
                disclaimer=SUGGEST_DISCLAIMER,
            )
            for item in chosen[:limit]
        ]
