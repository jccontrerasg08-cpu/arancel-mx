# TestPyPI to PyPI Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:test-driven-development` for scripts/workflow contracts, `superpowers:verification-before-completion` before any live publication claim, and re-verify all time-sensitive PyPI/GitHub Actions details immediately before implementation.

**Goal:** Publish `arancel-mx 0.2.0` through a fail-closed chain where the exact wheel/sdist bytes are built once, uploaded to TestPyPI, downloaded back and hash-verified, externally certified across the blocking OS/Python matrix, manually approved, then uploaded unchanged to PyPI and re-certified from the public index.

**Architecture:** A dedicated tag-only workflow `.github/workflows/publish-python-package.yml` handles package publication. It does not create GitHub Releases. Build artifacts are immutable GitHub Actions artifacts with recorded SHA256. TestPyPI and PyPI use separate Trusted Publisher/OIDC environments. External consumer jobs do not checkout the repository source tree. Release-candidate tags stop after TestPyPI certification. Final tags require production environment approval before PyPI upload.

**Depends on:** all deterministic consumer, CLI/doctor, and package-certification plans complete and green on protected `main`.

## Global release invariants

- Package tags: `pkg-v0.2.0rcN` and `pkg-v0.2.0`.
- A tag must point exactly to the current protected green `main` tip at workflow start.
- Tag version must equal normalized `project.version` in `pyproject.toml`.
- Final package bytes are built once.
- No rebuild between TestPyPI and PyPI.
- No GitHub Release for `pkg-v*`.
- `data-*` GitHub Releases remain the only releases used by `/releases/latest` dataset links.
- TestPyPI and PyPI use Trusted Publishing/OIDC, never long-lived upload tokens.
- Only publishing jobs get `id-token: write`.
- `pypi` environment requires human approval.
- Release candidate tags never publish to production PyPI.
- External certification jobs have no source checkout and clear `PYTHONPATH`/`PYTHONHOME`.
- Every third-party Action uses a full reviewed commit SHA.
- Current publisher action observed during planning: `pypa/gh-action-pypi-publish` v1.14.2 points to commit `dc37677b2e1c63e2034f94d8a5b11f265b73ba33`; re-resolve before implementation.

---

### Task 1: Package tag/version validation script

**Files:**
- Create: `scripts/validate_package_tag.py`
- Create: `tests/package_release/test_validate_package_tag.py`

**First red tests:**
- `test_accepts_matching_rc_tag_and_project_version()`
- `test_accepts_matching_final_tag_and_project_version()`
- `test_rejects_non_pkg_tag()`
- `test_rejects_tag_version_mismatch()`
- `test_rejects_malformed_pep440_version()`
- `test_identifies_release_candidate_as_testpypi_only()`

**Implementation output:** deterministic JSON containing normalized version, tag, `is_prerelease`, and expected production eligibility.

**Verify:**
```bash
python -m pytest tests/package_release/test_validate_package_tag.py -q
```

**Commit:** `build: validate package release tags against project version`

---

### Task 2: Protected-main origin gate

**Files:**
- Extend: `scripts/validate_package_tag.py` or create `scripts/validate_release_origin.py`
- Create: `tests/package_release/test_release_origin.py`

**First red tests with injected git/GitHub metadata:**
- tag SHA equals current main SHA -> pass;
- stale main SHA -> fail;
- arbitrary branch commit -> fail;
- missing mandatory check result -> fail;
- failed mandatory check result -> fail.

**Implementation:** workflow resolves tag SHA and current `refs/heads/main`; equality is mandatory before registry mutation. Check-suite validation uses GitHub API metadata available to the workflow.

**Verify:**
```bash
python -m pytest tests/package_release/test_release_origin.py -q
```

**Commit:** `build: require package tags from green protected main`

---

### Task 3: Build-once distribution and digest manifest

**Files:**
- Create: `scripts/hash_distributions.py`
- Create: `tests/package_release/test_hash_distributions.py`

