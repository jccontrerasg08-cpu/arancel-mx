# First Official Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first end-to-end, fail-closed `arancel-mx` dataset pipeline that discovers current official LIGIE/NICO sources, captures them with provenance, parses and validates the HS2 -> HS4 -> HS6 -> MX8 -> NICO10 hierarchy, materializes the canonical DuckDB dataset, exports equivalent CSV/JSON/DuckDB artifacts, packages source evidence, and uploads the verified result as a GitHub Actions artifact.

**Architecture:** Keep existing source registry, normalization, DuckDB schema, canonical materialization, release exporter, and packaging code as the stable core. Add small adapters around them: strict HTTP retrieval, deterministic snapshot selection, workbook profile resolution, hierarchy assembly, one orchestration service, a thin script entrypoint, and a separate network-enabled Actions workflow. The normal CI remains offline and secret-free. Generated datasets remain outside Git history.

**Tech Stack:** Python 3.11, requests, pandas, openpyxl, xlrd, PyMuPDF, DuckDB, pytest, GitHub Actions, `actions/upload-artifact`.

## Global Constraints

- Work only on `feat/first-official-dataset` until review and CI are complete.
- Do not commit downloaded official workbooks, PDFs, `.duckdb` files, generated CSV/JSON releases, or `out/` contents.
- Treat `src/arancel_mx/sources/source_registry.json` as the authority for allowed canonical pages, hosts, media types, and document families.
- Do not guess workbook columns, legal dates, HS descriptions, or current snapshots. Ambiguity is a hard failure.
- Every canonical classification/rate row must reference a known `source_document_id`.
- Create one `tariff_rate` input for every LIGIE fraction, even when all tariff values are null, because the existing consolidation contract materializes `fraccion8` and `nico10` through the fraction rate relationship.
- Use `validity_basis="observed_snapshot"` when no verified legal effective date is available. Do not manufacture `effective_from`.
- Use `dataset_version=YYYY.MM.DD`, `schema_version="1"`, and `ligie_version="LIGIE-2022"` for this first orchestration path.
- Keep normal `.github/workflows/ci.yml` offline. Network retrieval belongs only in `.github/workflows/build-official-dataset.yml`.
- Pin GitHub Actions by full commit SHA. Use checkout `d23441a48e516b6c34aea4fa41551a30e30af803`, setup-python `ece7cb06caefa5fff74198d8649806c4678c61a1`, and upload-artifact `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`.
- The temporary design and implementation-plan documents must not ship in the final public PR. Remove `docs/first-official-dataset-design.md` and this plan after implementation verification and before opening the final PR.
- Preserve every existing README information contract and bilingual link.

## File Map

**Create**

- `src/arancel_mx/sources/http.py`: strict official HTTP download boundary.
- `src/arancel_mx/parsers/profiles.py`: deterministic workbook profile resolver.
- `src/arancel_mx/pipeline/hierarchy.py`: hierarchy and parent coverage validation.
- `src/arancel_mx/pipeline/official_dataset.py`: end-to-end dataset orchestration.
- `scripts/build_official_dataset.py`: thin reproducible command entrypoint.
- `.github/workflows/build-official-dataset.yml`: scheduled/manual real-source build and artifact upload.
- `tests/sources/test_http.py`: host, redirect, type, and size download tests.
- `tests/parsers/test_profiles.py`: deterministic profile matching tests.
- `tests/pipeline/test_hierarchy.py`: hierarchy coverage tests.
- `tests/pipeline/test_official_dataset.py`: offline end-to-end build test using synthetic official-like responses.
- `tests/test_official_dataset_script.py`: script argument/delegation test.
- `tests/test_official_dataset_workflow.py`: workflow contract test.

**Modify**

- `src/arancel_mx/parsers/workbooks.py`: `.xls`/`.xlsx` probing, profile forward-fill, unit preservation.
- `src/arancel_mx/parsers/__init__.py`: export profile resolver types/functions.
- `src/arancel_mx/sources/__init__.py`: export HTTP primitives.
- `src/arancel_mx/pipeline/__init__.py`: export official dataset config/builder.
- `README.md`: document the real dataset build workflow only after the integration is verified.
- `README.en.md`: mirror the Spanish build documentation.
- `docs/release-process.md`: document real build artifact workflow and explicit publication gate.
- `tests/test_public_distribution.py`: require the new public workflow/script without weakening existing safety assertions.

**Reuse without redesign**

- `src/arancel_mx/sources/registry.py`
- `src/arancel_mx/sources/capture.py`
- `src/arancel_mx/sources/diputados.py`
- `src/arancel_mx/pipeline/reconcile.py`
- `src/arancel_mx/pipeline/build.py`
- `src/arancel_mx/storage/duckdb.py`
- `src/arancel_mx/release/package.py`

---

## Task 1: Make workbook parsing strict enough for real SNICE snapshots

**Files:**
- Create: `src/arancel_mx/parsers/profiles.py`
- Create: `tests/parsers/test_profiles.py`
- Modify: `src/arancel_mx/parsers/workbooks.py`
- Modify: `src/arancel_mx/parsers/__init__.py`
- Modify: `tests/parsers/test_workbooks.py`

