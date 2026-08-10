"""Strict HTTP retrieval for registered official tariff documents."""

from __future__ import annotations

import codecs
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
import re
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
    if not _host_allowed(url, allowed_hosts):
        raise ValueError(f"requested host is not allowed: {url}")

    response = session.get(url, timeout=timeout_s, stream=True)
    try:
        response.raise_for_status()
        final_url = str(response.url)
        if not _host_allowed(final_url, allowed_hosts):
            raise ValueError(f"redirected host is not allowed: {final_url}")

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
        close = getattr(response, "close", None)
        if callable(close):
            close()
