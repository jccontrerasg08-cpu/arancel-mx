from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import duckdb
import pytest

from arancel_mx.consumer.errors import InvalidCodeError, QueryError, RecordNotFoundError
from arancel_mx.consumer.models import NationalNote, ProvenanceRecord, SearchResult, SuggestHit, TariffRecord
from arancel_mx.consumer.query import (
    SCORER_VERSION,
    chapters,
    children,
    ficha,
    format_code,
    lookup,
    normalize_code,
    parent,
    provenance,
    search,
    suggest,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("01", "01"),
        ("0101", "0101"),
        ("010121", "010121"),
        ("01012101", "01012101"),
        ("0101210100", "0101210100"),
    ],
)
def test_normalize_accepts_2_4_6_8_10_digits(raw: str, expected: str) -> None:
    assert normalize_code(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("01 01 21 01", "01012101"),
        ("01.01.21.01", "01012101"),
        ("01-01-21-01", "01012101"),
        (" 01.01-21 01 ", "01012101"),
    ],
)
def test_normalize_removes_unambiguous_spaces_dots_and_hyphens(raw: str, expected: str) -> None:
    assert normalize_code(raw) == expected


def test_normalize_rejects_letters() -> None:
    with pytest.raises(InvalidCodeError):
        normalize_code("01A12101")


@pytest.mark.parametrize("raw", ["0", "010", "01012", "0101210", "010121010"])
def test_normalize_rejects_lengths_other_than_2_4_6_8_10(raw: str) -> None:
    with pytest.raises(InvalidCodeError):
        normalize_code(raw)


def test_normalize_rejects_empty_value() -> None:
    with pytest.raises(InvalidCodeError):
        normalize_code("   ")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("01", "01"),
        ("0101", "01.01"),
        ("010121", "0101.21"),
        ("01012101", "0101.21.01"),
        ("01.01.21.01", "0101.21.01"),
        ("0101210100", "0101.21.01 00"),
    ],
)
def test_format_code_matches_tigie_browser_display(raw: str, expected: str) -> None:
    assert format_code(raw) == expected


def _connect(path: Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(path), read_only=True)


