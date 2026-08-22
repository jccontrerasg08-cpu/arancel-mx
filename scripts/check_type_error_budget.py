"""Prevent strict mypy debt from increasing beyond the reviewed baseline."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Final


ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_TARGET: Final = "src/arancel_mx"
ERROR_CODE_PATTERN: Final = re.compile(r"\[([a-z-]+)\]")


def load_type_error_budget(path: Path = ROOT / "pyproject.toml") -> dict[str, int]:
    """Return the reviewed maximum count for each temporarily disabled error code."""
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    raw_budget = config["tool"]["arancel_mx"]["type_error_budget"]
    if not isinstance(raw_budget, dict) or not raw_budget:
        raise ValueError("[tool.arancel_mx.type_error_budget] must declare at least one error code")
    budget: dict[str, int] = {}
    for code, limit in raw_budget.items():
        if not isinstance(code, str) or not isinstance(limit, int) or limit < 0:
            raise ValueError("type-error budget entries must map error-code strings to non-negative integers")
        budget[code] = limit
    return budget


def count_budgeted_errors(output: str, budget: dict[str, int]) -> dict[str, int]:
    """Count only configured mypy error codes from command output."""
    counts = Counter(ERROR_CODE_PATTERN.findall(output))
    return {code: counts[code] for code in budget}


def budget_violations(counts: dict[str, int], budget: dict[str, int]) -> tuple[str, ...]:
    """Return deterministic messages for type-error codes exceeding their baseline."""
    return tuple(
        f"{code}: {counts.get(code, 0)} > {limit}"
        for code, limit in sorted(budget.items())
        if counts.get(code, 0) > limit
    )


def run_mypy() -> tuple[int, str]:
    """Run strict debt reporting against the fixed package boundary."""
    completed = subprocess.run(  # noqa: S603 - executable and arguments are fixed CI values.
        [
            sys.executable,
            "-m",
            "mypy",
            "--enable-error-code",
            "arg-type",
            "--enable-error-code",
            "attr-defined",
            DEFAULT_TARGET,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout + completed.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mypy-output",
        type=Path,
        help="Read a saved mypy output file instead of invoking mypy.",
    )
    args = parser.parse_args()

    budget = load_type_error_budget()
    if args.mypy_output is not None:
        output = args.mypy_output.read_text(encoding="utf-8")
    else:
        return_code, output = run_mypy()
        if return_code not in {0, 1}:
            print(output, end="")
            return return_code

    counts = count_budgeted_errors(output, budget)
    violations = budget_violations(counts, budget)
    print("Mypy strict-debt budget:")
    for code, limit in sorted(budget.items()):
        print(f"  {code}: {counts[code]} / {limit}")
    if violations:
        print("Type-error budget exceeded:")
        for violation in violations:
            print(f"  {violation}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
