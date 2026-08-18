from __future__ import annotations

from datetime import datetime, timezone
from importlib.util import find_spec


class RecordingTransaction:
    def __init__(self, connection: "RecordingConnection") -> None:
        self.connection = connection

    def __enter__(self) -> "RecordingTransaction":
        self.connection.events.append("begin")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.connection.events.append("rollback" if exc_type is not None else "commit")
        return False


class RecordingConnection:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.statements: list[tuple[str, tuple[object, ...] | None]] = []

    def transaction(self) -> RecordingTransaction:
        return RecordingTransaction(self)

    def execute(self, statement: str, values: tuple[object, ...] | None = None) -> None:
        self.statements.append((statement, values))


def test_verified_release_promotion_loads_versioned_rows_before_switching_active_pointer():
    assert find_spec("arancel_mx.operational") is not None, (
        "the central operational promotion module must exist"
    )

    from arancel_mx.operational import OperationalRecord, OperationalRelease, promote_release

    connection = RecordingConnection()
    release = OperationalRelease(
        tag="data-2026.08.18",
        dataset_version="2026.08.18",
        schema_version="2",
        manifest_sha256="a" * 64,
        generated_at=datetime(2026, 8, 18, 11, 17, tzinfo=timezone.utc),
        published_at=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
        source_checked_at=datetime(2026, 8, 18, 11, 17, tzinfo=timezone.utc),
    )
    record = OperationalRecord(
        code="85171301",
        level="fraccion8",
        description="Teléfonos inteligentes.",
        record_hash="b" * 64,
        source_document_ids=("source-1",),
        payload={"code": "85171301", "description": "Teléfonos inteligentes."},
    )

    promote_release(connection, release, [record])

    assert connection.events == ["begin", "commit"]
    statements = [statement for statement, _values in connection.statements]
    release_position = next(
        index
        for index, statement in enumerate(statements)
        if "INSERT INTO operational_release" in statement
    )
    record_position = next(
        index
        for index, statement in enumerate(statements)
        if "INSERT INTO operational_record" in statement
    )
    active_pointer_position = next(
        index
        for index, statement in enumerate(statements)
        if "INSERT INTO operational_active_release" in statement
    )
    assert release_position < record_position < active_pointer_position
    assert connection.statements[-1][1] == ("data-2026.08.18",)


def test_rejected_release_never_opens_a_database_transaction():
    assert find_spec("arancel_mx.operational") is not None, (
        "the central operational promotion module must exist"
    )

    from arancel_mx.operational import OperationalRelease, PromotionError, promote_release

    connection = RecordingConnection()
    invalid_release = OperationalRelease(
        tag="data-2026.08.18",
        dataset_version="2026.08.18",
        schema_version="2",
        manifest_sha256="not-a-sha256",
        generated_at=datetime(2026, 8, 18, 11, 17, tzinfo=timezone.utc),
        published_at=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
        source_checked_at=datetime(2026, 8, 18, 11, 17, tzinfo=timezone.utc),
    )

    try:
        promote_release(connection, invalid_release, [])
    except PromotionError as error:
        assert "manifest_sha256" in str(error)
    else:
        raise AssertionError("invalid releases must fail before database mutation")

    assert connection.events == []
    assert connection.statements == []


def test_certified_release_loader_preserves_the_public_record_payload(tmp_path, monkeypatch):
    assert find_spec("arancel_mx.operational") is not None

    import duckdb

    from arancel_mx.operational import OperationalRecord, load_certified_release

    release_dir = tmp_path / "release"
    release_dir.mkdir()
    manifest_path = release_dir / "manifest.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    database = release_dir / "arancel_mx.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute(
            """
            CREATE TABLE arancel_mx (
                code VARCHAR,
                level VARCHAR,
                description VARCHAR,
                record_hash VARCHAR,
                source_document_ids_json VARCHAR,
                igi_text VARCHAR,
                ige_text VARCHAR
            )
            """
        )
        connection.execute(
            """
            INSERT INTO arancel_mx VALUES (
                '85171301',
                'fraccion8',
                'Teléfonos inteligentes.',
                ?,
                '["source-1","source-2"]',
                '10',
                'Ex.'
            )
            """,
            ["c" * 64],
        )

    monkeypatch.setattr(
        "arancel_mx.operational.verify_publication_bundle",
        lambda path: {
            "dataset_version": "2026.08.18",
            "schema_version": "2",
            "generated_at": "2026-08-18T11:17:00Z",
        },
    )

    release, records = load_certified_release(
        release_dir,
        published_at=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
        source_checked_at=datetime(2026, 8, 18, 11, 17, tzinfo=timezone.utc),
    )

    assert release.tag == "data-2026.08.18"
    assert records == [
        OperationalRecord(
            code="85171301",
            level="fraccion8",
            description="Teléfonos inteligentes.",
            record_hash="c" * 64,
            source_document_ids=("source-1", "source-2"),
            payload={
                "code": "85171301",
                "description": "Teléfonos inteligentes.",
                "igi_text": "10",
                "ige_text": "Ex.",
                "level": "fraccion8",
                "record_hash": "c" * 64,
                "source_document_ids_json": '["source-1","source-2"]',
            },
        )
    ]
