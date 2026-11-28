"""Precomputed release comparisons for the static data API (``/data/v1/diffs``).

The pages build compares the release it publishes with the published release right
before it and writes the same report as ``arancel-mx data diff --format json``. Both
sides are verified releases downloaded through the consumer client. When the previous
release cannot be resolved, the index says why instead of publishing an empty diff
that would read as "nothing changed".
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from typing import Any, cast

from arancel_mx.consumer.release_diff import auxiliary_rows, current_rows, release_diff_report

DIFF_INDEX = "diffs/index.json"
DIFF_INDEX_POLICY = "release-diff-pages-v1"

_TAG = re.compile(r"^data-\d{4}\.\d{2}\.\d{2}$")


def previous_tag(current: str, tags: Iterable[str]) -> str | None:
    """The newest well-formed release tag older than ``current`` (tags sort by date)."""

    older = sorted(tag for tag in tags if _TAG.match(tag) and tag < current)
    return older[-1] if older else None


def diff_file_name(from_version: str, to_version: str) -> str:
    return f"diffs/{from_version}--{to_version}.json"


def _dump(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _side(dataset: Any) -> tuple[dict[str, dict[str, object]], dict[str, Any], dict[str, object]]:
    with dataset.connect() as connection:
        rows = current_rows(connection)
        auxiliary = auxiliary_rows(connection)
    info = dataset.info
    return (
        rows,
        auxiliary,
        {
            "dataset_version": info.dataset_version,
            "release_verified": info.release_verified,
            "github_digest_state": info.github_digest_state,
        },
    )


def release_diff_files(
    before: Any | None,
    after: Any,
    *,
    reason: str | None = None,
) -> dict[str, bytes]:
    """Return the ``diffs/`` files to add to the static API tree.

    ``before`` and ``after`` are opened ``Dataset`` objects. With no ``before``, only the
    index is written, carrying ``reason``.
    """

    to_version = str(after.info.dataset_version)
    if before is None:
        return {
            DIFF_INDEX: _dump(
                {
                    "policy_version": DIFF_INDEX_POLICY,
                    "to": to_version,
                    "latest": None,
                    "diffs": [],
                    "reason": reason or "no previous published release",
                }
            )
        }
    before_rows, before_auxiliary, from_info = _side(before)
    after_rows, after_auxiliary, to_info = _side(after)
    report = release_diff_report(
        before_rows,
        after_rows,
        from_info=from_info,
        to_info=to_info,
        auxiliary_from=before_auxiliary,
        auxiliary_to=after_auxiliary,
    )
    from_version = str(from_info["dataset_version"])
    name = diff_file_name(from_version, to_version)
    counts = cast("Mapping[str, Any]", report["counts"])
    auxiliary = cast("Mapping[str, Mapping[str, Any]]", report.get("auxiliary") or {})
    entry = {
        "from": from_version,
        "to": to_version,
        "path": name,
        "comparison_status": report["comparison_status"],
        "changes": counts["changes"],
        "by_event": counts["by_event"],
        "auxiliary": {
            table: {"status": result["status"], "changes": len(result.get("changes") or [])}
            for table, result in auxiliary.items()
        },
    }
    index = {
        "policy_version": DIFF_INDEX_POLICY,
        "to": to_version,
        "latest": name,
        "diffs": [entry],
        "note": report["note"],
    }
    return {DIFF_INDEX: _dump(index), name: _dump(report)}
