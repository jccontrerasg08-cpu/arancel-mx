# Docs shrink, test-only deps, and national-notes pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining audit work as two sequential PRs: shrink duplicated maintainer docs and drop test-only `reportlab`/`PyYAML`, then wire existing national-notes parsing into the official `data-*` capture so `arancel_mx_national_notes` can be non-empty.

**Architecture:** Parser, materialize, and registry entry already exist. PR2 only deletes duplicated prose and replaces test-time PDF/YAML libraries with committed fixtures plus text/regex workflow contracts. The notes PR only adds one `_capture_source` of `registry["national_notes"].canonical_page`, parses with `parse_national_notes_html`, and passes `national_notes=` into `materialize_arancel`. No new CLI, no GIR/IVA/NOM/T-MEC, no `source_registry.json` edit.

**Tech Stack:** Python 3.11+, pytest, DuckDB, PyMuPDF (runtime PDF), GitHub Actions YAML as text, official SNICE HTML.

## Global Constraints

- Sequence: PR #71 (audit deletions) first, then Part A (this plan Tasks 1–8) as one PR, then Part B (Tasks 9–12) as a second PR. Do not merge unless asked.
- Never create `docs/superpowers/` (`tests/test_public_distribution.py` asserts it does not exist).
- Do not add dependencies. Do not drop `filelock`, `openpyxl`, `PyMuPDF`, `xlrd`, `duckdb`, or `requests`.
- Do not edit `src/arancel_mx/sources/source_registry.json` (`registry_sha256` is release identity). The `national_notes` entry is already correct.
- Do not invent GIR, IVA, NOM, T-MEC, section/chapter notes, or reglas complementarias.
- Do not add a national-notes CLI. Maintainer `build` / `check-updates` / `release` stay unchanged.
- Do not put notes into `discover_registered_sources({"ligie","nico"})`. Fetch `canonical_page` HTML directly.
- Keep notes out of `_reconcile_snapshot` SNICE filter (`{"ligie","nico"}`).
- Certification `REQUIRED_SOURCE_ROLES` is a minimum set; extra `national_notes` is allowed without changing it.
- `tests/pipeline/test_official_dataset_change_detection.py` mocks capture with six identities; leave `source_count: 6` there.
- Pytest: `ARANCEL_MX_SKIP_URL_CHECKS=1` and `.venv/bin` on `PATH` (for `check-wheel-contents`).
- Same git checkout is shared state. Part A Tasks 4–5 touch `tests/pipeline/test_official_dataset.py`; Part B Task 9 touches it again — sequential, not parallel writers. YAML vs PDF tasks are file-disjoint and may use isolated worktrees.
- RLE / TheAlgorithms work is out of scope.

---

## File map

### Part A — PR2 (docs + test-only deps)

| File | Responsibility |
|---|---|
| `docs/package-release.md` | Maintainer pkg-v / build-once / gates only; links to consumer docs |
| `docs/production-certification.md` | GitHub write-boundary runbook only |
| `tests/package/test_readme_metadata.py` | Keep channel asserts on package-release; move consumer strings |
| `tests/fixtures/pdf/ligie_hierarchy.pdf` | Committed hierarchy PDF (replaces reportlab) |
| `tests/fixtures/pdf/ligie_pagebreak.pdf` | Committed page-break PDF |
| `tests/parsers/test_documents.py` | Load those fixtures; drop reportlab |
| `tests/pipeline/test_official_dataset.py` | Load hierarchy fixture instead of `hierarchy_pdf_bytes()` |
| `tests/test_workflow_hardening.py` | Workflow contract via text/regex, not PyYAML |
| `tests/package_release/test_publish_workflow.py` | Same |
| `pyproject.toml` | Remove `PyYAML` and `reportlab` from `dev` |
| `requirements/production-build.txt` | Remove `PyYAML`, `reportlab`, and unused `pillow` pin |
| `tests/package/test_dependency_contract.py` | Stop requiring `reportlab` in `dev` |
| `CHANGELOG.md` | Unreleased note for the shrink + dep drop |

### Part B — national notes in official capture

| File | Responsibility |
|---|---|
| `src/arancel_mx/pipeline/official_sources.py` | Authority, capture, release filename |
| `src/arancel_mx/pipeline/official_dataset.py` | Parse HTML and pass `national_notes=` |
| `tests/pipeline/test_official_sources.py` | Fake session + expected 7 sources |
| `tests/pipeline/test_official_dataset.py` | Fake session + view count + identity |
| `tests/fixtures/snice/ligie.notasnac22.html` | Offline notes HTML |
| `docs/data-model.md`, `docs/external-consumption.md`, `README.md`, `README.en.md`, `CHANGELOG.md` | Pipeline captures notes; published `data-2026.08.11` may still be empty |

### Must not change

`src/arancel_mx/sources/source_registry.json`, `parse_national_notes_html`, `materialize_arancel` / `_insert_national_notes`, consumer CLI, `REQUIRED_SOURCE_ROLES`.

---

## Part A — PR2

### Task 1: Retarget consumer asserts off package-release

**Files:**
- Modify: `tests/package/test_readme_metadata.py:33-43`
- Test: `tests/package/test_readme_metadata.py`

**Interfaces:**
- Consumes: existing `_read()`
- Produces: consumer strings asserted on `docs/consumer-cli.md` / `docs/external-consumption.md`; package-release keeps maintainer strings plus doc links

- [ ] **Step 1: Replace the consumer-tour test and add the consumer-docs test**

`docs/consumer-cli.md` already contains `pip install arancel-mx`, `from arancel_mx import Dataset`, `Dataset.latest()`, and `XDG_CACHE_HOME`. `docs/external-consumption.md:111` already contains `Dataset.compare`.

Replace `test_package_release_doc_explains_lightweight_install_and_python_api` with:

