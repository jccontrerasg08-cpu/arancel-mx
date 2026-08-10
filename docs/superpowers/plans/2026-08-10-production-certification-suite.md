# Production Certification Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that `arancel-mx` is installable, consumable, reproducible, fail-closed, and operationally safe through deterministic certification tests plus controlled live GitHub write-boundary checks.

**Architecture:** Add a certification layer around the existing package and six-asset release contract instead of creating a second ETL path. Read-only certification logic lives under `src/arancel_mx/certification/`, workflow-only GitHub mutation helpers live under `scripts/`, and a dedicated manual workflow exercises temporary draft-release and issue mutations using namespaces that can never collide with production `data-*` releases or `[DATA ALERT]` issues.

**Tech Stack:** Python 3.11+, pytest, build, DuckDB, GitHub Actions, GitHub REST API through the existing `scripts.github_api.GitHubApi`, SHA-256, tarfile, tempfile/venv/subprocess from the Python standard library.

## Global Constraints

- Keep Python `>=3.11` as the package floor.
- Do not weaken fail-closed legal reconciliation.
- Do not publish certification releases under `data-YYYY.MM.DD`.
- Do not mutate an existing public dataset release.
- Do not add external PATs if the built-in `GITHUB_TOKEN` is sufficient.
- The certification release namespace is `certification-<run-id>` only.
- The certification issue prefix is `[CERTIFICATION ALERT]` only.
- A temporary draft release and any temporary certification tag/ref must be deleted and absence verified before the workflow can report success.
- A certification Issue is closed and retained as auditable trace; it is never reused as a production alert.
- The workflow default permissions remain `contents: read`; `contents: write` and `issues: write` are granted only to isolated mutation jobs.
- Every implementation PR must include a documented double-check of current `main`, the approved spec, relevant upstream docs, diff scope, tests, build, whitespace, credentials, and cleanup behavior before the PR is opened.
- Current production contract remains exactly six assets: `arancel_mx.duckdb`, `arancel_mx.csv`, `arancel_mx.json`, `manifest.json`, `SHA256SUMS`, `official-sources.tar.gz`.

---

## Planned file structure

```text
src/arancel_mx/certification/
├── __init__.py                 public internal entrypoints for certification
├── bundle.py                   six-asset, source-archive and cross-format checks
├── consumer.py                 DuckDB consumer contract checks
└── reports.py                  typed result/report helpers

scripts/
├── certify_package_install.py  real wheel/sdist install smoke runner
├── certify_github_release.py   temporary draft release lifecycle
└── certify_github_issue.py     temporary issue lifecycle

.github/workflows/
└── production-certification.yml

tests/certification/
├── test_bundle.py
├── test_consumer.py
├── test_package_install.py
├── test_github_release.py
├── test_github_issue.py
└── test_workflow_contract.py
```

No certification module may fetch official tariff sources. Live official-source access remains exclusively in the existing official-data pipeline.

### Task 1: Clean-install wheel and sdist certification

**Files:**
- Create: `scripts/certify_package_install.py`
- Create: `tests/certification/test_package_install.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: built artifacts from `python -m build`.
- Produces: CLI program `scripts/certify_package_install.py DIST_PATH` returning exit code `0` only after clean install/import/entrypoint checks pass.

- [ ] **Step 1: Write the failing unit test for subprocess command construction**

```python
from pathlib import Path
from scripts.certify_package_install import smoke_commands


