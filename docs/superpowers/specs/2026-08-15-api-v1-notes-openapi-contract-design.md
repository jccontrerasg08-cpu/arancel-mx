# API v1 National Notes Scope and OpenAPI Contract Design

**Date:** 2026-08-15
**Repository:** `jccontrerasg08-cpu/arancel-mx`
**Branch:** `fix/api-v1-notes-openapi-contract`
**Status:** Approved and self-reviewed design

## Context

The public FastAPI v1 service is live on FastAPI Cloud and has been exercised against the immutable `data-2026.08.15` release from an external Windows client. Production verification covered liveness, readiness, metadata, exact MX8 and NICO10 lookup, ficha, hierarchy, provenance, search, suggest, chapters, National Notes, OpenAPI, docs, invalid input, missing records, missing routes, disallowed methods, validation bounds, CORS preflight, and server-owned request IDs.

The runtime contract is healthy, but two additive contract gaps were discovered:

1. The National Notes parser already identifies `scope_type` and `scope_value`, the DuckDB schema already contains `national_note_applicability`, and `PUBLIC_INTERNAL_TABLES` already includes that table for distributable releases. The missing operation is persistence of applicability rows plus exposure through the public view/consumer/API. As a result, two legally distinct notes can currently be returned with the same `chapter` and `note_number` while their original section-versus-chapter scope is lost.
2. Runtime errors are sanitized into the versioned `ErrorEnvelope`, but OpenAPI currently documents mainly success responses and FastAPI's default validation schema. It does not accurately describe the actual 400/404/422/500/503 error contract or readiness 503 behavior observed in production.

This design corrects those gaps without introducing `/v2` and without changing the meaning or names of existing v1 fields.

## Objectives

1. Preserve authoritative National Note applicability semantics from parser through DuckDB, consumer models, and FastAPI wire responses.
2. Keep `/v1` backward-compatible by adding fields only.
3. Preserve compatibility with already-published immutable snapshots, including `data-2026.08.15`.
4. Make OpenAPI accurately describe the existing runtime error envelope and readiness semantics.
5. Preserve immutable release discipline by generating a new `data-*` release instead of mutating `data-2026.08.15`.
6. Keep this follow-up narrowly scoped to legal-note semantics and API contract accuracy.

## Non-goals

This change will not:

- change search ranking or scoring;
- optimize or redesign `suggest`;
- add response compression, caching, distributed rate limiting, authentication, or API keys;
- change the GET-only public API boundary;
- expose write, scrape, reconciliation, publication, or maintainer endpoints;
- add live WCO or VUCEM calls to request handling;
- redesign the provenance source-authority model;
- alter tariff rates, code hierarchy, NICO semantics, or existing lookup behavior;
- mutate any existing immutable data release.

## Compatibility policy

The change remains under `/v1` because the HTTP contract is additive.

Existing fields remain present and keep their current meaning. Existing endpoint paths and runtime status behavior remain unchanged. Clients that ignore unknown JSON fields continue to work.

The following fields are added to `NationalNote` and `NationalNoteResponse`:

- `scope_type: str | None`
- `scope_value: str | None`
- `applicability_basis: str`

For newly built official releases, `scope_type` is expected to be `chapter` or `section`, and `applicability_basis` is expected to be `explicit` for the supported official source path.

For legacy immutable snapshots whose `arancel_mx_national_notes` view predates applicability columns, the consumer must not infer original legal scope. It must return:

- `scope_type = None`
- `scope_value = None`
- `applicability_basis = "unresolved"`

This compatibility behavior lets newer package/API code continue serving an older verified snapshot while remaining honest about information that the old artifact did not preserve.

## National Notes data model

### Existing storage

The repository already defines:

- `national_note`
- `national_note_version`
- `national_note_applicability`

`PUBLIC_INTERNAL_TABLES` already includes `national_note_applicability`, so the release database copy path does not need a new table allowlist entry.

The parser already emits scope metadata for official National Notes. The missing operation is persistence of that applicability metadata.

### Required build behavior

For every newly materialized National Note version, `_insert_national_notes` must insert exactly one corresponding `national_note_applicability` row for the parser-provided materialized applicability.

The applicability row contains:

- deterministic `applicability_id`;
- `national_note_version_id`;
- `scope_type`;
- `scope_value`;
- `applicability_basis`;
- `source_document_id`.

The identifier must be derived only from stable semantic fields and must not depend on local paths, insertion order, runtime-generated timestamps, or random values.

For input rows that predate explicit applicability fields but are being materialized by current code, compatibility defaults are:

- `scope_type = "chapter"`
- `scope_value = chapter`
- `applicability_basis = "explicit"`

This default applies only while building a new database from an already chapter-materialized input row. It must never be used to reinterpret an already-published legacy DuckDB snapshot and must never infer section scope from note text, note number, or source title.