```python
def test_package_release_doc_explains_lightweight_install_and_python_api() -> None:
    document = _read("docs/package-release.md")
    assert 'pip install "arancel-mx[maintainer]"' in document
    assert "data-YYYY.MM.DD" in document
    assert "dataset is not embedded" in document.lower()
    assert "pkg-v0.2.1" in document
    assert "docs/consumer-cli.md" in document
    assert "docs/external-consumption.md" in document
    assert "docs/release-process.md" in document


def test_consumer_docs_cover_install_and_python_api() -> None:
    cli = _read("docs/consumer-cli.md")
    ingest = _read("docs/external-consumption.md")
    assert "pip install arancel-mx" in cli
    assert "from arancel_mx import Dataset" in cli
    assert "Dataset.latest()" in cli
    assert "XDG_CACHE_HOME" in cli
    assert "Dataset.compare" in ingest
```

Leave `test_package_release_doc_keeps_code_and_data_release_channels_separate` and `test_package_release_doc_describes_020_as_published` unchanged.

- [ ] **Step 2: Run tests — package-release link asserts fail until Task 2**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/package/test_readme_metadata.py -q`

Expected: `test_consumer_docs_cover_install_and_python_api` PASS. `test_package_release_doc_explains_lightweight_install_and_python_api` FAIL on missing `docs/consumer-cli.md` (and the other two links) in `docs/package-release.md`.

- [ ] **Step 3: Commit the test change only**

```bash
git add tests/package/test_readme_metadata.py
git commit -m "test: retarget consumer API asserts onto consumer docs"
```

---

### Task 2: Shrink docs/package-release.md

**Files:**
- Modify: `docs/package-release.md` (replace entire file)

**Interfaces:**
- Consumes: Task 1 assertions
- Produces: maintainer-only package-release contract

- [ ] **Step 1: Replace the file with this exact body**

Delete consumer installation, first CLI use, Python API, cache/XDG tour, and the nested six-asset tree. Keep pkg-v channel, build-once, gates, published 0.2.0 / in-tree 0.2.1 / matrix wording.

````markdown
# Python package release contract

This document is the maintainer contract for publishing `arancel-mx` to TestPyPI/PyPI. Consumer install, CLI, and Python API live in [`docs/consumer-cli.md`](consumer-cli.md) and [`docs/external-consumption.md`](external-consumption.md). The `data-*` GitHub Release transaction lives in [`docs/release-process.md`](release-process.md).

`arancel-mx==0.2.0` is published on PyPI. The checkout declares `project.version` `0.2.1`; that version is not on PyPI until `pkg-v0.2.1` passes TestPyPI and the OS/Python matrix.

The dataset is not embedded in the wheel or sdist. Published tariff data remains in immutable GitHub Releases named `data-YYYY.MM.DD`.

Repository maintainers who need the ETL/parsing pipeline can install the optional extra:

```bash
pip install "arancel-mx[maintainer]"
```

## Package and data versions are independent

The Python distribution uses PEP 440 package versions such as `0.2.0` (PyPI) and in-tree `0.2.1`. Tariff datasets use immutable date tags such as `data-2026.08.11` (`/releases/latest` currently). The PyPI project page long description is frozen at the `0.2.0` upload until `pkg-v0.2.1`.

A package change does not create a new tariff dataset. A new tariff dataset does not require rebuilding the Python wheel.

## Git tags and GitHub Releases

Package candidates use git tags such as:

```text
pkg-v0.2.0
```

The package workflow must **not create a GitHub Release** for `pkg-v*` tags. GitHub Releases remain reserved for `data-*` bundles because the repository's public `/releases/latest/download/...` links are part of the dataset download contract.

The package publication channel is instead:

```text
git tag pkg-vX.Y.Z
        ↓
GitHub Actions build once
        ↓
TestPyPI
        ↓
external certification
        ↓
manual production approval
        ↓
PyPI
```

## Build-once rule

The wheel and sdist promoted to PyPI must be the exact bytes certified through TestPyPI. A production publish may not rebuild the package after staging certification. SHA256 values are generated immediately after the single build and rechecked before each publication step.

## Release gates

A package version is not considered ready merely because `python -m build` succeeds. The release sequence also requires distribution-content validation, dependency checks, clean installs outside the source checkout, Python/OS compatibility matrices, TestPyPI installation by exact version, real dataset download/integrity/query checks, strict offline retesting, manual approval for the `pypi` environment, and post-publication installation from PyPI.

Trusted Publishing uploaded `arancel-mx==0.2.0` on 2026-08-12. The 2026-08-11 design's full external OS/Python matrix was not a blocking gate for that upload. `0.2.1` treats Ubuntu/Windows/macOS × CPython 3.11, 3.12, and 3.13 as a blocking publish gate after TestPyPI (`external-certification-matrix` in `publish-python-package.yml`). CPython 3.14 and extra install modes (pipx/uv) are not claimed.
````

Keep the file path. `MANIFEST.in` and `tests/package/test_distribution_contents.py` require the path, not the body.

- [ ] **Step 2: Re-run metadata tests**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/package/test_readme_metadata.py -q`

Expected: PASS (including the three package-release tests).

- [ ] **Step 3: Commit**

```bash
git add docs/package-release.md
git commit -m "docs: shrink package-release to maintainer channels"
```

---

### Task 3: Shrink docs/production-certification.md

**Files:**
- Modify: `docs/production-certification.md`

**Interfaces:**
- Consumes: none
- Produces: runbook without package-smoke / public-bundle / routine-verification tours

No test reads this file's body. After PR #71, `CertificationReport` has no `.passed` field; on current `main` the field still exists. Either way, delete the tour that contains `assert report.passed`.

- [ ] **Step 1: Delete three sections and link the real homes**

