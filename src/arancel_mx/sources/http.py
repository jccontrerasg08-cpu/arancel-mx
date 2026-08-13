"""Strict HTTP retrieval for registered official tariff documents."""

from __future__ import annotations

import codecs
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
import re
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.util.ssl_ import create_urllib3_context

MAX_REDIRECTS = 5
OFFICIAL_HTTPS_CIPHERS = "DEFAULT:@SECLEVEL=1"
# changedetection.io content_fetchers/requests.py default REQUESTS_RETRY_MAX_COUNT
OFFICIAL_TRANSPORT_RETRIES = 6
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


_EXTENSION_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html",
    ".htm": "text/html",
}

_CHARSET_PARAMETER = re.compile(
    r"(?:^|;)\s*charset\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^;\s]+))",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FetchedDocument:
    requested_url: str
    final_url: str
    media_type: str
    content: bytes
    retrieved_at: datetime
    charset: str | None = None


def _host_allowed(url: str, allowed_hosts: tuple[str, ...]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return bool(host) and host in {value.lower() for value in allowed_hosts}


def _require_https(url: str) -> None:
    if urlparse(url).scheme.lower() != "https":
        raise ValueError(f"official document URL must use https: {url}")


def _require_allowed_https_url(
    url: str,
    allowed_hosts: tuple[str, ...],
    *,
    redirected: bool,
) -> None:
    _require_https(url)
    if not _host_allowed(url, allowed_hosts):
        kind = "redirected host" if redirected else "requested host"
        raise ValueError(f"{kind} is not allowed: {url}")


def _close_response(response: object) -> None:
    close = getattr(response, "close", None)
    if callable(close):
        close()


def _is_redirect(response: object) -> bool:
    if getattr(response, "is_redirect", False):
        return True
    status = getattr(response, "status_code", None)
    try:
        return int(status) in _REDIRECT_STATUSES
    except (TypeError, ValueError):
        return False


def _redirect_location(response: object, current_url: str) -> str:
    headers = getattr(response, "headers", None) or {}
    location = headers.get("Location")
    if location is None:
        location = headers.get("location")
    if not location or not str(location).strip():
        raise ValueError(f"official document redirect is missing Location: {current_url}")
    return urljoin(current_url, str(location).strip())


def _normalized_media_type(value: object) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _declared_charset(value: object) -> str | None:
    match = _CHARSET_PARAMETER.search(str(value or ""))
    if match is None:
        return None
    charset = next((part for part in match.groups() if part), "").strip().lower()
    return charset or None


def _media_type_from_extension(url: str) -> str | None:
    suffix = PurePosixPath(urlparse(url).path).suffix.lower()
    return _EXTENSION_MEDIA_TYPES.get(suffix)


class _OfficialHttpsAdapter(HTTPAdapter):
    """HTTPS to legacy gob.mx hosts with weak DH parameters."""

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers(OFFICIAL_HTTPS_CIPHERS)
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def _transport_retry() -> Retry:
    """Retry connect/read failures only. HTTP status codes are not retried.

    Algorithm from changedetection.io ``content_fetchers/requests.py``:
    ``status=0``, ``backoff_factor=0.5``, connect/read equal to total.
    """

    return Retry(
        total=OFFICIAL_TRANSPORT_RETRIES,
        connect=OFFICIAL_TRANSPORT_RETRIES,
        read=OFFICIAL_TRANSPORT_RETRIES,
        status=0,
        backoff_factor=0.5,
        allowed_methods=frozenset({"HEAD", "GET", "OPTIONS", "POST"}),
        raise_on_status=False,
    )


def build_official_session() -> requests.Session:
    """Session for Diputados/SNICE/DOF capture and CI URL probes."""

    retry = _transport_retry()
    session = requests.Session()
    session.mount("https://", _OfficialHttpsAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def decode_fetched_text(document: FetchedDocument) -> str:
    """Decode registered text content without silently replacing invalid bytes."""
    if not document.media_type.startswith("text/"):
        raise ValueError(f"official document is not text: {document.media_type}")

    if document.charset:
        try:
            codecs.lookup(document.charset)
        except LookupError as exc:
            raise ValueError(
                f"official document declares unsupported charset: {document.charset}"
            ) from exc
        try:
            return document.content.decode(document.charset, errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"official document does not match declared charset: {document.charset}"
            ) from exc

    try:
        return document.content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        try:
            return document.content.decode("cp1252", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("official text document encoding is unsupported") from exc


def _read_bounded_content(response, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    received = 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        if not chunk:
            continue
        piece = bytes(chunk)
        received += len(piece)
        if received > max_bytes:
            raise ValueError("official document size exceeds limit")
        chunks.append(piece)
    return b"".join(chunks)


def fetch_official_document(
    session,
    url: str,
    allowed_hosts: tuple[str, ...],
    media_types: tuple[str, ...],
    timeout_s: float = 60.0,
    max_bytes: int = 100 * 1024 * 1024,
) -> FetchedDocument:
    """Fetch one document and enforce the registry's host/type/size boundary."""
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    _require_allowed_https_url(url, allowed_hosts, redirected=False)

    current_url = url
    response = None
    redirects = 0
    try:
        while True:
            response = session.get(
                current_url,
                timeout=timeout_s,
                stream=True,
                allow_redirects=False,
            )
            if not _is_redirect(response):
                break
            if redirects >= MAX_REDIRECTS:
                raise ValueError("official document redirect limit exceeded")
            next_url = _redirect_location(response, current_url)
            _close_response(response)
            response = None
            redirects += 1
            _require_allowed_https_url(next_url, allowed_hosts, redirected=True)
            current_url = next_url

        if response is None:
            raise ValueError("official document request returned no response")
        response.raise_for_status()
        final_url = str(getattr(response, "url", "") or current_url)
        _require_allowed_https_url(
            final_url,
            allowed_hosts,
            redirected=final_url != url,
        )

        content_type = response.headers.get("Content-Type")
        allowed_media_types = {value.lower() for value in media_types}
        media_type = _normalized_media_type(content_type)
        if media_type == "application/octet-stream":
            inferred = _media_type_from_extension(final_url)
            if inferred is None or inferred.lower() not in allowed_media_types:
                raise ValueError(f"official document media type is not allowed: {media_type}")
            media_type = inferred.lower()
        elif media_type not in allowed_media_types:
            raise ValueError(f"official document media type is not allowed: {media_type}")

        declared_size = response.headers.get("Content-Length")
        if declared_size not in (None, ""):
            try:
                declared_bytes = int(declared_size)
            except (TypeError, ValueError) as exc:
                raise ValueError("official document size header is invalid") from exc
            if declared_bytes < 0 or declared_bytes > max_bytes:
                raise ValueError("official document size exceeds limit")

        content = _read_bounded_content(response, max_bytes)
        return FetchedDocument(
            requested_url=url,
            final_url=final_url,
            media_type=media_type,
            content=content,
            retrieved_at=datetime.now(timezone.utc),
            charset=_declared_charset(content_type),
        )
    finally:
        _close_response(response)
