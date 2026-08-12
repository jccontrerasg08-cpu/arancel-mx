"""Bounded, fail-closed diagnostics for the official data pipeline workflow.

GitHub Actions job outputs gate publication, so turning a result file into
workflow outputs is a trust boundary: a value carrying a newline would let one
diagnostic line define additional outputs, including the ``status`` the
publisher depends on. This module keeps that translation in reviewed, tested
code instead of inline workflow scripts, and only emits validated single-line
values.

Only the standard library is imported so the workflow can still report a
diagnosis when dependency installation is the step that failed.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
import os
from pathlib import Path
import re


MAX_MESSAGE_LENGTH = 800
MAX_TOKEN_LENGTH = 120
PIPELINE_STATUSES = frozenset({"built", "no_change", "failed"})
PUBLISHER_STATUSES = frozenset({"published", "failed"})
UNKNOWN = "unknown"
INVALID_DIAGNOSTICS = "invalid_diagnostics"
PREFLIGHT_MESSAGE = (
    "workflow failed before structured pipeline diagnostics were available; "
    "inspect the run logs"
)
PUBLISHER_FALLBACK_MESSAGE = (
    "publisher failed without structured diagnostics; inspect the workflow run logs"
)
UNSUPPORTED_STATUS_MESSAGE = (
    "diagnostics declared an unsupported status; inspect the workflow run logs"
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_OUTPUT_KEY = re.compile(r"[a-z][a-z0-9_]*")


def _token(value: object, *, default: str) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) > MAX_TOKEN_LENGTH or not _TOKEN.fullmatch(text):
        return default
    return text


def _message(value: object, *, default: str) -> str:
    text = " ".join(str(value if value is not None else "").split())
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 3] + "..."
    return text or default


def load_result(path: Path) -> dict[str, object]:
    """Read a diagnostics file, treating any unusable content as absent."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def summarize_pipeline(
    result: Mapping[str, object],
    *,
    dataset_version: str,
    artifact_name: str,
) -> dict[str, str]:
    version = _token(dataset_version, default=UNKNOWN)
    artifact = _token(artifact_name, default=UNKNOWN)
    if not result:
        return {
            "status": "failed",
            "stage": "preflight",
            "dataset_version": version,
            "failure_category": "preflight_failure",
            "message": PREFLIGHT_MESSAGE,
            "artifact_name": artifact,
        }

    status = _token(result.get("status"), default="")
    if status not in PIPELINE_STATUSES:
        return {
            "status": "failed",
            "stage": _token(result.get("stage"), default=UNKNOWN),
            "dataset_version": _token(result.get("dataset_version"), default=version),
            "failure_category": INVALID_DIAGNOSTICS,
            "message": UNSUPPORTED_STATUS_MESSAGE,
            "artifact_name": _token(result.get("artifact_name"), default=artifact),
        }
    return {
        "status": status,
        "stage": _token(result.get("stage"), default=UNKNOWN),
        "dataset_version": _token(result.get("dataset_version"), default=version),
        "failure_category": (
            _token(result.get("failure_category"), default="unknown_error")
            if status == "failed"
            else ""
        ),
        "message": _message(result.get("message"), default=""),
        "artifact_name": _token(result.get("artifact_name"), default=artifact),
    }


def summarize_publisher(result: Mapping[str, object]) -> dict[str, str]:
    if not result:
        return {
            "status": "failed",
            "stage": "publish",
            "failure_category": "publisher_failure",
            "message": PUBLISHER_FALLBACK_MESSAGE,
        }

    status = _token(result.get("status"), default="")
    if status not in PUBLISHER_STATUSES:
        return {
            "status": "failed",
            "stage": _token(result.get("stage"), default="publish"),
            "failure_category": INVALID_DIAGNOSTICS,
            "message": UNSUPPORTED_STATUS_MESSAGE,
        }
    return {
        "status": status,
        "stage": _token(
            result.get("stage"),
            default="complete" if status == "published" else "publish",
        ),
        "failure_category": (
            _token(result.get("failure_category"), default="release_publication")
            if status == "failed"
            else ""
        ),
        "message": _message(result.get("message"), default=""),
    }


def render_github_output(values: Mapping[str, str]) -> str:
    """Render validated ``key=value`` output lines or refuse to render any."""

    lines: list[str] = []
    for key, value in values.items():
        if not _OUTPUT_KEY.fullmatch(key):
            raise ValueError(f"unsupported workflow output key: {key!r}")
        if not isinstance(value, str) or "\n" in value or "\r" in value:
            raise ValueError(f"workflow output must be a single line: {key}")
        lines.append(f"{key}={value}\n")
    return "".join(lines)


def write_github_output(values: Mapping[str, str], path: Path) -> None:
    payload = render_github_output(values)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(payload)


def write_failure_result(
    path: Path,
    *,
    stage: str,
    failure_category: str,
    dataset_version: str,
    message: str,
) -> dict[str, str]:
    result = {
        "status": "failed",
        "stage": _token(stage, default=UNKNOWN),
        "dataset_version": _token(dataset_version, default=UNKNOWN),
        "failure_category": _token(failure_category, default="unknown_error"),
        "message": _message(message, default="failure reported without diagnostic text"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _output_path(argument: str | None, env: Mapping[str, str]) -> Path:
    candidate = argument or env.get("GITHUB_OUTPUT") or ""
    if not candidate.strip():
        raise ValueError("GITHUB_OUTPUT is not set; pass --output explicitly")
    return Path(candidate)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    pipeline = commands.add_parser(
        "pipeline-outputs",
        help="publish bounded build diagnostics as workflow outputs",
    )
    pipeline.add_argument("--result", type=Path, required=True)
    pipeline.add_argument("--dataset-version", default="")
    pipeline.add_argument("--artifact-name", default="")
    pipeline.add_argument("--output", default=None)

    publisher = commands.add_parser(
        "publisher-outputs",
        help="publish bounded publication diagnostics as workflow outputs",
    )
    publisher.add_argument("--result", type=Path, required=True)
    publisher.add_argument("--output", default=None)

    failure = commands.add_parser(
        "write-failure",
        help="write a bounded failure diagnostics file for a workflow stage",
    )
    failure.add_argument("--path", type=Path, required=True)
    failure.add_argument("--stage", required=True)
    failure.add_argument("--failure-category", required=True)
    failure.add_argument("--dataset-version", default="")
    failure.add_argument("--message", default="")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "write-failure":
        values = write_failure_result(
            args.path,
            stage=args.stage,
            failure_category=args.failure_category,
            dataset_version=args.dataset_version,
            message=args.message,
        )
    else:
        if args.command == "pipeline-outputs":
            values = summarize_pipeline(
                load_result(args.result),
                dataset_version=args.dataset_version,
                artifact_name=args.artifact_name,
            )
        else:
            values = summarize_publisher(load_result(args.result))
        write_github_output(values, _output_path(args.output, os.environ))
    print(json.dumps(values, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