Delete from `## Package artifact smoke certification` through the end of `## Routine verification commands` (current lines 129–211). Keep Certified live baseline, Safety boundaries, Manual dispatch, Expected successful lifecycle, Inspecting evidence, Failure recovery, Scope.

Insert this paragraph immediately after Inspecting evidence (before Failure recovery):

```markdown
Package install smoke, public-bundle `certify_bundle()`, and routine `pytest`/`build` commands live in [`docs/release-process.md`](release-process.md) and [`docs/package-release.md`](package-release.md). This runbook covers only the isolated GitHub write boundaries.
```

- [ ] **Step 2: Confirm the stale snippet is gone**

Run: `rg -n "report.passed" docs/production-certification.md`

Expected: no matches.

- [ ] **Step 3: Commit**

```bash
git add docs/production-certification.md
git commit -m "docs: drop certification tours duplicated in release-process"
```

---

### Task 4: Commit PDF fixtures and drop reportlab from parser tests

**Files:**
- Create: `tests/fixtures/pdf/ligie_hierarchy.pdf`
- Create: `tests/fixtures/pdf/ligie_pagebreak.pdf`
- Modify: `tests/parsers/test_documents.py`

**Interfaces:**
- Consumes: current reportlab story in `test_pdf_parser_extracts_official_hierarchy` and `test_pdf_parser_joins_heading_split_across_pages`
- Produces: two binary fixtures that `parse_ligie_pdf_hierarchy` already accepts

`src/` does not import reportlab. Runtime PDF parsing is PyMuPDF. `tests/` is pruned from the sdist (`MANIFEST.in`), so committed PDFs do not ship.

- [ ] **Step 1: Point the two PDF tests at missing fixtures (they fail)**

Remove reportlab imports. Change the two tests to copy committed files:

```python
from datetime import date
from pathlib import Path
import shutil

from arancel_mx.parsers.documents import (
    _hierarchy_entries_from_table,
    parse_ligie_pdf_hierarchy,
)

SOURCE = Path(__file__).parents[2] / "src" / "arancel_mx" / "parsers" / "documents.py"
PDF_FIXTURES = Path(__file__).parents[1] / "fixtures" / "pdf"


def test_pdf_parser_extracts_official_hierarchy(tmp_path):
    path = tmp_path / "ligie.pdf"
    shutil.copyfile(PDF_FIXTURES / "ligie_hierarchy.pdf", path)

    rows = parse_ligie_pdf_hierarchy(
        path, "doc-pdf", "LIGIE-2022", date(2025, 12, 29), None
    )

    assert [row["level"] for row in rows] == ["hs2", "hs4", "hs6"]
    assert [row["code"] for row in rows] == ["01", "0101", "010121"]
    assert rows[0]["description"] == "Animales vivos"


def test_pdf_parser_joins_heading_split_across_pages(tmp_path: Path) -> None:
    path = tmp_path / "ligie-pagebreak.pdf"
    shutil.copyfile(PDF_FIXTURES / "ligie_pagebreak.pdf", path)

    rows = parse_ligie_pdf_hierarchy(
        path, "doc-pdf", "LIGIE-2022", date(2025, 12, 29), None
    )
    by_code = {row["code"]: row["description"] for row in rows}

    assert by_code["1104"].endswith("molido.")
    assert "Granos aplastados o en copos" not in by_code["1104"]
    assert by_code["110412"] == "De avena."
```

Leave `_finished_hierarchy` table-only tests unchanged (no PDF).

- [ ] **Step 2: Run to verify they fail because fixtures are missing**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/parsers/test_documents.py::test_pdf_parser_extracts_official_hierarchy tests/parsers/test_documents.py::test_pdf_parser_joins_heading_split_across_pages -q`

Expected: FAIL `FileNotFoundError` (or equivalent) for `tests/fixtures/pdf/…`.

- [ ] **Step 3: Generate the two PDFs once with the current reportlab helpers, then delete the generator**

While reportlab is still installed, run this throwaway snippet from the repo root (do not commit the snippet):

```python
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer, Table, TableStyle

out = Path("tests/fixtures/pdf")
out.mkdir(parents=True, exist_ok=True)

story = [
    Table([["Capítulo 01"], ["Animales vivos"]]),
    Spacer(1, 10),
    Table(
        [
            ["CÓDIGO", "", "DESCRIPCIÓN", "UNIDAD", "IMP.", "EXP."],
            ["01.01", "", "Caballos, asnos, mulos y burdéganos, vivos.", "", "", ""],
            ["0101.21", "--", "Reproductores de raza pura.", "", "", ""],
            ["0101.21.01", "", "Reproductores de raza pura.", "Cbza", "10", "Ex."],
        ],
        colWidths=[70, 20, 280, 50, 40, 40],
        style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]),
    ),
]
SimpleDocTemplate(str(out / "ligie_hierarchy.pdf"), pagesize=letter).build(story)

story = [
    Table(
        [
            ["CÓDIGO", "", "DESCRIPCIÓN"],
            ["11.04", "", "germen de cereales entero, aplastado, en copos o"],
        ],
        colWidths=[70, 20, 400],
        style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]),
    ),
    PageBreak(),
    Table(
        [
            ["", "", "molido."],
            ["", "-", "Granos aplastados o en copos:"],
            ["1104.12", "--", "De avena."],
        ],
        colWidths=[70, 20, 400],
        style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]),
    ),
]
SimpleDocTemplate(str(out / "ligie_pagebreak.pdf"), pagesize=letter).build(story)
```

This is the same story as today's tests. Do not keep a generate script.

- [ ] **Step 4: Re-run the two parser tests**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/parsers/test_documents.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/pdf/ligie_hierarchy.pdf tests/fixtures/pdf/ligie_pagebreak.pdf tests/parsers/test_documents.py
git commit -m "test: replace reportlab PDF generation with committed fixtures"
```

---

### Task 5: Official-dataset tests read the hierarchy fixture

