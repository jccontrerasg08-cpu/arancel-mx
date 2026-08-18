from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").lower().split())


def test_front_door_summarizes_fail_closed_trust_without_workflow_internals() -> None:
    spanish = _text("README.md")
    english = _text("README.en.md")

    for document in (spanish, english):
        assert "data-yyyy.mm.dd" in document
        assert "manifest" in document
        assert "sha256" in document
        assert "github release" in document
        assert ".github/workflows/official-data-pipeline.yml" not in document
        assert "requirements/production-build.txt" not in document

    assert "reconciliación y validación" in spanish
    assert "release verificada sigue siendo la fuente de verdad" in spanish
    assert "reconciliation + validation" in english
    assert "verified release remains the source of truth" in english


def test_release_process_documents_current_autonomous_fail_closed_pipeline() -> None:
    release = _text("docs/release-process.md")
    required = (
        ".github/workflows/official-data-pipeline.yml",
        "17 11 * * 1",
        "requirements/production-build.txt",
        "no_change",
        "github issue",
        "data-yyyy.mm.dd",
        "official-sources.tar.gz",
        "scripts/build_official_dataset.py",
        "publicación automática",
        "cualquier falla bloquea la publicación",
        "schema_version",
        "schema v2",
        "retrieved_at",
        "actual fetch time",
        "generated_at",
        "draft",
        "certify_bundle",
        "six assets",
        "immutable",
        "same-date",
        "release_tag_collision",
        "recovery",
        "ci / test",
        "artifact attestation",
        "actions/attest",
        "gh attestation verify",
        "--repo jccontrerasg08-cpu/arancel-mx",
        "--signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml",
        "sha256sums",
        "manifest.json",
        "not a legal signature",
        "source code",
        "release attestation",
    )

    assert [value for value in required if value not in release] == []
    assert "publication is manual" not in release
    assert "publicación es manual" not in release
    assert "build-official-dataset.yml" not in release


def test_sources_document_legal_reconciliation_as_blocking_gate() -> None:
    sources = _text("docs/sources.md")
    required = (
        "diputados",
        "dof",
        "registered",
        "ledger",
        "reconciliation",
        "blocking gate",
        "discrepancy",
        "publication",
        "retrieved_at",
        "siicex-caaarem",
        "tigies-mx",
        "tigiex",
        "rgce",
        "anexo 9",
        "igi_text",
        "not an official source",
        "last_law_reform",
        "2025-12-29",
        "data-2026.08.15",
        "ligie_2022_ref02_29dic25.pdf",
    )
    assert [value for value in required if value not in sources] == []


def test_data_model_separates_fetch_time_generation_time_and_internal_release_provenance() -> None:
    model = _text("docs/data-model.md")
    required = (
        "retrieved_at",
        "actual fetch time",
        "generated_at",
        "schema_version",
        "dataset_release.release_metadata_json",
        "internal release provenance",
        "registry_sha256",
        "github_run_id",
        "github_artifact_name",
        "arancel_mx_national_notes",
        "national_note",
    )
    assert [value for value in required if value not in model] == []
