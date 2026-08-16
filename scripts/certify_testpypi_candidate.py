"""Install and certify a TestPyPI candidate from an independent CI runner.

The TestPyPI Simple index may reach independent GitHub-hosted runners at
slightly different times. This helper retries only the candidate installation
from TestPyPI on the runner that will execute the certification, then installs
its declared runtime dependencies from PyPI. It never imports the repository
checkout and never permits TestPyPI to resolve unrelated dependencies.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from importlib import metadata
import subprocess
import sys
import time


Run = Callable[..., object]
Sleep = Callable[[float], object]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retry a TestPyPI candidate installation, then certify dependencies from PyPI.",
    )
    parser.add_argument("expected_version")
    parser.add_argument("--attempts", type=int, default=40)
    parser.add_argument("--delay-seconds", type=float, default=15.0)
    args = parser.parse_args(argv)
    if args.attempts < 1:
        parser.error("--attempts must be at least 1")
    if args.delay_seconds < 0:
        parser.error("--delay-seconds must be non-negative")
    return args


def _candidate_install_command(expected_version: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-deps",
        "--no-cache-dir",
        "--index-url",
        "https://test.pypi.org/simple/",
        f"arancel-mx=={expected_version}",
    ]


def install_candidate_with_retry(
    *,
    expected_version: str,
    attempts: int,
    delay_seconds: float,
    run: Run = subprocess.run,
    sleep: Sleep = time.sleep,
) -> None:
    """Install the exact candidate after bounded per-runner index propagation retries."""
    command = _candidate_install_command(expected_version)
    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(1, attempts + 1):
        try:
            run(command, check=True)  # noqa: S603 - fixed interpreter and package-index arguments.
        except subprocess.CalledProcessError as error:
            last_error = error
            if attempt == attempts:
                raise
            print(
                f"TestPyPI candidate arancel-mx=={expected_version} is not yet "
                f"available to this runner (attempt {attempt}/{attempts}); retrying.",
                flush=True,
            )
            sleep(delay_seconds)
        else:
            print(
                f"TestPyPI candidate arancel-mx=={expected_version} is available "
                f"to this runner on attempt {attempt}/{attempts}.",
                flush=True,
            )
            return
    if last_error is None:
        raise RuntimeError("candidate retry loop ended without an installation result")
    raise last_error


def install_runtime_dependencies_from_pypi(*, run: Run = subprocess.run) -> None:
    """Resolve only the installed candidate's declared runtime dependencies from PyPI."""
    requirements = metadata.requires("arancel-mx") or []
    if requirements:
        run(  # noqa: S603 - fixed interpreter and trusted installed metadata arguments.
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--index-url",
                "https://pypi.org/simple/",
                *requirements,
            ],
            check=True,
        )
    run(  # noqa: S603 - fixed interpreter and no shell.
        [sys.executable, "-m", "pip", "check"],
        check=True,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    install_candidate_with_retry(
        expected_version=args.expected_version,
        attempts=args.attempts,
        delay_seconds=args.delay_seconds,
    )
    install_runtime_dependencies_from_pypi()
    return 0


if __name__ == "__main__":
    sys.exit(main())
