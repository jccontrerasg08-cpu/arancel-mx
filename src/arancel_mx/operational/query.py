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
SELECT record.payload, record.code = %s AS exact_code
FROM current_operational_record AS record
WHERE record.code = %s OR record.description ILIKE %s
ORDER BY exact_code DESC, record.code ASC
LIMIT %s
""".strip()


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
    for payload, exact_code in rows:
        if not isinstance(payload, dict):
            raise ValueError("operational record payload must be an object")
        results.append(
            {
                "record": payload,
                "match_kind": "exact_code" if exact_code else "description",
                "score": 100 if exact_code else 50,
                "confidence": 1.0 if exact_code else 0.5,
            }
        )
    return results
