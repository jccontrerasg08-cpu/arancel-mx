# Suggest product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `wco cite|download`, shared search/suggest banner, Spanish help, suggest golden with a real national note.

**Architecture:** Reuse `wco_support.cite_chapter` / `download_chapter` / `download_gir`. Table-only presentation change. JSON/CSV keys unchanged.

**Tech Stack:** argparse nested subparsers (copy `data`), existing `ArancelMXError` CLI boundary.

## Global Constraints

- Branch: `cursor/suggest-product-0f14` at `/workspace/.worktrees/suggest-product`.
- Base: `cursor/retrieval-suggest-0f14` (not `main`).
- `PYTHONPATH=$PWD/src`.
- No force-push. Do not merge PRs or mark draft ready.
- Do not edit `.github/workflows/published-bundle-canary.yml` or `tests/test_published_bundle_canary.py`.
- Do not edit `tests/consumer/test_cli_search_json.py` or `tests/consumer/test_cli_suggest_json.py`.
- Do not edit CHANGELOG.md.
- No LLM, no nomenclator vendor, no WCO in `source_registry.json`, do not say “legally grounded”.

---

### Task 1: WcoSupportError is a consumer error

**Files:**
- Modify: `src/arancel_mx/consumer/wco_support.py`
- Test: `tests/consumer/test_wco_support.py`

- [ ] **Step 1: Failing test**

```python
from arancel_mx.consumer.errors import ArancelMXError
from arancel_mx.consumer.wco_support import WcoSupportError

def test_wco_support_error_is_arancel_mx_error() -> None:
    assert issubclass(WcoSupportError, ArancelMXError)
```

- [ ] **Step 2: `class WcoSupportError(ArancelMXError):`**

- [ ] **Step 3: pytest that test. Commit** `fix: treat WCO cache failures as ArancelMXError`

---

### Task 2: `wco cite` / `wco download` CLI

**Files:**
- Modify: `src/arancel_mx/consumer/cli.py` (`register_consumer_commands`, `run_consumer`)
- Create: `tests/consumer/test_cli_wco.py`
- Modify: `tests/consumer/test_cli_parser.py` (add `"wco"` to the command list)

Parser shape (mirror `data`):

```text
arancel-mx wco cite 61
arancel-mx wco cite gir
arancel-mx wco download 61 [--offline]
arancel-mx wco download gir [--offline]
```

Spanish help:

- `wco`: `Cita o descarga PDF HS 2022 de la OMA (apoyo de lectura, no autoridad LIGIE/NICO)`
- `cite`: `Muestra URL y ruta local si está en caché; no descarga`
- `download`: `Descarga el PDF al caché local`

`cite` calls `cite_chapter` / `cite` for gir via `gir_pdf_url` + `local_gir_pdf` (add a `cite_gir()` helper in `wco_support.py` if `cite_chapter("gir")` is wrong — it is wrong; gir is not a chapter).

Table stdout for cite (one block):

```text
WCO support  {url}
WCO cache    {local_path or (none)}
{disclaimer}
```

JSON: `render_json` of `WcoCite` (dataclass already). Wire `--format` on cite like other commands.

- [ ] **Step 1: Tests first** in `test_cli_wco.py`:
  - `cite 01` prints `01_2022e.pdf` URL, does not call `urlopen` (`monkeypatch` boom).
  - `cite gir` prints `0001_2022e-gir.pdf`.
  - `download 01 --offline` with empty cache: stderr `error:`, exit 2, no traceback.
  - `download 01` with fake `%PDF` body writes cache, then `cite 01` shows `WCO cache` path.
  - Invalid `cite 99` / `cite 0`: exit 2, `error:`.
  - `--help` Spanish: `apoyo`, `no autoridad` or `LIGIE`.

- [ ] **Step 2: Implement the smallest argparse + handlers.** Catch `ValueError` from chapter normalize by converting to `QueryError`/`ArancelMXError` so `main()` returns 2.

- [ ] **Step 3: pytest the new file + parser. Commit** `feat: add arancel-mx wco cite and download`

---

### Task 3: Shared banner; search table; empty suggest

**Files:**
- Modify: `src/arancel_mx/consumer/output.py`
- Create: `tests/consumer/test_cli_search_table.py`
- Modify: `tests/consumer/test_output.py` (search table / empty suggest)
- Modify: `tests/consumer/test_cli_suggest_local.py` only if the reproductores banner bytes change; keep them if the helper emits the same line.

Helper:

```python
def _hit_banner(index: int, total: int, result: SearchResult) -> str:
    return (
        f"--- {index}/{total}  {result.record.code}  score={result.score}  "
        f"confidence={result.confidence}  scorer={result.scorer_version} ---"
    )
```

Search table (not ficha):

```text
--- 1/N  CODE  score=…  confidence=…  scorer=1 ---
{format_code(code)}  {Nivel}  {description}
```

Empty suggest: `disclaimer + "\nNo results."` when `SuggestHit` sequence is empty. Today empty tuples are `"No results."` only — detect suggest via `empty_csv_schema == "suggest"` or pass disclaimer. Smallest: in `render_table`, if `not items` and caller is suggest, include disclaimer. `render()` already gets `empty_csv_schema`. Thread it into `render_table`.

- [ ] **Step 1: Failing goldens** for `search reproductores --limit 1 --dataset fixture` table, and empty suggest table.

- [ ] **Step 2: Implement helper + search table + empty suggest.**

- [ ] **Step 3: pytest output + search table + existing suggest local golden. Commit** `feat: share search/suggest table banner`

---

### Task 4: Suggest golden with a national note; Spanish suggest help

**Files:**
- Modify: `tests/consumer/test_cli_suggest_local.py` (add a notes-present test; do not replace the none-notes reproductores golden)
- Modify: `src/arancel_mx/consumer/cli.py` suggest `help_text` / `description` to Spanish retrieve-only
- Modify: `tests/consumer/test_cli_queries.py` `test_suggest_help_is_retrieve_only_not_a_classification` to accept Spanish (`no es una clasificación` / `solo recuperación` / `retrieve-only` — keep “no clasifica” meaning)

Suggest help Spanish:

`Sugerencias retrieve-only; no es una clasificación`

- [ ] **Step 1: Notes-present CLI test** — copy the DuckDB inserts from `test_suggest_national_notes_attach_when_present`, then `main(["suggest", "reproductores", "--dataset", str(path)])` and assert `Los animales vivos de este capítulo.` and `Notas nacionales` without `(none)`.

- [ ] **Step 2: Spanish help. Commit** `test: lock suggest table with national notes`

---

### Task 5: Docs (minimal)

**Files:**
- Modify: `docs/consumer-cli.md` — one `wco cite` / `wco download` example and the retrieve-only / WCO-not-authority line.
- Modify: `docs/external-consumption.md` only if a required phrase is missing after CLI change.

- [ ] **Step 1: `PYTHONPATH=$PWD/src python -m pytest -q tests/consumer/test_docs_contract.py tests/consumer/test_cli_wco.py tests/consumer/test_cli_search_table.py tests/consumer/test_cli_suggest_local.py tests/consumer/test_cli_parser.py tests/consumer/test_output.py tests/consumer/test_wco_support.py`**

- [ ] **Step 2: Push `cursor/suggest-product-0f14`. Open a draft PR targeting `cursor/retrieval-suggest-0f14` (not `main`).**