### Public view

Newly built `arancel_mx_national_notes` views expose:

- `national_note_id`
- `chapter`
- `scope_type`
- `scope_value`
- `applicability_basis`
- `note_number`
- `national_note_version_id`
- `text`
- `effective_from`
- `effective_to`
- `source_document_id`

The view joins `national_note_applicability` to `national_note_version` by `national_note_version_id`.

For newly built datasets, every public National Note version must have exactly one applicability row under the current materialized contract. Zero or multiple applicability rows are structural validation failures and block publication.

Equal `chapter + note_number` values are not duplicates by themselves because section-level and chapter-level notes can legitimately share both fields.

### Example

A section-level Note 1 from Section XVI materialized onto chapter 85 is represented as:

```json
{
  "chapter": "85",
  "scope_type": "section",
  "scope_value": "XVI",
  "applicability_basis": "explicit",
  "note_number": "1"
}
```

A chapter-specific Note 1 for chapter 85 is represented as:

```json
{
  "chapter": "85",
  "scope_type": "chapter",
  "scope_value": "85",
  "applicability_basis": "explicit",
  "note_number": "1"
}
```

Those rows are semantically distinct even though they share `chapter` and `note_number`.

## Consumer contract

`arancel_mx.consumer.models.NationalNote` becomes an additive immutable model with:

- existing `chapter`;
- new optional `scope_type`;
- new optional `scope_value`;
- new `applicability_basis`;
- existing `note_number`;
- existing `text`;
- existing `source_document_id`.

`consumer.query.national_notes(connection, chapter)` performs schema-feature detection on `arancel_mx_national_notes`:

- if the applicability columns exist, select and return them directly;
- if they do not exist, use the legacy unresolved values defined above;
- never infer scope from text or note numbering.

The call signature of `Dataset.national_notes(chapter)` remains unchanged.

Ordering preserves the current externally observable primary order by `note_number` to avoid a behavioral change in this PR. New scope/source identifiers are used only as deterministic tie-breakers for equal `note_number` rows. Numeric reordering of note numbers is explicitly deferred because it could change client-visible ordering.

## FastAPI wire contract

`NationalNoteResponse` adds the same three applicability fields and maps them losslessly from the consumer model.

The existing endpoints remain unchanged in path and purpose:

- `GET /v1/chapters/{chapter}/national-notes`
- `GET /v1/suggest`

Both expose the additive applicability fields wherever a National Note is serialized.

No existing response field is removed or renamed.

## OpenAPI error contract

