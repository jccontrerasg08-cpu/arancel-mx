from __future__ import annotations

from importlib import metadata
from pathlib import Path

import arancel_mx


def test_runtime_version_matches_installed_distribution_metadata() -> None:
    assert arancel_mx.__version__ == metadata.version("arancel-mx")


def test_init_has_no_literal_duplicate_project_version() -> None:
    source = Path("src/arancel_mx/__init__.py").read_text(encoding="utf-8")
    assert '__version__ = "0.' not in source
    assert "_distribution_version(\"arancel-mx\")" in source


def test_public_exports_include_dataset_and_runtime_version() -> None:
    assert "Dataset" in arancel_mx.__all__
    assert "__version__" in arancel_mx.__all__
    assert arancel_mx.Dataset is not None
