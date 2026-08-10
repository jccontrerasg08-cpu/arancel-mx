"""Unified free-first catalog indexing and search."""

from __future__ import annotations

import re
import hashlib
import unicodedata
from pathlib import Path

import pandas as pd

from . import db
from .hs_global import parse_hs_global_file
from .paths import RAW_DIR


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.split())


CATALOG_SOURCE_CODES = ("snice-nico", "vucem-tigie", "hs-global")


def _code_level(code: str) -> int:
    return len(code)


def rebuild_tigie_catalog(raw_dir: Path | None = None) -> int:
    """Compatibility wrapper that refreshes the local SQL catalog."""
    if raw_dir:
        return refresh_catalog_sql({"vucem-tigie": raw_dir})
    return refresh_catalog_sql({code: RAW_DIR / code for code in CATALOG_SOURCE_CODES})


def refresh_catalog_sql(
    raw_dirs: dict[str, Path] | None = None,
    db_path: Path = db.DB_PATH,
) -> int:
    """Rebuild catalog SQL from raw assets in one transaction."""
    db.init_db(db_path)
    source_dirs = raw_dirs or {code: RAW_DIR / code for code in CATALOG_SOURCE_CODES}
    source_codes = tuple(code for code in CATALOG_SOURCE_CODES if code in source_dirs)
    rows: list[dict] = []
    for source_code in source_codes:
        rows.extend(_parse_source_assets(source_code, source_dirs[source_code]))

    with db.connect(db_path) as conn:
        refresh_run_id = db.next_id(conn, "catalog_refresh_run", "refresh_run_id")
        started_at = db.utc_now_naive()
        conn.execute(
            """
            INSERT INTO catalog_refresh_run
            (refresh_run_id, status, started_at, source_codes)
            VALUES (?, 'RUNNING', ?, ?)
            """,
            [refresh_run_id, started_at, ",".join(source_codes)],
        )
        try:
            conn.execute("BEGIN TRANSACTION")
            if source_codes:
                placeholders = ",".join("?" for _ in source_codes)
                conn.execute(f"DELETE FROM catalog_item WHERE source_code IN ({placeholders})", list(source_codes))
            if any(code in {"snice-nico", "vucem-tigie"} for code in source_codes):
                _reset_legacy_catalog_tables(conn)
            if rows:
                _insert_catalog_rows(conn, rows)
                legacy_rows = [row for row in rows if row["source_code"] in {"snice-nico", "vucem-tigie"}]
                if legacy_rows:
                    _insert_legacy_tigie_rows(conn, legacy_rows)
                nico_rows = [
                    {
                        "nico10": row["code"],
                        "fraccion8": row["code"][:8],
                        "nico": row["code"][8:],
                        "description": row["description"][:1000],
                        "source_file": row["source_file"],
                    }
                    for row in legacy_rows
                    if len(row["code"]) == 10
                ]
                if nico_rows:
                    _insert_nico_rows(conn, nico_rows)
            _refresh_tariff_operational_tables(conn)
            conn.execute(
                """
                UPDATE catalog_refresh_run
                SET status = 'OK', finished_at = ?, records_loaded = ?, message = ?
                WHERE refresh_run_id = ?
                """,
                [db.utc_now_naive(), len(rows), "catalog refreshed", refresh_run_id],
            )
            conn.execute("COMMIT")
        except Exception as exc:
            conn.execute("ROLLBACK")
            conn.execute(
                """
                UPDATE catalog_refresh_run
                SET status = 'ERROR', finished_at = ?, records_loaded = 0, message = ?
                WHERE refresh_run_id = ?
                """,
                [db.utc_now_naive(), str(exc), refresh_run_id],
            )
            raise
    return len(rows)


def _insert_catalog_rows(conn, rows: list[dict]) -> None:
    frame = pd.DataFrame(
        [
            {
                "item_key": _item_key(row["source_code"], row["code"]),
                "code": row["code"],
                "code_level": row["code_level"],
                "description": row["description"][:1000],
                "normalized_description": normalize_text(row["description"])[:1000],
                "normalized_search_text": normalize_text(f'{row["code"]} {row["description"]}')[:1200],
                "source_code": row["source_code"],
                "country_scope": row["country_scope"],
                "source_file": row["source_file"],
                "source_url": row.get("source_url", ""),
                "raw_text": row["raw_text"][:4000],
            }
            for row in rows
        ]
    )
    conn.register("catalog_item_stage", frame)
    conn.execute(
        """
        INSERT INTO catalog_item
        (item_key, code, code_level, description, normalized_description,
         normalized_search_text, source_code, country_scope, source_file,
         source_url, raw_text)
        SELECT item_key, code, code_level, description, normalized_description,
               normalized_search_text, source_code, country_scope, source_file,
               source_url, raw_text
        FROM catalog_item_stage
        """
    )
    conn.unregister("catalog_item_stage")


