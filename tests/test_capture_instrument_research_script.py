from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path

import scripts.capture_instrument_research as capture_script
from arancel_mx.sources.http import FetchedDocument

FIXTURE = Path(__file__).parent / "fixtures" / "diputados" / "ligie_2022.html"
NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def _doc(url: str, content: bytes, media_type: str) -> FetchedDocument:
    return FetchedDocument(url, url, media_type, content, NOW, "utf-8")


def _fetcher(pages: dict[str, tuple[bytes, str]], calls: list[str]):
    def fetch(url: str) -> FetchedDocument:
        calls.append(url)
        if url == capture_script.LEDGER_URL:
            return _doc(url, FIXTURE.read_bytes(), "text/html")
        if url in pages:
            content, media_type = pages[url]
            return _doc(url, content, media_type)
        if url.lower().endswith(".pdf"):
            return _doc(url, b"%PDF-1.7 " + url.encode(), "application/pdf")
        raise ValueError("official document media type is not allowed: text/plain")

    return fetch


def test_capture_downloads_ledger_links_with_hashes(tmp_path):
    calls: list[str] = []
    manifest = capture_script.run(
        tmp_path, _fetcher({}, calls), dof_dates=[], sidof_notes=[], max_documents=400
    )

    assert manifest["ledger"]["documents"], "fixture ledger must parse"
    ok = [r for r in manifest["documents"] if r["status"] == "ok"]
    assert len(ok) > 1
    for record in ok:
        stored = (tmp_path / record["path"]).read_bytes()
        assert hashlib.sha256(stored).hexdigest() == record["sha256"]
        assert record["url"].startswith("https://")
    sums = (tmp_path / "SHA256SUMS").read_text(encoding="utf-8")
    assert all(record["sha256"] in sums for record in ok)
    assert len(calls) == len(set(calls)), "each URL is fetched once"
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))[
        "counts"
    ]["ok"] == len(ok)


def test_capture_records_failures_and_off_host_links_without_aborting(tmp_path):
    def fetch(url: str) -> FetchedDocument:
        if url == capture_script.LEDGER_URL:
            return _doc(url, FIXTURE.read_bytes(), "text/html")
        raise ConnectionError("reset")

    manifest = capture_script.run(
        tmp_path, fetch, dof_dates=[], sidof_notes=["123"], max_documents=400
    )

    statuses = {r["status"] for r in manifest["documents"]}
    assert "error" in statuses
    assert all(
        r["status"] != "ok"
        for r in manifest["documents"]
        if r["url"] != capture_script.LEDGER_URL
    )


def test_capture_scans_dof_daily_index_for_tariff_instruments(tmp_path):
    index = "https://www.dof.gob.mx/index.php?year=2026&month=10&day=13&edicion=MAT"
    note = "https://www.dof.gob.mx/nota_detalle.php?codigo=1&fecha=13/10/2026"
    other = "https://www.dof.gob.mx/nota_detalle.php?codigo=2&fecha=13/10/2026"
    html = (
        f'<a href="{note}">DECRETO por el que se modifica la Tarifa de la Ley de los '
        f"Impuestos Generales de Importación y de Exportación.</a>"
        f'<a href="{other}">AVISO de convocatoria a la licitación pública</a>'
    ).encode()
    note_html = b'<a href="/nota_to_doc.php?codnota=1">Descargar</a>'
    calls: list[str] = []
    pages = {
        index: (html, "text/html"),
        note: (note_html, "text/html"),
        "https://www.dof.gob.mx/nota_to_doc.php?codnota=1": (
            b"doc",
            "application/msword",
        ),
    }

    def fetch(url: str) -> FetchedDocument:
        if url == capture_script.LEDGER_URL:
            raise ConnectionError("blocked")
        return _fetcher(pages, calls)(url)

    manifest = capture_script.run(
        tmp_path,
        fetch,
        dof_dates=[date(2026, 10, 13)],
        sidof_notes=[],
        max_documents=400,
    )

    assert [m["url"] for m in manifest["dof_matches"]] == [note]
    assert other not in calls
    assert "https://www.dof.gob.mx/nota_to_doc.php?codnota=1" in calls
    assert manifest["ledger"]["error"]


def test_capture_respects_document_limit(tmp_path):
    calls: list[str] = []
    manifest = capture_script.run(
        tmp_path, _fetcher({}, calls), dof_dates=[], sidof_notes=[], max_documents=2
    )
    assert manifest["counts"]["ok"] == 2
    assert manifest["counts"].get("skipped_limit", 0) >= 1


def test_main_returns_failure_when_ledger_unavailable(tmp_path, monkeypatch):
    def fake_fetch(session, url, *args, **kwargs):
        raise ConnectionError("blocked")

    monkeypatch.setattr(capture_script, "fetch_official_document", fake_fetch)
    assert capture_script.main(["--out", str(tmp_path)]) == 1
