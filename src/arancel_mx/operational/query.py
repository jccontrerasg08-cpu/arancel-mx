"""Read-only serving queries over the active verified Neon release."""

from __future__ import annotations

from typing import Any, Protocol


class QueryCursor(Protocol):
    def fetchone(self) -> tuple[Any, ...] | None: ...

    def fetchall(self) -> list[tuple[Any, ...]]: ...


class QueryConnection(Protocol):
    def execute(
        self, statement: str, values: tuple[object, ...] | None = None
    ) -> QueryCursor: ...


_ACTIVE_RELEASE_METADATA = """
SELECT release.tag, release.dataset_version, release.schema_version, release.published_at
FROM operational_active_release AS active
JOIN operational_release AS release ON release.tag = active.tag
""".strip()


_ACTIVE_RELEASE_SEARCH = """
SELECT record.payload, record.code = %s AS exact_code, release.dataset_version
FROM current_operational_record AS record
JOIN operational_release AS release ON release.tag = record.release_tag
WHERE record.code = %s OR record.description ILIKE %s
ORDER BY exact_code DESC, record.code ASC
LIMIT %s
""".strip()


def _active_payload(payload: object, dataset_version: object) -> dict[str, object]:
    """Return one public record only when it matches the active release identity."""

    if not isinstance(payload, dict):
        raise ValueError("operational record payload must be an object")
    if str(payload.get("dataset_version")) != str(dataset_version):
        raise ValueError("operational record dataset_version does not match active release")
    return payload


def active_release_metadata(connection: QueryConnection) -> dict[str, object] | None:
    """Return the active serving release identity, never an unpromoted candidate."""

    row = connection.execute(_ACTIVE_RELEASE_METADATA).fetchone()
    if row is None:
        return None
    tag, dataset_version, schema_version, published_at = row
    return {
        "dataset_tag": str(tag),
        "dataset_version": str(dataset_version),
        "schema_version": str(schema_version),
        "release_published_at": published_at.isoformat()
        if hasattr(published_at, "isoformat")
        else str(published_at),
        "release_verified": True,
        "structural_valid": True,
        "read_only": True,
    }


def search_active_release(
    connection: QueryConnection, query: str, *, limit: int = 8
) -> list[dict[str, object]]:
    """Search public payloads only within the one atomically active release."""

    normalized = query.strip()
    if not normalized:
        raise ValueError("query is required")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    rows = connection.execute(
        _ACTIVE_RELEASE_SEARCH,
        (normalized, normalized, f"%{normalized}%", limit),
    ).fetchall()
    results: list[dict[str, object]] = []
    for payload, exact_code, dataset_version in rows:
        results.append(
            {
                "record": _active_payload(payload, dataset_version),
                "match_kind": "exact_code" if exact_code else "description",
                "score": 100 if exact_code else 50,
                "confidence": 1.0 if exact_code else 0.5,
            }
        )
    return results


_ACTIVE_RELEASE_LOOKUP = """
SELECT record.payload, release.dataset_version
FROM current_operational_record AS record
JOIN operational_release AS release ON release.tag = record.release_tag
WHERE record.code = %s
""".strip()

_ACTIVE_RELEASE_CHAPTERS = """
SELECT record.payload, release.dataset_version
FROM current_operational_record AS record
JOIN operational_release AS release ON release.tag = record.release_tag
WHERE record.level = 'hs2'
ORDER BY record.code ASC
""".strip()

_ACTIVE_RELEASE_CHILDREN = """
SELECT record.payload, release.dataset_version
FROM current_operational_record AS record
JOIN operational_release AS release ON release.tag = record.release_tag
WHERE record.level = %s AND record.code LIKE %s AND length(record.code) = %s
ORDER BY record.code ASC, record.description ASC
""".strip()

_ACTIVE_RELEASE_EVIDENCE = """
SELECT release.evidence_json
FROM operational_active_release AS active
JOIN operational_release AS release ON release.tag = active.tag
""".strip()

_PARENT_WIDTH = {2: None, 4: 2, 6: 4, 8: 6, 10: 8}
_CHILDREN = {2: ("hs4", 4), 4: ("hs6", 6), 6: ("fraccion8", 8), 8: ("nico10", 10)}


def _public_number(value: object) -> float | None:
    return None if value is None else float(value)


