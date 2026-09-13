"""Missing values stay missing; averages are weighted by valid daily values."""

import calendar
import math
from datetime import date


def _valid(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _measure(values):
    values = [value for value in values if _valid(value)]
    return dict(
        count=len(values),
        mean=sum(values) / len(values) if values else None,
        total=sum(values) if values else None,
        min=min(values) if values else None,
        max=max(values) if values else None,
    )


def _summarize(rows, start=None, end=None, stations=None):
    dates = sorted({date.fromisoformat(row["date"]) for row in rows})
    start = start or (dates[0] if dates else None)
    end = end or (dates[-1] if dates else None)
    stations = (
        stations
        if stations is not None
        else len({row.get("station_id", row.get("place", "station")) for row in rows})
    )
    calendar_days = (end - start).days + 1 if start and end else 0
    observed = len(
        {
            (row.get("station_id", row.get("place", "station")), row["date"])
            for row in rows
        }
    )
    expected = calendar_days * stations
    rain_known = [
        row for row in rows if _valid(row.get("rain")) or row.get("trace_rain")
    ]
    rainy = sum(
        bool(row.get("trace_rain")) or (_valid(row.get("rain")) and row["rain"] > 0)
        for row in rain_known
    )
    result = {
        "records": len(rows),
        "coverage": dict(
            start=start.isoformat() if start else None,
            end=end.isoformat() if end else None,
            calendar_days=calendar_days,
            stations=stations,
            observed_days=len(dates),
            observed_station_days=observed,
            expected_station_days=expected,
            fraction=observed / expected if expected else None,
        ),
        "rainy_days": rainy,
        "rain_known_days": len(rain_known),
        "trace_days": sum(bool(row.get("trace_rain")) for row in rows),
        "rainy_fraction": rainy / len(rain_known) if rain_known else None,
    }
    for measure in ("rain", "min_temp", "max_temp"):
        result[measure] = _measure(row.get(measure) for row in rows)
    result["paired_temp"] = _measure(
        (row["min_temp"] + row["max_temp"]) / 2
        for row in rows
        if _valid(row.get("min_temp")) and _valid(row.get("max_temp"))
    )
    return result


def summarize(rows, *, start=None, end=None):
    """Summarize station-day rows, including valid counts and span coverage.

    Rain totals across stations are station-day sums, not regional rainfall.
    Coverage assumes the stations in this snapshot were expected throughout its
    span; it describes data availability, not station operating history.
    """
    rows = list(rows)
    stations = len({row.get("station_id", row.get("place", "station")) for row in rows})
    start = date.fromisoformat(start) if isinstance(start, str) else start
    end = date.fromisoformat(end) if isinstance(end, str) else end
    if start and end and start > end:
        raise ValueError("Coverage start must be on or before end")
    selected = [
        row
        for row in rows
        if (start is None or row["date"] >= start.isoformat())
        and (end is None or row["date"] <= end.isoformat())
    ]
    return _summarize(selected, start, end, stations)


def month_statistics(rows):
    """Return every calendar month in the observed span, including empty months."""
    rows = list(rows)
    if not rows:
        return {}
    dates = sorted(date.fromisoformat(row["date"]) for row in rows)
    current = dates[0].replace(day=1)
    last = dates[-1].replace(day=1)
    stations = len({row.get("station_id", row.get("place", "station")) for row in rows})
    grouped = {}
    for row in rows:
        grouped.setdefault(row["date"][:7], []).append(row)
    result = {}
    while current <= last:
        key = current.strftime("%Y-%m")
        end = current.replace(day=calendar.monthrange(current.year, current.month)[1])
        result[key] = _summarize(grouped.get(key, []), current, end, stations)
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
    return result
