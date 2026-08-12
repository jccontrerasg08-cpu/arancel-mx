# PyPI Consumer CLI and Doctor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:test-driven-development` for every behavior change and `superpowers:verification-before-completion` before marking a task complete.

**Goal:** Add the consumer-facing CLI contract for `arancel-mx 0.2.0` without breaking the existing maintainer commands, and provide a deterministic `doctor` diagnostic command for external users and support.

**Architecture:** Keep `src/arancel_mx/cli.py` as the single console entrypoint, but move consumer-specific parsing/handlers/output into `src/arancel_mx/consumer/cli.py`, `src/arancel_mx/consumer/output.py`, and `src/arancel_mx/consumer/doctor.py`. The top-level CLI assembles consumer and maintainer subcommands and maps public `ArancelMXError` exceptions to stable exit codes/messages. Consumer handlers depend only on the public consumer service boundary, not on ETL internals.

**Depends on:** `2026-08-11-pypi-consumer-core.md` Tasks 1-10.

## Global behavior contract

- Existing maintainer commands remain available: `build`, `check-updates`, deprecated read-only `update`, `reconcile`, `release`.
- Consumer commands: `doctor`, `data status|download|update|list|path|verify`, `lookup`, `search`, `parent`, `children`, `provenance`.
- Common options: `--dataset`, `--offline`, `--format table|json|csv`, `--limit` where applicable.
- CLI flags override environment variables; environment variables override defaults.
- Machine output is deterministic. JSON uses stable keys/order policy; CSV uses stable headers and newline behavior.
- `data path` prints only the path on stdout on success.
- User-facing errors go to stderr. No traceback for expected public errors.
- `doctor`: `0=HEALTHY`, `1=DEGRADED`, `2=UNHEALTHY`.
- No command may print auth headers, cookies, tokens, unrelated environment variables, or private file contents.
- TDD sequence for every task: focused red test -> observe expected failure -> minimal implementation -> focused green -> relevant suite -> commit.

---

### Task 1: Consumer parser composition without breaking maintainer CLI

**Files:**
- Create: `src/arancel_mx/consumer/cli.py`
- Modify: `src/arancel_mx/cli.py`
- Modify: `tests/test_cli.py`
- Create: `tests/consumer/test_cli_parser.py`

**First red tests:**
- `test_parser_exposes_consumer_and_maintainer_commands()`
- `test_existing_maintainer_help_remains_available()`
- `test_no_args_still_returns_help_and_zero()`
- `test_update_alias_warning_is_unchanged()`

**Implementation:**
- Add a small `register_consumer_commands(subparsers)` function.
- Keep maintainer parser construction in the existing top-level CLI until a later refactor is justified.
- Add `--version` at top level using package runtime metadata.
- Ensure `python -m arancel_mx --help` and `arancel-mx --help` share the same parser.

**Verify:**
```bash
python -m pytest tests/test_cli.py tests/consumer/test_cli_parser.py -q
```

**Commit:** `feat: compose consumer and maintainer CLI commands`

---

### Task 2: Deterministic output serializers

**Files:**
- Create: `src/arancel_mx/consumer/output.py`
- Create: `tests/consumer/test_output.py`

**First red tests:**
- `test_json_output_is_utf8_safe_and_deterministic()`
- `test_csv_output_has_stable_headers()`
- `test_table_output_handles_none_without_literal_python_repr()`
- `test_path_output_is_plain_text_only()`

**Implementation:**
- Serialize dataclasses/models through an explicit public-field mapping.
- JSON: `ensure_ascii=False`; deterministic key order.
- CSV: stable field list per result type and `lineterminator="\n"`.
- Table output is human convenience only and must not be parsed by tests as a machine contract.

**Verify:**
```bash
python -m pytest tests/consumer/test_output.py -q
```

**Commit:** `feat: add deterministic consumer output formats`

---

### Task 3: `lookup`, `search`, `parent`, `children`, `provenance`

**Files:**
- Modify: `src/arancel_mx/consumer/cli.py`
- Create: `tests/consumer/test_cli_queries.py`

