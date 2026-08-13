# Open Source Check List

Walk through these items before tagging a public package revision or treating a new clone as release-ready.

This is the CFPB [open-source-project-template](https://github.com/cfpb/open-source-project-template/blob/main/opensource-checklist.md) checklist, rewritten for `arancel-mx`: Apache-2.0, not a U.S. government public-domain release.

- **Has PII been removed?**
  - Tracked text is scanned by `tests/test_public_distribution.py` (`test_tracked_text_contains_no_credentials_or_private_absolute_paths`).
  - Inspect images under `docs/` for personal data, credentials, or non-public identifiers. Official SNICE/DOF diagrams are expected.

- **Have security vulnerabilities been remediated?**
  - Follow [SECURITY.md](SECURITY.md).
  - Maintainer GitHub controls: [docs/operations/github-settings.md](docs/operations/github-settings.md).
  - References: [OWASP Top 10](https://owasp.org/www-project-top-ten/), [National Vulnerability Database](https://nvd.nist.gov/), [SANS SWAT Checklist](https://www.sans.org/security-resources/).

- **Are we including any other open source products? If so, is there any conflict with Apache-2.0?**
  - See [TERMS.md](TERMS.md). Dependencies are declared, not vendored.

- **Is our `TERMS.md` included?**

- **Is a `CHANGELOG.md` present and does it contain structured, consistently formatted recent history?**
  - Keep [Keep a Changelog](https://keepachangelog.com/) headings. Dataset releases stay on the `data-YYYY.MM.DD` GitHub Releases channel and are not duplicated as package versions.

- **Are instructions for contributing included (`CONTRIBUTING.md`)?**

- **Are installation instructions clearly written in the `README` _and_ tested on a clean machine?**
  - Consumer path: `pip install arancel-mx`. Contributor path: `python -m pip install -e ".[dev]"`.
  - CI job `test` in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) installs from a clean environment.

- **Are all dependencies described in the `README`, `pyproject.toml`, and `requirements/production-build.txt`?**

- **Are the public API docs present?**
  - Consumer API and CLI: [docs/consumer-cli.md](docs/consumer-cli.md) and [docs/external-consumption.md](docs/external-consumption.md).

- **Are there unit tests?**
  - `python -m pytest -q`

- **If applicable and possible, is GitHub Actions CI set up?**
  - Required check on `main` is **`test`**.

- **Have multiple people reviewed the code?**
  - `main` requires a pull request. See [docs/operations/github-settings.md](docs/operations/github-settings.md).

- **Is there a screenshot in the `README`, if applicable?**
  - `docs/demo.gif`


Use the GitHub issue form [`.github/ISSUE_TEMPLATE/open_source_release.yml`](.github/ISSUE_TEMPLATE/open_source_release.yml) to track this walkthrough.

## Copy this version to paste into a GitHub issue with live checkboxes:

```
- [ ] **Has PII been removed?**
  - Tracked text scan in `tests/test_public_distribution.py`.
  - Inspect images under `docs/` for personal data, credentials, or non-public identifiers.
- [ ] **Have security vulnerabilities been remediated?**
- [ ] **Are we including any other open source products? If so, is there any conflict with Apache-2.0?**
- [ ] **Is our `TERMS.md` included?**
- [ ] **Is a `CHANGELOG.md` present and does it contain structured, consistently formatted recent history?**
- [ ] **Are instructions for contributing included (`CONTRIBUTING.md`)?**
- [ ] **Are installation instructions clearly written in the `README` _and_ tested on a clean machine?**
- [ ] **Are all dependencies described in the `README`, `pyproject.toml`, and `requirements/production-build.txt`?**
- [ ] **Are the public API docs present (`docs/consumer-cli.md`, `docs/external-consumption.md`)?**
- [ ] **Are there unit tests?**
- [ ] **If applicable and possible, is GitHub Actions CI set up?**
- [ ] **Have multiple people reviewed the code?**
- [ ] **Is there a screenshot in the `README`, if applicable?**
```

----

## Models in this repository

- [README.md](README.md) / [README.en.md](README.en.md)
- [docs/external-consumption.md](docs/external-consumption.md)
- [docs/package-release.md](docs/package-release.md)
- [docs/release-process.md](docs/release-process.md)
