import json
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.fetch_previous_release import _parse_manifest
from arancel_mx.pipeline import official_dataset
from arancel_mx.pipeline.official_dataset import OfficialDatasetConfig, build_official_dataset
from arancel_mx.release.metadata import SourceIdentity, source_identity_from_manifest


LEGACY_VERSION = "2026.08.10"


def legacy_manifest(version=LEGACY_VERSION):
    return {
        "dataset_version": version,
        "schema_version": "1",
        "validation_status": "passed",
        "row_count": 26641,
        "artifact_sha256": {
            "arancel_mx.csv": "a" * 64,
            "arancel_mx.json": "b" * 64,
            "arancel_mx.duckdb": "c" * 64,
        },
    }


def identity(dataset_key, document_role, url):
    return SourceIdentity(
        dataset_key=dataset_key,
        document_role=document_role,
        source_url=url,
        sha256="d" * 64,
        registry_version="2026-08-10",
    )


def current_identities():
    return (
        identity("ligie", "ligie_snapshot", "https://www.snice.gob.mx/ligie.xlsx"),
        identity("nico", "nico_snapshot", "https://www.snice.gob.mx/nico.xlsx"),
        identity(
            "diputados_ligie",
            "legal_ledger",
            "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm",
        ),
        identity("diputados_ligie", "consolidated_text", "https://www.diputados.gob.mx/LIGIE.pdf"),
        identity("dof_law_reform", "law_reform", "https://www.dof.gob.mx/reform.pdf"),
    )


def test_known_schema_v1_release_is_marked_as_legacy_baseline():
    parsed = _parse_manifest(
        json.dumps(legacy_manifest()).encode("utf-8"),
        LEGACY_VERSION,
    )

    assert parsed["baseline_status"] == "legacy_baseline"
    assert parsed["schema_version"] == "1"
    assert "source_identity" not in parsed
    with pytest.raises(ValueError, match="source_identity"):
        source_identity_from_manifest(parsed)


def test_unknown_future_schema_v1_release_is_not_accepted_as_legacy():
    with pytest.raises(ValueError, match="source_identity"):
        _parse_manifest(
            json.dumps(legacy_manifest("2026.08.11")).encode("utf-8"),
            "2026.08.11",
        )


def test_legacy_baseline_forces_full_schema_v2_build_instead_of_no_change(
    tmp_path, monkeypatch
):
    config = OfficialDatasetConfig(
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "release",
        effective_as_of=date(2026, 8, 11),
        dataset_version="2026.08.11",
        generated_at=datetime(2026, 8, 11, 8, 0, tzinfo=timezone.utc),
    )
    snapshot = SimpleNamespace(
        identities=current_identities(),
        sources=(
            SimpleNamespace(
                dataset_key="ligie",
                document_role="ligie_snapshot",
                capture=SimpleNamespace(path=Path("/ligie.fixture")),
                source_document={"source_document_id": "source-ligie"},
            ),
            SimpleNamespace(
                dataset_key="nico",
                document_role="nico_snapshot",
                capture=SimpleNamespace(path=Path("/nico.fixture")),
                source_document={"source_document_id": "source-nico"},
            ),
            SimpleNamespace(
                dataset_key="diputados_ligie",
                document_role="legal_ledger",
                capture=SimpleNamespace(path=Path("/ledger.fixture")),
                source_document={"source_document_id": "source-ledger"},
            ),
            SimpleNamespace(
                dataset_key="diputados_ligie",
                document_role="consolidated_text",
                capture=SimpleNamespace(path=Path("/diputados.fixture")),
                source_document={"source_document_id": "source-diputados"},
            ),
            SimpleNamespace(
                dataset_key="national_notes",
                document_role="national_notes",
                capture=SimpleNamespace(path=Path("/national_notes.fixture")),
                source_document={"source_document_id": "source-national_notes-national_notes"},
                fetched=SimpleNamespace(
                    media_type="text/html",
                    content=b"<h2>Capitulo 01</h2><p>1. Nota nacional.</p>",
                    charset="utf-8",
                ),
            ),
        ),
    )
    monkeypatch.setattr(
        official_dataset,
        "capture_official_inputs",
        lambda config, session=None: snapshot,
    )

    def parser_reached(*_args, **_kwargs):
        raise RuntimeError("schema-v2 bootstrap reached full build")

    monkeypatch.setattr(official_dataset, "probe_workbook", parser_reached)
    previous = legacy_manifest()
    previous["baseline_status"] = "legacy_baseline"

    with pytest.raises(RuntimeError, match="schema-v2 bootstrap reached full build"):
        build_official_dataset(config, previous_manifest=previous)
