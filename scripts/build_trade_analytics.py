#!/usr/bin/env python3
"""Build a small BCMM analytics snapshot from official CSV exports."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arancel_mx.trade_analytics import write_snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate official INEGI BCMM CSV files.")
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "src/arancel_mx/trade_analytics_snapshot.json")
    parser.add_argument("--source-url", default="https://www.inegi.org.mx/programas/comext/default.html")
    args = parser.parse_args()
    snapshot = write_snapshot(args.input, args.output, args.source_url)
    print(f"Wrote {args.output} from {snapshot['coverage']['input_rows']} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
