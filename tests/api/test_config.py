from pathlib import Path

import pytest

from arancel_mx.api.config import load_settings


def test_settings_require_explicit_dataset_tag() -> None:
    with pytest.raises(ValueError, match="ARANCEL_MX_API_DATASET"):
        load_settings({})


@pytest.mark.parametrize(
    "value",
    ["latest", "2026.08.15", "data-2026-08-15", "data-2026.8.15"],
)
def test_settings_reject_non_immutable_dataset_tags(value: str) -> None:
    with pytest.raises(ValueError, match="data-YYYY.MM.DD"):
        load_settings({"ARANCEL_MX_API_DATASET": value})


def test_settings_parse_supported_values() -> None:
    settings = load_settings(
        {
            "ARANCEL_MX_API_DATASET": "data-2026.08.15",
            "ARANCEL_MX_API_CACHE_DIR": "/tmp/arancel-api",
            "ARANCEL_MX_API_TIMEOUT": "15",
            "ARANCEL_MX_API_OFFLINE": "true",
        }
    )

    assert settings.dataset_tag == "data-2026.08.15"
    assert settings.cache_dir == Path("/tmp/arancel-api")
    assert settings.timeout == 15.0
    assert settings.offline is True


@pytest.mark.parametrize("value", ["0", "-1", "120.1", "not-a-number"])
def test_settings_reject_invalid_timeout(value: str) -> None:
    with pytest.raises(ValueError, match="ARANCEL_MX_API_TIMEOUT"):
        load_settings(
            {
                "ARANCEL_MX_API_DATASET": "data-2026.08.15",
                "ARANCEL_MX_API_TIMEOUT": value,
            }
        )


def test_settings_default_timeout_is_30_seconds() -> None:
    settings = load_settings({"ARANCEL_MX_API_DATASET": "data-2026.08.15"})

    assert settings.timeout == 30.0
    assert settings.cache_dir is None
    assert settings.offline is False


@pytest.mark.parametrize("value", ["sometimes", "2"])
def test_settings_reject_invalid_offline_value(value: str) -> None:
    with pytest.raises(ValueError, match="ARANCEL_MX_API_OFFLINE"):
        load_settings(
            {
                "ARANCEL_MX_API_DATASET": "data-2026.08.15",
                "ARANCEL_MX_API_OFFLINE": value,
            }
        )
