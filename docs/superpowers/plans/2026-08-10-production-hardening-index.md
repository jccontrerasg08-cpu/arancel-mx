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

## Review gates

### Gate A: Core data ready

Required evidence:
- full pytest suite green;
- package build green;
- legal reconciliation blocks mismatches;
- actual retrieval timestamps preserved;
- identical source identity returns `no_change`;
- schema v2 manifest provenance validated.

### Gate B: Automation dry run ready

Required evidence:
- production workflow contract tests green;
- build job has read-only permissions;
- publisher alone has `contents: write`;
- notifier alone has `issues: write`;
- manual `publish=false` dry run succeeds without a GitHub Release mutation;
- failure simulation creates/upserts a test alert only in a controlled verification path.

### Gate C: Autonomous production ready

Required evidence:
- release immutability enabled;
- `main` ruleset active with `CI / test` required;
- repository default Actions token remains read-only;
- exact production dependency constraints in use;
- all Actions references pinned to commit SHA;
- documentation reflects automatic fail-closed behavior.

## Final verification

After all three plans:

```bash
python -m pip install -c requirements/production-build.txt -e ".[dev]"
python -m pytest -q
python -m build
git diff --check
```

Then run one manual `publish=false` workflow dispatch from the implementation branch to validate read-only live-source behavior, merge through protected `main`, and use a trusted-main manual/scheduled run for the first publication-enabled cycle.
