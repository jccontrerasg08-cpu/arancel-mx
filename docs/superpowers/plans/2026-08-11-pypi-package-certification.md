# PyPI Package Certification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:test-driven-development` for behavior and contract changes, and `superpowers:verification-before-completion` before claiming package readiness.

**Goal:** Turn the current installable engineering package into a production-grade distributable whose wheel and sdist are independently validated across the claimed Python/OS matrix before any live registry publication.

**Architecture:** Preserve the current `src/` package layout and existing data-pipeline workflows. Add packaging-specific metadata, tests, a clean-install probe, and a dedicated PR/main package-preflight workflow. Keep the existing required `CI / test` check until branch rules are intentionally migrated. Supply-chain tests verify that Actions are pinned by full SHA and approved by action identity, but do not hardcode an obsolete prior SHA in a way that makes legitimate Dependabot upgrades fail automatically.

**Depends on:** consumer core and CLI/doctor plans implemented and green.

## Global constraints

- Target distribution: `arancel-mx 0.2.0`.
- `pyproject.toml` remains the single package-version source.
- Runtime `__version__` comes from `importlib.metadata.version("arancel-mx")`.
- Wheel does not embed the large DuckDB dataset.
- Wheel/sdist must contain required source registry and `py.typed` only when typing contract is actually valid.
- Supported Python claims are proven, not aspirational.
- Blocking release matrix: Ubuntu x64, Windows x64, macOS ARM64, macOS Intel x Python 3.11-3.14.
- PR/main preflight may use a reduced matrix but must include Linux edge versions plus Windows and macOS consumer smoke.
- Existing DuckDB 1.1.0 compatibility probe remains mandatory.
- Every third-party Action reference in production workflows uses a full 40-character commit SHA.
- Deterministic packaging tests do not publish to TestPyPI or PyPI.

---

### Task 1: Single package-version source of truth

**Files:**
- Modify: `src/arancel_mx/__init__.py`
- Create: `tests/package/test_version.py`

**First red tests:**
- `test_runtime_version_matches_installed_distribution_metadata()`
- `test_init_has_no_literal_duplicate_project_version()`
- `test_public_exports_include_dataset_and_version_only_as_documented()`

**Implementation:**
- Replace literal `__version__ = "0.1.0"` with `importlib.metadata.version("arancel-mx")` and a narrowly scoped editable/source-tree fallback only if necessary for tests.
- Do not create a second version file.

**Verify:**
```bash
python -m pytest tests/package/test_version.py -q
```

**Commit:** `refactor: derive package version from distribution metadata`

---

### Task 2: Complete PyPI metadata without overstating support

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/package/test_metadata.py`

**First red tests:**
- `test_project_has_public_urls_and_keywords()`
- `test_project_license_metadata_is_valid()`
- `test_python_classifiers_match_certified_range()`
- `test_console_script_points_to_public_cli_entrypoint()`
- `test_distribution_does_not_claim_embedded_dataset()`

**Implementation metadata:**
- description adjusted to consumer + engineering toolkit;
- authors/maintainers using public project identity;
- keywords for Mexico tariff/TIGIE/NICO/HS/DuckDB;
- project URLs: Repository, Issues, Documentation, Changelog, Data Releases;
- Development Status classifier appropriate for 0.x;
- Python classifiers only after corresponding CI cells are green;
- OS Independent classifier if appropriate;
- Apache-2.0 SPDX/license-files preserved.

**Verify:**
```bash
python -m pytest tests/package/test_metadata.py -q
python -m build
```

**Commit:** `build: complete public package metadata`

---

### Task 3: Split runtime consumer dependencies from maintainer-heavy dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements/production-build.txt` if required by repository policy
- Create: `tests/package/test_dependencies.py`
- Modify: `tests/test_dependency_policy.py`

**Design decision to implement:** the installed consumer package should not force users to install ETL-only dependencies unless runtime import boundaries still require them.

**First red tests:**
- `test_import_arancel_mx_does_not_import_pandas_openpyxl_pymupdf_xlrd()`
- `test_consumer_commands_work_with_consumer_runtime_dependencies_only()`
- `test_maintainer_extra_contains_build_pipeline_dependencies()`
- `test_pip_check_passes_consumer_install()`

**Implementation:**
- Consumer runtime likely includes `duckdb`, `requests`, `platformdirs`, `filelock`.
- Move `pandas`, `openpyxl`, `PyMuPDF`, `xlrd` to a documented maintainer/build optional extra only after import-boundary tests prove maintainer commands still work when extra installed.
- Preserve backwards compatibility for contributors through `.[dev]` including maintainer dependencies.

