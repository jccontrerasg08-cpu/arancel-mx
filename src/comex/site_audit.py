"""Passive website audit helpers."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests


SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "Cross-Origin-Opener-Policy",
    "Content-Security-Policy",
]


class _EndpointParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.endpoints: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        field = {"a": "href", "form": "action", "script": "src", "link": "href"}.get(tag)
        value = attrs_dict.get(field or "")
        if value:
            self.endpoints.add(urljoin(self.base_url, value))


def _same_host(url: str, host: str) -> bool:
    return urlparse(url).netloc == host


def _clean_url(url: str) -> str:
    return urlparse(url)._replace(fragment="", query="").geturl()


def fetch_page(url: str, timeout: int = 10) -> tuple[requests.Response, str]:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "comex-passive-audit/1.0"})
    return response, response.text


def extract_endpoints(url: str, html: str) -> list[str]:
    parser = _EndpointParser(url)
    parser.feed(html)
    host = urlparse(url).netloc
    return sorted({_clean_url(item) for item in parser.endpoints if _same_host(item, host)})


def analyze_js(text: str) -> dict:
    paths = sorted(set(re.findall(r"""["'](/[A-Za-z0-9_./?=&%-]+)["']""", text)))[:80]
    urls = sorted(set(re.findall(r"""https?://[^\s"'<>`]+""", text)))[:80]
    keywords = sorted({word for word in ["api", "firebase", "firestore", "pdf", "render", "token"] if word in text.lower()})
    return {"paths": paths, "urls": urls, "keywords": keywords}


def audit_site(url: str, timeout: int = 10) -> dict:
    response, html = fetch_page(url, timeout)
    endpoints = extract_endpoints(url, html)
    scripts = [item for item in endpoints if item.endswith(".js")]
    script_findings = {}
    for script_url in scripts[:5]:
        try:
            script_findings[script_url] = analyze_js(fetch_page(script_url, timeout)[1])
        except requests.RequestException as exc:
            script_findings[script_url] = {"error": str(exc)}

    headers = dict(response.headers)
    missing_headers = [name for name in SECURITY_HEADERS if name not in headers]
    return {
        "url": url,
        "status_code": response.status_code,
        "headers": headers,
        "missing_security_headers": missing_headers,
        "endpoints": endpoints,
        "scripts_analyzed": script_findings,
    }


def _self_check() -> None:
    html = '<a href="/app#x">app</a><form action="/sat/noms/search"></form><script src="/src/app.min.js"></script>'
    endpoints = extract_endpoints("https://eximfox.mx/app", html)
    assert "https://eximfox.mx/app" in endpoints
    assert "https://eximfox.mx/sat/noms/search" in endpoints
    assert analyze_js('fetch("/api/items"); const x="https://example.com/a";')["paths"] == ["/api/items"]


if __name__ == "__main__":
    _self_check()
