# API v1 National Notes Scope and OpenAPI Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve National Note applicability semantics end-to-end and make OpenAPI describe the public FastAPI v1 runtime contract accurately without breaking existing `/v1` clients or immutable legacy data releases.

**Architecture:** Persist parser-provided applicability into the existing `national_note_applicability` table, expose it through the public notes view, and make the consumer feature-detect legacy versus new view shapes. Legacy immutable snapshots remain serviceable with unresolved scope metadata instead of inferred legal scope. The HTTP layer maps additive consumer fields directly and uses reusable FastAPI `responses` mappings plus typed health/readiness models.

**Tech Stack:** Python 3.11+ package runtime, Python 3.13 FastAPI Cloud runtime, DuckDB, FastAPI, Pydantic, pytest, Ruff, mypy, GitHub Actions.

## Global Constraints

- Keep the public HTTP namespace at `/v1`; all response changes are additive.
- Do not remove, rename, or reinterpret existing National Note response fields.
- New National Note fields are `scope_type: str | None`, `scope_value: str | None`, and `applicability_basis: str`.
- New official releases persist parser-provided scope and use `applicability_basis="explicit"` for the supported source path.
- Legacy immutable snapshots without scope columns return `scope_type=None`, `scope_value=None`, `applicability_basis="unresolved"`.
- Never infer legal scope from note text, note number, source title, or chapter attachment.
- Keep `data-2026.08.15` immutable and usable by newer package/API code.
- Do not change search/suggest ranking, compression, caching, rate limiting, auth, provenance semantics, tariff values, hierarchy, or NICO behavior in this PR.
- Keep the API GET-only and read-only.
- Add no runtime dependency.
- Preserve current primary National Note ordering by `note_number`; use scope/source/version only as stable tie-breakers.
- Use one focused PR from `fix/api-v1-notes-openapi-contract` to `main`.

---

## File Structure

- Modify `src/arancel_mx/pipeline/build.py`: persist applicability, expose it in the view, validate one applicability row per new note version.
- Modify `src/arancel_mx/consumer/models.py`: append additive scope fields to `NationalNote` with legacy-safe defaults.
- Modify `src/arancel_mx/consumer/query.py`: feature-detect old/new notes views and map them without inference.
- Modify `src/arancel_mx/api/models.py`: add scope fields plus typed health/readiness models.
- Create `src/arancel_mx/api/openapi.py`: reusable `ErrorEnvelope` response mappings.
- Modify `src/arancel_mx/api/routes.py`: attach endpoint-specific OpenAPI error mappings and typed health response.
- Modify `src/arancel_mx/api/app.py`: type `/readyz` and document 503.
- Modify `tests/pipeline/test_build.py`, `tests/consumer/test_national_notes_public.py`, `tests/api/test_models.py`, `tests/api/test_notes_routes.py`, `tests/api/test_openapi.py`, `tests/api/test_service_routes.py`, `tests/package/test_quality_tooling.py`.
- Modify `.github/workflows/ci.yml`: Python 3.13 smoke against immutable `data-2026.08.15` must prove legacy notes remain serviceable.
- Modify `CHANGELOG.md`: document additive semantics and OpenAPI correction under `Unreleased`.

---

### Task 1: Persist National Note Applicability and Validate It

**Files:**
- Modify: `tests/pipeline/test_build.py`
- Modify: `src/arancel_mx/pipeline/build.py`

**Interfaces:**
- Consumes: National Note input rows with `chapter`, `note_number`, `text`, `source_document_id`, optionally `scope_type`, `scope_value`, `applicability_basis`.
- Produces: one deterministic `national_note_applicability` row per `national_note_version_id`; scope-aware `arancel_mx_national_notes`; validation check `national_note_applicability_cardinality`.

- [ ] **Step 1: Add one exact helper for National Notes build inputs**

Add to `tests/pipeline/test_build.py` after `release_metadata()`:

```python
def note_build_inputs(chapter: str = "01"):
    source = {
        "source_document_id": "doc-1",
        "authority": "Cámara de Diputados",
        "publication_venue": "DOF",
        "title": "LIGIE",
        "source_url": "https://www.diputados.gob.mx/ligie.pdf",
        "sha256": "a" * 64,
        "observed_at": date(2026, 8, 9),
        "retrieved_at": datetime(2026, 8, 9, 12, 0),
    }
    classification = {
        "level": "hs2",
        "code": chapter,
        "description": "Capítulo de prueba.",
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "updated_at": date(2026, 8, 9),
        "source_document_id": "doc-1",
    }
    release = {
        "dataset_version": "2026.08.09",
        "schema_version": "2",
        "ligie_version": "LIGIE-2022",
        "effective_as_of": date(2026, 8, 9),
        "generated_at": datetime(2026, 8, 9, 12, 0),
        "release_metadata": release_metadata(),
    }
    return source, classification, release
```