**Expected output:** `dist/SHA256SUMS.package` with exactly the wheel and sdist filenames and hashes, plus machine-readable JSON if helpful.

**First red tests:**
- exactly two expected distributions;
- duplicate/unexpected distribution fails;
- stable SHA256 format;
- hash re-verification detects one-byte mutation.

**Verify:**
```bash
python -m build
python scripts/hash_distributions.py dist
python -m pytest tests/package_release/test_hash_distributions.py -q
```

**Commit:** `build: record immutable package distribution hashes`

---

### Task 4: Standalone certification artifact bundle

**Files:**
- Reuse: `scripts/package_consumer_probe.py`
- Create: `scripts/package_certification_bundle.py`
- Create: `tests/package_release/test_certification_bundle.py`

**Bundle contains only:**
- standalone consumer probe;
- expected package version;
- expected wheel/sdist SHA256;
- minimal non-secret certification metadata.

It must not contain repository source or credentials.

**First red tests:** forbidden source paths absent; expected hash/version present; probe executable/readable cross-platform.

**Commit:** `build: create source-free external certification bundle`

---

### Task 5: TestPyPI Trusted Publisher workflow job

**Files:**
- Create: `.github/workflows/publish-python-package.yml`
- Create: `tests/package_release/test_publish_workflow.py`

**Trigger:** push tags matching `pkg-v*` only.

**Workflow default permissions:** minimal `contents: read`.

**Conceptual jobs:**
```text
validate-tag-and-origin
build-once
inspect-distributions
publish-testpypi
verify-testpypi-roundtrip
external-certification
production-approval/publish-pypi
post-pypi-certification
```

**TestPyPI job:**
- environment: `testpypi`;
- `permissions: id-token: write` only there;
- downloads the exact build artifact;
- re-verifies hashes immediately before upload;
- uses reviewed full-SHA `pypa/gh-action-pypi-publish`;
- repository URL configured for TestPyPI as required by current action docs.

**First red workflow tests:**
- tag-only trigger;
- no `workflow_dispatch` production bypass;
- no `pull_request_target`;
- no secrets or token references;
- OIDC scoped only to publisher jobs;
- full-SHA action pinning.

**Commit:** `ci: add TestPyPI trusted publication gate`

---

### Task 6: TestPyPI roundtrip provenance verification

**Files:**
- Create: `scripts/verify_testpypi_roundtrip.py`
- Create: `tests/package_release/test_testpypi_roundtrip.py`
- Extend workflow.

**Authoritative flow:**
```text
fresh job, no checkout
pip download --no-deps --index-url https://test.pypi.org/simple arancel-mx==VERSION
verify filename/version
verify SHA256 against original build manifest
```

Test both wheel and sdist retrieval explicitly. Runtime dependencies are resolved from PyPI only after `arancel-mx` distribution provenance has been established.

**First red tests:** wrong version, wrong digest, duplicate candidate file, missing sdist/wheel all fail.

**Commit:** `ci: verify TestPyPI package bytes match build artifact`

---

### Task 7: Blocking external OS/Python matrix from TestPyPI

**Files:**
- Extend: `.github/workflows/publish-python-package.yml`
- Create: `tests/package_release/test_external_matrix_contract.py`

**Blocking matrix:**
```text
Ubuntu x64:      3.11 3.12 3.13 3.14
Windows x64:     3.11 3.12 3.13 3.14
macOS ARM64:     3.11 3.12 3.13 3.14
macOS Intel:     3.11 3.12 3.13 3.14
```

Re-verify runner labels immediately before implementation.

**Each job:**
- no checkout action;
- download only certification bundle/artifact metadata;
- fresh HOME/cache/temp working dir;
- clear `PYTHONPATH`, `PYTHONHOME`;
- retrieve exact TestPyPI candidate by version;
- verify candidate hash;
- install;
- `pip check`;
- run standalone probe;
- perform live public dataset download through package;
- run `doctor --json`, lookup, search, parent, children, provenance;
- disable network for offline smoke using verified cache.

