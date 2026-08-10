"""Strict HTTP retrieval for registered official tariff documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import urlparse


_EXTENSION_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html",
    ".htm": "text/html",
}


@dataclass(frozen=True)
class FetchedDocument:
    requested_url: str
    final_url: str
    media_type: str
    content: bytes
    retrieved_at: datetime


def _host_allowed(url: str, allowed_hosts: tuple[str, ...]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return bool(host) and host in {value.lower() for value in allowed_hosts}


def _normalized_media_type(value: object) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _media_type_from_extension(url: str) -> str | None:
    suffix = PurePosixPath(urlparse(url).path).suffix.lower()
    return _EXTENSION_MEDIA_TYPES.get(suffix)


def fetch_official_document(
    session,
    url: str,
    allowed_hosts: tuple[str, ...],
    media_types: tuple[str, ...],
    timeout_s: float = 60.0,
    max_bytes: int = 100 * 1024 * 1024,
) -> FetchedDocument:
    """Fetch one document and enforce the registry's host/type/size boundary."""
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    if not _host_allowed(url, allowed_hosts):
        raise ValueError(f"requested host is not allowed: {url}")

    response = session.get(url, timeout=timeout_s)
    response.raise_for_status()
    final_url = str(response.url)
    if not _host_allowed(final_url, allowed_hosts):
        raise ValueError(f"redirected host is not allowed: {final_url}")

    allowed_media_types = {value.lower() for value in media_types}
    media_type = _normalized_media_type(response.headers.get("Content-Type"))
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

    content = bytes(response.content)
    if len(content) > max_bytes:
        raise ValueError("official document size exceeds limit")

    return FetchedDocument(
        requested_url=url,
        final_url=final_url,
        media_type=media_type,
        content=content,
        retrieved_at=datetime.now(timezone.utc),
    )
