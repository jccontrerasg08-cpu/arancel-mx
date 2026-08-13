# Audit deletions

Date: 2026-08-13  
Repo: arancel-mx  
Status: draft spec (not implemented)

## Goal

Remove unused code and orphan files that have no production callers. Do not change official capture, materialize, compare, or `data-*` release shape. National-notes parsers stay; wiring them into `data-*` is a later spec.

## Sequence

1. This spec, two PRs (approach C).
2. Later spec: publish LIGIE national notes in `data-*` (pipeline-only).
3. Run-length encoding: out of scope. `itertools.groupby` already encodes runs; this is not an algorithms catalog.

## Keep (both PRs)

- Empty public `nico_proposal*` / `weighted_*` / `national_note*` tables and views
- `source_registry.json` keys (including unused sources; they affect `registry_sha256`)
- `parse_national_notes_html`, `_insert_national_notes`, `parse_indicator_workbook`
- CLI lazy maintainer wrappers and `build_release`
- SIICEX/VUCEM parsers; `normalize_duty` / `descriptions_consistent` / `description_tokens`
- `filelock`; bilingual READMEs; OSS checklist paste block
- `docs/demo.gif`; URL-check retry loops in `scripts/check_documented_urls.py`
- `docs/package-release.md` and `docs/production-certification.md` body (except PR2)

## PR1 — dead code and orphans

No edits to `pyproject.toml` dependencies, `requirements/production-build.txt`, `docs/package-release.md`, or `docs/production-certification.md`.

### Delete files

- `src/arancel_mx/domain/models.py`
- `src/arancel_mx/sources/snice.py`
- `tests/domain/test_staging.py`
- `tests/sources/test_snice.py`
- `tests/test_demo_workflow.py`
- `scripts/current_resolver_probe.py`
- `tests/package/test_current_resolver.py`
- `tools/generate_demo.py` and the `tools/` directory (it has no other files)
- `.github/workflows/generate-demo.yml`
- `docs/demo.svg`
- `docs/arancel-mx.md`
- `tests/fixtures/siicex/TarifaW.OpenView.html`

### Edit

- `domain/normalization.py`: drop `_staging_json` through `_insert_promoted_rows` (`stage_rows` / `validate_staging` / `promote_staging` and staging-only helpers). Keep `consolidate_records` and everything the official build uses.
- `domain/__init__.py`: drop staging and model exports.
- `storage/duckdb.py`: drop DDL for `source_registry`, `source_discovery_run`, `source_discovery_item`, `source_capture`, `staging_arancel_row`, `arancel_quarantine` only. Keep `source_document` onward, `ensure_tariff_schema`, `init_tariff_db`. Do not touch `source_registry.json` or release `source_capture.json`.
- `sources/classifier_consistency.py`: drop `REFERENCE_FRACTION_CODE`, `ClassifierRecord`, `classifier_record_from_*`, `compare_classifier_records`, `compare_vucem_and_siicex_fractions`. Keep duty/description helpers. Drop unused SIICEX/VUCEM imports.
- `sources/capture.py`: drop `can_reuse_parse` only.
- `sources/__init__.py`: drop `can_reuse_parse`, `DownloadTask`, `discover_snice_documents`.
- `certification/reports.py` + `bundle.py`: drop `CertificationReport.passed`. Failures already raise `ValueError`; a returned report is success.
- `scripts/publish_release.py` and `.github/workflows/official-data-pipeline.yml`: drop `if not report.passed` (dead after raise-on-failure). Keep the `except` that maps `certify_bundle` errors to fail-closed publication failure.
- `consumer/compare.py`: remove `_DatasetView` Protocol; duck-type `dataset` (or `Dataset` under `TYPE_CHECKING` only).
- `tests/package/test_dependency_compatibility.py`: in `--mode latest`, assert `pandas` / `openpyxl` / `pymupdf` / `xlrd` are absent from resolved packages.
- `tests/sources/test_classifier_consistency.py`: drop the two compare-adapter tests; keep SIICEX parse, `normalize_duty`, `descriptions_consistent`.
- `tests/sources/test_capture.py`: drop `can_reuse_parse` import and `test_parse_reuse_requires_the_complete_identity`.
- `tests/certification/test_bundle.py` and `tests/automation/test_publish_release.py`: stop asserting/mocking `passed`.
- `README.md` / `README.en.md`: remove `generate-demo.yml` from the tree and the security-section bullet that demo automation opens a PR. Keep `docs/demo.gif`.
- `tests/test_workflow_hardening.py`: set `CHECKOUTS_KEEPING_CREDENTIALS` to `frozenset()` so a new credential-keeping checkout still fails.
- `docs/operations/github-settings.md`: remove generate-demo permission line and the sentence that the demo workflow may create a PR.

### Tests that die with the code

Whole files: `test_staging.py`, `test_snice.py`, `test_demo_workflow.py`, `test_current_resolver.py`.

### Behavior that must not change

Official pipeline still uses `discover_registered_sources` / `capture_document` / `materialize_arancel`. Consumer `compare` still uses `normalize_duty` and `descriptions_consistent`. `certify_bundle` still fail-closes by raising. Public DuckDB still drops non-`PUBLIC_INTERNAL_TABLES` tables.

### Coverage

Do not lower `fail_under` in `pyproject.toml` unless CI proves a drop caused only by deleted lines. Prefer leaving the threshold.

## PR2 — docs shrink and test-only deps

After PR1 is green on `main` (or stacked on PR1).

- Shrink `docs/package-release.md`: drop consumer install/CLI/API tour and nested six-asset tree; link `docs/consumer-cli.md`, `docs/external-consumption.md`, `docs/release-process.md`. Keep pkg-v* / build-once / release-gates. Retarget `tests/package/test_readme_metadata.py` / distribution tests if they require deleted sentences; do not delete the file (`MANIFEST.in` ships it).
- Shrink `docs/production-certification.md`: drop package-smoke / public-bundle / routine-verification tours; link `docs/release-process.md`. Keep baseline, boundaries, lifecycle, recovery. Update `assert report.passed` to match PR1 (`certify_bundle` success is a returned report, not `.passed`).
- Drop `reportlab` and `PyYAML` from `pyproject.toml` / `requirements/production-build.txt` / dependency-contract tests. Commit small parseable PDF fixtures for `tests/parsers/test_documents.py` and `tests/pipeline/test_official_dataset.py`. Assert workflow YAML with text/regex like other contract tests; handle YAML 1.1 bare `on:` without PyYAML.

## Error handling

Deletions must not weaken fail-closed publication: `certify_bundle` raises on the first failure; publishers already catch that. Removing `.passed` must not add a path that publishes after a failed certification.

## Success

PR1: `pytest` green with `ARANCEL_MX_SKIP_URL_CHECKS=1`; no remaining imports of deleted symbols; `docs/demo.gif` still referenced from READMEs.

PR2: same tests green without `reportlab`/`PyYAML` installed in the test extra.

## Out of scope

National-notes `data-*` wiring, GIR/IVA/NOM/T-MEC, merging `consumer/http.py` with `sources/http.py`, RLE, lowering Python versions, changing `registry_sha256` by editing registry JSON.