- [ ] **Step 1: Write failing tests for deterministic profile resolution**

Add tests that construct workbooks with realistic header variants and require a unique profile:

```python
from openpyxl import Workbook
import pytest

from arancel_mx.parsers.profiles import resolve_workbook_profile
from arancel_mx.parsers.workbooks import probe_workbook


def _save(tmp_path, name, rows):
    path = tmp_path / name
    book = Workbook()
    sheet = book.active
    sheet.title = "Hoja1"
    for row in rows:
        sheet.append(row)
    book.save(path)
    return path


def test_resolves_ligie_profile_from_registered_header_aliases(tmp_path):
    path = _save(tmp_path, "FRACCIONESARANCELARIAS-20260810.XLSX", [
        ["nota"],
        ["Fracción", "Descripción", "Unidad", "IGI", "IGE"],
        ["01012101", "Reproductores de raza pura.", "Cbza", "10", "Ex."],
    ])

    resolved = resolve_workbook_profile(probe_workbook(path), "ligie_snapshot")

    assert resolved.parser_version == "ligie-profile-1"
    assert resolved.profile.sheet == "Hoja1"
    assert resolved.profile.header_row == 2
    assert resolved.profile.columns["code"] == "Fracción"
    assert resolved.profile.columns["unit_name"] == "Unidad"


def test_resolves_nico_profile_without_guessing(tmp_path):
    path = _save(tmp_path, "NICO-AGOSTO26-LIGIE_20260810-20260810.XLSX", [
        ["Fracción Arancelaria", "NICO", "Descripción NICO"],
        ["01012101", "00", "Reproductores"],
    ])

    resolved = resolve_workbook_profile(probe_workbook(path), "nico_snapshot")

    assert resolved.parser_version == "nico-profile-1"
    assert resolved.profile.columns == {
        "fraccion8": "Fracción Arancelaria",
        "nico2": "NICO",
        "description": "Descripción NICO",
    }


def test_ambiguous_registered_headers_fail_closed(tmp_path):
    path = _save(tmp_path, "ambiguous.xlsx", [
        ["Fracción", "Descripción", "IGI", "IGE"],
        ["01012101", "A", "10", "Ex."],
        ["Fracción", "Descripción", "IGI", "IGE"],
    ])

    with pytest.raises(ValueError, match="ambiguous workbook profile"):
        resolve_workbook_profile(probe_workbook(path), "ligie_snapshot")
```

- [ ] **Step 2: Run the new profile tests and confirm failure**

Run:

```bash
python -m pytest tests/parsers/test_profiles.py -q
```

Expected: fail because `arancel_mx.parsers.profiles` does not exist.

- [ ] **Step 3: Implement normalized header matching in `profiles.py`**

Use an accent-insensitive, whitespace-normalized header key and explicit aliases:

```python
from dataclasses import dataclass
import re
import unicodedata

from arancel_mx.parsers.workbooks import WorkbookProbe, WorkbookProfile


@dataclass(frozen=True)
class ResolvedWorkbookProfile:
    family: str
    parser_version: str
    profile: WorkbookProfile


ALIASES = {
    "ligie_snapshot": {
        "required": {
            "code": ("FRACCION", "FRACCION ARANCELARIA"),
            "description": ("DESCRIPCION",),
        },
        "optional": {
            "unit_name": ("UNIDAD", "UNIDAD DE MEDIDA", "UMT"),
            "igi": ("IGI", "IMP", "IMPORTACION"),
            "ige": ("IGE", "EXP", "EXPORTACION"),
        },
        "parser_version": "ligie-profile-1",
    },
    "nico_snapshot": {
        "required": {
            "fraccion8": ("FRACCION", "FRACCION ARANCELARIA"),
            "nico2": ("NICO",),
            "description": ("DESCRIPCION", "DESCRIPCION NICO"),
        },
        "optional": {},
        "parser_version": "nico-profile-1",
    },
}


def _header_key(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    plain = "".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", plain.upper()).strip()
```

`resolve_workbook_profile(probe, family)` must scan every sampled row in every sheet, build a logical-to-original-header map, require all required logical fields, add optional fields only when present, and require exactly one matching `(sheet, header_row)` candidate. Zero matches raises `ValueError("unknown workbook profile: ...")`; more than one raises `ValueError("ambiguous workbook profile: ...")`.

- [ ] **Step 4: Add real `.xls` and `.xlsx` probing support**

Replace the openpyxl-only `probe_workbook` implementation with a pandas `ExcelFile` implementation that chooses the engine from the suffix:

```python
def _excel_engine(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".xls":
        return "xlrd"
    if suffix == ".xlsx":
        return "openpyxl"
    raise ValueError(f"unsupported workbook format: {path.suffix}")
```

For each sheet, read with `header=None`, `nrows=sample_rows`, then truncate each tuple to `sample_columns`. This keeps profile discovery bounded and supports both formats already declared by `pyproject.toml`.

- [ ] **Step 5: Preserve unit fields and apply forward-fill**

In `_read_profile`, after reading the registered columns:

```python
for logical in profile.forward_fill:
    header = profile.columns[logical]
    frame[header] = frame[header].replace("", pd.NA).ffill().fillna("")
```

In `parse_ligie_workbook`, add:

```python
"unit_code": str(raw.get("unit_code", "")).strip() or None,
"unit_name": str(raw.get("unit_name", "")).strip() or None,
```

Keep `igi_*` and `ige_*` behavior unchanged.

- [ ] **Step 6: Export the resolver publicly inside the parser package**

Add to `src/arancel_mx/parsers/__init__.py`:

```python
from arancel_mx.parsers.profiles import ResolvedWorkbookProfile, resolve_workbook_profile
```

and add both names to `__all__`.

- [ ] **Step 7: Run parser tests**

```bash
python -m pytest tests/parsers -q
```

Expected: all parser tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/arancel_mx/parsers tests/parsers
git commit -m "feat: resolve official workbook profiles"
```

---

## Task 2: Add a strict official HTTP boundary and snapshot selection

**Files:**
- Create: `src/arancel_mx/sources/http.py`
- Create: `tests/sources/test_http.py`
- Modify: `src/arancel_mx/sources/__init__.py`
- Modify: `src/arancel_mx/pipeline/reconcile.py`
- Modify: `tests/pipeline/test_reconcile.py`

- [ ] **Step 1: Write failing HTTP tests**

Cover allowed hosts, redirect host validation, content type, and size:

```python
from datetime import datetime, timezone
import pytest

from arancel_mx.sources.http import fetch_official_document


class Response:
    def __init__(self, url, content=b"abc", content_type="application/pdf"):
        self.url = url
        self.content = content
        self.headers = {"Content-Type": content_type, "Content-Length": str(len(content))}

    def raise_for_status(self):
        return None


class Session:
    def __init__(self, response):
        self.response = response

    def get(self, url, timeout):
        return self.response


def test_download_rejects_redirect_outside_registered_hosts():
    with pytest.raises(ValueError, match="not allowed"):
        fetch_official_document(
            Session(Response("https://example.com/file.pdf")),
            "https://www.snice.gob.mx/file.pdf",
            ("www.snice.gob.mx", "snice.gob.mx"),
            ("application/pdf",),
        )
```

Also test accepted final host, accepted `Content-Type` with charset, and rejection when body exceeds `max_bytes`.

- [ ] **Step 2: Confirm failure**

```bash
python -m pytest tests/sources/test_http.py -q
```

Expected: import failure for the new module.

- [ ] **Step 3: Implement `FetchedDocument` and `fetch_official_document`**

Interface:

```python
@dataclass(frozen=True)
class FetchedDocument:
    requested_url: str
    final_url: str
    media_type: str
    content: bytes
    retrieved_at: datetime


def fetch_official_document(
    session,
    url: str,
    allowed_hosts: tuple[str, ...],
    media_types: tuple[str, ...],
    timeout_s: float = 60.0,
    max_bytes: int = 100 * 1024 * 1024,
) -> FetchedDocument:
    ...
```

Rules:

1. Request with timeout.
2. `raise_for_status()`.
3. Validate final `response.url` hostname against `allowed_hosts` after redirects.
4. Normalize response content type before `;` and require it in registered `media_types`; if an official server returns `application/octet-stream`, permit it only when the final filename extension unambiguously maps to a media type allowed by the entry.
5. Reject declared or actual size over `max_bytes`.
6. Return exact bytes and a timezone-aware UTC `retrieved_at`.

- [ ] **Step 4: Add deterministic current-snapshot selection to `pipeline/reconcile.py`**

Add:

```python
def select_current_document(
    documents: Sequence[DiscoveredDocument],
    dataset_key: str,
    document_role: str,
) -> DiscoveredDocument:
    ...
```

Selection rules:

- filter exact `dataset_key` and `document_role`;
- zero candidates: `ValueError("missing official snapshot: ...")`;
- one candidate: select it;
- multiple candidates: extract 8-digit `YYYYMMDD` tokens from title and URL basename;
- choose the unique candidate with the greatest valid calendar date;
- if the greatest date belongs to multiple distinct URLs or no candidate has a usable date, raise `ValueError("ambiguous official snapshot: ...")`.

- [ ] **Step 5: Add snapshot tests**

```python
def test_snapshot_selection_uses_unique_latest_dated_candidate():
    docs = (
        DiscoveredDocument("ligie", "ligie_snapshot", "index", "https://www.snice.gob.mx/FRACCIONESARANCELARIAS-20260701.XLSX", "julio", XLSX),
        DiscoveredDocument("ligie", "ligie_snapshot", "index", "https://www.snice.gob.mx/FRACCIONESARANCELARIAS-20260801.XLSX", "agosto", XLSX),
    )
    assert select_current_document(docs, "ligie", "ligie_snapshot").source_url.endswith("20260801.XLSX")
```

Add a tie test that fails closed.

- [ ] **Step 6: Export HTTP primitives**

Update `src/arancel_mx/sources/__init__.py` to export `FetchedDocument` and `fetch_official_document`.

- [ ] **Step 7: Run focused tests**

```bash
python -m pytest tests/sources tests/pipeline/test_reconcile.py -q
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/arancel_mx/sources src/arancel_mx/pipeline/reconcile.py tests/sources tests/pipeline/test_reconcile.py
git commit -m "feat: validate official downloads and snapshots"
```

---

## Task 3: Make hierarchy assembly explicit and fail closed

**Files:**
- Create: `src/arancel_mx/pipeline/hierarchy.py`
- Create: `tests/pipeline/test_hierarchy.py`
- Modify: `src/arancel_mx/pipeline/__init__.py`

- [ ] **Step 1: Write hierarchy tests**

```python
import pytest

