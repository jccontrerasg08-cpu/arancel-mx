import json

from arancel_mx import cli
from arancel_mx.cli import build_parser, main


def test_parser_exposes_tariff_command_families():
    help_text = build_parser().format_help()

    for command in ("build", "update", "reconcile", "release"):
        assert command in help_text


def test_main_prints_help_without_arguments(capsys):
    assert main([]) == 0
    assert "arancel-mx" in capsys.readouterr().out


def test_build_delegates_once_and_prints_json(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "build_release", lambda database, output: calls.append((database, output)) or {"status": "passed"})

    result = main(["build", "--database", str(tmp_path / "db.duckdb"), "--output-dir", str(tmp_path / "out")])

    assert result == 0
    assert calls == [(tmp_path / "db.duckdb", tmp_path / "out")]
    assert json.loads(capsys.readouterr().out) == {"status": "passed"}


def test_update_delegates_once_with_typed_config(tmp_path, monkeypatch, capsys):
    calls = []

    class Plan:
        def to_dict(self):
            return {"status": "no_change"}

    monkeypatch.setattr(cli, "check_for_updates", lambda config: calls.append(config) or Plan())

    assert main(["update", "--state-path", str(tmp_path / "state.json")]) == 0
    assert calls[0].state_path == tmp_path / "state.json"
    assert json.loads(capsys.readouterr().out) == {"status": "no_change"}


def test_reconcile_reads_json_and_delegates_once(tmp_path, monkeypatch, capsys):
    paths = [tmp_path / name for name in ("ledger.json", "dof.json", "snice.json")]
    for path in paths:
        path.write_text("[]", encoding="utf-8")
    calls = []
    monkeypatch.setattr(cli, "reconcile_legal_instruments", lambda *items: calls.append(items) or {"publishable": True})

    assert main(["reconcile", "--ledger-json", str(paths[0]), "--dof-json", str(paths[1]), "--snice-json", str(paths[2])]) == 0
    assert calls == [([], [], [])]
    assert json.loads(capsys.readouterr().out) == {"publishable": True}


def test_release_delegates_once(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "prepare_release_archive", lambda *paths: calls.append(paths) or {"source_count": 2})

    assert main(["release", "--release-dir", str(tmp_path / "release"), "--source-dir", str(tmp_path / "sources"), "--latest-dir", str(tmp_path / "latest")]) == 0
    assert calls == [(tmp_path / "release", tmp_path / "sources", tmp_path / "latest")]
    assert json.loads(capsys.readouterr().out) == {"source_count": 2}


def test_expected_validation_error_returns_two(tmp_path, monkeypatch, capsys):
    def fail(*args):
        raise ValueError("invalid release")

    monkeypatch.setattr(cli, "build_release", fail)

    result = main(["build", "--database", str(tmp_path / "db"), "--output-dir", str(tmp_path / "out")])

    assert result == 2
    assert capsys.readouterr().err == "error: invalid release\n"
