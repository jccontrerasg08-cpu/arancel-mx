<div align="center">

<img src="docs/assets/arancel-mx-banner.svg" alt="arancel-mx - reproducible, auditable, traceable Mexican tariff data" width="100%" />

# arancel-mx

### Reproducible, auditable, traceable Mexican tariff data

Open Python tools to capture, normalize, reconcile, and publish Mexican tariff data with verifiable provenance.

<p>
  <a href="./README.md">Español</a> · <strong>English</strong>
</p>

[![CI](https://github.com/jccontrerasg08-cpu/arancel-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/jccontrerasg08-cpu/arancel-mx/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![DuckDB](https://img.shields.io/badge/DuckDB-embedded-FFF000?logo=duckdb&logoColor=000)](https://duckdb.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[Installation](#installation)** · **[CLI](#quick-cli-usage)** · **[Python](#python-usage)** · **[Data](#data-model)** · **[Sources](#official-sources)** · **[Automation](#official-data-pipeline)** · **[Certification](docs/production-certification.md)** · **[Contributing](#contributing)**

</div>

---

<p align="center">
  <img alt="arancel-mx terminal demo" src="docs/demo.gif" style="max-width:100%; border-radius:8px; box-shadow:0 8px 30px rgba(2,6,23,0.6)" />
</p>

<p align="center"><strong>Capture · Reconcile · Normalize · Validate · Publish</strong></p>

---

## Scope

`arancel-mx` is a public project focused on an open, reproducible, auditable data layer for LIGIE, NICO, and their official Mexican sources. The public core prioritizes data, documentary provenance, validation, DuckDB, and reproducible artifacts rather than trying to replace a complete commercial foreign-trade platform.

> [!IMPORTANT]
> `arancel-mx` is a technical data tool. **It does not constitute legal advice.** For tariff-classification, regulatory-compliance, import, or export decisions, consult the applicable official publications and qualified professionals when appropriate.

## Quick summary

- Captures registered Diputados, DOF, and SNICE snapshots with SHA256 and real `retrieved_at` timestamps.
- Reconciles legal evidence before a candidate can be publishable.
- Normalizes HS2, HS4, HS6, Mexican 8-digit tariff fractions, and 10-digit NICO identifiers.
- Materializes DuckDB and exports CSV, JSON, and a schema v2 manifest.
- Detects `no_change` without creating redundant releases.
- Runs a **daily automated check** and performs **automatic publication** only for a changed dataset that passes every gate.
- Creates or updates a **GitHub Issue** when a production stage fails.
- Publishes verified immutable releases named `data-YYYY.MM.DD` with an exact six-asset contract.
- Maintains an isolated manual certification workflow for release/Issue permissions and rollback without touching `data-*` releases.

## What makes it different

| Property | Implementation |
|---|---|
| Provenance | Each source keeps authority, URL, identity, hash, and capture time |
| Legal evidence | The registered Diputados ledger is reconciled against DOF and registered sources |
| Fail-closed | Discrepancies, parser ambiguity, checksum errors, or invalid data block publication |
| Reproducibility | Exact production constraints and manifest schema v2 |
| Determinism | Canonical exports, checksums, and a captured-source archive |
| Auditability | Releases identify the registry, commit, GitHub run, and exact Actions artifact |
| Recovery | Deterministic automation alerts close only after a later healthy production run |

## HS to Mexican tariff fraction and NICO

```text
HS 2
  ↓
HS 4
  ↓
HS 6
  ↓
Mexican tariff fraction, 8 digits
  ↓
NICO, 10 digits
```

<p align="center">
  <img src="docs/assets/hs-mx-nico-flow.svg" alt="Conceptual flow from HS to Mexican tariff fraction and NICO" width="900" />
</p>

The canonical model validates parent-child relationships so a tariff fraction cannot be published without its HS6 parent and a NICO cannot be published without its active tariff fraction.

## Architecture

```text
official sources → capture → legal reconciliation → parse → validate
→ unchanged: stop green
→ changed + valid: verified immutable release
→ any failure: block publication + GitHub Issue
```

In component terms:

```text
Diputados / DOF / SNICE
          ↓
 source_registry + discovery
          ↓
 capture + source_capture.json
          ↓
 SHA256 + retrieved_at
          ↓
 legal reconciliation
          ↓
 offline XLS/XLSX/PDF parsers
          ↓
 normalization + validation
          ↓
 canonical DuckDB
    ↙       ↓       ↘
  CSV      JSON    manifest.json
          ↓
 verified six-asset bundle
          ↓
 GitHub Release data-YYYY.MM.DD
```

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Pipeline from official sources to DuckDB, CSV, JSON, manifest, and release" width="950" />
</p>

## Installation

```bash
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Python 3.11 or newer is required. Verify the CLI with:

```bash
python -m arancel_mx --help
```

Official builds and CI use the reproducible environment constrained by `requirements/production-build.txt`:

```bash
python -m pip install pip==26.2.1
python -m pip install -c requirements/production-build.txt -e ".[dev]"
```

## Quick CLI usage

The preferred public commands are `build`, `check-updates`, `reconcile`, and `release`.

```bash
# help
python -m arancel_mx --help

# export artifacts from an already validated DuckDB database
python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release

# check registered official-source state and write a change report
python -m arancel_mx check-updates --state-path data/update_state/ligie.json --report-path out/update.json

# reconcile legal evidence
python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json

# verify and prepare a local publication bundle
python -m arancel_mx release --release-dir out/release --source-dir data/raw/release --latest-dir out/latest
```

During the 0.x series, `update` remains a compatibility alias for `check-updates`; new documentation uses `check-updates` as the preferred command name.

| Command | Purpose |
|---|---|
| `build` | Export an already validated tariff database |
| `check-updates` | Check registered official-source state |
| `reconcile` | Reconcile the legal ledger and observed evidence |
| `release` | Verify hashes and prepare the local release contract |

## Python usage

```python
import arancel_mx

print(arancel_mx.__version__)
```

The public query API will grow as search and HS6 ↔ MX8 ↔ NICO10 navigation interfaces stabilize. Unimplemented roadmap capabilities are not presented as stable API.

## Data model

DuckDB separates classification, tariff rates, legal intervals, and provenance. Main tables include `source_registry`, `source_document`, `hs_code`, `tariff_fraction`, `nico`, `tariff_rate`, `canonical_record`, `record_provenance`, and `dataset_release`.

The release manifest uses schema v2 and records fields such as `registry_sha256`, `git_commit_sha`, `github_run_id`, `github_run_attempt`, `github_workflow_ref`, and `github_artifact_name`.

See [`docs/data-model.md`](docs/data-model.md) for the semantics of `retrieved_at`, `generated_at`, and `dataset_release.release_metadata_json`.

## Artifacts and reproducibility

A valid public release contains exactly:

```text
release/
├── arancel_mx.duckdb
├── arancel_mx.csv
├── arancel_mx.json
├── manifest.json
├── SHA256SUMS
└── official-sources.tar.gz
```

`manifest.json` records version, provenance, reconciliation, counts, and hashes. `SHA256SUMS` covers the other five assets. `official-sources.tar.gz` preserves the captured official bytes and their `source_capture.json`.

Logical data is reproducible. A physical DuckDB file is verified by SHA256 for that specific build without assuming that two independently created DuckDB files must be byte-for-byte identical.

## End-to-end official dataset build

The public builder remains available:

```bash
python scripts/build_official_dataset.py \
  --work-dir data/embedded/official-build \
  --output-dir out/release \
  --effective-as-of 2026-08-10 \
  --dataset-version 2026.08.10
```

For production, `scripts/run_official_pipeline.py` adds comparison against the previous published manifest, structured diagnostics, and `no_change` semantics.

## Official data pipeline

The **Official data pipeline** workflow is defined in [`.github/workflows/official-data-pipeline.yml`](.github/workflows/official-data-pipeline.yml).

- Schedule: `17 11 * * *`, a **daily automated check** in UTC.
- `workflow_dispatch`: available for trusted manual dry-runs; `publish=false` is the default manual value.
- Build: global/read-only `contents: read` with offline tests before source access.
- Publish: `contents: write` only when trusted `main` produced `built` and mutation is authorized.
- Notify: `issues: write` only for the automation-alert lifecycle.

**Automatic publication** occurs only for a valid, changed, independently verified candidate. **Any failure blocks publication.** If the registered source identity is unchanged, `no_change` stops green and the publisher remains `skipped`.

Before publication, the bundle is verified locally, verified again after downloading the exact Actions artifact, uploaded to a draft release, and remotely verified before the draft becomes public. An existing `data-YYYY.MM.DD` tag or release is never overwritten.

See [`docs/release-process.md`](docs/release-process.md) for the exact transaction and failure model and [`docs/production-certification.md`](docs/production-certification.md) for the isolated write-boundary certification runbook.

## Official sources

The versioned registry lives at `src/arancel_mx/sources/source_registry.json`.

Primary registered URLs include:

- Chamber of Deputies, LIGIE: https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm
- SNICE, LIGIE: https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html
- SNICE, NICO and NICO proposals: https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html
- SNICE, National Notes: https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html
- SNICE, indicators: https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html
- Diario Oficial de la Federación, related publication: https://www.dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022

[`docs/sources.md`](docs/sources.md) explains how the registered Diputados ledger anchors reconciliation and how DOF evidence acts as a blocking publication gate.

## Official process visuals

### DOF schedule, part 1

<p align="center">
  <img alt="DOF publication schedule and deadlines, part 1" src="docs/dof_timeline.png" style="max-width:85%" />
</p>

### DOF schedule, part 2

<p align="center">
  <img alt="DOF publication schedule and deadlines, part 2" src="docs/dof_timeline2.png" style="max-width:85%" />
</p>

### NICO / DOF flow

<p align="center">
  <img alt="NICO and DOF publication flow" src="docs/nico_flow.png" style="max-width:85%" />
</p>

These images are documentary context, not a live technical status indicator for the dataset.

## Repository structure

```text
.github/
├── workflows/
│   ├── ci.yml
│   ├── official-data-pipeline.yml
│   ├── production-certification.yml
│   └── generate-demo.yml
└── dependabot.yml
requirements/
└── production-build.txt
src/arancel_mx/
├── certification/
├── pipeline/
├── release/
├── sources/
│   └── source_registry.json
└── storage/
scripts/
├── build_official_dataset.py
├── run_official_pipeline.py
├── certify_package_install.py
├── check_duckdb_compat.py
├── certify_github_release.py
├── certify_github_issue.py
├── fetch_previous_release.py
├── publish_release.py
└── data_alert.py
docs/
tests/
LICENSE
NOTICE
```

Engineering design and implementation plans live under `docs/superpowers/` and are intentionally public. Distribution tests scan tracked text for credential patterns and private machine paths. Generated official data, local DuckDB files, `.env` files, and tokens remain outside Git.

## Tests

```bash
python -m pytest -q
python -m build
git diff --check
```

The workflow display name is **CI** and the exact required check context enforced by the `main` ruleset is **`test`**. Normal pull-request CI does not perform live official-source updates or publish releases.

GitHub write permissions are certified separately through the manual **Production certification** workflow. Run `31450616908` on `a14c57ee3aeeb982e6aa7077ae1b34582585db8b` completed successfully and left no certification drafts or tags; see [`docs/production-certification.md`](docs/production-certification.md).

## Security and supply chain

- External GitHub Actions are pinned to full commit SHAs.
- Official build dependencies are constrained by `requirements/production-build.txt`.
- Dependabot opens weekly PRs for Python and GitHub Actions updates.
- Production permissions are job-scoped instead of using `write-all`.
- Releases use the repository `GITHUB_TOKEN`, not a PAT.
- Demo-generation automation opens a PR rather than pushing generated assets directly to `main`.
- Write-boundary certification uses `certification-*` and `[CERTIFICATION ALERT]`, isolated from production namespaces.

The production repository-settings runbook is [`docs/operations/github-settings.md`](docs/operations/github-settings.md). It defines release immutability, the `main` ruleset, required check `test`, Actions permissions, merge settings, and Advanced Security settings that maintainers must verify in the GitHub UI.

See [`SECURITY.md`](SECURITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), and [`docs/production-certification.md`](docs/production-certification.md).

## Project status

| Capability | Status |
|---|---|
| XLS/XLSX/PDF parsers | Available |
| Normalization and hierarchy | Available |
| DuckDB + CSV + JSON | Available |
| Source registry | Available |
| Blocking legal reconciliation | Available |
| Manifest schema v2 | Available |
| End-to-end official build | Available |
| Automatic source-change detection | Available |
| Verified automatic publication | Available |
| GitHub Issue alerts and recovery | Available |
| Live release/Issue write-boundary certification | Available |
| Stable public search API | Roadmap |
| PyPI publication | Roadmap |

## Contributing

Open-source community contributions are welcome. Review [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), [`SECURITY.md`](SECURITY.md), `LICENSE`, and `NOTICE` before submitting changes.

Source, parser, reconciliation, and release-contract changes should add offline fixtures or tests for the expected behavior. Changes to the official build dependency environment should update `requirements/production-build.txt` in the same PR when appropriate.

[Español](README.md) · [Documentation](docs/) · [Sources](docs/sources.md) · [Certification](docs/production-certification.md) · [Contribute](CONTRIBUTING.md) · [Security](SECURITY.md)
