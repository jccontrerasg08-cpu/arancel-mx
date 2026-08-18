from __future__ import annotations

from datetime import datetime, timezone


def test_runner_loads_the_certified_bundle_before_opening_the_database(monkeypatch, tmp_path):
    from scripts import promote_operational_release as runner

    events: list[object] = []
    release = object()
    records = [object()]

    def load_bundle(path, *, published_at, source_checked_at):
        events.append(("load", path, published_at, source_checked_at))
        return release, records

    class Connection:
        def __enter__(self):
            events.append("connection_enter")
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            events.append("connection_exit")
            return False

    def connect(url):
        events.append(("connect", url))
        return Connection()

    def promote(connection, actual_release, actual_records):
        events.append(("promote", connection, actual_release, actual_records))

    monkeypatch.setattr(runner, "load_certified_release", load_bundle)
    monkeypatch.setattr(runner, "promote_release", promote)

    published_at = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
    source_checked_at = datetime(2026, 8, 18, 11, 17, tzinfo=timezone.utc)
    result = runner.promote_operational_release(
        tmp_path / "release",
        database_url="postgresql://central",
        published_at=published_at,
        source_checked_at=source_checked_at,
        connect=connect,
    )

    assert result == {"release_tag": None, "record_count": 1}
    assert events[0] == ("load", tmp_path / "release", published_at, source_checked_at)
    assert events[1] == ("connect", "postgresql://central")
    assert events[2] == "connection_enter"
    assert events[3][0] == "promote"
    assert events[3][2:] == (release, records)
    assert events[4] == "connection_exit"


def test_runner_rejects_missing_database_url_before_certification(tmp_path):
    from scripts.promote_operational_release import OperationalPromotionRunnerError
    from scripts.promote_operational_release import promote_operational_release

    try:
        promote_operational_release(
            tmp_path / "release",
            database_url="",
            published_at=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
            source_checked_at=datetime(2026, 8, 18, 11, 17, tzinfo=timezone.utc),
        )
    except OperationalPromotionRunnerError as error:
        assert "database_url" in str(error)
    else:
        raise AssertionError("the central database URL must be configured explicitly")
