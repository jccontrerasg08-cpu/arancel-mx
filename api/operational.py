"""Read-only Vercel function for the active verified Arancel MX Neon release."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import json
import logging
from urllib.parse import parse_qs, urlparse

from arancel_mx.operational.query import active_release_metadata, search_active_release
from arancel_mx.operational.runtime_config import operational_database_url


logger = logging.getLogger(__name__)


def _connect(database_url: str):
    import psycopg

    return psycopg.connect(database_url)


class handler(BaseHTTPRequestHandler):
    """Expose only metadata and bounded retrieval from the active release view."""

    def do_GET(self) -> None:  # noqa: N802 - Vercel uses BaseHTTPRequestHandler
        database_url = operational_database_url()
        if not database_url:
            self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_configured"})
            return
        query = parse_qs(urlparse(self.path).query)
        resource = query.get("resource", [""])[0]
        try:
            with _connect(database_url) as connection:
                if resource == "meta":
                    payload = active_release_metadata(connection)
                    if payload is None:
                        self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_ready"})
                        return
                    self._respond(HTTPStatus.OK, payload)
                    return
                if resource == "search":
                    text = query.get("q", [""])[0]
                    limit = int(query.get("limit", ["8"])[0])
                    self._respond(HTTPStatus.OK, search_active_release(connection, text, limit=limit))
                    return
        except (OSError, RuntimeError, ValueError):
            logger.error("operational read-only query failed")
            self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_ready"})
            return
        self._respond(HTTPStatus.NOT_FOUND, {"status": "not_found"})

    def _respond(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
