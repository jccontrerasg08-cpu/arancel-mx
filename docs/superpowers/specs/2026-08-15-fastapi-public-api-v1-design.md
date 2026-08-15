# Public FastAPI v1 Design

Date: 2026-08-15
Status: approved design
Target repository: `jccontrerasg08-cpu/arancel-mx`
Target deployment: FastAPI Cloud

## 1. Objective

Expose the verified `arancel-mx` consumer surface through a small public, read-only HTTP API without moving source capture, legal reconciliation, release publication, or dataset mutation into the web service.

The API is a transport adapter over the existing `Dataset` facade. It must not duplicate tariff interpretation logic or create a second source of truth.

Success means:

- a public client can query current HS2/HS4/HS6/MX8/NICO10 records without installing Python;
- responses are backed by one explicitly selected immutable `data-YYYY.MM.DD` release;
- the service never reports readiness or serves tariff data until the selected dataset is structurally verified;
- DuckDB is opened read-only;
- API failures never weaken the existing official-data publication gates;
- normal repository CI remains the pre-merge gate before FastAPI Cloud deploys the default branch.

## 2. Repository and platform facts verified before design

Current repository facts:

- `main` is `0f5c0f5f9aba0591cf229d1552c6b4f825323e92` when this design was written.
- There were no open pull requests before creating `feat/fastapi-public-api-v1`.
- The project uses a `src/` package layout and root `pyproject.toml`.
- `Dataset` already exposes read-only `lookup`, `search`, `suggest`, `parent`, `children`, `provenance`, `ficha`, `chapters`, and `compare` operations.
- `Dataset.connect()` opens DuckDB with `read_only=True`.
- engineering specs under `docs/superpowers` are intentionally pruned from the sdist by `MANIFEST.in`.

FastAPI/FastAPI Cloud facts verified from current official documentation:

- FastAPI Cloud supports GitHub deployments from the default branch and currently has no GitHub PR preview deployments.
- A root `pyproject.toml` and `src/` application layout are supported.
- an explicit `[tool.fastapi] entrypoint = "arancel_mx.api.app:app"` is the supported way to locate an app in an installable `src/` package.
- FastAPI Cloud documents `fastapi[standard]` as the dependency to include for an existing `pyproject.toml` application.
- FastAPI lifespan is the supported mechanism for one-time startup resource loading.
- FastAPI `TestClient` with pytest is the documented testing path.

Primary references:

- https://fastapicloud.com/docs/source-control/github-integration/
- https://fastapicloud.com/docs/builds-and-deployments/configuring-fastapi/
- https://fastapicloud.com/docs/builds-and-deployments/install-dependencies/
- https://fastapicloud.com/docs/getting-started/existing-project/
- https://fastapi.tiangolo.com/advanced/events/
- https://fastapi.tiangolo.com/tutorial/testing/
- https://fastapi.tiangolo.com/tutorial/handling-errors/
- https://fastapi.tiangolo.com/tutorial/cors/

## 3. Scope

### In scope

Public GET-only API endpoints for:

- service metadata and health;
- exact tariff-code lookup;
- hierarchy card (`ficha`);
- deterministic search;
- retrieve-only `suggest`;
- direct parent and children;
- provenance;
- chapters;
- chapter National Notes.

The API version is `/v1`. Package version, API version, and dataset version remain independent identifiers.

### Explicitly out of scope for v1

- authentication or API keys;
- user accounts;
- POST/PUT/PATCH/DELETE mutation endpoints;
- source scraping;
- legal reconciliation;
- release creation or publication;
- dataset update endpoints;
- live VUCEM `compare` requests;
- WCO PDF downloads;
- LLM/classifier functionality;
- bulk exports;
- asynchronous job queues;
- custom distributed rate-limit infrastructure;
- automatically publishing a new PyPI package merely because the FastAPI Cloud app is deployed.

