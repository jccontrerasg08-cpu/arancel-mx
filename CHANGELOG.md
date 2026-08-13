# Changelog

All notable changes to the Python package are documented here. Dataset releases have an independent `data-YYYY.MM.DD` lifecycle in GitHub Releases and are not duplicated as package versions.

## [0.2.0] - Unreleased package candidate

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

This section describes the package candidate being certified. It does not mean `arancel-mx==0.2.0` is already available on PyPI. TestPyPI certification, external install matrices, production approval, and post-publish verification remain release gates.
