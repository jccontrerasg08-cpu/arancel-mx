"""Smoke-test built distributions in a clean virtual environment.

This script deliberately runs the installed package outside the repository checkout so
an editable checkout, the current working directory, or package-local source files
cannot make an incomplete wheel/sdist appear usable.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _venv_console_script(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "arancel-mx.exe"
    return venv_dir / "bin" / "arancel-mx"


def smoke_commands(dist_path: Path, work_dir: Path) -> list[list[str]]:
    """Return install and smoke commands for an already-created virtualenv."""
    artifact = dist_path.resolve()
    python = _venv_python(work_dir)
    console_script = _venv_console_script(work_dir)

    return [
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            str(artifact),
        ],
        [
            str(python),
            "-c",
            "import arancel_mx; print(arancel_mx.__version__)",
        ],
        [str(python), "-m", "arancel_mx", "--help"],
        [str(console_script), "--help"],
        [
            str(python),
            "-c",
            (
                "from importlib.resources import files; "
                "assert files('arancel_mx').joinpath("
                "'sources/source_registry.json').is_file()"
            ),
        ],
    ]


def _clean_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install and smoke-test one built arancel-mx distribution.",
    )
    parser.add_argument(
        "distribution",
        type=Path,
        help="Path to a built wheel or source distribution.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    distribution = args.distribution.resolve()

    if not distribution.is_file():
        raise SystemExit(f"distribution does not exist: {distribution}")

    checkout = Path.cwd().resolve()
    with tempfile.TemporaryDirectory(prefix="arancel-mx-install-") as temp_dir:
        temp_root = Path(temp_dir).resolve()
        external_cwd = temp_root / "consumer"
        venv_dir = temp_root / "venv"
        external_cwd.mkdir()

        if temp_root.is_relative_to(checkout):
            raise RuntimeError(
                "clean-install certification temporary directory is inside checkout"
            )

        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        env = _clean_environment()
        for command in smoke_commands(distribution, venv_dir):
            subprocess.run(command, check=True, cwd=external_cwd, env=env)

    return 0


if __name__ == "__main__":
    sys.exit(main())
