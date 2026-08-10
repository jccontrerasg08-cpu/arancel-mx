from datetime import date, timezone
import json
from pathlib import Path

import pytest

import scripts.build_official_dataset as build_script


def test_script_parses_typed_build_configuration(tmp_path, monkeypatch, capsys):
    calls = []

    def fake_build(config):
        calls.append(config)
        return {"validation_status": "passed", "row_count": 5}

    monkeypatch.setattr(build_script, "build_official_dataset", fake_build)

    result = build_script.main(
        [
            "--work-dir",
            str(tmp_path / "work"),
            "--output-dir",
            str(tmp_path / "release"),
            "--effective-as-of",
            "2026-08-10",
            "--dataset-version",
            "2026.08.10",
            "--generated-at",
            "2026-08-10T08:00:00Z",
            "--timeout",
            "12.5",
        ]
    )

    assert result == 0
    assert len(calls) == 1
    config = calls[0]
    assert config.work_dir == Path(tmp_path / "work")
    assert config.output_dir == Path(tmp_path / "release")
    assert config.effective_as_of == date(2026, 8, 10)
    assert config.dataset_version == "2026.08.10"
    assert config.generated_at.tzinfo is timezone.utc
    assert config.generated_at.isoformat() == "2026-08-10T08:00:00+00:00"
    assert config.timeout_s == 12.5
    assert json.loads(capsys.readouterr().out) == {
        "row_count": 5,
        "validation_status": "passed",
    }


def test_script_rejects_invalid_dataset_version_without_building(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(
        build_script,
        "build_official_dataset",
        lambda config: calls.append(config),
    )

    result = build_script.main(
        [
            "--work-dir",
            str(tmp_path / "work"),
            "--output-dir",
            str(tmp_path / "release"),
            "--effective-as-of",
            "2026-08-10",
            "--dataset-version",
            "2026-8-10",
        ]
    )

    assert result == 2
    assert calls == []
    assert "dataset-version" in capsys.readouterr().err


@pytest.mark.parametrize("message", ["invalid source", "release already exists"])
def test_expected_build_error_returns_two(tmp_path, monkeypatch, capsys, message):
    def fail(config):
        raise ValueError(message)

    monkeypatch.setattr(build_script, "build_official_dataset", fail)

    result = build_script.main(
        [
            "--work-dir",
            str(tmp_path / "work"),
            "--output-dir",
            str(tmp_path / "release"),
            "--effective-as-of",
            "2026-08-10",
            "--dataset-version",
            "2026.08.10",
        ]
    )

    assert result == 2
    assert capsys.readouterr().err == f"error: {message}\n"
