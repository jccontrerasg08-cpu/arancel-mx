# First Official Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first end-to-end, fail-closed `arancel-mx` pipeline that turns current official LIGIE/NICO sources into a validated canonical dataset and verified Actions artifact.

**Architecture:** Reuse the existing registry, capture layer, normalization, canonical DuckDB schema, `materialize_arancel`, deterministic exporter, and release verifier. Add only five focused pieces: strict HTTP retrieval, deterministic workbook profiles, explicit hierarchy validation, one orchestration service, and a network-enabled Actions workflow. Normal CI stays offline. Generated data never enters Git history.

**Tech Stack:** Python 3.11, requests, pandas, openpyxl, xlrd, PyMuPDF, DuckDB, pytest, GitHub Actions.

## Global Constraints

- Implement on `feat/first-official-dataset` only.
- Never commit downloaded XLS/XLSX/PDF files, `.duckdb`, generated CSV/JSON, source archives, `data/embedded/`, or `out/`.
- Only use sources allowed by `src/arancel_mx/sources/source_registry.json`.
- Fail closed on unknown/ambiguous workbook layouts, snapshots, hosts, media types, missing parents, incomplete provenance, or canonical validation failures.
- Never synthesize legal descriptions or effective dates.
- Use `validity_basis="observed_snapshot"` when a legal effective date cannot be tied to the exact record.
- Use `dataset_version=YYYY.MM.DD`, `schema_version="1"`, `ligie_version="LIGIE-2022"` for this first builder.
- Create one rate input for every LIGIE fraction, including rows whose duty/unit values are null, because the existing consolidation code requires a fraction-rate relationship to materialize `fraccion8` and `nico10` records.
- Keep `.github/workflows/ci.yml` offline and secret-free. Real network work belongs in a separate workflow.
- Pin Actions to: checkout `d23441a48e516b6c34aea4fa41551a30e30af803`, setup-python `ece7cb06caefa5fff74198d8649806c4678c61a1`, upload-artifact `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`.
- Preserve all current README information and bilingual links.
- Remove the temporary design and this implementation plan from the final public tree after implementation verification, as previous public-distribution work does.

## File Map

Create:

- `src/arancel_mx/parsers/profiles.py`
- `src/arancel_mx/sources/http.py`
- `src/arancel_mx/pipeline/hierarchy.py`
- `src/arancel_mx/pipeline/official_dataset.py`
- `scripts/build_official_dataset.py`
- `.github/workflows/build-official-dataset.yml`
- `tests/parsers/test_profiles.py`
- `tests/sources/test_http.py`
- `tests/pipeline/test_hierarchy.py`
- `tests/pipeline/test_official_dataset.py`
- `tests/test_official_dataset_script.py`
- `tests/test_official_dataset_workflow.py`

Modify:

- `src/arancel_mx/parsers/workbooks.py`
- `src/arancel_mx/parsers/__init__.py`
- `src/arancel_mx/sources/__init__.py`
- `src/arancel_mx/pipeline/reconcile.py`
- `src/arancel_mx/pipeline/__init__.py`
- `README.md`
- `README.en.md`
- `docs/release-process.md`
- `tests/test_public_distribution.py`

Reuse unchanged unless a regression test proves a bug:

- `src/arancel_mx/sources/registry.py`
- `src/arancel_mx/sources/capture.py`
- `src/arancel_mx/sources/diputados.py`
- `src/arancel_mx/parsers/documents.py`
- `src/arancel_mx/pipeline/build.py`
- `src/arancel_mx/storage/duckdb.py`
- `src/arancel_mx/release/package.py`

---

## Task 1: Resolve real official workbook layouts deterministically

**Files:** create `src/arancel_mx/parsers/profiles.py`, `tests/parsers/test_profiles.py`; modify `workbooks.py`, parser `__init__.py`, and `tests/parsers/test_workbooks.py`.

- [ ] **Step 1: Write failing profile tests**

Use synthetic workbooks with these exact cases:

