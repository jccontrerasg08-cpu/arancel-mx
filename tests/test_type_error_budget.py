from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_type_error_budget.py"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_type_error_budget_is_explicit_and_tracks_only_current_debt() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    budget = config.get("tool", {}).get("arancel_mx", {}).get("type_error_budget")

    assert budget == {"arg-type": 33, "attr-defined": 3}


def test_type_error_budget_rejects_growth_from_saved_mypy_output(tmp_path: Path) -> None:
    output = tmp_path / "mypy.txt"
    output.write_text(
        "src/example.py:1: error: unexpected type [arg-type]\n" * 34,
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, str(CHECKER), "--mypy-output", str(output)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "arg-type: 34 > 33" in completed.stdout


def test_ci_enforces_the_strict_type_error_budget_after_mypy() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "python -m mypy src/arancel_mx" in workflow
    assert "python -m scripts.check_type_error_budget" in workflow
    assert workflow.index("python -m mypy src/arancel_mx") < workflow.index(
        "python -m scripts.check_type_error_budget"
    )


def test_type_error_budget_does_not_accept_an_arbitrary_mypy_target() -> None:
    completed = subprocess.run(
        [sys.executable, str(CHECKER), "--target", "outside-the-package"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "unrecognized arguments" in completed.stderr
