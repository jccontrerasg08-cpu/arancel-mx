# Consumer CLI

`arancel-mx` exposes a consumer-first command line for downloading, verifying, querying, and diagnosing published Mexican tariff datasets without cloning the repository.

> The consumer CLI is implemented in the package now. The `pip install arancel-mx` command below is the public installation path once the distribution is published to PyPI. Until that publication happens, contributors should use the editable development install documented in the README.

## Install and first run

Python 3.11 or newer is required.

```bash
pip install arancel-mx
arancel-mx --version
arancel-mx doctor
arancel-mx data download
arancel-mx lookup 01012101
arancel-mx search "refrigeradores"
arancel-mx data verify
```

`data download` resolves one exact public `data-YYYY.MM.DD` release, downloads its required assets, verifies integrity, and only then promotes the dataset into the local cache. A failed or partial download is not promoted as usable data.

## Package version and dataset version

The package version and dataset version are independent identifiers.

- **package version**: the Python distribution and CLI implementation, reported by `arancel-mx --version`, for example `0.1.0`.
- **dataset version**: an immutable public tariff-data release named `data-YYYY.MM.DD`, for example `data-2026.08.11`.

Updating the Python package does not silently replace a pinned dataset version. Publishing a new dataset release does not require changing the package version.

To select an exact data release instead of the default latest selection:

```bash
arancel-mx data download --dataset data-YYYY.MM.DD
arancel-mx lookup 01012101 --dataset data-YYYY.MM.DD
arancel-mx data verify --dataset data-YYYY.MM.DD
```

The same pin can be supplied through `ARANCEL_MX_DATASET`.

## Offline use

After a dataset has been downloaded and verified, query commands can operate without network access:

```bash
arancel-mx lookup 01012101 --offline
arancel-mx search "refrigeradores" --offline
arancel-mx data status --offline --format json
arancel-mx data verify --offline --format json
arancel-mx doctor --offline --json
```

Offline mode is strict. It uses verified local data only and does not fall back to a network request. If the requested dataset is unavailable or fails local verification, the command fails instead of downloading another release.

Offline mode can also be enabled for a process or shell with `ARANCEL_MX_OFFLINE=1`.

## Machine-readable output

Query and data commands support deterministic table, JSON, and CSV output where applicable.

```bash
arancel-mx lookup 01012101 --format json
arancel-mx search "refrigeradores" --format csv
arancel-mx data status --format json
arancel-mx data list --format csv
arancel-mx data verify --format json
```

Use `--format json` for structured automation and `--format csv` for row-oriented interchange. `data path` intentionally prints only the selected local DuckDB path so it can be consumed directly by scripts.

## Query commands

```bash
arancel-mx lookup 01012101
arancel-mx search "refrigeradores" --limit 20
arancel-mx parent 01012101
arancel-mx children 010121
arancel-mx provenance 01012101
```

- `lookup` resolves an exact normalized tariff code.
- `search` ranks current records by code or description.
- `parent` returns the direct parent in the HS2 → HS4 → HS6 → MX8 → NICO10 hierarchy.
- `children` returns direct children of a code.
- `provenance` returns the recorded source traceability for the selected code.

The same normalization and query semantics are shared by the public Python consumer layer and CLI.

## Dataset lifecycle commands

```bash
arancel-mx data status
arancel-mx data list
arancel-mx data list --remote
arancel-mx data download
arancel-mx data update
arancel-mx data path
arancel-mx data verify
arancel-mx data verify --online
arancel-mx data verify --bundle
```

`data update` is idempotent when the newest valid release is already cached and it does not delete older verified versions. `data verify` is local by default. `--online` compares the cached metadata with the exact remote release. `--bundle` temporarily verifies the complete six-asset public release contract.

## Doctor

Run diagnostics after installation or when a dataset cannot be queried:

```bash
arancel-mx doctor
arancel-mx doctor --json
```

`doctor` checks distribution metadata, the console entrypoint, Python/platform information, the packaged source registry, cache writability, local dataset verification, read-only DuckDB access, an actual query, offline readiness, and public release metadata when network access is enabled.

The process exit contract is stable:

| Status | Exit code | Meaning |
|---|---:|---|
| `HEALTHY` | 0 | Required local checks passed and no warning condition was detected |
| `DEGRADED` | 1 | Local use remains viable but a non-fatal condition, such as unavailable remote metadata, was detected |
| `UNHEALTHY` | 2 | A required installation, cache, integrity, or query check failed |

`arancel-mx doctor --json` emits the same diagnostic model as the human-readable output, with the same exit-code mapping.

## Environment variables

Explicit CLI or API arguments take precedence over environment variables, which take precedence over defaults.

| Variable | Purpose |
|---|---|
| `ARANCEL_MX_CACHE_DIR` | Override the cross-platform user cache directory |
| `ARANCEL_MX_DATASET` | Pin an exact `data-YYYY.MM.DD` release |
| `ARANCEL_MX_OFFLINE` | Enable strict offline mode with `1`, `true`, `yes`, or `on` |
| `ARANCEL_MX_TIMEOUT` | Set the positive HTTP timeout in seconds |

Invalid consumer configuration fails with an actionable public error instead of being treated as an integrity failure.

## Integrity and cache guarantees

The consumer flow is fail-closed:

1. Resolve one exact public data release.
2. Download to temporary state.
3. Verify the required asset set, SHA256 values, manifest contract, and DuckDB structure.
4. Promote the verified version into the cache atomically.
5. Open the selected DuckDB read-only for queries.

Concurrent downloads are serialized with a file lock. Existing verified versions remain available, and a corrupt or incomplete candidate is not silently substituted for another dataset.

For the publication-side six-asset contract and attestations, see [`release-process.md`](release-process.md). For the canonical database schema, see [`data-model.md`](data-model.md).

> `arancel-mx` is a technical data tool and does not constitute legal advice. Consult the applicable official publications and qualified professionals for tariff-classification or compliance decisions.
