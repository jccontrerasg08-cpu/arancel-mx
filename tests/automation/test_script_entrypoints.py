from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = (
    "fetch_previous_release.py",
    "publish_release.py",
    "data_alert.py",
)
MODULES = tuple(f"scripts.{name.removesuffix('.py')}" for name in SCRIPTS)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args, "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_github_aware_scripts_work_as_direct_script_entrypoints():
    for script in SCRIPTS:
        result = _run(str(Path("scripts") / script))
        assert result.returncode == 0, (script, result.stdout, result.stderr)


def test_github_aware_scripts_work_as_repo_modules():
    for module in MODULES:
        result = _run("-m", module)
        assert result.returncode == 0, (module, result.stdout, result.stderr)
