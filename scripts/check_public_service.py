"""Read-only public contract canary for the deployed arancel-mx service."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Protocol

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


def _endpoint(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def _json_response(session: Session, base_url: str, path: str, *, timeout: float) -> Any:
    response = session.get(_endpoint(base_url, path), timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").casefold()
    if "application/json" not in content_type:
        raise ValueError(f"{path} must return application/json")
    return response.json()


def _require_record(payload: object, path: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must return an object")
    return payload


def _require_nico_without_rates(record: dict[str, Any], path: str) -> None:
    if record.get("level") != "nico10" or len(str(record.get("code") or "")) != 10:
        raise ValueError(f"{path} must return a 10-digit NICO")
    if record.get("igi") is not None or record.get("ige") is not None:
        raise ValueError(f"{path} must not expose IGI or IGE for a NICO")


def check_public_contract(
    session: Session,
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 20.0,
) -> PublicContractResult:
    """Verify the public release, NICO hierarchy, evidence, and discovery surfaces."""

    meta = _require_record(_json_response(session, base_url, "/v1/meta", timeout=timeout), "/v1/meta")
    dataset_version = meta.get("dataset_version")
    if not isinstance(dataset_version, str) or not dataset_version:
        raise ValueError("/v1/meta must declare dataset_version")
    if meta.get("release_verified") is not True or meta.get("structural_valid") is not True:
        raise ValueError("/v1/meta must declare a verified, structurally valid release")

    lookup = _require_record(
        _json_response(session, base_url, "/v1/lookup/0101210100", timeout=timeout),
        "/v1/lookup/0101210100",
    )
    _require_nico_without_rates(lookup, "/v1/lookup/0101210100")
    if lookup.get("dataset_version") != dataset_version:
        raise ValueError("lookup dataset_version must match /v1/meta")

    ficha = _require_record(
        _json_response(session, base_url, "/v1/ficha/0101210100", timeout=timeout),
        "/v1/ficha/0101210100",
    )
    record = _require_record(ficha.get("record"), "/v1/ficha/0101210100.record")
    _require_nico_without_rates(record, "/v1/ficha/0101210100.record")
    hierarchy = ficha.get("hierarchy")
    if not isinstance(hierarchy, list):
        raise ValueError("/v1/ficha/0101210100 must contain hierarchy")
    fraction = next(
        (
            item
            for item in hierarchy
            if isinstance(item, dict) and item.get("level") == "fraccion8" and len(str(item.get("code") or "")) == 8
        ),
        None,
    )
    if not isinstance(fraction, dict) or fraction.get("igi") is None or fraction.get("ige") is None:
        raise ValueError("NICO ficha hierarchy must retain the parent fraction's published rates")
    if fraction.get("dataset_version") != dataset_version:
        raise ValueError("NICO ficha parent fraction dataset_version must match /v1/meta")
    if record.get("dataset_version") != dataset_version:
        raise ValueError("ficha dataset_version must match /v1/meta")

    provenance = _json_response(
        session,
        base_url,
        "/v1/codes/01012101/provenance",
        timeout=timeout,
    )
    if not isinstance(provenance, list) or not provenance:
        raise ValueError("provenance endpoint must return at least one active source record")

    notes = _json_response(
        session,
        base_url,
        "/v1/chapters/01/national-notes",
        timeout=timeout,
    )
    if not isinstance(notes, list):
        raise ValueError("national-notes endpoint must return an array")

    suggestion = _json_response(
        session,
        base_url,
        "/v1/suggest?q=reproductores&limit=1",
        timeout=timeout,
    )
    if not isinstance(suggestion, list) or not suggestion:
        raise ValueError("suggest endpoint must return a retrieve-only match")

    openapi = _require_record(
        _json_response(session, base_url, "/openapi.json", timeout=timeout),
        "/openapi.json",
    )
    if not isinstance(openapi.get("openapi"), str) or not isinstance(openapi.get("paths"), dict):
        raise ValueError("/openapi.json must expose an OpenAPI document")

    docs_response = session.get(_endpoint(base_url, "/docs"), timeout=timeout)
    docs_response.raise_for_status()
    if "text/html" not in docs_response.headers.get("Content-Type", "").casefold():
        raise ValueError("/docs must return text/html")
    if "swagger" not in docs_response.text.casefold():
        raise ValueError("/docs must contain Swagger UI markup")

    return PublicContractResult(
        base_url=base_url.rstrip("/"),
        dataset_version=dataset_version,
        checked_paths=(
            "/v1/meta",
            "/v1/lookup/0101210100",
            "/v1/ficha/0101210100",
            "/v1/codes/01012101/provenance",
            "/v1/chapters/01/national-notes",
            "/v1/suggest?q=reproductores&limit=1",
            "/openapi.json",
            "/docs",
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT
    result = check_public_contract(session, base_url=args.base_url, timeout=args.timeout)
    print(f"OK public contract: {result.base_url} release={result.dataset_version}")
    for path in result.checked_paths:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