def _insert_legacy_tigie_rows(conn, rows: list[dict]) -> None:
    frame = pd.DataFrame(
        [
            {
                "code": row["code"],
                "description": row["description"][:1000],
                "source_file": row["source_file"],
                "raw_text": row["raw_text"][:4000],
            }
            for row in rows
        ]
    )
    conn.register("vucem_tigie_stage", frame)
    conn.execute(
        """
        INSERT INTO vucem_tigie_items (code, description, source_file, raw_text)
        SELECT code, description, source_file, raw_text
        FROM vucem_tigie_stage
        """
    )
    conn.unregister("vucem_tigie_stage")


def _insert_nico_rows(conn, rows: list[dict]) -> None:
    frame = pd.DataFrame(rows)
    conn.register("nico_stage", frame)
    conn.execute(
        """
        INSERT INTO dim_nico_catalog (nico10, fraccion8, nico, description, source_file)
        SELECT nico10, fraccion8, nico, description, source_file
        FROM nico_stage
        """
    )
    conn.unregister("nico_stage")


def _refresh_tariff_operational_tables(conn) -> None:
    """Project catalog_item into operational tariff tables used by the UI."""
    conn.execute("DELETE FROM catalog_tariff_fraction")
    conn.execute("DELETE FROM catalog_tariff_nico")
    conn.execute(
        """
        INSERT INTO catalog_tariff_fraction (
            code, fraccion8, nico10, hs2, hs4, hs6, description, source_code,
            country_scope, source_file, source_url
        )
        SELECT
            code,
            CASE WHEN LENGTH(code) >= 8 THEN SUBSTR(code, 1, 8) ELSE NULL END AS fraccion8,
            CASE WHEN LENGTH(code) = 10 THEN code ELSE NULL END AS nico10,
            CASE WHEN LENGTH(code) >= 2 THEN SUBSTR(code, 1, 2) ELSE NULL END AS hs2,
            CASE WHEN LENGTH(code) >= 4 THEN SUBSTR(code, 1, 4) ELSE NULL END AS hs4,
            CASE WHEN LENGTH(code) >= 6 THEN SUBSTR(code, 1, 6) ELSE NULL END AS hs6,
            description,
            source_code,
            country_scope,
            source_file,
            source_url
        FROM (
            SELECT
                item.*,
                ROW_NUMBER() OVER (
                    PARTITION BY item.code
                    ORDER BY
                        CASE item.country_scope WHEN 'MX' THEN 0 ELSE 1 END,
                        source.priority ASC NULLS LAST,
                        item.code_level DESC,
                        item.loaded_at DESC
                ) AS rn
            FROM catalog_item AS item
            LEFT JOIN catalog_source AS source
                ON source.source_code = item.source_code
            WHERE item.code_level IN (2, 4, 6, 8, 10)
        ) ranked
        WHERE rn = 1
        """
    )
    conn.execute(
        """
        INSERT INTO catalog_tariff_nico (
            nico10, fraccion8, nico, description, source_code, source_file
        )
        SELECT
            code AS nico10,
            SUBSTR(code, 1, 8) AS fraccion8,
            SUBSTR(code, 9, 2) AS nico,
            description,
            source_code,
            source_file
        FROM catalog_tariff_fraction
        WHERE LENGTH(code) = 10
        """
    )


def _reset_legacy_catalog_tables(conn) -> None:
    conn.execute("DELETE FROM vucem_tigie_items")
    conn.execute("DELETE FROM dim_nico_catalog")


def _parse_source_assets(source_code: str, base: Path) -> list[dict]:
    if not base.exists():
        return []
    if source_code == "hs-global":
        return _parse_hs_global_assets(base)

    found: dict[str, tuple[str, str, str]] = {}
    for path in sorted(base.glob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".xlsx", ".xls"}:
            for code, desc in _extract_excel_code_description_pairs(path):
                if code and desc and code not in found:
                    found[code] = (desc, str(path), desc)
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for code, desc in _extract_code_description_pairs(text):
            if code and desc and code not in found:
                found[code] = (desc, str(path), desc)
    return [
        _catalog_row(source_code, code, desc, source, raw)
        for code, (desc, source, raw) in found.items()
    ]


