from arancel_mx.cli import build_parser, main


def test_parser_exposes_tariff_command_families():
    help_text = build_parser().format_help()

    for command in ("build", "update", "reconcile", "release"):
        assert command in help_text


def test_main_prints_help_without_arguments(capsys):
    assert main([]) == 0
    assert "arancel-mx" in capsys.readouterr().out
