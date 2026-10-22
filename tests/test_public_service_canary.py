from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_service_canary_script_is_versioned() -> None:
    assert (ROOT / "scripts" / "check_public_service.py").is_file()


from typing import Any

import pytest

from scripts import check_public_service
from scripts.check_public_service import check_public_contract


class _Response:
    def __init__(self, payload: Any, *, content_type: str = "application/json") -> None:
        self._payload = payload
        self.status_code = 200
        self.headers = {"Content-Type": content_type}
        self.text = "<html>Swagger UI</html>" if content_type == "text/html" else "{}"

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _Session:
    def __init__(self, responses: dict[str, _Response]) -> None:
        self.responses = responses

    def get(self, url: str, *, timeout: float) -> _Response:
        return self.responses[url]


def _responses(*, record_dataset_version: str = "2026.08.17") -> dict[str, _Response]:
    base = "https://example.test/data/v1"
    record = {
        "code": "8517130100",
        "level": "nico10",
        "dataset_version": record_dataset_version,
    }
    return {
        f"{base}/meta.json": _Response(
            {
                "dataset_tag": "data-2026.08.17",
                "dataset_version": "2026.08.17",
                "release_verified": True,
            }
        ),
        f"{base}/manifest.json": _Response(
            {
                "dataset_tag": "data-2026.08.17",
                "files": {"meta.json": {}, "records/85.json": {}, "search-index.json": {}},
            }
        ),
        f"{base}/records/85.json": _Response([record]),
        f"{base}/search-index.json": _Response(
            {"scorer_version": "1", "entries": [["8517130100", "telefonos inteligentes"]]}
        ),
        "https://example.test/v1/meta": _Response({}),
    }


def test_public_contract_probes_only_the_static_data_api() -> None:
    result = check_public_contract(_Session(_responses()), base_url="https://example.test")

    assert result.dataset_version == "2026.08.17"
    assert result.checked_paths == (
        "/data/v1/meta.json",
        "/data/v1/manifest.json",
        "/data/v1/records/85.json",
        "/data/v1/search-index.json",
    )
    assert all(not path.startswith("/v1/") for path in result.checked_paths)


def test_latency_probe_is_read_only_and_reports_each_static_file() -> None:
    ticks = iter((0.0, 0.1, 1.0, 1.3, 2.0, 2.5))
    measure_public_latency = getattr(check_public_service, "measure_public_latency", None)
    assert callable(measure_public_latency)
    result = measure_public_latency(
        _Session(_responses()),
        base_url="https://example.test",
        samples=1,
        clock=lambda: next(ticks),
    )

    assert tuple(sample.path for sample in result.samples) == (
        "/data/v1/meta.json",
        "/data/v1/search-index.json",
        "/data/v1/records/85.json",
    )
    assert tuple(sample.seconds for sample in result.samples) == pytest.approx((0.1, 0.3, 0.5))
    assert all(sample.status_code == 200 for sample in result.samples)


def test_public_contract_rejects_records_from_another_release() -> None:
    session = _Session(_responses(record_dataset_version="2026.08.16"))

    with pytest.raises(ValueError, match="dataset_version must match"):
        check_public_contract(session, base_url="https://example.test")


def test_public_contract_rejects_an_unverified_release() -> None:
    responses = _responses()
    responses["https://example.test/data/v1/meta.json"] = _Response(
        {"dataset_tag": "data-2026.08.17", "dataset_version": "2026.08.17", "release_verified": False}
    )

    with pytest.raises(ValueError, match="verified release"):
        check_public_contract(_Session(responses), base_url="https://example.test")


def test_public_contract_rejects_a_missing_dataset_tag() -> None:
    responses = _responses()
    responses["https://example.test/data/v1/meta.json"] = _Response(
        {"dataset_version": "2026.08.17", "release_verified": True}
    )

    with pytest.raises(ValueError, match="dataset_tag"):
        check_public_contract(_Session(responses), base_url="https://example.test")


def test_public_contract_rejects_a_non_json_response() -> None:
    responses = _responses()
    responses["https://example.test/data/v1/records/85.json"] = _Response({}, content_type="text/html")

    with pytest.raises(ValueError, match="application/json"):
        check_public_contract(_Session(responses), base_url="https://example.test")
