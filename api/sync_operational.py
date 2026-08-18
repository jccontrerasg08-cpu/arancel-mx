"""Private Vercel cron handler for certified Arancel MX operational-data sync."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import json
import logging
import os
from pathlib import Path
import sys

from api._runtime import ensure_project_source


ensure_project_source()

from arancel_mx.operational.runtime_config import operational_database_url
from arancel_mx.operational.sync import OperationalSyncError, synchronize_latest_release


logger = logging.getLogger(__name__)


def _connect(database_url: str):
    vendor_directory = Path(__file__).with_name("_vendor")
    vendor_path = str(vendor_directory)
    if vendor_directory.is_dir() and vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)

    import psycopg

    return psycopg.connect(database_url)


class handler(BaseHTTPRequestHandler):
    """Run an idempotent Neon promotion only for authenticated Vercel cron calls."""

    def do_GET(self) -> None:  # noqa: N802 - Vercel uses BaseHTTPRequestHandler
        cron_secret = os.environ.get("CRON_SECRET")
        if not cron_secret:
            self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_configured"})
            return
        authorization = self.headers.get("Authorization")
        if authorization != f"Bearer {cron_secret}":
            self._respond(HTTPStatus.UNAUTHORIZED, {"status": "unauthorized"})
            return

        database_url = operational_database_url()
        if not database_url:
            self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_configured"})
            return
        try:
            with _connect(database_url) as connection:
                result = synchronize_latest_release(connection)
        except (OperationalSyncError, OSError, RuntimeError, ValueError):
            logger.error("verified operational release synchronization failed")
            self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_promoted"})
            return
        self._respond(HTTPStatus.OK, {"status": "promoted", **result})

    def _respond(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