```python
def test_resolves_ligie_profile_from_registered_aliases(tmp_path):
    path = make_workbook(tmp_path, "ligie.xlsx", [
        ["nota"],
        ["Fracción", "Descripción", "Unidad", "IGI", "IGE"],
        ["01012101", "Reproductores de raza pura.", "Cbza", "10", "Ex."],
    ])
    resolved = resolve_workbook_profile(probe_workbook(path), "ligie_snapshot")
    assert resolved.parser_version == "ligie-profile-1"
    assert resolved.profile.header_row == 2
    assert resolved.profile.columns["code"] == "Fracción"
    assert resolved.profile.columns["unit_name"] == "Unidad"


def test_resolves_nico_profile_from_registered_aliases(tmp_path):
    path = make_workbook(tmp_path, "nico.xlsx", [
        ["Fracción Arancelaria", "NICO", "Descripción NICO"],
        ["01012101", "00", "Reproductores"],
    ])
    resolved = resolve_workbook_profile(probe_workbook(path), "nico_snapshot")
    assert resolved.profile.columns == {
        "fraccion8": "Fracción Arancelaria",
        "nico2": "NICO",
        "description": "Descripción NICO",
    }


def test_ambiguous_profile_fails_closed(tmp_path):
    path = make_workbook(tmp_path, "ambiguous.xlsx", [
        ["Fracción", "Descripción", "IGI", "IGE"],
        ["01012101", "A", "10", "Ex."],
        ["Fracción", "Descripción", "IGI", "IGE"],
    ])
    with pytest.raises(ValueError, match="ambiguous workbook profile"):
        resolve_workbook_profile(probe_workbook(path), "ligie_snapshot")
```

Run:

```bash
python -m pytest tests/parsers/test_profiles.py -q
```

Expected: fail because the profile module does not exist.

- [ ] **Step 2: Implement explicit alias matching**

`profiles.py` exports:

```python
@dataclass(frozen=True)
class ResolvedWorkbookProfile:
    family: str
    parser_version: str
    profile: WorkbookProfile


def resolve_workbook_profile(
    probe: WorkbookProbe,
    family: str,
) -> ResolvedWorkbookProfile:
    ...
```

Implementation rules:

- normalize headers with Unicode NFKD, remove accents, uppercase, collapse non-alphanumerics to spaces;
- LIGIE required aliases: `code = {FRACCION, FRACCION ARANCELARIA}`, `description = {DESCRIPCION}`;
- LIGIE optional aliases: `unit_name = {UNIDAD, UNIDAD DE MEDIDA, UMT}`, `igi = {IGI, IMP, IMPORTACION}`, `ige = {IGE, EXP, EXPORTACION}`;
- NICO required aliases: `fraccion8 = {FRACCION, FRACCION ARANCELARIA}`, `nico2 = {NICO}`, `description = {DESCRIPCION, DESCRIPCION NICO}`;
- scan every sampled row/sheet;
- exactly one matching `(sheet, header_row)` is required;
- zero matches raises `ValueError("unknown workbook profile: <family>")`;
- multiple matches raises `ValueError("ambiguous workbook profile: <family>")`.

- [ ] **Step 3: Make workbook probing support both `.xls` and `.xlsx`**

Add:

```python
def _excel_engine(path: Path) -> str:
    if path.suffix.lower() == ".xls":
        return "xlrd"
    if path.suffix.lower() == ".xlsx":
        return "openpyxl"
    raise ValueError(f"unsupported workbook format: {path.suffix}")
```

Use `pandas.ExcelFile` and bounded `read_excel(..., header=None, nrows=sample_rows)` for probing. Keep sample width capped by `sample_columns`.

- [ ] **Step 4: Preserve units and activate forward-fill**

Apply `WorkbookProfile.forward_fill` in `_read_profile`. Add `unit_code` and `unit_name` to LIGIE normalized output when those logical columns exist.

- [ ] **Step 5: Export profile types from `parsers/__init__.py` and run tests**

```bash
python -m pytest tests/parsers -q
```

Expected: all parser tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/arancel_mx/parsers tests/parsers
git commit -m "feat: resolve official workbook profiles"
```

---

## Task 2: Validate official downloads and select the current snapshot

**Files:** create `src/arancel_mx/sources/http.py`, `tests/sources/test_http.py`; modify source `__init__.py`, `pipeline/reconcile.py`, and `tests/pipeline/test_reconcile.py`.

- [ ] **Step 1: Write failing HTTP-boundary tests**

Required cases:

```python
def test_redirect_outside_registered_host_is_rejected():
    with pytest.raises(ValueError, match="not allowed"):
        fetch_official_document(
            Session(Response("https://example.com/file.pdf")),
            "https://www.snice.gob.mx/file.pdf",
            ("www.snice.gob.mx", "snice.gob.mx"),
            ("application/pdf",),
        )


