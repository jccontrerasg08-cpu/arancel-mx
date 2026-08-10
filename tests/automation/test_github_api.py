import json

import pytest

from scripts.github_api import GitHubApi, GitHubApiError, GitHubNotFound


class FakeResponse:
    def __init__(self, status_code=200, *, json_value=None, content=b"", text=None):
        self.status_code = status_code
        self._json_value = json_value
        self.content = content
        self.text = text if text is not None else (
            json.dumps(json_value) if json_value is not None else content.decode("utf-8", errors="replace")
        )

    def json(self):
        if self._json_value is None:
            raise ValueError("not json")
        return self._json_value


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


def client(session, token="secret-token"):
    return GitHubApi(
        repository="owner/repo",
        token=token,
        session=session,
    )


def test_json_request_sends_required_github_headers_and_timeout():
    session = FakeSession([FakeResponse(json_value={"ok": True})])

    result = client(session).request_json("GET", "/releases")

    assert result == {"ok": True}
    method, url, kwargs = session.calls[0]
    assert method == "GET"
    assert url == "https://api.github.com/repos/owner/repo/releases"
    assert kwargs["timeout"] == 30.0
    assert kwargs["headers"] == {
        "Authorization": "Bearer secret-token",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def test_binary_request_uses_requested_accept_header():
    session = FakeSession([FakeResponse(content=b"asset-bytes")])

    result = client(session).request_bytes(
        "GET",
        "/releases/assets/42",
        accept="application/octet-stream",
    )

    assert result == b"asset-bytes"
    _method, _url, kwargs = session.calls[0]
    assert kwargs["headers"]["Accept"] == "application/octet-stream"


def test_absolute_api_path_is_allowed_only_under_configured_api_root():
    session = FakeSession([FakeResponse(json_value={"id": 1})])

    result = client(session).request_json(
        "GET", "https://api.github.com/repos/owner/repo/releases/1"
    )

    assert result == {"id": 1}


def test_404_maps_to_not_found_without_leaking_token():
    token = "super-secret-token"
    session = FakeSession(
        [FakeResponse(status_code=404, json_value={"message": "Not Found"})]
    )

    with pytest.raises(GitHubNotFound, match="404.*Not Found") as raised:
        client(session, token=token).request_json("GET", "/releases/tags/data-2026.08.10")

    assert token not in str(raised.value)


def test_non_success_error_contains_status_and_sanitized_github_message():
    token = "super-secret-token"
    session = FakeSession(
        [
            FakeResponse(
                status_code=422,
                json_value={
                    "message": "Validation Failed",
                    "documentation_url": "https://docs.github.com/rest",
                },
            )
        ]
    )

    with pytest.raises(GitHubApiError, match="422.*Validation Failed") as raised:
        client(session, token=token).request_json("POST", "/releases", json={})

    assert token not in str(raised.value)
    assert "Authorization" not in str(raised.value)


def test_error_text_is_length_capped_and_does_not_echo_token():
    token = "token-that-must-not-leak"
    session = FakeSession(
        [FakeResponse(status_code=500, text=("x" * 5000) + token)]
    )

    with pytest.raises(GitHubApiError) as raised:
        client(session, token=token).request_bytes("GET", "/broken")

    message = str(raised.value)
    assert token not in message
    assert len(message) < 1200


def test_external_absolute_url_is_rejected_before_request():
    session = FakeSession([])

    with pytest.raises(ValueError, match="outside configured GitHub API"):
        client(session).request_json("GET", "https://example.com/steal")

    assert session.calls == []
