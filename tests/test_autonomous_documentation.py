from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").lower().split())


def test_bilingual_readmes_describe_autonomous_fail_closed_pipeline():
    spanish = _text("README.md")
    english = _text("README.en.md")

    shared = (
        ".github/workflows/official-data-pipeline.yml",
        "17 11 * * *",
        "requirements/production-build.txt",
        "no_change",
        "github issue",
        "data-yyyy.mm.dd",
        "official-sources.tar.gz",
        "check-updates",
    )
    for document in (spanish, english):
        assert [value for value in shared if value not in document] == []
        assert ".github/workflows/build-official-dataset.yml" in document

    assert "fuentes oficiales → captura → reconciliación legal → parseo → validación" in spanish
    assert "sin cambios: termina en verde" in spanish
    assert "cambio válido: release inmutable verificado" in spanish
    assert "cualquier fallo: bloquea la publicación + github issue" in spanish
    assert "official sources → capture → legal reconciliation → parse → validate" in english
    assert "unchanged: stop green" in english
    assert "changed + valid: verified immutable release" in english
    assert "any failure: block publication + github issue" in english


def test_release_process_documents_exact_publication_and_recovery_contract():
    release = _text("docs/release-process.md")
    required = (
        "schema_version",
        "schema v2",
        "retrieved_at",
        "actual fetch time",
        "generated_at",
        "no_change",
        "draft",
        "verify_publication_bundle",
        "six assets",
        "immutable",
        "same-date",
        "release_tag_collision",
        "github issue",
        "recovery",
        "ci / test",
    )

    assert [value for value in required if value not in release] == []
    assert "publication is manual" not in release
    assert "publicación es manual" not in release


def test_sources_document_legal_reconciliation_as_blocking_gate():
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
    )
    assert [value for value in required if value not in sources] == []


def test_data_model_separates_fetch_time_generation_time_and_internal_release_provenance():
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
    )
    assert [value for value in required if value not in model] == []
