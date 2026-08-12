from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from arancel_mx.pipeline import official_sources
from arancel_mx.pipeline.official_dataset import OfficialDatasetConfig
from arancel_mx.pipeline.official_sources import (
    capture_official_inputs,
    write_release_sources,
)
from arancel_mx.sources.legal_evidence import RequiredDofEvidence


DIPUTADOS_LEDGER = (
    Path(__file__).parents[1] / "fixtures" / "diputados" / "ligie_2022.html"
).read_text(encoding="utf-8")
DIPUTADOS_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"
DIPUTADOS_PDF = "https://www.diputados.gob.mx/LeyesBiblio/pdf/LIGIE_2022.pdf"
LAW_REFORM_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/reforma02.pdf"
TARIFF_DECREE_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/tarifa15.pdf"
LIGIE_INDEX = "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html"
NICO_INDEX = "https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html"
LIGIE_URL = "https://www.snice.gob.mx/files/FRACCIONESARANCELARIAS_20260810.XLSX"
NICO_URL = "https://www.snice.gob.mx/files/NICO-AGOSTO26-LIGIE_20260810-20260810.XLSX"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class Response:
    def __init__(self, url, content, content_type, text=None):
        self.url = url
        self.content = content
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(content)),
        }
        self._text = text

    @property
    def text(self):
        if self._text is not None:
            return self._text
        return self.content.decode("utf-8", errors="replace")

    def iter_content(self, chunk_size=1024 * 1024):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.requested = []

    def get(self, url, timeout=None, stream=False):
        self.requested.append((url, timeout))
        if url not in self.responses:
            raise AssertionError(f"unexpected network URL: {url}")
        return self.responses[url]


def fake_session():
    ligie_html = f'<a href="{LIGIE_URL}">Fracciones 20260810</a>'
    nico_html = f'<a href="{NICO_URL}">NICO 20260810</a>'
    responses = {
        DIPUTADOS_URL: Response(
            DIPUTADOS_URL,
            DIPUTADOS_LEDGER.encode("utf-8"),
            "text/html; charset=utf-8",
            DIPUTADOS_LEDGER,
        ),
        DIPUTADOS_PDF: Response(DIPUTADOS_PDF, b"%PDF-1.7\nfixture", "application/pdf"),
        LAW_REFORM_URL: Response(
            LAW_REFORM_URL, b"%PDF-1.7\nlaw-reform", "application/pdf"
        ),
        TARIFF_DECREE_URL: Response(
            TARIFF_DECREE_URL, b"%PDF-1.7\ntariff-decree", "application/pdf"
        ),
        LIGIE_INDEX: Response(
            LIGIE_INDEX, ligie_html.encode("utf-8"), "text/html", ligie_html
        ),
        NICO_INDEX: Response(
            NICO_INDEX, nico_html.encode("utf-8"), "text/html", nico_html
        ),
        LIGIE_URL: Response(LIGIE_URL, b"ligie-workbook", XLSX_TYPE),
        NICO_URL: Response(NICO_URL, b"nico-workbook", XLSX_TYPE),
    }
    return FakeSession(responses)


def config(tmp_path, *, timeout_s=60.0):
    return OfficialDatasetConfig(
        work_dir=tmp_path / "work",
        output_dir=tmp_path / "release",
        effective_as_of=date(2026, 8, 10),
        dataset_version="2026.08.10",
        generated_at=datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
        timeout_s=timeout_s,
    )


def test_capture_official_inputs_returns_registered_and_required_legal_roles(tmp_path):
    snapshot = capture_official_inputs(config(tmp_path), session=fake_session())

    assert {
        (source.dataset_key, source.document_role) for source in snapshot.sources
    } == {
        ("ligie", "ligie_snapshot"),
        ("nico", "nico_snapshot"),
        ("diputados_ligie", "legal_ledger"),
        ("diputados_ligie", "consolidated_text"),
        ("dof_law_reform", "law_reform"),
        ("dof_tariff_decree", "tariff_decree"),
    }
    assert snapshot.registry_version == "2026-08-10"
    assert len(snapshot.registry_sha256) == 64
    assert len(snapshot.identities) == 6
    assert all(identity.registry_version == "2026-08-10" for identity in snapshot.identities)
    assert snapshot.reconciliation.publishable is True
    assert snapshot.reconciliation.discrepancies == ()

    by_role = {
        (source.dataset_key, source.document_role): source
        for source in snapshot.sources
    }
    assert by_role[("dof_law_reform", "law_reform")].source_document[
        "published_at"
    ] == date(2025, 12, 29)
    assert by_role[("dof_tariff_decree", "tariff_decree")].source_document[
        "published_at"
    ] == date(2026, 4, 23)
    ledger = by_role[("diputados_ligie", "legal_ledger")]
    assert ledger.capture.path.is_file()
    assert ledger.source_document["media_type"].startswith("text/html")
    assert ledger.source_document["sha256"] == ledger.capture.sha256


def test_missing_captured_required_dof_role_blocks_reconciliation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        official_sources,
        "required_dof_evidence",
        lambda _ledger: (
            RequiredDofEvidence(
                role="law_reform",
                published_at=date(2025, 12, 29),
                url=LAW_REFORM_URL,
                media_type="application/pdf",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"legal reconciliation failed: .*missing_dof_evidence:tariff_decree",
    ):
        capture_official_inputs(config(tmp_path), session=fake_session())


def test_capture_fetches_only_ledger_linked_required_dof_urls(tmp_path):
    session = fake_session()

    capture_official_inputs(config(tmp_path), session=session)

    requested_urls = {url for url, _timeout in session.requested}
    assert LAW_REFORM_URL in requested_urls
    assert TARIFF_DECREE_URL in requested_urls


def test_release_sources_preserve_required_dof_evidence(tmp_path):
    build_config = config(tmp_path)
    snapshot = capture_official_inputs(build_config, session=fake_session())

    source_dir = write_release_sources(build_config, snapshot.sources)

    assert sorted(path.name for path in source_dir.iterdir()) == [
        "dof-law-reform.pdf",
        "dof-tariff-decree.pdf",
        "ligie-consolidated.pdf",
        "ligie-ledger.htm",
        "ligie.xlsx",
        "nico.xlsx",
        "source_capture.json",
    ]


def test_capture_official_inputs_uses_one_configured_timeout_for_every_request(tmp_path):
    session = fake_session()

    capture_official_inputs(config(tmp_path, timeout_s=17.5), session=session)

    assert {timeout for _url, timeout in session.requested} == {17.5}


def test_capture_preserves_actual_http_retrieval_timestamp(tmp_path, monkeypatch):
    retrieved = datetime(2026, 8, 10, 7, 59, 31, tzinfo=timezone.utc)
    generated = datetime(2026, 8, 10, 8, 0, 0, tzinfo=timezone.utc)
    real_fetch = official_sources.fetch_official_document

    def fetch_with_known_timestamp(*args, **kwargs):
        return replace(real_fetch(*args, **kwargs), retrieved_at=retrieved)

    monkeypatch.setattr(
        official_sources,
        "fetch_official_document",
        fetch_with_known_timestamp,
    )

    snapshot = capture_official_inputs(config(tmp_path), session=fake_session())

    for source in snapshot.sources:
        assert source.source_document["retrieved_at"] == retrieved
        assert source.source_document["retrieved_at"] != generated
        assert source.capture.metadata["retrieved_at"] == "2026-08-10T07:59:31Z"
