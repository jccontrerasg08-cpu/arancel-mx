# Production Hardening Execution Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement the linked plans task-by-task.

**Goal:** Provide the dependency order and review gates for the three approved `arancel-mx` production-hardening implementation plans.

## Execution order

1. [`2026-08-10-core-data-correctness.md`](./2026-08-10-core-data-correctness.md)
   - Makes the source/data layer trustworthy enough to automate.
   - Must finish first because the publisher must never automate the current optional reconciliation path.

2. [`2026-08-10-autonomous-release-alerts.md`](./2026-08-10-autonomous-release-alerts.md)
   - Builds on schema v2, source identity, reconciliation, and no-change behavior.
   - Introduces GitHub mutation only after the core build is fail-closed.

3. [`2026-08-10-repository-supply-chain-hardening.md`](./2026-08-10-repository-supply-chain-hardening.md)
   - Locks production dependencies, hardens auxiliary workflows, aligns docs, and configures repository policy.
   - The dependency constraints portion should be completed before the final autonomous-workflow cutover because the production workflow consumes the constraints file.

## Cross-plan dependency exception

The following task from plan 3 may be pulled forward while plan 2 is being implemented:

- Plan 3, Task 1: `requirements/production-build.txt`.

This is the only intentional cross-plan dependency. Do not enable automatic GitHub Release publication until all core-data tasks and the production constraints file are green.

## Self-review corrections that apply to all plans

These corrections are mandatory and supersede any narrower wording in the individual task descriptions.

### Legacy `data-2026.08.10` bootstrap

The currently published release predates schema v2 and has no `source_identity` field. That is a migration condition, not corruption.

- `source_identity_from_manifest()` remains strict for schema-v2 manifests.
- `fetch_previous_release.py` must accept a valid legacy manifest and mark it as `legacy_baseline` rather than rejecting it.
- When the latest valid release is legacy, the first schema-v2 production run must perform a full reconciled build instead of returning `no_change`.
- This one-time schema/provenance bootstrap is considered a meaningful release change even if canonical tariff rows are logically equal.
- If `data-YYYY.MM.DD` already exists on that UTC date, publication remains blocked rather than overwritten; the next date/run can publish the schema-v2 bootstrap release.
- Once one schema-v2 release exists, all later no-change decisions must use strict complete source identity, including captured legal evidence.

This avoids unsafe guessing about dataset roles in the old manifest and ensures the new DOF evidence becomes part of the auditable baseline.

### Safe branch dry runs

A manually dispatched `publish=false` run may execute the read-only test/discovery/reconciliation/build/verification path from an implementation branch. GitHub mutation remains forbidden there.

The publisher job must require both:

```text
publish enabled AND github.ref == refs/heads/main
```

Scheduled runs exist only on merged `main`, and publication-enabled manual runs are trusted-main only. Therefore a branch dry run can validate live sources without acquiring `contents: write` behavior.

### Production Python toolchain pin

The production constraints task must pin the installer/build backend as well as runtime/dev packages:

```text
pip==26.2.1
setuptools==83.0.0
```

`setuptools 83.0.0` is the stable release available before this design date and should replace the open-ended build-system requirement for official reproducible builds. The implementation must either set `[build-system].requires = ["setuptools==83.0.0"]` or prove through a failing/passing policy test that an equivalent exact PEP 517 build-backend constraint is enforced.

CI and the official data workflow must install the known-good pip version explicitly before installing the project under `requirements/production-build.txt`; they must not run an unconstrained `pip install --upgrade pip`.

## Review gates

### Gate A: Core data ready

Required evidence:
- full pytest suite green;
- package build green;
- legal reconciliation blocks mismatches;
- actual retrieval timestamps preserved;
- strict schema-v2 source identity returns `no_change` when identical;
- a legacy v1 baseline forces one schema-v2 bootstrap build rather than being silently treated as current;
- schema v2 manifest provenance validated.

### Gate B: Automation dry run ready

Required evidence:
- production workflow contract tests green;
- build job has read-only permissions;
- publisher alone has `contents: write`;
- notifier alone has `issues: write`;
- manual branch `publish=false` dry run succeeds without a GitHub Release mutation;
- publisher explicitly requires trusted `main`;
- failure simulation creates/upserts a test alert only in a controlled verification path.

### Gate C: Autonomous production ready

Required evidence:
- release immutability enabled;
- `main` ruleset active with `CI / test` required;
- repository default Actions token remains read-only;
- exact production dependency and Python build-tool constraints in use;
- all Actions references pinned to commit SHA;
- documentation reflects automatic fail-closed behavior.

## Final verification

After all three plans:

```bash
python -m pip install "pip==26.2.1"
python -m pip install -c requirements/production-build.txt -e ".[dev]"
python -m pytest -q
python -m build
git diff --check
```

Then run one manual `publish=false` workflow dispatch from the implementation branch to validate read-only live-source behavior, merge through protected `main`, and use a trusted-main manual/scheduled run for the first publication-enabled cycle.