Use this helper only in the National Notes tests touched by this plan.

- [ ] **Step 2: Write the failing persistence regression**

Replace the body setup of `test_build_materializes_national_notes_into_the_public_view` with:

```python
source, classification, release = note_build_inputs("85")
notes = [
    {
        "chapter": "85",
        "scope_type": "section",
        "scope_value": "XVI",
        "applicability_basis": "explicit",
        "note_number": "1",
        "text": "Nota nacional materializada desde la Sección XVI.",
        "source_document_id": "doc-1",
    }
]

with connect(path) as connection:
    materialize_arancel(
        connection, [source], [classification], [], release, national_notes=notes
    )
    first_id = connection.execute(
        "SELECT applicability_id FROM national_note_applicability"
    ).fetchone()[0]
    applicability = connection.execute(
        """
        SELECT scope_type, scope_value, applicability_basis, source_document_id
        FROM national_note_applicability
        """
    ).fetchone()
    public_note = connection.execute(
        """
        SELECT chapter, scope_type, scope_value, applicability_basis,
               note_number, text, source_document_id
        FROM arancel_mx_national_notes
        """
    ).fetchone()
    materialize_arancel(
        connection, [source], [classification], [], release, national_notes=notes
    )
    second_id = connection.execute(
        "SELECT applicability_id FROM national_note_applicability"
    ).fetchone()[0]

assert first_id == second_id
assert applicability == ("section", "XVI", "explicit", "doc-1")
assert public_note == (
    "85",
    "section",
    "XVI",
    "explicit",
    "1",
    "Nota nacional materializada desde la Sección XVI.",
    "doc-1",
)
```

Keep the existing second materialization-with-no-notes assertion in a separate test so this regression has one purpose.

- [ ] **Step 3: Run the focused test and verify RED**

```bash
python -m pytest -q tests/pipeline/test_build.py::test_build_materializes_national_notes_into_the_public_view
```

Expected: FAIL because no applicability row is inserted and the view has no scope columns.

- [ ] **Step 4: Persist deterministic applicability rows**

In `_insert_national_notes`, after inserting `national_note_version`, add:

```python
scope_type = str(row.get("scope_type") or "chapter")
scope_value_obj = row.get("scope_value", row.get("chapter"))
scope_value = None if scope_value_obj is None else str(scope_value_obj)
applicability_basis = str(row.get("applicability_basis") or "explicit")
applicability_id = str(
    row.get("applicability_id")
    or hashlib.sha256(
        canonical_json(
            [version_id, scope_type, scope_value, applicability_basis, source_id]
        ).encode("utf-8")
    ).hexdigest()
)
conn.execute(
    "INSERT INTO national_note_applicability VALUES (?, ?, ?, ?, ?, ?)",
    [
        applicability_id,
        version_id,
        scope_type,
        scope_value,
        applicability_basis,
        source_id,
    ],
)
```

Do not derive section scope from any text field.

- [ ] **Step 5: Expose applicability in the public view**

Replace the National Notes view in `_build_view` with:

```sql
CREATE OR REPLACE VIEW arancel_mx_national_notes AS
SELECT n.national_note_id,
       n.chapter,
       a.scope_type,
       a.scope_value,
       a.applicability_basis,
       n.note_number,
       v.national_note_version_id,
       v.text,
       v.effective_from,
       v.effective_to,
       v.source_document_id
FROM national_note n
JOIN national_note_version v USING (national_note_id)
JOIN national_note_applicability a USING (national_note_version_id)
```

- [ ] **Step 6: Write a failing cardinality validation regression**

Change the import to:

```python
from arancel_mx.pipeline.build import _validate_database, materialize_arancel
```

Add:

