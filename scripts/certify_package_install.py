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

    heavy_probe = (
        "import importlib.util; "
        "blocked=('pandas','openpyxl','xlrd','fitz','pymupdf'); "
        "found=[name for name in blocked if importlib.util.find_spec(name) is not None]; "
        "assert not found, f'maintainer dependencies leaked into base install: {found}'"
    )

    return [
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            str(artifact),
        ],
        [str(python), "-m", "pip", "check"],
        [
            str(python),
            "-c",
            "import arancel_mx; print(arancel_mx.__version__)",
        ],
        [
            str(python),
            "-c",
            "from arancel_mx.api.app import app; assert app.title == 'Arancel MX API'",
        ],
        [str(python), "-m", "arancel_mx", "--help"],
        [str(console_script), "--help"],
        [
            str(python),
            "-c",
            (
                "from importlib.resources import files; "
                "assert files('arancel_mx').joinpath("
                "'sources/source_registry.json').is_file(); "
                "assert files('arancel_mx').joinpath('py.typed').is_file()"
            ),
        ],
        [str(python), "-c", heavy_probe],
    ]


def _clean_environment(home: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    if home is not None:
        home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(home)
        if os.name == "nt":
            env["USERPROFILE"] = str(home)
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
    parser.add_argument(
        "--expected-version",
        help="Expected installed arancel-mx version for the standalone probe.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        help="Optional local DuckDB fixture for a read-only consumer query probe.",
    )
    args = parser.parse_args(argv)
    if args.dataset is not None and not args.expected_version:
        parser.error("--dataset requires --expected-version so the consumer probe runs")
    return args


def _probe_command(
    python: Path,
    *,
    checkout: Path,
    expected_version: str,
    dataset: Path | None,
) -> list[str]:
    probe = checkout / "scripts" / "package_consumer_probe.py"
    command = [
        str(python),
        str(probe),
        "--expected-version",
        expected_version,
        "--forbid-root",
        str(checkout),
    ]
    if dataset is not None:
        command.extend(["--dataset", str(dataset.resolve())])
    return command


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    distribution = args.distribution.resolve()

    if not distribution.is_file():
        raise SystemExit(f"distribution does not exist: {distribution}")
    if args.dataset is not None and not args.dataset.resolve().is_file():
        raise SystemExit(f"dataset does not exist: {args.dataset.resolve()}")

    checkout = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="arancel-mx-install-") as temp_dir:
        temp_root = Path(temp_dir).resolve()
        external_cwd = temp_root / "external consumer ñ"
        venv_dir = temp_root / "venv"
        external_home = temp_root / "home with spaces ñ"
        external_cwd.mkdir()

        if temp_root.is_relative_to(checkout):
            raise RuntimeError(
                "clean-install certification temporary directory is inside checkout"
            )

        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        env = _clean_environment(external_home)
        for command in smoke_commands(distribution, venv_dir):
            subprocess.run(  # noqa: S603 - commands use the isolated venv and a verified local artifact.
                command,
                check=True,
                cwd=external_cwd,
                env=env,
            )

        if args.expected_version is not None:
            subprocess.run(  # noqa: S603 - probe path is repository-local and arguments are validated above.
                _probe_command(
                    _venv_python(venv_dir),
                    checkout=checkout,
                    expected_version=args.expected_version,
                    dataset=args.dataset,
                ),
                check=True,
                cwd=external_cwd,
                env=env,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
