# PyPI Consumer 0.2.0 Implementation Rollout Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver `arancel-mx 0.2.0` as a consumer-first Python package whose exact wheel/sdist bytes are built once, published to TestPyPI, externally certified, manually approved, then published unchanged to PyPI and externally re-certified.

**Architecture:** Keep the existing official-data ETL/release subsystem intact and add a separate consumer boundary under `src/arancel_mx/consumer/`. Consumer code treats immutable `data-*` GitHub Releases as the dataset distribution channel, stores only verified cache state, opens DuckDB read-only, exposes typed models through `Dataset`, and maps implementation failures into documented public exceptions. Packaging/release automation is split into fast PR/main preflight and tag-only publishing/certification workflows.

**Tech Stack:** Python 3.11-3.14, `argparse`, `requests`, `duckdb`, `platformdirs`, `filelock`, `pytest`, `setuptools`, `build`, `twine`, `check-wheel-contents`, GitHub Actions, TestPyPI/PyPI Trusted Publishing OIDC.

## Global Constraints

- Normative design: `docs/superpowers/specs/2026-08-11-pypi-consumer-distribution-and-external-certification-design.md` plus `docs/superpowers/specs/2026-08-11-pypi-consumer-distribution-design-self-review-addendum.md`.
- Planning baseline: protected `main` commit `ae64617d2c6e9483c2485cffd5d5eed18ca6ed21`.
- Current package metadata baseline: `arancel-mx 0.1.0`, Python `>=3.11`.
- Target production package: `arancel-mx 0.2.0`.
- Package tags: `pkg-v0.2.0rcN` for TestPyPI-only candidates, `pkg-v0.2.0` for the production candidate.
- Dataset tags remain independent: `data-YYYY.MM.DD`.
- Never create a GitHub Release for `pkg-v*`; GitHub `releases/latest` must remain the latest public data release.
- Current verified data baseline for deterministic external-smoke expectations: `data-2026.08.11`, immutable, six release assets.
- The wheel never embeds the large tariff database.
- Public consumer databases are opened read-only.
- Offline mode performs zero network access.
- A failed or partial download never acquires verified-cache state.
- GitHub API asset digests are verified whenever a valid `sha256:<hex>` digest is present; a missing digest is represented explicitly as unavailable and does not count as a successful API-digest check; malformed/present-but-mismatched digests fail closed.
- CLI flags override environment variables; environment variables override defaults.
- Public stable surface for 0.2.x: `Dataset`, `TariffRecord`, `SearchResult`, `ProvenanceRecord`, `DatasetInfo`, documented exceptions, documented method signatures.
- Maintainer commands `build`, `check-updates`, deprecated read-only `update`, `reconcile`, `release` remain available.
- `doctor` exit codes: `0=HEALTHY`, `1=DEGRADED`, `2=UNHEALTHY`.
- Blocking external matrix: Ubuntu x64, Windows x64, macOS ARM64, macOS Intel x CPython 3.11, 3.12, 3.13, 3.14.
- Runner labels verified during planning: `macos-15` is ARM64 and `macos-15-intel` is x64; re-check immediately before workflow implementation.
- TestPyPI/PyPI publishing uses Trusted Publishing/OIDC; `id-token: write` exists only on publishing jobs.
- Production PyPI environment requires manual approval.
- No permanent `PYPI_TOKEN`, `TEST_PYPI_TOKEN`, `.pypirc` password, username/password, or long-lived package credential is introduced.
- External consumer jobs do not checkout repository source and clear `PYTHONPATH` and `PYTHONHOME`.
- Third-party Actions are pinned by full commit SHA.
- Current PyPA publisher action observed during planning: `pypa/gh-action-pypi-publish` release `v1.14.2`, commit `dc37677b2e1c63e2034f94d8a5b11f265b73ba33`; implementation task re-resolves and verifies the exact full SHA before writing the workflow.
- TDD order for every behavior task: failing focused test -> observe expected failure -> minimal implementation -> focused pass -> relevant suite pass -> commit.
- No live TestPyPI/PyPI mutation occurs until all deterministic implementation/preflight plans are complete and green.

---

## Rollout files and responsibility

### Plan A: Consumer core

`docs/superpowers/plans/2026-08-11-pypi-consumer-core.md`

Owns:

- public exceptions and immutable models;
- version source of truth at runtime;
- configuration precedence;
- release discovery and six-asset validation;
- streamed downloads/retries;
- cache layout, file locking, atomic promotion, verified metadata;
- manifest/checksum/API-digest/schema/DuckDB verification;
- `Dataset.latest()`, `Dataset.version()`, `Dataset.open()`;
- lookup, search, hierarchy, provenance;
- offline semantics;
- package-upgrade/cache-reuse deterministic tests.

### Plan B: Consumer CLI and doctor

