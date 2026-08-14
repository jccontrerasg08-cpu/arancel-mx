# Python package release contract

This document is the maintainer contract for publishing `arancel-mx` to TestPyPI/PyPI. Consumer install, CLI, and Python API live in [`docs/consumer-cli.md`](consumer-cli.md) and [`docs/external-consumption.md`](external-consumption.md). The `data-*` GitHub Release transaction lives in [`docs/release-process.md`](release-process.md).

`arancel-mx==0.2.0` is published on PyPI. The checkout declares `project.version` `0.2.1`; that version is not on PyPI until `pkg-v0.2.1` passes TestPyPI and the OS/Python matrix.

The dataset is not embedded in the wheel or sdist. Published tariff data remains in immutable GitHub Releases named `data-YYYY.MM.DD`.

Repository maintainers who need the ETL/parsing pipeline can install the optional extra:

```bash
pip install "arancel-mx[maintainer]"
```

## Package and data versions are independent

The Python distribution uses PEP 440 package versions such as `0.2.0` (PyPI) and in-tree `0.2.1`. Tariff datasets use immutable date tags such as `data-2026.08.11` (`/releases/latest` currently). The PyPI project page long description is frozen at the `0.2.0` upload until `pkg-v0.2.1`.

A package change does not create a new tariff dataset. A new tariff dataset does not require rebuilding the Python wheel.

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

## Build-once rule

The wheel and sdist promoted to PyPI must be the exact bytes certified through TestPyPI. A production publish may not rebuild the package after staging certification. SHA256 values are generated immediately after the single build and rechecked before each publication step.

## Release gates

A package version is not considered ready merely because `python -m build` succeeds. The release sequence also requires distribution-content validation, dependency checks, clean installs outside the source checkout, Python/OS compatibility matrices, TestPyPI installation by exact version, real dataset download/integrity/query checks, strict offline retesting, manual approval for the `pypi` environment, and post-publication installation from PyPI.

Trusted Publishing uploaded `arancel-mx==0.2.0` on 2026-08-12. The 2026-08-11 design's full external OS/Python matrix was not a blocking gate for that upload. `0.2.1` treats Ubuntu/Windows/macOS × CPython 3.11, 3.12, and 3.13 as a blocking publish gate after TestPyPI (`external-certification-matrix` in `publish-python-package.yml`). CPython 3.14 and extra install modes (pipx/uv) are not claimed.
