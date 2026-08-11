# Public dataset

A valid `arancel-mx` release contains exactly six assets:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

Do not count the source-code archives that GitHub automatically adds to each release.

## Levels

Canonical records are organized as:

```text
hs2
hs4
hs6
fraccion8
nico10
```

Descriptive HS rows do not receive artificially inherited tariff rates. Rates belong only to the levels and validity periods supported by evidence.

## CSV

`arancel_mx.csv` is convenient for pandas, R, spreadsheets, and ETL loading. Codes should be treated as text so leading zeroes are preserved.

```python
import pandas as pd

df = pd.read_csv("arancel_mx.csv", dtype={"code": "string"})
print(df.groupby("level").size())
```

## JSON

`arancel_mx.json` represents the same public logical records and is useful for consumers that prefer objects/documents.

## DuckDB

`arancel_mx.duckdb` is the distributable analytical materialization. The public `arancel_mx` view supports queries such as:

```sql
SELECT level, COUNT(*)
FROM arancel_mx
GROUP BY level
ORDER BY level;
```

The public DuckDB is not the complete operational warehouse. See [`data-model.md`](data-model.md).

## Manifest, checksums, and sources

- `manifest.json` fixes the version, counts, provenance, and build metadata.
- `SHA256SUMS` verifies the other five assets.
- `official-sources.tar.gz` preserves captured official bytes and `source_capture.json` for auditability.

Read [`verify-release.md`](verify-release.md) before integrating a release into another system.
