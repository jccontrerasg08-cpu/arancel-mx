from arancel_mx.cli import build_parser


def test_data_diagnostics_accept_dataset_and_json_format() -> None:
    parser = build_parser()
    nico = parser.parse_args(
        ["data", "nico-coverage", "--dataset", "data-2026.11.09", "--offline", "--format", "json"]
    )
    assert nico.data_command == "nico-coverage"
    assert nico.consumer_action == "data_nico_coverage"
    assert nico.dataset == "data-2026.11.09"
    assert nico.offline is True
    assert nico.format == "json"

    rates = parser.parse_args(["data", "rate-validity", "--format", "csv"])
    assert rates.consumer_action == "data_rate_validity"
    assert rates.format == "csv"
