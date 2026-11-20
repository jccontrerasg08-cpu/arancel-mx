from __future__ import annotations

from pathlib import Path
import re

from arancel_mx.api.app import _MARKETING_PAGES, _MOVED_PAGES


def test_the_moa_guide_and_product_aliases_redirect_to_the_pages_that_replaced_them() -> None:
    assert "/moa" in _MARKETING_PAGES and "/app" not in _MOVED_PAGES
    assert _MOVED_PAGES["/moa-guide"] == "/moa"
    assert _MOVED_PAGES["/product"] == "/app"
    assert not {"/moa-guide", "/product"} & set(_MARKETING_PAGES), "an alias is a redirect, not a page"


def test_the_alias_redirects_match_the_frontend_route_manifest() -> None:
    routes = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "routes.js").read_text(encoding="utf-8")
    block = routes.split("export const ROUTE_ALIASES = Object.freeze({", 1)[1].split("})", 1)[0]
    declared = dict(re.findall(r"'(/[^']+)': '(/[^']+)'", block))

    assert declared == {"/product": "/app", "/moa-guide": "/moa"}
    assert {old: new for old, new in _MOVED_PAGES.items() if old in declared} == declared


def test_marketing_routes_include_the_figures_page() -> None:
    assert "/data" in _MARKETING_PAGES
