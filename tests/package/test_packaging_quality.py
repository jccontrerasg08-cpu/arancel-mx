from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tomllib


def _project() -> dict[str, object]:
    return tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_quality_tools_are_pinned_for_reproducible_ci() -> None:
    constraints = Path("requirements/production-build.txt").read_text(encoding="utf-8")
    assert "twine==6.2.0" in constraints
    assert "check-wheel-contents==0.6.3" in constraints

    dev = "\n".join(_project()["optional-dependencies"]["dev"])
    assert "twine" in dev
    assert "check-wheel-contents" in dev


def test_built_distributions_pass_twine_and_wheel_quality_checks(tmp_path: Path) -> None:
    out = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(out)],
        check=True,
        capture_output=True,
        text=True,
    )
    artifacts = sorted(out.glob("arancel_mx-*"))
    wheel = next(path for path in artifacts if path.suffix == ".whl")

    twine = subprocess.run(
        [sys.executable, "-m", "twine", "check", *map(str, artifacts)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert twine.returncode == 0, twine.stdout + twine.stderr

    checker = shutil.which("check-wheel-contents")
    assert checker is not None
    contents = subprocess.run(
        [checker, str(wheel)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert contents.returncode == 0, contents.stdout + contents.stderr
