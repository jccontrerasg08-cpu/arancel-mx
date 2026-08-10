"""DuckDB access and migrations for operational comex data."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
import traceback
from typing import Iterator

import duckdb

from .paths import DB_PATH, ensure_data_dirs


def _sql_identifier(value: str) -> str:
    clean = str(value)
    if not clean or clean[0].isdigit() or not clean.replace("_", "").isalnum():
        raise ValueError(f"Invalid SQL identifier: {value!r}")
    return clean


MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS dim_country (
        country_key BIGINT PRIMARY KEY,
        canonical_name VARCHAR NOT NULL,
        iso3 VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_country_name ON dim_country(canonical_name);

    CREATE TABLE IF NOT EXISTS dim_flow (
        flow_key BIGINT PRIMARY KEY,
        flow_code VARCHAR NOT NULL,
        flow_name VARCHAR NOT NULL
    );
    INSERT OR IGNORE INTO dim_flow VALUES
        (1, 'IMPORT', 'Importacion'),
        (2, 'EXPORT', 'Exportacion');

    CREATE TABLE IF NOT EXISTS dim_source (
        source_key BIGINT PRIMARY KEY,
        source_code VARCHAR NOT NULL,
        source_name VARCHAR NOT NULL,
        source_url VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_source_code ON dim_source(source_code);

    CREATE TABLE IF NOT EXISTS load_run (
        load_run_id BIGINT PRIMARY KEY,
        source_code VARCHAR NOT NULL,
        mode VARCHAR NOT NULL,
        status VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL,
        finished_at TIMESTAMP,
        records_read BIGINT DEFAULT 0,
        records_loaded BIGINT DEFAULT 0,
        message VARCHAR,
        artifact_path VARCHAR
    );

    CREATE TABLE IF NOT EXISTS fact_trade_monthly (
        date_month DATE NOT NULL,
        year SMALLINT NOT NULL,
        month SMALLINT NOT NULL,
        flow_code VARCHAR NOT NULL,
        country_name VARCHAR NOT NULL,
        country_iso3 VARCHAR,
        tariff_code VARCHAR NOT NULL,
        tariff_level SMALLINT NOT NULL,
        hs2 VARCHAR,
        hs4 VARCHAR,
        hs6 VARCHAR,
        fraccion8 VARCHAR,
        nico10 VARCHAR,
        tariff_description VARCHAR,
        unit_name VARCHAR,
        quantity DOUBLE,
        value_usd DOUBLE,
        source_code VARCHAR NOT NULL,
        source_file VARCHAR,
        source_revision VARCHAR,
        load_run_id BIGINT,
        record_hash VARCHAR NOT NULL,
        inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (date_month, flow_code, country_name, tariff_code, source_code)
    );
    CREATE INDEX IF NOT EXISTS ix_fact_trade_monthly_nico10 ON fact_trade_monthly(nico10);
    CREATE INDEX IF NOT EXISTS ix_fact_trade_monthly_fraccion8 ON fact_trade_monthly(fraccion8);
    CREATE INDEX IF NOT EXISTS ix_fact_trade_monthly_hs6 ON fact_trade_monthly(hs6);

    CREATE TABLE IF NOT EXISTS fact_trade_monthly_history AS
    SELECT * FROM fact_trade_monthly WHERE 1=0;

    CREATE TABLE IF NOT EXISTS dim_nico_catalog (
        nico10 VARCHAR PRIMARY KEY,
        fraccion8 VARCHAR NOT NULL,
        nico VARCHAR NOT NULL,
        description VARCHAR,
        source_file VARCHAR,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_dim_nico_catalog_fraccion8 ON dim_nico_catalog(fraccion8);
    """,
    """
    CREATE TABLE IF NOT EXISTS etl_file_registry (
        file_path VARCHAR PRIMARY KEY,
        parser_name VARCHAR NOT NULL,
        file_hash VARCHAR NOT NULL,
        processed_at TIMESTAMP NOT NULL,
        load_run_id BIGINT
    );

    CREATE TABLE IF NOT EXISTS etl_error_log (
        error_id BIGINT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        context VARCHAR,
        file_path VARCHAR,
        error_message VARCHAR,
        traceback VARCHAR
    );

    CREATE TABLE IF NOT EXISTS vucem_tigie_items (
        code VARCHAR PRIMARY KEY,
        description VARCHAR NOT NULL,
        source_file VARCHAR,
        raw_text VARCHAR,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS vucem_notifications (
        notification_id VARCHAR PRIMARY KEY,
        rfc VARCHAR,
        title VARCHAR,
        body VARCHAR,
        source_file VARCHAR,
        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS anam_public_pages (
        page_key VARCHAR PRIMARY KEY,
        url VARCHAR NOT NULL,
        title VARCHAR,
        source_file VARCHAR,
        sha256 VARCHAR,
        fetched_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS anam_trade_agreements (
        agreement_key VARCHAR PRIMARY KEY,
        page_key VARCHAR NOT NULL,
        title VARCHAR,
        url VARCHAR NOT NULL,
        host VARCHAR,
        dof_code VARCHAR,
        published_date VARCHAR,
        source_file VARCHAR,
        sha256 VARCHAR,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_anam_trade_agreements_page ON anam_trade_agreements(page_key);

    CREATE TABLE IF NOT EXISTS dof_publication (
        publication_id VARCHAR PRIMARY KEY,
        title VARCHAR NOT NULL,
        url VARCHAR NOT NULL,
        published_date VARCHAR,
        dof_code VARCHAR,
        section VARCHAR,
        topic VARCHAR,
        summary VARCHAR,
        source_file VARCHAR,
        indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_dof_publication_date ON dof_publication(published_date);
    CREATE INDEX IF NOT EXISTS ix_dof_publication_topic ON dof_publication(topic);
    """,
    """
    CREATE TABLE IF NOT EXISTS catalog_source (
        source_code VARCHAR PRIMARY KEY,
        source_name VARCHAR NOT NULL,
        country_scope VARCHAR NOT NULL,
        source_url VARCHAR,
        priority SMALLINT NOT NULL,
        enabled BOOLEAN DEFAULT TRUE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    INSERT OR IGNORE INTO catalog_source VALUES
        ('snice-nico', 'SNICE NICO/LIGIE', 'MX', 'https://www.snice.gob.mx', 10, TRUE, CURRENT_TIMESTAMP),
        ('vucem-tigie', 'VUCEM TIGIE', 'MX', 'https://www.ventanillaunica.gob.mx/Clasificador', 20, TRUE, CURRENT_TIMESTAMP),
        ('hs-global', 'World Bank/WITS HSProducts', 'GLOBAL', 'https://wits.worldbank.org/data/public/HSProducts.xls', 80, TRUE, CURRENT_TIMESTAMP);

    CREATE TABLE IF NOT EXISTS catalog_item (
        item_key VARCHAR PRIMARY KEY,
        code VARCHAR NOT NULL,
        code_level SMALLINT NOT NULL,
        description VARCHAR NOT NULL,
        normalized_description VARCHAR NOT NULL,
        normalized_search_text VARCHAR NOT NULL,
        source_code VARCHAR NOT NULL,
        country_scope VARCHAR NOT NULL,
        source_file VARCHAR,
        source_url VARCHAR,
        raw_text VARCHAR,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_catalog_item_code ON catalog_item(code);
    CREATE INDEX IF NOT EXISTS ix_catalog_item_source ON catalog_item(source_code);
    CREATE INDEX IF NOT EXISTS ix_catalog_item_scope ON catalog_item(country_scope);
    CREATE INDEX IF NOT EXISTS ix_catalog_item_level ON catalog_item(code_level);

    CREATE TABLE IF NOT EXISTS catalog_refresh_run (
        refresh_run_id BIGINT PRIMARY KEY,
        status VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL,
        finished_at TIMESTAMP,
        source_codes VARCHAR,
        records_loaded BIGINT DEFAULT 0,
        message VARCHAR
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS dashboard_country_balance (
        country_name VARCHAR,
        iso3 VARCHAR NOT NULL,
        balance_mdd DOUBLE,
        period VARCHAR NOT NULL,
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (period, iso3)
    );

    CREATE TABLE IF NOT EXISTS dashboard_customs_revenue (
        customs_name VARCHAR,
        cve VARCHAR NOT NULL,
        customs_type VARCHAR,
        lat DOUBLE,
        lon DOUBLE,
        total_mdp DOUBLE,
        iva_mdp DOUBLE,
        igi_mdp DOUBLE,
        dta_mdp DOUBLE,
        ieps_mdp DOUBLE,
        isan_mdp DOUBLE,
        otros_mdp DOUBLE,
        variation_pct DOUBLE,
        period VARCHAR NOT NULL,
        saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (period, cve)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS warehouse_snapshot (
        snapshot_id BIGINT PRIMARY KEY,
        source_code VARCHAR NOT NULL,
        source_file VARCHAR,
        source_mtime DOUBLE,
        fuente VARCHAR,
        actualizado TIMESTAMP,
        completo BOOLEAN,
        status VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL,
        finished_at TIMESTAMP,
        records_loaded BIGINT DEFAULT 0,
        message VARCHAR
    );

    CREATE TABLE IF NOT EXISTS dim_banxico_series (
        series_id VARCHAR PRIMARY KEY,
        nombre VARCHAR NOT NULL,
        flujo VARCHAR,
        grupo VARCHAR,
        unit_name VARCHAR,
        source_code VARCHAR DEFAULT 'banxico-sie',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS fact_banxico_series_monthly (
        series_id VARCHAR NOT NULL,
        date_month DATE NOT NULL,
        value DOUBLE,
        source_code VARCHAR DEFAULT 'banxico-sie',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (series_id, date_month)
    );
    CREATE INDEX IF NOT EXISTS ix_fact_banxico_series_monthly_date
        ON fact_banxico_series_monthly(date_month);

    CREATE TABLE IF NOT EXISTS fact_dashboard_annual (
        period VARCHAR PRIMARY KEY,
        exports_mdd DOUBLE,
        imports_mdd DOUBLE,
        balance_mdd DOUBLE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS fact_dashboard_accumulated (
        label VARCHAR NOT NULL,
        year VARCHAR NOT NULL,
        exports_mdd DOUBLE,
        imports_mdd DOUBLE,
        balance_mdd DOUBLE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (label, year)
    );

    CREATE TABLE IF NOT EXISTS fact_country_balance (
        period VARCHAR NOT NULL,
        country_name VARCHAR NOT NULL,
        iso3 VARCHAR NOT NULL,
        balance_mdd DOUBLE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (period, iso3)
    );
    CREATE INDEX IF NOT EXISTS ix_fact_country_balance_iso3 ON fact_country_balance(iso3);

    CREATE TABLE IF NOT EXISTS dim_customs (
        cve VARCHAR PRIMARY KEY,
        customs_name VARCHAR NOT NULL,
        customs_type VARCHAR,
        lat DOUBLE,
        lon DOUBLE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS fact_customs_revenue (
        period VARCHAR NOT NULL,
        cve VARCHAR NOT NULL,
        total_mdp DOUBLE,
        iva_mdp DOUBLE,
        igi_mdp DOUBLE,
        dta_mdp DOUBLE,
        ieps_mdp DOUBLE,
        isan_mdp DOUBLE,
        otros_mdp DOUBLE,
        previous_total_mdp DOUBLE,
        variation_pct DOUBLE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (period, cve)
    );
    CREATE INDEX IF NOT EXISTS ix_fact_customs_revenue_cve ON fact_customs_revenue(cve);

    CREATE TABLE IF NOT EXISTS fact_trade_component (
        component_group VARCHAR NOT NULL,
        component_name VARCHAR NOT NULL,
        period VARCHAR NOT NULL,
        value_mdd DOUBLE,
        sort_order SMALLINT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (component_group, component_name, period)
    );

    CREATE TABLE IF NOT EXISTS dashboard_cache_payload (
        cache_key VARCHAR PRIMARY KEY,
        payload_json VARCHAR NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS catalog_tariff_fraction (
        code VARCHAR PRIMARY KEY,
        fraccion8 VARCHAR,
        nico10 VARCHAR,
        hs2 VARCHAR,
        hs4 VARCHAR,
        hs6 VARCHAR,
        description VARCHAR NOT NULL,
        source_code VARCHAR NOT NULL,
        country_scope VARCHAR NOT NULL,
        source_file VARCHAR,
        source_url VARCHAR,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_catalog_tariff_fraction_fraccion8 ON catalog_tariff_fraction(fraccion8);
    CREATE INDEX IF NOT EXISTS ix_catalog_tariff_fraction_hs6 ON catalog_tariff_fraction(hs6);

    CREATE TABLE IF NOT EXISTS catalog_tariff_nico (
        nico10 VARCHAR PRIMARY KEY,
        fraccion8 VARCHAR NOT NULL,
        nico VARCHAR NOT NULL,
        description VARCHAR,
        source_code VARCHAR,
        source_file VARCHAR,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_catalog_tariff_nico_fraccion8 ON catalog_tariff_nico(fraccion8);

    CREATE TABLE IF NOT EXISTS catalog_tariff_rate (
        rate_id VARCHAR PRIMARY KEY,
        code VARCHAR NOT NULL,
        tax_code VARCHAR NOT NULL,
        tax_name VARCHAR,
        import_rate VARCHAR,
        export_rate VARCHAR,
        unit_name VARCHAR,
        effective_from DATE,
        effective_to DATE,
        source_code VARCHAR,
        source_file VARCHAR,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_catalog_tariff_rate_code ON catalog_tariff_rate(code);

    CREATE TABLE IF NOT EXISTS tariff_regulation (
        regulation_id VARCHAR PRIMARY KEY,
        regulation_type VARCHAR NOT NULL,
        regulation_code VARCHAR NOT NULL,
        title VARCHAR,
        description VARCHAR,
        authority VARCHAR,
        source_code VARCHAR,
        source_url VARCHAR,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tariff_fraction_regulation (
        code VARCHAR NOT NULL,
        regulation_id VARCHAR NOT NULL,
        scope_note VARCHAR,
        applies_to VARCHAR,
        effective_from DATE,
        effective_to DATE,
        source_code VARCHAR,
        source_file VARCHAR,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (code, regulation_id)
    );
    CREATE INDEX IF NOT EXISTS ix_tariff_fraction_regulation_code
        ON tariff_fraction_regulation(code);

    CREATE TABLE IF NOT EXISTS pedimento (
        pedimento_id VARCHAR PRIMARY KEY,
        pedimento_number VARCHAR,
        operation_type VARCHAR,
        customs_code VARCHAR,
        rfc_importer VARCHAR,
        rfc_exporter VARCHAR,
        broker_patent VARCHAR,
        payment_date DATE,
        source_file VARCHAR,
        extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS pedimento_item (
        item_id VARCHAR PRIMARY KEY,
        pedimento_id VARCHAR NOT NULL,
        sequence_number VARCHAR,
        code VARCHAR,
        nico10 VARCHAR,
        description VARCHAR,
        quantity DOUBLE,
        unit_name VARCHAR,
        value_usd DOUBLE,
        origin_country VARCHAR,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS ix_pedimento_item_pedimento ON pedimento_item(pedimento_id);
    CREATE INDEX IF NOT EXISTS ix_pedimento_item_code ON pedimento_item(code);
    """,
]