def test_lookup_returns_exact_current_record(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        record = lookup(conn, "01.01.21.01")
    finally:
        conn.close()

    assert isinstance(record, TariffRecord)
    assert record.code == "01012101"
    assert record.level == "fraccion8"
    assert record.unit_name == "Cbza"
    assert record.igi_kind == "ad_valorem"
    assert record.igi_value == 10.0
    assert record.ige_kind == "exento"
    assert record.ige_value == 0.0
    assert record.parent_code == "010121"
    assert record.dataset_version == "2026.08.11"
    assert record.schema_version == "2"
    assert record.is_current is True


def test_lookup_absent_valid_code_raises_record_not_found(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        with pytest.raises(RecordNotFoundError, match="99999999"):
            lookup(conn, "99999999")
    finally:
        conn.close()


def test_lookup_invalid_code_raises_invalid_code(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        with pytest.raises(InvalidCodeError):
            lookup(conn, "not-a-code")
    finally:
        conn.close()


def test_search_exact_code_ranks_first(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        results = search(conn, "0101", limit=20)
    finally:
        conn.close()

    assert results[0].record.code == "0101"
    assert results[0].score == 1000
    assert results[0].match_kind == "exact_code"


def test_search_code_prefix_ranks_before_description_only(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        results = search(conn, "010121", limit=20)
    finally:
        conn.close()

    assert [result.record.code for result in results[:4]] == [
        "010121",
        "01012101",
        "0101210100",
    ]
    assert results[0].score == 1000
    assert all(result.score == 700 for result in results[1:3])


def test_search_is_case_insensitive(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        results = search(conn, "ANIMALES VIVOS", limit=10)
    finally:
        conn.close()
    assert results[0].record.code == "01"
    assert results[0].match_kind == "description"


def test_search_is_accent_insensitive(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        results = search(conn, "burdeganos", limit=10)
    finally:
        conn.close()
    assert results[0].record.code == "0101"


def test_search_token_ranking_is_deterministic(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        first = search(conn, "raza pura", limit=20)
        second = search(conn, "raza pura", limit=20)
    finally:
        conn.close()

    assert first == second
    assert [result.record.code for result in first] == [
        "010121",
        "01012101",
        "0101210100",
    ]
    assert {result.score for result in first} == {355}


def test_search_limit_must_be_positive(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        with pytest.raises(ValueError, match="limit"):
            search(conn, "raza", limit=0)
    finally:
        conn.close()


def test_search_empty_text_raises_query_error(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        with pytest.raises(QueryError, match="search text"):
            search(conn, "   ", limit=10)
    finally:
        conn.close()


def test_search_limit_is_applied_after_deterministic_sort(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        results = search(conn, "reproductores", limit=2)
    finally:
        conn.close()
    assert len(results) == 2
    assert [item.record.code for item in results] == ["010121", "01012101"]


def test_parent_hs2_returns_none(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        assert parent(conn, "01") is None
    finally:
        conn.close()


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("0101", "01"),
        ("010121", "0101"),
        ("01012101", "010121"),
        ("0101210100", "01012101"),
    ],
)
def test_parent_returns_direct_parent(consumer_duckdb: Path, code: str, expected: str) -> None:
    conn = _connect(consumer_duckdb)
    try:
        result = parent(conn, code)
    finally:
        conn.close()
    assert result is not None
    assert result.code == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("01", ("0101",)),
        ("0101", ("010121",)),
        ("010121", ("01012101",)),
        ("01012101", ("0101210100",)),
        ("0101210100", ()),
    ],
)
def test_children_returns_only_direct_children_sorted_by_code(
    consumer_duckdb: Path,
    code: str,
    expected: tuple[str, ...],
) -> None:
    conn = _connect(consumer_duckdb)
    try:
        result = children(conn, code)
    finally:
        conn.close()
    assert tuple(record.code for record in result) == expected


def test_provenance_returns_primary_first_then_deterministic_source_order(
    consumer_duckdb: Path,
) -> None:
    conn = duckdb.connect(str(consumer_duckdb))
    try:
        conn.execute(
            """
            INSERT INTO source_document (
                source_document_id, authority, publication_venue, title, source_url,
                media_type, sha256, local_path, published_at, effective_from,
                effective_to, observed_at, retrieved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                "a-secondary",
                "DOF",
                "Diario Oficial de la Federación",
                "Modificación fixture",
                "https://example.invalid/secondary",
                "application/pdf",
                "a" * 64,
                None,
                date(2026, 5, 1),
                date(2026, 5, 2),
                None,
                date(2026, 8, 11),
                datetime(2026, 8, 11, 12, 1, 0),
            ],
        )
        conn.execute(
            """
            INSERT INTO record_provenance
                (record_id, source_document_id, role, is_primary)
            VALUES ('r-frac', 'a-secondary', 'modification', FALSE)
            """
        )
    finally:
        conn.close()

    conn = _connect(consumer_duckdb)
    try:
        records = provenance(conn, "01012101")
    finally:
        conn.close()

    assert all(isinstance(record, ProvenanceRecord) for record in records)
    assert [record.source_document_id for record in records] == [
        "fixture-source",
        "a-secondary",
    ]
    assert records[0].is_primary is True
    assert records[1].is_primary is False


def test_ficha_returns_official_hierarchy_card(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        card = ficha(conn, "01.01.21.01")
    finally:
        conn.close()

    assert card.formatted_code == "0101.21.01"
    assert card.record.code == "01012101"
    assert card.section is not None
    assert card.section.roman == "I"
    assert card.section.source == "hs_section_grouping"
    assert tuple(node.code for node in card.hierarchy) == (
        "01",
        "0101",
        "010121",
        "01012101",
    )
    assert tuple(node.code for node in card.children) == ("0101210100",)


def test_ficha_for_chapter_has_no_parent_and_lists_headings(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        card = ficha(conn, "01")
    finally:
        conn.close()

    assert card.record.level == "hs2"
    assert card.hierarchy[0].code == "01"
    assert tuple(node.code for node in card.children) == ("0101",)


def test_chapters_returns_current_hs2_records(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        result = chapters(conn)
    finally:
        conn.close()

    assert tuple(record.code for record in result) == ("01",)
    assert result[0].description == "Animales vivos"


def _insert_current_record(
    conn: duckdb.DuckDBPyConnection,
    record_id: str,
    code: str,
    level: str,
    hs2: str | None,
    hs4: str | None,
    hs6: str | None,
    fraccion8: str | None,
    nico2: str | None,
    nico10: str | None,
    description: str,
) -> None:
    unit_code = "01" if level in {"fraccion8", "nico10"} else None
    unit_name = "Cbza" if level in {"fraccion8", "nico10"} else None
    values_from_level = "fraccion8" if level in {"fraccion8", "nico10"} else None
    igi_text = "10" if level in {"fraccion8", "nico10"} else None
    igi_kind = "ad_valorem" if level in {"fraccion8", "nico10"} else None
    igi_value = 10.0 if level in {"fraccion8", "nico10"} else None
    ige_text = "Ex." if level in {"fraccion8", "nico10"} else None
    ige_kind = "exento" if level in {"fraccion8", "nico10"} else None
    ige_value = 0.0 if level in {"fraccion8", "nico10"} else None
    conn.execute(
        """
        INSERT INTO canonical_record (
            record_id, record_version, is_current, code, formatted_code, level,
            hs2, hs4, hs6, fraccion8, nico2, nico10, name, description,
            name_is_derived, unit_code, unit_name, values_from_level,
            igi_text, igi_kind, igi_value, ige_text, ige_kind, ige_value,
            ligie_version, dataset_version, schema_version, record_hash,
            validity_basis, updated_at, published_at,
            classification_effective_from, classification_effective_to,
            rate_effective_from, rate_effective_to, effective_from, effective_to,
            observed_at, retrieved_at, primary_source_document_id
        ) VALUES (
            ?, 1, TRUE, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE,
            ?, ?, ?, ?, ?, ?, ?, ?, ?,
            'LIGIE-2022', '2026.08.11', '2', ?, 'legal', ?, ?, ?, NULL,
            ?, NULL, ?, NULL, ?, ?, 'fixture-source'
        )
        """,
        [
            record_id,
            code,
            code,
            level,
            hs2,
            hs4,
            hs6,
            fraccion8,
            nico2,
            nico10,
            description,
            description,
            unit_code,
            unit_name,
            values_from_level,
            igi_text,
            igi_kind,
            igi_value,
            ige_text,
            ige_kind,
            ige_value,
            record_id.encode("utf-8").hex().zfill(64)[:64],
            date(2026, 4, 20),
            date(2026, 4, 20),
            date(2026, 4, 20),
            date(2026, 4, 20) if level in {"fraccion8", "nico10"} else None,
            date(2026, 4, 20),
            date(2026, 8, 11),
            datetime(2026, 8, 11, 12, 0, 0),
        ],
    )
    conn.execute(
        """
        INSERT INTO record_provenance
            (record_id, source_document_id, role, is_primary)
        VALUES (?, 'fixture-source', ?, TRUE)
        """,
        [record_id, "nico" if level == "nico10" else "base"],
    )


def test_search_description_ranks_strong_chapter_before_weak_token_overlap(
    consumer_duckdb: Path,
) -> None:
    conn = duckdb.connect(str(consumer_duckdb))
    try:
        _insert_current_record(
            conn,
            "r-61-hs2",
            "61",
            "hs2",
            "61",
            None,
            None,
            None,
            None,
            None,
            "Prendas de vestir",
        )
        _insert_current_record(
            conn,
            "r-61-frac",
            "61091001",
            "fraccion8",
            "61",
            "6109",
            "610910",
            "61091001",
            None,
            None,
            "Camisas de punto",
        )
    finally:
        conn.close()

    conn = _connect(consumer_duckdb)
    try:
        results = search(conn, "camisas de punto", limit=20)
    finally:
        conn.close()

    hit_chapters = [item.record.hs2 or item.record.code[:2] for item in results]
    assert "61" in hit_chapters
    assert "01" in hit_chapters
    last_61 = max(index for index, chapter in enumerate(hit_chapters) if chapter == "61")
    first_01 = min(index for index, chapter in enumerate(hit_chapters) if chapter == "01")
    assert last_61 < first_01


def test_search_result_scorer_version_is_one(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        results = search(conn, "reproductores", limit=20)
    finally:
        conn.close()

    assert results
    assert SCORER_VERSION == "1"
    assert all(item.scorer_version == "1" for item in results)
    assert all(item.scorer_version == SCORER_VERSION for item in results)


def test_search_result_confidence_by_match_kind(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        code_hits = search(conn, "010121", limit=20)
        description_hits = search(conn, "raza pura", limit=20)
        partial_hits = search(conn, "animales vivos extra", limit=20)
    finally:
        conn.close()

    assert code_hits[0].match_kind == "exact_code"
    assert code_hits[0].confidence == 1.0
    prefix_hits = [item for item in code_hits if item.match_kind == "code_prefix"]
    assert prefix_hits
    assert all(item.confidence == 0.85 for item in prefix_hits)
    assert all(0.0 <= item.confidence <= 1.0 for item in (*code_hits, *description_hits, *partial_hits))
    assert description_hits
    assert all(item.match_kind == "description" for item in description_hits)
    assert all(item.confidence == 1.0 for item in description_hits)
    chapter = next(item for item in partial_hits if item.record.code == "01")
    assert chapter.match_kind == "description"
    assert chapter.confidence == pytest.approx(2 / 3)


def test_suggest_prefers_fraccion8_and_attaches_ficha(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        hits = suggest(conn, "reproductores")
    finally:
        conn.close()

    assert hits
    assert len(hits) <= 5
    assert all(isinstance(hit, SuggestHit) for hit in hits)
    assert [hit.search.record.level for hit in hits] == ["fraccion8"]
    assert hits[0].search.record.code == "01012101"
    assert hits[0].ficha.record.code == "01012101"
    assert hits[0].ficha.formatted_code == "0101.21.01"
    assert hits[0].national_notes == ()
    lowered = hits[0].disclaimer.lower()
    assert "not a classification" in lowered
    assert "wco" in lowered
    assert "ligie" in lowered
    assert "nico" in lowered


def test_suggest_falls_back_when_no_fraccion8_matches(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        hits = suggest(conn, "ANIMALES VIVOS")
    finally:
        conn.close()

    assert hits
    assert hits[0].search.record.level == "hs2"
    assert hits[0].search.record.code == "01"


def test_suggest_returns_ranked_fraccion8_candidates_not_a_single_winner(
    consumer_duckdb: Path,
) -> None:
    conn = duckdb.connect(str(consumer_duckdb))
    try:
        _insert_current_record(
            conn,
            "r-frac-2",
            "01012102",
            "fraccion8",
            "01",
            "0101",
            "010121",
            "01012102",
            None,
            None,
            "Reproductores de raza pura extra",
        )
    finally:
        conn.close()

    conn = _connect(consumer_duckdb)
    try:
        hits = suggest(conn, "reproductores")
    finally:
        conn.close()

    assert [hit.search.record.code for hit in hits] == ["01012101", "01012102"]
    assert all(hit.search.record.level == "fraccion8" for hit in hits)
    assert len(hits) == 2


def test_suggest_limit_default_is_five() -> None:
    import inspect

    assert inspect.signature(suggest).parameters["limit"].default == 5


def test_suggest_national_notes_empty_when_view_missing(consumer_duckdb: Path) -> None:
    conn = _connect(consumer_duckdb)
    try:
        hits = suggest(conn, "reproductores")
    finally:
        conn.close()

    assert hits[0].national_notes == ()


def test_suggest_national_notes_attach_when_present(consumer_duckdb: Path) -> None:
    conn = duckdb.connect(str(consumer_duckdb))
    try:
        conn.execute(
            "INSERT INTO national_note VALUES ('note-01-1', '01', '1')"
        )
        conn.execute(
            """
            INSERT INTO national_note_version VALUES (
                'note-01-1-v', 'note-01-1',
                'Los animales vivos de este capítulo.',
                NULL, NULL, 'fixture-source'
            )
            """
        )
        conn.execute(
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
        conn.close()

    conn = _connect(consumer_duckdb)
    try:
        hits = suggest(conn, "reproductores")
    finally:
        conn.close()

    assert hits[0].search.record.code == "01012101"
    assert hits[0].national_notes == (
        NationalNote(
            chapter="01",
            note_number="1",
            text="Los animales vivos de este capítulo.",
            source_document_id="fixture-source",
        ),
    )
