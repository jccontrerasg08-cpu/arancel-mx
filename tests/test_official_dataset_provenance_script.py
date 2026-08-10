import scripts.build_official_dataset as build_script


def test_script_accepts_explicit_github_release_provenance(tmp_path, monkeypatch):
    calls = []

    def fake_build(config):
        calls.append(config)
        return {"status": "built", "validation_status": "passed", "row_count": 5}

    monkeypatch.setattr(build_script, "build_official_dataset", fake_build)

    result = build_script.main(
        [
            "--work-dir",
            str(tmp_path / "work"),
            "--output-dir",
            str(tmp_path / "release"),
            "--effective-as-of",
            "2026-08-10",
            "--dataset-version",
            "2026.08.10",
            "--git-commit-sha",
            "abc123",
            "--github-run-id",
            "12345",
            "--github-run-attempt",
            "2",
            "--github-workflow-ref",
            "jccontrerasg08-cpu/arancel-mx/.github/workflows/build-official-dataset.yml@refs/heads/main",
            "--github-artifact-name",
            "official-dataset-2026.08.10",
        ]
    )

    assert result == 0
    config = calls[0]
    assert config.git_commit_sha == "abc123"
    assert config.github_run_id == "12345"
    assert config.github_run_attempt == "2"
    assert config.github_workflow_ref.endswith("@refs/heads/main")
    assert config.github_artifact_name == "official-dataset-2026.08.10"


def test_script_defaults_provenance_to_local(tmp_path, monkeypatch):
    calls = []

    def fake_build(config):
        calls.append(config)
        return {"status": "built", "validation_status": "passed", "row_count": 5}

    monkeypatch.setattr(build_script, "build_official_dataset", fake_build)

    result = build_script.main(
        [
            "--work-dir",
            str(tmp_path / "work"),
            "--output-dir",
            str(tmp_path / "release"),
            "--effective-as-of",
            "2026-08-10",
            "--dataset-version",
            "2026.08.10",
        ]
    )

    assert result == 0
    provenance = calls[0].provenance().to_dict()
    assert set(provenance.values()) == {"local"}