```python
def test_validation_rejects_missing_national_note_applicability(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    source, classification, release = note_build_inputs("01")
    notes = [
        {
            "chapter": "01",
            "note_number": "1",
            "text": "Los animales vivos de este capítulo.",
            "source_document_id": "doc-1",
        }
    ]

    with connect(path) as connection:
        materialize_arancel(
            connection, [source], [classification], [], release, national_notes=notes
        )
        connection.execute("DELETE FROM national_note_applicability")
        with pytest.raises(
            ValueError,
            match="national_note_applicability_cardinality",
        ):
            _validate_database(connection)
```

- [ ] **Step 7: Run that test and verify RED**

```bash
python -m pytest -q tests/pipeline/test_build.py::test_validation_rejects_missing_national_note_applicability
```

Expected: FAIL because `_validate_database` does not yet include the cardinality check.

- [ ] **Step 8: Add the validation check**

Inside `_validate_database` add:

```python
"national_note_applicability_cardinality": conn.execute(
    """
    SELECT COUNT(*) FROM (
        SELECT v.national_note_version_id,
               COUNT(a.applicability_id) AS applicability_count
        FROM national_note_version v
        LEFT JOIN national_note_applicability a
          USING (national_note_version_id)
        GROUP BY v.national_note_version_id
        HAVING applicability_count <> 1
    )
    """
).fetchone()[0],
```

- [ ] **Step 9: Run Task 1 GREEN**

```bash
python -m pytest -q tests/pipeline/test_build.py tests/parsers/test_national_notes.py
python -m ruff check src/arancel_mx/pipeline/build.py tests/pipeline/test_build.py
```

Expected: PASS.

- [ ] **Step 10: Commit Task 1**

```bash
git add src/arancel_mx/pipeline/build.py tests/pipeline/test_build.py
git commit -m "fix: persist national note applicability"
```

---

### Task 2: Add Consumer Scope Fields with Legacy Snapshot Fallback

**Files:**
- Modify: `tests/consumer/test_national_notes_public.py`
- Modify: `src/arancel_mx/consumer/models.py`
- Modify: `src/arancel_mx/consumer/query.py`

**Interfaces:**
- Consumes: old 8-column `arancel_mx_national_notes` or new scope-aware view.
- Produces: precise new-release `NationalNote` objects and unresolved legacy `NationalNote` objects.

- [ ] **Step 1: Rename the current old-view helper**

Rename `_materialize_note` to `_materialize_legacy_note` and update its call sites.

Update the existing expected note to:

```python
NationalNote(
    chapter="01",
    note_number="1",
    text="Los animales vivos de este capítulo.",
    source_document_id="fixture-source",
    scope_type=None,
    scope_value=None,
    applicability_basis="unresolved",
)
```

- [ ] **Step 2: Add a scope-aware fixture**

Add:

```python
def _materialize_scoped_notes(path: Path) -> None:
    connection = duckdb.connect(str(path))
    try:
        connection.execute("INSERT INTO national_note VALUES ('section-85-1', '85', '1')")
        connection.execute("INSERT INTO national_note VALUES ('chapter-85-1', '85', '1')")
        connection.execute(
            """
            INSERT INTO national_note_version VALUES
            ('section-85-1-v', 'section-85-1', 'Nota de Sección XVI.', NULL, NULL, 'fixture-source'),
            ('chapter-85-1-v', 'chapter-85-1', 'Nota del Capítulo 85.', NULL, NULL, 'fixture-source')
            """
        )
        connection.execute(
            """
            INSERT INTO national_note_applicability VALUES
            ('app-section-85-1', 'section-85-1-v', 'section', 'XVI', 'explicit', 'fixture-source'),
            ('app-chapter-85-1', 'chapter-85-1-v', 'chapter', '85', 'explicit', 'fixture-source')
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE VIEW arancel_mx_national_notes AS
            SELECT n.national_note_id, n.chapter,
                   a.scope_type, a.scope_value, a.applicability_basis,
                   n.note_number, v.national_note_version_id, v.text,
                   v.effective_from, v.effective_to, v.source_document_id
            FROM national_note n
            JOIN national_note_version v USING (national_note_id)
            JOIN national_note_applicability a USING (national_note_version_id)
            """
        )
    finally:
        connection.close()
```

- [ ] **Step 3: Add a failing precise-scope regression**

```python
def test_national_notes_preserves_distinct_section_and_chapter_scope(
    consumer_duckdb: Path,
) -> None:
    _materialize_scoped_notes(consumer_duckdb)
    connection = duckdb.connect(str(consumer_duckdb), read_only=True)
    try:
        notes = national_notes(connection, "85")
    finally:
        connection.close()

    assert {(note.scope_type, note.scope_value, note.text) for note in notes} == {
        ("section", "XVI", "Nota de Sección XVI."),
        ("chapter", "85", "Nota del Capítulo 85."),
    }
    assert {note.applicability_basis for note in notes} == {"explicit"}
```

