# Repository and Supply-Chain Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `arancel-mx` predictable and maintainable around the autonomous data pipeline by locking production-build dependencies, hardening auxiliary Actions, enabling Dependabot-friendly updates, aligning public documentation, and configuring GitHub repository protections.

**Architecture:** Keep library dependency ranges flexible in `pyproject.toml`, but constrain official CI/production data builds with a committed exact constraints file. All GitHub Actions are immutable SHA references. Maintenance automation opens PRs instead of bypassing `main`. Repository settings provide the final policy boundary: immutable releases, protected main, required offline CI, and security features.

**Tech Stack:** GitHub Actions, Dependabot, pip constraints, Python 3.11, pytest, GitHub repository Rulesets/Settings.

## Global Constraints

- Do not widen global `GITHUB_TOKEN` permissions.
- Dependency upgrades must arrive as reviewable commits/PRs rather than appearing silently in a scheduled production run.
- Do not require live official websites as a merge check for ordinary code PRs.
- Auxiliary/demo workflows must not mask failed pushes or commit directly through branch protection.
- Keep release/data files outside Git history.
- Documentation must describe implemented behavior, not roadmap behavior, after the autonomous pipeline lands.

---

## Task 1: Establish an exact production-build constraints file

**Files:**
- Create: `requirements/production-build.txt`
- Modify: `.github/workflows/ci.yml`
- Modify later: `.github/workflows/official-data-pipeline.yml`
- Create: `tests/test_dependency_policy.py`

**Initial constraints baseline:** use the versions from the already successful verified `data-2026.08.10` Actions build as the first known-good set:

```text
build==1.5.0
certifi==2026.7.22
charset-normalizer==3.4.9
duckdb==1.5.5
et-xmlfile==2.0.0
idna==3.18
iniconfig==2.3.0
numpy==2.4.6
openpyxl==3.1.5
packaging==26.3
pandas==3.0.5
pillow==12.3.0
pluggy==1.6.0
Pygments==2.20.0
PyMuPDF==1.28.2
pyproject_hooks==1.2.0
pytest==9.1.1
python-dateutil==2.9.0.post0
reportlab==5.0.0
requests==2.34.2
six==1.17.0
urllib3==2.7.0
xlrd==2.0.2
```

- [ ] Add a failing policy test that parses `pyproject.toml` direct dependencies and asserts each installed runtime/dev dependency has one exact `==` constraint entry.
- [ ] Add a test that rejects duplicate packages and non-exact operators such as `>=`, `~=`, or unversioned names in `requirements/production-build.txt`.
- [ ] Run `python -m pytest tests/test_dependency_policy.py -q` and confirm failure before the file exists.
- [ ] Create the constraints file with the known-good versions above.
- [ ] Change CI installation from:

```bash
python -m pip install -e ".[dev]"
```

to:

```bash
python -m pip install -c requirements/production-build.txt -e ".[dev]"
```

- [ ] Use the same constrained installation in `official-data-pipeline.yml`.
- [ ] Do not pin the public package requirements in `pyproject.toml`; they remain compatibility ranges for downstream users.
- [ ] Run dependency policy tests and full CI tests.
- [ ] Commit: `build: constrain official production dependencies`.

---

## Task 2: Add Dependabot for Python and GitHub Actions

**Files:**
- Create: `.github/dependabot.yml`
- Modify: `tests/test_dependency_policy.py`

**Configuration:**

```yaml
version: 2
updates:
  - package-ecosystem: pip
    directory: "/"
    schedule:
      interval: weekly
      day: monday
    labels:
      - dependencies
      - python
    open-pull-requests-limit: 5

  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: weekly
      day: monday
    labels:
      - dependencies
      - github-actions
    open-pull-requests-limit: 5
```

- [ ] Add failing tests that require both ecosystems and weekly cadence.
- [ ] Add a test ensuring Dependabot config does not contain credentials or registries that require a repository secret.
- [ ] Create the file and run tests.
- [ ] Confirm the dependency update process is: Dependabot PR → offline CI → review/auto-merge policy, never direct mutation of production release dependencies.
- [ ] Commit: `chore: configure dependabot updates`.

---

## Task 3: Make the CI job a stable required-status-check contract

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_public_distribution.py`

**Stable check:** `CI / test`.

- [ ] Add a static test asserting the workflow name remains exactly `CI` and the merge-gate job ID remains exactly `test`.
- [ ] Assert `pull_request` and push-to-main triggers remain.
- [ ] Assert `contents: read`, timeout, pinned checkout/setup-python, constrained dependency install, pytest, package build, and `git diff --check` are present.
- [ ] Assert the CI workflow contains no `contents: write`, `issues: write`, `pull-requests: write`, secrets, live-update command, or production release command.
- [ ] Run the static test and fix any naming drift.
- [ ] Commit: `ci: stabilize required offline check contract`.

---

## Task 4: Harden the demo-generation workflow and make it PR-based

**Files:**
- Modify: `.github/workflows/generate-demo.yml`
- Create: `tests/test_demo_workflow.py`

**Desired behavior:** manual workflow only; generate demo assets; if changed, push an automation branch and open a PR; never commit directly to protected `main`; never suppress a failed command with `|| true`.

**Permissions:**

```yaml
permissions:
  contents: write
  pull-requests: write
