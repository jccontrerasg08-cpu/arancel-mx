"""Minimal GitHub REST client used only by trusted automation scripts."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests


DEFAULT_API_VERSION = "2022-11-28"
DEFAULT_TIMEOUT_S = 30.0
MAX_ERROR_MESSAGE = 900


class GitHubApiError(RuntimeError):
    """A sanitized non-success response from the GitHub REST API."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"GitHub API {status_code}: {message}")
        self.status_code = status_code


class GitHubNotFound(GitHubApiError):
    """A sanitized GitHub REST 404 response."""


def _nonblank(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-blank string")
    return value.strip()


class GitHubApi:
    def __init__(
        self,
        repository: str,
        token: str,
        api_url: str = "https://api.github.com",
        session: Any | None = None,
    ):
        repository = _nonblank(repository, "repository")
        if repository.count("/") != 1:
            raise ValueError("repository must use owner/name")
        self.repository = repository
        self.token = _nonblank(token, "token")
        self.api_url = _nonblank(api_url, "api_url").rstrip("/")
        parsed = urlparse(self.api_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("api_url must be an absolute HTTPS URL")
        self.session = session or requests.Session()

    def _url(self, path: str) -> str:
        path = _nonblank(path, "path")
        if path.startswith("http://") or path.startswith("https://"):
            parsed_path = urlparse(path)
            parsed_root = urlparse(self.api_url)
            if (
                parsed_path.scheme != parsed_root.scheme
                or parsed_path.netloc != parsed_root.netloc
                or not parsed_path.path.startswith(f"/repos/{self.repository}/")
            ):
                raise ValueError("absolute URL is outside configured GitHub API")
            return path
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.api_url}/repos/{self.repository}{path}"

    def _upload_url(self, value: str) -> str:
        value = _nonblank(value, "upload_url")
        parsed = urlparse(value)
        root = urlparse(self.api_url)
        if root.netloc == "api.github.com":
            allowed_host = "uploads.github.com"
        else:
            allowed_host = root.netloc
        expected_prefix = f"/repos/{self.repository}/releases/"
        if (
            parsed.scheme != "https"
            or parsed.netloc != allowed_host
            or not parsed.path.startswith(expected_prefix)
            or not parsed.path.endswith("/assets")
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ValueError("upload URL is outside configured GitHub upload API")
        return value

    def _headers(self, accept: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": accept,
            "X-GitHub-Api-Version": DEFAULT_API_VERSION,
        }

    def _error_message(self, response: Any) -> str:
        message = "request failed"
        try:
            payload = response.json()
        except (ValueError, TypeError):
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("message"), str):
            message = payload["message"]
        elif isinstance(getattr(response, "text", None), str) and response.text.strip():
            message = response.text.strip()
        message = message.replace(self.token, "[REDACTED]")
        message = " ".join(message.split())
        if len(message) > MAX_ERROR_MESSAGE:
            message = message[: MAX_ERROR_MESSAGE - 3] + "..."
        return message

    def _raise_for_status(self, response: Any) -> None:
        status = int(response.status_code)
        if 200 <= status < 300:
            return
        error_type = GitHubNotFound if status == 404 else GitHubApiError
        raise error_type(status, self._error_message(response))

    def _request(
        self,
        method: str,
        path: str,
        *,
        accept: str,
        timeout: float = DEFAULT_TIMEOUT_S,
        **kwargs: Any,
    ) -> Any:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        supplied_headers = kwargs.pop("headers", None)
        if supplied_headers:
            raise ValueError("custom headers are not accepted; use the accept argument")
        response = self.session.request(
            method.upper(),
            self._url(path),
            headers=self._headers(accept),
            timeout=timeout,
            **kwargs,
        )
        self._raise_for_status(response)
        return response

    def request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        accept = kwargs.pop("accept", "application/vnd.github+json")
        response = self._request(method, path, accept=accept, **kwargs)
        try:
            return response.json()
        except (ValueError, TypeError) as exc:
            raise GitHubApiError(
                int(response.status_code),
                "successful response did not contain valid JSON",
            ) from exc

    def request_bytes(self, method: str, path: str, **kwargs: Any) -> bytes:
        accept = kwargs.pop("accept", "application/octet-stream")
        response = self._request(method, path, accept=accept, **kwargs)
        return bytes(response.content)

    def request_upload_json(
        self,
        upload_url: str,
        data: bytes,
        *,
        timeout: float = DEFAULT_TIMEOUT_S,
    ) -> Any:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("release asset upload data must be bytes-like")
        headers = self._headers("application/vnd.github+json")
        headers["Content-Type"] = "application/octet-stream"
        response = self.session.request(
            "POST",
            self._upload_url(upload_url),
            headers=headers,
            timeout=timeout,
            data=bytes(data),
        )
        self._raise_for_status(response)
        try:
            return response.json()
        except (ValueError, TypeError) as exc:
            raise GitHubApiError(
                int(response.status_code),
                "successful upload response did not contain valid JSON",
            ) from exc
