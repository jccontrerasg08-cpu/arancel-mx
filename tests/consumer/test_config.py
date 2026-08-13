from pathlib import Path

import pytest

from arancel_mx.consumer.config import resolve_config


ENV_NAMES = (
    "ARANCEL_MX_CACHE_DIR",
    "ARANCEL_MX_DATASET",
    "ARANCEL_MX_OFFLINE",
    "ARANCEL_MX_TIMEOUT",
)


def _clear_consumer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_default_cache_uses_xdg_cache_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_consumer_env(monkeypatch)
    expected = tmp_path / "xdg-cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(expected))

    config = resolve_config()

    assert config.cache_dir == expected / "arancel-mx"


def test_explicit_cache_dir_overrides_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_consumer_env(monkeypatch)
    monkeypatch.setenv("ARANCEL_MX_CACHE_DIR", str(tmp_path / "env"))

    config = resolve_config(cache_dir=tmp_path / "explicit")

    assert config.cache_dir == tmp_path / "explicit"


def test_environment_cache_dir_overrides_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_consumer_env(monkeypatch)
    expected = tmp_path / "environment"
    monkeypatch.setenv("ARANCEL_MX_CACHE_DIR", str(expected))

    config = resolve_config()

    assert config.cache_dir == expected


def test_explicit_dataset_overrides_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_consumer_env(monkeypatch)
    monkeypatch.setenv("ARANCEL_MX_DATASET", "data-2026.08.10")

    config = resolve_config(dataset="data-2026.08.11")

    assert config.dataset == "data-2026.08.11"


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "YeS", "on", "ON"])
def test_offline_accepts_true_environment_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    _clear_consumer_env(monkeypatch)
    monkeypatch.setenv("ARANCEL_MX_OFFLINE", value)

    assert resolve_config().offline is True


@pytest.mark.parametrize("value", ["0", "false", "FALSE", "no", "No", "off", "OFF"])
def test_offline_accepts_false_environment_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    _clear_consumer_env(monkeypatch)
    monkeypatch.setenv("ARANCEL_MX_OFFLINE", value)

    assert resolve_config().offline is False


def test_invalid_offline_environment_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_consumer_env(monkeypatch)
    monkeypatch.setenv("ARANCEL_MX_OFFLINE", "sometimes")

    with pytest.raises(ValueError, match="ARANCEL_MX_OFFLINE must be a boolean value"):
        resolve_config()


@pytest.mark.parametrize("value", [0, 0.0, -1, -0.5])
def test_timeout_must_be_positive(
    monkeypatch: pytest.MonkeyPatch, value: float
) -> None:
    _clear_consumer_env(monkeypatch)

    with pytest.raises(ValueError, match="timeout must be greater than zero"):
        resolve_config(timeout=value)


def test_environment_timeout_must_be_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_consumer_env(monkeypatch)
    monkeypatch.setenv("ARANCEL_MX_TIMEOUT", "0")

    with pytest.raises(ValueError, match="timeout must be greater than zero"):
        resolve_config()


def test_explicit_timeout_overrides_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_consumer_env(monkeypatch)
    monkeypatch.setenv("ARANCEL_MX_TIMEOUT", "99")

    config = resolve_config(timeout=7.5)

    assert config.timeout == 7.5


def test_explicit_false_offline_overrides_true_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_consumer_env(monkeypatch)
    monkeypatch.setenv("ARANCEL_MX_OFFLINE", "true")

    config = resolve_config(offline=False)

    assert config.offline is False


def test_unicode_custom_cache_path_is_preserved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clear_consumer_env(monkeypatch)
    expected = tmp_path / "caché con ñ" / "datos"

    config = resolve_config(cache_dir=expected)

    assert config.cache_dir == expected
