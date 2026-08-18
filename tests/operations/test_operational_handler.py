from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HANDLER_PATH = ROOT / "api" / "operational.py"


def _handler_module():
    specification = importlib.util.spec_from_file_location("vercel_operational_handler", HANDLER_PATH)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_operational_handler_serves_only_active_release_metadata(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.path = "/api/operational?resource=meta"
    request.headers = {}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.setenv("ARANCEL_MX_DATABASE_URL", "postgresql://central")

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    metadata = {"dataset_tag": "data-2026.08.18", "release_verified": True}
    monkeypatch.setattr(module, "_connect", lambda url: Connection())
    monkeypatch.setattr(module, "active_release_metadata", lambda connection: metadata)

    request.do_GET()

    assert response == [module.HTTPStatus.OK, metadata]
