import json

from scripts import publish_release as publisher


def test_main_writes_failure_result_before_returning_nonzero(tmp_path, monkeypatch):
    result_path = tmp_path / "publisher-result.json"
    token = "publisher-token-that-must-not-leak"
    monkeypatch.setenv("GITHUB_TOKEN", token)
    monkeypatch.setattr(publisher, "GitHubApi", lambda *_args, **_kwargs: object())

    def fail(*_args, **_kwargs):
        raise publisher.PublicationError(
            "release_tag_collision",
            f"collision while using {token} " + ("x" * 5000),
        )

    monkeypatch.setattr(publisher, "publish_release", fail)

    exit_code = publisher.main(
        [
            "--release-dir",
            str(tmp_path / "release"),
            "--commit-sha",
            "abc123",
            "--repository",
            "owner/repo",
            "--token",
            token,
            "--result-path",
            str(result_path),
        ]
    )

    assert exit_code == 2
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert result["stage"] == "publish"
    assert result["failure_category"] == "release_tag_collision"
    assert token not in result["message"]
    assert "[REDACTED]" in result["message"]
    assert len(result["message"]) <= publisher.MAX_DIAGNOSTIC_LENGTH


def test_main_writes_success_result_before_returning_zero(tmp_path, monkeypatch):
    result_path = tmp_path / "publisher-result.json"
    expected = {
        "status": "published",
        "dataset_version": "2026.08.10",
        "tag": "data-2026.08.10",
        "release_id": 10,
    }
    monkeypatch.setattr(publisher, "GitHubApi", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(publisher, "publish_release", lambda *_args, **_kwargs: expected)

    exit_code = publisher.main(
        [
            "--release-dir",
            str(tmp_path / "release"),
            "--commit-sha",
            "abc123",
            "--repository",
            "owner/repo",
            "--token",
            "token",
            "--result-path",
            str(result_path),
        ]
    )

    assert exit_code == 0
    assert json.loads(result_path.read_text(encoding="utf-8")) == expected
