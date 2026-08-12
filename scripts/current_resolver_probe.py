"""Exercise a built arancel-mx distribution with the normal pip resolver."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install arancel-mx with the normal resolver and report resolved versions.",
    )
    parser.add_argument("distribution", type=Path)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--dataset", type=Path)
    return parser


def _venv_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _clean_env(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    home.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(home)
    if os.name == "nt":
        env["USERPROFILE"] = str(home)
    return env


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise SystemExit(completed.returncode)
    return completed


def _normalized_packages(payload: object) -> dict[str, str]:
    if not isinstance(payload, list):
        raise ValueError("pip list did not return a JSON array")
    resolved: dict[str, str] = {}
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("pip list contains a non-object entry")
        name = item.get("name")
        version = item.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            raise ValueError("pip list entry is missing name/version strings")
        resolved[name.lower().replace("_", "-")] = version
    return dict(sorted(resolved.items()))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    distribution = args.distribution.resolve()
    if not distribution.is_file():
        raise SystemExit(f"distribution does not exist: {distribution}")
    dataset = args.dataset.resolve() if args.dataset is not None else None
    if dataset is not None and not dataset.is_file():
        raise SystemExit(f"dataset does not exist: {dataset}")

    checkout = Path(__file__).resolve().parents[1]
    probe = checkout / "scripts" / "package_consumer_probe.py"

    with tempfile.TemporaryDirectory(prefix="arancel-mx-resolver-") as temporary:
        root = Path(temporary).resolve()
        environment = root / "venv"
        external = root / "external consumer ñ"
        external.mkdir()
        env = _clean_env(root / "home with spaces ñ")
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)

        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                str(distribution),
            ],
            cwd=external,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=external, env=env)
        listing = _run(
            [str(python), "-m", "pip", "list", "--format=json"],
            cwd=external,
            env=env,
        )
        resolved = _normalized_packages(json.loads(listing.stdout))

        probe_command = [
            str(python),
            str(probe),
            "--expected-version",
            args.expected_version,
            "--forbid-root",
            str(checkout),
        ]
        if dataset is not None:
            probe_command.extend(["--dataset", str(dataset)])
        probed = _run(probe_command, cwd=external, env=env)
        probe_payload = json.loads(probed.stdout)
        if not isinstance(probe_payload, dict) or probe_payload.get("status") != "ok":
            raise SystemExit("consumer probe did not report success")

        sys.stdout.write(
            json.dumps(
                {"probe": probe_payload, "resolved": resolved, "status": "ok"},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