ARANCEL_SCHEMA = """
CREATE TABLE IF NOT EXISTS source_registry (
    dataset_key VARCHAR PRIMARY KEY,
    registry_version VARCHAR NOT NULL,
    canonical_page VARCHAR NOT NULL,
    source_role VARCHAR NOT NULL,
    authoritative_for_tariff BOOLEAN NOT NULL,
    authoritative_for_discovery BOOLEAN NOT NULL,
    authoritative_for_consolidated_text BOOLEAN NOT NULL,
    legal_publication_authority VARCHAR NOT NULL,
    config_json VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS source_discovery_run (
    discovery_run_id VARCHAR PRIMARY KEY,
    registry_version VARCHAR NOT NULL,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status VARCHAR NOT NULL,
    previous_manifest_sha256 VARCHAR,
    proposed_manifest_sha256 VARCHAR,
    summary_json VARCHAR
);

CREATE TABLE IF NOT EXISTS source_discovery_item (
    discovery_run_id VARCHAR NOT NULL,
    item_id VARCHAR NOT NULL,
    dataset_key VARCHAR NOT NULL,
    document_role VARCHAR NOT NULL,
    discovery_url VARCHAR NOT NULL,
    source_url VARCHAR NOT NULL,
    title VARCHAR,
    displayed_date DATE,
    media_type VARCHAR,
    reported_size BIGINT,
    content_sha256 VARCHAR,
    change_type VARCHAR,
    PRIMARY KEY (discovery_run_id, item_id)
);

CREATE TABLE IF NOT EXISTS source_capture (
    capture_id VARCHAR PRIMARY KEY,
    source_document_id VARCHAR,
    dataset_key VARCHAR NOT NULL,
    document_role VARCHAR NOT NULL,
    source_url VARCHAR NOT NULL,
    local_path VARCHAR NOT NULL,
    media_type VARCHAR,
    byte_size BIGINT NOT NULL,
    source_sha256 VARCHAR NOT NULL,
    parser_version VARCHAR,
    schema_version VARCHAR,
    registry_version VARCHAR NOT NULL,
    observed_at DATE NOT NULL,
    retrieved_at TIMESTAMP NOT NULL,
    manifest_json VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS staging_arancel_row (
    staging_row_id VARCHAR PRIMARY KEY,
    capture_id VARCHAR NOT NULL,
    dataset_key VARCHAR NOT NULL,
    document_role VARCHAR NOT NULL,
    sheet_name VARCHAR,
    source_row_number BIGINT,
    parser_version VARCHAR NOT NULL,
    raw_json VARCHAR NOT NULL,
    normalized_json VARCHAR NOT NULL,
    row_status VARCHAR NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS arancel_quarantine (
    quarantine_id VARCHAR PRIMARY KEY,
    staging_row_id VARCHAR NOT NULL,
    reason_code VARCHAR NOT NULL,
    reason_detail VARCHAR,
    blocking BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS source_document (
    source_document_id VARCHAR PRIMARY KEY,
    authority VARCHAR NOT NULL,
    publication_venue VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    source_url VARCHAR NOT NULL,
    media_type VARCHAR,
    sha256 VARCHAR NOT NULL,
    local_path VARCHAR,
    published_at DATE,
    effective_from DATE,
    effective_to DATE,
    observed_at DATE NOT NULL,
    retrieved_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS hs_code (
    classification_id VARCHAR PRIMARY KEY,
    code VARCHAR NOT NULL,
    level VARCHAR NOT NULL CHECK (level IN ('hs2', 'hs4', 'hs6')),
    hs2 VARCHAR,
    hs4 VARCHAR,
    hs6 VARCHAR,
    description VARCHAR NOT NULL,
    ligie_version VARCHAR NOT NULL,
    validity_basis VARCHAR NOT NULL CHECK (validity_basis IN ('legal', 'observed_snapshot', 'unknown')),
    updated_at DATE,
    published_at DATE,
    classification_effective_from DATE,
    classification_effective_to DATE,
    source_document_id VARCHAR NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_hs_code_code ON hs_code(code);

CREATE TABLE IF NOT EXISTS tariff_fraction (
    fraction_revision_id VARCHAR PRIMARY KEY,
    code VARCHAR NOT NULL,
    hs2 VARCHAR NOT NULL,
    hs4 VARCHAR NOT NULL,
    hs6 VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    ligie_version VARCHAR NOT NULL,
    validity_basis VARCHAR NOT NULL CHECK (validity_basis IN ('legal', 'observed_snapshot', 'unknown')),
    updated_at DATE,
    published_at DATE,
    classification_effective_from DATE,
    classification_effective_to DATE,
    source_document_id VARCHAR NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_arancel_fraction_code ON tariff_fraction(code);

CREATE TABLE IF NOT EXISTS nico (
    nico_revision_id VARCHAR PRIMARY KEY,
    nico10 VARCHAR NOT NULL,
    fraccion8 VARCHAR NOT NULL,
    nico2 VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    ligie_version VARCHAR NOT NULL,
    validity_basis VARCHAR NOT NULL CHECK (validity_basis IN ('legal', 'observed_snapshot', 'unknown')),
    updated_at DATE,
    published_at DATE,
    classification_effective_from DATE,
    classification_effective_to DATE,
    source_document_id VARCHAR NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_arancel_nico10 ON nico(nico10);
CREATE INDEX IF NOT EXISTS ix_arancel_nico_parent ON nico(fraccion8);

CREATE TABLE IF NOT EXISTS nico_version (
    nico_version_id VARCHAR PRIMARY KEY,
    nico10 VARCHAR NOT NULL,
    fraccion8 VARCHAR NOT NULL,
    nico2 VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    legal_status VARCHAR NOT NULL DEFAULT 'current',
    effective_from DATE,
    effective_to DATE,
    source_document_id VARCHAR NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_nico_version_code ON nico_version(nico10);

CREATE TABLE IF NOT EXISTS nico_amendment (
    nico_amendment_id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    dof_codigo VARCHAR,
    published_at DATE,
    effective_from DATE,
    source_document_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS nico_amendment_line (
    nico_amendment_id VARCHAR NOT NULL,
    line_id VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    nico10 VARCHAR,
    fraccion8 VARCHAR,
    description VARCHAR,
    PRIMARY KEY (nico_amendment_id, line_id)
);

CREATE TABLE IF NOT EXISTS nico_proposal_batch (
    proposal_batch_id VARCHAR PRIMARY KEY,
    observed_at DATE NOT NULL,
    published_at DATE,
    source_document_id VARCHAR NOT NULL,
    source_sha256 VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS nico_proposal (
    proposal_id VARCHAR PRIMARY KEY,
    proposal_batch_id VARCHAR NOT NULL,
    proposed_nico10 VARCHAR,
    fraccion8 VARCHAR,
    action VARCHAR,
    description VARCHAR,
    legal_status VARCHAR NOT NULL DEFAULT 'proposal'
        CHECK (legal_status = 'proposal')
);

CREATE TABLE IF NOT EXISTS national_note (
    national_note_id VARCHAR PRIMARY KEY,
    chapter VARCHAR,
    note_number VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS national_note_version (
    national_note_version_id VARCHAR PRIMARY KEY,
    national_note_id VARCHAR NOT NULL,
    text VARCHAR NOT NULL,
    effective_from DATE,
    effective_to DATE,
    source_document_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS national_note_amendment (
    national_note_amendment_id VARCHAR PRIMARY KEY,
    national_note_id VARCHAR,
    title VARCHAR NOT NULL,
    dof_codigo VARCHAR,
    published_at DATE,
    effective_from DATE,
    source_document_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS national_note_applicability (
    applicability_id VARCHAR PRIMARY KEY,
    national_note_version_id VARCHAR NOT NULL,
    scope_type VARCHAR NOT NULL,
    scope_value VARCHAR,
    applicability_basis VARCHAR NOT NULL
        CHECK (applicability_basis IN ('explicit', 'unresolved')),
    source_document_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS indicator_methodology (
    methodology_id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    version VARCHAR,
    extraction_status VARCHAR NOT NULL,
    formula_json VARCHAR,
    source_document_id VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS weighted_tariff_indicator (
    indicator_id VARCHAR PRIMARY KEY,
    period DATE NOT NULL,
    hs6 VARCHAR NOT NULL,
    nmf_weighted_rate DECIMAL(18, 6),
    import_value_usd DECIMAL(24, 2),
    source_document_id VARCHAR NOT NULL,
    methodology_id VARCHAR
);

CREATE TABLE IF NOT EXISTS tariff_rate (
    rate_revision_id VARCHAR PRIMARY KEY,
    code VARCHAR NOT NULL,
    unit_code VARCHAR,
    unit_name VARCHAR,
    igi_text VARCHAR,
    igi_kind VARCHAR CHECK (igi_kind IS NULL OR igi_kind IN ('ad_valorem', 'exento', 'prohibida', 'especifica', 'compuesta', 'desconocida')),
    igi_value DECIMAL(18, 6),
    ige_text VARCHAR,
    ige_kind VARCHAR CHECK (ige_kind IS NULL OR ige_kind IN ('ad_valorem', 'exento', 'prohibida', 'especifica', 'compuesta', 'desconocida')),
    ige_value DECIMAL(18, 6),
    ligie_version VARCHAR NOT NULL,
    updated_at DATE,
    published_at DATE,
    rate_effective_from DATE,
    rate_effective_to DATE,
    source_document_id VARCHAR NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_arancel_rate_code ON tariff_rate(code);

CREATE TABLE IF NOT EXISTS canonical_record (
    record_id VARCHAR PRIMARY KEY,
    record_version INTEGER NOT NULL,
    is_current BOOLEAN NOT NULL,
    code VARCHAR NOT NULL,
    formatted_code VARCHAR NOT NULL,
    level VARCHAR NOT NULL CHECK (level IN ('hs2', 'hs4', 'hs6', 'fraccion8', 'nico10')),
    hs2 VARCHAR,
    hs4 VARCHAR,
    hs6 VARCHAR,
    fraccion8 VARCHAR,
    nico2 VARCHAR,
    nico10 VARCHAR,
    name VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    name_is_derived BOOLEAN NOT NULL,
    unit_code VARCHAR,
    unit_name VARCHAR,
    values_from_level VARCHAR,
    igi_text VARCHAR,
    igi_kind VARCHAR,
    igi_value DECIMAL(18, 6),
    ige_text VARCHAR,
    ige_kind VARCHAR,
    ige_value DECIMAL(18, 6),
    ligie_version VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    record_hash VARCHAR NOT NULL,
    validity_basis VARCHAR NOT NULL,
    updated_at DATE,
    published_at DATE,
    classification_effective_from DATE,
    classification_effective_to DATE,
    rate_effective_from DATE,
    rate_effective_to DATE,
    effective_from DATE,
    effective_to DATE,
    observed_at DATE NOT NULL,
    retrieved_at TIMESTAMP NOT NULL,
    primary_source_document_id VARCHAR NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_canonical_record_code ON canonical_record(code);

CREATE TABLE IF NOT EXISTS record_provenance (
    record_id VARCHAR NOT NULL,
    source_document_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL CHECK (role IN ('base', 'modification', 'nico', 'rate', 'enrichment')),
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (record_id, source_document_id, role)
);

CREATE TABLE IF NOT EXISTS dataset_release (
    dataset_version VARCHAR PRIMARY KEY,
    schema_version VARCHAR NOT NULL,
    ligie_version VARCHAR NOT NULL,
    effective_as_of DATE NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    row_count BIGINT NOT NULL DEFAULT 0,
    validation_status VARCHAR NOT NULL,
    validation_results_json VARCHAR,
    source_documents_json VARCHAR
);
"""


