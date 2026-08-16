# Changelog

All notable changes to the Python package are documented here. Dataset releases have an independent `data-YYYY.MM.DD` lifecycle in GitHub Releases and are not duplicated as package versions.

## [Unreleased]

### Added

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

- Live docs match in-tree `0.3.2` vs PyPI `0.2.0`: cache paths, `compare`, national notes, the public source tree, and the FastAPI v1 consumption boundary.
- Documented `/releases/latest` as `data-2026.08.15` (six public assets), Diputados `law_reform` 2025-12-29 / `tariff_decree` 2026-04-23 from that manifest, and that the PyPI long description is frozen at the `0.2.0` upload.
- Development tests use `httpx2` with Starlette's current TestClient path; base package runtime stays independent of that test-only compatibility dependency.

### Removed

- Dropped test-only `reportlab` and `PyYAML` from the `dev` extra; parser tests use committed PDF fixtures and workflow contracts read YAML as text.
- Unused staging promotion path, warehouse-only DDL, SNICE HTML crawler, SIICEX↔VUCEM adapter types, parse-reuse helper, demo-generation workflow, and `current_resolver_probe`.

### Fixed

- Preserve National Note applicability (`section` vs `chapter`) from materialization through DuckDB, the consumer API, and FastAPI. Newer clients remain compatible with older immutable datasets by reporting legacy note scope as unresolved instead of inferring legal scope.
- OpenAPI now documents the sanitized `ErrorEnvelope` used by handled 400/404/422/500/503 responses and typed health/readiness schemas, including the legitimate 503 not-ready response.
- Official capture, `check-updates`, and documented-URL probes share `build_official_session()`: urllib3 retries connect/read only (`status=0`, backoff 0.5, `total=6`) and HTTPS `DEFAULT:@SECLEVEL=1` for weak-DH gob.mx hosts. HTTP 4xx/5xx stay fail-closed. Script-level URL probes no longer stack a second 3-attempt loop on those transport retries.
- `prepare_release_archive()` stages the source archive, `SHA256SUMS`, and latest pointer before replacing anything in the release directory, so a failed copy leaves the original checksums and no dangling `official-sources.tar.gz`. Cleanup still removes the staging directory if restoring checksums fails.
- `verify_sources()` rejects non-object `source_capture.json` rows with `ValueError` instead of `AttributeError`.
- xlrd integral numeric cells stringify without a `.0` suffix, so a 7-digit `.xls` code is rejected instead of publishing a different 8-digit identity.
- Restored `from arancel_mx.consumer import Dataset` and the other public consumer re-exports.
- Dependabot no longer requests repository labels that do not exist.
- Documented-URL checks wait 1.5s then 3s between connection retries, then retry only the URLs that failed the first pass.
- Package certification retries the exact TestPyPI candidate for up to 10 minutes on each Ubuntu, Windows, and macOS runner before resolving runtime dependencies solely from PyPI. This replaces the insufficient global Simple-index substring check, which could observe the candidate before independent pip clients could resolve it.

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

Historical TestPyPI candidates only. `pkg-v0.3.0` uploaded to TestPyPI but did not reach PyPI because macOS queried the Simple index before the new version propagated. `pkg-v0.3.1` added a global readiness check, but its direct Simple-index observation was still earlier than some independent pip clients. Neither candidate reached PyPI. The unchanged package source continues as the `0.3.2` in-tree candidate with bounded per-runner installation retries.

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
