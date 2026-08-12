"""Catalog and parsing helpers for SIICEX-CAAAREM TIGIE HTML pages."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from arancel_mx.sources.vucem import TableParser, normalize_fraction_code


SIICEX_TARIFA_INDEX_URL = (
    "http://www.siicex-caaarem.org.mx/Bases/tigiei.nsf/TarifaW?OpenView"
)
SIICEX_SAMPLE_FRACTION_CODE = "90014002"
SIICEX_SAMPLE_FRACTION_DOCUMENT_URL = (
    "http://www.siicex-caaarem.org.mx/Bases/tigiei.nsf/"
    "d58945443a3d19d886256bab00510b2e/c08642781ad9ca4e8625730200736507?OpenDocument"
)

SIICEX_HTTP_HOSTS = frozenset(
    {
        "www.siicex-caaarem.org.mx",
        "siicex-caaarem.org.mx",
    }
)


@dataclass(frozen=True)
class SiicexFractionDocument:
    code: str
    description: str
    import_duty: str | None
    export_duty: str | None


def _fold(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", " ".join(str(value or "").split()))
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def _duty_from_tables(tables: list[list[list[str]]]) -> tuple[str | None, str | None]:
    import_duty: str | None = None
    export_duty: str | None = None
    for table in tables:
        for row in table:
            if len(row) < 2:
                continue
            label = _fold(row[0])
            value = row[1].strip()
            if label in {"igi", "impuesto general de importacion"}:
                import_duty = value
            if label in {"ige", "impuesto general de exportacion"}:
                export_duty = value
    return import_duty, export_duty


def _fraction_row(
    tables: list[list[list[str]]],
    *,
    code: str,
) -> tuple[str, str] | None:
    for table in tables:
        for row in table:
            if len(row) < 2:
                continue
            label = _fold(row[0])
            if "fraccion" in label or "hts code" in label or "codigo" in label:
                fraction_code = normalize_fraction_code(row[1])
                if fraction_code.endswith(code):
                    description = row[2] if len(row) > 2 else row[-1]
                    return code, description
            joined = " ".join(row)
            if normalize_fraction_code(joined).endswith(code) and "fraccion" in _fold(joined):
                description = row[-1]
                return code, description
    return None


def parse_fraction_document(html: str, *, expected_code: str | None = None) -> SiicexFractionDocument:
    """Parse one SIICEX Lotus Notes fraction document into structured tariff fields."""
    code = expected_code or ""
    if not code:
        match = re.search(r"(\d{8})", html)
        if match:
            code = match.group(1)
    if not code:
        raise ValueError("SIICEX fraction document HTML is missing an 8-digit code")

    parser = TableParser()
    parser.feed(html)
    fraction = _fraction_row(parser.tables, code=code)
    if fraction is None:
        raise ValueError(f"SIICEX fraction document HTML is missing a tariff row for {code}")
    parsed_code, description = fraction
    import_duty, export_duty = _duty_from_tables(parser.tables)
    return SiicexFractionDocument(
        code=parsed_code,
        description=description,
        import_duty=import_duty,
        export_duty=export_duty,
    )


def validate_tarifa_index_html(html: str) -> None:
    folded = _fold(html)
    markers = (
        "tarifa",
        "fracciones arancelarias",
        "ligie",
        "tigie",
        "siicex",
        "caaarem",
    )
    if not any(marker in folded for marker in markers):
        raise ValueError("SIICEX TarifaW index HTML is missing expected tariff markers")
