from __future__ import annotations

from dataclasses import FrozenInstanceError
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from arancel_mx.consumer.wco_support import (
    DISCLAIMER,
    WCO_HS2022_BASE,
    WcoCite,
    WcoSupportError,
    cache_root,
    chapter_pdf_url,
    cite_chapter,
    download_chapter,
    download_gir,
    gir_pdf_url,
    local_chapter_pdf,
    local_gir_pdf,
)

FAKE_PDF = b"%PDF-1.4\nfake wco chapter\n"
_REPO = Path(__file__).resolve().parents[2]
_MODULE = _REPO / "src" / "arancel_mx" / "consumer" / "wco_support.py"
_REGISTRY = _REPO / "src" / "arancel_mx" / "sources" / "source_registry.json"


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _install_body(monkeypatch: pytest.MonkeyPatch, body: bytes) -> list[tuple[str, float | None]]:
    calls: list[tuple[str, float | None]] = []

    def fake_urlopen(url: str, timeout: float | None = None) -> _FakeResponse:
        calls.append((url, timeout))
        return _FakeResponse(body)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return calls


def _forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("network request attempted")

    monkeypatch.setattr("urllib.request.urlopen", boom)


def test_chapter_pdf_url_normalizes_and_uses_frozen_base() -> None:
    expected = (
        "https://www.wcoomd.org/-/media/wco/public/global/pdf/"
        "topics/nomenclature/instruments-and-tools/hs-nomenclature-2022/2022"
    )
    assert WCO_HS2022_BASE == expected
    assert chapter_pdf_url(1) == f"{WCO_HS2022_BASE}/01_2022e.pdf"
    assert chapter_pdf_url("01") == f"{WCO_HS2022_BASE}/01_2022e.pdf"
    assert chapter_pdf_url("61") == f"{WCO_HS2022_BASE}/61_2022e.pdf"
    assert gir_pdf_url() == f"{WCO_HS2022_BASE}/0001_2022e-gir.pdf"


@pytest.mark.parametrize("chapter", ["", "0", "00", "98", "99", "ab", "1.5", "100"])
def test_invalid_chapter_raises_value_error(chapter: str) -> None:
    with pytest.raises(ValueError):
        chapter_pdf_url(chapter)


def test_cache_root_nests_under_consumer_cache(tmp_path: Path) -> None:
    assert cache_root(tmp_path) == tmp_path / "wco-support" / "hs-2022"


def test_cache_root_default_uses_resolve_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ARANCEL_MX_CACHE_DIR", str(tmp_path / "env-cache"))
    assert cache_root() == tmp_path / "env-cache" / "wco-support" / "hs-2022"


def test_local_pdfs_are_none_when_missing_and_never_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _forbid_network(monkeypatch)
    assert local_chapter_pdf("61", cache_dir=tmp_path) is None
    assert local_gir_pdf(cache_dir=tmp_path) is None


def test_local_pdfs_return_existing_files_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _forbid_network(monkeypatch)
    chapter = cache_root(tmp_path) / "61_2022e.pdf"
    gir = cache_root(tmp_path) / "0001_2022e-gir.pdf"
    chapter.parent.mkdir(parents=True)
    chapter.write_bytes(FAKE_PDF)
    gir.write_bytes(FAKE_PDF)

    assert local_chapter_pdf("61", cache_dir=tmp_path) == chapter
    assert local_gir_pdf(cache_dir=tmp_path) == gir


def test_cite_chapter_is_support_only_and_skips_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _forbid_network(monkeypatch)
    cite = cite_chapter("1", cache_dir=tmp_path)
    assert cite.kind == "chapter"
    assert cite.chapter == "01"
    assert cite.url == chapter_pdf_url("01")
    assert cite.local_path is None
    assert cite.disclaimer == DISCLAIMER
    assert "support only" in DISCLAIMER
    assert "Not LIGIE/NICO legal identity" in DISCLAIMER
    assert "legally grounded" not in DISCLAIMER.lower()

    path = cache_root(tmp_path) / "01_2022e.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(FAKE_PDF)
    cached = cite_chapter("01", cache_dir=tmp_path)
    assert cached.local_path == str(path)


def test_wco_cite_is_frozen() -> None:
    cite = WcoCite(
        chapter="61",
        kind="chapter",
        url=chapter_pdf_url("61"),
        local_path=None,
        disclaimer=DISCLAIMER,
    )
    with pytest.raises(FrozenInstanceError):
        cite.url = "https://example.invalid"  # type: ignore[misc]


def test_download_chapter_writes_pdf_via_temp_replace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = _install_body(monkeypatch, FAKE_PDF)
    path = download_chapter("61", cache_dir=tmp_path, timeout=12)

    assert path == cache_root(tmp_path) / "61_2022e.pdf"
    assert path.read_bytes() == FAKE_PDF
    assert calls == [(chapter_pdf_url("61"), 12)]
    assert list(path.parent.glob("*.part")) == []
    assert local_chapter_pdf("61", cache_dir=tmp_path) == path


def test_download_gir_happy_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = _install_body(monkeypatch, FAKE_PDF)
    path = download_gir(cache_dir=tmp_path, timeout=9)

    assert path == cache_root(tmp_path) / "0001_2022e-gir.pdf"
    assert path.read_bytes() == FAKE_PDF
    assert calls == [(gir_pdf_url(), 9)]


def test_download_uses_cache_hit_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dest = cache_root(tmp_path) / "61_2022e.pdf"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(FAKE_PDF)
    _forbid_network(monkeypatch)

    assert download_chapter("61", cache_dir=tmp_path) == dest
    assert download_chapter("61", cache_dir=tmp_path, offline=True) == dest


def test_download_http_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(url: str, timeout: float | None = None) -> object:
        raise HTTPError(url, 404, "Not Found", hdrs=None, fp=BytesIO())

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(WcoSupportError, match="failed to download"):
        download_chapter("61", cache_dir=tmp_path)
    assert local_chapter_pdf("61", cache_dir=tmp_path) is None


def test_download_url_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def boom(url: str, timeout: float | None = None) -> object:
        raise URLError("dns")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(WcoSupportError, match="failed to download"):
        download_gir(cache_dir=tmp_path)


@pytest.mark.parametrize("body", [b"", b"<!DOCTYPE html>"])
def test_download_rejects_empty_and_non_pdf(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, body: bytes
) -> None:
    _install_body(monkeypatch, body)
    with pytest.raises(WcoSupportError):
        download_chapter("61", cache_dir=tmp_path)
    root = cache_root(tmp_path)
    assert not (root / "61_2022e.pdf").exists()
    if root.exists():
        assert list(root.glob("*.part")) == []


def test_offline_missing_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _forbid_network(monkeypatch)
    with pytest.raises(WcoSupportError, match="offline"):
        download_chapter("61", cache_dir=tmp_path, offline=True)
    with pytest.raises(WcoSupportError, match="offline"):
        download_gir(cache_dir=tmp_path, offline=True)


def test_registry_still_excludes_wcoomd() -> None:
    text = _REGISTRY.read_text(encoding="utf-8").lower()
    assert "wcoomd.org" not in text


def test_wco_support_does_not_import_sources() -> None:
    text = _MODULE.read_text(encoding="utf-8")
    assert "arancel_mx.sources" not in text
    assert "dspy" not in text.lower()
    assert "openai" not in text.lower()
