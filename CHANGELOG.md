# Changelog

All notable changes to the Python package are documented here. Dataset releases have an independent `data-YYYY.MM.DD` lifecycle in GitHub Releases and are not duplicated as package versions.

## [Unreleased]

### Changed

- Live docs match in-tree `0.2.1` vs PyPI `0.2.0`: cache paths, `compare`, national notes, and the public source tree.
- Documented `/releases/latest` as `data-2026.08.11` (six public assets), Diputados `law_reform` 2025-12-29 / `tariff_decree` 2026-04-23 from that manifest, and that the PyPI long description is frozen at the `0.2.0` upload.
### Fixed

- `prepare_release_archive()` stages the source archive, `SHA256SUMS`, and latest pointer before replacing anything in the release directory, so a failed copy leaves the original checksums and no dangling `official-sources.tar.gz`. Cleanup still removes the staging directory if restoring checksums fails.
- `verify_sources()` rejects non-object `source_capture.json` rows with `ValueError` instead of `AttributeError`.
- xlrd integral numeric cells stringify without a `.0` suffix, so a 7-digit `.xls` code is rejected instead of publishing a different 8-digit identity.
- Restored `from arancel_mx.consumer import Dataset` and the other public consumer re-exports.
- Dependabot no longer requests repository labels that do not exist.
- Documented-URL checks wait 1.5s then 3s between connection retries, then retry only the URLs that failed the first pass.

## [0.2.1] - 2026-08-13

### Added

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

In-tree only. `0.2.1` is not on PyPI until `pkg-v0.2.1` passes TestPyPI and the OS/Python matrix.

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

Trusted Publishing uploaded `arancel-mx==0.2.0` to PyPI on 2026-08-12. The original 2026-08-11 design's full external OS/Python matrix was not a blocking gate for that upload. `0.2.1` treats Ubuntu/Windows/macOS × CPython 3.11–3.13 as a blocking publish gate.
