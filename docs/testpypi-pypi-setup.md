# TestPyPI and PyPI Trusted Publisher setup checklist

The [`publish-python-package.yml`](../.github/workflows/publish-python-package.yml)
workflow publishes the Python package with GitHub Actions Trusted Publishing
(OIDC). It stores **no** upload tokens. The repository can prove the workflow's
intent and structure, but it cannot prove the registry and environment
configuration that lives in the PyPI and GitHub web UIs. Complete this checklist
once, before creating the first `pkg-v*` tag.

## Prerequisites

1. Create a PyPI account and a separate TestPyPI account, each with 2FA enabled.
2. Confirm the normalized project name `arancel-mx` is available on both
   registries, or that you already own it. Use
   `scripts/check_package_registry_name.py` when available; otherwise check
   `https://pypi.org/project/arancel-mx/` and
   `https://test.pypi.org/project/arancel-mx/`.
3. Confirm no long-lived package secret exists: there must be no `PYPI_TOKEN`,
   `TEST_PYPI_TOKEN`, `.pypirc`, or equivalent credential in the repository,
   organization, or environment secrets.

## GitHub environments

4. Create a GitHub Actions environment named `testpypi`.
5. Create a GitHub Actions environment named `pypi`.
6. Add at least one required reviewer to the `pypi` environment so production
   publication waits for manual approval. TestPyPI may publish without a
   reviewer.

## Trusted Publisher configuration

7. On TestPyPI, add a **pending** Trusted Publisher for this repository with:
   - Owner: `jccontrerasg08-cpu`
   - Repository: `arancel-mx`
   - Workflow filename: `publish-python-package.yml`
   - Environment: `testpypi`
8. On PyPI, add the same Trusted Publisher but with environment `pypi`.

## Release invariants (enforced by the workflow and tests)

- Tags use the `pkg-vX.Y.Z` form and must equal `project.version` in
  `pyproject.toml`. Pre-release tags use `pkg-vX.Y.ZrcN`.
- Pre-release tags publish to TestPyPI only; final tags additionally publish to
  PyPI after manual approval.
- The distribution is built once and the same bytes are uploaded to both
  registries; hashes are re-verified before each upload.
- The workflow never creates a GitHub Release. Only `data-YYYY.MM.DD` releases
  back the public dataset download links.

## Before the first live tag

9. Re-verify the current `pypa/gh-action-pypi-publish` commit SHA and update the
   pin if a newer reviewed release exists.
10. Confirm `main` is green, set `project.version` to the intended value, and
    create `pkg-vX.Y.Z` (or `pkg-vX.Y.ZrcN`) at the current `main` tip.

Repository tests verify this document and the workflow structure, but live
publication only begins after a maintainer has completed the UI steps above.
