from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import validate_package_tag as validator


def test_accepts_matching_final_tag_and_project_version() -> None:
    result = validator.evaluate("pkg-v0.2.0", "0.2.0")
    assert result == {
        "tag": "pkg-v0.2.0",
        "version": "0.2.0",
        "is_prerelease": False,
        "production_eligible": True,
    }


def test_accepts_matching_rc_tag_and_project_version() -> None:
    result = validator.evaluate("pkg-v0.2.0rc1", "0.2.0rc1")
    assert result["is_prerelease"] is True
    assert result["production_eligible"] is False
    assert result["version"] == "0.2.0rc1"


def test_rejects_non_pkg_tag() -> None:
    with pytest.raises(validator.TagError):
        validator.evaluate("v0.2.0", "0.2.0")


def test_rejects_tag_version_mismatch() -> None:
    with pytest.raises(validator.TagError):
        validator.evaluate("pkg-v0.2.1", "0.2.0")


def test_rejects_malformed_pep440_version() -> None:
    with pytest.raises(validator.TagError):
        validator.evaluate("pkg-v0.2.0.final", "0.2.0")


def test_identifies_release_candidate_as_testpypi_only() -> None:
    final = validator.evaluate("pkg-v0.2.0", "0.2.0")
    candidate = validator.evaluate("pkg-v0.2.0rc2", "0.2.0rc2")
    assert final["production_eligible"] is True
    assert candidate["production_eligible"] is False


def test_project_version_reads_repository_pyproject() -> None:
    # The repository is the single source of truth for the package version.
    assert validator.normalize_version(validator.project_version())[0]


def test_github_output_lines_are_single_line_key_values() -> None:
    result = validator.evaluate("pkg-v0.2.0", "0.2.0")
    rendered = validator.render_output_lines(result)
    parsed = dict(line.split("=", 1) for line in rendered.splitlines())
    assert parsed == {
        "version": "0.2.0",
        "is_prerelease": "false",
        "production_eligible": "true",
    }


def test_cli_emits_github_output_without_reserved_name_in_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "gh-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    exit_code = validator.main(["pkg-v0.2.0", "--pyproject", str(_pyproject(tmp_path)), "--github-output"])
    assert exit_code == 0
    emitted = dict(line.split("=", 1) for line in output.read_text().splitlines())
    assert emitted["production_eligible"] == "true"
    assert json.loads(capsys.readouterr().out)["version"] == "0.2.0"


def test_cli_rejects_mismatched_tag(tmp_path: Path) -> None:
    assert validator.main(["pkg-v9.9.9", "--pyproject", str(_pyproject(tmp_path))]) == 2


def _pyproject(tmp_path: Path) -> Path:
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nname = "arancel-mx"\nversion = "0.2.0"\n', encoding="utf-8")
    return path
