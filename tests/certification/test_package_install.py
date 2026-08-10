from pathlib import Path

from scripts.certify_package_install import smoke_commands


def test_smoke_commands_cover_installed_package_surfaces(tmp_path: Path):
    commands = smoke_commands(
        Path("dist/arancel_mx-0.1.0-py3-none-any.whl"),
        tmp_path / "venv",
    )
    rendered = [" ".join(command) for command in commands]

    assert any("import arancel_mx" in item for item in rendered)
    assert any("-m arancel_mx --help" in item for item in rendered)
    assert any("arancel-mx" in item and "--help" in item for item in rendered)
    assert any("importlib.resources" in item and "source_registry.json" in item for item in rendered)