def test_smoke_commands_run_outside_checkout(tmp_path: Path):
    commands = smoke_commands(Path("dist/arancel_mx-0.1.0-py3-none-any.whl"), tmp_path)
    rendered = [" ".join(command) for command in commands]
    assert any("import arancel_mx" in item for item in rendered)
    assert any("-m arancel_mx --help" in item for item in rendered)
    assert any("arancel-mx --help" in item for item in rendered)
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python -m pytest tests/certification/test_package_install.py -q`

Expected: FAIL because `scripts.certify_package_install` does not exist.

- [ ] **Step 3: Implement the minimal clean-install runner**

Implement `smoke_commands(dist_path: Path, work_dir: Path) -> list[list[str]]` and `main()` using `venv.EnvBuilder(with_pip=True)`, `subprocess.run(..., check=True, cwd=external_tmp_dir)`, and these exact checks after installation:

```text
python -c "import arancel_mx; print(arancel_mx.__version__)"
python -m arancel_mx --help
arancel-mx --help
python -c "from importlib.resources import files; assert files('arancel_mx').joinpath('sources/source_registry.json').is_file()"
```

The working directory for all checks must be a new temporary directory outside the repository checkout.

- [ ] **Step 4: Add real wheel and sdist smoke execution to CI**

After `python -m build`, run:

```bash
python scripts/certify_package_install.py dist/*.whl
python scripts/certify_package_install.py dist/*.tar.gz
```

Keep the existing required job name `test` unchanged so the branch ruleset does not drift.

- [ ] **Step 5: Verify GREEN and packaging isolation**

Run:

```bash
python -m pytest tests/certification/test_package_install.py tests/test_cli.py -q
python -m build
python scripts/certify_package_install.py dist/*.whl
python scripts/certify_package_install.py dist/*.tar.gz
git diff --check
```

Expected: all commands succeed.

- [ ] **Step 6: Commit**

```bash
git add scripts/certify_package_install.py tests/certification/test_package_install.py .github/workflows/ci.yml
git commit -m "test: certify installed package artifacts"
```

### Task 2: Independent six-asset bundle certification

**Files:**
- Create: `src/arancel_mx/certification/__init__.py`
- Create: `src/arancel_mx/certification/reports.py`
- Create: `src/arancel_mx/certification/bundle.py`
- Create: `tests/certification/test_bundle.py`
- Modify: `src/arancel_mx/release/__init__.py`

**Interfaces:**
- Consumes: `release_dir: Path` containing the six public assets.
- Produces: `certify_bundle(release_dir: Path) -> CertificationReport` where `CertificationReport.passed: bool`, `checks: tuple[str, ...]`, and `row_count: int`.

- [ ] **Step 1: Add RED tests for exact asset set and corruption**

Create tests that build a minimal synthetic release fixture and assert:

```python
report = certify_bundle(release_dir)
assert report.passed is True

(release_dir / "arancel_mx.csv").write_bytes(b"corrupted")
with pytest.raises(ValueError, match="checksum"):
    certify_bundle(release_dir)
```

Also add separate tests for missing asset, unexpected seventh asset, malformed checksum line, and duplicate checksum entry.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/certification/test_bundle.py -q`

Expected: FAIL because certification module does not exist.

- [ ] **Step 3: Implement exact-asset and checksum verification**

Reuse `PUBLIC_RELEASE_ASSETS`, `sha256`, and `verify_publication_bundle` from `arancel_mx.release.package`. Reject any set unequal to the six public names before parsing content.

- [ ] **Step 4: Implement source archive reconstruction checks**

Use `tarfile.open(..., "r:gz")` without extracting by default. Reject:

```python
member.name.startswith("/")
".." in Path(member.name).parts
member.issym()
member.islnk()
```

Read `source_capture.json` in-memory, recompute every archived document SHA-256, and require every source document referenced by `manifest.json` to exist exactly once.

- [ ] **Step 5: Implement CSV/JSON equivalence**

Load JSON as a list of objects and CSV with `csv.DictReader`; normalize `None`/empty strings and decimal text deterministically, key by `record_id`, and require the same row count, key set, public column set, and values.

- [ ] **Step 6: Verify GREEN**

Run:

```bash
python -m pytest tests/certification/test_bundle.py tests/release -q
python -m pytest -q
git diff --check
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/arancel_mx/certification src/arancel_mx/release/__init__.py tests/certification/test_bundle.py
git commit -m "test: certify public release bundle integrity"
```

### Task 3: DuckDB consumer contract and compatibility probe

**Files:**
- Create: `src/arancel_mx/certification/consumer.py`
- Create: `scripts/check_duckdb_compat.py`
- Create: `tests/certification/test_consumer.py`
- Modify: `docs/data-model.md`

**Interfaces:**
- Consumes: `database_path: Path`, parsed `manifest: Mapping[str, object]`.
- Produces: `certify_duckdb(database_path: Path, manifest: Mapping[str, object]) -> tuple[str, ...]` and CLI probe `scripts/check_duckdb_compat.py DATABASE`.

- [ ] **Step 1: Add RED consumer-contract tests**

Use a temporary DuckDB fixture and assert the checker requires:

```text
source_registry
source_document
hs_code
tariff_fraction
nico
tariff_rate
canonical_record
record_provenance
dataset_release
arancel_mx
```

Also require manifest row count equality, `record_id` uniqueness, MX8 parent HS6 existence, NICO10 parent MX8 existence, and no IGI/IGE values on `hs2`/`hs4`/`hs6` rows.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/certification/test_consumer.py -q`

Expected: FAIL because `certify_duckdb` does not exist.

- [ ] **Step 3: Implement read-only consumer checks**

Open with existing `arancel_mx.storage.connect(path, read_only=True)` and use explicit SQL assertions. Never mutate the database during certification.

- [ ] **Step 4: Add compatibility probe script**

`check_duckdb_compat.py` must only open the database read-only, query `SELECT COUNT(*) FROM arancel_mx`, and exit nonzero on failure. The implementation PR must run it inside an isolated environment using the package's documented minimum DuckDB version before making any compatibility claim.

- [ ] **Step 5: Resolve the minimum-version contract with executed evidence**

Start with the current declared floor `duckdb>=1.1`. Build a release database with the locked production environment and attempt to open it with the latest available `1.1.x` release. If that succeeds, document the executed version and command. If it fails, do not hide the failure: either configure an explicitly compatible storage format supported by the production DuckDB version and re-run the probe, or raise the dependency floor in `pyproject.toml` and production constraints in the same PR. No README claim is allowed without a passing executed probe.

- [ ] **Step 6: Verify**

Run:

```bash
python -m pytest tests/certification/test_consumer.py tests/storage -q
python -m pytest -q
python -m build
git diff --check
```

- [ ] **Step 7: Commit**

```bash
git add src/arancel_mx/certification/consumer.py scripts/check_duckdb_compat.py tests/certification/test_consumer.py docs/data-model.md pyproject.toml requirements/production-build.txt
git commit -m "test: certify DuckDB consumer compatibility"
```

Only add `pyproject.toml` and `requirements/production-build.txt` to the commit if the executed compatibility probe proves the current floor is false.

### Task 4: Deterministic rebuild and schema-v2 no-change replay

**Files:**
- Create: `tests/certification/test_reproducibility.py`
- Modify: `tests/automation/test_run_official_pipeline.py`
- Modify only if required by RED evidence: `src/arancel_mx/pipeline/official_dataset.py`
- Modify only if required by RED evidence: `src/arancel_mx/release/package.py`

**Interfaces:**
- Consumes: frozen source fixtures and fixed build metadata.
- Produces: deterministic logical outputs and a second-run result with `status == "no_change"`.

- [ ] **Step 1: Add RED deterministic-rebuild test**

Run the same fixture build twice into separate temporary directories with identical `dataset_version`, `generated_at`, source bytes, registry, and commit metadata. Assert JSON, CSV, manifest logical fields, `SHA256SUMS`, and source archive hashes are identical. Compare DuckDB logical rows rather than physical file bytes.

- [ ] **Step 2: Add RED no-change replay test**

Take the first build's schema-v2 `manifest.json` and pass it as the previous manifest to a second run with identical source identities. Assert:

```python
assert result["status"] == "no_change"
assert not second_release_dir.exists() or not any(second_release_dir.iterdir())
```

- [ ] **Step 3: Confirm RED only where behavior is missing**

Run: `python -m pytest tests/certification/test_reproducibility.py tests/automation/test_run_official_pipeline.py -q`

Expected: existing behavior may already satisfy some assertions. Do not modify production code for tests that already pass.

- [ ] **Step 4: Implement only the minimal missing determinism/no-change fix**

No source fetching, legal classification, or release namespace changes are allowed in this task. Any fix must preserve `retrieved_at` as actual fetch time and must not fake timestamps.

- [ ] **Step 5: Verify**

Run:

```bash
python -m pytest tests/certification/test_reproducibility.py tests/automation/test_run_official_pipeline.py -q
python -m pytest -q
python -m build
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add tests/certification/test_reproducibility.py tests/automation/test_run_official_pipeline.py src/arancel_mx/pipeline/official_dataset.py src/arancel_mx/release/package.py
git commit -m "test: prove deterministic rebuild and no-change replay"
```

Stage only production files actually changed.

### Task 5: Fault-injection certification matrix

**Files:**
- Create: `tests/certification/test_fault_injection.py`
- Modify existing focused tests only where a missing boundary belongs: `tests/sources/`, `tests/parsers/`, `tests/automation/test_publish_release.py`
- Modify production modules only when a new RED test exposes a real missing fail-closed boundary.

**Interfaces:**
- Produces structured bounded failures for every certified boundary without leaking credentials.

- [ ] **Step 1: Inventory existing coverage before adding tests**

Search current tests for timeout, redirect host validation, response size limit, media type validation, truncated workbook/PDF, parser ambiguity, missing DOF evidence, conflicting legal evidence, source hash mismatch, cross-format mismatch, manifest provenance mismatch, tag collision, upload digest mismatch, and failed cleanup.

Record a short matrix in the PR body with `existing`, `new`, or `not applicable` for each item.

- [ ] **Step 2: Add only missing RED cases**

Each new case must assert both the failure and its stable category/message fragment. Example:

```python
with pytest.raises(SourceCaptureError, match="allowlisted"):
    fetch_source(...)
```

For publisher failures, assert diagnostic output never contains the test token value.

- [ ] **Step 3: Run the targeted file and confirm RED for each genuinely missing boundary**

Run: `python -m pytest tests/certification/test_fault_injection.py -q`

- [ ] **Step 4: Implement minimal fail-closed fixes**

Never downgrade an error to warning to make a test pass. Never add heuristic legal fallback.

- [ ] **Step 5: Verify full suite**

```bash
python -m pytest -q
python -m build
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add tests/certification/test_fault_injection.py tests/sources tests/parsers tests/automation src/arancel_mx scripts
git commit -m "test: certify fail-closed fault boundaries"
```

Stage only files touched by proved missing coverage.

### Task 6: Controlled temporary draft-release mutation

**Files:**
- Create: `scripts/certify_github_release.py`
- Create: `tests/certification/test_github_release.py`
- Create: `.github/workflows/production-certification.yml`
- Create: `tests/certification/test_workflow_contract.py`

**Interfaces:**
- Consumes: `GITHUB_REPOSITORY`, `GITHUB_TOKEN`, `GITHUB_RUN_ID`.
- Produces: a JSON result with `status: "passed"`, `release_absent: true`, and `tag_absent: true` only after cleanup is verified.

- [ ] **Step 1: Add RED unit tests using a fake `GitHubApi`**

Test exact lifecycle:

```text
GET release/tag -> 404
GET git/ref/tag -> 404
POST draft release
upload tiny certification fixture
GET draft
verify bytes/digest
DELETE draft
GET release/tag -> 404
GET git/ref/tag -> 404
```

Also test cleanup after upload verification failure.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/certification/test_github_release.py -q`

- [ ] **Step 3: Implement certification-only release helper**

Hard-code the accepted prefix check:

```python
if not tag.startswith("certification-"):
    raise ValueError("certification tag must use certification- namespace")
if tag.startswith("data-"):
    raise ValueError("production data tag is forbidden")
```

Create a draft release only. Never PATCH it to `draft: false`.

- [ ] **Step 4: Add manual workflow with least privilege**

`production-certification.yml` is `workflow_dispatch` only. Default workflow permissions are `contents: read`. The draft-release job alone gets:

```yaml
permissions:
  contents: write
```

Use pinned full-SHA GitHub Actions, matching repository policy. Run unit/offline certification before the mutation job. Use `if: always()` cleanup inside the helper so cleanup is attempted even after verification failure.

- [ ] **Step 5: Add workflow contract tests**

Assert statically that:

```text
workflow_dispatch exists
schedule is absent
pull_request is absent
contents: write appears only in the release mutation job
"data-" is forbidden in certification tag construction
```

- [ ] **Step 6: Verify offline**

```bash
python -m pytest tests/certification/test_github_release.py tests/certification/test_workflow_contract.py -q
python -m pytest -q
python -m build
git diff --check
```

- [ ] **Step 7: Commit**

```bash
git add scripts/certify_github_release.py tests/certification/test_github_release.py tests/certification/test_workflow_contract.py .github/workflows/production-certification.yml
git commit -m "feat: add isolated release-boundary certification"
```

### Task 7: Controlled temporary GitHub Issue mutation

**Files:**
- Create: `scripts/certify_github_issue.py`
- Create: `tests/certification/test_github_issue.py`
- Modify: `.github/workflows/production-certification.yml`
- Modify: `tests/certification/test_workflow_contract.py`

**Interfaces:**
- Produces a closed issue titled exactly `[CERTIFICATION ALERT] <run-id>` and JSON result containing its issue number and `state: "closed"`.

- [ ] **Step 1: Add RED fake-API lifecycle tests**

Assert create -> fetch -> update/comment -> close -> fetch closed. Assert the helper rejects titles beginning `[DATA ALERT]`.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/certification/test_github_issue.py -q`

- [ ] **Step 3: Implement certification issue helper**

Use the existing GitHub API wrapper and repository issue endpoints. Include run ID, commit SHA, and `certification only; not a production incident` in the body. Close with a final certification-complete comment or body update.

- [ ] **Step 4: Add isolated `issues: write` job**

The issue job receives only:

```yaml
permissions:
  contents: read
  issues: write
```

It must not depend on production `[DATA ALERT]` dedupe keys and must never call `scripts.data_alert`.

- [ ] **Step 5: Verify offline**

```bash
python -m pytest tests/certification/test_github_issue.py tests/certification/test_workflow_contract.py -q
python -m pytest -q
python -m build
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add scripts/certify_github_issue.py tests/certification/test_github_issue.py tests/certification/test_workflow_contract.py .github/workflows/production-certification.yml
git commit -m "feat: add isolated issue-boundary certification"
```

### Task 8: Live certification run, rollback verification, and operator documentation

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`
- Create: `docs/production-certification.md`
- Modify: `.github/pull_request_template.md`

**Interfaces:**
- Consumes: merged manual certification workflow on protected `main`.
- Produces: one successful certification run, no remaining draft release/tag, one closed certification issue, and documented evidence.

- [ ] **Step 1: Double-check live preconditions before dispatch**

Verify from GitHub API/UI:

```text
main protected and current CI green
no open production data alert caused by current main
no existing certification tag for the new run id
no draft certification release for the new run id
workflow permissions match plan
```

- [ ] **Step 2: Dispatch `Production certification` from trusted `main`**

Run the workflow manually once. Do not use a PR branch for live write-boundary mutation.

- [ ] **Step 3: Verify live postconditions**

Require all of:

```text
workflow conclusion == success
no new data-* tag
no public production release changed
no draft certification release remains
no certification tag/ref remains
certification Issue exists and is closed
main SHA unchanged by workflow
```

If any cleanup invariant fails, stop and repair cleanup before any later production work.

- [ ] **Step 4: Document the operator runbook**

`docs/production-certification.md` must contain the manual dispatch path, safety namespaces, expected cleanup, how to inspect the closed certification issue, and exact commands for package smoke checks and bundle verification.

- [ ] **Step 5: Add the double-check checklist to the PR template**

Add explicit checkboxes for current-main comparison, upstream docs when relevant, no generated assets/secrets, and live mutation cleanup evidence when a PR touches certification workflows.

- [ ] **Step 6: Verify docs and repository suite**

```bash
python -m pytest -q
python -m build
git diff --check
```

- [ ] **Step 7: Commit**

```bash
git add README.md README.en.md docs/production-certification.md .github/pull_request_template.md
git commit -m "docs: document production certification evidence"
```

## Final certification gate

Before declaring Subproject A complete, execute and archive evidence for:

```bash
python -m pytest -q
python -m build
git diff --check
```

Then run one new `Official data pipeline` with `publish=false` from protected `main` and require it to remain green. The certification work is rejected if it changes the six-asset contract, legal reconciliation result, or publisher namespace unintentionally.
