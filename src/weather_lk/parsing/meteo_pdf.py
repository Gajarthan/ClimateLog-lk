"""Parse the Meteorology Department's daily station report tables.

The date belongs to the printed report, never to download time. Camelot is an
optional dependency loaded only when actual PDF extraction is requested.
"""

import math
import re
from datetime import date

from weather_lk.domain.models import Observation, ParseResult
from weather_lk.domain.validation import ValidationError
from weather_lk.stations.catalog import StationCatalog

PARSER_VERSION = "meteo-v1"
_DATE = re.compile(r"\b(\d{4})[.\-/](\d{2})[.\-/](\d{2})\b")
_MISSING = {"", "-", "--", "—", "NA", "N/A", "N.A.", "NIL", "NULL"}


def _number(token, field, flags, diagnostics, location):
    token = str(token)
    value = token.strip().upper()
    if value in _MISSING:
        flags.append(f"missing_{field}")
        return None, False
    if field == "rain" and value in {"TR", "TRACE"}:
        return 0.0, True
    suffix = r"\s*MM" if field == "rain" else r"\s*(?:°\s*)?C"
    value = re.sub(suffix + r"$", "", value).strip()
    # Lattice extraction occasionally carries the preceding column unit onto
    # the first value of a rainfall section. Keep the unmodified token in raw.
    if field == "rain":
        value = re.sub(r"^MM\s+", "", value)
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", value):
        number = float(value)
        if math.isfinite(number):
            return number, False
    flags.append(f"malformed_{field}")
    diagnostics.append(f"{location}: malformed {field} token {token!r}")
    return None, False


def _is_weather_table(table):
    text = " ".join(str(cell) for row in table for cell in row).casefold()
    simple_rain = any(
        any(re.fullmatch(r"stations?", cell.strip(), re.IGNORECASE) for cell in row)
        and "rainfall" in " ".join(row).casefold()
        for row in table
    )
    return (
        "meteorological stations" in text
        or "rainfall stations" in text
        or simple_rain
        or ("station" in text and "max" in text and "min" in text and "rain" in text)
    )


def _rainfall_pairs(row):
    """Recognize adjacent pairs or the two observed lattice spacer layouts."""
    if len(row) == 2:
        pairs = [(0, 1)]
    elif len(row) == 4:
        pairs = [(0, 1), (2, 3)]
    elif len(row) == 5 and not row[3]:
        pairs = [(0, 1), (2, 4)]
    elif len(row) == 6 and not row[3] and not row[4]:
        pairs = [(0, 1), (2, 5)]
    elif len(row) == 6:
        pairs = [(0, 1), (2, 3), (4, 5)]
    else:
        return None
    for name_index, rain_index in pairs:
        name = row[name_index]
        if (not name and row[rain_index]) or (
            name and not any(character.isalpha() for character in name)
        ):
            return None
    return pairs


def _weather_columns(row, current):
    columns = dict(current)
    for field, pattern in {
        "station": r"\bstations?\b",
        "max_temp": r"max(?:imum)?\b",
        "min_temp": r"min(?:imum)?\b",
        "rain": r"\brainfall\b",
    }.items():
        matches = [
            index
            for index, cell in enumerate(row)
            if re.search(pattern, cell, re.IGNORECASE)
        ]
        if len(matches) > 1:
            raise ValidationError(
                f"Ambiguous weather column header for {field}: {row!r}"
            )
        if matches:
            columns[field] = matches[0]
    if len(set(columns.values())) != len(columns):
        raise ValidationError(f"Unsupported weather column header: {row!r}")
    return columns


