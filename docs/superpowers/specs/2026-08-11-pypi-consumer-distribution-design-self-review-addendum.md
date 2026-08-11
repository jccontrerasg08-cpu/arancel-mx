# PyPI Consumer Distribution Design Self-Review Addendum

**Status:** Normative clarification produced by the design self-review  
**Applies to:** `2026-08-11-pypi-consumer-distribution-and-external-certification-design.md`  
**Baseline:** `main` at `23a2dd937d6699e2663245eca0270a11ea34a0aa`

This addendum closes ambiguities found during the required spec self-review. The implementation plan must treat these clarifications as part of the approved design.

## 1. Package tag trust boundary

A `pkg-v*` tag is not sufficient merely because its version matches `pyproject.toml`.

The release workflow must also prove that the tag points to the protected `main` commit intended for release. For 0.2.0 the strict rule is:

1. resolve the tag SHA;
2. resolve `refs/heads/main` at release-workflow start;
3. require the tag SHA to equal that protected `main` SHA;
4. require the commit's mandatory CI/check suite to be successful;
5. fail before TestPyPI if either condition is false.

The release process therefore creates `pkg-v*` only from a green protected `main` tip. A tag on an arbitrary branch, unmerged commit, or stale commit cannot publish.

If `main` advances before the release workflow establishes this equality, the run fails closed and a new version/tag decision is required. The workflow never force-moves or reuses an already published version tag.

## 2. Exact `data` CLI semantics

The 0.2.0 consumer commands mean:

- `data download`: resolve the requested `--dataset` or the newest valid remote `data-*` release, download/verify it if absent, and return the verified local path. It does not delete another cached version.
- `data update`: compare the newest valid remote `data-*` release with locally verified versions; download/verify the newer release when one exists; otherwise report `no_change`. It never rewrites a verified older version.
- `data status`: report selected/default dataset, newest locally verified version, online/offline mode, cache health, and whether a newer valid remote release is known when network access is allowed.
- `data list`: list locally verified dataset versions by default. `data list --remote` lists valid public `data-*` releases without downloading their DuckDB assets.
- `data path`: print only the selected verified DuckDB path on stdout for scripting, with diagnostic errors on stderr.
- `data verify`: revalidate the selected local cached dataset against its stored release metadata, manifest, SHA256 information, schema, and DuckDB contract without network by default. `--online` may refresh/compare remote release metadata. `--bundle` explicitly downloads/verifies the full six-asset public release.

These semantics are covered by CLI contract tests and documented examples.

## 3. Local `Dataset.open()` integrity semantics

`Dataset.open(path)` opens the supplied DuckDB read-only and validates the required public schema/relations before returning a usable `Dataset`.

A bare DuckDB path alone cannot prove GitHub-release provenance. Therefore:

- local schema validation is mandatory;
- no false claim of SHA256/release provenance is made when companion metadata is absent;
- a `Dataset` opened from the managed verified cache retains its verified release identity;
- user-supplied standalone files expose their integrity/provenance status through `DatasetInfo`.

Cryptographic/release verification and structural DuckDB validation are distinct states in the public model.

## 4. `doctor` exit-code contract

`doctor` machine behavior is fixed:

```text
0 = HEALTHY
1 = DEGRADED
2 = UNHEALTHY
```

`DEGRADED` is reserved for cases where core local usage is valid but a non-core capability is unavailable, for example network access while a fully verified offline cache remains usable.

`doctor --json` emits the same status and numeric exit semantics.

## 5. Release-asset digest anchoring

For GitHub releases whose API metadata exposes an asset `digest` in `sha256:<hex>` form, every downloaded consumer asset must match that digest.

For the normal three-file cache transaction this means independently hashing:

```text
manifest.json
SHA256SUMS
arancel_mx.duckdb
```

The DuckDB must additionally match the checksum recorded by the release checksum contract. Digest checks are layered rather than substituted for one another.

If the expected GitHub API digest is present but malformed or mismatched, the transaction fails with `DatasetIntegrityError`.

The implementation plan must define explicit compatibility behavior if GitHub stops returning the digest field. It may not silently reinterpret a missing field as a successful digest check.

## 6. Consumer matrix without source checkout

External TestPyPI/PyPI certification jobs must not have the repository source tree available on `sys.path` or as the working implementation source.

The approved mechanism is:

1. build job creates the package distributions and a small standalone consumer-probe script/artifact;
2. external matrix jobs download only the distribution metadata/digests and the standalone probe, not the repository checkout;
3. the probe imports only the installed `arancel_mx` package and standard test helpers;
4. jobs use a temporary HOME/cache directory and clear `PYTHONPATH`/`PYTHONHOME`;
5. consumer commands execute from a fresh temporary working directory.

This keeps certification reproducible while proving that no local `src/arancel_mx` checkout can make a broken distribution appear healthy.

## 7. Self-review result

After these clarifications:

- no `TBD`/`TODO` placeholders remain in the design;
- code/data release namespaces are internally consistent;
- the TestPyPI -> matrix -> manual PyPI gate is fail-closed;
- package-tag origin is explicitly constrained to protected green `main`;
- CLI data-command behavior is unambiguous;
- local structural validation is separated from cryptographic release provenance;
- diagnostics have deterministic exit semantics;
- external certification cannot accidentally import repository source.

The combined design and this addendum are ready for final user review before implementation planning.
