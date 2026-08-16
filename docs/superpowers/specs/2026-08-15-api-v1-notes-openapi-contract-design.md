# API v1 National Notes Scope and OpenAPI Contract Design

**Date:** 2026-08-15
**Repository:** `jccontrerasg08-cpu/arancel-mx`
**Branch:** `fix/api-v1-notes-openapi-contract`
**Status:** Approved design

## Context

The public FastAPI v1 service is live on FastAPI Cloud and has been exercised against the immutable `data-2026.08.15` release from an external Windows client. Production verification covered liveness, readiness, metadata, exact MX8 and NICO10 lookup, ficha, hierarchy, provenance, search, suggest, chapters, National Notes, OpenAPI, docs, invalid input, missing records, missing routes, disallowed methods, validation bounds, CORS preflight, and server-owned request IDs.

The runtime contract is healthy, but two additive contract gaps were discovered:

1. The National Notes pipeline parser already identifies `scope_type` and `scope_value`, and the DuckDB schema already contains `national_note_applicability`, but the build path does not persist the applicability row and the public `arancel_mx_national_notes` view does not expose it. As a result, two legally distinct notes can be returned with the same `chapter` and `note_number` while their original section-versus-chapter scope is lost.
2. Runtime errors are sanitized into the versioned `ErrorEnvelope`, but OpenAPI currently documents mainly the success responses and FastAPI's default validation schema. It does not accurately describe the actual 400/404/405/422/500/503 error contract or readiness 503 behavior observed in production.

This design corrects those gaps without introducing a `/v2` API and without changing the meaning or names of existing v1 fields.

## Objectives

1. Preserve authoritative National Note applicability semantics from parser through DuckDB, consumer models, and FastAPI wire responses.
2. Keep `/v1` backward-compatible by adding fields only.
3. Make OpenAPI accurately describe the existing runtime error envelope and readiness semantics.
4. Preserve immutable release discipline by generating a new `data-*` release instead of mutating `data-2026.08.15`.
5. Keep this follow-up narrowly scoped to legal-note semantics and API contract accuracy.

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
- mutate the immutable `data-2026.08.15` release.

## Compatibility policy

The change remains under `/v1` because the HTTP contract is strictly additive.

Existing fields remain present and keep their current meaning. Existing endpoint paths and status behavior remain unchanged. Clients that ignore unknown JSON fields continue to work without changes.

The following fields are added to `NationalNote` and `NationalNoteResponse`:

- `scope_type: str`
- `scope_value: str | None`
- `applicability_basis: str`

For official National Notes materialized by the current parser, `scope_type` is expected to be `chapter` or `section`, and `applicability_basis` is expected to be `explicit` for the supported official source path. The storage schema remains the source of truth for allowed applicability values.

## National Notes data model

### Existing storage

The repository already defines:

- `national_note`
- `national_note_version`
- `national_note_applicability`

The parser already emits scope metadata for official National Notes. The missing operation is persistence of the applicability row.

### Required build behavior

For every materialized National Note version, `_insert_national_notes` must insert exactly one corresponding `national_note_applicability` row for the parser-provided materialized applicability.

The applicability row must contain:

- a deterministic `applicability_id`;
- `national_note_version_id`;
- `scope_type`;
- `scope_value`;
- `applicability_basis`;
- `source_document_id`.

The deterministic identifier must be derived from stable semantic fields and must not depend on local paths, insertion order, timestamps generated at runtime, or nondeterministic values.

For parser rows that do not explicitly provide applicability fields, compatibility defaults must preserve the historical chapter-materialized behavior:

- `scope_type = "chapter"`
- `scope_value = chapter`
- `applicability_basis = "explicit"`

This default is only a persistence compatibility rule for already materialized chapter rows. It must not infer section scope from note text, note number, or source title.

### Public view

`arancel_mx_national_notes` must expose enough columns to reconstruct the public consumer model without inference:

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

The view must join `national_note_applicability` to `national_note_version` by `national_note_version_id`.

A materialized version with zero or multiple applicability rows is a structural inconsistency for this current public contract and must be detected by validation or by a deterministic query failure rather than silently collapsed.

### Example

A section-level Note 1 from Section XVI materialized onto chapter 85 must be represented as:

```json
{
  "chapter": "85",
  "scope_type": "section",
  "scope_value": "XVI",
  "applicability_basis": "explicit",
  "note_number": "1"
}
```

A chapter-specific Note 1 for chapter 85 must be represented as:

```json
{
  "chapter": "85",
  "scope_type": "chapter",
  "scope_value": "85",
  "applicability_basis": "explicit",
  "note_number": "1"
}
```

Those rows may share the same `chapter` and `note_number`, but they are not semantically duplicate notes.

## Consumer contract

`arancel_mx.consumer.models.NationalNote` becomes an additive immutable model with:

- existing `chapter`;
- new `scope_type`;
- new `scope_value`;
- new `applicability_basis`;
- existing `note_number`;
- existing `text`;
- existing `source_document_id`.

