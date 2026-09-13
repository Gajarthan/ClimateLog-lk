import pytest

from weather_lk.config import Settings


def test_settings_are_explicit_and_do_not_create_directories(tmp_path):
    settings = Settings.from_env({"WEATHER_DATA_DIR": str(tmp_path / "data")})
    assert settings.data_dir == tmp_path / "data"
    assert settings.max_reports is None
    assert settings.database_path == tmp_path / "data" / "weather.sqlite3"
    assert not settings.data_dir.exists()


@pytest.mark.parametrize(
    "name,value",
    [
        ("WEATHER_MAX_REPORTS", "0"),
        ("WEATHER_RUN_TIMEOUT_SECONDS", "-1"),
        ("WEATHER_STALE_HOURS", "nan"),
    ],
)
def test_invalid_limits_are_rejected(name, value):
    with pytest.raises(ValueError):
        Settings.from_env({name: value})


def test_windows_has_no_implicit_processing_limit(tmp_path):
    settings = Settings.from_env(
        {"WEATHER_MAX_REPORTS": "12", "WEATHER_RUN_TIMEOUT_SECONDS": "90"}
    )
    assert settings.max_reports == 12
    assert settings.run_timeout_seconds == 90
