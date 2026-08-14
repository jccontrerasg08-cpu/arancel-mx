from __future__ import annotations

from pathlib import Path

import pytest

from arancel_mx.cli import main
from arancel_mx.consumer.wco_support import cache_root, chapter_pdf_url, gir_pdf_url


FAKE_PDF = b"%PDF-1.4\nfake wco chapter\n"


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("network request attempted")

    monkeypatch.setattr("urllib.request.urlopen", boom)


def _isolate_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    cache_dir = tmp_path / "cache"
    monkeypatch.setenv("ARANCEL_MX_CACHE_DIR", str(cache_dir))
    return cache_dir


def test_wco_cite_01_prints_url_and_does_not_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    _isolate_cache(monkeypatch, tmp_path)
    _forbid_network(monkeypatch)

    assert main(["wco", "cite", "01"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "01_2022e.pdf" in captured.out
    assert chapter_pdf_url("01") in captured.out
    assert "WCO support" in captured.out
    assert "(none)" in captured.out


def test_wco_cite_gir_prints_gir_filename(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    _isolate_cache(monkeypatch, tmp_path)
    _forbid_network(monkeypatch)

    assert main(["wco", "cite", "gir"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "0001_2022e-gir.pdf" in captured.out
    assert gir_pdf_url() in captured.out


def test_wco_download_offline_empty_cache_is_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    _isolate_cache(monkeypatch, tmp_path)
    _forbid_network(monkeypatch)

    result = main(["wco", "download", "01", "--offline"])
    captured = capsys.readouterr()
    assert result == 2
    assert captured.err.startswith("error:")
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_wco_download_then_cite_shows_cache_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    cache_dir = _isolate_cache(monkeypatch, tmp_path)

    def fake_urlopen(url: str, timeout: float | None = None) -> _FakeResponse:
        return _FakeResponse(FAKE_PDF)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert main(["wco", "download", "01"]) == 0
    capsys.readouterr()

    _forbid_network(monkeypatch)
    assert main(["wco", "cite", "01"]) == 0
    out = capsys.readouterr().out
    cached = cache_root(cache_dir) / "01_2022e.pdf"
    assert str(cached) in out
    assert "WCO cache" in out
    cache_line = next(line for line in out.splitlines() if line.startswith("WCO cache"))
    assert "(none)" not in cache_line


@pytest.mark.parametrize("target", ["99", "0"])
def test_wco_cite_invalid_chapter_is_public_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys, target: str
) -> None:
    _isolate_cache(monkeypatch, tmp_path)
    _forbid_network(monkeypatch)

    result = main(["wco", "cite", target])
    captured = capsys.readouterr()
    assert result == 2
    assert captured.err.startswith("error:")
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_wco_help_is_spanish_support_not_authority(capsys) -> None:
    assert main(["wco", "--help"]) == 0
    text = capsys.readouterr().out.lower()
    assert "apoyo" in text
    assert "ligie" in text
    assert "autoridad" in text or "no autoridad" in text
