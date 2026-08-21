from __future__ import annotations

from arancel_mx.api.app import _MARKETING_PAGES


def test_marketing_routes_include_the_public_moa_guide_alias() -> None:
    assert "/moa" in _MARKETING_PAGES
    assert "/moa-guide" in _MARKETING_PAGES
