from dataclasses import replace
from datetime import date, datetime, timezone
from functools import lru_cache
import hashlib
from io import BytesIO
import json
from pathlib import Path

import duckdb
from openpyxl import Workbook
import pytest

from arancel_mx.pipeline import official_sources
from arancel_mx.pipeline.official_dataset import (
    OfficialDatasetConfig,
    build_official_dataset,
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
NOTES_URL = "https://dof.gob.mx/nota_detalle.php?codigo=5673161&fecha=02/12/2022"
NOTES_HTML = (
    Path(__file__).parents[1] / "fixtures" / "dof" / "national-notes-2022.html"
).read_text(encoding="utf-8")
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


def ligie_workbook_bytes(*, include_rates=True):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "FA"
    for _ in range(6):
        sheet.append([None])
    if include_rates:
        sheet.append(
            [
                None,
                None,
                "Fracción Arancelaria",
                "Descripción",
                "Unidad de Medida",
                "Arancel %",
                None,
            ]
        )
        sheet.append([None, None, None, None, None, "IMP.", "EXP."])
        sheet.append(
            [
                None,
                None,
                "0101.21.01",
                "Reproductores de raza pura.",
                "Cbza",
                "10",
                "Ex.",
            ]
        )
    else:
        sheet.append(
            [None, None, "Fracción Arancelaria", "Descripción", "Unidad de Medida"]
        )
        sheet.append(
            [None, None, "0101.21.01", "Reproductores de raza pura.", "Cbza"]
        )
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


PDF_HIERARCHY = (
    Path(__file__).parents[1] / "fixtures" / "pdf" / "ligie_hierarchy.pdf"
)


@lru_cache(maxsize=1)
def fixture_bytes():
    ligie_bytes = ligie_workbook_bytes()
    nico_bytes = workbook_bytes(
        [
            ["Fracción Arancelaria", "NICO", "Descripción NICO"],
            ["01012101", "00", "Reproductores de raza pura."],
        ]
    )
    return ligie_bytes, nico_bytes, PDF_HIERARCHY.read_bytes()


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

    def get(self, url, timeout=None, stream=False, allow_redirects=True):
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
        LIGIE_URL: Response(LIGIE_URL, ligie_bytes, XLSX_TYPE),
        NICO_URL: Response(NICO_URL, nico_bytes, XLSX_TYPE),
        NOTES_URL: Response(
            NOTES_URL, NOTES_HTML.encode("utf-8"), "text/html; charset=utf-8", NOTES_HTML
        ),
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


def checksum_map(release_dir):
    result = {}
    for line in (release_dir / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        digest, name = line.split("  ", maxsplit=1)
        result[name] = digest
    return result


def test_offline_build_produces_verified_release(tmp_path):
    build_config = config(tmp_path, "first")
    session = fake_session()

    summary = build_official_dataset(build_config, session=session)

    assert summary["validation_status"] == "passed"
    assert summary["row_count"] == 5
    assert summary["source_count"] == 7
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
        LAW_REFORM_URL,
        TARIFF_DECREE_URL,
        LIGIE_INDEX,
        NICO_INDEX,
        LIGIE_URL,
        NICO_URL,
        NOTES_URL,
    }

    with duckdb.connect(
        str(build_config.output_dir / "arancel_mx.duckdb"), read_only=True
    ) as connection:
        levels = dict(
            connection.execute(
                "SELECT level, COUNT(*) FROM arancel_mx GROUP BY level ORDER BY level"
            ).fetchall()
        )
        fraction_rate = connection.execute(
            """
            SELECT unit_name, igi_text, igi_kind, CAST(igi_value AS VARCHAR),
                   ige_text, ige_kind, CAST(ige_value AS VARCHAR)
            FROM arancel_mx
            WHERE level = 'fraccion8' AND code = '01012101'
            """
        ).fetchone()
        notes_count = connection.execute(
            "SELECT COUNT(*) FROM arancel_mx_national_notes"
        ).fetchone()[0]
        assert notes_count == 20
        chapter_notes = connection.execute(
            "SELECT chapter, note_number, text FROM arancel_mx_national_notes "
            "ORDER BY chapter, note_number"
        ).fetchall()
        assert chapter_notes[0][0] == "01"
        assert chapter_notes[0][1] == "1"
    assert levels == {"fraccion8": 1, "hs2": 1, "hs4": 1, "hs6": 1, "nico10": 1}
    assert fraction_rate == (
        "Cbza",
        "10",
        "ad_valorem",
        "10.000000",
        "Ex.",
        "exento",
        "0.000000",
    )

    manifest = json.loads(
        (build_config.output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["validation_status"] == "passed"
    assert len(manifest["source_documents"]) == 7
    assert {
        (
            identity["dataset_key"],
            identity["document_role"],
        )
        for identity in manifest["source_identity"]
    } == {
        ("ligie", "ligie_snapshot"),
        ("nico", "nico_snapshot"),
        ("diputados_ligie", "legal_ledger"),
        ("diputados_ligie", "consolidated_text"),
        ("dof_law_reform", "law_reform"),
        ("dof_tariff_decree", "tariff_decree"),
        ("national_notes", "national_notes"),
    }
    for source in manifest["source_documents"]:
        assert source["source_url"].startswith("https://")
        assert len(source["sha256"]) == 64
        assert "local_path" not in source
    national_notes_source = next(
        source
        for source in manifest["source_documents"]
        if source["title"] == "Notas nacionales LIGIE (DOF)"
    )
    assert national_notes_source["source_url"] == NOTES_URL
    assert national_notes_source["publication_venue"] == "Diario Oficial de la Federación"


def test_build_rejects_fraction_dataset_without_tariff_values(tmp_path):
    build_config = config(tmp_path, "missing-rates")
    session = fake_session()
    session.responses[LIGIE_URL] = Response(
        LIGIE_URL,
        ligie_workbook_bytes(include_rates=False),
        XLSX_TYPE,
    )

    with pytest.raises(ValueError, match="no matching tariff rate"):
        build_official_dataset(build_config, session=session)


def test_build_accepts_declared_legacy_charset_for_diputados_ledger(tmp_path):
    build_config = config(tmp_path, "legacy-ledger")
    session = fake_session()
    legacy_ledger = "<!-- Reforma – vigente -->\n" + DIPUTADOS_LEDGER
    session.responses[DIPUTADOS_URL] = Response(
        DIPUTADOS_URL,
        legacy_ledger.encode("cp1252"),
        "text/html; charset=windows-1252",
    )

    summary = build_official_dataset(build_config, session=session)

    assert summary["validation_status"] == "passed"
    assert summary["row_count"] == 5


def test_build_blocks_mismatched_legal_evidence_before_output(tmp_path, monkeypatch):
    build_config = config(tmp_path, "legal-mismatch")
    monkeypatch.setattr(
        official_sources,
        "required_dof_evidence",
        lambda _ledger: (
            RequiredDofEvidence(
                role="law_reform",
                published_at=date(2025, 12, 28),
                url=LAW_REFORM_URL,
                media_type="application/pdf",
            ),
            RequiredDofEvidence(
                role="tariff_decree",
                published_at=date(2026, 4, 23),
                url=TARIFF_DECREE_URL,
                media_type="application/pdf",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"legal reconciliation failed: .*missing_dof_evidence:law_reform",
    ):
        build_official_dataset(build_config, session=fake_session())

    assert not build_config.output_dir.exists()
    assert not (build_config.work_dir / "candidate" / "arancel_mx.duckdb").exists()


def test_identical_inputs_produce_logically_deterministic_release(
    tmp_path, monkeypatch
):
    fixed_retrieved_at = datetime(2026, 8, 10, 7, 59, 31, tzinfo=timezone.utc)
    real_fetch = official_sources.fetch_official_document

    def fetch_with_fixed_timestamp(*args, **kwargs):
        return replace(real_fetch(*args, **kwargs), retrieved_at=fixed_retrieved_at)

    monkeypatch.setattr(
        official_sources,
        "fetch_official_document",
        fetch_with_fixed_timestamp,
    )
    first = config(tmp_path, "first")
    second = config(tmp_path, "second")

    build_official_dataset(first, session=fake_session())
    build_official_dataset(second, session=fake_session())

    deterministic_assets = (
        "arancel_mx.csv",
        "arancel_mx.json",
        "official-sources.tar.gz",
    )
    for name in deterministic_assets:
        assert (first.output_dir / name).read_bytes() == (second.output_dir / name).read_bytes()

    first_checksums = checksum_map(first.output_dir)
    second_checksums = checksum_map(second.output_dir)
    for name in deterministic_assets:
        assert first_checksums[name] == second_checksums[name]

    first_manifest = json.loads(
        (first.output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    second_manifest = json.loads(
        (second.output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    first_db_hash = first_manifest["artifact_sha256"].pop("arancel_mx.duckdb")
    second_db_hash = second_manifest["artifact_sha256"].pop("arancel_mx.duckdb")
    assert first_manifest == second_manifest
    assert first_db_hash == first_checksums["arancel_mx.duckdb"]
    assert second_db_hash == second_checksums["arancel_mx.duckdb"]
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


def test_schema_v2_manifest_replay_returns_no_change_without_candidate(tmp_path):
    first = config(tmp_path, "first-published")
    first_summary = build_official_dataset(first, session=fake_session())
    previous_manifest = json.loads(
        (first.output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    second = config(tmp_path, "second-evaluation")

    result = build_official_dataset(
        second,
        session=fake_session(),
        previous_manifest=previous_manifest,
    )

    assert first_summary["status"] == "built"
    assert previous_manifest["schema_version"] == "2"
    assert result == {
        "status": "no_change",
        "dataset_version": "2026.08.10",
        "schema_version": "2",
        "row_count": 5,
        "validation_status": "passed",
        "source_count": 7,
        "output_dir": None,
    }
    assert not second.output_dir.exists()
    assert not (second.work_dir / "candidate" / "arancel_mx.duckdb").exists()
