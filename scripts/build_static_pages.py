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

from arancel_mx.consumer.config import resolve_config
from arancel_mx.consumer.dataset import Dataset
from arancel_mx.consumer.manager import DatasetManager
from arancel_mx.diff_pages import previous_tag, release_diff_files
from arancel_mx.static_api import build_static_api, verify_static_api


def write_host_files(out: Path) -> None:
    """Write the files that tell hosts how to treat the gh-pages branch."""
    # Serve files as they are; Pages must not run Jekyll over the tree.
    (out / ".nojekyll").write_text("", encoding="utf-8")
    # The Vercel project builds every pushed branch; gh-pages holds only data.
    (out / "vercel.json").write_text(
        json.dumps({"git": {"deploymentEnabled": False}}) + "\n", encoding="utf-8"
    )


def diff_files(
    current: Dataset, tag: str, *, diff_from: str, cache_dir: Path | None
) -> dict[str, bytes]:
    """Compare ``current`` with the previous published release (``diff_from='auto'``).

    A failure to resolve or verify the previous release never blocks the data
    publication: the index then records the reason and no comparison is published.
    """

    if diff_from == "none":
        return {}
    try:
        if diff_from == "auto":
            config = (
                resolve_config(cache_dir=cache_dir) if cache_dir else resolve_config()
            )
            previous = previous_tag(tag, DatasetManager(config).list_remote())
        else:
            previous = diff_from
        if previous is None:
            return release_diff_files(None, current, reason="no earlier published release")
        before = Dataset.version(previous, cache_dir=cache_dir)
        if not before.info.release_verified:
            return release_diff_files(
                None, current, reason=f"{previous} did not pass verification"
            )
        return release_diff_files(before, current)
    except Exception as exc:  # noqa: BLE001 - recorded in the index, never fatal
        return release_diff_files(
            None, current, reason=f"previous release unavailable: {type(exc).__name__}"
        )


def build_pages(
    out: Path,
    *,
    tag: str | None,
    cache_dir: Path | None,
    diff_from: str = "auto",
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
    extra = diff_files(dataset, resolved_tag, diff_from=diff_from, cache_dir=cache_dir)
    manifest = build_static_api(
        Path(dataset.info.path),
        root,
        dataset_tag=resolved_tag,
        release_verified=True,
        extra_files=extra,
    )
    problems = verify_static_api(root)
    if problems:
        raise ValueError("static API verification failed: " + "; ".join(problems))
    write_host_files(out)
    return {
        "dataset_tag": resolved_tag,
        "files": len(manifest["files"]),
        "record_count": manifest["record_count"],
        "diffs": sorted(name for name in extra if name != "diffs/index.json"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--tag", default=None, help="data-YYYY.MM.DD; latest release when omitted"
    )
    parser.add_argument("--cache-dir", type=Path, default=None)
    parser.add_argument(
        "--diff-from",
        default="auto",
        help="auto: previous published release (default); none: skip; or data-YYYY.MM.DD",
    )
    args = parser.parse_args(argv)
    print(
        json.dumps(
            build_pages(
                args.out, tag=args.tag, cache_dir=args.cache_dir, diff_from=args.diff_from
            )
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
