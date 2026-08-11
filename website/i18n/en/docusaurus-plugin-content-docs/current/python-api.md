# Python API

The public Python API is intentionally limited during the `0.x` series.

The minimum guaranteed surface today is that the package imports and reports its version:

```python
import arancel_mx

print(arancel_mx.__version__)
```

The CLI can also be invoked with:

```bash
python -m arancel_mx --help
```

## What is not promised yet

A stable search, automatic-classification, or programmatic HS6 ↔ MX8 ↔ NICO10 navigation API is not currently promised. Those capabilities remain subject to change until public interfaces, compatibility tests, and dedicated documentation exist.

For analytical consumption today, the CSV/JSON/DuckDB artifacts are a more appropriate contract than importing internal `pipeline`, `sources`, `storage`, or `release` modules.

Internal modules may change during `0.x` even when they are visible in the source tree.