**Failure semantics:** one blocking cell failure blocks production.

**Commit:** `ci: certify TestPyPI across blocking platform matrix`

---

### Task 8: Installation-mode matrix

**Files:**
- Extend workflow.
- Create: `tests/package_release/test_install_modes_contract.py`

**Required blocking modes across representative cells, in addition to the 16-cell base matrix:**
- pip wheel;
- pip `--only-binary=:all:`;
- pip source `--no-binary=arancel-mx`;
- pipx CLI install;
- `uv pip install`;
- `uv tool install`.

At minimum exercise all three major OS families; use additional Python edges where practical. Do not multiply every mode across every matrix cell unless evidence shows it is necessary. The base 16-cell matrix still proves interpreter/platform support; this matrix proves installation tool/mode support.

**Commit:** `ci: certify pip pipx uv and sdist install modes`

---

### Task 9: Destructive consumer certification before production

**Files:**
- Reuse deterministic tests from consumer plan.
- Create: `scripts/package_failure_probe.py`
- Create: `tests/package_release/test_failure_probe.py`
- Extend workflow with controlled fault tests where network behavior can be safely simulated.

**Required classes:** timeout, 404, retryable 429/5xx, truncated download, wrong SHA, invalid manifest, unsupported schema, corrupt DuckDB, asset missing/duplicate, unwritable cache, Unicode path, concurrent download, no-cache offline, network-down verified-cache.

**Rule:** every failure asserts no false `verified.json` state.

**Commit:** `test: add package destructive external certification`

---

### Task 10: Production PyPI environment gate

**Files:**
- Extend workflow.
- Extend `tests/package_release/test_publish_workflow.py`.
- Document: `docs/package-release.md`.

**Production job requirements:**
- final versions only, not `rcN`;
- `needs` all required TestPyPI and external certification jobs;
- environment `pypi`;
- required human reviewer configured in GitHub UI;
- `id-token: write` only on publish job;
- retrieve original build-once artifact;
- verify SHA256 again immediately before upload;
- publish exact bytes with Trusted Publishing.

**Fail closed:** no approval or any skipped/failed dependency means no upload.

**Commit:** `ci: gate production PyPI publication on certified bytes`

---

### Task 11: PyPI post-publication full external certification

**Files:**
- Extend workflow.
- Create: `tests/package_release/test_post_publish_contract.py`.

**Flow:** new source-free jobs install exact `arancel-mx==VERSION` from `https://pypi.org` and repeat the blocking 16-cell smoke for import/CLI/dataset/query/offline behavior.

**Also verify:** PyPI-reported distribution digests against original build SHA256 when available through stable API/metadata.

**Commit:** `ci: verify production package from public PyPI`

---

### Task 12: Package publication alert/yank response path

**Files:**
- Create: `scripts/package_release_alert.py`
- Create: `tests/package_release/test_package_release_alert.py`
- Modify: `docs/package-release.md`

**Behavior after post-PyPI failure:**
- deterministic `[PACKAGE ALERT] arancel-mx VERSION` GitHub Issue create/update path;
- include failed matrix/job evidence without secrets;
- document manual criteria for yanking;
- never delete/re-upload or reuse version number;
- corrected release is a new patch version.

Do not auto-yank in 0.2.0 unless explicitly approved later; alert and human decision are safer for first production lifecycle.

**Commit:** `ops: add package publication failure response path`

---

### Task 13: Release-candidate lifecycle

**Files:**
- Extend workflow tests and docs.

**Rules:**
- `0.2.0rc1`, `rc2`, etc. can publish to TestPyPI and run full certification;
- RC workflow stops before PyPI production job;
- once accepted, source version becomes `0.2.0`;
- final `pkg-v0.2.0` gets a fresh build-once artifact, is itself uploaded to TestPyPI, and must pass full certification;
- passing `rcN` never authorizes different final bytes.

