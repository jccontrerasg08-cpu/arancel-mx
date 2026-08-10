"""One-command local runner for any terminal."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(cmd: list[str], **kwargs) -> None:
    subprocess.check_call(cmd, cwd=ROOT, **kwargs)


def ensure_venv() -> None:
    if not PY.exists():
        print("Creating .venv...")
        venv.EnvBuilder(with_pip=True).create(VENV)


def bootstrap(no_install: bool) -> None:
    ensure_venv()
    if not no_install:
        print("Installing requirements...")
        run([str(PY), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(PY), "-m", "pip", "install", "-r", "requirements.txt"])
    print("Preparing DuckDB...")
    run([str(PY), "comex.py", "init-db"])
    if (ROOT / "data" / "comercio_exterior.json").exists():
        run([str(PY), "comex.py", "warehouse-refresh"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Comex dashboard locally")
    parser.add_argument("--port", default=os.environ.get("PORT", "8050"))
    parser.add_argument("--no-install", action="store_true", help="Skip pip install when .venv is already ready")
    args = parser.parse_args(argv)

    bootstrap(args.no_install)
    env = {**os.environ, "PORT": str(args.port)}
    print(f"\nDashboard: http://127.0.0.1:{args.port}\nPress Ctrl+C to stop.\n")
    return subprocess.call([str(PY), "app.py"], cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