**First red tests:**
- `test_lookup_json_contract()`
- `test_lookup_invalid_code_returns_public_error()`
- `test_search_accepts_limit_and_format()`
- `test_parent_returns_one_record()`
- `test_children_returns_deterministic_sequence()`
- `test_provenance_json_contract()`
- `test_query_dataset_override_selects_requested_release()`
- `test_query_offline_flag_never_calls_network()`

**Implementation:**
- Handlers construct/select `Dataset` through one helper.
- Reuse public exception types from core plan.
- Do not embed SQL in CLI handlers.
- Exit code for normal consumer command errors: `2`.

**Verify:**
```bash
python -m pytest tests/consumer/test_cli_queries.py -q
```

**Commit:** `feat: expose tariff query commands in CLI`

---

### Task 4: `data download` and `data path`

**Files:**
- Modify: `src/arancel_mx/consumer/cli.py`
- Create: `tests/consumer/test_cli_data_download.py`

**First red tests:**
- `test_data_download_returns_verified_path()`
- `test_data_download_existing_verified_cache_is_idempotent()`
- `test_data_download_dataset_option_pins_version()`
- `test_data_path_stdout_contains_only_path()`
- `test_data_path_missing_cache_fails_without_noise_on_stdout()`

**Implementation:**
- `download` delegates to `DatasetManager` and never deletes older verified versions.
- `path` never triggers an implicit download.

**Verify:**
```bash
python -m pytest tests/consumer/test_cli_data_download.py -q
```

**Commit:** `feat: add data download and path commands`

---

### Task 5: `data status` and `data list`

**Files:**
- Modify: `src/arancel_mx/consumer/cli.py`
- Create: `tests/consumer/test_cli_data_status.py`

**First red tests:**
- `test_data_status_reports_selected_and_local_latest()`
- `test_data_status_offline_makes_zero_http_calls()`
- `test_data_status_online_reports_remote_newer_when_present()`
- `test_data_list_defaults_to_verified_local_versions()`
- `test_data_list_remote_filters_malformed_or_prerelease_tags()`

**Implementation:**
- Status returns a structured model/dict before formatting.
- `data list --remote` does metadata discovery only, not DuckDB download.

**Verify:**
```bash
python -m pytest tests/consumer/test_cli_data_status.py -q
```

**Commit:** `feat: add data status and list commands`

---

### Task 6: `data update`

**Files:**
- Modify: `src/arancel_mx/consumer/cli.py`
- Create: `tests/consumer/test_cli_data_update.py`

**First red tests:**
- `test_data_update_downloads_newer_valid_release()`
- `test_data_update_reports_no_change()`
- `test_data_update_does_not_overwrite_old_verified_version()`
- `test_data_update_offline_is_rejected_with_actionable_error()`

**Implementation:**
- Compare local newest verified version to newest valid remote version.
- Never mutate an existing verified directory.

**Verify:**
```bash
python -m pytest tests/consumer/test_cli_data_update.py -q
```

**Commit:** `feat: add safe dataset update command`

---

### Task 7: `data verify` local, online, and bundle modes

**Files:**
- Modify: `src/arancel_mx/consumer/cli.py`
- Create: `tests/consumer/test_cli_data_verify.py`

**First red tests:**
- `test_data_verify_default_uses_only_local_metadata()`
- `test_data_verify_online_compares_remote_release_identity()`
- `test_data_verify_bundle_checks_all_six_assets()`
- `test_data_verify_integrity_failure_returns_nonzero_and_does_not_repair_silently()`

**Implementation:**
- Default verification is read-only/local.
- `--online` refreshes metadata comparison but does not silently replace data.
- `--bundle` explicitly performs the expensive six-asset verification path.

**Verify:**
```bash
python -m pytest tests/consumer/test_cli_data_verify.py -q
```

**Commit:** `feat: add layered dataset verification command`

---

### Task 8: Doctor data model and individual checks

**Files:**
- Create: `src/arancel_mx/consumer/doctor.py`
- Create: `tests/consumer/test_doctor.py`

**First red tests:**
- `test_doctor_healthy_when_all_core_checks_pass()`
- `test_doctor_degraded_when_network_fails_but_verified_cache_is_usable()`
- `test_doctor_unhealthy_when_no_usable_dataset_exists()`
- `test_doctor_does_not_expose_sensitive_environment_values()`
- `test_doctor_checks_read_only_duckdb_query()`
- `test_doctor_offline_skips_network_check()`

