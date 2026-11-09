"""Tell whether a freshly built static API equals the one gh-pages already serves.

The tag alone cannot decide that: a change to the exporter (a new section, a
new field) rebuilds different files for the same release tag. The manifest
lists every file with its size and SHA-256, so equal manifests (ignoring the
build timestamp) mean equal content.

Exit status 0 when the content is the same, 1 when it differs or the deployed
manifest is missing or unreadable, so the caller publishes in every doubtful case.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Mapping, Sequence

# generated_at changes on every build and says nothing about the content.
_IDENTITY = ("static_format", "dataset_tag", "dataset_version", "record_count", "files")


def same_content(deployed: Mapping[str, object], built: Mapping[str, object]) -> bool:
    """Return True when both manifests describe the same release and the same files."""
    return all(key in deployed and deployed[key] == built.get(key) for key in _IDENTITY)


def _load(path: Path) -> Mapping[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print("usage: static_pages_unchanged DEPLOYED_MANIFEST BUILT_MANIFEST", file=sys.stderr)
        return 2
    deployed, built = (_load(Path(item)) for item in arguments)
    return 0 if deployed is not None and built is not None and same_content(deployed, built) else 1


if __name__ == "__main__":
    sys.exit(main())
