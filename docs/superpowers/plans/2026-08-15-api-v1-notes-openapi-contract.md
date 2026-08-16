# API v1 National Notes Scope and OpenAPI Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve National Note applicability semantics end-to-end and make OpenAPI describe the public FastAPI v1 runtime contract accurately without breaking existing `/v1` clients or immutable legacy data releases.

**Architecture:** Persist parser-provided applicability into the already-existing `national_note_applicability` table, expose it through the public notes view, and make the consumer feature-detect old versus new note views. Legacy immutable snapshots remain serviceable with unresolved scope metadata instead of inferred legal scope. The HTTP layer maps the additive consumer fields directly and uses reusable FastAPI `responses` mappings plus typed health/readiness models.

**Tech Stack:** Python 3.11+ library runtime, Python 3.13 FastAPI Cloud runtime, DuckDB, FastAPI, Pydantic, pytest, Ruff, mypy, GitHub Actions.

## Global Constraints

- Keep the public HTTP namespace at `/v1`; all response changes are additive.
- Do not remove, rename, or reinterpret existing National Note response fields.
- New National Note fields are `scope_type: str | None`, `scope_value: str | None`, and `applicability_basis: str`.
- New-format official releases persist `scope_type`/`scope_value` and use `applicability_basis="explicit"` for the supported parser path.
- Legacy immutable snapshots without applicability columns return `scope_type=None`, `scope_value=None`, `applicability_basis="unresolved"`; never infer section/chapter scope from text.
- Keep `data-2026.08.15` immutable and usable by newer package/API code.
- Do not change search ranking, suggest ranking, response compression, caching, rate limiting, authentication, provenance semantics, tariff rates, or NICO behavior in this PR.
- Keep the API GET-only and read-only.
- Add no new runtime dependency.
- Preserve current primary National Note ordering by `note_number`; use scope/source identifiers only as tie-breakers.
- Use one focused PR from `fix/api-v1-notes-openapi-contract` to `main`.
- Before merge, recheck `main`, open PR topology, the complete diff, review findings, and all mandatory CI checks.

---

## File Structure

**Modify** `src/arancel_mx/pipeline/build.py`
- Persist one applicability row per newly materialized National Note version.
- Include applicability fields in `arancel_mx_national_notes`.
- Validate exactly one applicability row per new public note version.

**Modify** `src/arancel_mx/consumer/models.py`
- Add optional scope fields and unresolved compatibility basis to `NationalNote` without breaking existing constructor call sites.

**Modify** `src/arancel_mx/consumer/query.py`
- Feature-detect old/new National Notes view shapes.
- Return precise scope metadata for new releases and unresolved metadata for legacy releases.

**Modify** `src/arancel_mx/api/models.py`
- Add scope fields to `NationalNoteResponse`.
- Add `HealthResponse`, `ReadyResponse`, and `NotReadyResponse`.

**Create** `src/arancel_mx/api/openapi.py`
- Hold reusable additional-response mappings using `ErrorEnvelope`.

**Modify** `src/arancel_mx/api/routes.py`
- Attach typed health response and endpoint-specific additional error responses.

**Modify** `src/arancel_mx/api/app.py`
- Type `/readyz` and document its 503 degraded response.

**Modify** `tests/pipeline/test_build.py`
- Cover applicability persistence, deterministic IDs, public view fields, and validation cardinality.

**Modify** `tests/consumer/test_national_notes_public.py`
- Cover new-format precise scope and legacy unresolved fallback.

**Modify** `tests/api/test_models.py`
- Cover additive wire fields and suggest propagation.

**Modify** `tests/api/test_notes_routes.py`
- Cover chapter-note serialization with scope fields.

**Modify** `tests/api/test_openapi.py`
- Cover `ErrorEnvelope`, custom 422 schemas, and typed health/readiness schemas.

**Modify** `tests/api/test_service_routes.py`
- Preserve exact runtime JSON for health/readiness behavior.

**Modify** `.github/workflows/ci.yml`
- Extend the Python 3.13 FastAPI Cloud startup smoke against `data-2026.08.15` to prove the legacy release remains ready and returns unresolved scope fields.

**Modify** `CHANGELOG.md`
- Record the additive National Notes applicability contract and accurate OpenAPI error/readiness documentation under `Unreleased`.

---

### Task 1: Persist and Validate National Note Applicability

