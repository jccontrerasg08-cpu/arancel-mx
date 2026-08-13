from __future__ import annotations

import pytest

import arancel_mx
from arancel_mx.cli import build_parser, main


def test_parser_exposes_consumer_and_maintainer_commands() -> None:
    help_text = build_parser().format_help()
    for command in (
        "doctor",
        "data",
        "lookup",
        "search",
        "parent",
        "children",
        "provenance",
        "ficha",
        "chapters",
        "build",
        "check-updates",
        "update",
        "reconcile",
        "release",
    ):
        assert command in help_text


def test_existing_maintainer_help_remains_available(capsys) -> None:
    assert main(["build", "--help"]) == 0
    assert "--database" in capsys.readouterr().out


def test_no_args_still_returns_help_and_zero(capsys) -> None:
    assert main([]) == 0
    assert "arancel-mx" in capsys.readouterr().out


def test_data_requires_nested_subcommand(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["data"])
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "required" in captured.err.lower()
    assert "status" in captured.err


def test_update_alias_warning_is_unchanged(tmp_path, monkeypatch, capsys) -> None:
    from arancel_mx import cli

    class Plan:
        def to_dict(self):
            return {"status": "no_change"}

    state = tmp_path / "state.json"
    state.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(cli, "check_for_updates", lambda config: Plan())

    assert main(["update", "--state-path", str(state)]) == 0
    assert "deprecated read-only alias" in capsys.readouterr().err


def test_top_level_version_uses_runtime_distribution_metadata(capsys) -> None:
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert arancel_mx.__version__ in capsys.readouterr().out


def test_consumer_common_parser_options_are_present() -> None:
    parser = build_parser()
    query = parser.parse_args(
        ["search", "refrigeradores", "--dataset", "data-2026.08.11", "--offline", "--format", "json", "--limit", "7"]
    )
    assert query.command == "search"
    assert query.dataset == "data-2026.08.11"
    assert query.offline is True
    assert query.format == "json"
    assert query.limit == 7

    data = parser.parse_args(["data", "verify", "--dataset", "data-2026.08.11", "--online", "--bundle"])
    assert data.command == "data"
    assert data.data_command == "verify"
    assert data.dataset == "data-2026.08.11"
    assert data.online is True
    assert data.bundle is True