def test_registered_content_type_with_charset_is_accepted():
    fetched = fetch_official_document(
        Session(Response("https://www.snice.gob.mx/file.pdf", content_type="application/pdf; charset=binary")),
        "https://www.snice.gob.mx/file.pdf",
        ("www.snice.gob.mx", "snice.gob.mx"),
        ("application/pdf",),
    )
    assert fetched.content == b"abc"
```

Also reject declared or actual body size over the configured limit.

Run:

```bash
python -m pytest tests/sources/test_http.py -q
```

Expected: import failure.

- [ ] **Step 2: Implement strict retrieval**

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

Rules: request with timeout, `raise_for_status`, validate final redirect host, normalize media type before `;`, allow `application/octet-stream` only when the final file extension maps unambiguously to a registered allowed type, reject oversized payloads, return exact bytes and timezone-aware UTC retrieval time.

- [ ] **Step 3: Add deterministic snapshot selection**

Add to `pipeline/reconcile.py`:

```python
def select_current_document(
    documents: Sequence[DiscoveredDocument],
    dataset_key: str,
    document_role: str,
) -> DiscoveredDocument:
    ...
```

Rules: exact filter; one candidate wins; for multiple candidates parse valid `YYYYMMDD` tokens from title and URL basename, select the unique maximum date; ties or no parseable dates fail with `ambiguous official snapshot`.

Test latest selection and tie rejection.

- [ ] **Step 4: Export HTTP types and run focused tests**

```bash
python -m pytest tests/sources tests/pipeline/test_reconcile.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/arancel_mx/sources src/arancel_mx/pipeline/reconcile.py tests/sources tests/pipeline/test_reconcile.py
git commit -m "feat: validate official downloads and snapshots"
```

---

## Task 3: Validate HS -> fraction -> NICO hierarchy explicitly

**Files:** create `src/arancel_mx/pipeline/hierarchy.py`, `tests/pipeline/test_hierarchy.py`; modify pipeline `__init__.py`.

- [ ] **Step 1: Write hierarchy tests**

```python
def test_complete_hierarchy_is_kept_without_generated_descriptions():
    hs = [
        row("hs2", "01", "Animales vivos"),
        row("hs4", "0101", "Caballos"),
        row("hs6", "010121", "Reproductores"),
    ]
    fractions = [row("fraccion8", "01012101", "Reproductores de raza pura")]
    nicos = [row("nico10", "0101210100", "Reproductores")]
    result = assemble_classifications(hs, fractions, nicos)
    assert [item["code"] for item in result] == ["01", "0101", "010121", "01012101", "0101210100"]
    assert result[0]["description"] == "Animales vivos"


def test_fraction_without_hs6_parent_fails():
    with pytest.raises(ValueError, match="missing HS6 parent"):
        assemble_classifications([], [row("fraccion8", "01012101", "x")], [])


def test_nico_without_fraction_parent_fails():
    with pytest.raises(ValueError, match="missing fraction parent"):
        assemble_classifications([], [], [row("nico10", "0101210100", "x")])
```

Run and confirm red:

```bash
python -m pytest tests/pipeline/test_hierarchy.py -q
```

- [ ] **Step 2: Implement `assemble_classifications`**

```python
def assemble_classifications(
    hs_rows: Sequence[Mapping[str, object]],
    fraction_rows: Sequence[Mapping[str, object]],
    nico_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    ...
```

Reject conflicting duplicates by `(level, code, ligie_version)`. Require fraction `code[:6]` in HS6, HS6 `code[:4]` in HS4, HS4 `code[:2]` in HS2, and NICO `code[:8]` in fractions. Never create missing rows/descriptions. Return deterministic level/code order.

- [ ] **Step 3: Export and verify**

```bash
python -m pytest tests/pipeline/test_hierarchy.py tests/pipeline/test_build.py -q
```

- [ ] **Step 4: Commit**

```bash
git add src/arancel_mx/pipeline tests/pipeline/test_hierarchy.py
git commit -m "feat: validate tariff hierarchy assembly"
```

---

## Task 4: Implement the offline-testable end-to-end official dataset builder

**Files:** create `src/arancel_mx/pipeline/official_dataset.py`, `tests/pipeline/test_official_dataset.py`; modify pipeline `__init__.py`.

- [ ] **Step 1: Build an offline integration test fixture**

Generate in memory inside the test:

- LIGIE XLSX with one `01012101` fraction, unit, IGI and IGE;
- NICO XLSX with `01012101` + `00`;
- a PDF with official-style chapter `01`, heading `01.01`, subheading `0101.21`;
- minimal SNICE index HTML whose filenames satisfy current registry patterns;
- the existing Diputados ledger fixture routed to the synthetic consolidated PDF;
- a fake session mapping URL -> response, with `get(url, timeout=None)` and no network fallback.

- [ ] **Step 2: Write the end-to-end assertion before implementation**

```python
def test_offline_build_produces_verified_release(tmp_path):
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
        "SHA256SUMS", "arancel_mx.csv", "arancel_mx.duckdb",
        "arancel_mx.json", "manifest.json", "official-sources.tar.gz",
    ]