**Files:**
- Modify: `tests/pipeline/test_build.py`
- Modify: `src/arancel_mx/pipeline/build.py`

**Interfaces:**
- Consumes: parser/materialization rows containing `chapter`, `note_number`, `text`, `source_document_id`, optionally `scope_type`, `scope_value`, `applicability_basis`.
- Produces: one deterministic `national_note_applicability` row per `national_note_version_id`; a new-format `arancel_mx_national_notes` view exposing scope metadata; validation check `national_note_applicability_cardinality`.

- [ ] **Step 1: Write a failing persistence regression**

Extend `test_build_materializes_national_notes_into_the_public_view` so its input note is explicitly scoped and the query checks both the applicability table and public view:

```python
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

Use an HS2 classification for chapter `85` in this test so the fixture is internally consistent.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python -m pytest -q tests/pipeline/test_build.py::test_build_materializes_national_notes_into_the_public_view
```

Expected: FAIL because `_insert_national_notes` does not insert `national_note_applicability` and the public view lacks `scope_type`, `scope_value`, and `applicability_basis`.

- [ ] **Step 3: Implement deterministic applicability persistence**

In `_insert_national_notes`, after `version_id` is known and the version row is inserted, compute and insert the applicability row:

```python
scope_type = str(row.get("scope_type") or "chapter")
scope_value_obj = row.get("scope_value", row.get("chapter"))
scope_value = None if scope_value_obj is None else str(scope_value_obj)
applicability_basis = str(row.get("applicability_basis") or "explicit")
applicability_id = str(
    row.get("applicability_id")
    or hashlib.sha256(
        canonical_json(
            [
                version_id,
                scope_type,
                scope_value,
                applicability_basis,
                source_id,
            ]
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

Do not infer section scope anywhere in this function. The only default is the documented compatibility default for newly materialized rows that already carry a chapter.

- [ ] **Step 4: Expose applicability in the public view**

Replace the National Notes view body in `_build_view` with a direct join through the applicability table:

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

- [ ] **Step 5: Add a failing validation-cardinality regression**

Import `_validate_database` in `tests/pipeline/test_build.py` and add:

```python
def test_validation_rejects_missing_national_note_applicability(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    # Reuse the same valid source/classification/release shape as the notes test.
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
        with pytest.raises(ValueError, match="national_note_applicability_cardinality"):
            _validate_database(connection)
```

Build the `source`, `classification`, and `release` dictionaries explicitly in the test using the existing `release_metadata()` helper; do not introduce a new fixture abstraction solely for this test.

- [ ] **Step 6: Run the new validation test and verify RED**

Run:

```bash
python -m pytest -q tests/pipeline/test_build.py::test_validation_rejects_missing_national_note_applicability
```

Expected: FAIL because `_validate_database` does not yet check applicability cardinality.

- [ ] **Step 7: Add the validation check**

Inside `_validate_database`, add:

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

Because `_validate_database` already converts nonzero checks into a `ValueError`, no new error mechanism is needed.

- [ ] **Step 8: Add deterministic-ID regression**

In the notes materialization test, capture `applicability_id`, rematerialize the identical inputs, capture it again, and assert equality:

```python
first_id = connection.execute(
    "SELECT applicability_id FROM national_note_applicability"
).fetchone()[0]
materialize_arancel(
    connection, [source], [classification], [], release, national_notes=notes
)
second_id = connection.execute(
    "SELECT applicability_id FROM national_note_applicability"
).fetchone()[0]
assert first_id == second_id
```

- [ ] **Step 9: Run the pipeline slice GREEN**

Run:

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

### Task 2: Preserve Scope in the Consumer with Legacy Snapshot Fallback

**Files:**
- Modify: `tests/consumer/test_national_notes_public.py`
- Modify: `src/arancel_mx/consumer/models.py`
- Modify: `src/arancel_mx/consumer/query.py`

**Interfaces:**
- Consumes: old `arancel_mx_national_notes` views with 8 columns or new views containing `scope_type`, `scope_value`, `applicability_basis`.
- Produces: `NationalNote(chapter, note_number, text, source_document_id, scope_type=None, scope_value=None, applicability_basis="unresolved")` for old snapshots and precise fields for new snapshots.

- [ ] **Step 1: Turn the existing helper into an explicit legacy fixture**

Rename `_materialize_note` to `_materialize_legacy_note` without changing its old view definition. Update its current call sites accordingly.

Change the expected object in `test_national_notes_returns_materialized_chapter_notes` to:

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

- [ ] **Step 2: Add a new-format scoped fixture and regression**

Add this helper to `tests/consumer/test_national_notes_public.py`:

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

Add:

```python
def test_national_notes_preserves_distinct_section_and_chapter_scope(consumer_duckdb: Path):
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

- [ ] **Step 3: Run both consumer regressions and verify RED**

Run:

```bash
python -m pytest -q \
  tests/consumer/test_national_notes_public.py::test_national_notes_returns_materialized_chapter_notes \
  tests/consumer/test_national_notes_public.py::test_national_notes_preserves_distinct_section_and_chapter_scope
```

Expected: FAIL because `NationalNote` and `national_notes()` do not yet expose scope metadata.

- [ ] **Step 4: Extend `NationalNote` without breaking existing construction**

Append defaulted fields after the existing required fields in `src/arancel_mx/consumer/models.py`:

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

Appending defaults preserves existing keyword and positional construction for the original four fields.

- [ ] **Step 5: Feature-detect the public notes view**

In `national_notes()`, after confirming the view exists, inspect its columns:

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

For `scoped=True`, query:

```sql
SELECT chapter, note_number, text, source_document_id,
       scope_type, scope_value, applicability_basis
FROM arancel_mx_national_notes
WHERE chapter = ?
ORDER BY note_number, scope_type, scope_value NULLS LAST,
         source_document_id, national_note_version_id
```

Map directly:

```python
NationalNote(
    chapter=str(row[0]),
    note_number=str(row[1]),
    text=str(row[2]),
    source_document_id=str(row[3]),
    scope_type=None if row[4] is None else str(row[4]),
    scope_value=None if row[5] is None else str(row[5]),
    applicability_basis=str(row[6]),
)
```

For legacy views, keep the existing four-column query but add stable source/version tie-breakers:

```sql
SELECT chapter, note_number, text, source_document_id
FROM arancel_mx_national_notes
WHERE chapter = ?
ORDER BY note_number, source_document_id, national_note_version_id
```

Map legacy rows with the model defaults. Do not inspect note text to infer scope.

- [ ] **Step 6: Run the complete consumer notes slice GREEN**

Run:

```bash
python -m pytest -q tests/consumer/test_national_notes_public.py tests/consumer/test_query.py
python -m mypy src/arancel_mx/consumer
python -m ruff check src/arancel_mx/consumer tests/consumer/test_national_notes_public.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

```bash
git add src/arancel_mx/consumer/models.py src/arancel_mx/consumer/query.py tests/consumer/test_national_notes_public.py
git commit -m "fix: preserve national note scope in consumer"
```

---

### Task 3: Expose Additive Scope Fields Through FastAPI

**Files:**
- Modify: `tests/api/test_models.py`
- Modify: `tests/api/test_notes_routes.py`
- Modify: `src/arancel_mx/api/models.py`

**Interfaces:**
- Consumes: `NationalNote.scope_type`, `scope_value`, `applicability_basis` from Task 2.
- Produces: additive JSON fields in `NationalNoteResponse` and all nested suggest National Notes.

- [ ] **Step 1: Add failing wire-model assertions**

In `test_search_and_suggest_wire_models_keep_retrieval_metadata`, construct the note as:

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

- [ ] **Step 2: Add failing route serialization assertions**

In `NotesDataset.national_notes`, construct:

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

Update the expected response object in `test_national_notes_return_only_requested_two_digit_chapter` with:

```python
"scope_type": "section",
"scope_value": "XVI",
"applicability_basis": "explicit",
```

- [ ] **Step 3: Run the API note/model tests and verify RED**

Run:

```bash
python -m pytest -q tests/api/test_models.py tests/api/test_notes_routes.py
```

Expected: FAIL because `NationalNoteResponse` does not contain the additive fields.

- [ ] **Step 4: Extend `NationalNoteResponse` and mapping**

In `src/arancel_mx/api/models.py`:

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

No route logic change is required for notes/suggest because both already serialize through `NationalNoteResponse.from_note`.

- [ ] **Step 5: Run the API scope slice GREEN**

Run:

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

### Task 4: Make OpenAPI Match the Sanitized Runtime Contract

**Files:**
- Create: `src/arancel_mx/api/openapi.py`
- Modify: `src/arancel_mx/api/models.py`
- Modify: `src/arancel_mx/api/routes.py`
- Modify: `src/arancel_mx/api/app.py`
- Modify: `tests/api/test_openapi.py`
- Modify: `tests/api/test_service_routes.py`

**Interfaces:**
- Consumes: existing `ErrorEnvelope` runtime shape and exception handlers.
- Produces: reusable `LOOKUP_ERROR_RESPONSES`, `RETRIEVAL_ERROR_RESPONSES`, `NOTES_ERROR_RESPONSES`, `META_ERROR_RESPONSES`; typed `HealthResponse`, `ReadyResponse`, `NotReadyResponse`.

- [ ] **Step 1: Add failing OpenAPI error-schema regression**

Append to `tests/api/test_openapi.py`:

```python
def _json_schema(response_spec: dict) -> dict:
    return response_spec["content"]["application/json"]["schema"]


def test_openapi_documents_sanitized_error_envelope(valid_settings, fake_dataset) -> None:
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

- [ ] **Step 2: Add failing health/readiness schema regression**

Also append:

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

Run:

```bash
python -m pytest -q tests/api/test_openapi.py
```

Expected: FAIL because additional runtime error responses and typed health/readiness schemas are not declared.

- [ ] **Step 4: Add typed service response models**

In `src/arancel_mx/api/models.py`, import `Literal` and add:

```python
class HealthResponse(FrozenModel):
    status: Literal["ok"]


class ReadyResponse(FrozenModel):
    status: Literal["ready"]
    dataset_version: str


class NotReadyResponse(FrozenModel):
    status: Literal["not_ready"]
```

- [ ] **Step 5: Create reusable OpenAPI response mappings**

Create `src/arancel_mx/api/openapi.py`:

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

Do not create a catch-all map that advertises irrelevant statuses on every endpoint.

- [ ] **Step 6: Attach mappings to route decorators**

In `routes.py`, import the new constants and models. Update decorators:

```python
@router.get(
    "/healthz",
    response_model=HealthResponse,
)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")
```

Use `responses=LOOKUP_ERROR_RESPONSES` on lookup/ficha/parent/children/provenance; `responses=RETRIEVAL_ERROR_RESPONSES` on search/suggest; `responses=NOTES_ERROR_RESPONSES` on National Notes; `responses=META_ERROR_RESPONSES` on metadata.

Do not change route paths, request limits, tags, or data delegation.

- [ ] **Step 7: Type readiness without changing its JSON**

In `app.py`, import `ReadyResponse` and `NotReadyResponse`. Replace the decorator and return values with:

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
    return ReadyResponse(
        status="ready",
        dataset_version=dataset.info.dataset_version,
    )
```

If mypy flags `dataset.info.dataset_version` as optional, fail closed explicitly before constructing `ReadyResponse` rather than coercing `None` to a string:

```python
if dataset.info.dataset_version is None:
    raise DatasetUnavailableError("verified dataset version is missing")
```

Use the existing sanitized `DatasetError` handling path.

- [ ] **Step 8: Preserve exact runtime response regressions**

In `tests/api/test_service_routes.py`, keep the existing `healthz` assertion unchanged and add a readiness test:

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

Do not change the existing production-proven request-ID or CORS tests.

- [ ] **Step 9: Run the full API slice GREEN**

Run:

```bash
python -m pytest -q tests/api
python -m mypy src/arancel_mx/api src/arancel_mx/consumer src/arancel_mx/__init__.py
python -m ruff check src/arancel_mx/api tests/api
```

Expected: PASS.

- [ ] **Step 10: Commit Task 4**

```bash
git add \
  src/arancel_mx/api/openapi.py \
  src/arancel_mx/api/models.py \
  src/arancel_mx/api/routes.py \
  src/arancel_mx/api/app.py \
  tests/api/test_openapi.py \
  tests/api/test_service_routes.py
git commit -m "fix: document public API error contract"
```

---

### Task 5: Protect Legacy `data-2026.08.15` in FastAPI Cloud CI

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 2 legacy fallback and Task 3 additive API fields.
- Produces: Python 3.13 CI evidence that the currently pinned production dataset remains ready after the code upgrade.

- [ ] **Step 1: Add a failing workflow contract test if the repository already asserts startup-smoke text**

First run:

```bash
python -m pytest -q tests/package/test_quality_tooling.py tests/test_dependency_policy.py
```

If these tests already validate the exact `fastapi-cloud-runtime` smoke block, extend the existing assertion rather than adding a duplicate test file. Require the workflow text to contain `/v1/chapters/85/national-notes` and `applicability_basis`.

If no existing assertion covers smoke contents, add this exact regression to `tests/package/test_quality_tooling.py`:

```python
def test_fastapi_cloud_runtime_smokes_legacy_national_notes() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    runtime = workflow.split("fastapi-cloud-runtime:", 1)[1]
    assert "/v1/chapters/85/national-notes" in runtime
    assert 'applicability_basis' in runtime
    assert 'unresolved' in runtime
```

- [ ] **Step 2: Run the focused workflow-contract test and verify RED**

Run the exact test added or extended in Step 1.

Expected: FAIL because CI does not yet smoke the legacy notes compatibility path.

- [ ] **Step 3: Extend the existing Python 3.13 startup smoke**

In `.github/workflows/ci.yml`, after the existing `/v1/meta` assertions in `Smoke-test default FastAPI startup`, add:

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

This test intentionally runs against immutable `data-2026.08.15` and proves that a package code deployment does not require an immediate data-tag switch.

- [ ] **Step 4: Update the changelog**

Under `## [Unreleased]` -> `### Fixed`, add two bullets:

```markdown
- Preserve National Note applicability (`section` vs `chapter`) from materialization through DuckDB, the consumer API, and FastAPI. Newer clients remain compatible with older immutable datasets by reporting legacy note scope as unresolved instead of inferring legal scope.
- OpenAPI now documents the sanitized `ErrorEnvelope` used by handled 400/404/422/500/503 responses and typed health/readiness schemas, including the legitimate 503 not-ready response.
```

Do not claim that a new data release exists yet.

- [ ] **Step 5: Run workflow/docs slice GREEN**

Run:

```bash
python -m pytest -q tests/package/test_quality_tooling.py tests/api
python -m ruff check src tests scripts
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add .github/workflows/ci.yml CHANGELOG.md tests/package/test_quality_tooling.py
git commit -m "test: protect legacy dataset API compatibility"
```

If `tests/package/test_quality_tooling.py` required no change in Step 1, omit it from `git add`.

---

### Task 6: Full Repository Verification and Focused PR

**Files:**
- Review only: all changed files from Tasks 1-5
- PR target: `main`

**Interfaces:**
- Consumes: complete branch implementation.
- Produces: one reviewable PR with all repository gates green and no unrelated performance work.

- [ ] **Step 1: Recheck repository topology before final verification**

Confirm:

```bash
git fetch origin
git rev-parse origin/main
git log --oneline --decorate -5 origin/main
git diff --stat origin/main...HEAD
```

On GitHub, confirm there is no unrelated open PR that changes the same files. If `main` moved, inspect the new commits before rebasing/merging the base; do not force-update over unknown work.

- [ ] **Step 2: Run the complete required test suite**

Run:

```bash
ARANCEL_MX_SKIP_URL_CHECKS=1 python -m pytest -q --cov=arancel_mx --cov-report=term-missing
```

Expected: all tests pass and repository coverage remains at or above the configured floor.

- [ ] **Step 3: Run static and security gates**

Run:

```bash
python -m ruff check src tests scripts
python -m ruff check --select S src scripts
python -m mypy src/arancel_mx/consumer src/arancel_mx/api src/arancel_mx/__init__.py
```

Expected: PASS.

- [ ] **Step 4: Run official-source URL gates**

Run:

```bash
python -m scripts.check_documented_urls --timeout 45
python -m scripts.validate_ligie_html_pages --timeout 45
```

Expected: PASS. Do not weaken URL validation to make an upstream outage look green; if an upstream availability issue occurs, diagnose it separately from deterministic code failures.

- [ ] **Step 5: Build and certify distributions**

Run:

```bash
rm -rf dist build
python -m build
python scripts/certify_package_install.py dist/*.whl
python scripts/certify_package_install.py dist/*.tar.gz
```

Expected: PASS, including import of the FastAPI entrypoint from installed artifacts.

- [ ] **Step 6: Verify DuckDB compatibility and clean tree via the normal CI workflow**

Open one draft PR from `fix/api-v1-notes-openapi-contract` to `main` if it is not already open. Wait for both required CI jobs:

- `test`
- `fastapi-cloud-runtime`

Also require configured CodeQL/security checks green. The `test` job must pass the existing DuckDB 1.1.0 compatibility probe, wheel/sdist smoke, official URL checks, and clean-tree gate from `.github/workflows/ci.yml`.

- [ ] **Step 7: Inspect the complete PR diff and review feedback**

Check every changed filename and the full patch. Verify that the PR contains only:

- applicability persistence/view/validation;
- consumer old/new snapshot compatibility;
- additive API note fields;
- OpenAPI error/readiness contracts;
- CI legacy-release smoke;
- changelog/docs generated by this plan.

Reject or defer suggestions involving search ranking, GZip, caching, rate limiting, authentication, unrelated refactors, or provenance redesign.

- [ ] **Step 8: Final exact-head verification and squash merge**

Record the reviewed PR head SHA, confirm all mandatory checks are green on that SHA, then squash-merge that exact head into `main`.

Use a squash title equivalent to:

```text
fix: preserve national note API applicability
```

- [ ] **Step 9: Verify post-merge `main`**

Confirm the merged `main` SHA receives green push CI and a successful FastAPI Cloud deployment while still pinned to `data-2026.08.15`.

Externally verify:

```text
GET /healthz -> 200
GET /readyz -> 200
GET /v1/meta -> dataset_tag data-2026.08.15
GET /v1/chapters/85/national-notes -> 200
```

For the old release, every returned note must contain:

```json
{
  "scope_type": null,
  "scope_value": null,
  "applicability_basis": "unresolved"
}
```

Do not repoint production yet.

---

### Task 7: Publish and Adopt the Next Immutable Data Release

**Files:**
- No source mutation unless release verification exposes a defect.
- Use the repository's existing Official data pipeline and release artifacts.

**Interfaces:**
- Consumes: merged applicability-aware materialization code on `main`.
- Produces: a new immutable `data-*` release with precise National Note applicability and a deliberate FastAPI Cloud dataset-pin update.

- [ ] **Step 1: Run the existing Official data pipeline from verified `main`**

Use the repository's existing production workflow with publication enabled. Do not create an ad-hoc release command and do not reuse `data-2026.08.15`.

- [ ] **Step 2: Verify all expected immutable release assets**

Require the normal six-asset bundle:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

Verify `SHA256SUMS`, manifest validation status, source identity, release target SHA, and immutable release state using the repository's existing certification commands/workflows.

- [ ] **Step 3: Verify applicability inside the new DuckDB**

Against the downloaded new `arancel_mx.duckdb`, run:

```sql
SELECT chapter, scope_type, scope_value, applicability_basis,
       note_number, text, source_document_id
FROM arancel_mx_national_notes
WHERE chapter = '85' AND note_number = '1'
ORDER BY scope_type, scope_value;
```

Expected: at least two semantically distinct Note 1 rows including:

```text
scope_type=section, scope_value=XVI, applicability_basis=explicit
scope_type=chapter, scope_value=85, applicability_basis=explicit
```

Do not accept a release where the distinction is missing or reconstructed only in the HTTP layer.

- [ ] **Step 4: Repoint FastAPI Cloud only after release verification**

Change:

```text
ARANCEL_MX_API_DATASET=<new immutable data-* tag>
```

Save and redeploy. Do not use `latest`.

- [ ] **Step 5: Run final production smoke**

Verify externally:

```text
/healthz -> 200
/readyz -> 200
/v1/meta -> new dataset_tag, release_verified=true, structural_valid=true
/v1/chapters/85/national-notes -> precise section/chapter scopes
/v1/suggest?q=telefono%20inteligente&limit=1 -> precise note scopes
/openapi.json -> ErrorEnvelope for documented handled errors and typed ready/not-ready schemas
```

Re-run the existing negative/security battery for invalid code, missing record, limit validation, empty query, disallowed POST, CORS preflight, and spoofed `X-Request-ID`.

- [ ] **Step 6: Record release adoption evidence**

Update only the repository documentation that tracks the current data release if the existing release workflow does not do so automatically. Keep package version and data release lifecycle explicitly independent.

Do not start the deferred search/suggest performance work in this task.
