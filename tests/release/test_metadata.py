import pytest

from arancel_mx.release.metadata import (
    ReleaseProvenance,
    SourceIdentity,
    source_identity_changed,
    source_identity_changes,
    source_identity_digest,
    source_identity_history,
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


def test_source_identity_changes_are_keyed_and_auditable():
    previous = (
        identity(),
        identity(
            dataset_key="nico",
            document_role="nico_snapshot",
            source_url="https://www.snice.gob.mx/files/nico.xlsx",
            sha256=SHA_B,
        ),
    )
    current = (
        identity(source_url="https://www.snice.gob.mx/files/ligie-2026.xlsx"),
        identity(
            dataset_key="national_notes",
            document_role="national_notes",
            source_url="https://www.dof.gob.mx/notes.html",
            sha256=SHA_B,
        ),
    )

    assert source_identity_changes(current, previous) == [
        {
            "change": "updated",
            "dataset_key": "ligie",
            "document_role": "ligie_snapshot",
            "previous": previous[0].to_dict(),
            "current": current[0].to_dict(),
        },
        {
            "change": "added",
            "dataset_key": "national_notes",
            "document_role": "national_notes",
            "previous": None,
            "current": current[1].to_dict(),
        },
        {
            "change": "removed",
            "dataset_key": "nico",
            "document_role": "nico_snapshot",
            "previous": previous[1].to_dict(),
            "current": None,
        },
    ]


def test_source_identity_history_references_the_prior_release():
    previous = identity(sha256=SHA_B)
    current = identity()

    assert source_identity_history(
        [current],
        {
            "dataset_version": "2026.08.10",
            "source_identity": [previous.to_dict()],
        },
    ) == {
        "previous_dataset_version": "2026.08.10",
        "changes": [
            {
                "change": "updated",
                "dataset_key": "ligie",
                "document_role": "ligie_snapshot",
                "previous": previous.to_dict(),
                "current": current.to_dict(),
            }
        ],
    }


def test_source_identity_manifest_parsing_is_strict():
    with pytest.raises(ValueError, match="source_identity"):
        source_identity_from_manifest({"dataset_version": "2026.08.10"})

    manifest = {"source_identity": [identity().to_dict()]}
    assert source_identity_from_manifest(manifest) == (identity(),)
