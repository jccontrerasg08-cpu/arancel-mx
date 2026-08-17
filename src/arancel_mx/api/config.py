"""Environment-backed settings for the public HTTP API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import re

from arancel_mx.consumer.config import _parse_offline


_DATASET_TAG = re.compile(r"^data-\d{4}\.\d{2}\.\d{2}$")
_DEFAULT_TIMEOUT = 30.0
_MAX_TIMEOUT = 120.0


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Validated startup configuration for one immutable dataset release."""

    dataset_tag: str
    cache_dir: Path | None
    timeout: float
    offline: bool
    github_token: str | None = None


def load_settings(environ: Mapping[str, str] | None = None) -> ApiSettings:
    """Load API settings without allowing an implicit latest dataset."""

    source = os.environ if environ is None else environ
    dataset_tag = source.get("ARANCEL_MX_API_DATASET", "").strip()
    if not dataset_tag:
        raise ValueError("ARANCEL_MX_API_DATASET is required")
    if _DATASET_TAG.fullmatch(dataset_tag) is None:
        raise ValueError(
            "ARANCEL_MX_API_DATASET must use immutable data-YYYY.MM.DD format"
        )

    timeout_text = source.get("ARANCEL_MX_API_TIMEOUT", str(_DEFAULT_TIMEOUT)).strip()
    try:
        timeout = float(timeout_text)
    except ValueError as exc:
        raise ValueError("ARANCEL_MX_API_TIMEOUT must be numeric") from exc
    if not 0 < timeout <= _MAX_TIMEOUT:
        raise ValueError("ARANCEL_MX_API_TIMEOUT must be > 0 and <= 120 seconds")

    cache_text = source.get("ARANCEL_MX_API_CACHE_DIR", "").strip()
    cache_dir = Path(cache_text) if cache_text else None
    offline_text = source.get("ARANCEL_MX_API_OFFLINE", "false").strip() or "false"
    try:
        offline = _parse_offline(offline_text)
    except ValueError as exc:
        raise ValueError("ARANCEL_MX_API_OFFLINE must be a boolean value") from exc

    github_token = source.get("ARANCEL_MX_GITHUB_TOKEN", "").strip() or None
    return ApiSettings(
        dataset_tag=dataset_tag,
        cache_dir=cache_dir,
        timeout=timeout,
        offline=offline,
        github_token=github_token,
    )
