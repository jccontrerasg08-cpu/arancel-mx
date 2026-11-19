"""Daily canary for Annex 2.4.1: find the current edition, read it and check its shape.

It runs the same discovery, capture and reader as the official pipeline, but publishes nothing. A
failure means the next release would go out without NOM data (decision 0004), so it is worth
knowing before the pipeline runs. Exit 0 when the annex is found and reads like the annex.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

import requests

from arancel_mx.parsers.nom_annex import (
    AnnexParseError,
    locate_annex_pages,
    parse_annex,
    read_annex_pages,
    validate_annex_structure,
)
from arancel_mx.pipeline.reconcile import discover_registered_sources, select_current_document
from arancel_mx.sources.http import build_official_session, fetch_official_document
from arancel_mx.sources.registry import load_source_registry


def check(timeout_s: float = 60.0, session: Any | None = None) -> dict[str, object]:
    """Return what was found and read; raise ValueError/AnnexParseError/RequestException if not."""
    registry = load_source_registry()
    entry = registry["nom_annex"]
    client = session or build_official_session()
    discovered = discover_registered_sources({"nom_annex": entry}, client, timeout_s=timeout_s)
    document = select_current_document(discovered, "nom_annex", "nom_annex_rules")
    fetched = fetch_official_document(
        client, document.source_url, entry.allowed_hosts, entry.media_types, timeout_s=timeout_s
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "annex.pdf"
        path.write_bytes(fetched.content)
        first_page, last_page = locate_annex_pages(path)
        parsed = parse_annex(read_annex_pages(path, first_page, last_page), first_page=first_page)
        summary = validate_annex_structure(parsed)
    return {
        "status": "ok",
        "source_url": fetched.final_url,
        "sha256": hashlib.sha256(fetched.content).hexdigest(),
        "first_page": first_page,
        "last_page": last_page,
        **summary,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = check(args.timeout)
    except (AnnexParseError, ValueError, OSError, requests.RequestException) as error:
        print(json.dumps({"status": "failed", "error": f"{type(error).__name__}: {error}"[:500]}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