```

- [ ] Add failing static tests that reject `actions/checkout@v4`, `curl ... NodeSource`, unversioned `npm install -g svg-term-cli`, direct push to `main`, and every `|| true` occurrence.
- [ ] Add assertions that checkout/setup-node use full SHA pins and Node is installed through `actions/setup-node`.
- [ ] Before implementation, verify the currently supported `svg-term-cli` version and current `actions/setup-node` SHA from primary/official sources; record the exact version/SHA in the workflow commit message/PR evidence.
- [ ] Replace external shell installer usage with pinned `actions/setup-node` and an exact npm package version.
- [ ] Generate assets and use:

```bash
branch="automation/demo-${GITHUB_RUN_ID}"
git switch -c "$branch"
git add docs/demo.gif docs/demo.svg
git diff --cached --quiet && exit 0
git commit -m "docs: refresh terminal demo"
git push origin "$branch"
gh pr create \
  --base main \
  --head "$branch" \
  --title "docs: refresh terminal demo" \
  --body "Automated demo refresh from workflow run ${GITHUB_RUN_ID}."
```

- [ ] Ensure `GH_TOKEN: ${{ github.token }}` is scoped only to the PR-creation step/job and no self-approval is performed.
- [ ] Run static workflow tests.
- [ ] Commit: `ci: harden demo generation automation`.

---

## Task 5: Update public-distribution tests for intentional `docs/superpowers` documentation

**Files:**
- Modify: `tests/test_public_distribution.py`

**Context:** the existing test currently treats `docs/superpowers` as a private path, but the approved architecture/spec/plans are intentionally public repository documentation.

- [ ] Add a failing replacement expectation requiring these paths:

```text
docs/superpowers/specs/2026-08-10-production-hardening-automation-design.md
docs/superpowers/plans/2026-08-10-core-data-correctness.md
docs/superpowers/plans/2026-08-10-autonomous-release-alerts.md
docs/superpowers/plans/2026-08-10-repository-supply-chain-hardening.md
```

- [ ] Remove only `docs/superpowers` from the `private_paths` tuple; keep `.env`, `token.txt`, `PIPELINE.md`, and other genuinely private/legacy exclusions.
- [ ] Add a scan asserting public design/plan docs contain no credential-pattern hits or private absolute machine paths.
- [ ] Run `python -m pytest tests/test_public_distribution.py -q`.
- [ ] Commit: `test: allow public engineering specifications`.

---

## Task 6: Align Spanish and English README status with the autonomous pipeline

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `tests/test_public_distribution.py`

- [ ] First rewrite the documentation tests so they require the new workflow name `official-data-pipeline.yml`, daily automated source checks, automatic publication on a clean changed dataset, and automatic GitHub Issue alerts on failures.
- [ ] Make those tests fail against the old README wording.
- [ ] Update both READMEs in parallel so neither claims publication is manual after cutover.
- [ ] Replace roadmap entries for `automated detection of official-source changes` and `supervised automatic publication` with implemented status.
- [ ] Keep future roadmap items such as search API/PyPI only if still unimplemented.
- [ ] Document the fail-closed behavior in one short sequence:

```text
official sources → capture → legal reconciliation → parse → validate
→ unchanged: stop green
→ changed + valid: verified immutable release
→ any failure: block + GitHub Issue
```

- [ ] Update repository structure to include all production workflows and `requirements/production-build.txt`.
- [ ] Update CLI examples from `update` to preferred `check-updates` while noting the 0.x compatibility alias.
- [ ] Run documentation/public distribution tests.
- [ ] Commit: `docs: document autonomous fail-closed releases`.

---

## Task 7: Rewrite release-process and source documentation to match runtime exactly

**Files:**
- Modify: `docs/release-process.md`
- Modify: `docs/sources.md`
- Modify: `docs/data-model.md`
- Modify: `tests/test_public_distribution.py`

- [ ] Add failing documentation tests requiring `retrieved_at` = actual fetch time, schema v2 manifest provenance, DOF reconciliation as a build gate, source-change no-op semantics, draft upload verification, immutable release publication, and issue alert/recovery behavior.
- [ ] Update `docs/release-process.md` to remove the section titled manual publication and replace it with the exact automated sequence and permissions boundary.
- [ ] Explain same-date second-change behavior: fail/alert rather than overwrite.
- [ ] Update `docs/sources.md` so the existing claim that discrepancies block publication is backed by the now-integrated gate and explain how DOF evidence is anchored to the registered Diputados ledger.
- [ ] Update `docs/data-model.md` with `generated_at` separately from actual `retrieved_at` and document `dataset_release.release_metadata_json` as internal release provenance.
- [ ] Preserve the legal-advice disclaimer and distinguish legal validity from observed snapshots.
- [ ] Run documentation tests.
- [ ] Commit: `docs: align provenance and release process with production`.

---

## Task 8: Extend the PR template for production-sensitive changes

**Files:**
- Modify: `.github/pull_request_template.md`
- Modify: `tests/test_public_distribution.py`

- [ ] Add failing test expectations for checklist entries covering workflow permissions, release manifest/schema impact, official source registry impact, and dependency-lock updates.
- [ ] Add these checklist items:

```markdown
- [ ] Si modifiqué Actions, mantuve permisos mínimos y acciones fijadas por SHA.
- [ ] Si modifiqué fuentes/reconciliación, agregué fixtures o pruebas offline del fallo esperado.
- [ ] Si modifiqué el contrato de release, actualicé esquema/manifiesto/documentación.
- [ ] Si cambié dependencias del build oficial, actualicé `requirements/production-build.txt` en el mismo PR.
```

- [ ] Run public distribution tests.
- [ ] Commit: `docs: strengthen production change checklist`.

---

## Task 9: Document exact repository Settings that cannot be safely committed as code

**Files:**
- Create: `docs/operations/github-settings.md`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `tests/test_public_distribution.py`

**Required settings checklist:**

### Actions
- Default workflow permissions: **Read repository contents and packages permissions**.
- **Allow GitHub Actions to create and approve pull requests** may remain enabled, but no project workflow self-approves data/code PRs.

### Releases
- **Enable release immutability**: ON before autonomous publication is activated.

### Main branch ruleset
- Enforcement: Active.
- Target: default branch / `main`.
- Require pull request before merging: ON.
- Required status check: `CI / test`.
- Require branch to be up to date before merging: ON.
- Require conversation resolution: ON.
- Block force pushes: ON.
- Block deletion: ON.
- Require linear history: ON only after squash-only merge strategy is active.

### General merge settings
- Squash merging: ON.
- Merge commits: OFF.
- Rebase merging: OFF.
- Automatically delete head branches: ON.
- Always suggest updating pull request branches: ON.
- Auto-merge: optional ON after `CI / test` is required, for reviewed maintenance PRs only.

### Advanced Security
- Dependabot alerts: ON.
- Dependabot security updates: ON.
- Secret scanning: ON where available.
- Push protection: ON where available.
- Code scanning/default setup: ON where available for the public repository.
- Private vulnerability reporting: ON.

- [ ] Add a failing test that requires this operations document and the exact `CI / test` check name.
- [ ] Create the document with numbered UI paths and a verification checklist rather than vague recommendations.
- [ ] Link it from both READMEs.
- [ ] Run documentation tests.
- [ ] Commit: `docs: add github production settings runbook`.

---

## Task 10: Configure repository Settings manually after the hardened workflows land

**Files:** No repository source mutation by the implementation agent unless an API capability is explicitly available and verified. This task is a maintainer UI operation.

- [ ] In `Settings → General → Releases`, enable release immutability.
- [ ] In `Settings → General → Pull Requests`, leave squash merge enabled and disable merge commits/rebase merging.
- [ ] Enable automatically delete head branches and always suggest updating PR branches.
- [ ] In `Settings → Rules → Rulesets`, create/activate the `main` ruleset from `docs/operations/github-settings.md`.
- [ ] Select the actual `CI / test` status check after the hardened CI has run at least once.
- [ ] In `Settings → Actions → General`, confirm the repository default remains read-only. Do not switch to global read/write.
- [ ] Keep the already-enabled Actions PR creation setting, but verify no workflow grants `pull-requests: write` except the demo maintenance workflow.
- [ ] In `Settings → Advanced Security`, enable the available security controls in the runbook.
- [ ] Re-open the runbook and mark each verification item locally or in the implementation PR description.

---

## Task 11: Verify dependency and workflow reproducibility after hardening

**Files:** Verification only.

- [ ] Create a clean Python 3.11 environment.
- [ ] Run:

```bash
python -m pip install -c requirements/production-build.txt -e ".[dev]"
python -m pytest -q
python -m build
git diff --check
```

- [ ] Confirm pip resolves every direct dependency to the exact constrained version.
- [ ] Confirm CI and official production workflow use the same constraints file.
- [ ] Confirm every `uses:` reference under `.github/workflows/` is a full commit SHA, not a mutable tag.
- [ ] Confirm no workflow contains `permissions: write-all`, `pull_request_target`, remote shell installer pipes, or masked `git push` failures.
- [ ] Confirm `git ls-files` contains no generated official dataset assets, local DuckDB, `.env`, or token files.
- [ ] Commit any policy-test corrections as `test: complete repository hardening verification`.

## Exit Criteria

This plan is complete only when:

1. Official CI/data builds use exact known-good dependency constraints.
2. Dependabot opens reviewable Python and GitHub Actions updates.
3. `CI / test` is stable and suitable as the required main check.
4. Demo automation opens a PR instead of directly mutating protected `main`.
5. All workflow Actions use immutable SHAs and no remote installer pipe remains.
6. Public docs describe autonomous releases and fail-closed alerting accurately.
7. `docs/superpowers` is intentionally public and covered by distribution/security scans.
8. Release immutability and the `main` ruleset are enabled in GitHub Settings.
9. Advanced Security controls are enabled where available.
10. Full tests, package build, and whitespace checks pass in a clean constrained environment.