def _parse_hs_global_assets(base: Path) -> list[dict]:
    found: dict[str, dict] = {}
    for path in sorted(base.glob("*")):
        if not path.is_file():
            continue
        for parsed in parse_hs_global_file(path):
            code = parsed.get("code", "")
            desc = parsed.get("description", "")
            if code and desc and code not in found:
                found[code] = _catalog_row(
                    "hs-global",
                    code,
                    desc,
                    str(path),
                    desc,
                    parsed.get("source_url") or "https://wits.worldbank.org/data/public/HSProducts.xls",
                )
    return list(found.values())


def _catalog_row(
    source_code: str,
    code: str,
    description: str,
    source_file: str,
    raw_text: str,
    source_url: str = "",
) -> dict:
    scope = "GLOBAL" if source_code == "hs-global" else "MX"
    return {
        "source_code": source_code,
        "country_scope": scope,
        "code": code,
        "code_level": _code_level(code),
        "description": description,
        "source_file": source_file,
        "source_url": source_url,
        "raw_text": raw_text,
    }


def _item_key(source_code: str, code: str) -> str:
    digest = hashlib.sha1(f"{source_code}:{code}".encode("utf-8")).hexdigest()[:16]
    return f"{source_code}:{code}:{digest}"


def _normalize_code(value: object, width: int | None = None) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    digits = re.sub(r"\D", "", text)
    if width and digits:
        digits = digits.zfill(width)
    return digits


def _extract_excel_code_description_pairs(path: Path) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
    for df in sheets.values():
        header_idx = _find_nico_header_row(df)
        rows = df.iloc[header_idx + 1:] if header_idx is not None else df
        columns = _nico_column_positions(df.iloc[header_idx]) if header_idx is not None else (1, 2, 3)
        if columns is None:
            continue
        fraccion_idx, nico_idx, desc_idx = columns
        for row in rows.itertuples(index=False, name=None):
            cells = list(row)
            if len(cells) <= max(fraccion_idx, nico_idx, desc_idx):
                continue
            fraccion = _normalize_code(cells[fraccion_idx])
            nico = _normalize_code(cells[nico_idx], 2)
            desc = _clean_description(str(cells[desc_idx] or ""))
            if len(fraccion) == 8 and len(nico) == 2 and len(desc) > 3:
                pairs.append((f"{fraccion}{nico}", desc))
            elif len(fraccion) in {2, 4, 6, 8} and len(desc) > 3:
                pairs.append((fraccion, desc))
    return pairs


def _find_nico_header_row(df: pd.DataFrame) -> int | None:
    for idx in range(min(len(df), 15)):
        if _nico_column_positions(df.iloc[idx]) is not None:
            return idx
    return None


def _nico_column_positions(row) -> tuple[int, int, int] | None:
    names = [normalize_text(value) for value in row.tolist()]
    fraccion = next((idx for idx, name in enumerate(names) if "fraccion" in name), None)
    nico = next((idx for idx, name in enumerate(names) if name == "nico"), None)
    desc = next((idx for idx, name in enumerate(names) if name in {"descripcion", "description"}), None)
    if fraccion is None or nico is None or desc is None:
        return None
    return fraccion, nico, desc


def _extract_code_description_pairs(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    # TSV/CSV-like lines: code <tab/semicolon/comma> description
    for line in text.splitlines():
        clean = line.strip().strip(",;")
        match = re.match(r'["\']?(\d{2,10})["\']?\s*[\t;,|]\s*["\']?(.{4,240})', clean)
        if match:
            pairs.append((match.group(1), _clean_description(match.group(2))))

    # JS/object-like fragments: "code":"01012101", "description":"..."
    object_pattern = re.compile(
        r'(?:(?:codigo|clave|fraccion|code)["\']?\s*[:=]\s*["\']?(\d{2,10})["\']?).{0,120}?'
        r'(?:(?:descripcion|desc|text|name)["\']?\s*[:=]\s*["\']([^"\']{4,240})["\'])',
        re.IGNORECASE | re.DOTALL,
    )
    for match in object_pattern.finditer(text):
        pairs.append((match.group(1), _clean_description(match.group(2))))

    return [(code, desc) for code, desc in pairs if len(desc) > 3]


def _clean_description(value: str) -> str:
    value = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), value)
    value = value.replace("\\n", " ").replace("\\t", " ")
    value = re.sub(r"[\"'{}\[\];]+$", "", value)
    return re.sub(r"\s+", " ", value).strip()