**Files:**
- Modify: `tests/pipeline/test_official_dataset.py:12-14,91-120`

**Interfaces:**
- Consumes: `tests/fixtures/pdf/ligie_hierarchy.pdf` from Task 4
- Produces: `fixture_bytes()` without reportlab

- [ ] **Step 1: Delete reportlab imports and `hierarchy_pdf_bytes()`**

At the top of `tests/pipeline/test_official_dataset.py`, remove:

```python
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle
```

Replace `hierarchy_pdf_bytes` + `fixture_bytes` with:

```python
PDF_HIERARCHY = (
    Path(__file__).parents[1] / "fixtures" / "pdf" / "ligie_hierarchy.pdf"
)


@lru_cache(maxsize=1)
def fixture_bytes():
    ligie_bytes = ligie_workbook_bytes()
    nico_bytes = workbook_bytes(
        [
            ["Fracción Arancelaria", "NICO", "Descripción NICO"],
            ["01012101", "00", "Reproductores de raza pura."],
        ]
    )
    return ligie_bytes, nico_bytes, PDF_HIERARCHY.read_bytes()
```

- [ ] **Step 2: Run official dataset tests**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/pipeline/test_official_dataset.py tests/parsers/test_documents.py -q`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/pipeline/test_official_dataset.py
git commit -m "test: load official hierarchy PDF from fixture"
```

---

### Task 6: Rewrite workflow hardening tests without PyYAML

**Files:**
- Modify: `tests/test_workflow_hardening.py` (replace YAML loader; keep the same guarantees)

**Interfaces:**
- Consumes: `.github/workflows/*.yml` text
- Produces: the same structural asserts, using the `^on:` literal so YAML 1.1 `on`→`True` is irrelevant

Copy the job-slicing idea from `tests/test_official_dataset_workflow.py:27-38` and `tests/test_repository_hardening_verification.py:17-21`. Do not add a YAML parser.

- [ ] **Step 1: Replace the module with this text-based contract**

```python
"""Cross-workflow hardening contract, enforced on workflow text.

GitHub Actions YAML uses a bare `on:` key. A YAML 1.1 loader maps that key to
the boolean True, which is why this repo previously imported PyYAML. These
tests treat `on:` as a literal line instead.
"""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CHECKOUTS_KEEPING_CREDENTIALS = frozenset()
MAX_TIMEOUT_MINUTES = 60
_HOSTED_RUNNERS = frozenset({"ubuntu-latest", "windows-latest", "macos-latest"})
_PINNED_USES = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
_INTERPOLATION = re.compile(r"\$\{\{")
_TOP_LEVEL = re.compile(r"^[a-zA-Z_][\w-]*:")
_JOB_KEY = re.compile(r"^  ([\w-]+):$", re.MULTILINE)


def _workflow_paths() -> list[Path]:
    return sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))


def _workflow_texts() -> dict[str, str]:
    paths = _workflow_paths()
    assert paths
    return {path.name: path.read_text(encoding="utf-8") for path in paths}


def _block_after(text: str, header: str) -> str:
    match = re.search(rf"^{re.escape(header)}\n", text, re.MULTILINE)
    assert match is not None, header
    start = match.end()
    nxt = _TOP_LEVEL.search(text, start)
    return text[start : nxt.start() if nxt else len(text)]


def _job_blocks(text: str) -> dict[str, str]:
    jobs_match = re.search(r"^jobs:\n", text, re.MULTILINE)
    assert jobs_match is not None
    jobs_text = text[jobs_match.end() :]
    keys = list(_JOB_KEY.finditer(jobs_text))
    assert keys
    blocks: dict[str, str] = {}
    for i, match in enumerate(keys):
        end = keys[i + 1].start() if i + 1 < len(keys) else len(jobs_text)
        blocks[match.group(1)] = jobs_text[match.start() : end]
    return blocks


def _run_scripts(block: str) -> list[str]:
    scripts: list[str] = []
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        folded = re.match(r"^(\s+)run:\s+\|[-]?\s*$", lines[i])
        if folded:
            indent = len(folded.group(1))
            body: list[str] = []
            i += 1
            while i < len(lines) and (
                not lines[i].strip()
                or len(lines[i]) - len(lines[i].lstrip(" ")) > indent
            ):
                body.append(lines[i])
                i += 1
            scripts.append("\n".join(body))
            continue
        inline = re.match(r"^\s+run:\s+(\S.*)$", lines[i])
        if inline and not lines[i].rstrip().endswith("|"):
            scripts.append(inline.group(1))
        i += 1
    return scripts


def test_every_workflow_parses_and_declares_bounded_triggers():
    for name, text in _workflow_texts().items():
        triggers = _block_after(text, "on:")
        assert "pull_request_target:" not in triggers, name
        if "pull_request:" in triggers:
            assert name == "ci.yml", f"{name} must not build from untrusted pull requests"


def test_no_workflow_grants_write_permissions_outside_a_job():
    for name, text in _workflow_texts().items():
        permissions = _block_after(text, "permissions:")
        assert ": write" not in permissions, f"{name} grants workflow-level write"


def test_every_job_is_least_privilege_bounded_and_hosted_by_github():
    for name, text in _workflow_texts().items():
        for job_name, block in _job_blocks(text).items():
            label = f"{name}:{job_name}"
            assert re.search(r"^    permissions:\n", block, re.MULTILINE), (
                f"{label} inherits permissions"
            )
            timeout = re.search(
                r"^    timeout-minutes: (\d+)\s*$", block, re.MULTILINE
            )
            assert timeout, f"{label} has no timeout"
            assert 0 < int(timeout.group(1)) <= MAX_TIMEOUT_MINUTES, label
            if "${{ matrix.os }}" in block:
                oss = re.search(r"os:\s*\[([^\]]+)\]", block)
                assert oss, label
                names = {item.strip().strip("\"'") for item in oss.group(1).split(",")}
                assert names <= _HOSTED_RUNNERS, label
            else:
                assert re.search(
                    r"^    runs-on: ubuntu-latest\s*$", block, re.MULTILINE
                ), label


def test_every_workflow_serializes_concurrent_runs():
    for name, text in _workflow_texts().items():
        concurrency = _block_after(text, "concurrency:")
        assert "group:" in concurrency, name
        assert "cancel-in-progress:" in concurrency, name


def test_every_action_is_pinned_to_a_commit_sha_with_a_readable_version_comment():
    for path in _workflow_paths():
        text = path.read_text(encoding="utf-8")
        for uses in re.findall(r"^\s+uses: (\S+)", text, re.MULTILINE):
            assert _PINNED_USES.fullmatch(uses), f"{path.name} uses {uses}"
            assert f"uses: {uses} # v" in text, (
                f"{path.name} pins {uses} without a readable version comment"
            )


def test_checkout_credentials_are_an_explicit_and_justified_decision():
    for name, text in _workflow_texts().items():
        checkouts = len(re.findall(r"uses: actions/checkout@", text))
        if checkouts == 0:
            continue
        falses = len(re.findall(r"persist-credentials: false", text))
        if name in CHECKOUTS_KEEPING_CREDENTIALS:
            continue
        assert checkouts == falses, (
            f"{name} keeps a checkout credential without persist-credentials: false"
        )


def test_no_shell_script_interpolates_workflow_expressions():
    for name, text in _workflow_texts().items():
        for job_name, block in _job_blocks(text).items():
            for script in _run_scripts(block):
                assert not _INTERPOLATION.search(script), (
                    f"{name}:{job_name} interpolates an expression into a shell script; "
                    "pass the value through env: instead"
                )


def test_piped_shell_scripts_opt_into_pipefail():
    for name, text in _workflow_texts().items():
        for job_name, block in _job_blocks(text).items():
            for script in _run_scripts(block):
                if "|" not in script:
                    continue
                assert "set -euo pipefail" in script, (
                    f"{name}:{job_name} pipes without pipefail"
                )
                assert "shell: bash" in block, f"{name}:{job_name} pipes without shell: bash"


def test_workflow_outputs_are_only_written_through_the_reviewed_boundary():
    for path in _workflow_paths():
        text = path.read_text(encoding="utf-8")
        assert "GITHUB_OUTPUT" not in text, (
            f"{path.name} writes step outputs inline; use scripts.workflow_diagnostics "
            "so the values stay validated and single-line"
        )
```

