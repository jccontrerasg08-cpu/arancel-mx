import json

from scripts.static_pages_unchanged import main, same_content

FILES = {"sections.json": {"bytes": 764, "sha256": "a" * 64}, "chapters.json": {"bytes": 10, "sha256": "b" * 64}}


def manifest(**overrides):
    value = {
        "static_format": "1",
        "dataset_tag": "data-2026.11.06",
        "dataset_version": "2026.11.06",
        "record_count": 26641,
        "files": FILES,
        "generated_at": "2026-11-06T20:30:40+00:00",
    }
    value.update(overrides)
    return value


def test_build_time_does_not_count_as_a_change() -> None:
    assert same_content(manifest(), manifest(generated_at="2026-11-07T11:17:00+00:00"))


def test_a_changed_file_for_the_same_tag_is_a_change() -> None:
    changed = {**FILES, "sections.json": {"bytes": 800, "sha256": "c" * 64}}
    assert not same_content(manifest(), manifest(files=changed))


def test_an_added_file_is_a_change() -> None:
    added = {**FILES, "new.json": {"bytes": 1, "sha256": "d" * 64}}
    assert not same_content(manifest(), manifest(files=added))


def test_a_new_release_is_a_change() -> None:
    assert not same_content(manifest(), manifest(dataset_tag="data-2026.11.07", dataset_version="2026.11.07"))


def test_a_deployed_manifest_missing_a_field_is_a_change() -> None:
    deployed = manifest()
    del deployed["static_format"]
    assert not same_content(deployed, manifest())


def test_the_command_publishes_when_in_doubt(tmp_path) -> None:
    built = tmp_path / "built.json"
    built.write_text(json.dumps(manifest()), encoding="utf-8")
    deployed = tmp_path / "deployed.json"

    assert main([str(deployed), str(built)]) == 1  # nothing deployed yet
    deployed.write_text("not json", encoding="utf-8")
    assert main([str(deployed), str(built)]) == 1  # unreadable
    deployed.write_text(json.dumps(manifest(generated_at="2026-11-05T00:00:00+00:00")), encoding="utf-8")
    assert main([str(deployed), str(built)]) == 0  # same content
    deployed.write_text(json.dumps(manifest(record_count=1)), encoding="utf-8")
    assert main([str(deployed), str(built)]) == 1  # different content
    assert main([str(deployed)]) == 2  # usage error
