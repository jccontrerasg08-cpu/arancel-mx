from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from arancel_mx.pipeline import official_dataset
from arancel_mx.pipeline.official_dataset import OfficialDatasetConfig, build_official_dataset
from arancel_mx.release.metadata import SourceIdentity


SHA_A = "a" * 64
SHA_B = "b" * 64


def identity(dataset_key, document_role, source_url, sha256=SHA_A):
    return SourceIdentity(
        dataset_key=dataset_key,
        document_role=document_role,
        source_url=source_url,
        sha256=sha256,
        registry_version="2026-08-10",
    )


def identities():
    return (
        identity("ligie", "ligie_snapshot", "https://www.snice.gob.mx/ligie.xlsx"),
        identity("nico", "nico_snapshot", "https://www.snice.gob.mx/nico.xlsx"),
        identity(
            "diputados_ligie",
            "legal_ledger",
            "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm",
        ),
        identity(
            "diputados_ligie",
            "consolidated_text",
            "https://www.diputados.gob.mx/LIGIE.pdf",
        ),
        identity(
            "dof_law_reform",
            "law_reform",
            "https://www.diputados.gob.mx/reforma.pdf",
        ),
        identity(
            "dof_tariff_decree",
            "tariff_decree",
            "https://www.diputados.gob.mx/tarifa.pdf",
        ),
    )


def config(tmp_path, name="candidate"):
    return OfficialDatasetConfig(
        work_dir=tmp_path / f"{name}-work",
        output_dir=tmp_path / f"{name}-release",
        effective_as_of=date(2026, 8, 10),
        dataset_version="2026.08.10",
        generated_at=datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
    )


def captured_source(dataset_key, document_role=None):
    role = document_role or {
        "ligie": "ligie_snapshot",
        "nico": "nico_snapshot",
        "diputados_ligie": "consolidated_text",
    }[dataset_key]
    return SimpleNamespace(
        dataset_key=dataset_key,
        document_role=role,
        capture=SimpleNamespace(path=Path(f"/{dataset_key}.fixture")),
        source_document={"source_document_id": f"source-{dataset_key}-{role}"},
    )


def snapshot(current_identities):
    return SimpleNamespace(
        identities=tuple(current_identities),
        sources=(
            captured_source("ligie"),
            captured_source("nico"),
            captured_source("diputados_ligie", "legal_ledger"),
            captured_source("diputados_ligie", "consolidated_text"),
        ),
    )


def manifest(source_identities):
    return {
        "dataset_version": "2026.08.09",
        "validation_status": "passed",
        "row_count": 123,
        "source_identity": [item.to_dict() for item in source_identities],
    }


def test_identical_source_identity_skips_parsing_and_creates_no_release(
    tmp_path, monkeypatch
):
    build_config = config(tmp_path)
    current = identities()
    monkeypatch.setattr(
        official_dataset,
        "capture_official_inputs",
        lambda config, session=None: snapshot(current),
    )
    monkeypatch.setattr(
        official_dataset,
        "probe_workbook",
        lambda *_args, **_kwargs: pytest.fail("parser must not run for no_change"),
    )

    result = build_official_dataset(
        build_config,
        previous_manifest=manifest(current),
    )

    assert result == {
        "status": "no_change",
        "dataset_version": "2026.08.10",
        "schema_version": "2",
        "row_count": 123,
        "validation_status": "passed",
        "source_count": 6,
        "output_dir": None,
    }
    assert not build_config.output_dir.exists()
    assert not (build_config.work_dir / "candidate" / "arancel_mx.duckdb").exists()


def test_source_identity_order_does_not_create_false_change(tmp_path, monkeypatch):
    build_config = config(tmp_path, "reordered")
    current = identities()
    monkeypatch.setattr(
        official_dataset,
        "capture_official_inputs",
        lambda config, session=None: snapshot(current),
    )
    monkeypatch.setattr(
        official_dataset,
        "probe_workbook",
        lambda *_args, **_kwargs: pytest.fail("parser must not run for no_change"),
    )

    result = build_official_dataset(
        build_config,
        previous_manifest=manifest(tuple(reversed(current))),
    )

    assert result["status"] == "no_change"
    assert result["output_dir"] is None


def test_changed_source_identity_proceeds_into_full_build(tmp_path, monkeypatch):
    build_config = config(tmp_path, "changed")
    current = identities()
    previous = list(current)
    previous[0] = identity(
        "ligie",
        "ligie_snapshot",
        "https://www.snice.gob.mx/ligie.xlsx",
        sha256=SHA_B,
    )
    monkeypatch.setattr(
        official_dataset,
        "capture_official_inputs",
        lambda config, session=None: snapshot(current),
    )

    def parser_reached(*_args, **_kwargs):
        raise RuntimeError("full build reached")

    monkeypatch.setattr(official_dataset, "probe_workbook", parser_reached)

    with pytest.raises(RuntimeError, match="full build reached"):
        build_official_dataset(
            build_config,
            previous_manifest=manifest(tuple(previous)),
        )