def search_tigie(query: str, limit: int = 10, db_path: Path = db.DB_PATH) -> list[dict]:
    if not db_path.exists():
        db.init_db(db_path)
    query = query.strip()
    if not query:
        return []
    query_terms = normalize_text(query).split()
    if not query_terms:
        return []
    query_digits = _normalize_code(query)
    where_parts = []
    params: list[object] = []
    for term in query_terms:
        where_parts.append("normalized_search_text LIKE ?")
        params.append(f"%{term}%")
    if query_digits:
        where_parts.extend(["code = ?", "code LIKE ?", "? LIKE code || '%'"])
        params.extend([query_digits, f"{query_digits}%", query_digits])
    where_sql = " OR ".join(where_parts)
    params.append(max(limit * 40, 100))

    with db.connect(db_path, read_only=True) as conn:
        rows = conn.execute(
            f"""
            SELECT
                item.code,
                item.description,
                item.source_file,
                item.source_code,
                item.country_scope,
                item.code_level,
                item.normalized_search_text,
                source.source_name,
                source.priority
            FROM catalog_item AS item
            LEFT JOIN catalog_source AS source
                ON source.source_code = item.source_code
            WHERE {where_sql}
            ORDER BY source.priority ASC, item.code
            LIMIT ?
            """,
            params,
        ).fetchall()
    scored = []
    for row in rows:
        score = _score_catalog_row(query_terms, query_digits, row[0], row[6], row[4])
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], item[1][8] or 999, -int(item[1][5] or 0), item[1][0]))
    return [
        {
            "code": row[0],
            "description": row[1],
            "source_file": row[2],
            "source": row[7] or row[3],
            "scope": row[4],
            "level": row[5],
            "score": score,
        }
        for score, row in scored[:limit]
    ]



