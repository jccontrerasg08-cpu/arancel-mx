"""Runtime bootstrap helpers for Vercel's repository-root Python Functions."""

from __future__ import annotations

from pathlib import Path
import sys


def ensure_project_source() -> None:
    """Make the src-layout package importable from a bundled Vercel Function."""

    source_directory = Path(__file__).resolve().parents[1] / "src"
    source_path = str(source_directory)
    if source_directory.is_dir() and source_path not in sys.path:
        sys.path.insert(0, source_path)
