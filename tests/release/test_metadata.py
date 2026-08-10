import pytest

from arancel_mx.release.metadata import (
    ReleaseProvenance,
    SourceIdentity,
    source_identity_changed,
    source_identity_digest,
    source_identity_from_manifest,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def identity(
    dataset_key="ligie",
    document_role="ligie_snapshot",
    source_url="https://www.snice.gob.mx/files/ligie.xlsx",
    sha256=SHA_A,
    registry_version="1",
):
    return SourceIdentity(
        dataset_key=dataset_key,
        document_role=document_role,
        source_url=source_url,
        sha256=sha256,
        registry_version=registry_version,
    )


def test_local_release_provenance_is_explicit():
    value = ReleaseProvenance.local().to_dict()

    assert value == {
        "git_commit_sha": "local",
        "github_run_id": "local",
        "github_run_attempt": "local",
        "github_workflow_ref": "local",
        "github_artifact_name": "local",
    }


def test_release_provenance_rejects_blank_values():
    with pytest.raises(ValueError, match="git_commit_sha"):
        ReleaseProvenance(" ", "1", "1", "workflow", "artifact")


def test_source_identity_rejects_blank_values_and_invalid_hash():
    with pytest.raises(ValueError, match="dataset_key"):
        identity(dataset_key="")
    with pytest.raises(ValueError, match="sha256"):
        identity(sha256="not-a-sha256")


def test_source_identity_digest_is_order_independent():
    first = identity()
    second = identity(
        dataset_key="nico",
        document_role="nico_snapshot",
        source_url="https://www.snice.gob.mx/files/nico.xlsx",
        sha256=SHA_B,
    )

    assert source_identity_digest([first, second]) == source_identity_digest(
        [second, first]
    )


def test_source_identity_change_detection_ignores_order():
    first = identity()
    second = identity(
        dataset_key="nico",
        document_role="nico_snapshot",
        source_url="https://www.snice.gob.mx/files/nico.xlsx",
        sha256=SHA_B,
    )

    assert source_identity_changed([first, second], [second, first]) is False


def test_source_identity_change_detection_uses_all_identity_fields():
    base = identity()
    variants = (
        identity(source_url="https://www.snice.gob.mx/files/other.xlsx"),
        identity(sha256=SHA_B),
        identity(document_role="other_role"),
        identity(registry_version="2"),
    )

    assert all(source_identity_changed([base], [variant]) for variant in variants)


def test_source_identity_manifest_parsing_is_strict():
    with pytest.raises(ValueError, match="source_identity"):
        source_identity_from_manifest({"dataset_version": "2026.08.10"})

    manifest = {"source_identity": [identity().to_dict()]}
    assert source_identity_from_manifest(manifest) == (identity(),)