HS_CHAPTERS = [
    ("01", "Animales vivos"),
    ("02", "Carne y despojos comestibles"),
    ("03", "Pescados y crustaceos, moluscos y demas invertebrados acuaticos"),
    ("04", "Leche y productos lacteos; huevos de ave; miel natural"),
    ("05", "Los demas productos de origen animal"),
    ("06", "Plantas vivas y productos de la floricultura"),
    ("07", "Hortalizas, plantas, raices y tuberculos alimenticios"),
    ("08", "Frutas y frutos comestibles; cortezas de agrios o melones"),
    ("09", "Cafe, te, yerba mate y especias"),
    ("10", "Cereales"),
    ("11", "Productos de la molineria; malta; almidon y fecula"),
    ("12", "Semillas y frutos oleaginosos; plantas industriales o medicinales"),
    ("13", "Gomas, resinas y demas jugos y extractos vegetales"),
    ("14", "Materias trenzables y demas productos de origen vegetal"),
    ("15", "Grasas y aceites animales o vegetales"),
    ("16", "Preparaciones de carne, pescado o crustaceos"),
    ("17", "Azucares y articulos de confiteria"),
    ("18", "Cacao y sus preparaciones"),
    ("19", "Preparaciones a base de cereales, harina, almidon o leche"),
    ("20", "Preparaciones de hortalizas, frutas u otros frutos"),
    ("21", "Preparaciones alimenticias diversas"),
    ("22", "Bebidas, liquidos alcoholicos y vinagre"),
    ("23", "Residuos de industrias alimentarias; alimentos para animales"),
    ("24", "Tabaco y sucedaneos del tabaco elaborados"),
    ("25", "Sal, azufre, tierras y piedras; yesos, cales y cementos"),
    ("26", "Minerales metaliferos, escorias y cenizas"),
    ("27", "Combustibles minerales, aceites minerales y productos de su destilacion"),
    ("28", "Productos quimicos inorganicos"),
    ("29", "Productos quimicos organicos"),
    ("30", "Productos farmaceuticos"),
    ("31", "Abonos"),
    ("32", "Extractos curtientes o tintoreos; pinturas y barnices"),
    ("33", "Aceites esenciales; preparaciones de perfumeria o cosmetica"),
    ("34", "Jabon, agentes de superficie organicos; ceras artificiales"),
    ("35", "Materias albuminoideas; productos a base de almidon; colas; enzimas"),
    ("36", "Polvoras y explosivos; articulos de pirotecnia"),
    ("37", "Productos fotograficos o cinematograficos"),
    ("38", "Productos diversos de las industrias quimicas"),
    ("39", "Plastico y sus manufacturas"),
    ("40", "Caucho y sus manufacturas"),
    ("41", "Pieles, excepto peleteria, y cueros"),
    ("42", "Manufacturas de cuero; articulos de viaje y bolsos"),
    ("43", "Peleteria y confecciones de peleteria"),
    ("44", "Madera, carbon vegetal y manufacturas de madera"),
    ("45", "Corcho y sus manufacturas"),
    ("46", "Manufacturas de esparteria o cesteria"),
    ("47", "Pasta de madera; papel o carton para reciclar"),
    ("48", "Papel y carton; manufacturas de pasta de celulosa"),
    ("49", "Productos editoriales, prensa y artes graficas"),
    ("50", "Seda"),
    ("51", "Lana y pelo fino u ordinario; hilados de crin"),
    ("52", "Algodon"),
    ("53", "Las demas fibras textiles vegetales; hilados de papel"),
    ("54", "Filamentos sinteticos o artificiales"),
    ("55", "Fibras sinteticas o artificiales discontinuas"),
    ("56", "Guata, fieltro y tela sin tejer; hilados especiales; cordeles"),
    ("57", "Alfombras y revestimientos para el suelo de materia textil"),
    ("58", "Tejidos especiales; encajes; tapiceria; bordados"),
    ("59", "Telas impregnadas, recubiertas o estratificadas"),
    ("60", "Tejidos de punto"),
    ("61", "Prendas y complementos de vestir, de punto"),
    ("62", "Prendas y complementos de vestir, excepto los de punto"),
    ("63", "Los demas articulos textiles confeccionados; ropa usada"),
    ("64", "Calzado, polainas y articulos analogos"),
    ("65", "Sombreros, demas tocados y sus partes"),
    ("66", "Paraguas, sombrillas, bastones y sus partes"),
    ("67", "Plumas y plumon; flores artificiales; manufacturas de cabello"),
    ("68", "Manufacturas de piedra, yeso, cemento, amianto o mica"),
    ("69", "Productos ceramicos"),
    ("70", "Vidrio y manufacturas de vidrio"),
    ("71", "Perlas, piedras preciosas, metales preciosos; bisuteria; monedas"),
    ("72", "Fundicion, hierro y acero"),
    ("73", "Manufacturas de fundicion, hierro o acero"),
    ("74", "Cobre y sus manufacturas"),
    ("75", "Niquel y sus manufacturas"),
    ("76", "Aluminio y sus manufacturas"),
    ("78", "Plomo y sus manufacturas"),
    ("79", "Cinc y sus manufacturas"),
    ("80", "Estano y sus manufacturas"),
    ("81", "Los demas metales comunes; cermets"),
    ("82", "Herramientas y articulos de cuchilleria"),
    ("83", "Manufacturas diversas de metales comunes"),
    ("84", "Reactores nucleares, calderas, maquinas y aparatos mecanicos"),
    ("85", "Maquinas y aparatos electricos; aparatos de grabacion y reproduccion"),
    ("86", "Vehiculos y material para vias ferreas"),
    ("87", "Vehiculos automoviles, tractores y demas vehiculos terrestres"),
    ("88", "Aeronaves, vehiculos espaciales y sus partes"),
    ("89", "Barcos y demas artefactos flotantes"),
    ("90", "Instrumentos de optica, medida, control o precision; medico quirurgicos"),
    ("91", "Aparatos de relojeria y sus partes"),
    ("92", "Instrumentos musicales"),
    ("93", "Armas, municiones y sus partes"),
    ("94", "Muebles; aparatos de alumbrado; construcciones prefabricadas"),
    ("95", "Juguetes, juegos y articulos para recreo o deporte"),
    ("96", "Manufacturas diversas"),
    ("97", "Objetos de arte o coleccion y antiguedades"),
    ("98", "Disposiciones de tratamiento especial"),
    ("99", "Disposiciones especiales"),
]

HS_SECTIONS = [
    ("I", "Animales vivos y productos del reino animal", 1, 5),
    ("II", "Productos del reino vegetal", 6, 14),
    ("III", "Grasas y aceites animales o vegetales", 15, 15),
    ("IV", "Alimentos, bebidas, tabaco y sucedaneos", 16, 24),
    ("V", "Productos minerales", 25, 27),
    ("VI", "Productos de las industrias quimicas", 28, 38),
    ("VII", "Plasticos, caucho y sus manufacturas", 39, 40),
    ("VIII", "Pieles, cueros, peleteria y articulos", 41, 43),
    ("IX", "Madera, carbon vegetal, corcho y manufacturas", 44, 46),
    ("X", "Pasta de madera, papel y carton", 47, 49),
    ("XI", "Materias textiles y sus manufacturas", 50, 63),
    ("XII", "Calzado, sombreros y otros articulos", 64, 67),
    ("XIII", "Piedra, yeso, cemento, ceramica y vidrio", 68, 70),
    ("XIV", "Perlas, metales preciosos y bisuteria", 71, 71),
    ("XV", "Metales comunes y sus manufacturas", 72, 83),
    ("XVI", "Maquinas, aparatos y material electrico", 84, 85),
    ("XVII", "Material de transporte", 86, 89),
    ("XVIII", "Instrumentos de precision, relojeria y musica", 90, 92),
    ("XIX", "Armas, municiones y partes", 93, 93),
    ("XX", "Mercancias y productos diversos", 94, 96),
    ("XXI", "Objetos de arte, coleccion o antiguedades", 97, 99),
]


