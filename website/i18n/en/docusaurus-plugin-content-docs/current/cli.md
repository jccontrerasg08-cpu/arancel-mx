# CLI

The public CLI is exposed as both `arancel-mx` and `python -m arancel_mx`. During the 0.x series, the stable command contract is deliberately small.

```bash
python -m arancel_mx --help
```

## `build`

Exports artifacts from an already validated DuckDB database:

```bash
python -m arancel_mx build \
  --database data/arancel.duckdb \
  --output-dir out/release
```

It does not replace source capture or legal reconciliation in the official pipeline.

## `check-updates`

Checks registered official-ledger state without silently accepting a new state:

```bash
python -m arancel_mx check-updates \
  --state-path data/update_state/ligie.json \
  --report-path out/update.json
```

It optionally accepts `--ledger-url`. `update` remains only a deprecated read-only alias during 0.x.

## `reconcile`

Reconciles observed legal evidence:

```bash
python -m arancel_mx reconcile \
  --ledger-json ledger.json \
  --dof-json dof.json \
  --snice-json snice.json
```

A material discrepancy must be resolved before a candidate can be considered publishable.

## `release`

Verifies hashes and prepares the local publication contract:

```bash
python -m arancel_mx release \
  --release-dir out/release \
  --source-dir data/raw/release \
  --latest-dir out/latest
```

Actual automatic publication only occurs through the production workflow and its gates.

## Exit codes

The CLI returns `0` for an accepted execution. Invalid input, missing files, invalid JSON, handled HTTP errors, and domain-validation failures return `2` with an error message on stderr.
