"""Promote one independently certified release into the central serving database."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import datetime
import os
from pathlib import Path
from typing import Any

from arancel_mx.operational import load_certified_release, promote_release


class OperationalPromotionRunnerError(ValueError):
    """Raised when the standalone operational promotion cannot start safely."""


def _parse_datetime(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationalPromotionRunnerError(f"invalid {field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OperationalPromotionRunnerError(f"{field} must be timezone-aware")
    return parsed


def _connect(database_url: str) -> Any:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - exercised in deployment setup
        raise OperationalPromotionRunnerError(
            "psycopg is required for operational database promotion"
        ) from exc
    return psycopg.connect(database_url)


def promote_operational_release(
    release_dir: Path,
    *,
    database_url: str,
    published_at: datetime,
    source_checked_at: datetime,
    connect: Callable[[str], Any] = _connect,
) -> dict[str, object]:
    """Certify a release first, then promote it within one database connection."""

    if not database_url.strip():
        raise OperationalPromotionRunnerError("database_url is required")
    release, records = load_certified_release(
        Path(release_dir),
        published_at=published_at,
        source_checked_at=source_checked_at,
    )
    with connect(database_url) as connection:
        promote_release(connection, release, records)
    return {"release_tag": getattr(release, "tag", None), "record_count": len(records)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Promote one certified Arancel MX release to operational storage."
    )
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--published-at", required=True)
    parser.add_argument("--source-checked-at", required=True)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("ARANCEL_MX_DATABASE_URL", ""),
    )
    args = parser.parse_args(argv)
    result = promote_operational_release(
        args.release_dir,
        database_url=args.database_url,
        published_at=_parse_datetime(args.published_at, "published_at"),
        source_checked_at=_parse_datetime(args.source_checked_at, "source_checked_at"),
    )
    print(result)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
