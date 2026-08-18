<div align="center">

<img src="docs/assets/arancel-mx-banner.svg" alt="arancel.mx - open Mexican tariff data" width="100%" />

# arancel-mx

### From scattered official publications to verifiable, ready-to-use Mexican tariff data

`arancel-mx` captures, reconciles, normalizes, and publishes LIGIE/NICO data with verifiable provenance so you can **query, integrate, analyze, and audit** Mexican tariff data without rebuilding the pipeline yourself.

<p>
  <a href="./README.md">Español</a> · <strong>English</strong>
</p>

[![CI](https://github.com/jccontrerasg08-cpu/arancel-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/jccontrerasg08-cpu/arancel-mx/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![DuckDB](https://img.shields.io/badge/DuckDB-embedded-FFF000?logo=duckdb&logoColor=000)](https://duckdb.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[Open the hub](https://arancel-mx.vercel.app/)** · **[Latest data](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)** · **[Install](#in-60-seconds)** · **[Quickstart](docs/consumer-quickstart.md)** · **[Documentation](docs/README.md)**

</div>

## Why it exists

Mexican tariff data is published across documents, landing pages, and files with different legal and operational roles. Building a reliable application on top of those sources requires more than downloading a spreadsheet: you need to know **which source was observed, when it was captured, what legal evidence supports it, how it was normalized, and which exact bytes produced the published dataset**.

`arancel-mx` isolates that problem as a reusable public layer. Its responsibility is deliberately narrow: turn observed official sources into a canonical, reproducible, auditable representation. Analytical interfaces, RAG systems, automation, and broader foreign-trade products can consume that layer without duplicating parsers or inventing their own LIGIE/NICO truth.

> **Core idea:** you do not have to trust a README claim that the data is current. You can verify the release, hashes, manifest, and captured sources.

## Choose how to use it

| I want to... | Surface | First step |
|---|---|---|
| Use **Data / DuckDB** from SQL, BI, notebooks, or ETL | Immutable DuckDB, CSV, and JSON releases | `arancel-mx data download` |
| Use the **CLI** for fast tariff lookups | `lookup`, `search`, `ficha`, `chapters`, `provenance`, `compare` | `arancel-mx lookup 01012101` |
| Integrate with **Python** | Public `Dataset` API and types | `from arancel_mx import Dataset` |
| Build on the **HTTP / API** read-only surface | `/v1`, `/docs`, `/readyz`; no API key | `GET /v1/lookup/8517130100` |
| Perform **Audit and reproduction** | `manifest.json`, `SHA256SUMS`, captured sources, `data verify` | `sha256sum -c SHA256SUMS` |

### In 60 seconds

```bash
pip install arancel-mx==0.2.0
arancel-mx doctor
arancel-mx data download
arancel-mx lookup 01012101
arancel-mx ficha 01012101
arancel-mx data verify
```

Explore further:

```bash
arancel-mx chapters
arancel-mx search "refrigeradores"
arancel-mx suggest "camisas de algodón de punto"
arancel-mx compare 01012101
arancel-mx wco cite 01
```

The Python package and datasets have separate version channels. `arancel-mx --version` identifies the package; each published dataset uses an immutable `data-YYYY.MM.DD` release. Pinning the package does **not** pin the dataset.

## From official publication to verifiable release

```text
official sources → capture → legal reconciliation → parse → validate
→ unchanged: stop green
→ changed + valid: verified immutable release
→ any failure: block publication + GitHub Issue
```

The trust chain retains source identity, URL, SHA256, `retrieved_at`, reconciliation evidence, commit, GitHub Actions run, and release manifest. The model is fail-closed: discrepancies, ambiguous parsing, or invalid data do not get silently repaired to force publication.

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Pipeline from official sources to DuckDB, CSV, JSON, manifest, and release" width="950" />
</p>

## Latest dataset release

**Always download the most recent public `arancel-mx` dataset release.**

**[DuckDB](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.duckdb)** ·
**[CSV](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.csv)** ·
**[JSON](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.json)** ·
[Manifest](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/manifest.json) ·
[SHA256SUMS](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/SHA256SUMS) ·
[Official sources](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/official-sources.tar.gz) ·
**[View release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)**

The `/releases/latest/download/...` links resolve to assets from the public release currently marked as latest. GitHub lists the size of each asset on that page; the verifiable identity is `SHA256SUMS`, not the displayed file size.

```bash
sha256sum -c SHA256SUMS
```

<p align="center">
  <img alt="arancel-mx terminal demo" src="docs/demo.gif" style="max-width:100%; border-radius:8px; box-shadow:0 8px 30px rgba(2,6,23,0.6)" />
</p>

<p align="center"><strong>Capture · Reconcile · Normalize · Validate · Publish</strong></p>

## Scope

`arancel-mx` is a public data layer for LIGIE, NICO, and their official Mexican sources. It prioritizes data, documentary provenance, validation, DuckDB, and reproducible artifacts rather than trying to replace a complete commercial foreign-trade platform.

> [!IMPORTANT]
> `arancel-mx` is a technical data tool. **It does not constitute legal advice.** For tariff classification, regulatory compliance, import, or export decisions, consult the applicable official publications and qualified professionals when appropriate.

## What is included

- Captures registered Diputados, DOF, and SNICE snapshots with SHA256 and real `retrieved_at` timestamps.
- Can evaluate dated LIGIE/NICO candidates discovered through the registered SNICE_DOCS corpus while keeping parsing and legal reconciliation as blocking gates.
- Normalizes HS2, HS4, HS6, Mexican 8-digit tariff fractions, and 10-digit NICO identifiers.
- Materializes DuckDB and exports CSV, JSON, and a schema v2 manifest.
- Detects `no_change` without creating redundant releases.
- The **Official data pipeline** now runs a scheduled weekly Monday check and performs **automatic publication** only for changed data that passes every gate.
- Creates or updates a **GitHub Issue** when a production stage fails.
- Publishes verified immutable `data-YYYY.MM.DD` releases with an exact six-asset contract.
- Keeps manual write-boundary certification and rollback isolated from production namespaces.

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

### Fast source promotion without weaker trust

The LIGIE and NICO registries can inspect the explicit public SNICE_DOCS corpus. A document is eligible only when it comes from the registered index, matches an allowed family and media type, contains a valid date, and is the unambiguous newest candidate. Discovery origin is preserved with SHA256; parsing, validation, Diputados/DOF reconciliation, and certification remain publication gates.

<p align="center">
  <img src="docs/assets/source-promotion.png" alt="Registered SNICE pages and the SNICE_DOCS corpus converge on a dated candidate that passes publication gates" width="100%" />
</p>

Read the [source-promotion policy](docs/source-promotion.md) for the allowlist, NICO limits, and rollback procedure.

## Installation

Python 3.11 or newer is required.

### Published dataset consumer

`arancel-mx==0.2.0` is published on PyPI, uploaded 2026-08-12 through Trusted Publishing. The full external OS/Python matrix was not a blocking gate for that upload. `0.3.3` remains in-tree and its publication flow gates on Ubuntu/Windows/macOS × CPython 3.11–3.13 after TestPyPI.

```bash
pip install arancel-mx==0.2.0
arancel-mx --version
arancel-mx doctor
```

The canonical downstream guide is [`docs/external-consumption.md`](docs/external-consumption.md).

### Repository development

```bash
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m arancel_mx --help
```

Official builds and CI use `requirements/production-build.txt`:

```bash
python -m pip install pip==26.2.1
python -m pip install -c requirements/production-build.txt -e ".[dev]"
```

## Downstream ingest

Downstream apps should pin, install, verify, and query `arancel-mx` as an upstream data package. Start with the [consumer quickstart](docs/consumer-quickstart.md), [official source roles](docs/official-source-roles.md), [NICO/LIGIE hierarchy](docs/nico-ligie-guide.md), and full [`docs/external-consumption.md`](docs/external-consumption.md) contract.

Short path: **install**, **verify**, then **query**. Preserve the official `igi_text` / `ige_text` literals; `compare` against VUCEM is informative, not legal identity. Do not treat a self-ingested copy as upstream truth.

### Public HTTP API

The **public HTTP API** is **GET-only**, **read-only**, and requires **no API key**. Its stable contract lives under `/v1`; `/docs` exposes interactive OpenAPI documentation, `/readyz` reports readiness, and `/v1/meta` reports API, package, and dataset identities separately.

```text
ARANCEL_MX_API_DATASET=data-2026.08.15
```

There is no implicit `latest` fallback. The HTTP layer uses the verified `Dataset` facade, **does not classify** merchandise, and is not legal advice.

The primary hub is [`https://arancel-mx.vercel.app`](https://arancel-mx.vercel.app). Since integration #132, Vercel serves read-only operational metadata/search (`/v1/meta`, `/v1/search`) from its Neon-backed operational layer synchronized from verified releases. Other `/v1/*`, `/docs`, and `/readyz` paths are presented on the same public domain and proxied to the reusable FastAPI runtime at `arancel-mx.fastapicloud.dev`. The verified release remains the source of truth; the operational store does not replace the publication pipeline.

A direct FastAPI integration can pin its base URL explicitly:

```bash
export ARANCEL_MX_API_URL="https://arancel-mx.fastapicloud.dev"
curl "$ARANCEL_MX_API_URL/v1/lookup/8517130100"
```

The detailed endpoint contract lives in [`docs/external-consumption.md`](docs/external-consumption.md).

## Quick CLI usage

```bash
arancel-mx doctor
arancel-mx data download
arancel-mx lookup 01012101
arancel-mx ficha 01012101
arancel-mx compare 01012101
arancel-mx chapters
arancel-mx search "refrigeradores"
arancel-mx suggest "camisas de algodón de punto"
arancel-mx wco cite 01
arancel-mx data verify
```

After downloading and verifying a release, queries can run offline:

```bash
arancel-mx lookup 01012101 --offline --format json
arancel-mx data verify --offline --format json
```

Pin an exact release with `--dataset data-YYYY.MM.DD`. See [`docs/consumer-cli.md`](docs/consumer-cli.md) for JSON/CSV formats, environment variables, cache integrity, and `doctor` behavior.

### Consumer commands

| Command | Purpose |
|---|---|
| `doctor` | Diagnose installation, cache, dataset, DuckDB, and remote access |
| `data download` | Download and promote only a verified release into the cache |
| `data status` / `data list` | Show local versions and valid remote releases |
| `data update` | Download the newest valid release without deleting older versions |
| `data path` | Print the selected DuckDB path |
| `data verify` | Revalidate local and optional remote integrity |
| `lookup` / `search` | Query by exact code or text |
| `suggest` | Retrieve ficha and national notes for candidates; does not classify |
| `wco cite` / `wco download` | WCO HS 2022 PDF reference; reading support, not LIGIE/NICO authority |
| `ficha` | Chapter → fraction/NICO card with UM, IGI, and IGE |
| `compare` | Informative HS6 / MX8 / NICO diff against VUCEM |
| `chapters` | List HS2 chapters |
| `parent` / `children` | Navigate HS2 → HS4 → HS6 → MX8 → NICO10 |
| `provenance` | Show documentary traceability |

### Repository maintainer commands

```bash
python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release
python -m arancel_mx check-updates --state-path data/update_state/ligie.json --report-path out/update.json
python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json
python -m arancel_mx release --release-dir out/release --source-dir data/raw/release --latest-dir out/latest
```

## Python usage

```python
from arancel_mx import Dataset

dataset = Dataset.latest()
card = dataset.ficha("01012101")
print(card.formatted_code, card.record.description, card.record.igi_text)
for chapter in dataset.chapters():
    print(chapter.code, chapter.description)
```

`Dataset.open("arancel_mx.duckdb")` opens a structurally validated local file. `ficha` and `chapters` use the verified official dataset; they do not scrape SIICEX-CAAAREM or dumps such as tigies-mx.

## Data model

DuckDB separates classification, tariff rates, legal intervals, and provenance. Main tables include `source_registry`, `source_document`, `hs_code`, `tariff_fraction`, `nico`, `tariff_rate`, `canonical_record`, `record_provenance`, and `dataset_release`.

The schema v2 release manifest records `registry_sha256`, `git_commit_sha`, `github_run_id`, `github_run_attempt`, `github_workflow_ref`, and `github_artifact_name`. See [`docs/data-model.md`](docs/data-model.md).

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

`manifest.json` records version, provenance, reconciliation, counts, and hashes. `SHA256SUMS` covers the other five assets. `official-sources.tar.gz` preserves captured official bytes and `source_capture.json`.

## End-to-end official dataset build

```bash
python scripts/build_official_dataset.py \
  --work-dir data/embedded/official-build \
  --output-dir out/release \
  --effective-as-of 2026-08-10 \
  --dataset-version 2026.08.10
```

`scripts/run_official_pipeline.py` adds previous-manifest comparison, structured diagnostics, and `no_change` semantics.

## Official data pipeline

The **Official data pipeline** workflow is defined in [`.github/workflows/official-data-pipeline.yml`](.github/workflows/official-data-pipeline.yml).

- Current schedule: `17 11 * * 1`, a **weekly automated Monday check** in UTC.
- The previous `17 11 * * *` schedule represented the former **daily automated check** and was replaced by #132.
- `workflow_dispatch` supports trusted dry-runs; `publish=false` is the default manual value.
- Build: `contents: read` with offline tests before source access.
- Publish: `contents: write` only when trusted `main` produced `built` and mutation is authorized.
- Notify: `issues: write` only for automation alerts and recovery.
- Canary: [`.github/workflows/published-bundle-canary.yml`](.github/workflows/published-bundle-canary.yml) verifies the public six-asset contract.

**Automatic publication** occurs only for a valid, changed, independently verified candidate. **Any failure blocks publication.** If source identity is unchanged, `no_change` stops green and the publisher remains `skipped`.

See [`docs/release-process.md`](docs/release-process.md) and [`docs/production-certification.md`](docs/production-certification.md).

## Official sources

The versioned registry lives at `src/arancel_mx/sources/source_registry.json`.

Primary registered URLs include:

- [Chamber of Deputies, LIGIE](https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm)
- [SNICE, LIGIE](https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html)
- [SNICE, NICO and NICO proposals](https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html)
- [SNICE, National Notes](https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html)
- [SNICE, indicators](https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html)
- [Diario Oficial de la Federación, related publication](https://dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022)

[`docs/sources.md`](docs/sources.md) explains how the Diputados ledger anchors reconciliation and how DOF evidence acts as a blocking publication gate. SIICEX-CAAAREM and dumps such as tigies-mx are not official sources.

## Official process visuals

### DOF schedule, part 1

<p align="center"><img alt="DOF publication schedule and deadlines, part 1" src="docs/dof_timeline.png" style="max-width:85%" /></p>

### DOF schedule, part 2

<p align="center"><img alt="DOF publication schedule and deadlines, part 2" src="docs/dof_timeline2.png" style="max-width:85%" /></p>

### NICO / DOF flow

<p align="center"><img alt="NICO and DOF publication flow" src="docs/nico_flow.png" style="max-width:85%" /></p>

These images provide documentary context rather than live dataset status.

## Repository structure

```text
.github/
├── workflows/
│   ├── ci.yml
│   ├── official-data-pipeline.yml
│   ├── publish-python-package.yml
│   └── production-certification.yml
└── dependabot.yml
api/
requirements/
└── production-build.txt
src/arancel_mx/
├── api/
├── certification/
├── consumer/
├── domain/
├── operational/
├── parsers/
├── pipeline/
├── release/
├── sources/
└── storage/
scripts/
website/
docs/
tests/
TERMS.md
LICENSE
NOTICE
```

Distribution tests scan tracked text for credential patterns and private machine paths. Generated data, local DuckDB files, environment files, and tokens remain outside Git.

## Tests

```bash
python -m pytest -q
python -m build
git diff --check
```

The workflow display name is **CI** and the exact required `main` check is **`test`**. Normal pull requests do not publish releases.

The repository-settings runbook is [`docs/operations/github-settings.md`](docs/operations/github-settings.md). See also [`SECURITY.md`](SECURITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), and [`docs/production-certification.md`](docs/production-certification.md).

## Security and supply chain

- External GitHub Actions are pinned to full commit SHAs.
- Official build dependencies are constrained by `requirements/production-build.txt`.
- Dependabot proposes Python and GitHub Actions updates.
- Production permissions are job-scoped instead of `write-all`.
- Releases do not require a PAT.
- Write-boundary certification remains isolated from production namespaces.

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
| Vercel hub with operational metadata/search | Available |
| Public HTTP API | Available (`/v1`, GET-only/read-only, no API key) |
| TIGIE card (`ficha` / `chapters`) | Available |
| Compare HS6 / MX8 / NICO vs VUCEM | Available, informative |
| LIGIE national notes | Parser, official capture, and `arancel_mx_national_notes`; `data-2026.08.15` contains 266 records from the official DOF source |
| PyPI publication | Published: `arancel-mx==0.2.0` (`0.3.3` in-tree, not on PyPI until `pkg-v0.3.3`) |

## Contributing

Open-source community contributions are welcome. Review [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), [`SECURITY.md`](SECURITY.md), [`TERMS.md`](TERMS.md), [`opensource-checklist.md`](opensource-checklist.md), `LICENSE`, and `NOTICE` before submitting changes.

Source, parser, reconciliation, and release-contract changes should add offline fixtures/tests. Official-build dependency changes should update `requirements/production-build.txt` in the same PR when appropriate.

[Español](README.md) · [Documentation hub](docs/README.md) · [Consumer quickstart](docs/consumer-quickstart.md) · [Source roles](docs/official-source-roles.md) · [NICO/LIGIE](docs/nico-ligie-guide.md) · [Downstream ingest](docs/external-consumption.md) · [Sources](docs/sources.md) · [SNICE_DOCS policy](docs/source-promotion.md) · [Certification](docs/production-certification.md) · [Contribute](CONTRIBUTING.md) · [Security](SECURITY.md)