- [ ] **Step 4: Run the two consumer regressions and verify RED**

```bash
python -m pytest -q \
  tests/consumer/test_national_notes_public.py::test_national_notes_returns_materialized_chapter_notes \
  tests/consumer/test_national_notes_public.py::test_national_notes_preserves_distinct_section_and_chapter_scope
```

Expected: FAIL because `NationalNote` and `national_notes()` do not expose scope metadata.

- [ ] **Step 5: Extend `NationalNote` compatibly**

Append fields after the original required fields:

```python
@dataclass(frozen=True, slots=True)
class NationalNote:
    chapter: str
    note_number: str
    text: str
    source_document_id: str
    scope_type: str | None = None
    scope_value: str | None = None
    applicability_basis: str = "unresolved"
```

- [ ] **Step 6: Feature-detect the view shape**

After confirming the view exists, add:

```python
columns = {
    str(row[0]).lower()
    for row in connection.execute("DESCRIBE arancel_mx_national_notes").fetchall()
}
scoped = {
    "scope_type",
    "scope_value",
    "applicability_basis",
}.issubset(columns)
```

For new views execute:

```sql
SELECT chapter, note_number, text, source_document_id,
       scope_type, scope_value, applicability_basis
FROM arancel_mx_national_notes
WHERE chapter = ?
ORDER BY note_number, scope_type, scope_value NULLS LAST,
         source_document_id, national_note_version_id
```

Map each row explicitly into all seven `NationalNote` fields.

For legacy views execute:

```sql
SELECT chapter, note_number, text, source_document_id
FROM arancel_mx_national_notes
WHERE chapter = ?
ORDER BY note_number, source_document_id, national_note_version_id
```

Construct the four required fields only so the model supplies `None`, `None`, and `"unresolved"`.

- [ ] **Step 7: Run Task 2 GREEN**

```bash
python -m pytest -q tests/consumer/test_national_notes_public.py tests/consumer/test_query.py
python -m mypy src/arancel_mx/consumer
python -m ruff check src/arancel_mx/consumer tests/consumer/test_national_notes_public.py
```

Expected: PASS.

- [ ] **Step 8: Commit Task 2**

```bash
git add src/arancel_mx/consumer/models.py src/arancel_mx/consumer/query.py tests/consumer/test_national_notes_public.py
git commit -m "fix: preserve national note scope in consumer"
```

---

### Task 3: Expose Scope Fields Through the Existing FastAPI v1 Contract

**Files:**
- Modify: `tests/api/test_models.py`
- Modify: `tests/api/test_notes_routes.py`
- Modify: `src/arancel_mx/api/models.py`

**Interfaces:**
- Consumes: Task 2 `NationalNote` fields.
- Produces: additive `scope_type`, `scope_value`, `applicability_basis` in `NationalNoteResponse` and nested suggest notes.

- [ ] **Step 1: Write failing wire-model assertions**

Change the note in `test_search_and_suggest_wire_models_keep_retrieval_metadata` to:

```python
note = NationalNote(
    chapter="01",
    note_number="1",
    text="Nota oficial.",
    source_document_id="dof-notes",
    scope_type="chapter",
    scope_value="01",
    applicability_basis="explicit",
)
```

Add:

```python
note_payload = NationalNoteResponse.from_note(note).model_dump(mode="json")
assert note_payload["scope_type"] == "chapter"
assert note_payload["scope_value"] == "01"
assert note_payload["applicability_basis"] == "explicit"
```

- [ ] **Step 2: Write failing route assertions**

Change `NotesDataset.national_notes()` to return:

```python
NationalNote(
    chapter="85",
    note_number="1",
    text="Texto oficial de la nota nacional.",
    source_document_id="dof-national-notes",
    scope_type="section",
    scope_value="XVI",
    applicability_basis="explicit",
)
```

Add these keys to the expected JSON:

```python
"scope_type": "section",
"scope_value": "XVI",
"applicability_basis": "explicit",
```

- [ ] **Step 3: Run the API note tests and verify RED**

```bash
python -m pytest -q tests/api/test_models.py tests/api/test_notes_routes.py
```

