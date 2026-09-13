"""Immutable observation records shared by parsing, storage and analysis."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Observation:
    station_id: str
    place: str
    date: str
    rain: float | None = None
    min_temp: float | None = None
    max_temp: float | None = None
    lat: float | None = None
    lng: float | None = None
    trace_rain: bool = False
    raw: dict = field(default_factory=dict)
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParseResult:
    report_date: str
    observations: tuple[Observation, ...]
    diagnostics: tuple[str, ...] = ()
