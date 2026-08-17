from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import threading
import time
from typing import Iterator

import pytest
import requests

from arancel_mx.consumer.errors import DatasetDownloadError
from arancel_mx.consumer.http import build_session, stream_download


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        statuses: list[int] | None = None,
        body: bytes = b"ok",
        delay: float = 0.0,
        truncate: bool = False,
    ) -> None:
        super().__init__(server_address, _Handler)
        self.statuses = list(statuses or [200])
        self.body = body
        self.delay = delay
        self.truncate = truncate
        self.request_count = 0


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def do_GET(self) -> None:  # noqa: N802
        self.server.request_count += 1
        index = min(self.server.request_count - 1, len(self.server.statuses) - 1)
        status = self.server.statuses[index]
        if self.server.delay:
            time.sleep(self.server.delay)
        self.send_response(status)
        if status >= 400:
            body = f"status={status}".encode("ascii")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = self.server.body
        advertised = len(body) + 1024 if self.server.truncate else len(body)
        self.send_header("Content-Length", str(advertised))
        self.end_headers()
        if self.server.truncate:
            partial = body[: max(1, len(body) // 2)]
            self.wfile.write(partial)
            self.wfile.flush()
            self.close_connection = True
            return
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def _http_server(
    *,
    statuses: list[int] | None = None,
    body: bytes = b"ok",
    delay: float = 0.0,
    truncate: bool = False,
) -> Iterator[tuple[_Server, str]]:
    server = _Server(
        ("127.0.0.1", 0),
        statuses=statuses,
        body=body,
        delay=delay,
        truncate=truncate,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield server, f"http://{host}:{port}/asset"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_stream_download_writes_body_incrementally(tmp_path: Path) -> None:
    body = (b"0123456789abcdef" * 131072) + b"tail"
    destination = tmp_path / "asset.part"
    with _http_server(body=body) as (_, url):
        written = stream_download(build_session(), url, destination, timeout=2.0)

    assert written == len(body)
    assert destination.read_bytes() == body


def test_stream_download_returns_byte_count(tmp_path: Path) -> None:
    body = b"abc123" * 1000
    destination = tmp_path / "asset.part"
    with _http_server(body=body) as (_, url):
        written = stream_download(build_session(), url, destination, timeout=2.0)

    assert written == destination.stat().st_size == len(body)


def test_stream_download_maps_404_to_dataset_download_error(tmp_path: Path) -> None:
    destination = tmp_path / "asset.part"
    with _http_server(statuses=[404]) as (_, url):
        with pytest.raises(DatasetDownloadError) as raised:
            stream_download(build_session(), url, destination, timeout=2.0)

    assert isinstance(raised.value.__cause__, requests.HTTPError)


def test_stream_download_maps_dns_connection_failure(tmp_path: Path) -> None:
    class FailingSession:
        def get(self, *args: object, **kwargs: object) -> object:
            raise requests.ConnectionError("DNS resolution failed")

    with pytest.raises(DatasetDownloadError) as raised:
        stream_download(  # type: ignore[arg-type]
            FailingSession(),
            "https://does-not-resolve.invalid/asset",
            tmp_path / "asset.part",
            timeout=1.0,
        )

    assert isinstance(raised.value.__cause__, requests.ConnectionError)


def test_stream_download_maps_timeout(tmp_path: Path) -> None:
    destination = tmp_path / "asset.part"
    with _http_server(body=b"late", delay=0.25) as (_, url):
        with pytest.raises(DatasetDownloadError) as raised:
            stream_download(build_session(), url, destination, timeout=0.05)

    assert isinstance(raised.value.__cause__, requests.RequestException)


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retry_policy_retries_retryable_statuses(tmp_path: Path, status: int) -> None:
    destination = tmp_path / f"asset-{status}.part"
    with _http_server(statuses=[status, status, 200], body=b"recovered") as (server, url):
        written = stream_download(build_session(), url, destination, timeout=2.0)

    assert written == len(b"recovered")
    assert destination.read_bytes() == b"recovered"
    assert server.request_count == 3


def test_retry_policy_does_not_retry_404(tmp_path: Path) -> None:
    destination = tmp_path / "asset.part"
    with _http_server(statuses=[404, 200]) as (server, url):
        with pytest.raises(DatasetDownloadError):
            stream_download(build_session(), url, destination, timeout=2.0)

    assert server.request_count == 1


def test_build_session_retry_contract_is_exact() -> None:
    session = build_session()
    adapter = session.get_adapter("https://github.com/")
    retry = adapter.max_retries

    assert retry.total == 2
    assert retry.backoff_factor == 0.25
    assert retry.status_forcelist == {429, 500, 502, 503, 504}
    assert retry.allowed_methods == frozenset({"GET"})


def test_build_session_adds_github_authorization_only_when_requested() -> None:
    anonymous = build_session()
    authenticated = build_session(github_token="test-token")  # noqa: S106

    assert "Authorization" not in anonymous.headers
    assert authenticated.headers["Authorization"] == "Bearer test-token"
    assert authenticated.headers["Accept"] == "application/vnd.github+json"


def test_interrupted_response_leaves_only_temporary_file_for_caller_cleanup(
    tmp_path: Path,
) -> None:
    body = b"x" * (2 * 1024 * 1024)
    destination = tmp_path / "asset.part"
    final_destination = tmp_path / "asset.bin"
    with _http_server(body=body, truncate=True) as (_, url):
        with pytest.raises(DatasetDownloadError):
            stream_download(build_session(), url, destination, timeout=2.0)

    assert destination.exists()
    assert 0 < destination.stat().st_size < len(body)
    assert not final_destination.exists()


def test_timeout_must_be_positive(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="timeout must be greater than zero"):
        stream_download(
            build_session(),
            "http://127.0.0.1/asset",
            tmp_path / "asset.part",
            timeout=0,
        )
