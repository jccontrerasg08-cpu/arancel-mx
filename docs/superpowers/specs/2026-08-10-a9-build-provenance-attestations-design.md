# A9 Build Provenance Attestations Design

**Status:** Approved design, written specification pending final user review  
**Repository:** `jccontrerasg08-cpu/arancel-mx`  
**Baseline:** `main` at `2178e5d709b2239d2adb7467071d5f648f5307df`  
**Scope:** A9 only. A10 timestamping and A11 release-immutability verification remain separate gates.

## 1. Goal

Add cryptographically verifiable GitHub artifact provenance for the exact six public files produced by a real `Official data pipeline` publication, without changing the six-asset public release contract, weakening legal reconciliation, widening permissions outside the publication boundary, or creating attestations during `publish=false` dry-runs.

The six attested subjects are exactly:

1. `arancel_mx.duckdb`
2. `arancel_mx.csv`
3. `arancel_mx.json`
4. `manifest.json`
5. `SHA256SUMS`
6. `official-sources.tar.gz`

No ZIP produced by `actions/upload-artifact` is a public subject. The Actions ZIP is only transport between jobs.

## 2. Non-goals

A9 does **not**:

- add or remove a public release asset;
- change the dataset schema or row contract;
- alter source capture, legal reconciliation, parsing, or materialization;
- attest dry-run artifacts when `publish=false`;
- publish a second provenance file into the GitHub Release;
- introduce a PAT or external signing key;
- create an SBOM attestation;
- claim SLSA Build Level 3;
- implement independent RFC 3161/TSA timestamping;
- prove GitHub Release immutability;
- replace `SHA256SUMS`, manifest provenance, or bundle certification.

## 3. Authority and upstream contract

A9 uses GitHub's first-party artifact-attestation path:

- `actions/attest` for signed provenance;
- GitHub OIDC for the short-lived signing identity;
- Sigstore-backed signing as implemented by GitHub for public repositories;
- `gh attestation verify` for consumer-style verification.

The implementation must pin `actions/attest` by full commit SHA. The approved initial pin is:

```yaml
uses: actions/attest@508db95dd578ae2727ebd6217d5ba78e4fbda05d # v4.2.1
```

This SHA is the Git object currently referenced by the official `actions/attest` tag `v4.2.1`. Dependabot may later propose updates, but no floating `@v4` tag is allowed in production.

Official references:

- https://github.com/actions/attest
- https://github.com/actions/attest/releases/tag/v4.2.1
- https://docs.github.com/en/actions/concepts/security/artifact-attestations
- https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations
- https://cli.github.com/manual/gh_attestation_verify

## 4. Security model

The attestation is an additional integrity and provenance layer, not a replacement for existing checks.

A release is publishable only if all existing gates succeed first:

```text
official source capture
  -> source identity checks
  -> legal reconciliation
  -> deterministic materialization
  -> six-asset bundle validation
  -> Actions artifact upload
  -> publish job downloads exact artifact
  -> publish job re-verifies exact six-asset bundle
  -> A9 provenance attestation
  -> A9 provenance verification
  -> existing draft-release/upload/remote-verification flow
  -> public release
```

The attestation therefore binds the exact bytes that already passed the repository's independent certification layer to the GitHub Actions workflow identity that is authorized to publish them.

A9 must fail closed. If attestation creation or verification fails, no public release may be published.

## 5. Workflow placement

A9 belongs **only** in the existing `publish` job of `.github/workflows/official-data-pipeline.yml`.

Reasons:

1. `build-and-verify` currently operates with `contents: read` and must remain a non-publishing boundary.
2. `publish=false` must remain non-mutating with respect to GitHub releases, issues, and attestations.
3. The publish job already downloads the exact Actions artifact and verifies it before mutation.
4. Attestation permissions should exist only in the job that is already authorized to publish.

The A9 steps execute after the downloaded artifact has passed exact-bundle verification and before the release becomes public.

## 6. Permissions

Workflow-level/default permissions remain:

```yaml
permissions:
  contents: read
```

The `publish` job receives only the permissions it needs:

