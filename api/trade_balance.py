"""Read-only Vercel function: INEGI's monthly merchandise trade series, trimmed and cached at the edge.

The INEGI token lives only in the ``INEGI_TOKEN`` environment variable of the Vercel project. The browser never sees it:
it calls this function, which asks INEGI and returns just the three monthly series the trade balance section needs.
The page computes the annual table, the year to date and the last months from them (scripts/trade-balance-lib.mjs).
"""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import json
import logging
import os
from urllib.parse import quote
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)

# Monthly series, millions of US dollars: exports, imports and balance (FOB). Keep in step with
# scripts/trade-balance-lib.mjs; a test compares the two lists.
INDICATORS = ("33860", "33861", "33229")
API_BASE = "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR"
# The page shows ten years and needs the year before the first one to compare with: nothing older is sent.
FIRST_PERIOD = "2015/01"
EDGE_CACHE = "public, s-maxage=21600, stale-while-revalidate=86400"


def build_url(token: str) -> str:
    return f"{API_BASE}/{','.join(INDICATORS)}/es/00/false/BIE-BISE/2.0/{quote(token, safe='')}?type=json"


def fetch_inegi(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed https INEGI endpoint
        return json.loads(response.read().decode("utf-8"))


def trim_series(payload: dict) -> dict:
    """Keep only INDICADOR and (TIME_PERIOD, OBS_VALUE) from FIRST_PERIOD on; raise ValueError on an unexpected shape."""

    series = payload.get("Series") if isinstance(payload, dict) else None
    if not isinstance(series, list):
        raise ValueError("INEGI response has no Series list")
    trimmed = []
    for indicator in INDICATORS:
        entry = next((item for item in series if str(item.get("INDICADOR")) == indicator), None)
        if entry is None or not isinstance(entry.get("OBSERVATIONS"), list):
            raise ValueError(f"INEGI response is missing indicator {indicator}")
        observations = [
            {"TIME_PERIOD": item["TIME_PERIOD"], "OBS_VALUE": item["OBS_VALUE"]}
            for item in entry["OBSERVATIONS"]
            if str(item.get("TIME_PERIOD", "")) >= FIRST_PERIOD and item.get("OBS_VALUE") is not None
        ]
        trimmed.append({"INDICADOR": indicator, "OBSERVATIONS": observations})
    return {"Series": trimmed}


class handler(BaseHTTPRequestHandler):
    """GET only; answers 503 until INEGI_TOKEN is configured and 502 when INEGI cannot be reached."""

    def do_GET(self) -> None:  # noqa: N802 - Vercel uses BaseHTTPRequestHandler
        token = os.environ.get("INEGI_TOKEN", "").strip()
        if not token:
            self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_configured"})
            return
        try:
            payload = trim_series(fetch_inegi(build_url(token)))
        except Exception as error:  # noqa: BLE001 - never let the request URL (it holds the token) reach a response or a log
            logger.warning("INEGI trade series unavailable (%s)", type(error).__name__)
            self._respond(HTTPStatus.BAD_GATEWAY, {"status": "upstream_unavailable"})
            return
        self._respond(HTTPStatus.OK, payload)

    def _respond(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", EDGE_CACHE if status == HTTPStatus.OK else "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
