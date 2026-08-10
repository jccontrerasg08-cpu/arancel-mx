from arancel_mx.release.metadata import ReleaseProvenance


def test_local_release_provenance_is_explicit():
    value = ReleaseProvenance.local().to_dict()

    assert value == {
        "git_commit_sha": "local",
        "github_run_id": "local",
        "github_run_attempt": "local",
        "github_workflow_ref": "local",
        "github_artifact_name": "local",
    }