`consumer.query.national_notes(connection, chapter)` must select the applicability fields directly from `arancel_mx_national_notes`.

Ordering must remain deterministic. The preferred ordering is:

1. numeric-aware `note_number` ordering where already supported by current data representation;
2. stable `scope_type` and `scope_value` tie-breakers;
3. stable source/version identifiers as final tie-breakers if needed.

The query must not infer scope from note text.

`Dataset.national_notes(chapter)` remains the public facade and keeps the same call signature.

## FastAPI wire contract

`NationalNoteResponse` adds the same three applicability fields. `from_note` performs a direct lossless mapping from the consumer model.

The following existing endpoints remain unchanged in path and basic purpose:

- `GET /v1/chapters/{chapter}/national-notes`
- `GET /v1/suggest`

Both will expose the new fields anywhere a National Note is serialized.

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

OpenAPI must describe that actual runtime contract with `ErrorEnvelope` rather than advertising FastAPI's default `HTTPValidationError` for endpoints whose validation errors are intercepted by the application handler.

### Shared response definitions

The API module should define small reusable response-description mappings rather than duplicating large dictionaries in every decorator.

The mappings must remain explicit enough that each endpoint only advertises status codes that it can meaningfully return under the public contract.

Examples:

- lookup/ficha/parent/children/provenance: 400 invalid code, 404 missing record, 422 request validation where applicable, 503 verified dataset unavailable/inconsistent, 500 unexpected internal failure;
- search/suggest: 422 parameter validation, 503 dataset/query failure, 500 unexpected internal failure;
- National Notes: 422 path validation, 503 dataset/query failure, 500 unexpected internal failure;
- generic missing-route and method-not-allowed behavior remains globally handled even though those statuses are not duplicated onto every unrelated operation definition.

Descriptions must be concise and must not expose implementation details.

### Readiness model

Add an explicit typed readiness response model rather than leaving `/readyz` with an empty OpenAPI schema.

The success shape is:

```json
{
  "status": "ready",
  "dataset_version": "2026.08.15"
}
```

The degraded shape is:

```json
{
  "status": "not_ready"
}
```

A single model may represent this with `status` plus optional `dataset_version`, or two response models may be used if that produces a clearer OpenAPI contract. The chosen implementation must preserve the existing runtime JSON exactly.

`/readyz` must document both 200 and 503.

`/healthz` should also use a small typed response model for its existing `{ "status": "ok" }` body.

## Validation and integrity

The pipeline must add deterministic validation for applicability consistency. At minimum, the built database must fail validation when a materialized public National Note version does not have exactly one applicability row for this contract.

Existing canonical tariff validation remains unchanged.

The new validation must not treat equal `chapter + note_number` as a duplicate by itself because section-level and chapter-level notes can legitimately share both fields.

The release builder must continue exporting only validated releases.

## Immutable release migration

`data-2026.08.15` remains immutable and is not modified.

After the code fix merges to `main` and the official-data pipeline succeeds, publish a new immutable `data-YYYY.MM.DD` release using the normal repository release workflow.

The new release must be verified before FastAPI Cloud is repointed. Verification includes:

- expected release assets;
- SHA256SUMS consistency;
- manifest identity and validation status;
- DuckDB structural validation;
- National Notes applicability rows;
- chapter 85 regression proving one section-scoped Note 1 and one chapter-scoped Note 1 are distinguishable;
- package/data version independence remains explicit.

Only after release verification should `ARANCEL_MX_API_DATASET` be changed from `data-2026.08.15` to the new immutable tag and FastAPI Cloud redeployed.

## Production verification

After redeploy, verify externally:

- `/healthz` is 200;
- `/readyz` is 200 and reports the new dataset version;
- `/v1/meta` reports the new `dataset_tag`, verified release, and structural validity;
- `/v1/chapters/85/national-notes` contains both distinct Note 1 scopes;
- `/v1/suggest?q=telefono%20inteligente&limit=1` includes scope metadata for attached notes;
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
- exactly one applicability row exists per materialized National Note version under this contract;
- the public view exposes scope fields;
- database validation rejects missing or duplicate applicability rows.

### Consumer tests

Add regressions proving:

- `NationalNote` exposes the new fields;
- chapter 85 returns the section-level and chapter-level Note 1 as distinct objects;
- no scope inference occurs from text;
- ordering is deterministic.

### API tests

Add regressions proving:

- `NationalNoteResponse` exposes scope fields;
- chapter National Notes and suggest serialize them;
- OpenAPI uses `ErrorEnvelope` for the documented handled status codes;
- OpenAPI no longer advertises the default `HTTPValidationError` as the effective 422 body for the custom-handled operations;
- `/healthz` and `/readyz` have typed schemas;
- `/readyz` documents 503;
- runtime JSON for existing success and error cases remains unchanged except for the additive National Note fields.

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

These are valuable but are deliberately excluded from this PR to keep the legal-semantics correction auditable and low-risk.
