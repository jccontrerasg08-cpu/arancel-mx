from datetime import date, datetime, timezone
from functools import lru_cache
import hashlib
from io import BytesIO
import json
from pathlib import Path

import duckdb
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

from arancel_mx.pipeline.official_dataset import (
    OfficialDatasetConfig,
    build_official_dataset,
)


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


def workbook_bytes(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Datos"
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def hierarchy_pdf_bytes():
    stream = BytesIO()
    story = [
        Table([["Capítulo 01"], ["Animales vivos"]]),
        Spacer(1, 10),
        Table(
            [
                ["CÓDIGO", "", "DESCRIPCIÓN", "UNIDAD", "IMP.", "EXP."],
                ["01.01", "", "Caballos, asnos, mulos y burdéganos, vivos.", "", "", ""],
                ["0101.21", "--", "Reproductores de raza pura.", "", "", ""],
                ["0101.21.01", "", "Reproductores de raza pura.", "Cbza", "10", "Ex."],
            ],
            colWidths=[70, 20, 280, 50, 40, 40],
            style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]),
        ),
    ]
    SimpleDocTemplate(stream, pagesize=letter).build(story)
    return stream.getvalue()


@lru_cache(maxsize=1)
def fixture_bytes():
    ligie_bytes = workbook_bytes(
        [
            ["Fracción", "Descripción", "Unidad", "IGI", "IGE"],
            ["01012101", "Reproductores de raza pura.", "Cabeza", "10", "Ex."],
        ]
    )
    nico_bytes = workbook_bytes(
        [
            ["Fracción Arancelaria", "NICO", "Descripción NICO"],
            ["01012101", "00", "Reproductores de raza pura."],
        ]
    )
    return ligie_bytes, nico_bytes, hierarchy_pdf_bytes()


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
        self.requested.append(url)
        if url not in self.responses:
            raise AssertionError(f"unexpected network URL: {url}")
        return self.responses[url]


def fake_session():
    ligie_html = f'<a href="{LIGIE_URL}">Fracciones 20260810</a>'
    nico_html = f'<a href="{NICO_URL}">NICO 20260810</a>'
    ligie_bytes, nico_bytes, pdf_bytes = fixture_bytes()
    responses = {
        DIPUTADOS_URL: Response(
            DIPUTADOS_URL,
            DIPUTADOS_LEDGER.encode("utf-8"),
            "text/html; charset=utf-8",
            DIPUTADOS_LEDGER,
        ),
        DIPUTADOS_PDF: Response(DIPUTADOS_PDF, pdf_bytes, "application/pdf"),
        LIGIE_INDEX: Response(
            LIGIE_INDEX, ligie_html.encode("utf-8"), "text/html", ligie_html
        ),
        NICO_INDEX: Response(
            NICO_INDEX, nico_html.encode("utf-8"), "text/html", nico_html
        ),
        LIGIE_URL: Response(LIGIE_URL, ligie_bytes, XLSX_TYPE),
        NICO_URL: Response(NICO_URL, nico_bytes, XLSX_TYPE),
    }
    return FakeSession(responses)


def config(tmp_path, name):
    return OfficialDatasetConfig(
        work_dir=tmp_path / f"{name}-work",
        output_dir=tmp_path / f"{name}-release",
        effective_as_of=date(2026, 8, 10),
        dataset_version="2026.08.10",
        generated_at=datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc),
    )


def test_offline_build_produces_verified_release(tmp_path):
    build_config = config(tmp_path, "first")
    session = fake_session()

    summary = build_official_dataset(build_config, session=session)

    assert summary["validation_status"] == "passed"
    assert summary["row_count"] == 5
    assert summary["source_count"] == 3
    assert sorted(path.name for path in build_config.output_dir.iterdir()) == [
        "SHA256SUMS",
        "arancel_mx.csv",
        "arancel_mx.duckdb",
        "arancel_mx.json",
        "manifest.json",
        "official-sources.tar.gz",
    ]
    assert set(session.requested) == {
        DIPUTADOS_URL,
        DIPUTADOS_PDF,
        LIGIE_INDEX,
        NICO_INDEX,
        LIGIE_URL,
        NICO_URL,
    }

    with duckdb.connect(
        str(build_config.output_dir / "arancel_mx.duckdb"), read_only=True
    ) as connection:
        levels = dict(
            connection.execute(
                "SELECT level, COUNT(*) FROM arancel_mx GROUP BY level ORDER BY level"
            ).fetchall()
        )
    assert levels == {"fraccion8": 1, "hs2": 1, "hs4": 1, "hs6": 1, "nico10": 1}

    manifest = json.loads(
        (build_config.output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["validation_status"] == "passed"
    assert len(manifest["source_documents"]) == 3
    for source in manifest["source_documents"]:
        assert source["source_url"].startswith("https://")
        assert len(source["sha256"]) == 64
        assert "local_path" not in source


def test_build_accepts_declared_legacy_charset_for_diputados_ledger(tmp_path):
    build_config = config(tmp_path, "legacy-ledger")
    session = fake_session()
    session.responses[DIPUTADOS_URL] = Response(
        DIPUTADOS_URL,
        DIPUTADOS_LEDGER.encode("cp1252"),
        "text/html; charset=windows-1252",
    )

    summary = build_official_dataset(build_config, session=session)

    assert summary["validation_status"] == "passed"
    assert summary["row_count"] == 5


def test_identical_inputs_produce_logically_deterministic_release(tmp_path):
    first = config(tmp_path, "first")
    second = config(tmp_path, "second")

    build_official_dataset(first, session=fake_session())
    build_official_dataset(second, session=fake_session())

    for name in (
        "arancel_mx.csv",
        "arancel_mx.json",
        "official-sources.tar.gz",
    ):
        assert (first.output_dir / name).read_bytes() == (second.output_dir / name).read_bytes()

    first_manifest = json.loads(
        (first.output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    second_manifest = json.loads(
        (second.output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    first_db_hash = first_manifest["artifact_sha256"].pop("arancel_mx.duckdb")
    second_db_hash = second_manifest["artifact_sha256"].pop("arancel_mx.duckdb")
    assert first_manifest == second_manifest
    assert first_db_hash == hashlib.sha256(
        (first.output_dir / "arancel_mx.duckdb").read_bytes()
    ).hexdigest()
    assert second_db_hash == hashlib.sha256(
        (second.output_dir / "arancel_mx.duckdb").read_bytes()
    ).hexdigest()

    queries = {
        "ids": "SELECT record_id FROM arancel_mx ORDER BY level, code",
        "hashes": "SELECT record_hash FROM arancel_mx ORDER BY level, code",
        "rows": "SELECT level, code, description, igi_text, ige_text FROM arancel_mx ORDER BY level, code",
    }
    with duckdb.connect(str(first.output_dir / "arancel_mx.duckdb"), read_only=True) as left:
        with duckdb.connect(str(second.output_dir / "arancel_mx.duckdb"), read_only=True) as right:
            for query in queries.values():
                assert left.execute(query).fetchall() == right.execute(query).fetchall()
