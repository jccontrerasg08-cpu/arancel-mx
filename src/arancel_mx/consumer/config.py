"""Cross-platform consumer configuration with explicit precedence rules."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Final


_DEFAULT_TIMEOUT: Final[float] = 30.0
_MISSING: Final = object()
_TRUE_VALUES: Final = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES: Final = frozenset({"0", "false", "no", "off"})


@dataclass(frozen=True, slots=True)
class ConsumerConfig:
    """Resolved settings used by the public consumer boundary."""

    cache_dir: Path
    dataset: str | None
    offline: bool
    timeout: float


def _default_cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg and xdg.strip():
        return Path(xdg) / "arancel-mx"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "arancel-mx"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) if base and base.strip() else Path.home() / "AppData" / "Local"
        return root / "arancel-mx" / "Cache"
    return Path.home() / ".cache" / "arancel-mx"


def _environment(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    return value


def _parse_offline(value: object, *, environment: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    if environment:
        raise ValueError("ARANCEL_MX_OFFLINE must be a boolean value")
    raise ValueError("offline must be a boolean value")


def _parse_timeout(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("timeout must be greater than zero")
    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("timeout must be a number greater than zero") from exc
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    return timeout


def resolve_config(
    *,
    cache_dir: str | Path | None | object = _MISSING,
    dataset: str | None | object = _MISSING,
    offline: bool | object = _MISSING,
    timeout: float | object = _MISSING,
) -> ConsumerConfig:
    """Resolve explicit arguments, then environment variables, then defaults."""

    if cache_dir is _MISSING or cache_dir is None:
        cache_environment = _environment("ARANCEL_MX_CACHE_DIR")
        if cache_environment is None:
            resolved_cache_dir = _default_cache_dir()
        else:
            resolved_cache_dir = Path(cache_environment)
    else:
        resolved_cache_dir = Path(cache_dir)  # type: ignore[arg-type]

    if dataset is _MISSING:
        resolved_dataset = _environment("ARANCEL_MX_DATASET")
    elif dataset is None:
        resolved_dataset = None
    else:
        resolved_dataset = str(dataset)

    if offline is _MISSING:
        offline_environment = _environment("ARANCEL_MX_OFFLINE")
        resolved_offline = (
            False
            if offline_environment is None
            else _parse_offline(offline_environment, environment=True)
        )
    else:
        resolved_offline = _parse_offline(offline)

    if timeout is _MISSING:
        timeout_environment = _environment("ARANCEL_MX_TIMEOUT")
        resolved_timeout = (
            _DEFAULT_TIMEOUT
            if timeout_environment is None
            else _parse_timeout(timeout_environment)
        )
    else:
        resolved_timeout = _parse_timeout(timeout)

    return ConsumerConfig(
        cache_dir=resolved_cache_dir,
        dataset=resolved_dataset,
        offline=resolved_offline,
        timeout=resolved_timeout,
    )
