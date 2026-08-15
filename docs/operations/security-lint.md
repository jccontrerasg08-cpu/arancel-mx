# Security-lint policy

`arancel-mx` runs Ruff's Bandit-compatible `S` rules as part of the standard lint command. This keeps security review in the same required CI gate as syntax and correctness checks rather than treating it as an occasional manual scan.

## Baseline

The mandatory command is:

```bash
python -m ruff check src tests scripts
```

Production modules in `src/` and operational scripts in `scripts/` must have no untriaged `S` findings. The project uses the default Ruff command in CI, so a new security finding fails the `test` check unless it is remediated or given a narrow, reviewed suppression.

## Reviewed exceptions

The following exceptions are deliberately limited and should be revisited when the affected code changes.

| Rule | Location | Reason |
|---|---|---|
| `S310` | `consumer/wco_support.py` | The WCO download URL is constructed only from the package's fixed HTTPS base URL and a range-validated chapter or fixed filename. The response is checked for PDF content before atomically entering the local cache. |
| `S603` | `scripts/certify_package_install.py` | The certification script invokes only an isolated temporary virtual environment, a verified local distribution, and repository-local probe paths after validating all file inputs. |
| `S603` | `scripts/dependency_compatibility_probe.py` | The probe invokes commands only in its temporary virtual environment using validated distribution, dataset, and repository paths. |
| `S608` | `pipeline/build.py` | Dynamic SQL uses either static internal-table allowlists, a fixed public-column contract, or a fixed export ordering constant. Dynamic user-supplied identifiers are not interpolated. |
| `S101`, `S105`, `S107`, `S603`, `S607`, `S108` | `tests/**/*.py` | Pytest assertions, clearly synthetic token strings used to exercise redaction, and controlled local process/temporary-path fixtures are test contracts rather than production behavior. Production code and scripts are not covered by this waiver. |

Every new `# noqa: S...` suppression must include an explanation on the same line and be added to this table. Prefer a code change that removes the finding when practical.

## Maintainer review

Before merging a security-related change, run the standard lint command, the focused security command below, and the relevant tests:

```bash
python -m ruff check src tests scripts
python -m ruff check --select S src scripts
python -m pytest -q
```

Security findings from GitHub Dependabot, code scanning, or secret scanning are repository settings rather than source-controlled state. Maintainers must keep those controls enabled and review their alert queues according to [the GitHub settings runbook](github-settings.md).
