# Reproducibility

The project distinguishes consumer compatibility from production reproducibility.

## Dependencies

`pyproject.toml` uses compatible ranges so every consumer is not forced into an identical environment:

```text
duckdb>=1.1
pandas>=2.0
...
```

Official builds and CI use `requirements/production-build.txt`, where the complete environment is pinned to exact versions.

```bash
python -m pip install pip==26.2.1
python -m pip install -c requirements/production-build.txt -e ".[dev]"
```

The rule is:

```text
consumer compatibility -> ranges
production reproducibility -> exact pins
```

## Logical determinism

CSV, JSON, and DuckDB must represent the same public logical records. Text artifacts that are part of the deterministic contract are compared by content/hash when appropriate.

A physical DuckDB file is not necessarily promised to be byte-identical across independent builds. Its logical contents and minimum compatibility boundary are tested separately.

## No-op behavior

If registered source identity did not change relative to the latest release, the correct result is `no_change`. The pipeline does not create a redundant daily release.

## Supply chain

External workflow actions are pinned to full commit SHAs, production installation uses reviewed exact pins, and published assets are verified before and after the GitHub Release mutation. See [`release-process.md`](release-process.md) and [`verify-release.md`](verify-release.md).