**Verify:**
```bash
python -m pytest tests/package/test_dependencies.py tests/test_dependency_policy.py tests/test_import_boundaries.py -q
```

**Commit:** `build: separate consumer and maintainer dependencies`

---

### Task 4: PEP 561 marker and public typing contract

**Files:**
- Create: `src/arancel_mx/py.typed`
- Create: `tests/package/test_typing_marker.py`
- Add annotations in public consumer modules as needed from core plan.

**First red tests:**
- `test_py_typed_is_present_in_built_wheel()`
- `test_public_models_and_dataset_signatures_have_annotations()`

**Implementation:**
- Ship `py.typed` only after public modules are sufficiently annotated.

**Verify:**
```bash
python -m build
python -m pytest tests/package/test_typing_marker.py -q
```

**Commit:** `feat: mark consumer API as typed`

---

### Task 5: Changelog and package documentation files

**Files:**
- Create: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `README.en.md`
- Create or modify: `docs/package-release.md`
- Create: `tests/package/test_readme_metadata.py`

**First red tests:**
- `test_readme_contains_pip_install_and_first_query()`
- `test_readme_distinguishes_package_and_dataset_versions()`
- `test_changelog_has_020_section()`

**Implementation:**
- Document that installation does not include the full dataset.
- Link latest dataset releases separately.
- Include Python API and CLI first-use examples.

**Verify:**
```bash
python -m pytest tests/package/test_readme_metadata.py -q
```

**Commit:** `docs: prepare PyPI consumer documentation`

---

### Task 6: Build-content contract for wheel and sdist

**Files:**
- Create: `tests/package/test_distribution_contents.py`
- Modify: `tests/test_public_distribution.py`
- Modify: `MANIFEST.in` only if needed

**First red tests:**
- wheel includes consumer modules, `source_registry.json`, licenses, `py.typed`;
- wheel excludes repo-private data, `.git`, tests, source documents, release DuckDB/CSV/JSON;
- sdist contains source/package metadata needed for isolated rebuild;
- no personal absolute paths or credential-like files.

**Implementation:**
- Prefer setuptools configuration over ad-hoc packaging scripts.

**Verify:**
```bash
rm -rf dist build
python -m build
python -m pytest tests/package/test_distribution_contents.py tests/test_public_distribution.py -q
```

**Commit:** `test: harden wheel and sdist content contract`

---

### Task 7: Add packaging quality tools to dev/release tooling

**Files:**
- Modify: `pyproject.toml` dev optional dependencies or dedicated release extra
- Modify: `requirements/production-build.txt` according to pinning policy
- Create: `tests/package/test_build_tools_policy.py`

**Required tools:**
- `build`
- `twine`
- `check-wheel-contents`

**First red tests:**
- repository policy pins/controls build tools as expected;
- `twine check dist/*` is present in preflight contract;
- `check-wheel-contents` is present in preflight contract.

**Verify:**
```bash
python -m build
twine check dist/*
check-wheel-contents dist/*.whl
```

**Commit:** `build: add distribution validation tooling`

---

### Task 8: Standalone installed-package consumer probe

**Files:**
- Create: `scripts/package_consumer_probe.py`
- Create: `tests/package/test_consumer_probe.py`

**Probe contract:**
- imports only installed `arancel_mx` + standard library;
- prints structured JSON result;
- verifies package version;
- checks `arancel-mx --help` indirectly only where safe or provides import/API smoke;
- can run against a supplied verified dataset/cache;
- no repo imports.

**First red tests:**
- probe fails when package import resolves to checkout path;
- probe succeeds from a fresh working directory with wheel-installed package;
- probe reports version mismatch explicitly.

**Verify:**
```bash
python -m pytest tests/package/test_consumer_probe.py -q
```

**Commit:** `test: add standalone external consumer probe`

---

### Task 9: Clean wheel install outside checkout

**Files:**
- Modify: `tests/certification/test_package_install.py`
- Create: `scripts/certify_local_distribution.py` if orchestration is needed

**Required scenarios:**
- fresh venv;
- clear `PYTHONPATH`/`PYTHONHOME`;
- working directory outside repo;
- install wheel;
- `pip check`;
- import/version;
- console help;
- module help;
- packaged resource check;
- deterministic local consumer fixture query.

**Verify:**
```bash
python -m pytest tests/certification/test_package_install.py -q
```

**Commit:** `test: certify clean wheel installation`

---

### Task 10: Clean sdist rebuild/install outside checkout

**Files:**
- Extend: `tests/certification/test_package_install.py`
- Create: `tests/package/test_sdist_rebuild.py`

