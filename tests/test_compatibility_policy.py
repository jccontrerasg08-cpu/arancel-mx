from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_compatibility_policy_states_verified_python_window_and_public_surfaces() -> None:
    text = _text("docs/compatibility.md")

    for token in (
        "CPython 3.11–3.13",
        "requires-python = \">=3.11\"",
        "CLI",
        "arancel_mx",
        "`/v1`",
        "no clasifica mercancías",
    ):
        assert token in text


def test_compatibility_policy_requires_announced_deprecation_with_a_replacement() -> None:
    text = _text("docs/compatibility.md")

    for token in (
        "DeprecationWarning",
        "reemplazo",
        "versión objetivo de retirada",
        "CHANGELOG.md",
        "PEP 387",
    ):
        assert token in text


def test_contribution_and_docs_hubs_link_to_the_compatibility_policy() -> None:
    assert "docs/compatibility.md" in _text("CONTRIBUTING.md")
    assert "compatibility.md" in _text("docs/README.md")