- [ ] **Step 2: Run hardening tests (should stay green)**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/test_workflow_hardening.py tests/test_repository_hardening_verification.py -q`

Expected: PASS. If a regex is too strict for matrix `os:` list formatting, adjust only that regex against the real workflow text — do not reintroduce PyYAML.

- [ ] **Step 3: Commit**

```bash
git add tests/test_workflow_hardening.py
git commit -m "test: enforce workflow hardening on text, not PyYAML"
```

---

### Task 7: Rewrite publish-workflow tests without PyYAML

**Files:**
- Modify: `tests/package_release/test_publish_workflow.py`

**Interfaces:**
- Consumes: `.github/workflows/publish-python-package.yml` text
- Produces: the same trigger/OIDC/matrix guarantees

- [ ] **Step 1: Drop `yaml` and the parsed `workflow` fixture; keep `workflow_text`**

Remove `import yaml` and the `workflow` fixture. Add `import re` plus the same `_block_after` / `_job_blocks` helpers as Task 6 (copy, do not create a shared module). Replace parsed-dict tests with:

```python
def test_trigger_is_package_tags_only(workflow_text: str) -> None:
    assert re.search(
        r'^on:\n  push:\n    tags:\n      - "pkg-v\*"\n',
        workflow_text,
        re.MULTILINE,
    )
    triggers = _block_after(workflow_text, "on:")
    assert "workflow_dispatch:" not in triggers
    assert "pull_request:" not in triggers
    assert "pull_request_target:" not in triggers


def test_default_permissions_are_read_only(workflow_text: str) -> None:
    assert re.search(r"^permissions:\n  contents: read\s*$", workflow_text, re.MULTILINE)


def test_only_publisher_jobs_request_oidc(workflow_text: str) -> None:
    for name, block in _job_blocks(workflow_text).items():
        has_oidc = "id-token: write" in block
        assert has_oidc == (name in PUBLISH_JOBS), name


def test_publisher_jobs_use_gated_environments(workflow_text: str) -> None:
    jobs = _job_blocks(workflow_text)
    assert "name: testpypi" in jobs["publish-testpypi"]
    assert "name: pypi" in jobs["publish-pypi"]


def test_production_publish_is_final_release_only(workflow_text: str) -> None:
    block = _job_blocks(workflow_text)["publish-pypi"]
    assert "production_eligible" in block
    assert "'true'" in block


def test_tag_must_point_at_protected_main_tip(workflow_text: str) -> None:
    block = _job_blocks(workflow_text)["validate-tag"]
    assert "TAG_SHA: ${{ github.sha }}" in block
    assert "git fetch --no-tags --depth 1 origin main" in block
    assert 'main_sha="$(git rev-parse FETCH_HEAD)"' in block
    assert 'if [ "$TAG_SHA" != "$main_sha" ]; then' in block
    assert "exit 1" in block