**First red tests:**
- sdist can build a wheel in isolated environment;
- rebuilt wheel passes same installed probe;
- no files are sourced from original checkout during build.

**Verify:**
```bash
python -m pytest tests/package/test_sdist_rebuild.py tests/certification/test_package_install.py -q
```

**Commit:** `test: certify isolated sdist rebuild and install`

---

### Task 11: Dependency-floor and latest dependency certification

**Files:**
- Create: `tests/package/test_dependency_compatibility.py`
- Modify: existing DuckDB compatibility fixture/workflow as needed without removing it.

**Required:**
- `duckdb==1.1.0` floor probe;
- latest allowed DuckDB probe;
- latest allowed runtime dependencies install;
- `pip check` after each environment.

**Verify:**
```bash
python -m pytest tests/package/test_dependency_compatibility.py -q
```

**Commit:** `test: certify runtime dependency floor and latest ranges`

---

### Task 12: Refactor Action SHA policy so upgrades are reviewable, not self-conflicting

**Files:**
- Modify: `tests/test_public_distribution.py`
- Modify: `tests/certification/test_workflow_contract.py`
- Create: `tests/package/test_action_pinning.py`

**Reason:** Dependabot PRs #6 and #8 demonstrated that tests currently hardcode the previous approved SHA. A legitimate PR changes the workflow SHA, then CI fails solely because the test still requires the old SHA. This is not useful release validation.

**First red tests:**
- `test_every_third_party_action_is_pinned_to_full_sha()`
- `test_only_approved_action_repositories_are_used()`
- `test_workflows_do_not_use_floating_v_tags()`
- `test_publish_workflow_has_id_token_only_on_publish_jobs()` later from publication plan.

**Implementation:**
- Assert full 40-hex SHA syntax and expected action identity.
- Keep exact SHA review in the PR diff and release implementation checklist.
- Do not silently permit arbitrary third-party action names.

**Verify:**
```bash
python -m pytest tests/package/test_action_pinning.py tests/test_public_distribution.py tests/certification/test_workflow_contract.py -q
```

**Commit:** `test: make action pinning policy upgrade-safe`

---

### Task 13: Dedicated package preflight workflow

**Files:**
- Create: `.github/workflows/python-package-preflight.yml`
- Create: `tests/package/test_preflight_workflow.py`
- Keep: `.github/workflows/ci.yml` and required `test` check.

**Workflow permissions:**
```yaml
permissions:
  contents: read
```

**No:** `id-token: write`, registry upload, secrets, package tags, `pull_request_target`.

**Jobs:**
1. Linux package quality on Python 3.11 and 3.14.
2. Windows x64 smoke on representative Python version(s).
3. macOS ARM64 smoke.
4. macOS Intel smoke.
5. distribution content/metadata checks.
6. DuckDB floor compatibility may remain in existing CI if already authoritative.

**Commands include:**
```bash
python -m pytest ...
python -m build
twine check dist/*
check-wheel-contents dist/*.whl
python scripts/package_consumer_probe.py ...
```

**First red contract tests:** triggers, permissions, runner labels, no registry mutation, full-SHA Actions.

**Commit:** `ci: add cross-platform Python package preflight`

---

### Task 14: Verify Python 3.11-3.14 dependency availability before advertising

**Files:**
- Modify: `pyproject.toml` classifiers only after evidence.
- Create: `docs/package-support-matrix.md`
- Create: `tests/package/test_support_matrix_docs.py`

**Procedure:**
- Run preflight across 3.11-3.14 where feasible.
- If a runtime dependency cannot install on a claimed interpreter, fix dependency range or narrow `requires-python` before publication.
- Never leave docs/classifiers claiming a failed interpreter.

**Commit:** `docs: record certified package support matrix`

---

### Task 15: Local release-candidate preflight command/documentation

**Files:**
- Create: `scripts/package_preflight.py`
- Create: `tests/package/test_package_preflight_script.py`
- Modify: `docs/package-release.md`

**Script runs deterministic local checks only:** version consistency, build, hashes, twine check, wheel contents, clean wheel install, clean sdist rebuild, consumer probe.

It must not publish or require credentials.

**Verify:**
```bash
python scripts/package_preflight.py
```

**Commit:** `build: add deterministic package preflight command`

## Completion gate

This subplan is complete only when all of the following are green on a PR without any live registry mutation:

```bash
python -m pytest tests/package tests/certification/test_package_install.py -q
python -m build
twine check dist/*
check-wheel-contents dist/*.whl
python scripts/package_preflight.py
```

and the new package-preflight workflow passes its Linux/Windows/macOS jobs while the existing required `CI / test` check also remains green.