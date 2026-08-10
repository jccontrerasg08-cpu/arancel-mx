from datetime import date, datetime, timezone
import json

from arancel_mx.pipeline.official_dataset import OfficialDatasetConfig
from scripts.run_official_pipeline import execute_pipeline


def config(tmp_path):
    return OfficialDatasetConfig(
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "release",
        effective_as_of=date(2026, 8, 10),
        dataset_version="2026.08.10",
        generated_at=datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
        git_commit_sha="abc123",
        github_run_id="123",
        github_run_attempt="1",
        github_workflow_ref="owner/repo/.github/workflows/official-data-pipeline.yml@refs/heads/main",
        github_artifact_name="arancel-mx-123-1",
    )


def result_file(tmp_path):
    return tmp_path / "out" / "pipeline-result.json"


def test_no_change_writes_success_result_without_release_directory(tmp_path):
    build_config = config(tmp_path)

    def builder(config, session=None, previous_manifest=None):
        return {
            "status": "no_change",
            "dataset_version": config.dataset_version,
            "schema_version": "2",
            "row_count": 10,
            "validation_status": "passed",
            "source_count": 5,
            "output_dir": None,
        }

    exit_code, result = execute_pipeline(
        build_config,
        previous_manifest={"source_identity": []},
        result_path=result_file(tmp_path),
        builder=builder,
    )

    assert exit_code == 0
    assert result == {
        "status": "no_change",
        "stage": "complete",
        "dataset_version": "2026.08.10",
        "artifact_name": "arancel-mx-123-1",
        "message": "registered source identity is unchanged",
    }
    assert json.loads(result_file(tmp_path).read_text(encoding="utf-8")) == result
    assert not build_config.output_dir.exists()


def test_built_writes_release_result(tmp_path):
    build_config = config(tmp_path)

    def builder(config, session=None, previous_manifest=None):
        config.output_dir.mkdir(parents=True)
        return {
            "status": "built",
            "dataset_version": config.dataset_version,
            "schema_version": "2",
            "row_count": 10,
            "validation_status": "passed",
            "source_count": 5,
            "output_dir": str(config.output_dir),
        }

    exit_code, result = execute_pipeline(
        build_config,
        previous_manifest=None,
        result_path=result_file(tmp_path),
        builder=builder,
    )

    assert exit_code == 0
    assert result["status"] == "built"
    assert result["stage"] == "complete"
    assert result["release_dir"] == str(build_config.output_dir)
    assert result["artifact_name"] == "arancel-mx-123-1"
    assert build_config.output_dir.is_dir()


def test_legal_reconciliation_failure_is_structured_and_exits_two(tmp_path):
    def builder(*_args, **_kwargs):
        raise ValueError(
            "legal reconciliation failed: missing_dof_evidence:law_reform:2025-12-29"
        )

    exit_code, result = execute_pipeline(
        config(tmp_path),
        previous_manifest=None,
        result_path=result_file(tmp_path),
        builder=builder,
    )

    assert exit_code == 2
    assert result["status"] == "failed"
    assert result["stage"] == "build"
    assert result["failure_category"] == "legal_reconciliation"
    assert "missing_dof_evidence" in result["message"]
    assert json.loads(result_file(tmp_path).read_text(encoding="utf-8")) == result


def test_checksum_failure_gets_specific_category(tmp_path):
    def builder(*_args, **_kwargs):
        raise ValueError("source checksum mismatch: ligie.xlsx")

    exit_code, result = execute_pipeline(
        config(tmp_path),
        previous_manifest=None,
        result_path=result_file(tmp_path),
        builder=builder,
    )

    assert exit_code == 2
    assert result["failure_category"] == "checksum"


def test_unexpected_error_is_sanitized_and_never_contains_environment_secrets(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GITHUB_TOKEN", "token-value-that-must-not-leak")
    monkeypatch.setenv("OTHER_SECRET", "other-secret-value")

    def builder(*_args, **_kwargs):
        raise RuntimeError(
            "boom token-value-that-must-not-leak other-secret-value"
        )

    exit_code, result = execute_pipeline(
        config(tmp_path),
        previous_manifest=None,
        result_path=result_file(tmp_path),
        builder=builder,
    )

    assert exit_code == 2
    assert result["failure_category"] == "unexpected_error"
    assert "token-value-that-must-not-leak" not in result["message"]
    assert "other-secret-value" not in result["message"]
    assert "[REDACTED]" in result["message"]
