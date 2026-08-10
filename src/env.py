"""Tiny .env loader for local entrypoints."""

from __future__ import annotations

import os
from pathlib import Path


def load_env(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        key, raw = clean.split("=", 1)
        os.environ.setdefault(key.strip(), raw.strip().strip('"').strip("'"))
