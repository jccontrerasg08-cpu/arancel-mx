# Production Certification Rollout Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the approved production-certification and Docusaurus design in small, independently reviewable PRs with an explicit double-check before every PR.

**Architecture:** This index fixes execution order, PR boundaries, prerequisite relationships, and the pre-PR verification gate. Core certification comes first, then provenance/timestamp certification, then the documentation site. Live write-boundary tests only run from trusted `main` after their implementation PR is merged.

**Tech Stack:** See the three component implementation plans below.

## Global Constraints

- Every implementation PR starts from current protected `main`, never from a stale feature branch.
- Before every PR: compare branch vs `main`, re-read the approved spec and exact task, re-open current repository interfaces, re-check unstable upstream docs/settings/actions, run targeted RED/GREEN tests, full tests, build, whitespace, inspect full diff, and verify no credentials/generated assets/unrelated files are included.
- Do not open a PR while a known contradiction remains unresolved.
- Use squash merge only after required `test` and feature-specific checks are green.
- Run live GitHub write-boundary certification only from trusted `main` after the corresponding workflow has merged.
- Docusaurus work begins only after core Production Certification is green.

---

## Component plans in execution order

1. `docs/superpowers/plans/2026-08-10-production-certification-suite.md`
2. `docs/superpowers/plans/2026-08-10-supply-chain-and-timestamp-certification.md`
3. `docs/superpowers/plans/2026-08-10-docusaurus-documentation-site.md`

## PR sequence

### PR A1: Package-install certification

Implements Production Certification Task 1 only.

Pre-PR evidence:

```text
current main SHA recorded
pyproject console entrypoint re-read
package data inclusion verified
existing required CI job name remains test
wheel and sdist both built
clean-install smoke succeeds outside checkout
full pytest/build/diff-check green
```

### PR A2: Bundle certification

Implements Production Certification Task 2 only.

Required evidence:

```text
six exact assets enforced
SHA256SUMS/manifest verification
source archive traversal/link safety
source capture hashes/identities reconstructed
CSV and JSON logical equivalence
corruption cases fail closed
```

### PR A3: DuckDB consumer certification

Implements Production Certification Task 3. If executed minimum-version probing proves the current `duckdb>=1.1` promise false, dependency/storage changes remain in this dedicated PR and are documented from executed evidence.

### PR A4: Reproducibility and no-change replay

Implements Production Certification Task 4 only. Production code changes are allowed only when a RED test proves missing behavior.

### PR A5: Fault-injection matrix

Implements Production Certification Task 5. Inventory existing tests first and add only missing fail-closed cases. Split into narrower PRs if a new RED case requires touching unrelated production boundaries.

### PR A6: Controlled GitHub draft-release certification

Implements Production Certification Task 6. No live mutation occurs on the PR branch. After merge, dispatch from trusted `main` and require complete certification draft/tag cleanup.

### PR A7: Controlled GitHub Issue certification

Implements Production Certification Task 7. After merge, dispatch from trusted `main`; the certification Issue must end closed and remain isolated from `[DATA ALERT]` identities.

### PR A8: Certification evidence/runbook

Implements Production Certification Task 8 only after A6/A7 live evidence exists. Adds operator docs and the repository PR double-check checklist.

### PR A9: Timestamp semantics

Implements Supply-Chain Task 1. Prefer docs/test-only changes unless RED evidence proves code contradicts the selected build-start `generated_at` semantics.

### PR A10: Artifact attestations

Implements Supply-Chain Tasks 2 and 3. After merge, execute a new `publish=false` official pipeline run and verify provenance with `gh attestation verify` using the exact artifact/run.

### PR A11: Immutable release verification evidence

Implements Supply-Chain Task 4 only after a new post-hardening automated release actually reports immutable and GitHub release verification succeeds for all six assets. Then verify the next unchanged run creates no release.

### PR B1: Canonical public documentation

Implements Docusaurus Task 1. Creates the exact twelve-topic Spanish docs set and reduces README duplication without making GitHub README unusable.

### PR B2: Typed Docusaurus scaffold

Implements Docusaurus Task 2. Immediately before PR, re-verify stable Docusaurus, Node and TypeScript requirements from official Docusaurus docs and compare dependencies against a disposable official TypeScript scaffold.

Required evidence:

```text
all @docusaurus packages same exact version
package-lock committed
npm ci green
npm run typecheck green
npm run build green
root ../docs consumed
superpowers/** excluded
operations/** excluded
explicit sidebar only
```

### PR B3: English i18n parity

Implements Docusaurus Task 3. All twelve public Spanish docs must have exact English native-i18n counterparts. Both per-locale and all-locale builds must pass.

### PR B4: Read-only docs CI

Implements Docusaurus Task 4. Official action tags are resolved to full SHAs before PR. Docs CI has `contents: read` only and runs npm clean install, typecheck and ES/EN builds.

### PR B5: GitHub Pages deployment

Implements Docusaurus Task 5. Before PR, verify Pages source is GitHub Actions and resolve all official Pages actions to full SHAs. After merge, verify `github-pages` environment, public URL and no production-data mutation.

### PR B6: Dependabot and contributor workflow

Implements Docusaurus Task 6 after the Pages URL is live. Add npm Dependabot for `/website`, contributor commands, and verified site links.

### Live completion gate

Implements Docusaurus Task 7 and closes the approved spec only when all of these are true:

```text
protected-main CI green
production publish=false dry-run green
clean wheel/sdist installs green
DuckDB consumer compatibility documented from executed test
cross-format/source/hash certification green
deterministic rebuild and no_change green
fault injection fail-closed green
certification draft release removed and certification tag absent
certification issue closed
artifact attestation verification green
new automated release immutable and release verification green
next unchanged run creates no release
Docusaurus TypeScript check green
Docusaurus ES/EN builds green
GitHub Pages live
no internal superpowers/operations docs exposed
no docs workflow production-data mutation
```

## Double-check template for every implementation PR

Copy this into each implementation PR and fill it with actual evidence:

```markdown
## Double check pre-PR

- [ ] Branch created from current protected `main`; base SHA recorded.
- [ ] Approved spec and exact implementation-plan task re-read.
- [ ] Relevant repository interfaces/files re-opened from current `main`.
- [ ] Unstable upstream versions/actions/settings re-verified from official primary docs.
- [ ] RED test observed for new behavior, or existing behavior documented when no production change was necessary.
- [ ] Targeted GREEN tests pass.
- [ ] `python -m pytest -q` passes.
- [ ] `python -m build` passes.
- [ ] `git diff --check` passes.
- [ ] Full branch diff reviewed against `main`.
- [ ] No credentials, generated datasets, local databases, build directories, or unrelated files included.
- [ ] GitHub Actions changes preserve least privilege and use full-SHA action pins.
- [ ] Live-mutation PRs document namespace isolation and cleanup invariants.
- [ ] Documentation matches actual implemented behavior; no future capability is claimed as current.
```

For Docusaurus PRs append:

```markdown
- [ ] `npm ci` passes from committed lockfile.
- [ ] `npm run typecheck` passes.
- [ ] `npm run build` passes.
- [ ] ES and EN builds pass once i18n is present.
- [ ] `website/build`, `website/node_modules`, and `website/.docusaurus` are not committed.
```