`compare` remains outside v1 because it can perform a live external VUCEM request. The first HTTP contract must be deterministic over the verified selected dataset.

## 4. Architecture

```text
Internet
   |
   v
FastAPI Cloud
   |
   | GET only
   v
arancel_mx.api
   |
   v
arancel_mx.consumer.Dataset
   |
   | verified immutable dataset
   v
DuckDB opened read-only
```

### Components

`src/arancel_mx/api/app.py`
: application factory/lifespan, middleware, router registration, exception handlers, OpenAPI metadata.

`src/arancel_mx/api/config.py`
: environment-backed API settings with explicit dataset tag and bounded public limits.

`src/arancel_mx/api/dependencies.py`
: access to the lifespan-loaded `Dataset` instance. Request handlers do not construct or download a dataset per request.

`src/arancel_mx/api/models.py`
: explicit Pydantic response/error contracts. HTTP schema is versioned independently from consumer dataclasses.

`src/arancel_mx/api/routes.py`
: thin path operations that call the `Dataset` facade. No tariff logic belongs here.

Consumer extension:
: add one public `Dataset.national_notes(chapter)` method so the web adapter never imports the private `_national_notes()` query helper directly.

## 5. Dependency decision

The repository currently keeps its base Python distribution small. The preferred library shape would normally be an optional `api` extra. However, FastAPI Cloud's current official existing-project guidance says that when a project already has a `pyproject.toml`, `fastapi[standard]` should be present in project dependencies, and the platform documentation does not currently document selecting a package extra during GitHub-connected builds.

For v1, follow the documented platform contract instead of relying on undocumented extra-install behavior:

- add a bounded `fastapi[standard]` requirement to the project runtime dependencies;
- add `[tool.fastapi] entrypoint = "arancel_mx.api.app:app"`;
- do not introduce a second package/workspace solely to isolate this dependency;
- keep the existing CLI/library import path independent from API application initialization;
- reassess an isolated deployment package only if dependency weight becomes a demonstrated problem.

This is a conscious trade-off: slightly larger base installation in exchange for a standard, documented deployment path and no duplicate package metadata.

The in-tree package is already `0.2.1`. This feature can remain part of that unreleased package version unless the repository's package-release review decides otherwise. FastAPI Cloud deployment and PyPI publication remain separate release events.

## 6. Dataset lifecycle

Production requires:

`ARANCEL_MX_API_DATASET=data-2026.08.15`

The value must match `data-YYYY.MM.DD`. There is no silent `latest` fallback in the web service.

Lifespan startup:

1. parse and validate settings;
2. initialize application state as not ready;
3. call `Dataset.version(tag, offline=False, ...)` once;
4. reuse the existing download/cache/integrity machinery;
5. ensure verification succeeds;
6. retain the immutable `Dataset` object in application state;
7. mark readiness true only after all prior steps succeed.

Expected dataset bootstrap failures are recorded in sanitized application state instead of fabricating an empty dataset. This allows `/healthz` to report process health and `/readyz` to return 503 with a stable error while tariff endpoints also return 503. Unexpected programming errors are not silently swallowed.

Request handling opens short-lived read-only DuckDB connections through the existing `Dataset` methods. No writable connection is created.

A failed dataset download, integrity check, schema validation, or open operation must never be converted into a successful empty API response.

## 7. HTTP contract

### Service endpoints

`GET /`
: small service descriptor with links to `/docs`, `/openapi.json`, and `/v1/meta`.

`GET /healthz`
: process health only. Returns 200 when the application process is alive, even if the dataset is not ready.

`GET /readyz`
: returns 200 only when a verified dataset is loaded; otherwise 503.

`GET /v1/meta`
: returns `api_version`, package version, selected dataset version, schema version, and read-only status. Returns 503 while the selected dataset is unavailable.

### Data endpoints

`GET /v1/lookup/{code}`
: exact current record.

`GET /v1/ficha/{code}`
: hierarchy card based on existing `Dataset.ficha()` semantics.