Expected: FAIL because `NationalNoteResponse` lacks the new fields.

- [ ] **Step 4: Extend `NationalNoteResponse`**

Use:

```python
class NationalNoteResponse(FrozenModel):
    """One materialized official National Note with preserved applicability."""

    chapter: str
    note_number: str
    text: str
    source_document_id: str
    scope_type: str | None
    scope_value: str | None
    applicability_basis: str

    @classmethod
    def from_note(cls, note: NationalNote) -> NationalNoteResponse:
        return cls(
            chapter=note.chapter,
            note_number=note.note_number,
            text=note.text,
            source_document_id=note.source_document_id,
            scope_type=note.scope_type,
            scope_value=note.scope_value,
            applicability_basis=note.applicability_basis,
        )
```

No notes/suggest route logic changes are required because both already serialize this model.

- [ ] **Step 5: Run Task 3 GREEN**

```bash
python -m pytest -q tests/api/test_models.py tests/api/test_notes_routes.py tests/api/test_search_routes.py
python -m mypy src/arancel_mx/api
python -m ruff check src/arancel_mx/api tests/api/test_models.py tests/api/test_notes_routes.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add src/arancel_mx/api/models.py tests/api/test_models.py tests/api/test_notes_routes.py
git commit -m "feat: expose national note applicability in API"
```

---

### Task 4: Make OpenAPI Match the Runtime Error and Readiness Contract

**Files:**
- Create: `src/arancel_mx/api/openapi.py`
- Modify: `src/arancel_mx/api/models.py`
- Modify: `src/arancel_mx/api/routes.py`
- Modify: `src/arancel_mx/api/app.py`
- Modify: `tests/api/test_openapi.py`
- Modify: `tests/api/test_service_routes.py`

**Interfaces:**
- Consumes: existing `ErrorEnvelope` exception handlers.
- Produces: reusable endpoint-specific response maps plus `HealthResponse`, `ReadyResponse`, `NotReadyResponse`.

- [ ] **Step 1: Write failing OpenAPI error-schema test**

Append to `tests/api/test_openapi.py`:

```python
def _json_schema(response_spec: dict) -> dict:
    return response_spec["content"]["application/json"]["schema"]


def test_openapi_documents_sanitized_error_envelope(
    valid_settings,
    fake_dataset,
) -> None:
    application = _app(valid_settings, fake_dataset)
    with TestClient(application) as client:
        payload = client.get("/openapi.json").json()

    assert "ErrorEnvelope" in payload["components"]["schemas"]
    lookup = payload["paths"]["/v1/lookup/{code}"]["get"]["responses"]
    for status in ("400", "404", "422", "503", "500"):
        assert _json_schema(lookup[status]) == {
            "$ref": "#/components/schemas/ErrorEnvelope"
        }
    search = payload["paths"]["/v1/search"]["get"]["responses"]
    for status in ("422", "503", "500"):
        assert _json_schema(search[status]) == {
            "$ref": "#/components/schemas/ErrorEnvelope"
        }
```

- [ ] **Step 2: Write failing typed health/readiness OpenAPI test**

Append:

```python
def test_openapi_types_health_and_readiness(valid_settings, fake_dataset) -> None:
    application = _app(valid_settings, fake_dataset)
    with TestClient(application) as client:
        payload = client.get("/openapi.json").json()

    health = payload["paths"]["/healthz"]["get"]["responses"]
    ready = payload["paths"]["/readyz"]["get"]["responses"]
    assert _json_schema(health["200"]) == {
        "$ref": "#/components/schemas/HealthResponse"
    }
    assert _json_schema(ready["200"]) == {
        "$ref": "#/components/schemas/ReadyResponse"
    }
    assert _json_schema(ready["503"]) == {
        "$ref": "#/components/schemas/NotReadyResponse"
    }
```

- [ ] **Step 3: Run OpenAPI tests and verify RED**

```bash
python -m pytest -q tests/api/test_openapi.py
```

Expected: FAIL because the schemas are not declared.

- [ ] **Step 4: Add typed service models**

Import `Literal` in `api/models.py` and add:

```python
class HealthResponse(FrozenModel):
    status: Literal["ok"]


class ReadyResponse(FrozenModel):
    status: Literal["ready"]
    dataset_version: str


class NotReadyResponse(FrozenModel):
    status: Literal["not_ready"]
```

- [ ] **Step 5: Create `api/openapi.py`**