```

Open the output DuckDB and assert exactly one row at each level `hs2`, `hs4`, `hs6`, `fraccion8`, `nico10`. Assert manifest source documents contain URL + 64-character SHA256 and no `local_path`.

Run:

```bash
python -m pytest tests/pipeline/test_official_dataset.py -q
```

Expected: import failure for `official_dataset`.

- [ ] **Step 3: Implement configuration and stable source IDs**

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

Stable source ID is SHA256 of `dataset_key + NUL + final_url + NUL + source_sha256`, prefixed with `source-`.

- [ ] **Step 4: Discover only the three inputs required by the first core build**

1. Load registry.
2. Fetch/parse Diputados canonical ledger.
3. Require exactly one consolidated-text PDF link.
4. Call `discover_registered_sources` only with `ligie` and `nico` registry entries.
5. Select exact `ligie_snapshot` and `nico_snapshot` using `select_current_document`.
6. Do not fetch proposals, national notes, weighted indicators, or modification families for this first canonical build.

- [ ] **Step 5: Download, capture, and create public provenance records**

For LIGIE, NICO, and consolidated Diputados PDF: strict HTTP fetch, `capture_document`, stable `source_document_id`, authority/venue, final URL, media type, SHA256, local working path, observed date, retrieval timestamp.

Use identities:

```python
SOURCE_IDENTITY = {
    "ligie": ("Secretaría de Economía / SNICE", "SNICE"),
    "nico": ("Secretaría de Economía / SNICE", "SNICE"),
    "diputados_ligie": ("Cámara de Diputados", "Cámara de Diputados"),
}
```

Do not assign a publication/effective date unless it is tied to that exact source.

- [ ] **Step 6: Transform LIGIE into fraction classifications plus rates**

For each LIGIE staging row create a `fraccion8` classification with `validity_basis="observed_snapshot"`, `updated_at=config.effective_as_of`, `published_at=None`, no effective interval, and the LIGIE source ID.

Create one matching rate row per fraction with unit/IGI/IGE values, same LIGIE version/source, `updated_at=config.effective_as_of`, and no invented effective interval.

- [ ] **Step 7: Transform NICO rows**

Each row becomes `level="nico10"`, code `nico10`, official description, `validity_basis="observed_snapshot"`, `updated_at=config.effective_as_of`, no invented effective interval, and NICO source ID.

- [ ] **Step 8: Parse hierarchy without mislabeling publication dates**

Call:

```python
hs_rows = parse_ligie_pdf_hierarchy(
    diputados_pdf_path,
    diputados_source_id,
    config.ligie_version,
    published_at=None,
    effective_from=None,
)
for row in hs_rows:
    row["updated_at"] = config.effective_as_of
    row["published_at"] = None
    row["validity_basis"] = "observed_snapshot"