`GET /v1/search?q=...&limit=20`
: existing deterministic search contract. `limit` range 1..50. Query length 1..300.

`GET /v1/suggest?q=...&limit=5`
: existing retrieve-only contract. `limit` range 1..20. Query length 1..300. The response must preserve the existing disclaimer that this is not a classification.

`GET /v1/codes/{code}/parent`
: direct parent or JSON `null` for HS2.

`GET /v1/codes/{code}/children`
: direct current children only.

`GET /v1/codes/{code}/provenance`
: recorded source provenance, primary first, using existing query semantics.

`GET /v1/chapters`
: current HS2 chapter records.

`GET /v1/chapters/{chapter}/national-notes`
: National Notes materialized for the requested two-digit chapter.

No route in v1 accepts a request body.

## 8. Response design

Responses expose official source values without reinterpretation. Examples:

- preserve `igi_text` / `ige_text` such as `Ex.` and `Prohibida`;
- codes remain strings so leading zeroes are never lost;
- dates serialize as ISO 8601 strings or `null`;
- `nico2` remains a two-character string, including `00`;
- every tariff response carries `dataset_version` and `is_current` from the verified data model.

The HTTP layer may group existing fields for ergonomics, but it must not change their meaning.

## 9. Error contract

All handled API errors use one shape:

```json
{
  "error": {
    "code": "record_not_found",
    "message": "Tariff record not found.",
    "request_id": "..."
  }
}
```

Mapping:

- malformed tariff code or invalid query: 400;
- record not found: 404;
- FastAPI/Pydantic parameter validation: 422, normalized into the same top-level error shape;
- selected dataset unavailable or failed verification: 503;
- internal consumer inconsistency such as multiple current rows: 503;
- unexpected exception: 500 with no traceback, filesystem path, SQL, or internal exception text in the response.

A fresh server-generated request ID is assigned to each request and returned in `X-Request-ID`. v1 does not trust an arbitrary incoming request ID for log identity.

## 10. CORS and public-access boundary

The service is intentionally public and credential-free.

CORS policy:

- `allow_origins=["*"]`;
- `allow_credentials=False`;
- allow only `GET` cross-origin application methods; preflight `OPTIONS` is handled by CORS middleware;
- expose `X-Request-ID`;
- no authorization cookies or headers are part of v1.

This follows the public-read-only model and avoids the invalid wildcard-plus-credentials configuration warned about in FastAPI's CORS documentation.

Application-level abuse bounds are provided by query-length and result-count caps and by the absence of bulk endpoints. A custom distributed rate limiter is deferred until real traffic justifies one.

## 11. OpenAPI and documentation

Keep FastAPI's `/docs`, `/redoc`, and `/openapi.json` public.

OpenAPI metadata must state:

- data is informational and does not constitute legal advice;
- `search` and `suggest` do not classify merchandise;
- DOF/legal source precedence remains governed by the dataset pipeline, not the API;
- WCO/VUCEM are not elevated to Mexican legal authority by this service.

## 12. Tests and verification gates

Implementation follows TDD. For each behavior slice, add a failing test before production code.

Required focused tests:

- settings reject missing/invalid dataset tags;
- lifespan attempts exactly one dataset bootstrap and readiness reflects success/failure;
- dataset-bootstrap failure leaves health available, readiness/data unavailable, and does not fabricate data;
- root/meta/health/readiness contracts;
- exact HS/MX8/NICO10 lookup including leading-zero codes and `nico2="00"`;
- official tariff text is not rewritten;
- not-found and invalid-code mappings;
- search/suggest bounds and deterministic result contract;
- suggest disclaimer remains present;
- parent/children hierarchy;
- provenance ordering;
- National Notes by chapter;
- CORS does not enable credentials;
- request IDs are server-generated and returned consistently;
- unexpected exceptions do not leak internal details;
- API has no POST/PUT/PATCH/DELETE application routes;
- OpenAPI exposes only intended service/v1 operations;
- importing the normal CLI/library does not initialize the FastAPI application or download a dataset;
- FastAPI entrypoint imports from a built wheel, not only an editable checkout.

