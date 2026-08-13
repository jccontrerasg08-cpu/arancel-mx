# Python package release contract

This document describes the public Python distribution independently from the tariff-data release pipeline.

## Consumer installation

`arancel-mx==0.2.0` is published on PyPI. The checkout declares `project.version` `0.2.1`; that version is not on PyPI until `pkg-v0.2.1` passes TestPyPI and the OS/Python matrix. Downstream apps keep pinning the published wheel:

```bash
pip install arancel-mx==0.2.0
```

The base install is intentionally consumer-focused. The dataset is not embedded in the wheel or sdist. Published tariff data remains in immutable GitHub Releases named `data-YYYY.MM.DD` and is downloaded only when the user requests managed data.

Repository maintainers who need the ETL/parsing pipeline can install the optional extra:

```bash
pip install "arancel-mx[maintainer]"
```

Contributors should continue to use the full development extra from a checkout:

```bash
python -m pip install -e ".[dev]"
```

## First CLI use

```bash
arancel-mx --version
arancel-mx doctor
arancel-mx data download
arancel-mx lookup 01012101
arancel-mx ficha 01012101
arancel-mx compare 01012101
arancel-mx search "refrigeradores"
```

An exact data release can be pinned independently from the Python package version:

```bash
arancel-mx data download --dataset data-YYYY.MM.DD
arancel-mx lookup 01012101 --dataset data-YYYY.MM.DD
```

After the selected release has been verified, strict offline queries use only the verified local cache:

```bash
arancel-mx lookup 01012101 --offline --format json
arancel-mx doctor --offline --json
```

## Python API

```python
from arancel_mx import Dataset

# Resolve one exact latest data release, verify it, cache it, and open read-only.
db = Dataset.latest()
record = db.lookup("01012101")
card = db.ficha("01012101")
rows = db.compare("01012101")  # Dataset.compare vs VUCEM; informative, not legal identity
results = db.search("refrigeradores", limit=20)
children = db.children("0101")
sources = db.provenance("01012101")
```

Pin a dataset release explicitly:

```python
from arancel_mx import Dataset

db = Dataset.version("data-YYYY.MM.DD")
```

Or open a local DuckDB file structurally without claiming release provenance:

```python
from arancel_mx import Dataset

db = Dataset.open("/path/to/arancel_mx.duckdb")
```

`Dataset.open()` validates the local database structure, but a local file is not promoted to the stronger `release_verified` state merely because it opens successfully.

## Package and data versions are independent

The Python distribution uses PEP 440 package versions such as `0.2.0` (PyPI) and in-tree `0.2.1`. Tariff datasets use immutable date tags such as `data-2026.08.11`.

Verified datasets are cached under `XDG_CACHE_HOME/arancel-mx`, `~/Library/Caches/arancel-mx` on macOS, `%LOCALAPPDATA%/arancel-mx/Cache` on Windows, or `~/.cache/arancel-mx`. Override with `ARANCEL_MX_CACHE_DIR`. The consumer extra does not depend on `platformdirs`.

A package change does not create a new tariff dataset. A new tariff dataset does not require rebuilding the Python wheel. This separation keeps software compatibility independent from legal/data update cadence.

## Git tags and GitHub Releases

Package candidates use git tags such as:

```text
pkg-v0.2.0
```

The package workflow must **not create a GitHub Release** for `pkg-v*` tags. GitHub Releases remain reserved for `data-*` bundles because the repository's public `/releases/latest/download/...` links are part of the dataset download contract.

The package publication channel is instead:

```text
git tag pkg-vX.Y.Z
        ↓
GitHub Actions build once
        ↓
TestPyPI
        ↓
external certification
        ↓
manual production approval
        ↓
PyPI
```

The data publication channel remains:

```text
GitHub Releases
└── data-YYYY.MM.DD
    ├── arancel_mx.duckdb
    ├── arancel_mx.csv
    ├── arancel_mx.json
    ├── manifest.json
    ├── SHA256SUMS
    └── official-sources.tar.gz
```

## Build-once rule

The wheel and sdist promoted to PyPI must be the exact bytes certified through TestPyPI. A production publish may not rebuild the package after staging certification. SHA256 values are generated immediately after the single build and rechecked before each publication step.

## Release gates

A package version is not considered ready merely because `python -m build` succeeds. The release sequence also requires distribution-content validation, dependency checks, clean installs outside the source checkout, Python/OS compatibility matrices, TestPyPI installation by exact version, real dataset download/integrity/query checks, strict offline retesting, manual approval for the `pypi` environment, and post-publication installation from PyPI.

Trusted Publishing uploaded `arancel-mx==0.2.0` on 2026-08-12. The 2026-08-11 design's full external OS/Python matrix was not a blocking gate for that upload. `0.2.1` treats Ubuntu/Windows/macOS × CPython 3.11, 3.12, and 3.13 as a blocking publish gate after TestPyPI (`external-certification-matrix` in `publish-python-package.yml`). CPython 3.14 and extra install modes (pipx/uv) are not claimed.
