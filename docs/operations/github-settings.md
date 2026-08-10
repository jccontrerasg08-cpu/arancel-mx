# GitHub production settings runbook

This document is the maintainer checklist for repository settings that cannot be enforced safely from committed source alone. It defines the expected production boundary for `arancel-mx`; it does **not** assert that a setting is enabled until a maintainer verifies it in the GitHub UI.

The repository code is designed around the stable GitHub Actions job check `test`, read-only default workflow permissions, job-scoped production writes, immutable data releases, and protected `main`. The workflow display name is `CI`, but GitHub Rulesets require the emitted check-run context, which is the job name `test`.

## 1. Actions permissions

UI path: **Settings → Actions → General**.

1. Open **Workflow permissions**.
2. Select **Read repository contents and packages permissions** as the default workflow permission.
3. Do not switch the repository default to broad read/write permissions. The production workflow grants writes only to the jobs that need them.
4. **Allow GitHub Actions to create and approve pull requests** may remain enabled so maintenance automation can open PRs.
5. Verify that no project workflow self-approves code or data PRs. The demo workflow may create a PR, but review/merge remains subject to the normal `main` policy.

Expected repository boundary:

```text
default GITHUB_TOKEN: contents read
Official data pipeline / build-and-verify: contents read
Official data pipeline / publish: contents write
Official data pipeline / notify: contents read + issues write
generate-demo: contents write + pull-requests write
CI job test: contents read
```

## 2. Release immutability

UI path: **Settings → General → Releases**.

1. Locate the release protection/immutability controls.
2. Set **Enable release immutability** to ON before autonomous publication is activated on trusted `main`.
3. Confirm that an existing `data-YYYY.MM.DD` release/tag is not intended to be overwritten. A same-date second change must fail closed and surface `release_tag_collision` rather than mutate an existing public release.

This setting is a prerequisite for treating GitHub Releases as an immutable public dataset channel.

## 3. Main branch ruleset

UI path: **Settings → Rules → Rulesets**.

Create or edit the production ruleset with the following values:

1. **Enforcement: Active**.
2. **Target: `main`** or the repository default branch when it resolves to `main`.
3. Turn **Require a pull request before merging** ON.
4. Add required status check **`test`**.
5. Source: **GitHub Actions**.
6. Turn **Require branches to be up to date before merging** ON for that required check.
7. Turn **Require conversation resolution before merging** ON.
8. Turn **Block force pushes** ON.
9. Turn **Block deletions** ON.
10. Turn **Require linear history** ON only after the squash-only merge strategy in the next section is active.
11. Do not grant a workflow a bypass merely to publish tariff data. The production data workflow publishes Releases, not commits to protected `main`.

The exact required status check is **`test`**. GitHub Actions emits this context from the `test` job in `.github/workflows/ci.yml`; the workflow itself is displayed as `CI`. If GitHub asks you to select a check from recent history, select `test` with GitHub Actions as its source.

## 4. Pull request and merge behavior

UI path: **Settings → General → Pull Requests**.

Configure:

- **Squash merging: ON**.
- **Merge commits: OFF**.
- **Rebase merging: OFF**.
- **Automatically delete head branches: ON**.
- **Always suggest updating pull request branches: ON**.
- Auto-merge is optional. If enabled, use it only after `test` is required and only for already-reviewed maintenance PRs that satisfy the ruleset.

Using squash-only merging keeps `main` compatible with the linear-history requirement and avoids automation branches becoming permanent history noise.

## 5. Advanced Security

UI path: **Settings → Advanced Security**.

Enable the controls available for this public repository:

1. **Dependabot alerts: ON**.
2. **Dependabot security updates: ON**.
3. **Secret scanning: ON where available**.
4. **Push protection: ON where available**.
5. **Code scanning/default setup: ON where available**.
6. **Private vulnerability reporting: ON**.

Dependabot configuration is committed in `.github/dependabot.yml`; the repository settings above enable the corresponding security and alerting capabilities where GitHub exposes them.

## 6. Production activation order

Use this order before allowing scheduled publication to mutate GitHub Releases:

1. Confirm `test` has passed on the hardened implementation.
2. Set default Actions permissions to read-only.
3. Enable release immutability.
4. Enable squash-only merge behavior.
5. Activate the `main` ruleset and select `test` from GitHub Actions as required.
6. Enable the available Advanced Security controls.
7. Manually dispatch **Official data pipeline** with `publish=false` and inspect the build result, `pipeline-result.json`, manifest provenance, and any generated artifact.
8. Only after the dry-run is healthy, permit a trusted `main` execution with `publish=true` or allow the next scheduled production run.

## Verification checklist

Record these after checking the live repository UI. Leave an item unchecked until it has actually been verified.

- [ ] Settings → Actions → General uses **Read repository contents and packages permissions** by default.
- [ ] Actions PR creation is permitted only as needed; no workflow self-approves a code/data PR.
- [ ] Settings → General → Releases has **Enable release immutability** ON.
- [ ] Settings → Rules → Rulesets has an Active ruleset targeting `main`.
- [ ] The `main` ruleset requires a pull request before merging.
- [ ] The exact required status check is **`test`**.
- [ ] The required check source is **GitHub Actions**.
- [ ] Required branches must be up to date before merging.
- [ ] Conversation resolution is required.
- [ ] Force pushes and branch deletions are blocked.
- [ ] Linear history is required after squash-only merging is active.
- [ ] Squash merging: ON.
- [ ] Merge commits: OFF.
- [ ] Rebase merging: OFF.
- [ ] Automatically delete head branches: ON.
- [ ] Always suggest updating pull request branches: ON.
- [ ] Dependabot alerts: ON.
- [ ] Dependabot security updates: ON.
- [ ] Secret scanning: ON where available.
- [ ] Push protection: ON where available.
- [ ] Code scanning/default setup: ON where available.
- [ ] Private vulnerability reporting: ON.
- [ ] A trusted manual `publish=false` production dry-run completed without repository/release/issue mutation.
- [ ] After the first healthy live cycle, the release/no-change behavior and automation-alert recovery were verified against the workflow run.