from arancel_mx.pipeline.hierarchy import assemble_classifications


def _row(level, code, description="x"):
    return {"level": level, "code": code, "description": description}


def test_assembles_complete_hierarchy_without_inventing_parent_descriptions():
    hs = [_row("hs2", "01", "Animales vivos"), _row("hs4", "0101", "Caballos"), _row("hs6", "010121", "Reproductores")]
    fractions = [_row("fraccion8", "01012101", "Reproductores de raza pura")]
    nicos = [_row("nico10", "0101210100", "Reproductores")]

    rows = assemble_classifications(hs, fractions, nicos)

    assert [row["code"] for row in rows] == ["01", "0101", "010121", "01012101", "0101210100"]
    assert rows[0]["description"] == "Animales vivos"


def test_missing_hs_parent_blocks_dataset():
    with pytest.raises(ValueError, match="missing HS6 parent"):
        assemble_classifications([], [_row("fraccion8", "01012101")], [])


def test_orphan_nico_blocks_dataset():
    with pytest.raises(ValueError, match="missing fraction parent"):
        assemble_classifications([], [], [_row("nico10", "0101210100")])
```

- [ ] **Step 2: Confirm tests fail**

```bash
python -m pytest tests/pipeline/test_hierarchy.py -q
```

- [ ] **Step 3: Implement `assemble_classifications`**

Interface:

```python
def assemble_classifications(
    hs_rows: Sequence[Mapping[str, object]],
    fraction_rows: Sequence[Mapping[str, object]],
    nico_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    ...
```

Rules:

- deduplicate by `(level, code, ligie_version)` and reject conflicting duplicate content;
- every current fraction code requires exact `code[:6]` in HS6;
- every HS6 requires its `code[:4]` HS4;
- every HS4 requires its `code[:2]` HS2;
- every NICO requires exact fraction `code[:8]`;
- do not synthesize descriptions or rows;
- deterministic order: level rank `hs2, hs4, hs6, fraccion8, nico10`, then code, then effective date.

- [ ] **Step 4: Export the function from pipeline package**

Add `assemble_classifications` to `src/arancel_mx/pipeline/__init__.py` and `__all__`.

- [ ] **Step 5: Run hierarchy plus canonical build tests**

```bash
python -m pytest tests/pipeline/test_hierarchy.py tests/pipeline/test_build.py -q
```

- [ ] **Step 6: Commit**

```bash
git add src/arancel_mx/pipeline tests/pipeline/test_hierarchy.py
git commit -m "feat: validate tariff hierarchy assembly"
```

---

## Task 4: Implement the offline-testable end-to-end official dataset orchestrator

**Files:**
- Create: `src/arancel_mx/pipeline/official_dataset.py`
- Create: `tests/pipeline/test_official_dataset.py`
- Modify: `src/arancel_mx/pipeline/__init__.py`

- [ ] **Step 1: Build an offline integration fixture in the test**

The test must generate all binary inputs in memory, not add downloaded source files to git:

- a small LIGIE XLSX with one `01012101` row, unit, IGI, IGE;
- a small NICO XLSX with `01012101 + 00`;
- a small consolidated LIGIE PDF containing official-style chapter `01`, heading `01.01`, subheading `0101.21`;
- minimal SNICE index HTML linking the two workbooks with registry-compatible filenames;
- the existing Diputados fixture HTML, with its consolidated-text PDF URL routed to the synthetic PDF.

Implement a fake session with URL-to-response routing. No network call is permitted in this test.

- [ ] **Step 2: Write the failing end-to-end assertion**

```python
from datetime import date, datetime, timezone
import json
import duckdb

from arancel_mx.pipeline.official_dataset import OfficialDatasetConfig, build_official_dataset
from arancel_mx.release.package import verify_release


def test_offline_build_produces_verified_canonical_release(tmp_path):
    config = OfficialDatasetConfig(
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "release",
        effective_as_of=date(2026, 8, 10),
        dataset_version="2026.08.10",
        generated_at=datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
    )

    summary = build_official_dataset(config, session=fake_session())

    assert summary["validation_status"] == "passed"
    assert summary["row_count"] == 5
    assert sorted(path.name for path in config.output_dir.iterdir()) == [
        "SHA256SUMS",
        "arancel_mx.csv",
        "arancel_mx.duckdb",
        "arancel_mx.json",
        "manifest.json",
        "official-sources.tar.gz",
    ]
    assert verify_release(config.output_dir)["row_count"] == 5
    with duckdb.connect(str(config.output_dir / "arancel_mx.duckdb"), read_only=True) as conn:
        counts = dict(conn.execute("SELECT level, count(*) FROM arancel_mx GROUP BY level").fetchall())
    assert counts == {"hs2": 1, "hs4": 1, "hs6": 1, "fraccion8": 1, "nico10": 1}
```

Also assert the manifest contains only public source fields, no `local_path`, and every source document has `source_url` and a 64-character `sha256`.

- [ ] **Step 3: Confirm integration test fails**

```bash
python -m pytest tests/pipeline/test_official_dataset.py -q
```

Expected: import failure for `official_dataset`.

- [ ] **Step 4: Implement the config and stable IDs**

```python
@dataclass(frozen=True)
class OfficialDatasetConfig:
    work_dir: Path
    output_dir: Path
    effective_as_of: date
    dataset_version: str
    generated_at: datetime
    schema_version: str = "1"
    ligie_version: str = "LIGIE-2022"
    timeout_s: float = 60.0
```

Stable source ID:

```python
def _source_document_id(dataset_key: str, source_url: str, sha256: str) -> str:
    payload = f"{dataset_key}\0{source_url}\0{sha256}".encode("utf-8")
    return "source-" + hashlib.sha256(payload).hexdigest()
```

- [ ] **Step 5: Discover the three required inputs**

Inside `build_official_dataset`:

1. `registry = load_source_registry()`.
2. Fetch the Diputados canonical page with `fetch_official_document`, allowing its registered HTML type.
3. Parse it with `parse_ligie_ledger`.
4. Find exactly one consolidated-text PDF link; zero or multiple PDFs fails.
5. Run `discover_registered_sources` only against the `ligie` and `nico` registry entries.
6. Select exact `ligie_snapshot` and `nico_snapshot` via `select_current_document`.

Do not use proposal, notes, indicator, or modification pages for this first build.

- [ ] **Step 6: Download and capture immutable source bytes**

For each selected source:

- download through `fetch_official_document` using that entry's host/media allowlist;
- call `capture_document` with `source_id`, `kind`, `observed_at`, final URL, and a sanitized filename;
- build `source_document` metadata with stable ID, authority, venue, title, final URL, media type, SHA256, capture path, observed date, and retrieved timestamp.

Use authorities:

```python
SOURCE_IDENTITY = {
    "ligie": ("Secretaría de Economía / SNICE", "SNICE"),
    "nico": ("Secretaría de Economía / SNICE", "SNICE"),
    "diputados_ligie": ("Cámara de Diputados", "Cámara de Diputados"),
}
```

Do not claim a DOF publication date unless the parsed ledger provides one for the exact source.

- [ ] **Step 7: Parse LIGIE and create one rate per fraction**

Resolve the LIGIE workbook profile and call `parse_ligie_workbook`.

Transform each staging row into a fraction classification:

```python
{
    "level": "fraccion8",
    "code": row.normalized["code"],
    "description": row.normalized["description"],
    "ligie_version": config.ligie_version,
    "validity_basis": "observed_snapshot",
    "updated_at": config.effective_as_of,
    "published_at": None,
    "classification_effective_from": None,
    "classification_effective_to": None,
    "source_document_id": ligie_source_id,
}
```

Create a matching rate for every fraction:

```python
{
    "code": row.normalized["code"],
    "unit_code": row.normalized.get("unit_code"),
    "unit_name": row.normalized.get("unit_name"),
    "igi_text": row.normalized.get("igi_text"),
    "igi_kind": row.normalized.get("igi_kind"),
    "igi_value": row.normalized.get("igi_value"),
    "ige_text": row.normalized.get("ige_text"),
    "ige_kind": row.normalized.get("ige_kind"),
    "ige_value": row.normalized.get("ige_value"),
    "ligie_version": config.ligie_version,
    "updated_at": config.effective_as_of,
    "published_at": None,
    "rate_effective_from": None,
    "rate_effective_to": None,
    "source_document_id": ligie_source_id,
}
```

- [ ] **Step 8: Parse NICO**

Resolve the NICO profile and transform each row to:

```python
{
    "level": "nico10",
    "code": row.normalized["nico10"],
    "description": row.normalized["description"],
    "ligie_version": config.ligie_version,
    "validity_basis": "observed_snapshot",
    "updated_at": config.effective_as_of,
    "published_at": None,
    "classification_effective_from": None,
    "classification_effective_to": None,
    "source_document_id": nico_source_id,
}
```

- [ ] **Step 9: Parse official HS hierarchy and assemble classifications**

Call:

```python
parse_ligie_pdf_hierarchy(
    diputados_pdf_path,
    diputados_source_id,
    config.ligie_version,
    ledger.last_law_reform,
    None,
)
```

Then call `assemble_classifications(hs_rows, fraction_rows, nico_rows)`. A missing parent blocks the build.

- [ ] **Step 10: Materialize the candidate DB transactionally**

Create `work_dir / "candidate" / "arancel_mx.duckdb"` with `init_tariff_db`, then:

```python
release = {
    "dataset_version": config.dataset_version,
    "schema_version": config.schema_version,
    "ligie_version": config.ligie_version,
    "effective_as_of": config.effective_as_of,
    "generated_at": config.generated_at,
}
with connect(candidate_path) as conn:
    build_summary = materialize_arancel(conn, source_documents, classifications, rates, release)
```

Require `row_count > 0`, at least one `fraccion8`, and at least one `nico10` before export.

- [ ] **Step 11: Export and package sources**

Call `export_arancel_release(candidate_path, config.output_dir)`.

Stage a flat `work_dir / "release-sources"` directory with deterministic names:

```text
ligie.xlsx or ligie.xls
nico.xlsx or nico.xls
ligie-consolidated.pdf
source_capture.json
```

`source_capture.json` entries must include only relative filename, SHA256, source URL, source document ID, dataset key, and media type. Do not copy absolute local paths into it.

Call:

```python
prepare_release_archive(
    config.output_dir,
    release_sources_dir,
    config.work_dir / "latest",
)
verify_release(config.output_dir)
verify_sources(release_sources_dir)
```

Return a machine-readable summary containing dataset version, schema version, row count, validation status, source count, and output directory.

- [ ] **Step 12: Add a deterministic rebuild test**

Run the fake build twice into different roots with the same fixed `generated_at`. Compare:

- `arancel_mx.csv` bytes;
- `arancel_mx.json` bytes;
- `manifest.json` logical JSON after excluding no fields, because the clock is fixed;
- `official-sources.tar.gz` bytes;
- record IDs and record hashes queried from both DuckDB files.

Do not require the raw DuckDB file bytes themselves to be identical unless DuckDB proves byte-stable; require logical table equivalence and identical exported CSV/JSON/hash contracts.

- [ ] **Step 13: Run pipeline integration tests**

```bash
python -m pytest tests/pipeline/test_official_dataset.py tests/pipeline/test_build.py tests/release/test_package.py -q
```

- [ ] **Step 14: Commit**

```bash
git add src/arancel_mx/pipeline tests/pipeline/test_official_dataset.py
git commit -m "feat: build canonical dataset from official sources"
```

---

## Task 5: Add a reproducible script entrypoint

**Files:**
- Create: `scripts/build_official_dataset.py`
- Create: `tests/test_official_dataset_script.py`

- [ ] **Step 1: Write script contract test**

Load the script module using `importlib.util.spec_from_file_location`, monkeypatch `build_official_dataset`, and assert typed values:

```python
def test_script_parses_required_build_arguments(tmp_path, monkeypatch, capsys):
    module = load_script()
    calls = []
    monkeypatch.setattr(module, "build_official_dataset", lambda config: calls.append(config) or {"validation_status": "passed"})

    code = module.main([
        "--work-dir", str(tmp_path / "work"),
        "--output-dir", str(tmp_path / "release"),
        "--effective-as-of", "2026-08-10",
        "--dataset-version", "2026.08.10",
        "--generated-at", "2026-08-10T08:00:00+00:00",
    ])

    assert code == 0
    assert calls[0].effective_as_of.isoformat() == "2026-08-10"
    assert calls[0].dataset_version == "2026.08.10"
```

- [ ] **Step 2: Confirm failure**

```bash
python -m pytest tests/test_official_dataset_script.py -q
```

- [ ] **Step 3: Implement script**

Arguments:

```text
--work-dir             required
--output-dir           required
--effective-as-of      required ISO date
--dataset-version      required YYYY.MM.DD
--generated-at         optional ISO datetime, defaults to current UTC
--timeout              optional float, default 60
```

Validate dataset version with `^\d{4}\.\d{2}\.\d{2}$`, ensure generated timestamp is timezone-aware, construct `OfficialDatasetConfig`, call `build_official_dataset`, and print sorted UTF-8 JSON. Return `2` for `ValueError`, `FileNotFoundError`, `requests.RequestException`, and JSON decoding errors.

- [ ] **Step 4: Run script tests**

```bash
python -m pytest tests/test_official_dataset_script.py -q
```

- [ ] **Step 5: Commit**

```bash
git add scripts/build_official_dataset.py tests/test_official_dataset_script.py
git commit -m "feat: add official dataset build script"
```

---

## Task 6: Add the network-enabled GitHub Actions artifact build

**Files:**
- Create: `.github/workflows/build-official-dataset.yml`
- Create: `tests/test_official_dataset_workflow.py`
- Modify: `tests/test_public_distribution.py`

- [ ] **Step 1: Write workflow contract test first**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_official_dataset_workflow_is_read_only_and_uploads_verified_artifact():
    text = (ROOT / ".github/workflows/build-official-dataset.yml").read_text("utf-8")
    required = (
        "workflow_dispatch:",
        "schedule:",
        "contents: read",
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        'python-version: "3.11"',
        'python -m pip install -e ".[dev]"',
        "python -m pytest -q",
        "scripts/build_official_dataset.py",
        "out/release",
    )
    forbidden = ("contents: write", "secrets.", "git push", "gh release")
    assert [value for value in required if value not in text] == []
    assert [value for value in forbidden if value in text] == []
```

- [ ] **Step 2: Confirm failure**

```bash
python -m pytest tests/test_official_dataset_workflow.py -q
```

- [ ] **Step 3: Implement workflow**

Use this structure:

```yaml
name: Build official dataset

on:
  workflow_dispatch:
  schedule:
    - cron: "17 11 * * 1"

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    steps:
      - name: Checkout
        uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803

      - name: Set up Python
        uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1
        with:
          python-version: "3.11"

      - name: Install
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e ".[dev]"

      - name: Test offline suite
        run: python -m pytest -q

      - name: Build official dataset
        shell: bash
        run: |
          set -euo pipefail
          EFFECTIVE="$(date -u +%F)"
          VERSION="$(date -u +%Y.%m.%d)"
          GENERATED="$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
          python scripts/build_official_dataset.py \
            --work-dir data/embedded/official-build \
            --output-dir out/release \
            --effective-as-of "$EFFECTIVE" \
            --dataset-version "$VERSION" \
            --generated-at "$GENERATED"

      - name: Verify release
        run: |
          python - <<'PY'
          from pathlib import Path
          from arancel_mx.release.package import verify_release
          manifest = verify_release(Path("out/release"))
          assert manifest["validation_status"] == "passed"
          assert int(manifest["row_count"]) > 0
          PY

      - name: Upload verified dataset
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
        with:
          name: arancel-mx-${{ github.run_id }}
          path: out/release/
          if-no-files-found: error
          retention-days: 30
```

- [ ] **Step 4: Extend public distribution checks without weakening normal CI**

Add `.github/workflows/build-official-dataset.yml` and `scripts/build_official_dataset.py` to required public files. Keep the existing assertion that normal `ci.yml` has no network update or secrets.

- [ ] **Step 5: Run workflow/public contract tests**

```bash
python -m pytest tests/test_official_dataset_workflow.py tests/test_public_distribution.py -q
```

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/build-official-dataset.yml tests/test_official_dataset_workflow.py tests/test_public_distribution.py
git commit -m "ci: build verified official dataset artifact"
```

---

## Task 7: Document the implemented build without claiming an unpublished release

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `docs/release-process.md`

- [ ] **Step 1: Add Spanish build instructions**

Under `## Artefactos y reproducibilidad`, replace generic artifact names with the exact public contract:

```text
release/
├── arancel_mx.duckdb
├── arancel_mx.csv
├── arancel_mx.json
├── manifest.json
├── SHA256SUMS
└── official-sources.tar.gz
```

Add a subsection:

```markdown
### Construir el dataset oficial

La construcción end-to-end descarga únicamente fuentes permitidas por el registro, conserva SHA256 y procedencia, valida la jerarquía y genera los artefactos fuera del historial Git.

```bash
python scripts/build_official_dataset.py \
  --work-dir data/embedded/official-build \
  --output-dir out/release \
  --effective-as-of 2026-08-10 \
  --dataset-version 2026.08.10
```

El workflow `Build official dataset` también puede ejecutarse manualmente desde GitHub Actions y conserva el resultado validado como artifact. La creación de un GitHub Release sigue siendo una decisión explícita y supervisada.
```

Do not write that a public release/tag exists until one actually exists.

- [ ] **Step 2: Mirror the same facts in `README.en.md`**

Use the same exact artifact filenames and script, translated prose only.

- [ ] **Step 3: Extend `docs/release-process.md`**

Add a section after validation/export describing:

- end-to-end script;
- weekly/manual Actions build;
- artifact retention as CI evidence;
- explicit human publication gate;
- no generated DB/source documents in Git history.

- [ ] **Step 4: Update project status carefully**

Only after offline integration passes, add `Construcción end-to-end de dataset oficial | Disponible` / English equivalent. Keep `releases de dataset automatizados` as not fully automatic because the workflow only builds artifacts and does not publish GitHub Releases.

- [ ] **Step 5: Run README/public-distribution tests**

```bash
python -m pytest tests/test_public_distribution.py -q
```

- [ ] **Step 6: Commit**

```bash
git add README.md README.en.md docs/release-process.md
git commit -m "docs: document official dataset build"
```

---

## Task 8: Run the complete offline verification and inspect the branch

**Files:**
- No product changes unless a failing test exposes a bug.

- [ ] **Step 1: Run the full test suite**

```bash
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Build the Python distribution**

```bash
python -m build
```

Expected: sdist and wheel build successfully.

- [ ] **Step 3: Check whitespace**

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 4: Confirm no generated data are tracked**

```bash
git ls-files '*.duckdb' 'out/**' 'data/raw/**' 'data/embedded/**' 'data/releases/**'
```

Expected: no generated dataset files.

- [ ] **Step 5: Inspect changed files against scope**

```bash
git diff --stat main...HEAD
git diff --name-only main...HEAD
```

Expected product scope is limited to source retrieval/parsing/orchestration, tests, one Actions workflow, script, and public documentation.

---

## Task 9: Exercise the real official-source build

**Files:**
- Modify only if real official input exposes a reproducible parser/profile incompatibility. Any fix must start with a regression test.

- [ ] **Step 1: Run the script against live registered official sources**

From a network-enabled checkout:

```bash
python scripts/build_official_dataset.py \
  --work-dir data/embedded/official-build \
  --output-dir out/release \
  --effective-as-of 2026-08-10 \
  --dataset-version 2026.08.10 \
  --generated-at 2026-08-10T08:30:00+00:00
```

Expected: either a verified release or a precise fail-closed error naming the changed source/profile. Never bypass a failure by weakening validation.

- [ ] **Step 2: If a live source shape changed, use TDD for the exact shape**

Create the smallest sanitized synthetic fixture/test reproducing the observed header/selection behavior. Run that test red, update only the corresponding profile/discovery logic, then rerun the full suite.

Do not commit the downloaded official binary used for diagnosis.

- [ ] **Step 3: Verify acceptance criteria directly**

```bash
python - <<'PY'
from pathlib import Path
import json
import duckdb
from arancel_mx.release.package import verify_release

release = Path("out/release")
manifest = verify_release(release)
assert manifest["validation_status"] == "passed"
assert int(manifest["row_count"]) > 0
assert all(item.get("source_url") and len(item.get("sha256", "")) == 64 for item in manifest["source_documents"])
assert all("local_path" not in item for item in manifest["source_documents"])

with duckdb.connect(str(release / "arancel_mx.duckdb"), read_only=True) as conn:
    levels = dict(conn.execute("SELECT level, count(*) FROM arancel_mx GROUP BY level").fetchall())
    assert levels.get("fraccion8", 0) > 0
    assert levels.get("nico10", 0) > 0
    assert conn.execute("SELECT count(*) FROM arancel_mx WHERE source_count < 1").fetchone()[0] == 0

print(json.dumps({"row_count": manifest["row_count"], "levels": levels}, ensure_ascii=False))
PY
```

- [ ] **Step 4: Run the complete suite again after the real build**

```bash
python -m pytest -q
python -m build
git diff --check
```

---

## Task 10: Run/inspect GitHub Actions artifact build

**Files:**
- No source changes unless workflow execution reveals a reproducible workflow bug.

- [ ] **Step 1: Push the feature branch and let normal CI validate it**

```bash
git push -u origin feat/first-official-dataset
```

Wait for normal `CI` to complete successfully.

- [ ] **Step 2: Dispatch `Build official dataset` on the feature branch**

Use GitHub Actions `workflow_dispatch` for `feat/first-official-dataset`.

- [ ] **Step 3: Require successful workflow conclusion**

Do not open the final PR if the official dataset workflow fails. Diagnose failures from job logs, add a regression test where possible, fix, and rerun.

- [ ] **Step 4: Inspect the uploaded artifact contract**

The Actions artifact must contain exactly the release output set:

```text
SHA256SUMS
arancel_mx.csv
arancel_mx.duckdb
arancel_mx.json
manifest.json
official-sources.tar.gz
```

Download it and run `verify_release()` locally if the connector/runtime permits artifact download.

- [ ] **Step 5: Confirm no GitHub Release/tag was auto-created**

The first iteration must leave release publication manual and explicit.

---

## Task 11: Remove process-only specs and perform final verification

**Files:**
- Delete: `docs/first-official-dataset-design.md`
- Delete: `planning/2026-08-10-first-official-dataset.md`

- [ ] **Step 1: Remove the temporary design and plan from the public tree**

```bash
git rm docs/first-official-dataset-design.md planning/2026-08-10-first-official-dataset.md
git commit -m "docs: remove dataset implementation notes"
```

This preserves the design/plan in branch history while keeping implementation-process notes out of the final public distribution.

- [ ] **Step 2: Run final verification from the exact PR head**

```bash
python -m pytest -q
python -m build
git diff --check
```

Expected: all commands succeed.

- [ ] **Step 3: Confirm public-distribution safety**

```bash
python -m pytest tests/test_public_distribution.py -q
```

Expected: pass, including no private/process path violations.

- [ ] **Step 4: Compare final branch with main**

```bash
git diff --check main...HEAD
git diff --stat main...HEAD
git diff --name-only main...HEAD
```

Verify no generated official binary, database, source archive, local path, secret, or unrelated application code appears.

- [ ] **Step 5: Open the PR**

Title:

```text
feat: build first official consolidated tariff dataset
```

PR body must report:

- offline suite result;
- Python package build result;
- real-source build result and dataset row counts by level;
- GitHub Actions official-dataset workflow run result;
- artifact filename set;
- confirmation that no GitHub Release/tag is auto-created;
- provenance/validation guarantees.

Do not merge until both normal CI and the manually dispatched official-dataset workflow are green.

## Final Acceptance Checklist

- [ ] Official LIGIE snapshot is selected deterministically from the registered source.
- [ ] Official NICO snapshot is selected deterministically from the registered source.
- [ ] Consolidated hierarchy comes from the official legislative PDF and no parent description is invented.
- [ ] Every fraction has a corresponding rate row so canonical fractions and NICO can materialize.
- [ ] Every current NICO has a current fraction parent.
- [ ] Every current fraction has HS6 -> HS4 -> HS2 parents.
- [ ] Every canonical record has source provenance.
- [ ] `validation_status == "passed"` and `row_count > 0`.
- [ ] `arancel_mx.duckdb`, CSV, JSON, manifest, checksums, and source archive are produced.
- [ ] CSV/JSON/DuckDB share the canonical record contract and record hashes.
- [ ] Public manifest excludes local paths.
- [ ] `verify_release()` succeeds.
- [ ] `verify_sources()` succeeds before source packaging.
- [ ] Full offline pytest suite passes.
- [ ] Python package builds.
- [ ] `git diff --check` passes.
- [ ] Normal CI passes.
- [ ] Real official-source Actions build passes and artifact is downloadable.
- [ ] No generated dataset or official binary is committed to Git.
- [ ] No automatic GitHub Release/tag is created in this change.