def test_production_publish_requires_the_os_python_matrix(workflow_text: str) -> None:
    jobs = _job_blocks(workflow_text)
    matrix_job = jobs["external-certification-matrix"]
    assert "needs: [validate-tag, publish-testpypi]" in matrix_job
    assert "runs-on: ${{ matrix.os }}" in matrix_job
    assert "os: [ubuntu-latest, windows-latest, macos-latest]" in matrix_job
    assert 'python-version: ["3.11", "3.12", "3.13"]' in matrix_job
    pypi = jobs["publish-pypi"]
    assert (
        "needs: [validate-tag, build-once, publish-testpypi, external-certification-matrix]"
        in pypi
    )
    assert "actions/checkout@" not in matrix_job
    assert "arancel-mx doctor" not in matrix_job
    assert "${EXPECTED_VERSION}" not in matrix_job
    assert "os.environ['EXPECTED_VERSION']" in matrix_job
    build = jobs["build-once"]
    assert "python -m build" in build
    assert "EXPECTED_VERSION: ${{ needs.validate-tag.outputs.version }}" in build
    assert 'test -f "dist/arancel_mx-${EXPECTED_VERSION}.tar.gz"' in build
    for name in PUBLISH_JOBS:
        job = jobs[name]
        assert "actions/download-artifact@" in job
        assert "python -m build" not in job
```

Keep the existing `workflow_text` substring tests (`test_no_stored_upload_secrets`, `test_uses_trusted_publisher_action`, `test_workflow_never_creates_a_github_release`) unchanged.

- [ ] **Step 2: Run**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/package_release/test_publish_workflow.py -q`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/package_release/test_publish_workflow.py
git commit -m "test: assert publish workflow shape from text"
```

---

### Task 8: Drop reportlab, PyYAML, and unused pillow

**Files:**
- Modify: `pyproject.toml:59-60`
- Modify: `requirements/production-build.txt:22,29-30`
- Modify: `tests/package/test_dependency_contract.py:44`
- Modify: `CHANGELOG.md` Unreleased

**Interfaces:**
- Consumes: Tasks 4–7 (no remaining imports)
- Produces: `dev` extra without test-only PDF/YAML libs

- [ ] **Step 1: Change the contract test first**

In `test_dev_extra_preserves_full_repository_tooling`:

```python
assert {"build", "pytest"} <= dev
```

Grep the tree: `rg -n "reportlab|import yaml|PyYAML" --glob '!docs/plans/**'`

Expected after Tasks 4–7: only `pyproject.toml`, `requirements/production-build.txt`, and this contract test.

- [ ] **Step 2: Run the contract test — still passes while the extra lists reportlab**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/package/test_dependency_contract.py -q`

Expected: PASS (`{"build","pytest"}` is still a subset).

- [ ] **Step 3: Remove the packages**

`pyproject.toml` `dev` extra — delete:

```toml
    "PyYAML>=6.0",
    "reportlab>=4.2",
```

`requirements/production-build.txt` — delete:

```text
pillow==12.3.0
PyYAML==6.0.3
reportlab==5.0.0
```

`pillow` is only pinned as a reportlab transitive (`rg pillow` is that one line). Keep `openpyxl`, `PyMuPDF`, `xlrd`.

Add under CHANGELOG `## [Unreleased]` / `### Removed`:

```markdown
- Dropped test-only `reportlab` and `PyYAML` from the `dev` extra; parser tests use committed PDF fixtures and workflow contracts read YAML as text.
```

- [ ] **Step 4: Run the focused suite plus a reportlab/yaml import probe**

Run:

```bash
ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest \
  tests/package/test_dependency_contract.py \
  tests/parsers/test_documents.py \
  tests/pipeline/test_official_dataset.py \
  tests/test_workflow_hardening.py \
  tests/package_release/test_publish_workflow.py \
  tests/package/test_readme_metadata.py -q
```

Expected: PASS.

Then, after reinstalling the extra in the environment that will run CI (`pip install -c requirements/production-build.txt -e ".[dev]"`), `python -c "import reportlab"` and `python -c "import yaml"` must fail with `ModuleNotFoundError`. If this checkout's `.venv` still has the old wheels, that probe is only meaningful after the reinstall; CI install is the real gate.

- [ ] **Step 5: Commit Part A**

```bash
git add pyproject.toml requirements/production-build.txt tests/package/test_dependency_contract.py CHANGELOG.md
git commit -m "build: drop test-only reportlab and PyYAML"
```

Open/update the Part A PR here. Do not start Part B on the same PR.

---

## Part B — national notes in official capture

Prerequisite: Part A merged or this work stacked on it. `parse_national_notes_html(html: str, source_document_id: str) -> list[dict]` and `materialize_arancel(..., national_notes: Sequence[Mapping[str, object]] = ())` already work (`tests/parsers/test_national_notes.py`, `tests/pipeline/test_build.py`).

Registry (do not edit):

```json
"national_notes": {
  "canonical_page": "https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html",
  "media_types": ["text/html", "application/pdf", "application/msword"]
}
```

Call chain after this part:

```text
build_official_dataset
  → capture_official_inputs  # adds national_notes via _capture_source(canonical_page)
  → parse_national_notes_html(decode_fetched_text(fetched), source_document_id)
  → materialize_arancel(..., national_notes=rows)
  → view arancel_mx_national_notes
  → source_identity includes dataset_key=national_notes
```

Signatures to use, not reimplement:

```python
def _capture_source(*, dataset_key: str, document_role: str, title: str, url: str, entry: RegistryEntry, config: OfficialDatasetConfig, session: Any) -> CapturedOfficialSource

def parse_national_notes_html(html: str, source_document_id: str) -> list[dict]

def materialize_arancel(conn, source_documents, classifications, rates, release, national_notes: Sequence[Mapping[str, object]] = ()) -> dict[str, object]
```

---

### Task 9: Failing official tests for notes capture

**Files:**
- Create: `tests/fixtures/snice/ligie.notasnac22.html`
- Modify: `tests/pipeline/test_official_dataset.py` (`fake_session`, counts, identity set)
- Modify: `tests/pipeline/test_official_sources.py` (`fake_session`, role set, filenames)

