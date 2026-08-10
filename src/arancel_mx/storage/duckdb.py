"""DuckDB storage for the public tariff dataset."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import duckdb


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
    source_documents_json VARCHAR,
    release_metadata_json VARCHAR NOT NULL
);
"""


def ensure_tariff_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Install only the tables used by the tariff pipeline."""
    conn.execute(ARANCEL_SCHEMA)


@contextmanager
def connect(
    db_path: Path,
    read_only: bool = False,
) -> Iterator[duckdb.DuckDBPyConnection]:
    """Open a DuckDB connection and close it deterministically."""
    if not read_only:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path), read_only=read_only)
    try:
        yield conn
    finally:
        conn.close()


def init_tariff_db(db_path: Path) -> Path:
    """Create a database containing the tariff schema and return its path."""
    with connect(db_path) as conn:
        ensure_tariff_schema(conn)
    return db_path
