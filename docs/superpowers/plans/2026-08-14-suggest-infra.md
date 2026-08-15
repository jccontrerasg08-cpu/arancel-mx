# Suggest infra Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make PR #78 mergeable: `main` merged, JSON CLI goldens for description `search` and `suggest`, canary runs `suggest --offline`.

**Architecture:** Tests and the canary workflow only. No ranking, table, or `wco` CLI changes.

**Tech Stack:** pytest, GitHub Actions, existing `arancel_mx.cli.main`, `consumer_duckdb` fixture.

## Global Constraints

- Branch: `cursor/retrieval-suggest-0f14` at `/workspace/.worktrees/retrieval-suggest`.
- `PYTHONPATH=$PWD/src` for every pytest / `python -m arancel_mx` run.
- No force-push. No merge of the GitHub PR. Do not mark draft ready.
- Do not edit `src/arancel_mx/consumer/cli.py`, `output.py`, or `SUGGEST_REPRODUCTORES_TABLE`.
- Do not edit CHANGELOG.md (coordinator owns it).
- No LLM, no nomenclator vendor, no WCO in `source_registry.json`.

---

### Task 1: JSON search golden

**Files:**
- Create: `tests/consumer/test_cli_search_json.py`

**Interfaces:**
- Consumes: `arancel_mx.cli.main`, `consumer_duckdb` fixture
- Produces: byte-stable JSON stdout for `search reproductores --limit 1 --format json --dataset <duckdb>`

- [ ] **Step 1: Capture expected JSON**

```bash
cd /workspace/.worktrees/retrieval-suggest
PYTHONPATH=$PWD/src python - <<'PY'
from pathlib import Path
from arancel_mx.cli import main
from tests.consumer.conftest import create_consumer_duckdb
from io import StringIO
import sys
path = Path("/tmp/fixture-search.duckdb")
create_consumer_duckdb(path)
sys.argv = ["arancel-mx"]
# use main() with cap-like redirect
import io
buf = io.StringIO()
err = io.StringIO()
oldout, olderr = sys.stdout, sys.stderr
sys.stdout, sys.stderr = buf, err
rc = main(["search", "reproductores", "--limit", "1", "--format", "json", "--dataset", str(path)])
sys.stdout, sys.stderr = oldout, olderr
print("rc", rc)
print(buf.getvalue())
print("err", err.getvalue())
PY
```

- [ ] **Step 2: Write the test** (lock stdout JSON, empty stderr, exit 0). Also run the same argv via `subprocess` with `PYTHONPATH=$ROOT/src`. Assert first hit `record.code`, `scorer_version == "1"`, `match_kind == "description"`, `confidence` in `[0, 1]`. Prefer `assert out == GOLDEN` after capturing once.

- [ ] **Step 3: Run**

```bash
PYTHONPATH=$PWD/src python -m pytest -q tests/consumer/test_cli_search_json.py
```

Expected: PASS

- [ ] **Step 4: Commit** `test: lock search JSON CLI against local DuckDB`

---

### Task 2: JSON suggest golden

**Files:**
- Create: `tests/consumer/test_cli_suggest_json.py`

- [ ] **Step 1: Capture** `suggest reproductores --format json --dataset fixture` the same way as Task 1.

- [ ] **Step 2: Write the test.** Lock stdout JSON. Assert `disclaimer` contains `not a classification`, `search.record.code == "01012101"`, `ficha.formatted_code == "0101.21.01"`, `national_notes == []`, `search.scorer_version == "1"`. Plus subprocess with `PYTHONPATH=$ROOT/src`.

- [ ] **Step 3: Run** `PYTHONPATH=$PWD/src python -m pytest -q tests/consumer/test_cli_suggest_json.py tests/consumer/test_cli_suggest_local.py`

Expected: PASS. Local table golden unchanged.

- [ ] **Step 4: Commit** `test: lock suggest JSON CLI against local DuckDB`

---

### Task 3: Canary runs suggest offline

**Files:**
- Modify: `.github/workflows/published-bundle-canary.yml`
- Modify: `tests/test_published_bundle_canary.py`

- [ ] **Step 1: After `arancel-mx data verify --bundle`, add:**

```yaml
      - name: Retrieve-only suggest against the downloaded dataset
        run: arancel-mx suggest reproductores --offline
```

- [ ] **Step 2: Update `test_canary_installs_runtime_package_without_classifier_or_dev_extras` to require `arancel-mx suggest reproductores --offline` after verify, and keep order `install < download < verify < suggest`. Still forbid `[hs]`, `OPENAI`, `dspy`, `.[dev]`.**

- [ ] **Step 3: Run** `PYTHONPATH=$PWD/src python -m pytest -q tests/test_published_bundle_canary.py`

- [ ] **Step 4: Commit** `ci: run suggest --offline in published-bundle canary`

---

### Task 4: Blast radius

- [ ] **Step 1: Run**

```bash
PYTHONPATH=$PWD/src python -m pytest -q tests/consumer/test_cli_search_json.py tests/consumer/test_cli_suggest_json.py tests/consumer/test_cli_suggest_local.py tests/test_published_bundle_canary.py tests/package/test_consumer_probe.py tests/test_public_distribution.py
```

Expected: PASS

- [ ] **Step 2: `git push -u origin cursor/retrieval-suggest-0f14`** (never force).
