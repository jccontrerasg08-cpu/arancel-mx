from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from arancel_mx.consumer import Dataset
from arancel_mx.consumer.errors import QueryError
from arancel_mx.consumer.models import NationalNote
from arancel_mx.consumer.query import national_notes


def _materialize_note(path: Path) -> None:
    connection = duckdb.connect(str(path))
    try:
        connection.execute("INSERT INTO national_note VALUES ('note-01-1', '01', '1')")
        connection.execute(
            """
            INSERT INTO national_note_version VALUES (
                'note-01-1-v', 'note-01-1',
                'Los animales vivos de este capítulo.',
                NULL, NULL, 'fixture-source'
            )
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE VIEW arancel_mx_national_notes AS
            SELECT n.national_note_id, n.chapter, n.note_number,
                   v.national_note_version_id, v.text, v.effective_from,
                   v.effective_to, v.source_document_id
            FROM national_note n
            JOIN national_note_version v USING (national_note_id)
            """
        )
    finally:
        connection.close()


def test_national_notes_returns_materialized_chapter_notes(
    consumer_duckdb: Path,
) -> None:
    _materialize_note(consumer_duckdb)
    connection = duckdb.connect(str(consumer_duckdb), read_only=True)
    try:
        notes = national_notes(connection, "01")
    finally:
        connection.close()

    assert notes == (
        NationalNote(
            chapter="01",
            note_number="1",
            text="Los animales vivos de este capítulo.",
            source_document_id="fixture-source",
        ),
    )


@pytest.mark.parametrize("chapter", ["1", "010", "0101", "ab", " 01 "])
def test_national_notes_rejects_invalid_chapter_shape(
    consumer_duckdb: Path,
    chapter: str,
) -> None:
    connection = duckdb.connect(str(consumer_duckdb), read_only=True)
    try:
        with pytest.raises(QueryError, match="two digits"):
            national_notes(connection, chapter)
    finally:
        connection.close()


def test_national_notes_returns_empty_when_release_has_no_notes_view(
    consumer_duckdb: Path,
) -> None:
    connection = duckdb.connect(str(consumer_duckdb), read_only=True)
    try:
        assert national_notes(connection, "01") == ()
    finally:
        connection.close()


def test_dataset_exposes_national_notes(consumer_duckdb: Path) -> None:
    _materialize_note(consumer_duckdb)
    dataset = Dataset.open(consumer_duckdb)

    notes = dataset.national_notes("01")

    assert len(notes) == 1
    assert notes[0].chapter == "01"
    assert notes[0].source_document_id == "fixture-source"
