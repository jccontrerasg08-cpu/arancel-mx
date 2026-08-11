# Getting started

`arancel-mx` publishes a reproducible, auditable data layer for LIGIE, Mexican tariff fractions, and NICO. You can consume the data artifacts without installing Python, or install the project when you need the CLI or want to develop the pipeline.

> [!IMPORTANT]
> `arancel-mx` is a technical data tool. **It does not constitute legal advice.** Consult the applicable official publications for classification, compliance, import, or export decisions.

## Consume the data without installing anything

The shortest path for an analyst is a GitHub Release named `data-YYYY.MM.DD`. Every valid release contains exactly:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

Choose CSV for tabular tools, JSON for document-oriented pipelines, and DuckDB for local analytical queries. Before relying on a download, follow [`verify-release.md`](verify-release.md).

## Install the CLI from a checkout

Until the package is published to PyPI, the supported source-code path is:

```bash
git clone https://github.com/jccontrerasg08-cpu/arancel-mx.git
cd arancel-mx
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install .
python -m arancel_mx --help
arancel-mx --help
```

`pip install .` installs the consumer dependencies declared by the package. Python 3.11 or newer is required.

## Reproducible development

To contribute or reproduce the reviewed CI/production environment, use the exact versions from the constraints file:

```bash
python -m pip install pip==26.2.1
python -m pip install -c requirements/production-build.txt -e ".[dev]"
python -m pytest -q
python -m build
```

The distinction is intentional:

```text
consumer          -> compatible ranges in pyproject.toml
CI / production   -> exact pins in requirements/production-build.txt
```

## What to read next

- [`cli.md`](cli.md): current public commands.
- [`dataset.md`](dataset.md): artifacts and consumption paths.
- [`hs-mx-nico.md`](hs-mx-nico.md): HS2 → HS4 → HS6 → MX8 → NICO10 hierarchy.
- [`sources.md`](sources.md): official sources and their roles.
- [`provenance.md`](provenance.md): documentary traceability.
- [`verify-release.md`](verify-release.md): independent release verification.
- [Support](https://github.com/jccontrerasg08-cpu/arancel-mx/blob/main/SUPPORT.md): support and issue-reporting guidance.
