<div align="center">

<img src="docs/assets/arancel-mx-banner.svg" alt="arancel-mx - reproducible, auditable, traceable Mexican tariff data" width="100%" />

# arancel-mx

### Reproducible, auditable, traceable Mexican tariff data.

Open Python tools to capture, normalize, reconcile, and publish Mexican tariff data with verifiable provenance.

<p>
  <a href="./README.md">Español</a> · <strong>English</strong>
</p>

[![CI](https://github.com/jccontrerasg08-cpu/arancel-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/jccontrerasg08-cpu/arancel-mx/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![DuckDB](https://img.shields.io/badge/DuckDB-embedded-FFF000?logo=duckdb&logoColor=000)](https://duckdb.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[Quick start](#installation)** · **[CLI](#quick-cli-usage)** · **[Python](#python-usage)** · **[Data](#data-model)** · **[Sources](#official-sources-and-registered-urls)** · **[Architecture](#architecture)** · **[Contributing](#contributing)**

</div>

---

<p align="center">
  <img alt="arancel-mx terminal demo" src="docs/demo.gif" style="max-width:100%; border-radius:8px; box-shadow:0 8px 30px rgba(2,6,23,0.6)" />
</p>

<p align="center"><strong>Capture · Normalize · Reconcile · Validate · Publish</strong></p>

---

## Scope

`arancel-mx` is a public project focused on building an open, reproducible, auditable data layer for Mexican tariff information with traceability back to official sources.

The public core is centered on reusable data and tooling: LIGIE, NICO, HS code normalization, tariff rates, documentary provenance, DuckDB, and reproducible artifacts. It is not intended to replace a complete commercial foreign-trade system.

> [!IMPORTANT]
> `arancel-mx` is a technical data tool. **It does not constitute legal advice.** For tariff-classification, regulatory-compliance, import, or export decisions, consult the applicable official sources and qualified professionals when appropriate.

## Quick summary

- Audits and materializes LIGIE / NICO into a reproducible DuckDB database
- Normalizes HS codes and rates while preserving legal provenance and evidence
- Exports deterministic artifacts: CSV, JSON, DuckDB, and a SHA256 manifest

| Capability | What it provides |
|---|---|
| Capture | Evidence from official publications |
| Normalization | Canonical code and rate representations |
| Traceability | Documentary provenance and record origin |
| Reconciliation | Comparison across official evidence |
| Storage | Reproducible DuckDB analytical database |
| Publication | CSV, JSON, DuckDB, and SHA256 manifests |

## What makes it different

- Provenance: each row can retain documentary evidence and source origin (DOF / SNICE / Chamber of Deputies)
- Determinism: reproducible exports with manifests and checksums
- Auditability: discovery, capture, reconciliation, and validation flows remain inspectable

<p align="center">
  <img src="docs/assets/provenance.svg" alt="Traceability, reproducibility, and auditability in arancel-mx" width="900" />
</p>

## From HS to Mexican tariff fraction and NICO

One direction of the public core is to keep a coherent representation of the classification levels used for goods while preserving the evidence supporting each relationship.

<p align="center">
  <img src="docs/assets/hs-mx-nico-flow.svg" alt="Conceptual flow from HS 6 digits to Mexican 8-digit tariff fraction and 10-digit NICO identifier" width="900" />
</p>

Conceptually:

```text
HS 6 digits
     ↓
Mexican tariff fraction 8 digits
     ↓
NICO 2 additional digits
     ↓
Mexican 10-digit identifier
```

Public HS6 ↔ MX8 ↔ NICO10 search and navigation functions remain roadmap items until they are implemented, documented, and tested as a stable API.

## Main features

- Offline XLS/XLSX/PDF parsers for LIGIE and NICO
- Canonical normalization of codes and tariff rates
- Deterministic consolidation and versioning of records
- Flows to capture sources, verify DOF publications, and build verifiable releases

The repository also organizes the public core around parsers, pipelines, sources, storage, and release construction, with automated tests for reproducibility and public distribution.

## Architecture

The pipeline separates discovery, capture, processing, validation, and publication so each stage can be audited independently.

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Pipeline from official sources to DuckDB, CSV, JSON, manifests, and releases" width="950" />
</p>

```text
DOF / SNICE / Chamber of Deputies
              ↓
          discovery
              ↓
           capture
      URL + evidence + SHA256
              ↓
            parser
       XLS / XLSX / PDF
              ↓
        normalization
              ↓
          validation
              ↓
        reconciliation
              ↓
           DuckDB
        ↙      ↓      ↘
      CSV     JSON   manifest
              ↓
            release
```

## Installation

```bash
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Python 3.11 or newer is required. After activating the environment, verify the CLI with:

```bash
python -m arancel_mx --help
```

## Quick CLI usage

The current public commands are `build`, `update`, `reconcile`, and `release`.

```bash
# show help
python -m arancel_mx --help

# export artifacts from an already validated DuckDB database
python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release

# update state from the official ledger (requires network access)
python -m arancel_mx update --state-path data/update_state/ligie.json --report-path out/update.json

# reconcile evidence
python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json

# prepare local artifacts for publication
python -m arancel_mx release --release-dir out/release --source-dir data/raw/release --latest-dir out/latest
```

| Command | Purpose |
|---|---|
| `build` | Export a validated tariff database |
| `update` | Check the official LIGIE ledger; may require network access |
| `reconcile` | Reconcile tariff legal evidence |
| `release` | Verify and prepare publication artifacts |

## Python usage

The package can also be imported from Python:

```python
import arancel_mx

print(arancel_mx.__version__)
```

The public query API will grow as search, classification, and HS / fraction / NICO relationships stabilize. Roadmap functionality is not documented here as already implemented.

## Data model

DuckDB acts as the reproducible analytical representation of the dataset. The model separates classification, description, and provenance so the origin of the data can be reconstructed.

```text
classification
├── HS
├── MX tariff fraction
└── NICO

description
├── text
├── unit
└── rate

provenance
├── authority
├── document
├── URL
├── date
└── hash
```

See [`docs/data-model.md`](docs/data-model.md) for the documented project model.

## Artifacts and reproducibility

The official builder produces this exact contract:

```text
release/
├── arancel_mx.duckdb
├── arancel_mx.csv
├── arancel_mx.json
├── manifest.json
├── SHA256SUMS
└── official-sources.tar.gz
```

`manifest.json` records the dataset version, validation result, source documents, and artifact SHA256 values. `SHA256SUMS` verifies downloaded files, while `official-sources.tar.gz` preserves the captured official evidence used by the build. Logical data is reproducible; each physical DuckDB file is verified against its own SHA256 for that build.

### End-to-end official dataset build

The public orchestrator can build the dataset directly from registered sources:

```bash
python scripts/build_official_dataset.py \
  --work-dir data/embedded/official-build \
  --output-dir out/release \
  --effective-as-of 2026-08-10 \
  --dataset-version 2026.08.10
```

The **Build official dataset** workflow, defined in [`.github/workflows/build-official-dataset.yml`](.github/workflows/build-official-dataset.yml), runs the offline suite first and can then retrieve the registered official sources to produce and verify a GitHub Actions artifact. It supports manual `workflow_dispatch` runs and a weekly schedule.

The workflow **does not create tags or GitHub Releases**. Promoting verified artifacts into a tag and GitHub Release remains a manual, supervised publication decision. See [`docs/release-process.md`](docs/release-process.md) for the complete publication contract.

## Documentation and examples

- docs/: data model, publication process, and source guides
- tests/: fixtures and test cases that protect reproducibility

| Document | Content |
|---|---|
| [`docs/data-model.md`](docs/data-model.md) | Data model |
| [`docs/sources.md`](docs/sources.md) | Sources and provenance |
| [`docs/release-process.md`](docs/release-process.md) | Publication process |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution guide |
| [`SECURITY.md`](SECURITY.md) | Responsible vulnerability reporting |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) | Code of conduct |

## Official sources and registered URLs

The versioned source registry lives in `src/arancel_mx/sources/source_registry.json`. Primary sources:

- Chamber of Deputies - LIGIE reference and current text: https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm
- SNICE - LIGIE index / official publications: https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html
- SNICE - NICO / commercial identifications: https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html
- SNICE - NICO proposals / submissions and requests: https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html
- SNICE - National Notes: https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html
- SNICE - Weighted Indicators: https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html
- Diario Oficial de la Federación (DOF) - related NICO 2022 publication: https://www.dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022

| Source | Main role in the project context |
|---|---|
| Chamber of Deputies | LIGIE reference and text |
| SNICE | LIGIE, NICO, National Notes, indicators, and related publications |
| Diario Oficial de la Federación | Official publications and amendments |

[`src/arancel_mx/sources/source_registry.json`](src/arancel_mx/sources/source_registry.json) is the versioned technical reference for file patterns, URLs, and classification rules. See also [`docs/sources.md`](docs/sources.md).

## Official process and schedule visuals

Authorities publish schedules and procedures related to the receipt, evaluation, and publication of NICO requests and reforms. The following existing images provide documentary context for the publication process.

### Schedule and process, part 1

<p align="center">
  <img alt="DOF publication schedule and deadlines, part 1" src="docs/dof_timeline.png" style="max-width:85%; border-radius:6px; box-shadow:0 6px 20px rgba(0,0,0,0.25)" />
</p>

### Schedule and process, part 2

<p align="center">
  <img alt="DOF publication schedule and deadlines, part 2" src="docs/dof_timeline2.png" style="max-width:85%; border-radius:6px; box-shadow:0 6px 20px rgba(0,0,0,0.25)" />
</p>

<p align="center">
  <em>Source: Diario Oficial de la Federación / SNICE - see the official DOF publication for exact details and dates.</em>
</p>

### NICO / DOF publication flow

<p align="center">
  <img alt="NICO and DOF publication flow" src="docs/nico_flow.png" style="max-width:85%; border-radius:6px; box-shadow:0 6px 20px rgba(0,0,0,0.25)" />
</p>

See `src/arancel_mx/sources/source_registry.json` for file patterns and classification rules. These images provide official-process context and should not be interpreted as a live technical status indicator for the dataset.

## Project status

<p align="center">
  <img src="docs/assets/dataset-status.svg" alt="Public capability status for arancel-mx" width="900" />
</p>

| Component | Documented status |
|---|---|
| XLS / XLSX / PDF parsers | Available |
| Normalization | Available |
| DuckDB | Available |
| CSV / JSON | Available |
| Reconciliation | Available |
| Source registry | Available |
| SHA256 manifests | Available |
| `build`, `update`, `reconcile`, `release` CLI | Available |
| End-to-end official dataset build | Available |
| Verified GitHub Actions artifact | Available |
| CI | Available |
| Public HS / MX / NICO search API | Evolving / roadmap |
| PyPI publication | Planned |

## Roadmap

Planned direction of the public core:

- description search
- code lookup
- HS6 → MX8 tariff fraction → NICO10 navigation
- NICO10 → MX8 tariff fraction → HS6 navigation
- search CLI
- automated detection of official-source changes
- supervised automatic publication to GitHub Releases
- PyPI package publication
- navigable public documentation
- additional query interfaces, potentially including API or MCP access

Roadmap functionality should not be considered part of the stable API until it is implemented, documented, and tested.

## Repository structure

```text
arancel-mx/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── build-official-dataset.yml
├── docs/
│   ├── data-model.md
│   ├── sources.md
│   ├── release-process.md
│   ├── demo.gif
│   ├── dof_timeline.png
│   ├── dof_timeline2.png
│   └── nico_flow.png
├── scripts/
│   └── build_official_dataset.py
├── src/
│   └── arancel_mx/
│       ├── domain/
│       ├── parsers/
│       ├── pipeline/
│       ├── release/
│       ├── sources/
│       └── storage/
├── tests/
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── LICENSE
├── NOTICE
├── pyproject.toml
├── README.en.md
└── README.md
```

- `domain/`: tariff-domain models and rules.
- `parsers/`: XLS, XLSX, and PDF reading/extraction.
- `pipeline/`: normalization, reconciliation, and update flows.
- `sources/`: registry and official-source logic.
- `storage/`: DuckDB persistence and related structures.
- `release/`: construction and verification of publishable artifacts.
- `scripts/`: reproducible entrypoints for building verified datasets.
- `tests/`: fixtures and test cases protecting reproducibility and public-distribution rules.

## Tests

Run the test suite before opening a PR:

```bash
python -m pytest -q
python -m build
```

To reproduce the main CI checks locally:

```bash
python -m pytest -q
python -m build
git diff --check
```

CI uses the same development dependency set installed with:

```bash
python -m pip install -e ".[dev]"
```

## Contribution best practices

1. Open an issue describing the change or bug.
2. Create a descriptive branch such as `feat/add-source-dof`.
3. Add tests and offline fixtures when changing parsers or transformations.
4. Preserve source traceability through capture manifests and hashes.

Avoid adding data or evidence whose provenance cannot be identified, and keep public-core changes focused on Mexican tariff data.

## Contribution / contact

- Read CONTRIBUTING.md and SECURITY.md before submitting PRs.
- Use issues to discuss large changes or new data origins.

## Contributing

Contributions are welcome. Before opening a Pull Request, read [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

For significant changes, open an issue first and use a descriptive branch such as:

```text
feat/add-source-dof
```

## Security

See [`SECURITY.md`](SECURITY.md) for responsible vulnerability reporting.

Do not publish tokens, API keys, session cookies, credentials, secrets, `.env` files, or private keys in commits, fixtures, issues, or Pull Requests.

## License

`arancel-mx` is distributed under the **Apache-2.0** license. See LICENSE and NOTICE for attribution and terms.

- [`LICENSE`](LICENSE)
- [`NOTICE`](NOTICE)

Documents and data obtained from official agencies may be subject to their own applicable provisions and conditions.

## Acknowledgements

Thanks to the teams that publish and maintain the official sources used by this project, including the Chamber of Deputies, SNICE, and Diario Oficial de la Federación, and to the open-source and open-data community for the practices and tooling that make reproducible public-data projects possible.

---

<div align="center">

### arancel-mx

**Open data · verifiable provenance · reproducible releases**

[Español](README.md) · [Documentation](docs/) · [Sources](docs/sources.md) · [Contribute](CONTRIBUTING.md) · [Security](SECURITY.md)

</div>