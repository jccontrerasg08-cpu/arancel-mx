import json
import tempfile
import unittest
from pathlib import Path

from src.comex.db import connect, init_db


class RegistryTests(unittest.TestCase):
    def test_authoritative_page_is_required_to_classify_nico_snapshot(self):
        from src.comex.arancel_registry import classify_candidate, load_source_registry

        registry = load_source_registry()
        entry = registry["nico"]
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        self.assertEqual(
            classify_candidate(
                entry,
                entry.canonical_page,
                "NICO-ABRIL24-LIGIE_20240415-20240415.XLSX",
                media_type,
            ),
            "nico_snapshot",
        )
        self.assertIsNone(
            classify_candidate(
                entry,
                "https://www.snice.gob.mx/ligie.info22.html",
                "NICO-MAYO99-LIGIE_20990501-20990501.XLSX",
                media_type,
            )
        )

    def test_registry_keeps_legal_proposals_and_analytics_distinct(self):
        from src.comex.arancel_registry import load_source_registry

        registry = load_source_registry()

        self.assertTrue(registry["ligie"].authoritative_for_tariff)
        self.assertFalse(registry["nico_proposals"].authoritative_for_tariff)
        self.assertFalse(registry["weighted_tariff_indicators"].authoritative_for_tariff)
        self.assertEqual(registry["diputados_ligie"].legal_publication_authority, "DOF")

    def test_database_has_separate_discovery_legal_and_analytical_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.duckdb"
            init_db(path)
            with connect(path, read_only=True) as conn:
                tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}

        expected = {
            "source_registry",
            "source_discovery_run",
            "source_discovery_item",
            "source_capture",
            "staging_arancel_row",
            "arancel_quarantine",
            "nico_version",
            "nico_proposal_batch",
            "nico_proposal",
            "national_note",
            "national_note_version",
            "national_note_amendment",
            "national_note_applicability",
            "weighted_tariff_indicator",
            "indicator_methodology",
        }
        self.assertTrue(expected <= tables, json.dumps(sorted(expected - tables)))


if __name__ == "__main__":
    unittest.main()
