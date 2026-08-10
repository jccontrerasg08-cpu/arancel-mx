# Production Certification Rollout Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the approved production-certification and Docusaurus design in small, independently reviewable PRs with an explicit double-check before every PR.

**Architecture:** This index does not add implementation details beyond the component plans. It fixes execution order, PR boundaries, prerequisite relationships, and the pre-PR verification gate so certification, GitHub mutations, supply-chain provenance, and documentation rollout cannot be mixed accidentally.

**Tech Stack:** See the linked plans.

## Global Constraints

- Every implementation PR starts from current protected `main`, not from a stale feature branch.
- Before every PR, compare branch vs `main`, re-read the approved spec and relevant plan, re-check current upstream docs for any unstable dependency/action/settings assumption, run targeted tests plus full tests/build/whitespace, inspect the full diff, and verify no credentials/generated assets are included.
- Do not open a PR while a known contradiction remains unresolved.
- Use squash merge only after the required `test` check and any feature-specific checks are green.
- Run live GitHub write-boundary certification only from trusted `main` after the relevant workflow PR has merged.
- Docusaurus work begins only after core production certification is green.

---

## Plans and order

1. `2026-08-10-production-certification-suite.md`
2. `2026-08-10-supply-chain-and-timestamp-certification.md`
3. `2026-08-10-docusaurus-documentation-site.md`
4. `2026-08-10-docusaurus-typescript-quality.md`

The TypeScript quality plan is implemented alongside the first Docusaurus PR and enforced in docs CI before Pages deployment.

## PR sequence

### PR A1: Package-install certification

Implements Production Certification Task 1 only.

Pre-PR double check:

```text
current main SHA
pyproject console entrypoint
package data inclusion
existing CI job name remains test
wheel and sdist both built
clean-install smoke succeeds outside checkout
full pytest/build/diff-check green
```

### PR A2: Bundle and DuckDB consumer certification

Implements Production Certification Tasks 2 and 3 only if the combined diff remains focused; split into A2a/A2b if DuckDB compatibility requires a dependency-floor/storage-format change.

Required evidence:

```text
six exact assets
source archive safe paths and hashes
CSV/JSON equivalence
DuckDB logical consumer checks
executed minimum DuckDB compatibility probe
```

### PR A3: Reproducibility and fault injection

Implements Production Certification Tasks 4 and 5. Split if any fault-injection RED test exposes a production-code change outside release/source boundaries.

### PR A4: Controlled GitHub release certification

Implements Production Certification Task 6. No live mutation occurs on the PR branch. After merge, dispatch from trusted `main` and require complete draft/tag cleanup.

### PR A5: Controlled GitHub issue certification

Implements Production Certification Task 7. After merge, dispatch from trusted `main`; the certification Issue must end closed and remain isolated from `[DATA ALERT]` identities.

### PR A6: Certification runbook and checklist

Implements Production Certification Task 8 only after A4/A5 live evidence exists.

### PR A7: Timestamp semantics

Implements Supply-Chain Task 1. Prefer documentation/test-only change unless RED evidence proves code contradicts the chosen build-start semantics.

### PR A8: Artifact attestations

Implements Supply-Chain Tasks 2 and 3. After merge, execute a new `publish=false` official pipeline run and verify provenance with GitHub CLI.

### PR A9: Immutable release verification docs

Implements Supply-Chain Task 4 only after a new post-hardening automated release actually reports immutable and `gh release verify` / `verify-asset` have succeeded.

### PR B1: Docusaurus scaffold + TypeScript quality

Implements Docusaurus Task 1 and Docusaurus TypeScript Quality Task 1.

Before PR, re-verify:

```text
Docusaurus stable version
Node minimum
TypeScript minimum
official TypeScript support packages
npm lockfile clean install
npm typecheck
npm build
```

### PR B2: Canonical docs source + ES/EN parity

Implements Docusaurus Tasks 2 and 3. Must prove `docs/superpowers/**` is absent from generated public output and public sidebar docs have English translations.

### PR B3: Docs CI + TypeScript enforcement

Implements Docusaurus Task 4 and TypeScript Quality Task 2. Read-only workflow only.

### PR B4: GitHub Pages deployment

Implements Docusaurus Task 5. Before PR, resolve and record full SHAs for official Pages actions. After merge, verify Pages environment and deployment URL.

### PR B5: Dependabot + contributor/public links

Implements Docusaurus Task 6 after the Pages URL is live.

### Live completion gate

Implements Docusaurus Task 7 and the overall spec completion criteria.

Require all of:

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
Docusaurus ES/EN builds green
GitHub Pages live
no internal superpowers docs exposed
no docs workflow production-data mutation
```

## Double-check template for every PR

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
- [ ] `npm run typecheck` passes when TypeScript support is present.
- [ ] `npm run build` passes.
- [ ] ES and EN builds pass when i18n is present.
- [ ] `website/build`, `website/node_modules`, and `.docusaurus` are not committed.
```