**Interfaces:**
- Consumes: HTML already proven by `tests/parsers/test_national_notes.py`
- Produces: red tests until Tasks 10–11 wire capture+parse

- [ ] **Step 1: Add the HTML fixture**

Write `tests/fixtures/snice/ligie.notasnac22.html`:

```html
<html><head><script>void 0</script></head><body>
<h2>Capítulo 01</h2>
<p>1. Los animales vivos de este capítulo.</p>
<p>2. Se entiende por reproductores<br>de raza pura.</p>
<h2>Capítulo 02</h2>
<p>1. Carne y despojos comestibles.</p>
</body></html>
```

- [ ] **Step 2: Teach both fake sessions the notes URL**

In both `tests/pipeline/test_official_dataset.py` and `tests/pipeline/test_official_sources.py`:

```python
NOTES_URL = "https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html"
NOTES_HTML = (
    Path(__file__).parents[1] / "fixtures" / "snice" / "ligie.notasnac22.html"
).read_text(encoding="utf-8")
```

Inside `fake_session()` `responses`:

```python
NOTES_URL: Response(
    NOTES_URL, NOTES_HTML.encode("utf-8"), "text/html; charset=utf-8", NOTES_HTML
),
```

- [ ] **Step 3: Assert seven sources, notes identity, and a non-empty view**

`tests/pipeline/test_official_dataset.py` — in `test_offline_build_produces_verified_release`:

- `assert summary["source_count"] == 7`
- add `NOTES_URL` to `set(session.requested)`
- `assert len(manifest["source_documents"]) == 7`
- add `("national_notes", "national_notes")` to the `source_identity` set
- after the DuckDB assertions:

```python
        notes_count = connection.execute(
            "SELECT COUNT(*) FROM arancel_mx_national_notes"
        ).fetchone()[0]
        assert notes_count > 0
        chapter_notes = connection.execute(
            "SELECT chapter, note_number, text FROM arancel_mx_national_notes "
            "ORDER BY chapter, note_number"
        ).fetchall()
        assert chapter_notes[0][0] == "01"
        assert chapter_notes[0][1] == "1"
```

Also change `test_schema_v2_manifest_replay_returns_no_change_without_candidate` `"source_count": 6` → `7`.

`tests/pipeline/test_official_sources.py`:

- add `("national_notes", "national_notes")` to the captured role set
- `assert len(snapshot.identities) == 7`
- `test_release_sources_preserve_required_dof_evidence` expected names insert `"national-notes.html"` between `"ligie.xlsx"` and `"nico.xlsx"`:

```python
    assert sorted(path.name for path in source_dir.iterdir()) == [
        "dof-law-reform.pdf",
        "dof-tariff-decree.pdf",
        "ligie-consolidated.pdf",
        "ligie-ledger.htm",
        "ligie.xlsx",
        "national-notes.html",
        "nico.xlsx",
        "source_capture.json",
    ]
```

Do **not** change `tests/pipeline/test_official_dataset_change_detection.py` (`source_count: 6` is `len(mocked identities())`).

- [ ] **Step 4: Run — expect red**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/pipeline/test_official_sources.py tests/pipeline/test_official_dataset.py -q`

Expected: FAIL `unexpected network URL` for `NOTES_URL` and/or `source_count == 6` vs `7`.

- [ ] **Step 5: Commit tests only**

```bash
git add tests/fixtures/snice/ligie.notasnac22.html tests/pipeline/test_official_dataset.py tests/pipeline/test_official_sources.py
git commit -m "test: require national notes in official capture"
```

---

### Task 10: Capture national_notes in official_sources

**Files:**
- Modify: `src/arancel_mx/pipeline/official_sources.py`

**Interfaces:**
- Consumes: `load_source_registry()["national_notes"].canonical_page`, existing `_capture_source`
- Produces: a seventh `CapturedOfficialSource` with `dataset_key="national_notes"`, `document_role="national_notes"`

- [ ] **Step 1: Authority map**

In `SOURCE_AUTHORITY`:

```python
SOURCE_AUTHORITY = {
    "ligie": ("Secretaría de Economía / SNICE", "SNICE"),
    "nico": ("Secretaría de Economía / SNICE", "SNICE"),
    "diputados_ligie": ("Cámara de Diputados", "Cámara de Diputados"),
    "national_notes": ("Secretaría de Economía / SNICE", "SNICE"),
}
```

- [ ] **Step 2: Capture canonical HTML in `capture_official_inputs`**

After the diputados consolidated `_capture_source` and before `*legal_sources`, add:

```python
        _capture_source(
            dataset_key="national_notes",
            document_role="national_notes",
            title="Notas nacionales LIGIE",
            url=registry["national_notes"].canonical_page,
            entry=registry["national_notes"],
            config=config,
            session=client,
        ),
```

Do not add `national_notes` to `discovery_registry`. Do not add it to `_reconcile_snapshot` `snice_documents`.

- [ ] **Step 3: Release filename**

In `write_release_sources.release_filename`:

```python
        if key == ("national_notes", "national_notes"):
            return "national-notes.html"
```

- [ ] **Step 4: Run official_sources tests**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/pipeline/test_official_sources.py -q`

Expected: PASS. `tests/pipeline/test_official_dataset.py` still FAIL until parse+materialize (Task 11): notes are captured but the view stays empty / identity may already include the key after capture (identity comes from captured sources). After this task, `source_count` becomes 7 even before parse; the view `COUNT(*)` stays 0 until Task 11.

- [ ] **Step 5: Commit**

```bash
git add src/arancel_mx/pipeline/official_sources.py
git commit -m "feat: capture SNICE national notes HTML in official inputs"
```

---

### Task 11: Parse notes and materialize in official_dataset

**Files:**
- Modify: `src/arancel_mx/pipeline/official_dataset.py`

