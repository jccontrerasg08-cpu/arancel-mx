# Changelog

All notable changes to the Python package are documented here. Dataset releases have an independent `data-YYYY.MM.DD` lifecycle in GitHub Releases and are not duplicated as package versions.

## [Unreleased]

### Security

- `/v1/search` and `/v1/suggest` on Vercel reject `q` longer than 300 characters (the same bound as the FastAPI app) before loading the active release, and normalize each description once per row instead of once per query token.
- Release asset downloads must come from `https://github.com`, because the session sends the user's GitHub token. Downloads stop as soon as they exceed the asset's declared size.
- The Vercel cron secret is compared with `hmac.compare_digest`.
- Data-alert issues show diagnostic text in a code block, so text from an official host cannot add mentions, links or images.
- The Vercel build installs `psycopg` and `psycopg-binary` from `requirements/vercel.txt` with `--require-hashes`.
- Jobs that hold write tokens (`publish`, `notify`, and the production-certification boundary jobs) no longer restore the pip cache, which a read-only job that parses untrusted documents could have seeded. A workflow test enforces it.

### Added

- Static, read-only data API generated from each verified release (`arancel-mx static-api build|verify`, `arancel_mx.static_api`). It has one file per HS2 chapter, a search index and a SHA-256 manifest, and uses the same response models as `/v1`. It is published to GitHub Pages and served by Vercel at `/data/v1` through a rewrite, and by the FastAPI app at `/data/v1`. See decision 0002.
- Daily DOF watch through the official SIDOF web services (`arancel_mx.sources.sidof`, `scripts/watch_dof.py`). It opens one `dof-candidate` issue per new tariff-relevant DOF note for human review.

- Public FastAPI HTTP service with an explicit `/v1` contract over the existing verified `Dataset` facade. The service is GET-only, read-only, requires no API key, and exposes lookup, ficha, hierarchy, provenance, search, suggest, chapters, National Notes, health/readiness, OpenAPI, and metadata endpoints.
- FastAPI Cloud deployment metadata via `[tool.fastapi]` and an import-safe `arancel_mx.api.app:app` entrypoint. Production startup requires an explicit immutable `ARANCEL_MX_API_DATASET` such as `data-2026.08.15`; there is no silent `latest` fallback.
- API responses preserve tariff/NICO string identity, official IGI/IGE literals, source provenance, scorer metadata, and the retrieve-only classification disclaimer. The HTTP layer does not expose source capture, update, reconciliation, release publication, live VUCEM compare, or WCO download.
- FastAPI Cloud runtime is pinned to Python 3.13 with `.python-version` while package metadata continues supporting Python 3.11+. Clean-install certification imports the FastAPI entrypoint from built wheel/sdist artifacts.
- Description `search` ranks matching HS2 chapters first, then current rows under those chapters (`scorer_version` `"1"`, 0–1 `confidence` for analytics). Exact code/prefix ranking is unchanged. Not a classification.
- `arancel-mx --dataset path.duckdb` opens a local DuckDB file for query commands. Missing files fail closed. `package_consumer_probe.py --forbid-src-layout` rejects editable `src/arancel_mx` installs.
- `arancel-mx suggest` / `Dataset.suggest` retrieve ficha plus national notes for the top matches (prefer `fraccion8`). Retrieve-only; a human or their own model classifies.
- Optional local WCO HS 2022 PDF cache for reading support. Not legal identity, not DuckDB, not `source_registry.json`. Copyright remains WCO. `arancel-mx wco cite 61|gir` prints the URL (and cache path if present) without downloading; `wco download` stores the PDF (`--offline` fails closed).
- Search and suggest tables share the hit banner `--- i/n  CODE  score=…  confidence=…  scorer=1 ---`. Search prints one compact line (no ficha). Suggest still prints ficha, national notes, and the WCO support URL. Empty suggest prints the retrieve-only disclaimer then `No results.`
- `search`, `suggest`, and `compare` remain retrieval and verification tools with no classifier or LLM dependency. They do not perform or claim tariff classification, and no external classifier integration is included.
- Scheduled published-bundle canary (`47 12 * * *`): runtime install without extras, then `data download` + `data verify --bundle` against the latest public `data-*` release, then `arancel-mx suggest reproductores --offline`, then `arancel-mx wco cite 01`.
- Official `data-*` capture fetches SNICE national-notes HTML and materializes `arancel_mx_national_notes`. GIR, section/chapter notes, and reglas complementarias remain unpublished.
- Documented GitHub review extensions as install-only, `sha256sum -c SHA256SUMS` copy-paste, and `linguist-generated` for `.xls` fixtures.
- `docs/external-consumption.md` uses `arancel-mx data verify --bundle` after `data download`; `sha256sum -c SHA256SUMS` is for a full GitHub Release directory.
- English section in `TERMS.md`, GitHub issue form `.github/ISSUE_TEMPLATE/open_source_release.yml`, and a tighter tracked-text PII/secret scan.

