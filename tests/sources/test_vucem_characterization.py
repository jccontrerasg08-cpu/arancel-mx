from importlib.util import find_spec


def test_vucem_characterization_script_exists():
    assert find_spec("scripts.characterize_vucem") is not None


def test_build_vucem_url_accepts_only_eight_digit_tariff_fraction():
    from scripts import characterize_vucem as module

    fn = getattr(module, "build_vucem_url", None)
    assert callable(fn)
    assert fn("32041402") == (
        "https://www.ventanillaunica.gob.mx/Clasificador/data/buildHojas1/32041402.html"
    )

    for invalid in ("320414", "3204140200", "../../etc/passwd", "32.04.14.02", "abcdefgh"):
        try:
            fn(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(invalid)


def test_select_sample_rows_spreads_codes_across_chapters_and_filters_levels():
    from scripts import characterize_vucem as module

    fn = getattr(module, "select_sample_rows", None)
    assert callable(fn)
    rows = [
        {"level": "fraccion8", "code": "01012101", "description": "A"},
        {"level": "fraccion8", "code": "01012102", "description": "B"},
        {"level": "fraccion8", "code": "02011001", "description": "C"},
        {"level": "fraccion8", "code": "32041402", "description": "D"},
        {"level": "hs6", "code": "320414", "description": "ignore"},
        {"level": "fraccion8", "code": "32041402", "description": "duplicate"},
    ]

    sample = fn(rows, 4)

    assert [row["code"] for row in sample] == [
        "01012101",
        "02011001",
        "32041402",
        "01012102",
    ]


def test_analyze_vucem_html_records_structure_and_cross_check_signals():
    from scripts import characterize_vucem as module

    fn = getattr(module, "analyze_vucem_html", None)
    assert callable(fn)
    html = """
    <html><head><title>Fracción 32041402</title></head>
    <body>
      <h1>32041402</h1>
      <div id="ficha" class="tarifa vigente">Preparaciones colorantes orgánicas</div>
      <table><tr><th>Campo</th><th>Valor</th></tr><tr><td>Fracción</td><td>32041402</td></tr></table>
    </body></html>
    """

    result = fn("32041402", html, "Preparaciones colorantes organicas")

    assert result["page_title"] == "Fracción 32041402"
    assert result["code_present"] is True
    assert result["snice_description_present"] is True
    assert result["structure"]["table_count"] == 1
    assert result["structure"]["row_count"] == 2
    assert result["structure"]["cell_count"] == 4
    assert result["structure"]["ids"] == ["ficha"]
    assert result["structure"]["classes"] == ["tarifa", "vigente"]
    assert len(result["schema_fingerprint"]) == 64


def test_run_characterization_is_non_authoritative_and_records_partial_failures():
    from scripts import characterize_vucem as module

    fn = getattr(module, "run_characterization", None)
    snapshot_type = getattr(module, "PageSnapshot", None)
    assert callable(fn)
    assert snapshot_type is not None

    rows = [
        {"level": "fraccion8", "code": "01012101", "description": "Caballos"},
        {"level": "fraccion8", "code": "02011001", "description": "Carne"},
    ]

    def fetcher(url):
        if "02011001" in url:
            raise TimeoutError("synthetic timeout")
        return snapshot_type(
            final_url=url,
            media_type="text/html",
            retrieved_at="2026-08-11T18:00:00Z",
            sha256="a" * 64,
            byte_size=77,
            html="<html><body><h1>01012101</h1><p>Caballos</p></body></html>",
        )

    report = fn(rows, sample_size=2, fetcher=fetcher)

    assert report["source_role"] == "independent_operational_cross_check"
    assert report["authoritative_for_tariff"] is False
    assert report["publication_gate"] is False
    assert report["summary"]["fetched"] == 1
    assert report["summary"]["errors"] == 1
    assert report["summary"]["chapters_sampled"] == ["01", "02"]
    assert report["results"][0]["code_present"] is True
    assert report["results"][1]["error_type"] == "TimeoutError"


def test_load_public_csv_requires_release_columns_and_preserves_leading_zero(tmp_path):
    from scripts import characterize_vucem as module

    fn = getattr(module, "load_public_csv", None)
    assert callable(fn)
    path = tmp_path / "arancel_mx.csv"
    path.write_text(
        "code,level,description\n01012101,fraccion8,Caballos\n320414,hs6,Colorantes\n",
        encoding="utf-8",
    )

    rows = fn(path)

    assert rows[0]["code"] == "01012101"
    assert rows[0]["description"] == "Caballos"


def test_main_dry_run_writes_deterministic_sample_without_network(tmp_path):
    import json
    from scripts import characterize_vucem as module

    fn = getattr(module, "main", None)
    assert callable(fn)
    source = tmp_path / "arancel_mx.csv"
    output = tmp_path / "report.json"
    source.write_text(
        "code,level,description\n01012101,fraccion8,Caballos\n02011001,fraccion8,Carne\n",
        encoding="utf-8",
    )

    assert fn([
        "--snice-csv", str(source),
        "--output", str(output),
        "--sample-size", "2",
        "--dry-run",
    ]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["publication_gate"] is False
    assert [item["code"] for item in payload["results"]] == ["01012101", "02011001"]
    assert all(item["status"] == "planned" for item in payload["results"])


def test_vucem_characterization_is_documented_as_pre_registry_research():
    from pathlib import Path

    doc = Path("docs/vucem-characterization.md")
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8").lower()
    required = (
        "100+",
        "source_registry",
        "authoritative_for_tariff",
        "publication_gate",
        "schema_fingerprint",
        "update lag",
        "--sample-size 120",
        "--dry-run",
    )
    assert [value for value in required if value not in text] == []
