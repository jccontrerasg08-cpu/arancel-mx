from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_service_canary_script_is_versioned() -> None:
    assert (ROOT / "scripts" / "check_public_service.py").is_file()


from typing import Any

import pytest

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


def _responses(*, parent_dataset_version: str = "data-2026.08.17") -> dict[str, _Response]:
    base = "https://example.test"
    nico = {
        "code": "0101210100",
        "level": "nico10",
        "igi": None,
        "ige": None,
        "dataset_version": "data-2026.08.17",
    }
    fraction = {
        "code": "01012101",
        "level": "fraccion8",
        "igi": {"text": "10", "value": 10.0},
        "ige": {"text": "Ex.", "value": 0.0},
        "dataset_version": parent_dataset_version,
    }
    return {
        f"{base}/v1/meta": _Response(
            {"dataset_version": "data-2026.08.17", "release_verified": True, "structural_valid": True}
        ),
        f"{base}/v1/lookup/0101210100": _Response(nico),
        f"{base}/v1/ficha/0101210100": _Response({"record": nico, "hierarchy": [fraction, nico]}),
        f"{base}/v1/codes/01012101/provenance": _Response([{"code": "01012101"}]),
        f"{base}/v1/chapters/01/national-notes": _Response([]),
        f"{base}/v1/suggest?q=reproductores&limit=1": _Response([{"search": {}}]),
        f"{base}/openapi.json": _Response({"openapi": "3.1.0", "paths": {"/v1/meta": {}}}),
        f"{base}/docs": _Response({}, content_type="text/html"),
    }


def test_public_contract_rejects_a_parent_fraction_from_another_release() -> None:
    session = _Session(_responses(parent_dataset_version="data-2026.08.16"))

    with pytest.raises(ValueError, match="parent fraction dataset_version"):
        check_public_contract(session, base_url="https://example.test")