### Changed

- The official data pipeline runs daily instead of weekly; unchanged sources still end as `no_change`.
- The frontend, trade desk and hub scripts read `/data/v1` instead of `/v1`.
- Documentation describes only the current GitHub-first architecture. New canonical `docs/architecture.md` (macro and micro view), `docs/documentation-style.md` (Spanish, one canonical document per topic) and `docs/operations/v1-sunset.md` (the deprecated `/v1` runtime and its retirement steps). Maintainer and consumer guides are written in Spanish.
- `scripts/check_public_service.py` and the published-bundle canary probe the static data API under `/data/v1` instead of the deprecated `/v1` routes.
- Ponytail over-engineering audit applied: internal subpackages no longer re-export their modules from `__init__.py` (the public API stays `arancel_mx` and `arancel_mx.consumer`), duplicated helpers were merged (`atomic_write_json`, `fold_key`, `sha256`), and dead code was removed (`COMMANDS`, unused SIICEX constants and parameters, `certification/reports.py`, a duplicate OpenAPI error map, the broken `scripts/recover-glossary-from-bundle.mjs`). Ruff now enforces all pyflakes rules, so unused imports and variables fail CI.
- mypy now runs with every error code enabled. The 33 `arg-type` and 3 `attr-defined` findings that were tolerated through `[tool.arancel_mx.type_error_budget]` are fixed, and the budget script, its CI step and its tests are removed. Values read from DuckDB, JSON or HTTP are narrowed with `isinstance` and fail with `TypeError` instead of being passed through unchecked; `/v1/meta` returns 503 when the served dataset lacks a version instead of an invalid response.
- Official build pins refreshed: build 1.6.0, filelock 3.32.4, httpx2 2.12.0, idna 3.19, ruff 0.16.4 and urllib3 2.8.0 (`requirements/production-build.txt`), plus source-map-js 1.2.2 in `package-lock.json`. The API runtime CI job now takes its pytest and httpx2 versions from that constraints file instead of repeating them.
- Live docs match in-tree `0.3.3` vs PyPI `0.2.0`: cache paths, `compare`, national notes, the public source tree, and the FastAPI v1 consumption boundary.
- Documented `/releases/latest` as `data-2026.08.15` (six public assets), Diputados `law_reform` 2025-12-29 / `tariff_decree` 2026-04-23 from that manifest, and that the PyPI long description is frozen at the `0.2.0` upload.
- Development tests use `httpx2` with Starlette's current TestClient path; base package runtime stays independent of that test-only compatibility dependency.

### Deprecated

- HTTP `/v1` on the Vercel deployment (`arancel-mx.vercel.app/v1/*`). Responses carry `Deprecation`, `Sunset: Sun, 31 Jan 2027 00:00:00 GMT` and a `Link` to the static data API. After the sunset date the Vercel functions, their cron and the Neon database are retired. The FastAPI server in `arancel_mx.api` stays available for self-hosting.

### Removed

- Obsolete documents: `todo.md`, completed plans and specs under `docs/superpowers/`, `docs/public-product-sprint.md`, `docs/verification/`, `docs/vercel-centralization.md` and `docs/integration-handoff.md` (their still-valid content moved to `docs/architecture.md`, `docs/sources.md` and `docs/operations/v1-sunset.md`).
- Unused `railway.toml`, the unreferenced `arancel_mx/api/static/index.html` page and the legacy `website/assets/hub-search.{js,css}` files that the site no longer loads.
- Dropped test-only `reportlab` and `PyYAML` from the `dev` extra; parser tests use committed PDF fixtures and workflow contracts read YAML as text.
- Unused staging promotion path, warehouse-only DDL, SNICE HTML crawler, SIICEX↔VUCEM adapter types, parse-reuse helper, demo-generation workflow, and `current_resolver_probe`.

