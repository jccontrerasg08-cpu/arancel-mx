"""Build the GitHub Pages tree for one verified release (decision 0002).

Downloads the release through the consumer client, which checks the manifest
and SHA256SUMS, writes the static data API under ``<out>/v1`` and verifies every
file against its manifest. Publishing the tree is the workflow's job.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from arancel_mx.consumer.dataset import Dataset
from arancel_mx.static_api import build_static_api, verify_static_api


def build_pages(
    out: Path, *, tag: str | None, cache_dir: Path | None
) -> dict[str, object]:
    dataset = (
        Dataset.version(tag, cache_dir=cache_dir)
        if tag
        else Dataset.latest(cache_dir=cache_dir)
    )
    if not dataset.info.release_verified:
        raise ValueError("refusing to publish a release that was not verified")
    resolved_tag = tag or f"data-{dataset.info.dataset_version}"
    root = out / "v1"
    manifest = build_static_api(
        Path(dataset.info.path), root, dataset_tag=resolved_tag, release_verified=True
    )
    problems = verify_static_api(root)
    if problems:
        raise ValueError("static API verification failed: " + "; ".join(problems))
    # Serve files as they are; Pages must not run Jekyll over the tree.
    (out / ".nojekyll").write_text("", encoding="utf-8")
    return {
        "dataset_tag": resolved_tag,
        "files": len(manifest["files"]),
        "record_count": manifest["record_count"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--tag", default=None, help="data-YYYY.MM.DD; latest release when omitted"
    )
    parser.add_argument("--cache-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    print(json.dumps(build_pages(args.out, tag=args.tag, cache_dir=args.cache_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