def hs_autocomplete(query: str, limit: int = 20, db_path: Path = db.DB_PATH) -> list[dict]:
    digits = _normalize_code(query)
    if digits:
        if not db_path.exists():
            db.init_db(db_path)
        with db.connect(db_path, read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT item.code, item.description, source.priority
                FROM catalog_item AS item
                LEFT JOIN catalog_source AS source ON source.source_code = item.source_code
                WHERE item.code = ? OR item.code LIKE ? OR ? LIKE item.code || '%'
                ORDER BY
                    CASE
                        WHEN item.code = ? THEN 0
                        WHEN item.code LIKE ? THEN 1
                        ELSE 2
                    END,
                    source.priority ASC,
                    item.code_level DESC,
                    item.code
                LIMIT ?
                """,
                [digits, f"{digits}%", digits, digits, f"{digits}%", limit],
            ).fetchall()
        return [
            {
                "label": f"{_format_hs_code(row[0])} - {str(row[1])[:86]}",
                "value": row[0],
            }
            for row in rows
        ]
    return [
        {
            "label": f'{_format_hs_code(row["code"])} - {row["description"][:86]}',
            "value": row["code"],
        }
        for row in search_tigie(query, limit, db_path)
    ]


def hs_explorer_detail(code: str, db_path: Path = db.DB_PATH) -> dict:
    if not db_path.exists():
        db.init_db(db_path)
    digits = _normalize_code(code)
    if not digits:
        return {}

    with db.connect(db_path, read_only=True) as conn:
        exact = conn.execute(
            """
            SELECT item.code, item.description, item.source_code, item.country_scope,
                   item.source_file, item.source_url, item.code_level, source.source_name
            FROM catalog_item AS item
            LEFT JOIN catalog_source AS source ON source.source_code = item.source_code
            WHERE item.code = ?
            ORDER BY source.priority ASC
            LIMIT 1
            """,
            [digits],
        ).fetchone()
        if not exact:
            exact = conn.execute(
                """
                SELECT item.code, item.description, item.source_code, item.country_scope,
                       item.source_file, item.source_url, item.code_level, source.source_name
                FROM catalog_item AS item
                LEFT JOIN catalog_source AS source ON source.source_code = item.source_code
                WHERE item.code LIKE ? OR ? LIKE item.code || '%'
                ORDER BY ABS(LENGTH(item.code) - ?) ASC, source.priority ASC, item.code
                LIMIT 1
                """,
                [f"{digits}%", digits, len(digits)],
            ).fetchone()
        if not exact:
            return {}

        selected_code = exact[0]
        prefixes = [selected_code[:level] for level in (2, 4, 6, 8, 10) if len(selected_code) >= level]
        placeholders = ",".join("?" for _ in prefixes)
        ancestors = conn.execute(
            f"""
            SELECT item.code, item.description, item.code_level, item.country_scope,
                   item.source_code, source.source_name
            FROM catalog_item AS item
            LEFT JOIN catalog_source AS source ON source.source_code = item.source_code
            WHERE item.code IN ({placeholders})
            ORDER BY item.code_level ASC, source.priority ASC
            """,
            prefixes,
        ).fetchall() if prefixes else []

        children = conn.execute(
            """
            SELECT item.code, item.description, item.code_level, item.country_scope,
                   source.source_name
            FROM catalog_item AS item
            LEFT JOIN catalog_source AS source ON source.source_code = item.source_code
            WHERE item.code LIKE ? AND LENGTH(item.code) > ?
            ORDER BY item.code_level ASC, item.code
            LIMIT 8
            """,
            [f"{selected_code}%", len(selected_code)],
        ).fetchall()

    section = _hs_section(selected_code)
    hierarchy = _hierarchy_rows(selected_code, ancestors)
    child_products = []
    for child in children:
        for term in _description_terms(child[1], 2):
            if term not in child_products:
                child_products.append(term)
        if len(child_products) >= 6:
            break
    synonyms = _description_terms(exact[1], 7)
    return {
        "code": selected_code,
        "display_code": _format_hs_code(selected_code),
        "description": exact[1],
        "source_code": exact[2],
        "scope": exact[3],
        "source_file": exact[4],
        "source_url": exact[5],
        "level": exact[6],
        "source": exact[7] or exact[2],
        "section": section,
        "hierarchy": hierarchy,
        "children": [
            {
                "code": row[0],
                "display_code": _format_hs_code(row[0]),
                "description": row[1],
                "level": row[2],
                "scope": row[3],
                "source": row[4],
            }
            for row in children
        ],
        "synonyms": synonyms or child_products[:5],
        "typical_products": _description_terms(exact[1], 5) or child_products[:5],
        "duty": "No estructurado en el catalogo local",
        "rules": "No estructurado en el catalogo local",
        "notes": _notes_for_row(exact),
    }


def tariff_operational_file(code: str, db_path: Path = db.DB_PATH) -> dict:
    """Return the operational dossier for a fraction/NICO code."""
    if not db_path.exists():
        db.init_db(db_path)
    digits = _normalize_code(code)
    if not digits:
        return {}
    candidates = [digits]
    if len(digits) > 8:
        candidates.append(digits[:8])
    if len(digits) > 6:
        candidates.append(digits[:6])

    with db.connect(db_path, read_only=True) as conn:
        selected = None
        for candidate in candidates:
            selected = conn.execute(
                """
                SELECT code, fraccion8, nico10, hs2, hs4, hs6, description,
                       source_code, country_scope, source_file, source_url
                FROM catalog_tariff_fraction
                WHERE code = ?
                """,
                [candidate],
            ).fetchone()
            if selected:
                break
        if not selected:
            selected = conn.execute(
                """
                SELECT code, fraccion8, nico10, hs2, hs4, hs6, description,
                       source_code, country_scope, source_file, source_url
                FROM catalog_tariff_fraction
                WHERE code LIKE ? OR ? LIKE code || '%'
                ORDER BY ABS(LENGTH(code) - ?) ASC, country_scope DESC, code
                LIMIT 1
                """,
                [f"{digits}%", digits, len(digits)],
            ).fetchone()
        if not selected:
            return {}

        selected_code = selected[0]
        fraccion8 = selected[1] or (selected_code[:8] if len(selected_code) >= 8 else selected_code)
        nicos = conn.execute(
            """
            SELECT nico10, nico, description, source_code, source_file
            FROM catalog_tariff_nico
            WHERE fraccion8 = ?
            ORDER BY nico10
            LIMIT 24
            """,
            [fraccion8],
        ).fetchall()
        rates = conn.execute(
            """
            SELECT tax_code, tax_name, import_rate, export_rate, unit_name,
                   effective_from, effective_to, source_code
            FROM catalog_tariff_rate
            WHERE code = ? OR code = ?
            ORDER BY tax_code
            """,
            [selected_code, fraccion8],
        ).fetchall()
        regulations = conn.execute(
            """
            SELECT reg.regulation_type, reg.regulation_code, reg.title,
                   rel.scope_note, rel.applies_to, reg.authority, rel.source_code
            FROM tariff_fraction_regulation AS rel
            JOIN tariff_regulation AS reg USING (regulation_id)
            WHERE rel.code = ? OR rel.code = ?
            ORDER BY reg.regulation_type, reg.regulation_code
            """,
            [selected_code, fraccion8],
        ).fetchall()

    return {
        "code": selected_code,
        "display_code": _format_hs_code(selected_code),
        "fraccion8": fraccion8,
        "nico10": selected[2],
        "hs2": selected[3],
        "hs4": selected[4],
        "hs6": selected[5],
        "description": selected[6],
        "source_code": selected[7],
        "scope": selected[8],
        "source_file": selected[9],
        "source_url": selected[10],
        "nicos": [
            {
                "nico10": row[0],
                "nico": row[1],
                "description": row[2],
                "source": row[3],
                "source_file": row[4],
            }
            for row in nicos
        ],
        "rates": [
            {
                "tax_code": row[0],
                "tax_name": row[1],
                "import_rate": row[2],
                "export_rate": row[3],
                "unit_name": row[4],
                "effective_from": str(row[5]) if row[5] else "",
                "effective_to": str(row[6]) if row[6] else "",
                "source": row[7],
            }
            for row in rates
        ],
        "regulations": [
            {
                "type": row[0],
                "code": row[1],
                "title": row[2],
                "scope_note": row[3],
                "applies_to": row[4],
                "authority": row[5],
                "source": row[6],
            }
            for row in regulations
        ],
    }


def _hs_section(code: str) -> dict:
    chapter = int(code[:2]) if len(code) >= 2 and code[:2].isdigit() else 0
    for number, title, first, last in HS_SECTIONS:
        if first <= chapter <= last:
            return {"number": number, "title": title, "range": f"{first:02d}-{last:02d}"}
    return {"number": "n.d.", "title": "Seccion no determinada", "range": ""}


def _hierarchy_rows(selected_code: str, rows: list[tuple]) -> list[dict]:
    labels = {2: "Chapter", 4: "HS heading", 6: "Subheading", 8: "Fraccion", 10: "NICO"}
    found: dict[int, tuple] = {}
    for row in rows:
        found.setdefault(int(row[2] or len(row[0])), row)
    result = []
    for level in (2, 4, 6, 8, 10):
        if len(selected_code) < level:
            continue
        row = found.get(level)
        result.append({
            "step": labels[level],
            "code": selected_code[:level],
            "display_code": _format_hs_code(selected_code[:level]),
            "description": row[1] if row else "Sin descripcion local para este nivel",
            "scope": row[3] if row else "",
            "source": (row[5] or row[4]) if row else "",
        })
    return result


def _format_hs_code(code: str) -> str:
    code = str(code or "")
    if len(code) <= 2:
        return code
    if len(code) <= 4:
        return f"{code[:2]}.{code[2:]}"
    if len(code) <= 6:
        return f"{code[:2]}.{code[2:4]}.{code[4:]}"
    if len(code) <= 8:
        return f"{code[:2]}.{code[2:4]}.{code[4:6]}.{code[6:]}"
    return f"{code[:2]}.{code[2:4]}.{code[4:6]}.{code[6:8]}.{code[8:]}"


def _description_terms(description: str, limit: int) -> list[str]:
    stop = {"los", "las", "para", "con", "sin", "del", "las", "una", "unos", "otras", "otros", "demas", "incluidos"}
    words = []
    spanish_letters = r"A-Za-z\u00c1\u00c9\u00cd\u00d3\u00da\u00dc\u00d1\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1"
    for word in re.findall(fr"[{spanish_letters}]{{4,}}", description or ""):
        clean = normalize_text(word)
        if clean not in stop and clean not in words:
            words.append(clean)
    return words[:limit]


def _notes_for_row(row: tuple) -> str:
    scope = "Mexico" if row[3] == "MX" else "global"
    source = row[7] or row[2]
    return f"Registro {scope}; fuente: {source}. Verifica TIGIE/NICO vigente antes de clasificar o calcular contribuciones."


def _score_catalog_row(
    query_terms: list[str],
    query_digits: str,
    code: str,
    normalized_search_text: str,
    scope: str,
) -> int:
    score = 0
    if query_digits:
        if code == query_digits:
            score += 80
        elif code.startswith(query_digits):
            score += 30
        elif query_digits.startswith(code):
            score += 14
    for term in query_terms:
        if term == code:
            score += 40
        elif term in normalized_search_text:
            score += 8 if len(term) > 3 else 2
    if scope == "MX":
        score += 1
    return score


def catalog_summary() -> dict:
    if not db.DB_PATH.exists():
        return {"initialized": False, "items": 0, "sources": [], "by_scope": {}, "by_source": {}, "last_refresh": {}}
    with db.connect(read_only=True) as conn:
        count = conn.execute("SELECT COUNT(*) FROM catalog_item").fetchone()[0]
        by_scope = {
            r[0]: int(r[1])
            for r in conn.execute(
                "SELECT country_scope, COUNT(*) FROM catalog_item GROUP BY country_scope"
            ).fetchall()
        }
        by_source = {
            r[0]: int(r[1])
            for r in conn.execute(
                "SELECT source_code, COUNT(*) FROM catalog_item GROUP BY source_code"
            ).fetchall()
        }
        sources = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT source_file FROM catalog_item WHERE source_file IS NOT NULL LIMIT 10"
            ).fetchall()
        ]
        last = conn.execute(
            """
            SELECT status, started_at, finished_at, source_codes, records_loaded, message
            FROM catalog_refresh_run
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()
    return {
        "initialized": True,
        "items": int(count),
        "sources": sources,
        "by_scope": by_scope,
        "by_source": by_source,
        "last_refresh": {
            "status": last[0],
            "started_at": str(last[1]) if last and last[1] else "",
            "finished_at": str(last[2]) if last and last[2] else "",
            "source_codes": last[3] if last else "",
            "records_loaded": int(last[4]) if last and last[4] is not None else 0,
            "message": last[5] if last else "",
        } if last else {},
    }
