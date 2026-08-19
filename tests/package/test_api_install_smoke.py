from __future__ import annotations

from pathlib import Path

from scripts.certify_package_install import smoke_commands


def test_clean_install_smoke_imports_fastapi_entrypoint_without_startup(tmp_path: Path) -> None:
    commands = smoke_commands(tmp_path / "arancel_mx-0.3.4.whl", tmp_path / "venv")
    python_snippets = [
        command[2]
        for command in commands
        if len(command) >= 3 and command[1] == "-c"
    ]

    assert any(
        "from arancel_mx.api.app import app" in snippet
        and "app.title == 'Arancel MX API'" in snippet
        for snippet in python_snippets
    )
