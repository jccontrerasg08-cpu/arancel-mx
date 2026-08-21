from __future__ import annotations

from pathlib import Path
import tomllib


def _project() -> dict[str, object]:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    return payload["project"]


def test_project_version_is_033_release() -> None:
    assert _project()["version"] == "0.3.7"


def test_project_has_public_identity_urls_and_keywords() -> None:
    project = _project()
    assert project["authors"] == [{"name": "jccontrerasg08-cpu"}]
    assert project["maintainers"] == [{"name": "jccontrerasg08-cpu"}]
    keywords = set(project["keywords"])
    assert {"Mexico", "tariff", "TIGIE", "NICO", "HS", "DuckDB"} <= keywords
    urls = project["urls"]
    for key in ("Repository", "Issues", "Documentation", "Changelog", "Data Releases"):
        assert key in urls
        assert urls[key].startswith("https://github.com/jccontrerasg08-cpu/arancel-mx")


def test_project_license_and_python_floor_are_explicit() -> None:
    project = _project()
    assert project["license"] == "Apache-2.0"
    assert project["license-files"] == ["LICENSE", "NOTICE"]
    assert project["requires-python"] == ">=3.11"
    assert not any(str(item).startswith("License ::") for item in project["classifiers"])


def test_console_script_points_to_public_cli_entrypoint() -> None:
    project = _project()
    assert project["scripts"]["arancel-mx"] == "arancel_mx.cli:entrypoint"


def test_classifiers_do_not_claim_uncertified_future_python_versions() -> None:
    # Add newer interpreter classifiers only after the blocking matrix proves them.
    classifiers = set(_project()["classifiers"])
    assert "Development Status :: 4 - Beta" in classifiers
    assert "Programming Language :: Python :: 3 :: Only" in classifiers
    assert "Programming Language :: Python :: 3.11" in classifiers
    assert "Programming Language :: Python :: 3.12" in classifiers
    assert "Programming Language :: Python :: 3.13" in classifiers
    assert "Programming Language :: Python :: 3.14" not in classifiers


def test_distribution_metadata_does_not_claim_embedded_dataset() -> None:
    project = _project()
    description = str(project["description"]).lower()
    assert "dataset included" not in description
    assert "embedded dataset" not in description
