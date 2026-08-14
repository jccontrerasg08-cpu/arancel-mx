"""Probe an installed arancel-mx package from an external working directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def _emit(payload: dict[str, object]) -> None:
    sys.stdout.write(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify one installed arancel-mx consumer distribution.",
    )
    parser.add_argument("--expected-version", required=True)
    parser.add_argument(
        "--forbid-root",
        type=Path,
        help="Fail if arancel_mx imports from beneath this source checkout root.",
    )
    parser.add_argument(
        "--forbid-src-layout",
        action="store_true",
        help="Fail if arancel_mx imports from a checkout src/arancel_mx layout.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        help="Optional local DuckDB dataset to open and query read-only.",
    )
    parser.add_argument(
        "--lookup-code",
        default="01012101",
        help="Exact code used when --dataset is supplied.",
    )
    return parser


def _error(check: str, message: str, **metadata: object) -> int:
    _emit({"check": check, "message": message, "status": "error", **metadata})
    return 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        import arancel_mx
    except Exception as exc:  # pragma: no cover - exercised in external failure probes
        return _error("import", f"arancel_mx import failed: {type(exc).__name__}")

    origin_text = getattr(arancel_mx, "__file__", None)
    if not origin_text:
        return _error("import_origin", "arancel_mx import origin is unavailable")
    origin = Path(origin_text).resolve()

    if args.forbid_root is not None:
        forbidden = args.forbid_root.resolve()
        if origin.is_relative_to(forbidden):
            return _error(
                "import_origin",
                "arancel_mx resolved from the forbidden source checkout",
                import_origin=str(origin),
            )

    if args.forbid_src_layout:
        if (
            origin.name == "__init__.py"
            and origin.parent.name == "arancel_mx"
            and origin.parent.parent.name == "src"
        ):
            return _error(
                "import_origin",
                "arancel_mx resolved from a source checkout src layout",
                import_origin=str(origin),
            )

    actual_version = arancel_mx.__version__
    if actual_version != args.expected_version:
        return _error(
            "version",
            "installed package version does not match the expected version",
            actual_version=actual_version,
            expected_version=args.expected_version,
            import_origin=str(origin),
        )

    payload: dict[str, object] = {
        "import_origin": str(origin),
        "status": "ok",
        "version": actual_version,
    }

    if args.dataset is not None:
        dataset_path = args.dataset.resolve()
        try:
            dataset = arancel_mx.Dataset.open(dataset_path)
            record = dataset.lookup(args.lookup_code)
            hits = dataset.suggest("reproductores", limit=1)
        except Exception as exc:
            return _error(
                "dataset",
                f"local dataset probe failed: {type(exc).__name__}: {exc}",
                dataset=str(dataset_path),
                import_origin=str(origin),
                version=actual_version,
            )
        payload.update(
            {
                "dataset": str(dataset_path),
                "dataset_source": dataset.info.source,
                "dataset_structural_valid": dataset.info.structural_valid,
                "lookup_code": record.code,
                "suggest_count": len(hits),
                "suggest_code": None if not hits else hits[0].search.record.code,
                "suggest_scorer_version": None
                if not hits
                else hits[0].search.scorer_version,
            }
        )

    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