def parse_tables(tables, catalog=None) -> ParseResult:
    """Parse supported station table layouts, retaining raw tokens and issues.

    Each table contains rows of strings. Recognizable weather headers are required
    so charts, legends, statistics and unrelated tabular content stay excluded.
    """
    tables = [[list(map(str, row)) for row in table] for table in tables]
    relevant = [
        (index, table) for index, table in enumerate(tables) if _is_weather_table(table)
    ]
    relevant_indices = {index for index, _ in relevant}
    date_rows = [
        " ".join(row)
        for index, table in enumerate(tables)
        for row in table
        if index in relevant_indices or "weather report" in " ".join(row).casefold()
    ]
    dates = set()
    for text in date_rows:
        for match in _DATE.finditer(text):
            try:
                dates.add(date(*map(int, match.groups())).isoformat())
            except ValueError as exc:
                raise ValidationError(f"Invalid report date: {match.group()}") from exc
    if len(dates) != 1:
        raise ValidationError(
            f"Expected one unambiguous report date, found {sorted(dates)}"
        )
    report_date = dates.pop()
    catalog = catalog if catalog is not None else StationCatalog()
    diagnostics = []
    observations = []
    dated_text = " ".join(date_rows)
    period_ending = bool(
        re.search(r"period\s+ending\s+at\s+0830", dated_text, re.IGNORECASE)
    )
    if period_ending:
        diagnostics.append(
            "Printed report date identifies the 24-hour period ending at 0830SLTS; no date shift applied."
        )
    else:
        diagnostics.append(
            "Report date meaning uncertain; printed date retained without a date shift."
        )

    def append_observation(name, rain, maximum, minimum, table_index, row_index, row):
        station = catalog.resolve(name)
        if not station["place"]:
            diagnostics.append(
                f"Table {table_index}, row {row_index}: blank station ignored"
            )
            return
        flags = list(station.pop("quality_flags"))
        if not period_ending:
            flags.append("report_date_meaning_uncertain")
        location = f"Table {table_index}, row {row_index}, {station['place']}"
        rainfall, trace = _number(rain, "rain", flags, diagnostics, location)
        max_temp = min_temp = None
        if maximum is not None:
            max_temp, _ = _number(maximum, "max_temp", flags, diagnostics, location)
            min_temp, _ = _number(minimum, "min_temp", flags, diagnostics, location)
        raw = dict(
            station=name,
            rain=rain,
            max_temp=maximum,
            min_temp=minimum,
            report_date=report_date,
            row=row,
            table_index=table_index,
            row_index=row_index,
        )
        observations.append(
            Observation(
                **station,
                date=report_date,
                rain=rainfall,
                min_temp=min_temp,
                max_temp=max_temp,
                trace_rain=trace,
                raw=raw,
                quality_flags=tuple(flags),
            )
        )

    for table_index, table in relevant:
        mode = None
        weather_columns = dict(station=0, max_temp=1, min_temp=2, rain=3)
        for row_index, raw_row in enumerate(table):
            row = [" ".join(cell.split()) for cell in raw_row]
            text = " ".join(row).casefold()
            if "highest rainfall" in text:
                diagnostics.append(
                    "Report summary (not a station-table observation): " + " ".join(row)
                )
                mode = None
                continue
            if "rainfall stations" in text:
                mode = "rain"
                continue
            if "meteorological stations" in text or (
                "station" in text and "max" in text and "min" in text
            ):
                mode = "weather"
                weather_columns = _weather_columns(row, weather_columns)
                continue
            if (
                any(re.fullmatch(r"stations?", cell, re.IGNORECASE) for cell in row)
                and "rainfall" in text
            ):
                mode = "rain"
                continue
            if mode == "weather" and "max" in text and "min" in text:
                weather_columns = _weather_columns(row, weather_columns)
                continue
            if (
                _DATE.search(text)
                or not any(row)
                or "weather report" in text
                or "catchment areas" in text
                or "temperature" in text
                or "rainfall" in text
                or ("max" in text and "min" in text)
            ):
                continue
            if (
                mode == "weather"
                and len(row) in {4, 5, 6}
                and max(weather_columns.values()) < len(row)
                and row[weather_columns["station"]]
                and not any(
                    cell
                    for index, cell in enumerate(row)
                    if index not in weather_columns.values()
                )
            ):
                append_observation(
                    raw_row[weather_columns["station"]],
                    raw_row[weather_columns["rain"]],
                    raw_row[weather_columns["max_temp"]],
                    raw_row[weather_columns["min_temp"]],
                    table_index,
                    row_index,
                    raw_row,
                )
            elif mode == "rain" and (pairs := _rainfall_pairs(row)) is not None:
                for name_index, rain_index in pairs:
                    if row[name_index]:
                        append_observation(
                            raw_row[name_index],
                            raw_row[rain_index],
                            None,
                            None,
                            table_index,
                            row_index,
                            raw_row,
                        )
            elif mode is not None:
                raise ValidationError(
                    f"Table {table_index}, row {row_index}: unsupported station row {raw_row!r}"
                )
    return ParseResult(report_date, tuple(observations), tuple(diagnostics))


def parse_pdf(path, catalog=None) -> ParseResult:
    """Extract all PDF pages explicitly; importing this module does no PDF work."""
    import camelot

    tables = camelot.read_pdf(str(path), pages="all", flavor="lattice")
    return parse_tables([table.df.values.tolist() for table in tables], catalog=catalog)
