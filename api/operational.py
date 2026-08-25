"""Read-only Vercel function for the active verified Arancel MX Neon release."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
import json
import os
import logging
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

from api._runtime import ensure_project_source


ensure_project_source()

from arancel_mx.api import API_VERSION
from arancel_mx.operational.query import (
    active_release_metadata,
    chapters_active_release,
    children_active_release,
    ficha_active_release,
    lookup_active_release,
    national_notes_active_release,
    parent_active_release,
    provenance_active_release,
    search_public_active_release,
    sections_active_release,
    suggest_active_release,
)
from arancel_mx.api.repository import repository_snapshot
from arancel_mx.operational.runtime_config import operational_database_url


logger = logging.getLogger(__name__)


def _connect(database_url: str):
    vendor_directory = Path(__file__).with_name("_vendor")
    vendor_path = str(vendor_directory)
    if vendor_directory.is_dir() and vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)

    import psycopg

    return psycopg.connect(database_url)


class handler(BaseHTTPRequestHandler):
    """Expose only metadata and bounded retrieval from the active release view."""

    def do_GET(self) -> None:  # noqa: N802 - Vercel uses BaseHTTPRequestHandler
        query = parse_qs(urlparse(self.path).query)
        resource = query.get("resource", [""])[0]
        if resource == "health":
            self._respond(HTTPStatus.OK, {"status": "ok"})
            return
        if resource == "api":
            self._respond(
                HTTPStatus.OK,
                {
                    "name": "arancel-mx",
                    "api_version": API_VERSION,
                    "docs": "/documentation",
                    "meta": "/v1/meta",
                    "read_only": True,
                },
            )
            return
        if resource == "repository":
            snapshot = repository_snapshot(os.environ.get("GITHUB_TOKEN"))
            self._respond(HTTPStatus.OK, snapshot.model_dump(mode="json"))
            return
        if resource not in {
            "meta",
            "ready",
            "search",
            "suggest",
            "ficha",
            "sections",
            "lookup",
            "chapters",
            "parent",
            "children",
            "national-notes",
            "provenance",
        }:
            self._respond(HTTPStatus.NOT_FOUND, {"status": "not_found"})
            return

        database_url = operational_database_url()
        if not database_url:
            self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_configured"})
            return
        try:
            with _connect(database_url) as connection:
                if resource in {"meta", "ready"}:
                    payload = active_release_metadata(connection)
                    if payload is None:
                        self._respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_ready"})
                        return
                    if resource == "ready":
                        self._respond(
                            HTTPStatus.OK,
                            {
                                "status": "ready",
                                "dataset_version": payload["dataset_version"],
                            },
                        )
                        return
                    self._respond(HTTPStatus.OK, payload)
                    return
                if resource == "search":
                    text = query.get("q", [""])[0]
                    limit = int(query.get("limit", ["20"])[0])
                    self._respond(HTTPStatus.OK, search_public_active_release(connection, text, limit=limit))
                    return
                if resource == "suggest":
                    text = query.get("q", [""])[0]
                    limit = int(query.get("limit", ["5"])[0])
                    self._respond(HTTPStatus.OK, suggest_active_release(connection, text, limit=limit))
                    return
                if resource == "ficha":
                    ficha = ficha_active_release(connection, query.get("code", [""])[0])
                    if ficha is None:
                        self._respond(HTTPStatus.NOT_FOUND, {"status": "not_found"})
                    else:
                        self._respond(HTTPStatus.OK, ficha)
                    return
                if resource == "sections":
                    self._respond(HTTPStatus.OK, sections_active_release())
                    return
                if resource == "lookup":
                    record = lookup_active_release(connection, query.get("code", [""])[0])
                    if record is None:
                        self._respond(HTTPStatus.NOT_FOUND, {"status": "not_found"})
                    else:
                        self._respond(HTTPStatus.OK, record)
                    return
                if resource == "chapters":
                    self._respond(HTTPStatus.OK, chapters_active_release(connection))
                    return
                if resource == "parent":
                    self._respond(
                        HTTPStatus.OK,
                        parent_active_release(connection, query.get("code", [""])[0]),
                    )
                    return
                if resource == "children":
                    self._respond(
                        HTTPStatus.OK,
                        children_active_release(connection, query.get("code", [""])[0]),
                    )
                    return
                if resource == "national-notes":
                    self._respond(
                        HTTPStatus.OK,
                        national_notes_active_release(connection, query.get("chapter", [""])[0]),
                    )
                    return
                if resource == "provenance":
                    self._respond(
                        HTTPStatus.OK,
                        provenance_active_release(connection, query.get("code", [""])[0]),
                    )
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