```python
"""Reusable OpenAPI response contracts for the public v1 service."""

from __future__ import annotations

from typing import Final

from arancel_mx.api.models import ErrorEnvelope


def _error(description: str) -> dict[str, object]:
    return {"model": ErrorEnvelope, "description": description}


LOOKUP_ERROR_RESPONSES: Final[dict[int, dict[str, object]]] = {
    400: _error("Invalid tariff code."),
    404: _error("Tariff record not found."),
    422: _error("Request validation failed."),
    503: _error("Verified dataset unavailable or inconsistent."),
    500: _error("Internal server error."),
}

RETRIEVAL_ERROR_RESPONSES: Final[dict[int, dict[str, object]]] = {
    422: _error("Request validation failed."),
    503: _error("Verified dataset unavailable or inconsistent."),
    500: _error("Internal server error."),
}

NOTES_ERROR_RESPONSES: Final[dict[int, dict[str, object]]] = {
    422: _error("Request validation failed."),
    503: _error("Verified dataset unavailable or inconsistent."),
    500: _error("Internal server error."),
}

META_ERROR_RESPONSES: Final[dict[int, dict[str, object]]] = {
    503: _error("Verified dataset unavailable."),
    500: _error("Internal server error."),
}
```

- [ ] **Step 6: Attach exact response maps in `routes.py`**

Import the four constants and `HealthResponse`.

Use `responses=LOOKUP_ERROR_RESPONSES` on:

```text
/v1/lookup/{code}
/v1/ficha/{code}
/v1/codes/{code}/parent
/v1/codes/{code}/children
/v1/codes/{code}/provenance
```

Use `responses=RETRIEVAL_ERROR_RESPONSES` on `/v1/search` and `/v1/suggest`.

Use `responses=NOTES_ERROR_RESPONSES` on `/v1/chapters/{chapter}/national-notes`.

Use `responses=META_ERROR_RESPONSES` on `/v1/meta`.

Change health to:

```python
@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")
```

Do not alter path names, tags, query limits, or Dataset delegation.

- [ ] **Step 7: Type readiness explicitly in `app.py`**

Import `DatasetUnavailableError`, `ReadyResponse`, and `NotReadyResponse`.

Use:

```python
@application.get(
    "/readyz",
    response_model=ReadyResponse,
    responses={
        503: {
            "model": NotReadyResponse,
            "description": "Verified dataset is not ready.",
        }
    },
)
def readiness():
    dataset = application.state.dataset
    if not application.state.ready or dataset is None:
        return JSONResponse(
            NotReadyResponse(status="not_ready").model_dump(),
            status_code=503,
        )
    dataset_version = dataset.info.dataset_version
    if dataset_version is None:
        raise DatasetUnavailableError("verified dataset version is missing")
    return ReadyResponse(status="ready", dataset_version=dataset_version)
```

- [ ] **Step 8: Preserve runtime JSON in tests**

Add to `tests/api/test_service_routes.py`:

```python
def test_readyz_reports_verified_dataset_version(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dataset_version": "2026.08.15",
    }
```

Leave all existing request-ID and CORS tests unchanged.

- [ ] **Step 9: Run Task 4 GREEN**

```bash
python -m pytest -q tests/api
python -m mypy src/arancel_mx/api src/arancel_mx/consumer src/arancel_mx/__init__.py
python -m ruff check src/arancel_mx/api tests/api
```

Expected: PASS.

- [ ] **Step 10: Commit Task 4**

```bash
git add src/arancel_mx/api/openapi.py src/arancel_mx/api/models.py src/arancel_mx/api/routes.py src/arancel_mx/api/app.py tests/api/test_openapi.py tests/api/test_service_routes.py
git commit -m "fix: document public API error contract"
```

---

### Task 5: Prove Legacy `data-2026.08.15` Still Works on Python 3.13

**Files:**
- Modify: `tests/package/test_quality_tooling.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 2 legacy fallback and Task 3 API serialization.
- Produces: deterministic CI protection for the currently pinned production release.

- [ ] **Step 1: Write the exact failing CI workflow contract**

Add to `tests/package/test_quality_tooling.py`:

```python
def test_fastapi_cloud_runtime_smokes_legacy_national_notes() -> None:
    workflow = CI.read_text(encoding="utf-8")
    marker = "  fastapi-cloud-runtime:"
    assert marker in workflow
    runtime = workflow.split(marker, 1)[1]
    assert "/v1/chapters/85/national-notes" in runtime
    assert 'note["scope_type"] is None' in runtime
    assert 'note["scope_value"] is None' in runtime
    assert 'note["applicability_basis"] == "unresolved"' in runtime