**Commit:** `docs: define package release candidate lifecycle`

---

### Task 14: Manual registry/environment setup checklist

**Files:**
- Create: `docs/testpypi-pypi-setup.md`
- Create: `tests/package_release/test_setup_docs.py`

**Checklist before first live candidate:**
1. PyPI account and TestPyPI account ready with required 2FA/security.
2. Verify normalized `arancel-mx` project-name availability/ownership on both registries.
3. Create GitHub environments `testpypi` and `pypi`.
4. Configure required reviewer for `pypi`.
5. Configure pending Trusted Publisher tuples for exact owner/repo/workflow/environment.
6. Confirm no `PYPI_TOKEN`, `TEST_PYPI_TOKEN`, `.pypirc` credential or long-lived package secret exists.
7. Verify current PyPA publishing guidance and current publisher action SHA.
8. Verify current GitHub hosted runner labels.

**Important:** repository tests can verify docs/workflow intent but cannot prove UI/account configuration. Live publication does not start until user and implementation worker verify these prerequisites explicitly.

**Commit:** `docs: add trusted publisher setup checklist`

---

### Task 15: Package name and registry preflight

**Files:**
- Create: `scripts/check_package_registry_name.py`
- Create: `tests/package_release/test_registry_name.py`

**Behavior:** query official PyPI/TestPyPI project endpoints at execution time, normalize project name, distinguish not-found from existing unrelated ownership, and stop for explicit user decision if name is not safely usable.

No automatic typo/lookalike fallback name.

**Commit:** `build: add package registry name preflight`

---

### Task 16: Attestation/provenance verification documentation and checks

**Files:**
- Create: `scripts/verify_package_provenance.py` if current APIs support deterministic verification.
- Create: `tests/package_release/test_provenance_contract.py`.
- Modify docs.

**Evidence chain:**
```text
pkg-v tag + source commit
build artifact SHA256
GitHub Actions artifact identity
TestPyPI roundtrip SHA256
PyPI distribution SHA256
Trusted Publisher / PEP 740 attestations where current tooling emits them
```

Do not conflate package provenance with legal signatures of tariff source documents.

**Commit:** `security: verify package publication provenance`

---

### Task 17: First live `0.2.0rc1` readiness checkpoint

No tag is created until all deterministic plans are merged and protected `main` is green.

**Required commands/evidence before tag:**
```bash
python -m pytest -q
python scripts/package_preflight.py
python -m build
twine check dist/*
check-wheel-contents dist/*.whl
```

Then explicitly re-check:
- current main SHA;
- version set to `0.2.0rc1`;
- project name availability;
- TestPyPI Trusted Publisher configuration;
- no production token secrets;
- full action SHAs and runner labels.

Only then create `pkg-v0.2.0rc1` from the current green main tip.

**Commit:** no code commit; this is a release-operation gate.

---

### Task 18: Final `0.2.0` production readiness checkpoint

After at least one RC has provided useful external evidence and final code is settled:
- set version to `0.2.0` in the sole source of truth;
- merge through normal protected PR;
- wait for all required CI/preflight checks green;
- create `pkg-v0.2.0` exactly at current main tip;
- require final TestPyPI roundtrip + full certification again;
- approve `pypi` environment only after reviewing the evidence;
- post-PyPI full matrix must pass before state becomes `production-certified`.

## Completion states

Use these exact states in docs/status messages:
```text
design-approved
implementation-complete
deterministic-ci-verified
testpypi-configured
rc-externally-certified
final-testpypi-certified
pypi-published
post-pypi-certified
0.2.0-production-certified
```

Never claim a later state before the real live gate has occurred.

## Final completion gate

This publication subplan is complete only after the real external process has succeeded, not merely after workflow YAML exists. `arancel-mx 0.2.0` becomes **production-certified** only when the exact final wheel/sdist bytes have passed TestPyPI roundtrip verification, every blocking external matrix cell, manual production approval, PyPI upload, and the post-PyPI external matrix.