def _public_record(payload: object, dataset_version: object) -> dict[str, object]:
    """Adapt one active operational payload to the existing public tariff shape."""

    record = _active_payload(payload, dataset_version)
    code = str(record.get("code") or "")
    width = _PARENT_WIDTH.get(len(code))
    if not code or width is None and len(code) != 2:
        raise ValueError("operational record has an invalid tariff code")
    return {
        "code": code,
        "level": str(record.get("level") or ""),
        "description": str(record.get("description") or ""),
        "unit_name": record.get("unit_name"),
        "igi": {
            "text": record.get("igi_text"),
            "kind": record.get("igi_kind"),
            "value": _public_number(record.get("igi_value")),
        },
        "ige": {
            "text": record.get("ige_text"),
            "kind": record.get("ige_kind"),
            "value": _public_number(record.get("ige_value")),
        },
        "parent_code": None if width is None else code[:width],
        "dataset_version": str(dataset_version),
        "schema_version": str(record.get("schema_version") or ""),
        "effective_from": record.get("effective_from"),
        "effective_to": record.get("effective_to"),
        "is_current": bool(record.get("is_current")),
        "hierarchy": {
            key: record.get(key)
            for key in ("hs2", "hs4", "hs6", "fraccion8", "nico2", "nico10")
        },
        "ligie_version": record.get("ligie_version"),
        "validity_basis": record.get("validity_basis"),
    }


def lookup_active_release(connection: QueryConnection, code: str) -> dict[str, object] | None:
    """Return one exact active record in the stable public response shape."""

    from arancel_mx.consumer.query import normalize_code

    normalized = normalize_code(code)
    rows = connection.execute(_ACTIVE_RELEASE_LOOKUP, (normalized,)).fetchall()
    if len(rows) > 1:
        raise ValueError("multiple active records found for tariff code")
    return None if not rows else _public_record(*rows[0])


def chapters_active_release(connection: QueryConnection) -> list[dict[str, object]]:
    """Return all active HS2 chapters in the stable public response shape."""

    return [_public_record(*row) for row in connection.execute(_ACTIVE_RELEASE_CHAPTERS).fetchall()]


def children_active_release(connection: QueryConnection, code: str) -> list[dict[str, object]]:
    """Return only direct active hierarchy children for one verified record."""

    record = lookup_active_release(connection, code)
    if record is None:
        return []
    child = _CHILDREN.get(len(str(record["code"])))
    if child is None:
        return []
    level, width = child
    rows = connection.execute(
        _ACTIVE_RELEASE_CHILDREN,
        (level, f"{record['code']}%", width),
    ).fetchall()
    return [_public_record(*row) for row in rows]


def parent_active_release(connection: QueryConnection, code: str) -> dict[str, object] | None:
    """Return the direct verified parent, or null for an HS2 chapter."""

    record = lookup_active_release(connection, code)
    if record is None or record["parent_code"] is None:
        return None
    return lookup_active_release(connection, str(record["parent_code"]))


def active_release_evidence(connection: QueryConnection) -> dict[str, list[dict[str, object]]]:
    """Return evidence copied atomically with the active verified release."""

    row = connection.execute(_ACTIVE_RELEASE_EVIDENCE).fetchone()
    if row is None:
        return {"source_documents": [], "record_provenance": [], "national_notes": []}
    value = row[0]
    if isinstance(value, str):
        import json

        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError("active release evidence must be an object")
    return {
        key: value.get(key, [])
        for key in ("source_documents", "record_provenance", "national_notes")
    }


def national_notes_active_release(connection: QueryConnection, chapter: str) -> list[dict[str, object]]:
    """Return active materialized national notes for one two-digit chapter."""

    if len(chapter) != 2 or not chapter.isascii() or not chapter.isdigit():
        raise ValueError("chapter must be exactly two digits")
    notes = active_release_evidence(connection)["national_notes"]
    return [note for note in notes if note.get("chapter") == chapter]


def provenance_active_release(connection: QueryConnection, code: str) -> list[dict[str, object]]:
    """Return active source provenance with primary evidence first."""

    record = lookup_active_release(connection, code)
    if record is None:
        return []
    evidence = active_release_evidence(connection)
    documents = {
        str(item.get("source_document_id")): item
        for item in evidence["source_documents"]
    }
    rows = [
        item
        for item in evidence["record_provenance"]
        if item.get("code") == record["code"]
    ]
    result = []
    for item in rows:
        document = documents.get(str(item.get("source_document_id")))
        if document is not None:
            result.append({**item, **document})
    return sorted(
        result,
        key=lambda item: (
            not bool(item.get("is_primary")),
            str(item.get("source_document_id")),
            str(item.get("role")),
        ),
    )


_ACTIVE_RELEASE_RECORDS = """
SELECT record.payload, release.dataset_version
FROM current_operational_record AS record
JOIN operational_release AS release ON release.tag = record.release_tag
ORDER BY record.code ASC, record.description ASC
""".strip()