The service already returns one sanitized shape for handled failures:

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "request_id": "..."
  }
}
```

OpenAPI must describe the actual runtime contract with `ErrorEnvelope` rather than advertising FastAPI's default `HTTPValidationError` for operations whose validation errors are intercepted by the application handler.

Use FastAPI's supported `responses={status_code: {"model": Model, ...}}` mechanism. Shared mappings should keep definitions consistent without making endpoint status documentation overly broad.

Endpoint response documentation is explicit:

- lookup/ficha/parent/children/provenance: 400 `ErrorEnvelope`, 404 `ErrorEnvelope`, 422 `ErrorEnvelope` where parameter validation is possible, 503 `ErrorEnvelope`, 500 `ErrorEnvelope`;
- search/suggest: 422 `ErrorEnvelope`, 503 `ErrorEnvelope`, 500 `ErrorEnvelope`;
- National Notes: 422 `ErrorEnvelope`, 503 `ErrorEnvelope`, 500 `ErrorEnvelope`;
- metadata: 503 `ErrorEnvelope`, 500 `ErrorEnvelope`;
- root/health may document only their meaningful service-level responses;
- global missing-route 404 and method-not-allowed 405 remain handled by the global exception handler and are not duplicated onto every unrelated operation.

Tests must verify that the effective OpenAPI 422 content schema for these operations references `ErrorEnvelope`, not `HTTPValidationError`.

## Health and readiness models

Use explicit models, with no implementation-choice ambiguity:

- `HealthResponse`: `status: Literal["ok"]`;
- `ReadyResponse`: `status: Literal["ready"]`, `dataset_version: str`;
- `NotReadyResponse`: `status: Literal["not_ready"]`.

`GET /healthz` keeps its existing runtime JSON and uses `HealthResponse` as the 200 response model.

`GET /readyz` keeps its existing runtime JSON, uses `ReadyResponse` for 200, and documents 503 with `NotReadyResponse`.

The runtime response bodies must remain exactly compatible with what has already been verified in production.

## Validation and integrity

Add deterministic pipeline validation for new builds. Publication fails if any materialized public National Note version has zero or more than one applicability row.

Existing tariff validation remains unchanged.

The release builder continues exporting only validated releases.

Legacy published snapshots are not retroactively required to satisfy this new applicability validation. Compatibility is handled in the consumer as unresolved metadata.

## Immutable release migration

`data-2026.08.15` remains immutable and usable by newer package code.

After the code fix merges to `main` and the official-data pipeline succeeds, publish the next new immutable `data-*` tag produced by the normal workflow. Never reuse or replace `data-2026.08.15`.

Before repointing FastAPI Cloud, verify:

- expected release assets;
- SHA256SUMS consistency;
- manifest identity and validation status;
- DuckDB structural validation;
- populated National Notes applicability rows;
- chapter 85 regression proving one section-scoped Note 1 and one chapter-scoped Note 1 are distinguishable;
- package/data version independence remains explicit.

Only after that verification should `ARANCEL_MX_API_DATASET` be changed to the new immutable tag and FastAPI Cloud redeployed.

The merge of package code must not require an immediate data-environment switch: while FastAPI Cloud remains pinned to `data-2026.08.15`, the legacy fallback keeps the service ready and reports applicability as unresolved.

## Production verification

After code deployment while still pinned to the old release:

- `/healthz` remains 200;
- `/readyz` remains 200;
- `/v1/meta` still reports the old verified tag until deliberately repointed;
- National Notes serialize additive unresolved scope fields instead of failing startup or fabricating scope.

After the new data release is verified and the environment variable is repointed:

- `/healthz` is 200;
- `/readyz` is 200 and reports the new dataset version;
- `/v1/meta` reports the new `dataset_tag`, verified release, and structural validity;
- `/v1/chapters/85/national-notes` contains both distinct Note 1 scopes;
- `/v1/suggest?q=telefono%20inteligente&limit=1` includes precise scope metadata for attached notes;
- `/openapi.json` references `ErrorEnvelope` for documented handled errors;
- `/openapi.json` documents typed 200/503 readiness responses;
- invalid code, missing record, 422 bounds, GET-only behavior, CORS, and server-owned request IDs still match the already verified production contract.

## Testing strategy

Implementation uses RED -> GREEN TDD.

### Pipeline/storage tests

Add regressions proving:

- section-level parser rows persist `scope_type=section` and the correct Roman section value;
- chapter-level rows persist `scope_type=chapter` and the two-digit chapter value;
- applicability identifiers are deterministic;
- exactly one applicability row exists per materialized National Note version for new builds;
- the new public view exposes scope fields;
- database validation rejects missing or duplicate applicability rows;
- the public release database preserves `national_note_applicability`.

### Consumer tests

Add regressions proving:

- `NationalNote` exposes the new fields;
- a new-format fixture returns the section-level and chapter-level Note 1 as distinct objects;
- a legacy-format fixture without scope columns still loads and returns `scope_type=None`, `scope_value=None`, `applicability_basis="unresolved"`;
- no scope inference occurs from text;
- existing primary ordering by `note_number` is preserved and ties are deterministic.

### API tests

Add regressions proving:

- `NationalNoteResponse` exposes scope fields;
- chapter National Notes and suggest serialize them;
- legacy dataset fixtures remain serviceable;
- OpenAPI uses `ErrorEnvelope` for documented handled status codes;
- OpenAPI no longer advertises `HTTPValidationError` as the effective custom-handled 422 body on covered operations;
- `/healthz` and `/readyz` have typed schemas;
- `/readyz` documents both `ReadyResponse` and 503 `NotReadyResponse`;
- runtime JSON for existing success/error cases remains unchanged except for additive National Note fields.

### Repository gates

Before merge, require the same project gates used for the FastAPI v1 feature:

- complete pytest suite;
- repository coverage floor;
- Ruff;
- Ruff security rules;
- mypy including `src/arancel_mx/api`;
- official URL checks;
- package build;
- DuckDB compatibility probe;
- installed wheel/sdist smoke certification;
- Python 3.13 FastAPI Cloud runtime smoke;
- clean-tree/distribution contracts;
- CodeQL/check runs where configured.

## Pull request and merge policy

Use one focused PR from `fix/api-v1-notes-openapi-contract` to `main`.

The PR must not include search/suggest performance work, GZip, caching, rate limiting, or unrelated refactors.

Before merge:

1. recheck that `main` has not moved unexpectedly;
2. recheck open PR topology;
3. inspect the complete diff;
4. resolve actionable review findings with tests;
5. require all mandatory CI checks green;
6. squash-merge only the exact reviewed head SHA.

## Follow-up work intentionally deferred

After this semantic/API-contract fix is complete, create a separate performance and operations design for:

- bounded and more efficient search/suggest ranking;
- reducing duplicated National Note payload in suggest;
- optional HTTP compression after measurement;
- production API canary after deployments;
- performance budgets and regression measurements;
- future provenance distinction between structured operational source and legal authority.

These remain deliberately excluded from this PR so the legal-semantics correction stays auditable and low-risk.
