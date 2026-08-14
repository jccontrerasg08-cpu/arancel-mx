"""Optional WCO HS 2022 PDF support cache. Support only — not LIGIE/NICO identity."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import Literal
import urllib.error
import urllib.request

from arancel_mx.consumer.config import resolve_config

WCO_HS2022_BASE = (
    "https://www.wcoomd.org/-/media/wco/public/global/pdf/"
    "topics/nomenclature/instruments-and-tools/hs-nomenclature-2022/2022"
)
DISCLAIMER = (
    "WCO HS 2022 PDF is support only. Not LIGIE/NICO legal identity. "
    "Copyright remains with the WCO."
)
_GIR_NAME = "0001_2022e-gir.pdf"


class WcoSupportError(Exception):
    """Raised when a WCO support PDF is missing offline or fails download checks."""


@dataclass(frozen=True, slots=True)
class WcoCite:
    chapter: str | None
    kind: Literal["chapter", "gir"]
    url: str
    local_path: str | None
    disclaimer: str


def _normalize_chapter(chapter: str | int) -> str:
    if isinstance(chapter, bool) or not isinstance(chapter, (str, int)):
        raise ValueError(f"invalid HS chapter: {chapter!r}")
    text = str(chapter).strip()
    if not text.isdigit():
        raise ValueError(f"invalid HS chapter: {chapter!r}")
    number = int(text)
    if number < 1 or number > 97:
        raise ValueError(f"invalid HS chapter: {chapter!r}")
    return f"{number:02d}"


def chapter_pdf_url(chapter: str) -> str:
    return f"{WCO_HS2022_BASE}/{_normalize_chapter(chapter)}_2022e.pdf"


def gir_pdf_url() -> str:
    return f"{WCO_HS2022_BASE}/{_GIR_NAME}"


def cache_root(cache_dir: Path | None = None) -> Path:
    root = Path(cache_dir) if cache_dir is not None else resolve_config().cache_dir
    return root / "wco-support" / "hs-2022"


def _chapter_dest(chapter: str, cache_dir: Path | None) -> Path:
    code = _normalize_chapter(chapter)
    return cache_root(cache_dir) / f"{code}_2022e.pdf"


def local_chapter_pdf(chapter: str, *, cache_dir: Path | None = None) -> Path | None:
    path = _chapter_dest(chapter, cache_dir)
    return path if path.is_file() else None


def local_gir_pdf(*, cache_dir: Path | None = None) -> Path | None:
    path = cache_root(cache_dir) / _GIR_NAME
    return path if path.is_file() else None


def cite_chapter(chapter: str, *, cache_dir: Path | None = None) -> WcoCite:
    code = _normalize_chapter(chapter)
    local = local_chapter_pdf(code, cache_dir=cache_dir)
    return WcoCite(
        chapter=code,
        kind="chapter",
        url=chapter_pdf_url(code),
        local_path=None if local is None else str(local),
        disclaimer=DISCLAIMER,
    )


def _download(url: str, dest: Path, *, timeout: float, offline: bool) -> Path:
    if dest.is_file():
        return dest
    if offline:
        raise WcoSupportError(f"WCO HS 2022 PDF is not cached and offline=True: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WcoSupportError(f"failed to download WCO HS 2022 PDF: {url}") from exc
    if not body:
        raise WcoSupportError(f"WCO HS 2022 PDF response was empty: {url}")
    if not body.startswith(b"%PDF"):
        raise WcoSupportError(f"WCO HS 2022 response is not a PDF: {url}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".wco-", suffix=".part", dir=dest.parent, delete=False
        ) as handle:
            handle.write(body)
            temporary = Path(handle.name)
        os.replace(temporary, dest)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise WcoSupportError(f"failed to store WCO HS 2022 PDF: {dest}") from exc
    return dest


def download_chapter(
    chapter: str,
    *,
    cache_dir: Path | None = None,
    timeout: float = 30,
    offline: bool = False,
) -> Path:
    code = _normalize_chapter(chapter)
    return _download(
        chapter_pdf_url(code),
        _chapter_dest(code, cache_dir),
        timeout=timeout,
        offline=offline,
    )


def download_gir(
    *,
    cache_dir: Path | None = None,
    timeout: float = 30,
    offline: bool = False,
) -> Path:
    return _download(
        gir_pdf_url(),
        cache_root(cache_dir) / _GIR_NAME,
        timeout=timeout,
        offline=offline,
    )