def _public_section(chapter: str) -> dict[str, object] | None:
    from arancel_mx.consumer.hs_sections import section_for_chapter

    section = section_for_chapter(chapter)
    if section is None:
        return None
    return {
        "roman": section.roman,
        "name": section.name,
        "chapter_from": section.chapter_from,
        "chapter_to": section.chapter_to,
        "source": section.source,
    }


def _format_code(code: str) -> str:
    return ".".join(code[index : index + 2] for index in range(0, len(code), 2))


def ficha_active_release(connection: QueryConnection, code: str) -> dict[str, object] | None:
    """Return the stable hierarchy card from one active operational release."""

    record = lookup_active_release(connection, code)
    if record is None:
        return None
    tariff_code = str(record["code"])
    hierarchy = [
        item
        for width in (2, 4, 6, 8, 10)
        if width <= len(tariff_code)
        if (item := lookup_active_release(connection, tariff_code[:width])) is not None
    ]
    return {
        "record": record,
        "formatted_code": _format_code(tariff_code),
        "section": _public_section(tariff_code[:2]),
        "hierarchy": hierarchy,
        "children": children_active_release(connection, tariff_code),
    }


def _public_search_score(text: str, record: dict[str, object]) -> tuple[int, str, float] | None:
    from arancel_mx.consumer.query import _confidence, _normalize_text, _search_code_candidate

    candidate = _search_code_candidate(text.strip())
    code = str(record["code"])
    if candidate is not None and code == candidate:
        return (1000, "exact_code", 1.0)
    if candidate is not None and code.startswith(candidate):
        return (700, "code_prefix", 0.85)
    tokens = tuple(token for token in _normalize_text(text).split(" ") if token)
    if not tokens:
        return None
    matched = sum(token in _normalize_text(str(record["description"])) for token in tokens)
    if not matched:
        return None
    score = 300 + 25 * matched + (5 if matched == len(tokens) else 0)
    return (score, "description", _confidence("description", matched, len(tokens)))


def search_public_active_release(
    connection: QueryConnection, text: str, *, limit: int
) -> list[dict[str, object]]:
    """Return the existing deterministic retrieve-only search contract on Vercel."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("search text must not be empty")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    # ponytail: the certified active release is a bounded public tariff table. Upgrade to
    # normalized Neon search columns when active records outgrow this function's request budget.
    candidates = []
    for row in connection.execute(_ACTIVE_RELEASE_RECORDS).fetchall():
        record = _public_record(*row)
        matched = _public_search_score(text, record)
        if matched is not None:
            score, match_kind, confidence = matched
            candidates.append((record, score, match_kind, confidence))
    from arancel_mx.consumer.query import _search_code_candidate

    code_candidate = _search_code_candidate(text.strip())
    if code_candidate is None:
        chapter_score: dict[str, int] = {}
        for record, score, _kind, _confidence_value in candidates:
            chapter = str(record["hierarchy"]["hs2"] or record["code"][:2])
            chapter_score[chapter] = max(chapter_score.get(chapter, score), score)
        candidates.sort(
            key=lambda item: (
                -chapter_score[str(item[0]["hierarchy"]["hs2"] or item[0]["code"][:2])],
                -item[1],
                str(item[0]["code"]),
                str(item[0]["description"]),
            )
        )
    else:
        candidates.sort(key=lambda item: (-item[1], str(item[0]["code"]), str(item[0]["description"])))
    return [
        {
            "record": record,
            "score": score,
            "match_kind": match_kind,
            "scorer_version": "1",
            "confidence": confidence,
        }
        for record, score, match_kind, confidence in candidates[:limit]
    ]


def suggest_active_release(
    connection: QueryConnection, text: str, *, limit: int
) -> list[dict[str, object]]:
    """Return bounded retrieve-only suggestions with hierarchy and official notes."""

    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")
    ranked = search_public_active_release(connection, text, limit=50)
    preferred = [item for item in ranked if item["record"]["level"] == "fraccion8"]
    chosen = (preferred or ranked)[:limit]
    return [
        {
            "search": item,
            "ficha": ficha_active_release(connection, str(item["record"]["code"])),
            "national_notes": national_notes_active_release(
                connection, str(item["record"]["hierarchy"]["hs2"] or item["record"]["code"][:2])
            ),
            "disclaimer": "This is not a classification. Retrieve-only matches from the official dataset. WCO is not LIGIE/NICO authority.",
        }
        for item in chosen
    ]


def sections_active_release() -> list[dict[str, object]]:
    """Return the canonical static HS section hierarchy used by ficha responses."""

    from arancel_mx.consumer.hs_sections import hs_sections

    return [
        {
            "roman": section.roman,
            "name": section.name,
            "chapter_from": section.chapter_from,
            "chapter_to": section.chapter_to,
            "source": section.source,
        }
        for section in hs_sections()
    ]