**Interfaces:**
- Consumes: `CapturedOfficialSource` with `document_role="national_notes"`; `decode_fetched_text`; `parse_national_notes_html`; `materialize_arancel(..., national_notes=)`
- Produces: non-empty `arancel_mx_national_notes` on official builds whose HTML parses

- [ ] **Step 1: Imports**

Add to the existing documents import:

```python
from arancel_mx.parsers.documents import (
    parse_ligie_pdf_hierarchy,
    parse_national_notes_html,
)
from arancel_mx.sources.http import decode_fetched_text
```

- [ ] **Step 2: Parse after the required ligie/nico/diputados sources**

In `build_official_dataset`, after `diputados_source = _required_source(...)` and before workbook parsing:

```python
    notes_source = _required_source(snapshot, "national_notes", "national_notes")
    national_notes = parse_national_notes_html(
        decode_fetched_text(notes_source.fetched),
        str(notes_source.source_document["source_document_id"]),
    )
```

Empty/unnumbered HTML already raises `ValueError` inside `parse_national_notes_html` (fail-closed).

- [ ] **Step 3: Pass notes into materialize**

Replace the `materialize_arancel(...)` call with:

```python
        build_summary = materialize_arancel(
            connection,
            source_documents,
            classifications,
            rate_rows,
            release,
            national_notes=national_notes,
        )
```

Do not change `build.py`.

- [ ] **Step 4: Run pipeline tests**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/pipeline/test_official_dataset.py tests/pipeline/test_official_sources.py tests/pipeline/test_build.py tests/parsers/test_national_notes.py tests/pipeline/test_official_dataset_change_detection.py -q`

Expected: PASS, including `COUNT(*) > 0` and `("national_notes", "national_notes")` in `source_identity`.

- [ ] **Step 5: Commit**

```bash
git add src/arancel_mx/pipeline/official_dataset.py
git commit -m "feat: materialize captured national notes in official builds"
```

---

### Task 12: Docs — pipeline captures notes; published snapshot may still be empty

**Files:**
- Modify: `docs/data-model.md:72`
- Modify: `docs/external-consumption.md:163`
- Modify: `README.md` national-notes row
- Modify: `README.en.md` national-notes row
- Modify: `CHANGELOG.md` Unreleased

Wiring the pipeline does **not** rewrite GitHub Release `data-2026.08.11`. Docs must not claim that published snapshot is now filled.

- [ ] **Step 1: Replace the empty-view sentences**

`docs/data-model.md`:

```markdown
Las tablas `national_note*` y la vista `arancel_mx_national_notes` existen en el DuckDB público. El pipeline oficial captura la página SNICE de notas nacionales, las parsea y las materializa. La release publicada `data-2026.08.11` es anterior a esa captura, así que esa vista puede estar vacía hasta la siguiente `data-*`. GIR, notas de sección/capítulo y reglas complementarias no se publican.
```

`docs/external-consumption.md`:

```markdown
Las notas nacionales LIGIE tienen tablas (`national_note*`, vista `arancel_mx_national_notes`) y un parser HTML. El pipeline oficial ya captura esa fuente. La release publicada `data-2026.08.11` puede seguir dejando la vista vacía hasta la siguiente `data-*`. No se inventan instrumentos legales.
```

`README.md` table cell:

```markdown
| Notas nacionales LIGIE | Parser, captura oficial y vista `arancel_mx_national_notes`; `data-2026.08.11` puede seguir vacía hasta la siguiente `data-*` |
```

`README.en.md`:

```markdown
| LIGIE national notes | Parser, official capture, and `arancel_mx_national_notes`; `data-2026.08.11` may stay empty until the next `data-*` |
```

CHANGELOG Unreleased Added:

```markdown
- Official `data-*` capture fetches SNICE national-notes HTML and materializes `arancel_mx_national_notes`. GIR, section/chapter notes, and reglas complementarias remain unpublished.
```

- [ ] **Step 2: Run documentation contract tests**

Run: `ARANCEL_MX_SKIP_URL_CHECKS=1 .venv/bin/python -m pytest tests/package/test_readme_metadata.py tests/test_autonomous_documentation.py tests/test_public_distribution.py -q`

Expected: PASS. `docs/superpowers` still absent. Nested `docs/plans/` is outside the top-level `docs/*.md` forbidden-token scan.

- [ ] **Step 3: Full suite before claiming Part B done**

Run:

```bash
export PATH="$PWD/.venv/bin:$PATH"
ARANCEL_MX_SKIP_URL_CHECKS=1 python -m pytest -q
```

Expected: all previously passing tests still pass (count may differ slightly after PR #71).

- [ ] **Step 4: Commit**

```bash
git add docs/data-model.md docs/external-consumption.md README.md README.en.md CHANGELOG.md
git commit -m "docs: official pipeline captures national notes"
```

---

## Self-review

**Spec coverage**

| Requirement | Task |
|---|---|
| Shrink package-release; keep pkg-v / build-once / gates; keep file path | 1–2 |
| Shrink production-certification; drop smoke/bundle/routine; fix `report.passed` | 3 |
| Drop test-only reportlab; committed PDFs | 4–5, 8 |
| Drop test-only PyYAML; text/regex; `on:` not bool True | 6–7, 8 |
| Keep filelock/openpyxl/PyMuPDF/xlrd/duckdb/requests | 8 |
| Fetch notes HTML, parse, materialize; no new CLI | 9–11 |
| Do not edit `source_registry.json` | global + 10 |
| Do not invent GIR/IVA/NOM/T-MEC | global + 12 |
| Docs: published `data-2026.08.11` may still be empty | 12 |
| RLE out of scope | global |
| No `docs/superpowers/` | this file lives in `docs/plans/` |

**Placeholders:** none. **Types:** `_capture_source` / `parse_national_notes_html` / `materialize_arancel(..., national_notes=)` names match `official_sources.py`, `documents.py`, `build.py`.
