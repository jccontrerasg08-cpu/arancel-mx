"""Read-only public snapshot for multidimensional INEGI BCMM analytics."""
from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

EDGE_CACHE = "public, s-maxage=21600, stale-while-revalidate=86400"
SNAPSHOT = Path(__file__).resolve().parents[1] / "src" / "arancel_mx" / "trade_analytics_snapshot.json"
VIEWS = {"monthly", "partners", "tariff_groups"}


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        query = parse_qs(urlparse(self.path).query)
        try:
            payload = load_snapshot()
        except (OSError, json.JSONDecodeError):
            self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "snapshot_unavailable"})
            return
        view = query.get("view", [None])[0]
        if view:
            if view not in VIEWS:
                self._respond(HTTPStatus.BAD_REQUEST, {"status": "invalid_view"})
                return
            try:
                limit = max(1, min(int(query.get("limit", ["25"])[0]), 100))
            except ValueError:
                self._respond(HTTPStatus.BAD_REQUEST, {"status": "invalid_limit"})
                return
            flow = query.get("flow", [None])[0]
            rows = payload.get("observations", {}).get(view, [])
            if flow:
                rows = [row for row in rows if row.get("flow") == flow]
            payload = {key: value for key, value in payload.items() if key != "observations"}
            payload["view"] = view
            payload["filters"] = {"flow": flow, "limit": limit}
            payload["observations"] = rows[:limit]
        self._respond(HTTPStatus.OK, payload)

    def _respond(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", EDGE_CACHE if status == HTTPStatus.OK else "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