Repository gates before merge:

- `python -m pytest -q`;
- coverage remains at or above the existing 87% floor;
- `python -m ruff check src tests scripts`;
- `python -m ruff check --select S src scripts`;
- mypy includes the API package in addition to the existing consumer surface;
- `python -m build`;
- wheel/sdist content checks;
- installed-wheel smoke test;
- `fastapi dev` can discover the configured entrypoint without a path argument.

## 13. GitHub and FastAPI Cloud delivery flow

FastAPI Cloud is already connected to `jccontrerasg08-cpu/arancel-mx` with the repository root as the application directory.

Delivery sequence:

1. work only on `feat/fastapi-public-api-v1` or a successor feature branch;
2. before each material implementation batch, re-check open PRs and current `main` to avoid overlap;
3. push tests and implementation in reviewable commits;
4. open one focused PR to `main`;
5. require the existing repository CI plus API-specific gates to pass;
6. review the complete diff and any bot/human review findings;
7. merge only after fresh green evidence;
8. FastAPI Cloud deploys the new default-branch commit;
9. verify deployment logs/status in FastAPI Cloud;
10. run production smoke requests against `/healthz`, `/readyz`, `/v1/meta`, known HS/MX8/NICO10 lookups, search, provenance, and National Notes;
11. if production smoke fails, do not mutate data in place; fix through a new PR or roll back the application deployment.

FastAPI Cloud's GitHub integration currently deploys pushes to the default branch and does not provide PR preview deployments, so GitHub CI is the mandatory pre-deploy quality boundary.

## 14. Production smoke dataset

Initial deterministic smoke cases should include:

- `8517130100` to protect NICO `00` formatting;
- at least one leading-zero chapter/fraction/NICO path;
- one fraction with multiple NICO children;
- one exempt tariff;
- one prohibited/special tariff representation;
- one code with multiple provenance records;
- one chapter with materialized National Notes;
- one invalid code and one valid-format missing code.

Expected values should come from the pinned `data-2026.08.15` test fixture or a deliberately generated verified fixture, not duplicated ad hoc across tests.

## 15. Security and failure-mode rules

- no secrets are required for public API requests;
- no maintainer command or source-write function is imported into route modules;
- no user-supplied SQL identifiers or SQL fragments;
- query values remain parameterized through the existing consumer layer;
- no live upstream fetch occurs during a normal data request;
- dataset verification errors fail closed;
- request error payloads are sanitized;
- production logs may include server-generated request IDs and exception classes but must not log secrets or downloaded source contents;
- no CORS credentials;
- no debug mode in production;
- API startup must not publish or alter GitHub releases.

## 16. Deferred decisions

The following require evidence from real usage before expansion:

- distributed rate limiting;
- response caching headers beyond safe immutable metadata responses;
- dedicated API hostname/custom domain;
- a separate API package or uv workspace to remove FastAPI from base dependencies;
- bulk endpoints;
- authentication tiers;
- metrics/observability vendor integration;
- API v2 classification or RAG features.

## 17. Acceptance criteria

The feature is complete only when:

1. every listed v1 route is backed by the existing verified `Dataset` facade;
2. production selects an explicit immutable dataset tag;
3. dataset verification and read-only DuckDB behavior are enforced before any tariff response is served;
4. no write/maintainer endpoint exists;
5. tests demonstrate NICO string/leading-zero preservation;
6. all repository verification gates pass on the PR head;
7. the PR is merged after a final open-PR/main re-check;
8. FastAPI Cloud reports a successful deployment of the merged SHA;
9. production smoke tests pass against the deployed URL;
10. the README/docs state the public API contract, dataset pin, and non-legal-advice/retrieve-only boundaries accurately.