`docs/superpowers/plans/2026-08-11-pypi-consumer-cli-doctor.md`

Owns:

- `doctor` human/JSON report and exit codes;
- `data status/download/update/list/path/verify` exact semantics;
- `lookup/search/parent/children/provenance` CLI commands;
- deterministic JSON/CSV/table rendering;
- stderr/stdout discipline;
- maintainer-command regression coverage;
- consumer-first README/docs in Spanish and English.

### Plan C: Package quality and PR/main preflight

`docs/superpowers/plans/2026-08-11-pypi-package-preflight.md`

Owns:

- public package metadata, project URLs, classifiers and typing marker;
- `CHANGELOG.md`;
- wheel/sdist package-content contracts;
- `twine check`, `check-wheel-contents`, `pip check`;
- clean wheel/sdist install probes;
- minimum/latest dependency certification;
- Python 3.11-3.14 support evidence;
- Linux edge matrix plus Windows/macOS consumer smoke;
- `.github/workflows/python-package-preflight.yml`;
- atomic update of pinned Action SHAs and their workflow-contract tests.

### Plan D: TestPyPI, external certification and PyPI promotion

`docs/superpowers/plans/2026-08-11-testpypi-pypi-publication.md`

Owns:

- tag/main/version validation;
- build-once wheel/sdist artifact and SHA256 manifest;
- source-free external probe;
- TestPyPI OIDC publication;
- digest-verified TestPyPI roundtrip;
- full 16-cell OS/Python matrix;
- pip/pipx/uv and wheel/sdist modes;
- final manual `pypi` environment approval;
- same-byte PyPI upload;
- post-PyPI matrix;
- package alert/yank/patch response contract;
- manual UI/account prerequisites before first external run.

---

## Locked file map before implementation

### New production files

```text
src/arancel_mx/consumer/__init__.py
src/arancel_mx/consumer/errors.py
src/arancel_mx/consumer/models.py
src/arancel_mx/consumer/config.py
src/arancel_mx/consumer/release_api.py
src/arancel_mx/consumer/http.py
src/arancel_mx/consumer/cache.py
src/arancel_mx/consumer/integrity.py
src/arancel_mx/consumer/query.py
src/arancel_mx/consumer/manager.py
src/arancel_mx/consumer/dataset.py
src/arancel_mx/consumer/doctor.py
src/arancel_mx/consumer/output.py
src/arancel_mx/consumer/cli.py
src/arancel_mx/py.typed
scripts/validate_package_release.py
scripts/external_consumer_probe.py
.github/workflows/python-package-preflight.yml
.github/workflows/publish-python-package.yml
CHANGELOG.md
```

### Existing production files intentionally modified

```text
src/arancel_mx/__init__.py
src/arancel_mx/cli.py
pyproject.toml
README.md
README.en.md
docs/python-api.md
docs/cli.md
docs/getting-started.md
docs/dataset.md
docs/release-process.md
.github/workflows/ci.yml
requirements/production-build.txt
```

`official-data-pipeline.yml`, dataset parsers, legal-source ingestion, reconciliation and the public data schema are not redesigned by this project.

### New deterministic test files

```text
tests/consumer/conftest.py
tests/consumer/test_public_api.py
tests/consumer/test_config.py
tests/consumer/test_release_api.py
tests/consumer/test_http.py
tests/consumer/test_cache.py
tests/consumer/test_integrity.py
tests/consumer/test_query.py
tests/consumer/test_dataset.py
tests/consumer/test_manager.py
tests/consumer/test_offline.py
tests/consumer/test_doctor.py
tests/consumer/test_output.py
tests/consumer/test_cli.py
tests/consumer/test_upgrade_cache.py
tests/consumer/test_faults.py
tests/package/test_metadata.py
tests/package/test_distribution_contents.py
tests/package/test_clean_install.py
tests/package/test_preflight_workflow.py
tests/package/test_publish_workflow.py
tests/package/test_release_validation.py
tests/package/test_external_probe.py
```

Existing regression files retained and extended where ownership is already established:

```text
tests/test_cli.py
tests/test_public_distribution.py
tests/test_dependency_policy.py
tests/test_import_boundaries.py
tests/certification/test_consumer.py
tests/certification/test_package_install.py
tests/certification/test_workflow_contract.py
```

---

## Implementation PR sequence

Each numbered PR is independently reviewable and mergeable only after its own required checks are green.

