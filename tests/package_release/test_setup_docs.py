from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETUP_DOC = ROOT / "docs" / "testpypi-pypi-setup.md"


def test_setup_checklist_exists() -> None:
    assert SETUP_DOC.is_file()


def test_setup_checklist_covers_required_prerequisites() -> None:
    text = SETUP_DOC.read_text(encoding="utf-8").lower()
    required = (
        "testpypi",
        "pypi",
        "trusted publish",
        "environment",
        "required reviewer",
        "pkg-v",
        "no long-lived",
    )
    assert [item for item in required if item not in text] == []


def test_setup_checklist_names_the_publish_workflow() -> None:
    text = SETUP_DOC.read_text(encoding="utf-8")
    assert "publish-python-package.yml" in text
