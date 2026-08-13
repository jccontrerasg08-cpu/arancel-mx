# Changelog

All notable changes to the Python package are documented here. Dataset releases have an independent `data-YYYY.MM.DD` lifecycle in GitHub Releases and are not duplicated as package versions.

## [0.2.0] - 2026-08-12

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

Trusted Publishing uploaded `arancel-mx==0.2.0` to PyPI on 2026-08-12. The original 2026-08-11 design's full external OS/Python matrix was not a blocking gate for that upload. A later `0.2.1+` would be required to treat that matrix as a release gate.
