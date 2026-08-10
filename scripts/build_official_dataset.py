"""Build a verified arancel-mx dataset from registered official sources."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Sequence

import requests

from arancel_mx.pipeline.official_dataset import (
    OfficialDatasetConfig,
    build_official_dataset,
)


_DATASET_VERSION = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the canonical arancel-mx dataset from official sources."
    )
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--effective-as-of", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--generated-at")
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser


def _parse_generated_at(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("generated-at must include a timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _config_from_args(args: argparse.Namespace) -> OfficialDatasetConfig:
    if not _DATASET_VERSION.fullmatch(args.dataset_version):
        raise ValueError("dataset-version must use YYYY.MM.DD")
    if args.timeout <= 0:
        raise ValueError("timeout must be positive")
    try:
        effective_as_of = date.fromisoformat(args.effective_as_of)
    except ValueError as exc:
        raise ValueError("effective-as-of must use YYYY-MM-DD") from exc
    try:
        generated_at = _parse_generated_at(args.generated_at)
    except ValueError as exc:
        raise ValueError(f"invalid generated-at: {exc}") from exc
    return OfficialDatasetConfig(
        work_dir=args.work_dir,
        output_dir=args.output_dir,
        effective_as_of=effective_as_of,
        dataset_version=args.dataset_version,
        generated_at=generated_at,
        timeout_s=args.timeout,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = _config_from_args(args)
        summary = build_official_dataset(config)
    except (ValueError, OSError, requests.RequestException) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