```

This deliberately uses the observation date as technical `updated_at` while leaving legal publication/effect dates unset. Then call `assemble_classifications(hs_rows, fraction_rows, nico_rows)`.

- [ ] **Step 9: Materialize, validate, export, and package**

Build candidate DB at `work_dir/candidate/arancel_mx.duckdb`, call `materialize_arancel`, require `row_count > 0` plus nonzero `fraccion8` and `nico10`, then call `export_arancel_release`.

Stage a flat `work_dir/release-sources/` containing deterministic names:

```text
ligie.xls or ligie.xlsx
nico.xls or nico.xlsx
ligie-consolidated.pdf
source_capture.json
```

`source_capture.json` contains filename, SHA256, source URL, source document ID, dataset key, media type. It must contain no absolute paths.

Call `prepare_release_archive`, `verify_sources`, and `verify_release`. Return dataset version, schema version, row count, validation status, source count, output directory.

- [ ] **Step 10: Test logical determinism**

Build twice with identical fake inputs and fixed `generated_at`. Require identical CSV, JSON, manifest JSON, source archive bytes, record IDs, and record hashes. Compare DuckDB contents logically rather than requiring byte-identical database files.

- [ ] **Step 11: Run focused integration tests**

```bash
python -m pytest tests/pipeline/test_official_dataset.py tests/pipeline/test_build.py tests/release/test_package.py -q
```

- [ ] **Step 12: Commit**

```bash
git add src/arancel_mx/pipeline tests/pipeline/test_official_dataset.py
git commit -m "feat: build canonical dataset from official sources"
```

---

## Task 5: Add the reproducible command script

**Files:** create `scripts/build_official_dataset.py`, `tests/test_official_dataset_script.py`.

- [ ] **Step 1: Write script delegation/typing test**

Test these arguments: `--work-dir`, `--output-dir`, `--effective-as-of`, `--dataset-version`, `--generated-at`, `--timeout`. Monkeypatch `build_official_dataset` and assert parsed `date`, timezone-aware `datetime`, `Path`s, and version.

Run red:

```bash
python -m pytest tests/test_official_dataset_script.py -q
```

- [ ] **Step 2: Implement `main(argv=None) -> int`**

Validate dataset version against `^\d{4}\.\d{2}\.\d{2}$`. `--generated-at` defaults to current UTC. Print sorted UTF-8 JSON summary. Return `2` on expected validation/file/network errors.

Example supported command:

```bash
python scripts/build_official_dataset.py \
  --work-dir data/embedded/official-build \
  --output-dir out/release \
  --effective-as-of 2026-08-10 \
  --dataset-version 2026.08.10
```

- [ ] **Step 3: Run and commit**

```bash
python -m pytest tests/test_official_dataset_script.py -q
git add scripts/build_official_dataset.py tests/test_official_dataset_script.py
git commit -m "feat: add official dataset build script"
```

---

## Task 6: Add the separate network-enabled Actions build

**Files:** create `.github/workflows/build-official-dataset.yml`, `tests/test_official_dataset_workflow.py`; modify `tests/test_public_distribution.py`.

- [ ] **Step 1: Write workflow contract test first**

Require: `workflow_dispatch`, weekly `schedule`, `contents: read`, pinned checkout/setup-python/upload-artifact SHAs, Python 3.11, install `.[dev]`, offline pytest before network build, script call, `out/release` upload. Forbid `contents: write`, `secrets.`, `git push`, and release creation commands.

Run red:

```bash
python -m pytest tests/test_official_dataset_workflow.py -q
```

- [ ] **Step 2: Implement workflow**

Use Monday `17 11 * * 1`, `timeout-minutes: 45`, normal tests before build, and UTC shell dates for effective/version/generated values. Verify `manifest["validation_status"] == "passed"` and positive row count before upload.

Upload with:

```yaml
- name: Upload verified dataset
  uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
  with:
    name: arancel-mx-${{ github.run_id }}
    path: out/release/
    if-no-files-found: error
    retention-days: 30
