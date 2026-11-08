from __future__ import annotations

import importlib.util
import json
import re
from http import HTTPStatus
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
HANDLER_PATH = ROOT / "api" / "trade_balance.py"
SECRET = "unit-test-token-123"


def _module():
    specification = importlib.util.spec_from_file_location("vercel_trade_balance", HANDLER_PATH)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _call(module):
    response: list[object] = []
    request = module.handler.__new__(module.handler)
    request._respond = lambda status, payload: response.extend((status, payload))
    request.do_GET()
    return response


def _payload(first_month: str = "2014/12") -> dict:
    def series(identifier: str) -> dict:
        return {
            "INDICADOR": identifier,
            "FREQ": "8",
            "OBSERVATIONS": [
                {"TIME_PERIOD": first_month, "OBS_VALUE": "1.5", "OBS_STATUS": "x"},
                {"TIME_PERIOD": "2015/01", "OBS_VALUE": "2.5", "OBS_STATUS": "x"},
                {"TIME_PERIOD": "2026/09", "OBS_VALUE": "3.5", "OBS_STATUS": "x"},
                {"TIME_PERIOD": "2026/10", "OBS_VALUE": None},
            ],
        }

    return {"Header": {"Name": "x"}, "Series": [series("33229"), series("33860"), series("33861")]}


def test_without_a_token_the_function_reports_not_configured_and_never_calls_inegi(monkeypatch):
    module = _module()
    monkeypatch.delenv("INEGI_TOKEN", raising=False)
    monkeypatch.setattr(module, "fetch_inegi", lambda url: pytest.fail("INEGI must not be called without a token"))

    assert _call(module) == [HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_configured"}]


def test_with_a_token_it_returns_only_the_three_series_trimmed_to_the_needed_months(monkeypatch):
    module = _module()
    monkeypatch.setenv("INEGI_TOKEN", f"  {SECRET}  ")
    seen: list[str] = []
    monkeypatch.setattr(module, "fetch_inegi", lambda url: seen.append(url) or _payload())

    status, payload = _call(module)

    assert status == HTTPStatus.OK
    assert seen == [
        "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/33860,33861,33229/es/00/false/BIE-BISE/2.0/" + SECRET + "?type=json"
    ]
    assert [item["INDICADOR"] for item in payload["Series"]] == ["33860", "33861", "33229"]
    for item in payload["Series"]:
        assert item["OBSERVATIONS"] == [{"TIME_PERIOD": "2015/01", "OBS_VALUE": "2.5"}, {"TIME_PERIOD": "2026/09", "OBS_VALUE": "3.5"}]
    assert SECRET not in json.dumps(payload)


def test_an_upstream_failure_is_a_bad_gateway_that_leaks_neither_url_nor_token(monkeypatch, caplog):
    module = _module()
    monkeypatch.setenv("INEGI_TOKEN", SECRET)

    def explode(url: str):
        raise OSError(f"cannot reach {url}")

    monkeypatch.setattr(module, "fetch_inegi", explode)

    with caplog.at_level("WARNING"):
        response = _call(module)

    assert response == [HTTPStatus.BAD_GATEWAY, {"status": "upstream_unavailable"}]
    assert SECRET not in caplog.text and "inegi.org.mx" not in caplog.text


def test_an_unexpected_response_shape_is_rejected(monkeypatch):
    module = _module()
    monkeypatch.setenv("INEGI_TOKEN", SECRET)
    monkeypatch.setattr(module, "fetch_inegi", lambda url: {"Series": [{"INDICADOR": "33860", "OBSERVATIONS": []}]})

    assert _call(module) == [HTTPStatus.BAD_GATEWAY, {"status": "upstream_unavailable"}]


def test_the_function_and_the_page_ask_for_the_same_indicators() -> None:
    module = _module()
    library = (ROOT / "scripts" / "trade-balance-lib.mjs").read_text(encoding="utf-8")
    declared = re.search(r"export const INDICATORS = \{ exports: '(\d+)', imports: '(\d+)', balance: '(\d+)' \}", library)
    assert declared is not None
    assert declared.groups() == module.INDICATORS
    assert module.API_BASE in library


def test_vercel_config_does_not_swallow_the_function_in_the_spa_rewrite() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert not re.fullmatch(config["rewrites"][-1]["source"], "/api/trade_balance")