def _table_columns(conn: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    exists = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table],
    ).fetchone()[0]
    if not exists:
        return set()
    return {row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}


def _migrate_legacy_tariff_tables(conn: duckdb.DuckDBPyConnection) -> None:
    if "country_scope" in _table_columns(conn, "tariff_fraction"):
        conn.execute(
            """
            INSERT OR REPLACE INTO catalog_tariff_fraction
            SELECT code, fraccion8, nico10, hs2, hs4, hs6, description,
                   source_code, country_scope, source_file, source_url, loaded_at
            FROM tariff_fraction
            """
        )
        conn.execute("DROP TABLE tariff_fraction")

    if _table_columns(conn, "tariff_nico"):
        conn.execute(
            """
            INSERT OR REPLACE INTO catalog_tariff_nico
            SELECT nico10, fraccion8, nico, description, source_code, source_file, loaded_at
            FROM tariff_nico
            """
        )
        conn.execute("DROP TABLE tariff_nico")

    if "rate_id" in _table_columns(conn, "tariff_rate"):
        conn.execute(
            """
            INSERT OR REPLACE INTO catalog_tariff_rate
            SELECT rate_id, code, tax_code, tax_name, import_rate, export_rate,
                   unit_name, effective_from, effective_to, source_code, source_file, loaded_at
            FROM tariff_rate
            """
        )
        conn.execute("DROP TABLE tariff_rate")


