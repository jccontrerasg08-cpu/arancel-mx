<div align="center">

<img src="docs/assets/arancel-mx-banner.svg" alt="arancel-mx - reproducible, auditable, traceable Mexican tariff data" width="100%" />

# arancel-mx

### Reproducible, auditable, traceable Mexican tariff data

Open Python tooling and data releases for LIGIE, Mexican MX8 tariff fractions, and NICO10 with verifiable provenance.

<a href="./README.md">Español</a> · <strong>English</strong>

[![CI](https://github.com/jccontrerasg08-cpu/arancel-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/jccontrerasg08-cpu/arancel-mx/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**[Start here](docs/getting-started.md)** · **[Verify a release](docs/verify-release.md)** · **[CLI](docs/cli.md)** · **[Dataset](docs/dataset.md)** · **[Sources](docs/sources.md)** · **[Support](SUPPORT.md)**

</div>

<p align="center"><img alt="arancel-mx demo" src="docs/demo.gif" style="max-width:100%" /></p>

## In 30 seconds

`arancel-mx` builds and publishes an open data layer for Mexican tariff classification. The pipeline captures official sources, preserves hashes and actual retrieval times, reconciles legal evidence, validates HS2 → HS4 → HS6 → MX8 → NICO10, and only publishes a changed dataset after every gate passes.

Analysts can use CSV, JSON, or DuckDB from a `data-YYYY.MM.DD` release without installing Python. For a source-checkout install, see [`docs/getting-started.md`](docs/getting-started.md). For independent verification, see [`docs/verify-release.md`](docs/verify-release.md). For questions and bug reports, see [`SUPPORT.md`](SUPPORT.md). Citation metadata is in [`CITATION.cff`](CITATION.cff).

> [!IMPORTANT]
> `arancel-mx` is a technical data tool. It **does not constitute legal advice**. Consult applicable official publications and qualified professionals for classification, compliance, import, or export decisions.

## Scope

The public project focuses on data, documentary provenance, validation, DuckDB, and reproducible artifacts. It does not try to replace a complete commercial foreign-trade platform.

License: **Apache-2.0**.

A valid data release contains exactly:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

## Architecture

```text
official sources → capture → legal reconciliation → parse → validate
→ unchanged: stop green
→ changed + valid: verified immutable release
→ any failure: block publication + GitHub Issue
```

The registered source model keeps legal publication evidence, legislative compilation, and structured operational datasets separate. VUCEM is currently characterized only as an independent operational cross-check.

## Installation

Until the package is published to PyPI, install the CLI from a normal source checkout:

```bash
git clone https://github.com/jccontrerasg08-cpu/arancel-mx.git
cd arancel-mx
python -m venv .venv
source .venv/bin/activate
python -m pip install .
python -m arancel_mx --help
```

Official CI and production builds use the exact environment constrained by `requirements/production-build.txt`:

```bash
python -m pip install pip==26.2.1
python -m pip install -c requirements/production-build.txt -e ".[dev]"
```

Consumer dependencies remain compatible ranges in `pyproject.toml`; official builds use exact pins.

## Quick CLI usage

```bash
python -m arancel_mx --help
python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release
python -m arancel_mx check-updates --state-path data/update_state/ligie.json --report-path out/update.json
python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json
python -m arancel_mx release --release-dir out/release --source-dir data/raw/release --latest-dir out/latest
```

Preferred commands are `build`, `check-updates`, `reconcile`, and `release`. `update` remains a deprecated read-only alias during 0.x.

## Python usage

```python
import arancel_mx
print(arancel_mx.__version__)
```

A stable query/search API remains roadmap. Internal modules are not presented as stable interfaces.

## Official sources

The versioned registry is `src/arancel_mx/sources/source_registry.json`.

- DOF provides primary legal publication evidence.
- Diputados provides registered legislative compilation/ledger context.
- SNICE provides registered structured LIGIE/NICO datasets and related material.
- VUCEM remains a non-authoritative operational cross-check under characterization.

Registered source pages include:

- https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm
- https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html
- https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html
- https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html
- https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html
- https://www.dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022

## Official autonomous pipeline

The **Official data pipeline** is [`.github/workflows/official-data-pipeline.yml`](.github/workflows/official-data-pipeline.yml).

- Schedule: `17 11 * * *`, a **daily automated check** in UTC.
- `no_change` finishes green and publishes nothing redundant.
- **automatic publication** happens only for changed data that passes every gate.
- **any failure blocks publication** and produces bounded diagnostics for a GitHub Issue.
- Production releases use the immutable `data-YYYY.MM.DD` namespace.

The public end-to-end builder remains `scripts/build_official_dataset.py`. A verified bundle contains `arancel_mx.duckdb`, `arancel_mx.csv`, `arancel_mx.json`, `manifest.json`, `SHA256SUMS`, and `official-sources.tar.gz`.

## Reproducibility and verification

The release contract verifies DuckDB/CSV/JSON logical data, manifest provenance, checksums, and captured official source identity. Clean-install certification builds and installs both wheel and sdist outside the repository checkout.

The documentation site is locked by `website/package-lock.json`. `.github/workflows/docs-ci.yml` uses `npm ci`, typechecking, and independent Spanish and English builds with read-only repository permissions.

See [`docs/reproducibility.md`](docs/reproducibility.md), [`docs/verify-release.md`](docs/verify-release.md), and [`docs/production-certification.md`](docs/production-certification.md).

## Repository structure

```text
.github/        workflows, templates, CODEOWNERS, Dependabot
requirements/   exact production environment
src/arancel_mx/ Python package
scripts/        build, release, certification, utilities
docs/           public and engineering documentation
tests/          offline tests and production contracts
website/        Docusaurus site and reproducible npm lockfile
LICENSE
NOTICE
CITATION.cff
SUPPORT.md
```

## Tests

```bash
python -m pytest -q
python -m build
git diff --check
```

The required `main` check is `test`. Normal pull requests do not publish data releases or perform live official-source updates.

## Community and security

Open-source community contributions are welcome. Read [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), [`SECURITY.md`](SECURITY.md), [`SUPPORT.md`](SUPPORT.md), `LICENSE`, `NOTICE`, and [`CITATION.cff`](CITATION.cff).

Repository Actions are pinned by full commit SHA and use least-privilege permissions. Repository settings and hardening expectations are documented in [`docs/operations/github-settings.md`](docs/operations/github-settings.md).

## Documentation status

Canonical public documentation lives under `docs/`. Docusaurus ES/EN and permanent read-only docs CI are implemented on this branch. GitHub Pages is intentionally not advertised as live until a real production deployment is verified.
