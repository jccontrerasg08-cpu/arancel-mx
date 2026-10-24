"""Imports quoted in workflows and docs must resolve against the package.

Workflow heredocs and documentation examples are not executed by the suite, so
an internal reorganization can break them silently (this happened to the
publisher's ``certify_bundle`` import after the subpackage re-exports were
removed).
"""

from __future__ import annotations

import importlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
IMPORT = re.compile(r"from (arancel_mx(?:\.\w+)*) import \(?([\w ,\n]+)")


def _referenced_imports() -> list[tuple[str, str, str]]:
    sources = [
        *sorted((ROOT / ".github" / "workflows").glob("*.yml")),
        *sorted((ROOT / "docs").rglob("*.md")),
        ROOT / "README.md",
        ROOT / "README.en.md",
    ]
    found = []
    for path in sources:
        for match in IMPORT.finditer(path.read_text(encoding="utf-8")):
            for name in match.group(2).split(","):
                if name.strip():
                    found.append((path.relative_to(ROOT).as_posix(), match.group(1), name.split()[0]))
    return found


def test_imports_quoted_in_workflows_and_docs_resolve() -> None:
    references = _referenced_imports()
    assert any(path.startswith(".github/workflows/") for path, _, _ in references)
    broken = []
    for path, module_name, name in references:
        module = importlib.import_module(module_name)
        if not hasattr(module, name):
            try:
                importlib.import_module(f"{module_name}.{name}")
            except ImportError:
                broken.append(f"{path}: from {module_name} import {name}")
    assert broken == []