def ensure_arancel_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Install normalized tariff tables after preserving legacy catalog data."""
    _migrate_legacy_tariff_tables(conn)
    conn.execute(ARANCEL_SCHEMA)


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@contextmanager
def connect(db_path: Path = DB_PATH, read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
    ensure_data_dirs()
    conn = duckdb.connect(str(db_path), read_only=read_only)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> Path:
    """Initialize DuckDB with all operational tables."""
    ensure_data_dirs()
    with connect(db_path) as conn:
        for migration in MIGRATIONS:
            conn.execute(migration)
        ensure_arancel_schema(conn)
    return db_path


def next_id(conn: duckdb.DuckDBPyConnection, table: str, column: str) -> int:
    table = _sql_identifier(table)
    column = _sql_identifier(column)
    value = conn.execute(f"SELECT COALESCE(MAX({column}), 0) + 1 FROM {table}").fetchone()[0]
    return int(value)


def record_error(
    context: str,
    exc: BaseException,
    file_path: str | None = None,
    db_path: Path = DB_PATH,
) -> bool:
    try:
        init_db(db_path)
        with connect(db_path) as conn:
            error_id = next_id(conn, "etl_error_log", "error_id")
            conn.execute(
                """
                INSERT INTO etl_error_log
                    (error_id, context, file_path, error_message, traceback)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    error_id,
                    context[:200],
                    file_path,
                    str(exc)[:1000],
                    "".join(traceback.format_exception(exc))[:4000],
                ],
            )
        return True
    except Exception:
        return False


