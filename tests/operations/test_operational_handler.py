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


def test_operational_handler_serves_readiness_from_the_active_release(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.path = "/api/operational?resource=ready"
    request.headers = {}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.setenv("ARANCEL_MX_DATABASE_URL", "postgresql://central")

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(module, "_connect", lambda url: Connection())
    monkeypatch.setattr(
        module,
        "active_release_metadata",
        lambda connection: {"dataset_tag": "data-2026.08.18", "dataset_version": "2026.08.18"},
    )

    request.do_GET()

    assert response == [
        module.HTTPStatus.OK,
        {"status": "ready", "dataset_version": "2026.08.18"},
    ]


def test_operational_handler_accepts_vercel_neon_database_url(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.path = "/api/operational?resource=meta"
    request.headers = {}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.delenv("ARANCEL_MX_DATABASE_URL", raising=False)
    monkeypatch.setenv("ARANCEL_MX_DATABASE_DATABASE_URL", "postgresql://vercel-neon")

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


def test_operational_handler_serves_exact_lookup_from_the_active_release(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.path = "/api/operational?resource=lookup&code=85171301"
    request.headers = {}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.setenv("ARANCEL_MX_DATABASE_URL", "postgresql://central")

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    record = {"code": "85171301", "dataset_version": "2026.08.18"}
    monkeypatch.setattr(module, "_connect", lambda url: Connection())
    monkeypatch.setattr(module, "lookup_active_release", lambda connection, code: record)

    request.do_GET()

    assert response == [module.HTTPStatus.OK, record]


def test_operational_handler_rejects_unknown_resource_without_database_connection(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.path = "/api/operational"
    request.headers = {}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.setenv("ARANCEL_MX_DATABASE_URL", "postgresql://central")

    connections: list[str] = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    def connect(url: str):
        connections.append(url)
        return Connection()

    monkeypatch.setattr(module, "_connect", connect)

    request.do_GET()

    assert response == [module.HTTPStatus.NOT_FOUND, {"status": "not_found"}]
    assert connections == []


def test_operational_handler_serves_process_health_without_database(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.path = "/api/operational?resource=health"
    request.headers = {}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.delenv("ARANCEL_MX_DATABASE_URL", raising=False)
    monkeypatch.delenv("ARANCEL_MX_DATABASE_DATABASE_URL", raising=False)

    request.do_GET()

    assert response == [module.HTTPStatus.OK, {"status": "ok"}]


def test_operational_handler_serves_public_api_discovery_without_database(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.path = "/api/operational?resource=api"
    request.headers = {}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.delenv("ARANCEL_MX_DATABASE_URL", raising=False)
    monkeypatch.delenv("ARANCEL_MX_DATABASE_DATABASE_URL", raising=False)

    request.do_GET()

    assert response == [
        module.HTTPStatus.OK,
        {
            "name": "arancel-mx",
            "api_version": "v1",
            "docs": "/documentation",
            "meta": "/v1/meta",
            "read_only": True,
        },
    ]


def test_operational_handler_serves_repository_history_without_database(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.path = "/api/operational?resource=repository"
    request.headers = {}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.delenv("ARANCEL_MX_DATABASE_URL", raising=False)
    monkeypatch.delenv("ARANCEL_MX_DATABASE_DATABASE_URL", raising=False)

    payload = {"releases": [{"tag": "data-2026.08.17"}]}

    class Snapshot:
        def model_dump(self, *, mode: str):
            assert mode == "json"
            return payload

    monkeypatch.setenv("GITHUB_TOKEN", "release-token")
    monkeypatch.setattr(module, "repository_snapshot", lambda token: Snapshot(), raising=False)

    request.do_GET()

    assert response == [module.HTTPStatus.OK, payload]
