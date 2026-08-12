"""Validate a package release tag against the project version.

The package publication workflow is driven by ``pkg-vX.Y.Z`` tags that must
match the single source of truth for the version in ``pyproject.toml``. This
module is stdlib-only so the workflow can still validate a tag even when
dependency installation is the step that failed.

The accepted grammar is the subset of PEP 440 the package release process
uses: a dotted numeric release with an optional ``a``/``b``/``rc`` pre-release
segment, prefixed with ``pkg-v`` (for example ``pkg-v0.2.0`` or
``pkg-v0.2.0rc1``). A pre-release tag is publishable to TestPyPI only; a final
tag is additionally eligible for production PyPI after manual approval.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
TAG_PREFIX = "pkg-v"
_VERSION_RE = re.compile(r"^(?P<release>[0-9]+(?:\.[0-9]+)*)(?P<pre>(?:a|b|rc)[0-9]+)?$")
_OUTPUT_KEY = re.compile(r"[a-z][a-z0-9_]*")


class TagError(ValueError):
    """Raised when a tag or project version fails validation."""


def project_version(pyproject: Path | None = None) -> str:
    """Return ``project.version`` from ``pyproject.toml`` as the single source."""

    path = pyproject if pyproject is not None else ROOT / "pyproject.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project")
    version = project.get("version") if isinstance(project, dict) else None
    if not isinstance(version, str) or not version.strip():
        raise TagError("project.version is missing from pyproject.toml")
    return version.strip()


def normalize_version(value: str) -> tuple[str, bool]:
    """Return the normalized version and whether it is a pre-release."""

    match = _VERSION_RE.fullmatch(value.strip().lower())
    if match is None:
        raise TagError(f"invalid package version: {value!r}")
    pre = match.group("pre") or ""
    return match.group("release") + pre, bool(pre)


def evaluate(tag: str, version: str) -> dict[str, object]:
    """Validate ``tag`` against ``version`` and describe production eligibility."""

    if not tag.startswith(TAG_PREFIX):
        raise TagError(f"package tag must start with {TAG_PREFIX!r}: {tag!r}")
    tag_version, tag_is_prerelease = normalize_version(tag[len(TAG_PREFIX) :])
    project_normalized, _ = normalize_version(version)
    if tag_version != project_normalized:
        raise TagError(
            f"tag version {tag_version!r} does not match "
            f"project version {project_normalized!r}"
        )
    return {
        "tag": tag,
        "version": tag_version,
        "is_prerelease": tag_is_prerelease,
        "production_eligible": not tag_is_prerelease,
    }


def render_output_lines(result: dict[str, object]) -> str:
    """Render validated single-line ``key=value`` workflow output lines."""

    values = {
        "version": result["version"],
        "is_prerelease": result["is_prerelease"],
        "production_eligible": result["production_eligible"],
    }
    lines: list[str] = []
    for key, value in values.items():
        if not _OUTPUT_KEY.fullmatch(key):
            raise TagError(f"unsupported workflow output key: {key!r}")
        if isinstance(value, bool):
            text = "true" if value else "false"
        else:
            text = str(value)
        if "\n" in text or "\r" in text:
            raise TagError(f"workflow output must be a single line: {key}")
        lines.append(f"{key}={text}\n")
    return "".join(lines)


def _emit_workflow_output(result: dict[str, object]) -> None:
    # Reading the output path from the environment keeps the reserved variable
    # name out of reviewed workflow YAML while still emitting only validated,
    # single-line values.
    target = os.environ.get("GITHUB_OUTPUT", "").strip()
    if not target:
        raise TagError("workflow output requested but no output path is set")
    with open(target, "a", encoding="utf-8") as stream:
        stream.write(render_output_lines(result))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="the pushed tag, for example pkg-v0.2.0")
    parser.add_argument("--pyproject", type=Path, default=None)
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="append validated version outputs to the workflow output file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = evaluate(args.tag, project_version(args.pyproject))
        if args.github_output:
            _emit_workflow_output(result)
    except TagError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