```

- [ ] **Step 2: Run it and verify RED**

```bash
python -m pytest -q tests/package/test_quality_tooling.py::test_fastapi_cloud_runtime_smokes_legacy_national_notes
```

Expected: FAIL because the runtime smoke does not yet request legacy notes.

- [ ] **Step 3: Extend the existing Python 3.13 startup smoke**

In `.github/workflows/ci.yml`, append after the existing `/v1/meta` assertions:

```python
notes = client.get("/v1/chapters/85/national-notes")
assert notes.status_code == 200, notes.text
notes_payload = notes.json()
assert notes_payload, "expected chapter 85 national notes in data-2026.08.15"
assert all(note["scope_type"] is None for note in notes_payload)
assert all(note["scope_value"] is None for note in notes_payload)
assert all(
    note["applicability_basis"] == "unresolved" for note in notes_payload
)
```

The workflow remains pinned to `ARANCEL_MX_API_DATASET: data-2026.08.15` for this compatibility smoke.

- [ ] **Step 4: Update `CHANGELOG.md`**

Under `Unreleased` -> `Fixed`, add exactly:

```markdown
- Preserve National Note applicability (`section` vs `chapter`) from materialization through DuckDB, the consumer API, and FastAPI. Newer clients remain compatible with older immutable datasets by reporting legacy note scope as unresolved instead of inferring legal scope.
- OpenAPI now documents the sanitized `ErrorEnvelope` used by handled 400/404/422/500/503 responses and typed health/readiness schemas, including the legitimate 503 not-ready response.
```

Do not claim a new data release yet.

- [ ] **Step 5: Run Task 5 GREEN**

```bash
python -m pytest -q tests/package/test_quality_tooling.py tests/api
python -m ruff check src tests scripts
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add tests/package/test_quality_tooling.py .github/workflows/ci.yml CHANGELOG.md
git commit -m "test: protect legacy dataset API compatibility"
```

---

### Task 6: Full Verification, Review, and Squash Merge

**Files:**
- Review all changed files from Tasks 1-5.
- PR: `fix/api-v1-notes-openapi-contract` -> `main`.

**Interfaces:**
- Consumes: complete implementation branch.
- Produces: one focused, reviewed, green PR merged to `main`.

- [ ] **Step 1: Recheck repository topology**

```bash
git fetch origin
git rev-parse origin/main
git log --oneline -5 origin/main
git diff --stat origin/main...HEAD
```

On GitHub verify there is no other open PR touching these files. If `main` moved, inspect every new base commit before rebasing the branch.

- [ ] **Step 2: Run the complete test suite**

```bash
ARANCEL_MX_SKIP_URL_CHECKS=1 python -m pytest -q --cov=arancel_mx --cov-report=term-missing
```

Expected: PASS and coverage at or above the repository floor.

- [ ] **Step 3: Run static/security gates**

```bash
python -m ruff check src tests scripts
python -m ruff check --select S src scripts
python -m mypy src/arancel_mx/consumer src/arancel_mx/api src/arancel_mx/__init__.py
```

Expected: PASS.

- [ ] **Step 4: Run official URL checks**

```bash
python -m scripts.check_documented_urls --timeout 45
python -m scripts.validate_ligie_html_pages --timeout 45
```

Expected: PASS. Diagnose upstream availability separately; do not weaken deterministic validation.

- [ ] **Step 5: Build and certify distributions**

```bash
rm -rf dist build
python -m build
python scripts/certify_package_install.py dist/*.whl
python scripts/certify_package_install.py dist/*.tar.gz
```

Expected: PASS.

- [ ] **Step 6: Open one draft PR and require CI**

Open exactly one PR titled:

```text
fix: preserve national note API applicability
```

Require both CI jobs green on the same head SHA:

```text
test
fastapi-cloud-runtime
```

Also require configured CodeQL/security checks green.

- [ ] **Step 7: Review the complete diff and feedback**

Accept only fixes related to this plan. Defer search ranking, `suggest` optimization, GZip, caching, rate limiting, auth, provenance redesign, and unrelated refactors.

- [ ] **Step 8: Squash-merge the exact reviewed head**

Use squash title:

```text
fix: preserve national note API applicability
```

Do not merge if the branch head changed after final verification.

- [ ] **Step 9: Verify post-merge production on the old tag**

After FastAPI Cloud deploys merged `main` while still pinned to `data-2026.08.15`, externally require:

```text
GET /healthz -> 200
GET /readyz -> 200
GET /v1/meta -> 200 and dataset_tag=data-2026.08.15
GET /v1/chapters/85/national-notes -> 200
```

Every note returned from the old release must include:

```json
{
  "scope_type": null,
  "scope_value": null,
  "applicability_basis": "unresolved"
}
```

Do not repoint FastAPI Cloud yet.

---

### Task 7: Publish and Adopt the Next Immutable Data Release

**Files:**
- No source changes unless verification exposes a real defect.
- Workflow: `.github/workflows/official-data-pipeline.yml`.

**Interfaces:**
- Consumes: merged applicability-aware code on `main`.
- Produces: one new immutable `data-*` release and an explicit FastAPI Cloud dataset-pin update.

- [ ] **Step 1: Dispatch the production workflow**

Using GitHub CLI:

```bash
gh workflow run official-data-pipeline.yml --ref main -f publish=true
```

Then identify the run:

```bash
gh run list --workflow official-data-pipeline.yml --branch main --limit 5
```

Wait for the dispatched run to finish successfully.

- [ ] **Step 2: Resolve the new immutable release tag**

```bash
TAG="$(gh release list --limit 20 --json tagName,publishedAt --jq '[.[] | select(.tagName | startswith("data-"))] | sort_by(.publishedAt) | last | .tagName')"
printf '%s\n' "$TAG"
test -n "$TAG"
test "$TAG" != "data-2026.08.15"
```

Expected: a new immutable `data-*` tag produced from the successful workflow.

- [ ] **Step 3: Verify the six release assets and metadata**

```bash
gh release view "$TAG" --json tagName,targetCommitish,isImmutable,assets
rm -rf /tmp/arancel-mx-release-check
mkdir -p /tmp/arancel-mx-release-check
gh release download "$TAG" --dir /tmp/arancel-mx-release-check
cd /tmp/arancel-mx-release-check
sha256sum -c SHA256SUMS
```

Require exactly these six public assets:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

Require `isImmutable=true` and a target commit on the verified `main` lineage.

- [ ] **Step 4: Verify applicability in the new DuckDB**

Run:

```bash
python - <<'PY'
import duckdb

path = "/tmp/arancel-mx-release-check/arancel_mx.duckdb"
with duckdb.connect(path, read_only=True) as conn:
    rows = conn.execute(
        """
        SELECT chapter, scope_type, scope_value, applicability_basis,
               note_number, text, source_document_id
        FROM arancel_mx_national_notes
        WHERE chapter = '85' AND note_number = '1'
        ORDER BY scope_type, scope_value
        """
    ).fetchall()

assert any(row[1:4] == ("section", "XVI", "explicit") for row in rows), rows
assert any(row[1:4] == ("chapter", "85", "explicit") for row in rows), rows
PY
```

Do not accept a release where the distinction exists only in HTTP code.

- [ ] **Step 5: Verify the release with the package CLI**

From the repository checkout:

```bash
python -m arancel_mx data verify --bundle /tmp/arancel-mx-release-check
```

Expected: PASS.

- [ ] **Step 6: Repoint FastAPI Cloud explicitly**

Set the FastAPI Cloud environment variable:

```text
ARANCEL_MX_API_DATASET=<value of TAG from Step 2>
```

Use **Save and Redeploy**. Do not use `latest`.

- [ ] **Step 7: Run final production smoke**

Require:

```text
/healthz -> 200
/readyz -> 200
/v1/meta -> new dataset_tag, release_verified=true, structural_valid=true
/v1/chapters/85/national-notes -> section XVI and chapter 85 Note 1 scopes both explicit
/v1/suggest?q=telefono%20inteligente&limit=1 -> precise National Note scope fields
/openapi.json -> ErrorEnvelope on documented handled errors and typed ready/not-ready schemas
```

Re-run invalid code, missing record, 422 search bound, empty query, POST->405, CORS preflight, and spoofed `X-Request-ID`.

- [ ] **Step 8: Record release adoption without conflating package and data versions**

Update only the existing documentation fields that track the latest data release, preserving the separate Python package lifecycle. Do not start the deferred performance work in this task.
