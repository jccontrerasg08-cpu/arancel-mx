"""Bounded, streamed HTTP downloads for the public consumer path."""

from __future__ import annotations

from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from arancel_mx.consumer.errors import DatasetDownloadError


_CHUNK_SIZE = 1024 * 1024
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def build_session() -> requests.Session:
    """Build a requests session with the exact bounded GET retry contract."""

    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        other=0,
        backoff_factor=0.25,
        status_forcelist=_RETRYABLE_STATUSES,
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def stream_download(
    session: requests.Session,
    url: str,
    destination: Path,
    *,
    timeout: float,
) -> int:
    """Stream one URL into a caller-owned temporary path and return bytes written.

    The function deliberately never promotes or renames ``destination``.  Atomic
    publication belongs to the cache transaction layer, which means an interrupted
    transfer can leave only the temporary path for deterministic cleanup.
    """

    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    try:
        with session.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with destination.open("wb") as output:
                for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                    if not chunk:
                        continue
                    output.write(chunk)
                    written += len(chunk)
        return written
    except (requests.RequestException, OSError) as exc:
        raise DatasetDownloadError(f"failed to download dataset asset: {url}") from exc