def create_load_run(source_code: str, mode: str) -> int:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            UPDATE load_run
            SET status = 'ERROR', finished_at = ?, message = 'Interrupted by a newer run'
            WHERE source_code = ? AND mode = ? AND status = 'RUNNING'
            """,
            [utc_now_naive(), source_code, mode],
        )
        load_run_id = next_id(conn, "load_run", "load_run_id")
        conn.execute(
            """
            INSERT INTO load_run (load_run_id, source_code, mode, status, started_at)
            VALUES (?, ?, ?, 'RUNNING', ?)
            """,
            [load_run_id, source_code, mode, utc_now_naive()],
        )
        return load_run_id


def finish_load_run(
    load_run_id: int,
    status: str,
    records_read: int = 0,
    records_loaded: int = 0,
    message: str | None = None,
    artifact_path: str | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE load_run
            SET status = ?, finished_at = ?, records_read = ?, records_loaded = ?,
                message = ?, artifact_path = ?
            WHERE load_run_id = ?
            """,
            [status, utc_now_naive(), records_read, records_loaded, message, artifact_path, load_run_id],
        )


def db_status() -> dict:
    if not DB_PATH.exists():
        return {"initialized": False, "path": str(DB_PATH), "tables": {}, "last_runs": []}
    init_db(DB_PATH)
    tables = {}
    with connect(read_only=True) as conn:
        for table in (
            "vucem_tigie_items",
            "dim_nico_catalog",
            "catalog_source",
            "catalog_item",
            "catalog_refresh_run",
            "warehouse_snapshot",
            "dim_banxico_series",
            "fact_banxico_series_monthly",
            "fact_dashboard_annual",
            "fact_dashboard_accumulated",
            "fact_country_balance",
            "dim_customs",
            "fact_customs_revenue",
            "fact_trade_component",
            "vucem_notifications",
            "anam_public_pages",
            "anam_trade_agreements",
            "dof_publication",
            "dashboard_country_balance",
            "dashboard_customs_revenue",
            "catalog_tariff_fraction",
            "catalog_tariff_nico",
            "catalog_tariff_rate",
            "tariff_regulation",
            "tariff_fraction_regulation",
            "pedimento",
            "pedimento_item",
            "load_run",
            "etl_error_log",
        ):
            tables[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        tables["tariff_fraction"] = tables["catalog_tariff_fraction"]
        tables["tariff_nico"] = tables["catalog_tariff_nico"]
        tables["tariff_rate"] = tables["catalog_tariff_rate"]
        last_runs = conn.execute(
            """
            SELECT source_code, mode, status, started_at, finished_at, records_loaded, message
            FROM load_run
            ORDER BY started_at DESC
            LIMIT 10
            """
        ).fetchall()
        recent_errors = conn.execute(
            """
            SELECT created_at, context, file_path, error_message
            FROM etl_error_log
            ORDER BY created_at DESC
            LIMIT 10
            """
        ).fetchall()
    return {
        "initialized": True,
        "path": str(DB_PATH),
        "tables": tables,
        "last_runs": [
            {
                "source": r[0],
                "mode": r[1],
                "status": r[2],
                "started_at": str(r[3]) if r[3] else "",
                "finished_at": str(r[4]) if r[4] else "",
                "records_loaded": r[5],
                "message": r[6] or "",
            }
            for r in last_runs
        ],
        "recent_errors": [
            {
                "created_at": str(r[0]) if r[0] else "",
                "context": r[1] or "",
                "file_path": r[2] or "",
                "message": r[3] or "",
            }
            for r in recent_errors
        ],
    }