```yaml
permissions:
  contents: write
  attestations: write
  id-token: write
```

No `artifact-metadata: write` permission is added for A9. The six subjects are ordinary release files, not registry artifacts, and A9 does not use `push-to-registry` or organization linked-artifact storage records.

No PAT, deploy key, cloud KMS key, or external secret is introduced.

## 7. Subject selection

The action receives an explicit newline-delimited `subject-path` list. A broad glob is rejected because it could silently attest a seventh file if the release directory contract drifted.

Conceptual workflow input:

```yaml
with:
  subject-path: |
    out/publish/arancel_mx.duckdb
    out/publish/arancel_mx.csv
    out/publish/arancel_mx.json
    out/publish/manifest.json
    out/publish/SHA256SUMS
    out/publish/official-sources.tar.gz
```

The actual directory must match the existing publish job's downloaded artifact path. The implementation may not rename or duplicate the six public files solely for attestation.

`actions/attest` supports multiple subjects in one invocation. A9 therefore creates one provenance attestation containing references to all six subjects instead of six independent attestations.

## 8. Attestation verification

Creation alone is not sufficient. The same publish job must verify all six subjects before proceeding to public release publication.

Each file must pass `gh attestation verify` with both repository and signer-workflow identity constrained:

```bash
gh attestation verify "$asset" \
  --repo jccontrerasg08-cpu/arancel-mx \
  --signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml
```

GitHub CLI's default predicate check for this command is the SLSA provenance v1 predicate. A9 must not weaken that default with a broader predicate type.

The verification loop must enumerate the same six explicit asset names used by `PUBLIC_RELEASE_ASSETS`/the release contract. Any missing file, seventh file, digest mismatch, untrusted signer, wrong workflow, unavailable attestation, or verification error fails the publish job.

`GH_TOKEN` may use the existing `github.token`; no separate credential is allowed.

## 9. Release ordering and failure semantics

Preferred ordering:

1. Download verified Actions artifact.
2. Verify exact six-asset set and existing checksum/manifest/cross-format contracts.
3. Generate one provenance attestation over the six exact local files.
4. Verify all six local files against GitHub's attestation API and the exact signer workflow.
5. Continue the existing release lifecycle.
6. Publish only after existing remote-release verification succeeds.

If A9 fails at steps 3 or 4, the job exits nonzero before a public release is created. Existing structured publication failure diagnostics and `[DATA ALERT]` behavior remain responsible for production notification.

No attestation cleanup is attempted on a failed publication. Attestations are immutable provenance records for the exact subject digests and workflow execution; deleting a valid attestation merely because a later release step failed would remove useful audit evidence. A future successful build with different bytes receives its own attestation.

## 10. Dry-run semantics

`workflow_dispatch` with `publish=false` must continue to behave exactly as certified by run `31451589441`:

- `build-and-verify` may build and upload the six-file Actions artifact;
- `publish` is skipped;
- no provenance attestation is created;
- notification mutation remains disabled;
- no release or tag is created;
- `main` remains unchanged.

A static workflow contract test must enforce that the attestation action appears only in the conditional `publish` job and not in `build-and-verify` or `notify`.

## 11. Testing strategy

A9 uses TDD and adds policy tests before editing the workflow.

Required test coverage:

- workflow contains `actions/attest` pinned to the full approved SHA;
- floating `actions/attest@v4` is forbidden;
- `publish` has `contents: write`, `attestations: write`, and `id-token: write`;
- `build-and-verify` does not gain attestation/OIDC write permissions;
- `notify` does not gain attestation/OIDC write permissions;
- subject list is exactly the six public release assets;
- attestation occurs after downloaded-bundle verification and before public release publication;
- `gh attestation verify` constrains both `--repo` and `--signer-workflow`;
- all six subjects are verified;
- `publish=false` keeps the `publish` job skipped by the existing condition;
- existing production release namespace and issue namespace remain unchanged;
- full repository test/build/clean-install/whitespace gates remain green.

No unit test may mock away the exact asset names, permission names, action SHA, signer workflow path, or ordering contract.

## 12. Live certification gate

A9 is not complete merely because CI is green.

