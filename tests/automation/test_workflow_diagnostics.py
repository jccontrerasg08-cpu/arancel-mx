from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import workflow_diagnostics as diagnostics


def _outputs(path: Path) -> dict[str, str]:
    rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    return dict(row.split("=", 1) for row in rows)


def test_missing_result_file_is_a_preflight_failure(tmp_path: Path):
    summary = diagnostics.summarize_pipeline(
        diagnostics.load_result(tmp_path / "absent.json"),
        dataset_version="2026.08.12",
        artifact_name="arancel-mx-7-1",
    )

    assert summary["status"] == "failed"
    assert summary["stage"] == "preflight"
    assert summary["failure_category"] == "preflight_failure"
    assert summary["dataset_version"] == "2026.08.12"
    assert summary["artifact_name"] == "arancel-mx-7-1"


@pytest.mark.parametrize("payload", ["not json", "[]", '"built"', "null"])
def test_unusable_result_content_is_treated_as_absent(tmp_path: Path, payload: str):
    path = tmp_path / "pipeline-result.json"
    path.write_text(payload, encoding="utf-8")

    assert diagnostics.load_result(path) == {}


def test_built_result_is_forwarded_without_a_failure_category(tmp_path: Path):
    path = tmp_path / "pipeline-result.json"
    path.write_text(
        json.dumps(
            {
                "status": "built",
                "stage": "complete",
                "dataset_version": "2026.08.12",
                "artifact_name": "arancel-mx-7-1",
            }
        ),
        encoding="utf-8",
    )

    summary = diagnostics.summarize_pipeline(
        diagnostics.load_result(path),
        dataset_version="fallback",
        artifact_name="fallback",
    )

    assert summary["status"] == "built"
    assert summary["failure_category"] == ""
    assert summary["dataset_version"] == "2026.08.12"
    assert summary["artifact_name"] == "arancel-mx-7-1"


def test_unsupported_status_can_never_be_reported_as_publishable():
    for status in ("BUILT", "built\nstatus=built", "published", "", "ok", None):
        summary = diagnostics.summarize_pipeline(
            {"status": status, "stage": "complete"},
            dataset_version="2026.08.12",
            artifact_name="arancel-mx-7-1",
        )

        assert summary["status"] == "failed"
        assert summary["failure_category"] == diagnostics.INVALID_DIAGNOSTICS


def test_injected_newlines_can_never_define_extra_workflow_outputs():
    summary = diagnostics.summarize_pipeline(
        {
            "status": "failed",
            "stage": "build\nstatus=built",
            "dataset_version": "2026.08.12\nartifact_name=attacker",
            "failure_category": "parser\nstatus=built",
            "message": "boom\nstatus=built",
        },
        dataset_version="2026.08.12",
        artifact_name="arancel-mx-7-1",
    )
    rendered = diagnostics.render_github_output(summary)

    assert summary["status"] == "failed"
    assert summary["stage"] == diagnostics.UNKNOWN
    assert summary["dataset_version"] == "2026.08.12"
    assert summary["failure_category"] == "unknown_error"
    assert summary["message"] == "boom status=built"
    assert len(rendered.splitlines()) == len(summary)
    assert "\nstatus=built" not in rendered


def test_rendering_refuses_every_line_when_one_value_is_unsafe():
    with pytest.raises(ValueError, match="single line"):
        diagnostics.render_github_output({"status": "failed", "message": "a\nb"})

    with pytest.raises(ValueError, match="unsupported workflow output key"):
        diagnostics.render_github_output({"Status": "failed"})


def test_long_messages_are_bounded_for_the_workflow_summary():
    summary = diagnostics.summarize_pipeline(
        {"status": "failed", "stage": "build", "message": "x" * 5000},
        dataset_version="2026.08.12",
        artifact_name="arancel-mx-7-1",
    )

    assert len(summary["message"]) == diagnostics.MAX_MESSAGE_LENGTH
    assert summary["message"].endswith("...")


def test_published_result_reports_a_complete_stage_without_a_category():
    summary = diagnostics.summarize_publisher(
        {"status": "published", "dataset_version": "2026.08.12", "tag": "data-2026.08.12"}
    )

    assert summary == {
        "status": "published",
        "stage": "complete",
        "failure_category": "",
        "message": "",
    }


def test_missing_publisher_result_is_a_publisher_failure():
    summary = diagnostics.summarize_publisher({})

    assert summary["status"] == "failed"
    assert summary["stage"] == "publish"
    assert summary["failure_category"] == "publisher_failure"
    assert summary["message"] == diagnostics.PUBLISHER_FALLBACK_MESSAGE


def test_pipeline_outputs_command_appends_validated_lines(tmp_path: Path):
    result = tmp_path / "pipeline-result.json"
    result.write_text(
        json.dumps({"status": "no_change", "stage": "complete", "message": "unchanged"}),
        encoding="utf-8",
    )
    output = tmp_path / "github-output"
    output.write_text("existing=value\n", encoding="utf-8")

    exit_code = diagnostics.main(
        [
            "pipeline-outputs",
            "--result",
            str(result),
            "--dataset-version",
            "2026.08.12",
            "--artifact-name",
            "arancel-mx-7-1",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    values = _outputs(output)
    assert values["existing"] == "value"
    assert values["status"] == "no_change"
    assert values["dataset_version"] == "2026.08.12"
    assert values["message"] == "unchanged"


def test_publisher_outputs_command_requires_a_destination(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    result = tmp_path / "publisher-result.json"
    result.write_text(json.dumps({"status": "published"}), encoding="utf-8")

    with pytest.raises(ValueError, match="GITHUB_OUTPUT is not set"):
        diagnostics.main(["publisher-outputs", "--result", str(result)])


def test_write_failure_command_emits_a_bounded_result_file(tmp_path: Path):
    path = tmp_path / "nested" / "alert-result.json"

    exit_code = diagnostics.main(
        [
            "write-failure",
            "--path",
            str(path),
            "--stage",
            "previous_release",
            "--failure-category",
            "previous_release_lookup",
            "--dataset-version",
            "",
            "--message",
            "  lookup   failed  \n  again ",
        ]
    )

    assert exit_code == 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "status": "failed",
        "stage": "previous_release",
        "dataset_version": diagnostics.UNKNOWN,
        "failure_category": "previous_release_lookup",
        "message": "lookup failed again",
    }
