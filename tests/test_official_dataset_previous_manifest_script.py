import json

import scripts.build_official_dataset as build_script


def test_script_loads_previous_manifest_and_emits_no_change_status(
    tmp_path, monkeypatch, capsys
):
    previous = {
        "dataset_version": "2026.08.09",
        "validation_status": "passed",
        "row_count": 5,
        "source_identity": [{"dataset_key": "fixture"}],
    }
    previous_path = tmp_path / "previous-manifest.json"
    previous_path.write_text(json.dumps(previous), encoding="utf-8")
    calls = []

    def fake_build(config, previous_manifest=None):
        calls.append((config, previous_manifest))
        return {
            "status": "no_change",
            "dataset_version": config.dataset_version,
            "row_count": 5,
            "validation_status": "passed",
            "source_count": 5,
            "output_dir": None,
        }

    monkeypatch.setattr(build_script, "build_official_dataset", fake_build)

    result = build_script.main(
        [
            "--work-dir",
            str(tmp_path / "work"),
            "--output-dir",
            str(tmp_path / "release"),
            "--effective-as-of",
            "2026-08-10",
            "--dataset-version",
            "2026.08.10",
            "--previous-manifest",
            str(previous_path),
        ]
    )

    assert result == 0
    assert calls[0][1] == previous
    assert json.loads(capsys.readouterr().out)["status"] == "no_change"
