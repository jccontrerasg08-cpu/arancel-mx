from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tomllib


HEAVY_MAINTAINER_DEPS = {"openpyxl", "PyMuPDF", "xlrd"}
CORE_RUNTIME_PREFIXES = {"duckdb", "filelock", "requests"}


def _project() -> dict[str, object]:
    return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]


def _dependency_names(values: list[str]) -> set[str]:
    names = set()
    for value in values:
        token = value.split(";", 1)[0].strip()
        for separator in ("[", "<", ">", "=", "!", "~", " "):
            token = token.split(separator, 1)[0]
        names.add(token)
    return names


def test_base_install_contains_only_consumer_runtime_dependencies() -> None:
    project = _project()
    names = _dependency_names(project["dependencies"])
    assert names == CORE_RUNTIME_PREFIXES
    assert names.isdisjoint(HEAVY_MAINTAINER_DEPS)


def test_maintainer_extra_contains_pipeline_dependencies() -> None:
    extras = _project()["optional-dependencies"]
    maintainer = _dependency_names(extras["maintainer"])
    assert HEAVY_MAINTAINER_DEPS <= maintainer


def test_dev_extra_preserves_full_repository_tooling() -> None:
    extras = _project()["optional-dependencies"]
    dev = _dependency_names(extras["dev"])
    assert HEAVY_MAINTAINER_DEPS <= dev
    assert {"build", "pytest"} <= dev


def test_consumer_import_and_help_do_not_import_maintainer_heavy_modules() -> None:
    code = r'''
import importlib.abc
import sys

blocked = {"pandas", "openpyxl", "fitz", "pymupdf", "xlrd"}

class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in blocked:
            raise ModuleNotFoundError(f"blocked maintainer dependency imported: {fullname}")
        return None

sys.meta_path.insert(0, Blocker())
import arancel_mx
from arancel_mx.cli import build_parser
text = build_parser().format_help()
assert "lookup" in text and "doctor" in text and "build" in text
'''
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
