from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

import pytest


@pytest.fixture(scope="module")
def distributions(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    out = tmp_path_factory.mktemp("package-dist")
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(out)],
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(out.glob("arancel_mx-*.whl"))
    sdists = list(out.glob("arancel_mx-*.tar.gz"))
    assert len(wheels) == 1
    assert len(sdists) == 1
    return wheels[0], sdists[0]


def test_wheel_contains_public_runtime_contract(distributions: tuple[Path, Path]) -> None:
    wheel, _ = distributions
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    required = {
        "arancel_mx/__init__.py",
        "arancel_mx/cli.py",
        "arancel_mx/consumer/dataset.py",
        "arancel_mx/consumer/cli.py",
        "arancel_mx/sources/source_registry.json",
        "arancel_mx/py.typed",
    }
    assert required <= names
    assert any(name.endswith(".dist-info/METADATA") for name in names)
    assert any(name.endswith(".dist-info/entry_points.txt") for name in names)
    assert any(name.endswith(".dist-info/licenses/LICENSE") for name in names)
    assert any(name.endswith(".dist-info/licenses/NOTICE") for name in names)


def test_wheel_excludes_repository_and_dataset_payloads(distributions: tuple[Path, Path]) -> None:
    wheel, _ = distributions
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()

    forbidden_prefixes = ("tests/", "data/", "out/", "docs/", ".github/")
    forbidden_suffixes = (".duckdb", ".csv", ".xlsx", ".xls", ".pdf", ".tar.gz")
    assert not any(name.startswith(forbidden_prefixes) for name in names)
    assert not any(name.lower().endswith(forbidden_suffixes) for name in names)
    json_files = [name for name in names if name.endswith(".json")]
    assert json_files == ["arancel_mx/sources/source_registry.json"]


def test_sdist_contains_rebuild_inputs_and_public_package_docs(distributions: tuple[Path, Path]) -> None:
    _, sdist = distributions
    with tarfile.open(sdist, "r:gz") as archive:
        names = set(archive.getnames())

    root = "arancel_mx-0.2.0"
    required = {
        f"{root}/pyproject.toml",
        f"{root}/README.md",
        f"{root}/README.en.md",
        f"{root}/CHANGELOG.md",
        f"{root}/LICENSE",
        f"{root}/NOTICE",
        f"{root}/docs/package-release.md",
        f"{root}/docs/consumer-cli.md",
        f"{root}/docs/external-consumption.md",
        f"{root}/src/arancel_mx/__init__.py",
        f"{root}/src/arancel_mx/py.typed",
        f"{root}/src/arancel_mx/sources/source_registry.json",
    }
    assert required <= names


def test_sdist_excludes_generated_data_private_workspaces_and_tests(distributions: tuple[Path, Path]) -> None:
    _, sdist = distributions
    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()

    root = "arancel_mx-0.2.0/"
    forbidden_fragments = (
        f"{root}data/",
        f"{root}out/",
        f"{root}.git/",
        f"{root}.worktrees/",
        f"{root}tests/",
        f"{root}docs/superpowers/",
    )
    assert not any(fragment in name for name in names for fragment in forbidden_fragments)
    assert not any(name.lower().endswith((".duckdb", ".xlsx", ".xls", ".pdf")) for name in names)


def test_distribution_member_names_are_relative_and_non_sensitive(distributions: tuple[Path, Path]) -> None:
    wheel, sdist = distributions
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
    with tarfile.open(sdist, "r:gz") as archive:
        sdist_names = archive.getnames()

    for name in [*wheel_names, *sdist_names]:
        assert not name.startswith(("/", "\\"))
        lowered = name.lower()
        assert ".env" not in lowered
        assert "credential" not in lowered
        assert "private_key" not in lowered
        assert not lowered.endswith((".pem", ".key"))