```

- [ ] **Step 3: Extend public-distribution test**

Require the new workflow and script as public files. Do not weaken the existing assertion that normal `ci.yml` has no secrets or network update step.

- [ ] **Step 4: Verify and commit**

```bash
python -m pytest tests/test_official_dataset_workflow.py tests/test_public_distribution.py -q
git add .github/workflows/build-official-dataset.yml tests/test_official_dataset_workflow.py tests/test_public_distribution.py
git commit -m "ci: build verified official dataset artifact"
```

---

## Task 7: Document only what is demonstrably implemented

**Files:** modify `README.md`, `README.en.md`, `docs/release-process.md`.

- [ ] **Step 1: Replace generic release names with exact output contract**

Document:

```text
release/
├── arancel_mx.duckdb
├── arancel_mx.csv
├── arancel_mx.json
├── manifest.json
├── SHA256SUMS
└── official-sources.tar.gz
```

- [ ] **Step 2: Add build instructions in Spanish and English**

Include the exact script example from Task 5. State that the `Build official dataset` workflow can build a verified Actions artifact. State explicitly that GitHub Release/tag publication remains manual and supervised.

Do not claim a public release exists unless one has actually been created later.

- [ ] **Step 3: Update project status after integration is green**

Add `Construcción end-to-end de dataset oficial | Disponible` and English mirror. Keep automatic GitHub Releases as roadmap because this workflow only builds artifacts.

- [ ] **Step 4: Extend `docs/release-process.md`**

Document script, weekly/manual build, artifact verification, no generated data in Git history, and manual publication gate.

- [ ] **Step 5: Verify and commit**

```bash
python -m pytest tests/test_public_distribution.py -q
git add README.md README.en.md docs/release-process.md
git commit -m "docs: document official dataset build"
```

---

## Task 8: Verify offline, exercise real sources, run Actions, then prepare PR

**Files:** only regression-tested fixes if live sources reveal a real incompatibility; finally delete the two process-only plan/spec files.

- [ ] **Step 1: Run complete offline verification**

```bash
python -m pytest -q
python -m build
git diff --check
```

All must pass.

- [ ] **Step 2: Confirm no generated data is tracked**

```bash
git ls-files '*.duckdb' 'out/**' 'data/raw/**' 'data/embedded/**' 'data/releases/**'
```

Expected: no generated dataset files.

- [ ] **Step 3: Execute the real official-source build**

```bash
python scripts/build_official_dataset.py \
  --work-dir data/embedded/official-build \
  --output-dir out/release \
  --effective-as-of 2026-08-10 \
  --dataset-version 2026.08.10 \
  --generated-at 2026-08-10T08:30:00+00:00
```

If an official page/workbook has changed, do not weaken validation. Add the smallest sanitized regression test reproducing the observed shape, fix only the corresponding discovery/profile/parser behavior, then rerun the full suite.

- [ ] **Step 4: Verify real acceptance criteria directly**

```bash
python - <<'PY'
from pathlib import Path
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
print(levels)
PY
```

- [ ] **Step 5: Push branch, require normal CI green, then manually dispatch `Build official dataset` on this branch**

The Actions artifact must contain exactly the six output files. Download/verify it if the connector/runtime supports artifact download. Confirm no tag/GitHub Release was created automatically.

- [ ] **Step 6: Remove process-only documents before public PR**

```bash
git rm docs/first-official-dataset-design.md planning/2026-08-10-first-official-dataset.md
git commit -m "docs: remove dataset implementation notes"
```

- [ ] **Step 7: Run final verification from exact PR head**

```bash
python -m pytest -q
python -m build
git diff --check
python -m pytest tests/test_public_distribution.py -q
```

- [ ] **Step 8: Open PR only after both workflows are green**

Title:

```text
feat: build first official consolidated tariff dataset
```

PR evidence must include offline test/build results, real dataset row count by level, official workflow run conclusion, six artifact filenames, and confirmation that publication remains explicit/manual.

## Final Acceptance Checklist

- [ ] Current LIGIE snapshot selected deterministically.
- [ ] Current NICO snapshot selected deterministically.
- [ ] HS2/HS4/HS6 descriptions come from the official consolidated document, never generated prefixes.
- [ ] Every fraction has a rate input.
- [ ] Every current NICO has a current fraction parent.
- [ ] Every current fraction has HS6 -> HS4 -> HS2 parents.
- [ ] Every canonical record has provenance.
- [ ] `validation_status == "passed"` and `row_count > 0`.
- [ ] Six release artifacts are produced.
- [ ] CSV/JSON/DuckDB share canonical records and record hashes.
- [ ] Public manifest excludes local paths.
- [ ] `verify_release()` succeeds.
- [ ] `verify_sources()` succeeds before packaging.
- [ ] Full offline pytest passes.
- [ ] Python package builds.
- [ ] `git diff --check` passes.
- [ ] Normal CI passes.
- [ ] Real-source Actions build passes and artifact is available.
- [ ] No generated dataset/source binary is tracked in Git.
- [ ] No automatic GitHub Release/tag is created by this change.
