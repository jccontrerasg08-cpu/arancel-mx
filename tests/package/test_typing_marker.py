from __future__ import annotations

import inspect
from pathlib import Path
import subprocess
import sys
import zipfile

from arancel_mx import Dataset
from arancel_mx.consumer.models import DatasetInfo, ProvenanceRecord, SearchResult, TariffRecord


def test_py_typed_is_present_in_built_wheel(tmp_path: Path) -> None:
    out = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out)],
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(out.glob("arancel_mx-*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as archive:
        assert "arancel_mx/py.typed" in archive.namelist()


def test_public_dataset_signatures_have_annotations() -> None:
    for name in ("latest", "version", "open", "connect", "lookup", "search", "parent", "children", "provenance"):
        signature = inspect.signature(getattr(Dataset, name))
        assert signature.return_annotation is not inspect.Signature.empty, name
        for parameter in signature.parameters.values():
            if parameter.name in {"self", "cls"}:
                continue
            assert parameter.annotation is not inspect.Signature.empty, f"{name}.{parameter.name}"


def test_public_model_fields_are_annotated() -> None:
    for model in (DatasetInfo, ProvenanceRecord, SearchResult, TariffRecord):
        assert model.__annotations__, model.__name__
        assert all(value is not None for value in model.__annotations__.values())
