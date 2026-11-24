from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from arancel_mx.cli import main
from arancel_mx.consumer.release_diff import release_diff_report
from arancel_mx.consumer.release_diff_markdown import NO_VALUE, release_diff_markdown
from tests.consumer.conftest import create_consumer_duckdb


def _row(code: str, level: str = "fraccion8", **values: object) -> dict[str, object]:
    row: dict[str, object] = {
        "code": code, "level": level, "description": "Caballos", "igi_text": "10",
        "ige_text": "Ex.", "unit_code": "1", "parent": code[:6],
    }
    row.update(values)
    return row


def _report(before: list[dict[str, object]], after: list[dict[str, object]], *, verified: bool = True, **kwargs: object) -> dict[str, object]:
    info = {"release_verified": verified, "github_digest_state": "verified" if verified else "not_applicable"}
    return release_diff_report(
        {str(r["code"]): r for r in before},
        {str(r["code"]): r for r in after},
        from_info={"dataset_version": "2026.08.15", **info},
        to_info={"dataset_version": "2026.11.20", **info},
        **kwargs,  # type: ignore[arg-type]
    )


def test_renders_counts_changes_and_the_not_a_legal_event_note() -> None:
    text = release_diff_markdown(_report([_row("01012101")], [_row("01012101", igi_text="15")]))
    assert text.startswith("# Comparación de releases 2026.08.15 → 2026.11.20\n")
    assert "No son eventos legales" in text
    assert "- Estado de la comparación: snapshots verificados" in text
    assert "| Cambio de IGI | 1 |" in text
    assert "| `0101.21.01` | Fracción | Cambio de IGI | 10 | 15 |" in text


def test_a_value_that_disappears_is_written_as_no_value_never_as_zero() -> None:
    text = release_diff_markdown(_report([_row("01012101")], [_row("01012101", igi_text=None)], verified=False))
    assert f"| Cambio de IGI | 10 | {NO_VALUE} |" in text
    assert "al menos un archivo local sin verificación remota" in text


def test_release_text_cannot_break_the_table_or_add_markup() -> None:
    hostile = "Uno | dos [x](javascript:alert(1)) <img src=x>"
    text = release_diff_markdown(_report([_row("01012101")], [_row("01012101", description=hostile)]))
    line = next(line for line in text.splitlines() if "Cambio de descripción |" in line and "0101.21.01" in line)
    assert line.count(" | ") == 4  # five cells, the pipe in the text is escaped
    assert "\\|" in line and "\\[x\\]" in line and "\\<img" in line


def test_identical_releases_and_auxiliary_tables() -> None:
    report = _report([_row("01012101")], [_row("01012101")])
    report["auxiliary"] = {
        "nom": {"status": "not_compared", "reason": "from: view not present", "changes": []},
        "national_notes": {
            "status": "compared",
            "changes": [{"chapter": "01", "scope_type": "chapter", "scope_value": "01", "note_number": "1",
                         "event": "note_text_changed", "old_value": "Texto", "new_value": "Texto nuevo"}],
        },
    }
    text = release_diff_markdown(report)
    assert "Las dos releases no difieren en los niveles comparados." in text
    assert "No comparada: from: view not present." in text
    assert "| Cambio de texto de nota | Texto | Texto nuevo |" in text


def test_cli_writes_markdown_for_two_local_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = create_consumer_duckdb(tmp_path / "before.duckdb", dataset_version="2026.08.11")
    after = create_consumer_duckdb(tmp_path / "after.duckdb", dataset_version="2026.08.12")
    with duckdb.connect(str(after)) as conn:
        conn.execute("UPDATE canonical_record SET igi_text = '15' WHERE code = '01012101'")
    assert main(["data", "diff", "--from", str(before), "--to", str(after), "--format", "markdown"]) == 0
    text = capsys.readouterr().out
    assert text.startswith("# Comparación de releases 2026.08.11 → 2026.08.12\n")
    assert "| `0101.21.01` | Fracción | Cambio de IGI | 10 | 15 |" in text
