"""Explicit runtime settings; loading settings has no filesystem side effects."""

import math
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    max_reports: int | None = None
    run_timeout_seconds: float = 600
    stale_hours: float = 48
    source: str = "meteo"
    log_level: str = "INFO"
    public_data_url: str = "."
    download_timeout_seconds: float = 60
    download_retries: int = 3

    @property
    def database_path(self):
        return self.data_dir / "weather.sqlite3"

    @classmethod
    def from_env(cls, env=None, data_dir=None):
        env = os.environ if env is None else env

        def positive(name, default, convert=float):
            value = convert(env.get(name, default))
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a positive finite number")
            return value

        limit = env.get("WEATHER_MAX_REPORTS")
        return cls(
            data_dir=Path(
                data_dir
                or env.get("WEATHER_DATA_DIR")
                or Path.cwd() / "var" / "weather_lk"
            )
            .expanduser()
            .resolve(),
            max_reports=positive("WEATHER_MAX_REPORTS", limit, int) if limit else None,
            run_timeout_seconds=positive("WEATHER_RUN_TIMEOUT_SECONDS", 600),
            stale_hours=positive("WEATHER_STALE_HOURS", 48),
            source=env.get("WEATHER_SOURCE", "meteo"),
            log_level=env.get("WEATHER_LOG_LEVEL", "INFO").upper(),
            public_data_url=env.get("WEATHER_PUBLIC_DATA_URL", ".") or ".",
            download_timeout_seconds=positive("WEATHER_DOWNLOAD_TIMEOUT_SECONDS", 60),
            download_retries=positive("WEATHER_DOWNLOAD_RETRIES", 3, int),
        )