### Fixed

- The `gh-pages` tree carries a `vercel.json` that turns off Vercel Git deployments for that branch. Every data publish used to start a Vercel build that failed with `FASTAPI_ENTRYPOINT_NOT_FOUND`.
- The deprecated `/v1` API stopped at `data-2026.09.14`: the weekly Vercel cron inserted the 26,641 records one statement at a time, about 146 s at 4 ms of database latency against the 60 s function limit, so every promotion timed out and rolled back. Records are now inserted with one batched `executemany` (3.1 s in the same conditions), and a failed sync logs the error type and message instead of a generic line.
- The daily DOF watch never read SIDOF: `decode_fetched_text` rejected its `application/json` responses as non-text, so every day failed. JSON is now decoded as text.
- The `pages` job created `gh-pages` only after redirecting the build summary into `out/`, which does not exist on a fresh checkout; it now creates the directory first.
- The official data pipeline could not publish `data-2026.10.23`: the publisher imported `certify_bundle` from `arancel_mx.certification`, which no longer re-exports it, and failed before uploading. The workflow imports it from `arancel_mx.certification.bundle`, and a new test imports every `from arancel_mx… import …` quoted in workflows and docs so such a break fails CI.
- The static data API is published to `gh-pages` even when the daily pipeline ends as `no_change`. Before, only a new release created the branch, so `/data/v1` returned 404 and the published-bundle canary failed. Pages publication is now its own `pages` job (the only one with `pages: write`), skips the push when `gh-pages` already serves the latest release, and masks the push credential.
- Preserve National Note applicability (`section` vs `chapter`) from materialization through DuckDB, the consumer API, and FastAPI. Newer clients remain compatible with older immutable datasets by reporting legacy note scope as unresolved instead of inferring legal scope.
- OpenAPI now documents the sanitized `ErrorEnvelope` used by handled 400/404/422/500/503 responses and typed health/readiness schemas, including the legitimate 503 not-ready response.
- Official capture, `check-updates`, and documented-URL probes share `build_official_session()`: urllib3 retries connect/read only (`status=0`, backoff 0.5, `total=6`) and HTTPS `DEFAULT:@SECLEVEL=1` for weak-DH gob.mx hosts. HTTP 4xx/5xx stay fail-closed. Script-level URL probes no longer stack a second 3-attempt loop on those transport retries.
- `prepare_release_archive()` stages the source archive, `SHA256SUMS`, and latest pointer before replacing anything in the release directory, so a failed copy leaves the original checksums and no dangling `official-sources.tar.gz`. Cleanup still removes the staging directory if restoring checksums fails.
- `verify_sources()` rejects non-object `source_capture.json` rows with `ValueError` instead of `AttributeError`.
- xlrd integral numeric cells stringify without a `.0` suffix, so a 7-digit `.xls` code is rejected instead of publishing a different 8-digit identity.
- Restored `from arancel_mx.consumer import Dataset` and the other public consumer re-exports.
- Dependabot no longer requests repository labels that do not exist.
- Documented-URL checks wait 1.5s then 3s between connection retries, then retry only the URLs that failed the first pass.
- Package certification retries the exact TestPyPI candidate for up to 10 minutes on each Ubuntu, Windows, and macOS runner before resolving runtime dependencies solely from PyPI. A credential-free sparse checkout now supplies only the versioned certification helper to each otherwise clean runner; it is executed by absolute path and is never installed or added to `PYTHONPATH`. This replaces the insufficient global Simple-index substring check, which could observe the candidate before independent pip clients could resolve it.

## [0.3.0] - 2026-08-13

### Added

- `TERMS.md` and `opensource-checklist.md` for the Apache-2.0 public-release walkthrough.
- Package publish workflow blocks PyPI on an OS × Python matrix after TestPyPI: Ubuntu, Windows, and macOS × CPython 3.11, 3.12, and 3.13. The required PR `test` job stays single-cell Python 3.11 on Ubuntu.
- National-notes HTML parser and materialize path for `arancel_mx_national_notes`. GIR, section/chapter notes, and reglas complementarias remain unpublished.
- `arancel-mx compare` / `Dataset.compare` diffs HS6, MX8 (`fraccion8`), and NICO against VUCEM HTML sheets. The dataset column is the GitHub `data-*` release as read by the CLI. VUCEM is informative, not legal identity.