After merge to protected `main`, certification requires a controlled **real publication path** that is safe and intentional. Because `publish=false` correctly skips A9, that dry-run cannot prove the signing boundary.

The implementation plan must therefore define a non-destructive certification strategy before enabling A9 for the next production publication. The preferred strategy is to verify A9 on the next legitimate changed official dataset release rather than create a fake `data-*` release.

If a separate live certification workflow is proposed instead, it must use a `certification-*` namespace and may never attest or publish a fake `data-YYYY.MM.DD` dataset. That would be a separate approved implementation decision and must preserve the isolation principles already established by `Production certification`.

Until a live A9 attestation is observed and independently verified, documentation must say **implemented / CI-verified**, not **live-certified**.

## 13. Consumer verification documentation

After A9 is implemented, README/operations documentation should show how a consumer can verify a downloaded asset without trusting the release page alone:

```bash
gh attestation verify arancel_mx.duckdb \
  --repo jccontrerasg08-cpu/arancel-mx \
  --signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml
```

The same command shape applies to each of the other five release assets.

Documentation must distinguish:

- `SHA256SUMS`: local digest consistency;
- `manifest.json`: dataset/source/run provenance inside the release contract;
- GitHub artifact attestation: cryptographically signed workflow identity + subject digest provenance.

None of those layers is described as a legal signature on the underlying Mexican source documents.

## 14. Alternatives considered

### A. Attest the Actions ZIP

Rejected. The ZIP is transport-only and is not one of the six files consumers download from the public release.

### B. Six independent attestations

Rejected. `actions/attest` supports multiple subjects in one invocation, so six separate signing actions add noise and failure surface without improving the current trust boundary.

### C. Attest in `build-and-verify`

Rejected for A9. It would require signing permissions in the source-fetch/build boundary and would create attestations during `publish=false` runs. A9 intentionally limits signing to real publication attempts.

### D. Add external Cosign key/KMS or PAT

Rejected. GitHub OIDC + first-party attestation supports the required repository provenance without long-lived signing secrets.

### E. Publish attestation bundle as a seventh release asset

Rejected. The public contract must remain exactly six assets. GitHub stores the attestation and `gh attestation verify` retrieves it through the attestation service.

## 15. Acceptance criteria

A9 is implementation-complete when all of the following are true:

1. The public release contract remains exactly six assets.
2. `actions/attest` is pinned to `508db95dd578ae2727ebd6217d5ba78e4fbda05d` or a newer full SHA explicitly re-verified immediately before the implementation PR.
3. Only the `publish` job receives `attestations: write` and `id-token: write`.
4. One provenance attestation identifies exactly the six public asset subjects.
5. Every subject is verified with the exact repository and signer workflow before public release publication.
6. `publish=false` still creates no attestation, release, tag, or Issue mutation.
7. A failed attestation or verification prevents publication.
8. Existing source, reconciliation, bundle, publisher, notification, package-install, DuckDB compatibility, and production-certification tests remain green.
9. CI, build, clean-install wheel/sdist, DuckDB minimum-compatibility probe, and whitespace checks pass on the final PR head.
10. The implementation PR records the exact action SHA, official upstream references, permission diff, workflow ordering, test evidence, and double-check evidence.
11. Documentation does not claim live certification until an actual signed subject has been independently verified.

## 16. Pre-PR double-check contract

Before the implementation PR is opened, verify and record:

- current protected `main` SHA;
- branch is based on that SHA or is 0 commits behind after update;
- approved A9 spec is unchanged or any change has explicit approval;
- current official `actions/attest` release/tag and full SHA;
- current GitHub attestation permission requirements;
- exact six-subject list matches the repository's release constant;
- no seventh public asset is introduced;
- workflow default remains `contents: read`;
- only `publish` receives signing permissions;
- no PAT/secrets are added;
- `publish=false` condition remains non-mutating;
- signer workflow path is exact;
- tests prove ordering and permissions rather than merely string presence;
- full CI/build/compatibility/clean-install/whitespace gates are green;
- diff has no unrelated source, parser, schema, legal, or dataset changes;
- reviews and threads are resolved before merge.
