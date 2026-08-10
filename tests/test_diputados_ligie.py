import unittest
from dataclasses import replace
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "diputados" / "ligie_2022.html"
BASE_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"


class DiputadosLedgerTests(unittest.TestCase):
    def test_parser_keeps_law_and_tariff_dates_and_all_document_families_distinct(self):
        from src.comex.diputados_ligie import parse_ligie_ledger

        snapshot = parse_ligie_ledger(FIXTURE.read_text(encoding="utf-8"), BASE_URL)

        self.assertEqual(snapshot.last_law_reform.isoformat(), "2025-12-29")
        self.assertEqual(snapshot.latest_tariff_modification.isoformat(), "2026-04-23")
        self.assertEqual(
            {document.category for document in snapshot.documents},
            {
                "consolidated_text",
                "original",
                "law_reform",
                "tariff_decree",
                "nico_agreement",
                "national_notes",
                "correlation",
            },
        )

    def test_same_dates_with_changed_link_hash_routes_reconciliation(self):
        from src.comex.diputados_ligie import diff_ledgers, parse_ligie_ledger, route_changes

        previous = parse_ligie_ledger(FIXTURE.read_text(encoding="utf-8"), BASE_URL)
        current_document = previous.documents[0]
        changed_link = replace(current_document.links[0], content_sha256="f" * 64)
        changed_document = replace(current_document, links=(changed_link,))
        current = replace(
            previous,
            documents=(changed_document, *previous.documents[1:]),
        )

        changes = diff_ledgers(previous, current)
        self.assertEqual({change.event_type for change in changes}, {"consolidated_text_changed"})
        jobs = route_changes((*changes, *changes))
        self.assertEqual(len(jobs), len(set(jobs)))
        self.assertIn("canonical_rebuild", jobs)

    def test_unknown_legal_change_blocks_routing(self):
        from src.comex.diputados_ligie import LegalChange, route_changes

        with self.assertRaisesRegex(ValueError, "unknown_legal_change"):
            route_changes((LegalChange("unknown_legal_change", "new section"),))


if __name__ == "__main__":
    unittest.main()
