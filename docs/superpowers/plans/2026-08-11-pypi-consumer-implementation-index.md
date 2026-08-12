# PyPI Consumer 0.2.0 Implementation Rollout Index

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` or `superpowers:executing-plans`, with `superpowers:test-driven-development` for every behavior task and `superpowers:verification-before-completion` before each completion claim.

**Goal:** Deliver `arancel-mx 0.2.0` as a consumer-first Python package whose exact wheel/sdist bytes are built once, published to TestPyPI, externally certified, manually approved, published unchanged to PyPI, and externally re-certified.

**Architecture:** Keep the official-data ETL/release subsystem intact. Add a separate consumer boundary under `src/arancel_mx/consumer/`, keep `data-*` GitHub Releases as the dataset distribution channel, use verified local cache + read-only DuckDB for users, and separate fast deterministic PR/main checks from live tag-only registry certification.

**Planning baseline:** protected `main` commit `ae64617d2c6e9483c2485cffd5d5eed18ca6ed21`.

## Non-negotiable constraints

- Code package and dataset versions remain independent.
- Package target: `arancel-mx 0.2.0`.
- Package tags: `pkg-v0.2.0rcN` and `pkg-v0.2.0`.
- Dataset tags remain `data-YYYY.MM.DD`.
- Never create a GitHub Release for `pkg-v*`; `/releases/latest` must continue resolving to the newest public `data-*` release.
- Wheel never embeds the large DuckDB dataset.
- Consumer DuckDB is read-only.
- Offline mode performs zero network access.
- Failed/partial downloads never become verified cache.
- Public stable 0.2.x surface: `Dataset`, public immutable models, documented exceptions, documented method signatures.
- Existing maintainer commands remain available.
- `doctor`: `0=HEALTHY`, `1=DEGRADED`, `2=UNHEALTHY`.
- Blocking release matrix: Ubuntu x64, Windows x64, macOS ARM64, macOS Intel x CPython 3.11, 3.12, 3.13, 3.14.
- TestPyPI/PyPI use Trusted Publishing/OIDC.
- `id-token: write` only on publishing jobs.
- Production `pypi` environment requires human approval.
- No permanent PyPI/TestPyPI upload token.
- External consumer certification jobs do not checkout repository source.
- Every third-party GitHub Action is pinned to a reviewed full 40-character commit SHA.
- Tests verify full-SHA pinning and approved action identity. They do not redundantly hardcode the previous SHA in a way that makes a legitimate reviewed upgrade fail solely because the test still expects the old pin.
- No live TestPyPI/PyPI mutation until deterministic implementation/preflight is complete and green.

## Normative design

Implementation must conform to:

- `docs/superpowers/specs/2026-08-11-pypi-consumer-distribution-and-external-certification-design.md`
- `docs/superpowers/specs/2026-08-11-pypi-consumer-distribution-design-self-review-addendum.md`

If a plan conflicts with the approved spec, the spec wins unless an explicit new design decision is reviewed and documented.

## Plan map

### Plan A: Consumer core

`docs/superpowers/plans/2026-08-11-pypi-consumer-core.md`

Owns:
- public exception hierarchy;
- immutable public models;
- runtime package version;
- configuration precedence;
- exact `data-*` release discovery;
- six-asset remote contract;
- HTTP streaming/retries;
- cache layout, locking, `.part`, atomic promotion, `verified.json` last;
- manifest/SHA/API-digest/schema/DuckDB integrity;
- `Dataset.latest()`, `.version()`, `.open()`;
- lookup/search/parent/children/provenance;
- strict offline behavior;
- cache reuse/upgrade compatibility.

### Plan B: Consumer CLI + doctor

`docs/superpowers/plans/2026-08-11-pypi-consumer-cli-doctor.md`

Owns:
- consumer parser composition while preserving maintainer commands;
- deterministic JSON/CSV/table output;
- `lookup`, `search`, `parent`, `children`, `provenance`;
- `data status/download/update/list/path/verify`;
- `doctor` checks, human/JSON format and exit codes;
- expected-error boundary;
- deterministic CLI end-to-end fixture;
- Spanish/English consumer docs.

### Plan C: Package certification + PR/main preflight

`docs/superpowers/plans/2026-08-11-pypi-package-certification.md`

Owns:
- single package-version source;
- complete PyPI metadata;
- consumer vs maintainer dependency split;
- `py.typed` and typing contract;
- changelog and PyPI README content;
- wheel/sdist content contracts;
- `twine check`, `check-wheel-contents`, `pip check`;
- clean wheel installation;
- isolated sdist rebuild/install;
- dependency floor/latest certification;
- upgrade-safe full-SHA GitHub Action policy;
- `.github/workflows/python-package-preflight.yml`;
- Python 3.11-3.14 support evidence;
- deterministic local package preflight script.

### Plan D: TestPyPI -> external certification -> PyPI

`docs/superpowers/plans/2026-08-11-testpypi-pypi-publication.md`

Owns:
- package tag/version validation;
- proof tag == protected green main tip;
- build-once distribution hashes;
- source-free certification artifact;
- TestPyPI OIDC publication;
- digest-verified TestPyPI roundtrip;
- blocking 16-cell OS/Python matrix;
- pip/pipx/uv + wheel/sdist install modes;
- destructive external tests;
- manual `pypi` environment gate;
- same-byte PyPI publication;
- post-PyPI matrix;
- package alert/yank/patch response policy;
- RC lifecycle;
- manual account/environment/Trusted Publisher setup;
- package-name preflight;
- package provenance/attestation evidence.

## Implementation PR sequence

1. Consumer errors/models/version/config.
2. Exact release resolver and remote asset contract.
3. HTTP streaming + verified atomic cache transaction.
4. Integrity validation: manifest/checksum/API digest/schema/DuckDB.
5. Query engine + public `Dataset` facade.
6. Offline + manager semantics and cache reuse.
7. Consumer CLI + deterministic output.
8. Doctor + support/error contract.
9. Consumer documentation.
10. Package metadata/dependency split/typing/changelog.
11. Wheel + sdist clean certification and build tooling.
12. Cross-platform PR/main package preflight.
13. Release validation/build-once/hash/source-free probe tooling.
14. Publish workflow contract, still deterministic/no live registry.
15. Prepare and merge `0.2.0rc1` version change on protected main.
16. First live TestPyPI candidate and external certification.
17. Fixes produce `rc2+`; uploaded versions are never overwritten.
18. Prepare final `0.2.0` on protected green main.
19. Final exact-byte TestPyPI certification.
20. Human approval of `pypi` environment.
21. Same-byte PyPI publication.
22. Post-PyPI full external certification.

## TDD execution rule for every behavior task

Every implementation task follows this exact local sequence:

```text
1. write one focused failing test
2. run it and confirm the expected failure reason
3. implement the minimum behavior
4. rerun focused test to green
5. run the relevant subsystem suite
6. run broader regression suite when boundary changed
7. commit with one responsibility
```

No task is marked complete because code merely looks correct.

## Stage gates

### Gate 0: planning

- design merged;
- implementation branch contains docs only;
- current main baseline recorded;
- no registry mutation.

### Gate 1: deterministic consumer implementation

```bash
python -m pytest tests/consumer tests/test_cli.py tests/certification/test_consumer.py -q
python -m pytest -q
python -m build
```

### Gate 2: package preflight

```bash
python -m build
twine check dist/*
check-wheel-contents dist/*.whl
python -m pytest tests/package -q
python scripts/package_preflight.py
```

plus Linux/Windows/macOS preflight jobs green.

### Gate 3: publication workflow deterministic contract

Tests must prove:
- tag/version equality;
- tag SHA == current protected main SHA;
- mandatory main checks green;
- build once;
- immutable distribution hashes;
- TestPyPI precedes external matrix;
- external matrix precedes production environment;
- RC path cannot publish production PyPI;
- PyPI uses original build artifact;
- post-PyPI depends on successful production upload;
- no source checkout in external jobs;
- least-privilege OIDC permissions.

### Gate 4: live TestPyPI

The first external certification boundary begins with `0.2.0rc1`. Until the real TestPyPI candidate has passed its live matrix, status is not `externally-certified`.

### Gate 5: production

`0.2.0` is `production-certified` only after:
1. final bytes pass TestPyPI roundtrip and all blocking gates;
2. human approves `pypi` environment;
3. same bytes publish to PyPI;
4. exact-version installs from PyPI pass post-publication matrix.

## Repository cleanup status before implementation

The planning baseline has intentionally been reduced to three branches:

```text
main
docs/pypi-consumer-implementation-plan
feat/audit-14-20-24-docs-vucem
```

The preserved `feat/audit-14-20-24-docs-vucem` branch contains unrelated future work and must not be merged wholesale into this package rollout. Extract future pieces through small focused PRs.

Dependabot PRs #6, #7 and #8 were closed rather than merged. Their branches are no longer part of the active branch inventory. Action upgrades will be revisited in Plan C as reviewed, atomic workflow-pin changes against the then-current main baseline.

## Status vocabulary

Use exactly this progression:

```text
design-approved
implementation-plan-approved
implementation-complete
deterministic-ci-verified
testpypi-configured
rc-externally-certified
final-testpypi-certified
pypi-published
post-pypi-certified
0.2.0-production-certified
```

Do not report a later state before the corresponding real gate has succeeded.
