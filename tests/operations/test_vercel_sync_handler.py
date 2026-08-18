from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HANDLER_PATH = ROOT / "api" / "sync_operational.py"


def _handler_module():
    specification = importlib.util.spec_from_file_location("vercel_sync_handler", HANDLER_PATH)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_vercel_sync_handler_rejects_a_request_without_the_cron_secret(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.headers = {"Authorization": "Bearer incorrect"}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.setenv("CRON_SECRET", "expected")

    request.do_GET()

    assert response == [module.HTTPStatus.UNAUTHORIZED, {"status": "unauthorized"}]


def test_vercel_sync_handler_reports_missing_cron_configuration_without_touching_database(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.headers = {}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.delenv("CRON_SECRET", raising=False)

    request.do_GET()

    assert response == [module.HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_configured"}]


def test_vercel_sync_handler_reports_missing_database_configuration_after_valid_authorization(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.headers = {"Authorization": "Bearer expected"}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.setenv("CRON_SECRET", "expected")
    monkeypatch.delenv("ARANCEL_MX_DATABASE_URL", raising=False)

    request.do_GET()

    assert response == [module.HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_configured"}]


def test_vercel_sync_handler_accepts_vercel_neon_database_url(monkeypatch):
    module = _handler_module()
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request.headers = {"Authorization": "Bearer expected"}
    request._respond = lambda status, payload: response.extend((status, payload))
    monkeypatch.setenv("CRON_SECRET", "expected")
    monkeypatch.delenv("ARANCEL_MX_DATABASE_URL", raising=False)
    monkeypatch.setenv("ARANCEL_MX_DATABASE_DATABASE_URL", "postgresql://vercel-neon")

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(module, "_connect", lambda url: Connection())
    monkeypatch.setattr(
        module,
        "synchronize_latest_release",
        lambda connection: {"dataset_tag": "data-2026.08.18", "changed": False},
    )

    request.do_GET()

    assert response == [
        module.HTTPStatus.OK,
        {"status": "promoted", "dataset_tag": "data-2026.08.18", "changed": False},
    ]