### Removed

- Dropped `platformdirs` from the consumer runtime; cache paths use `XDG_CACHE_HOME` / `LOCALAPPDATA` / `~/Library/Caches`.
- Dropped `pandas` from the maintainer extra; workbooks are read with `openpyxl`/`xlrd`.
- Removed leftover pandas pins (`numpy`, `python-dateutil`, `six`) from `requirements/production-build.txt`.
- Removed the deprecated maintainer `update` CLI alias. Use `check-updates`.
- Removed shipped Superpowers plan/spec files under `docs/superpowers/`. Live contracts remain in `docs/`.

### Release status

Historical TestPyPI candidates only. `pkg-v0.3.0` uploaded to TestPyPI but did not reach PyPI because macOS queried the Simple index before the new version propagated. `pkg-v0.3.1` added a global readiness check, but its direct Simple-index observation was still earlier than some independent pip clients. `pkg-v0.3.2` added bounded per-runner retries but did not reach PyPI because the clean runners had no checkout from which to execute the versioned helper. None of these candidates reached PyPI. The unchanged package source continues as the `0.3.3` in-tree candidate with a credential-free sparse helper checkout and bounded per-runner installation retries.

## [0.2.0] - 2026-08-12

### Fixed

- Persist classification effective dates and non-core staging roles into DuckDB instead of dropping them during promotion.
- Store full source documents in `dataset_release.source_documents_json` and clear stale ancillary tables when rematerializing a release.
- Reject public datasets that contain more than one current row for the same tariff code.
- Fail closed on undated DOF ledger links, unresolved two-row LIGIE tariff headers, and inexact SIICEX/VUCEM fraction matches.
- Keep identical source captures idempotent when only `retrieved_at` changes, and require `YYYY.MM.DD` dataset versions in the official pipeline runner.
- Treat invalid local cache tags as version-not-found errors, serialize offline cache reads, and let `--no-offline` override `ARANCEL_MX_OFFLINE`.

### Added

- Public `Dataset` API for exact lookup, text search, hierarchy navigation, provenance, local file opening, and verified managed datasets.
- Consumer CLI commands for `data download`, `data status`, `data list`, `data update`, `data path`, and layered `data verify`.
- `lookup`, `search`, `parent`, `children`, and `provenance` CLI commands with deterministic table, JSON, and CSV output.
- `arancel-mx doctor` diagnostics with stable HEALTHY, DEGRADED, and UNHEALTHY exit semantics.
- Strict offline operation after a dataset has been downloaded and verified.
- Transactional cache promotion, release pinning, SHA256 validation, manifest checks, DuckDB structural verification, and exact six-asset bundle certification.
- Cross-platform cache configuration and a PEP 561 `py.typed` marker for the public consumer API.
- Tag-driven `publish-python-package.yml` workflow that builds the distribution once and publishes it to TestPyPI, then to PyPI for final tags after manual approval, using Trusted Publishing (OIDC) with no stored upload tokens.
- `scripts/validate_package_tag.py` tag/version validator and a `docs/testpypi-pypi-setup.md` Trusted Publisher setup checklist.

### Changed

- Prepared public package metadata for the PyPI `0.2.0` candidate.
- Reduced the default consumer dependency surface to DuckDB, filelock, platformdirs, and requests.
- Moved ETL/build-only dependencies to the `maintainer` and `dev` extras while keeping maintainer commands available through lazy imports.
- Python package releases and tariff dataset releases are explicitly versioned and published through separate channels.

### Release status

Trusted Publishing uploaded `arancel-mx==0.2.0` to PyPI on 2026-08-12. The original 2026-08-11 design's full external OS/Python matrix was not a blocking gate for that upload. The `0.3.0` TestPyPI candidate introduced Ubuntu/Windows/macOS × CPython 3.11–3.13 as a blocking publish gate. After the `0.3.1` global readiness check proved insufficient, `0.3.2` performs bounded candidate-install retries on each matrix runner before dependencies resolve from PyPI.
