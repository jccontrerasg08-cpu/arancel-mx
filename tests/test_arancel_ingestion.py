import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from src.comex.arancel_capture import capture_document, can_reuse_parse
from src.comex.arancel_workbooks import (
    WorkbookProfile,
    parse_indicator_workbook,
    parse_ligie_workbook,
    parse_nico_workbook,
    probe_workbook,
)


META = {
    "source_id": "snice-nico",
    "kind": "nico_current",
    "observed_at": "2026-08-09",
    "source_url": "https://www.snice.gob.mx/nico.xlsx",
    "filename": "nico.xlsx",
}


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_same_day_changed_bytes_keep_both_captures(self):
        first = capture_document(b"one", META, self.root)
        second = capture_document(b"two", META, self.root)
        self.assertNotEqual(first.path, second.path)
        self.assertTrue(first.path.exists() and second.path.exists())
        self.assertEqual(json.loads(first.manifest_path.read_text("utf-8"))["sha256"], first.sha256)

    def test_identical_capture_is_idempotent(self):
        first = capture_document(b"one", META, self.root)
        second = capture_document(b"one", META, self.root)
        self.assertEqual(first, second)

    def test_reuse_requires_all_four_identity_fields(self):
        previous = {
            "source_sha256": "abc",
            "parser_version": "1",
            "schema_version": "1",
            "registry_version": "1",
        }
        self.assertTrue(can_reuse_parse(previous, "abc", "1", "1", "1"))
        for values in [
            ("def", "1", "1", "1"),
            ("abc", "2", "1", "1"),
            ("abc", "1", "2", "1"),
            ("abc", "1", "1", "2"),
        ]:
            self.assertFalse(can_reuse_parse(previous, *values))


class WorkbookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = {"source_document_id": "src-1"}

    def tearDown(self):
        self.temp.cleanup()

    def _workbook(self, name, rows):
        path = self.root / name
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Datos"
        for row in rows:
            sheet.append(row)
        workbook.save(path)
        return path

    def test_probe_is_bounded_and_reports_sheet_samples(self):
        path = self._workbook("probe.xlsx", [["nota"], ["Fracción", "Descripción"], ["01012101", "Caballos"]])
        probe = probe_workbook(path, sample_rows=2)
        self.assertEqual(probe.sheet_names, ("Datos",))
        self.assertEqual(len(probe.samples["Datos"]), 2)

    def test_preserves_zeroes_and_supports_split_nico_columns(self):
        path = self._workbook(
            "nico.xlsx",
            [["Fracción", "NICO", "Descripción"], ["01012101", 0, "Reproductores"]],
        )
        profile = WorkbookProfile(
            sheet="Datos", header_row=1,
            columns={"fraccion8": "Fracción", "nico2": "NICO", "description": "Descripción"},
        )
        rows = parse_nico_workbook(path, self.source, profile)
        self.assertEqual(rows[0].normalized["nico10"], "0101210100")
        self.assertEqual(rows[0].raw["nico2"], "0")
        self.assertEqual((rows[0].sheet, rows[0].row_number), ("Datos", 2))

    def test_complete_short_code_is_not_padded(self):
        path = self._workbook(
            "ligie.xlsx",
            [["Fracción", "Descripción", "IGI", "IGE"], ["1012101", "Inválida", "10%", "Ex."]],
        )
        profile = WorkbookProfile(
            sheet="Datos", header_row=1,
            columns={"code": "Fracción", "description": "Descripción", "igi": "IGI", "ige": "IGE"},
        )
        with self.assertRaisesRegex(ValueError, "width"):
            parse_ligie_workbook(path, self.source, profile)

    def test_indicator_rows_stay_analytical(self):
        path = self._workbook(
            "indicator.xlsx", [["Año", "Indicador", "Valor"], [2025, "Arancel ponderado", 6.4]],
        )
        profile = WorkbookProfile(
            sheet="Datos", header_row=1,
            columns={"period": "Año", "indicator": "Indicador", "value": "Valor"},
        )
        row = parse_indicator_workbook(path, self.source, profile)[0]
        self.assertEqual(row.domain, "analytics")
        self.assertEqual(row.normalized["value"], "6.4")


if __name__ == "__main__":
    unittest.main()
