from datetime import date, datetime, timezone
from pathlib import Path

from arancel_mx.pipeline.official_dataset import OfficialDatasetConfig
from arancel_mx.pipeline.official_sources import capture_official_inputs


DIPUTADOS_LEDGER = (
    Path(__file__).parents[1] / "fixtures" / "diputados" / "ligie_2022.html"
).read_text(encoding="utf-8")
DIPUTADOS_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"
DIPUTADOS_PDF = "https://www.diputados.gob.mx/LeyesBiblio/pdf/LIGIE_2022.pdf"
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

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.requested = []

    def get(self, url, timeout=None):
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


def test_capture_official_inputs_returns_registered_base_roles(tmp_path):
    snapshot = capture_official_inputs(config(tmp_path), session=fake_session())

    assert {
        (source.dataset_key, source.document_role) for source in snapshot.sources
    } == {
        ("ligie", "ligie_snapshot"),
        ("nico", "nico_snapshot"),
        ("diputados_ligie", "consolidated_text"),
    }
    assert snapshot.registry_version == "2026-08-10"
    assert len(snapshot.registry_sha256) == 64
    assert len(snapshot.identities) == 3
    assert all(identity.registry_version == "2026-08-10" for identity in snapshot.identities)


def test_capture_official_inputs_uses_one_configured_timeout_for_every_request(tmp_path):
    session = fake_session()

    capture_official_inputs(config(tmp_path, timeout_s=17.5), session=session)

    assert {timeout for _url, timeout in session.requested} == {17.5}
