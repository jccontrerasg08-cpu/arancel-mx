from pathlib import Path

import pytest
import requests

from arancel_mx.parsers.documents import parse_ligie_pdf_hierarchy
from arancel_mx.parsers.workbooks import probe_workbook
from scripts.run_official_pipeline import classify_failure


def _captured_error(callable_):
    try:
        callable_()
    except Exception as error:  # noqa: BLE001 - the test probes third-party parser errors
        return error
    raise AssertionError("fault injection did not raise")


def test_network_timeout_has_stable_source_network_category():
    error = requests.Timeout("official source timed out")

    assert classify_failure(error) == "source_network"


def test_truncated_xlsx_has_stable_parser_category(tmp_path: Path):
    path = tmp_path / "truncated.xlsx"
    path.write_bytes(b"PK\x03\x04not-a-complete-zip")

    error = _captured_error(lambda: probe_workbook(path))

    assert classify_failure(error) == "parser", (
        type(error).__module__,
        type(error).__name__,
        str(error),
    )


def test_corrupted_xls_has_stable_parser_category(tmp_path: Path):
    path = tmp_path / "corrupted.xls"
    path.write_bytes(b"not-an-ole2-excel-workbook")

    error = _captured_error(lambda: probe_workbook(path))

    assert classify_failure(error) == "parser", (
        type(error).__module__,
        type(error).__name__,
        str(error),
    )


def test_corrupted_pdf_has_stable_parser_category(tmp_path: Path):
    path = tmp_path / "corrupted.pdf"
    path.write_bytes(b"%PDF-1.7\nthis is not a valid PDF body")

    error = _captured_error(
        lambda: parse_ligie_pdf_hierarchy(
            path,
            "source-corrupt-pdf",
            "LIGIE-2022",
            None,
            None,
        )
    )

    assert classify_failure(error) == "parser", (
        type(error).__module__,
        type(error).__name__,
        str(error),
    )