1. **Consumer types/config boundary**: errors, models, runtime package version, config precedence.
2. **Release resolver**: exact `data-*` discovery, six-asset contract, API digest metadata.
3. **HTTP/cache transaction**: streaming/retry, locking, `.part`, atomic promotion, `verified.json` last.
4. **Integrity gate**: checksums, manifest, API digest, DuckDB structural/release metadata validation.
5. **Query engine + `Dataset`**: lookup/search/parent/children/provenance/connect/open/latest/version.
6. **Offline + manager semantics**: download/update/status/list/path/verify and cache reuse.
7. **Consumer CLI + output**: all user commands and deterministic formats while preserving maintainer commands.
8. **Doctor + support contract**: health states, JSON, secret-redaction, exit codes.
9. **Consumer docs**: Spanish/English onboarding and package-vs-dataset distinction.
10. **Packaging quality**: metadata, `py.typed`, changelog, wheel/sdist inspections, dependency checks.
11. **Cross-platform PR preflight**: Python edge matrix and Windows/macOS smoke.
12. **Release validation/build-once tooling**: tag/main/version checks, digests, external probe.
13. **Publish workflow contract**: TestPyPI -> matrix -> manual PyPI -> post-PyPI architecture, still tested only with deterministic workflow tests.
14. **Release-candidate preparation**: explicit version change to `0.2.0rc1` only after Plans A-C and deterministic Plan D tasks are green.
15. **First live TestPyPI run**: external boundary begins here; no production PyPI action.
16. **Candidate fixes**: any source change produces `0.2.0rc2+`; never overwrite an uploaded candidate.
17. **Final version preparation**: set `project.version = "0.2.0"`, merge green to protected `main`, create `pkg-v0.2.0` at exact green main tip.
18. **Final TestPyPI certification**: exact final bytes pass all blocking gates.
19. **Manual production approval**: approve GitHub `pypi` environment only after final certification.
20. **PyPI + post-PyPI certification**: publish original build bytes and verify exact-version external installs.

---

## Stage gates

### Gate 0: Planning-only baseline

Required before code:

```text
main == ae64617d2c6e9483c2485cffd5d5eed18ca6ed21 at plan creation
design PR merged
design + addendum present
latest data release resolves to immutable data-2026.08.11 at plan creation
planning branch contains docs only
```

If `main` advances before execution, execution begins by rebasing/refreshing the implementation branch and re-running the baseline tests. The plan is not force-applied to a stale tree.

### Gate 1: Deterministic consumer implementation

Run:

```bash
python -m pytest tests/consumer tests/test_cli.py tests/certification/test_consumer.py -q
python -m pytest -q
python -m build
```

Expected: zero failures and successful build. No registry access required.

### Gate 2: Package preflight

Run:

```bash
python -m build
python -m twine check dist/*
check-wheel-contents dist/*.whl
python -m pytest tests/package -q
```

Then PR/main GitHub Actions must prove Linux plus required Windows/macOS smoke jobs.

### Gate 3: Publication workflow deterministic certification

Before a `pkg-v*` tag can be considered usable, tests must prove:

```text
tag regex and version equality
package tag SHA == protected main SHA
mandatory main checks green
build once
artifact digests recorded
TestPyPI before external matrix
external matrix before production approval
production approval before PyPI
RC path cannot reach PyPI
post-PyPI depends on successful PyPI publish
id-token: write only in publisher jobs
no source checkout in external consumer jobs
```

### Gate 4: External testing begins

The first real external step is `0.2.0rc1` publication to **TestPyPI**. Until Gate 3 is green, the project is not described as externally certified.

### Gate 5: Production

`0.2.0` is called production-certified only after exact final TestPyPI bytes pass the full matrix, the human approves `pypi`, the same bytes are published to PyPI, and the post-PyPI matrix passes.

---

## Dependabot PR policy during this rollout

Open Dependabot PRs that change full Action SHAs are not blindly merged because this repository deliberately tests exact workflow pins. A major Action bump must change both the workflow and the contract test in the same reviewed PR.

Current PRs #6 (`setup-python 7`) and #8 (`checkout 7.0.1`) fail because `tests/test_public_distribution.py` still requires the existing full SHAs; that failure is intentional evidence that the workflow contract changed without its policy test. PR #7 (`setup-node 7`) passed its current test surface but remains a major pin change and is deferred to the same atomic action-pin task.

During Plan C, resolve these three PRs as follows:

```text
1. re-verify current upstream Action release and full commit SHA;
2. update every affected workflow in one focused PR;
3. update exact-SHA contract tests in the same commit series;
4. run full CI;
5. close any superseded Dependabot PR instead of merging stale single-pin branches;
6. let Dependabot recreate future updates against the new baseline.
```

This avoids weakening the SHA-pinning security test merely to make Dependabot green.

---

## Completion definition

Do not collapse states. Use exactly this progression in status reporting:

```text
design approved
-> implementation plan approved
-> implementation complete
-> deterministic CI verified
-> TestPyPI configured
-> release candidate externally certified
-> final 0.2.0 TestPyPI externally certified
-> manual production approval
-> PyPI published
-> post-PyPI externally certified
-> 0.2.0 production-certified
```