**Implementation checks:**
- package version;
- Python version;
- OS/architecture;
- installed distribution metadata;
- console entrypoint metadata;
- packaged source registry;
- cache path/writability;
- network/release resolution when online;
- manifest/schema compatibility;
- checksum/verified state;
- DuckDB read-only open;
- known local query smoke;
- offline readiness.

Use immutable diagnostic result models. Each check has `name`, `status`, concise `detail`, and optional non-sensitive metadata.

**Verify:**
```bash
python -m pytest tests/consumer/test_doctor.py -q
```

**Commit:** `feat: implement consumer doctor diagnostics`

---

### Task 9: `doctor` human and JSON CLI contract

**Files:**
- Modify: `src/arancel_mx/consumer/cli.py`
- Create: `tests/consumer/test_cli_doctor.py`

**First red tests:**
- `test_doctor_cli_healthy_exit_zero()`
- `test_doctor_cli_degraded_exit_one()`
- `test_doctor_cli_unhealthy_exit_two()`
- `test_doctor_json_has_stable_schema()`
- `test_doctor_human_output_contains_no_secrets()`

**Implementation:**
- `doctor --json` and human output consume the same result model.
- Stable exit code mapping is independent of formatting.

**Verify:**
```bash
python -m pytest tests/consumer/test_cli_doctor.py tests/consumer/test_doctor.py -q
```

**Commit:** `feat: expose doctor command and exit contract`

---

### Task 10: Expected-error mapping and traceback boundary

**Files:**
- Modify: `src/arancel_mx/cli.py`
- Modify: `src/arancel_mx/consumer/cli.py`
- Create: `tests/consumer/test_cli_errors.py`

**First red tests:**
- `test_public_error_prints_actionable_stderr_without_traceback()`
- `test_unexpected_programming_error_is_not_misreported_as_integrity_error()`
- `test_json_decode_and_requests_internals_do_not_leak_as_primary_contract()`

**Implementation:**
- Catch documented public consumer exceptions at CLI boundary.
- Keep existing maintainer error behavior compatible.
- Avoid broad `except Exception` that hides defects.

**Verify:**
```bash
python -m pytest tests/consumer/test_cli_errors.py tests/test_cli.py -q
```

**Commit:** `refactor: enforce CLI public error boundary`

---

### Task 11: End-to-end CLI fixture against a certified small DuckDB

**Files:**
- Create: `tests/fixtures/consumer/create_consumer_fixture.py`
- Create: `tests/consumer/test_cli_e2e.py`
- Reuse/modify only if appropriate: `tests/certification/test_consumer.py`

**First red tests:**
- full local sequence: status -> verify -> lookup -> search -> parent -> children -> provenance;
- same sequence with `ARANCEL_MX_OFFLINE=1` and network function patched to fail if called;
- path containing spaces and `ñ`.

**Implementation:**
- Build deterministic tiny fixture matching the public DuckDB relation contract.
- Do not use live GitHub for deterministic PR CI.

**Verify:**
```bash
python -m pytest tests/consumer -q
```

**Commit:** `test: add deterministic consumer CLI end-to-end coverage`

---

### Task 12: Documentation examples and compatibility proof

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`
- Create: `docs/consumer-cli.md`
- Modify: `tests/test_autonomous_documentation.py` or add focused consumer docs test.

**Required examples:**
```bash
pip install arancel-mx
arancel-mx doctor
arancel-mx data download
arancel-mx lookup 01012101
arancel-mx search "refrigeradores"
arancel-mx data verify
```

Document offline use, data version pinning, machine formats, and distinction between package version and dataset version.

**Verify:**
```bash
python -m pytest tests/test_autonomous_documentation.py tests/consumer -q
python -m arancel_mx --help
```

**Commit:** `docs: document consumer CLI and diagnostics`

## Completion gate

This subplan is complete only when:

```bash
python -m pytest tests/consumer tests/test_cli.py -q
python -m arancel_mx --help
python -m arancel_mx doctor --help
python -m arancel_mx data --help
```

all pass, maintainer command tests remain green, and no live registry/network mutation is required by deterministic CI.