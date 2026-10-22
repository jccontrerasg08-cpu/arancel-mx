"""Read-only canary for the static data API that the public site serves under /data/v1."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from time import monotonic
from typing import Any, Callable, Protocol

import requests


DEFAULT_BASE_URL = "https://arancel-mx.vercel.app"
_USER_AGENT = "arancel-mx-public-contract-canary/1.0"


class Response(Protocol):
    status_code: int
    headers: dict[str, str]
    text: str

    def json(self) -> Any: ...

    def raise_for_status(self) -> None: ...


class Session(Protocol):
    def get(self, url: str, *, timeout: float) -> Response: ...


@dataclass(frozen=True)
class PublicContractResult:
    base_url: str
    dataset_version: str
    checked_paths: tuple[str, ...]


@dataclass(frozen=True)
class LatencySample:
    path: str
    seconds: float
    status_code: int


@dataclass(frozen=True)
class LatencyProbeResult:
    base_url: str
    samples: tuple[LatencySample, ...]


DATA_PREFIX = "/data/v1"
_META_PATH = f"{DATA_PREFIX}/meta.json"
_MANIFEST_PATH = f"{DATA_PREFIX}/manifest.json"
_RECORDS_PATH = f"{DATA_PREFIX}/records/85.json"
_SEARCH_INDEX_PATH = f"{DATA_PREFIX}/search-index.json"

_LATENCY_PATHS = (
    _META_PATH,
    _SEARCH_INDEX_PATH,
    _RECORDS_PATH,
)


def _endpoint(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def _json_response(session: Session, base_url: str, path: str, *, timeout: float) -> Any:
    response = session.get(_endpoint(base_url, path), timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").casefold()
    if "application/json" not in content_type:
        raise ValueError(f"{path} must return application/json")
    return response.json()


def _require_object(payload: object, path: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must return an object")
    return payload


def _require_text(payload: dict[str, Any], field: str, path: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must declare {field}")
    return value


def check_public_contract(
    session: Session,
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 20.0,
) -> PublicContractResult:
    """Verify the static data API files that the public site serves under /data/v1."""

    meta = _require_object(
        _json_response(session, base_url, _META_PATH, timeout=timeout), _META_PATH
    )
    dataset_tag = _require_text(meta, "dataset_tag", _META_PATH)
    dataset_version = _require_text(meta, "dataset_version", _META_PATH)
    if meta.get("release_verified") is not True:
        raise ValueError(f"{_META_PATH} must declare a verified release")

    manifest = _require_object(
        _json_response(session, base_url, _MANIFEST_PATH, timeout=timeout),
        _MANIFEST_PATH,
    )
    if manifest.get("dataset_tag") != dataset_tag:
        raise ValueError(f"{_MANIFEST_PATH} dataset_tag must match {_META_PATH}")
    files = manifest.get("files")
    if not isinstance(files, dict) or "records/85.json" not in files:
        raise ValueError(f"{_MANIFEST_PATH} must list every static file")

    records = _json_response(session, base_url, _RECORDS_PATH, timeout=timeout)
    if not isinstance(records, list) or not records:
        raise ValueError(f"{_RECORDS_PATH} must return a non-empty array")
    for record in records:
        if not isinstance(record, dict) or not str(record.get("code") or "").startswith("85"):
            raise ValueError(f"{_RECORDS_PATH} must contain only chapter 85 records")
        if record.get("dataset_version", dataset_version) != dataset_version:
            raise ValueError(f"{_RECORDS_PATH} dataset_version must match {_META_PATH}")

    search_index = _require_object(
        _json_response(session, base_url, _SEARCH_INDEX_PATH, timeout=timeout),
        _SEARCH_INDEX_PATH,
    )
    entries = search_index.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{_SEARCH_INDEX_PATH} must contain retrieve-only entries")

    return PublicContractResult(
        base_url=base_url.rstrip("/"),
        dataset_version=dataset_version,
        checked_paths=(_META_PATH, _MANIFEST_PATH, _RECORDS_PATH, _SEARCH_INDEX_PATH),
    )


def measure_public_latency(
    session: Session,
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 20.0,
    samples: int = 3,
    clock: Callable[[], float] = monotonic,
) -> LatencyProbeResult:
    """Measure static data API GETs without changing service data or configuration."""

    if samples < 1:
        raise ValueError("samples must be at least 1")
    observations: list[LatencySample] = []
    for _ in range(samples):
        for path in _LATENCY_PATHS:
            started_at = clock()
            response = session.get(_endpoint(base_url, path), timeout=timeout)
            response.raise_for_status()
            observations.append(
                LatencySample(
                    path=path,
                    seconds=clock() - started_at,
                    status_code=response.status_code,
                )
            )
    return LatencyProbeResult(base_url=base_url.rstrip("/"), samples=tuple(observations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--latency-samples", type=int, default=0)
    args = parser.parse_args()

    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT
    result = check_public_contract(session, base_url=args.base_url, timeout=args.timeout)
    print(f"OK public contract: {result.base_url} release={result.dataset_version}")
    for path in result.checked_paths:
        print(f"  - {path}")
    if args.latency_samples:
        latency = measure_public_latency(
            session,
            base_url=args.base_url,
            timeout=args.timeout,
            samples=args.latency_samples,
        )
        print(f"Latency samples: {len(latency.samples)}")
        for sample in latency.samples:
            print(f"  - {sample.path} status={sample.status_code} seconds={sample.seconds:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
