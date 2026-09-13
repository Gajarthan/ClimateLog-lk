"""Legacy schema conversion with additive station and source metadata."""

import csv
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone


def station_slug(station_id):
    value = str(station_id)
    readable = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")[:60] or "station"
    return f"st-{readable}-{hashlib.sha256(value.encode()).hexdigest()[:12]}"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_tsv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, delimiter="\t", extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (list, dict))
                    else value
                    for key, value in row.items()
                    if key in fields
                }
            )


def date_epoch(day):
    return int(
        datetime.fromisoformat(day)
        .replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
        .timestamp()
    )


def build_legacy_data(rows, public_data_url="."):
    """Build payloads keyed by legacy filename stem, without performing I/O."""
    rows = sorted(rows, key=lambda row: (row["date"], row["station_id"]))
    by_date, by_place, flat, places, events = {}, {}, [], {}, {}
    for row in rows:
        day, place = row["date"], row["place"]
        epoch = date_epoch(day)
        by_date.setdefault(day, dict(date=day, date_ut=epoch, weather_list=[]))[
            "weather_list"
        ].append(dict(row))
        by_place.setdefault(place, []).append(dict(row))
        measures = dict(
            rain_mm=row.get("rain"),
            temp_min_c=row.get("min_temp"),
            temp_max_c=row.get("max_temp"),
        )
        provenance = {
            key: row.get(key)
            for key in (
                "station_id",
                "trace_rain",
                "raw_path",
                "document_hash",
                "parser_version",
                "sources",
                "quality_flags",
            )
        }
        flat.append(dict(id=place, time_ut=epoch, **measures, **provenance))
        places[place] = dict(
            id=place,
            station_id=row["station_id"],
            lat_lng=[row.get("lat"), row.get("lng")],
        )
        events.setdefault(place, {})[day.replace("-", "")] = measures
    for daily in by_date.values():
        weather = daily["weather_list"]
        paths = sorted({row["raw_path"] for row in weather if row.get("raw_path")})
        # Archived PDFs and imported JSON use distinct suffixes in DocumentStore.
        # Preserve both as sources without suggesting an absent PDF exists.
        pdf_paths = [path for path in paths if path.lower().endswith(".pdf")]
        daily["source_paths"] = paths
        daily["pdf_paths"] = pdf_paths
        daily["pdf_path"] = pdf_paths[0] if pdf_paths else None
        for key, measure, chooser in [
            ("max_rain", "rain", max),
            ("min_temp", "min_temp", min),
            ("max_temp", "max_temp", max),
        ]:
            available = [row for row in weather if row.get(measure) is not None]
            extreme = (
                chooser(available, key=lambda row: row[measure]) if available else None
            )
            daily[key] = {
                key: extreme[measure] if extreme else None,
                key + "_place": extreme["place"] if extreme else None,
            }
    days = list(by_date)
    latest_epoch = date_epoch(days[-1]) if days else None
    latest = [row for row in flat if row["time_ut"] == latest_epoch]
    alert = dict(
        url_source="https://meteo.gov.lk",
        url_structured=public_data_url.rstrip("/") + "/flat.json",
        event="weather_report",
        event_measures=["rain_mm", "temp_min_c", "temp_max_c"],
        frequency="daily",
        event_data=events,
    )
    return dict(
        list_all=list(by_date.values()),
        idx_by_place=dict(sorted(by_place.items())),
        idx_by_date=by_date,
        date_list=days,
        flat=flat,
        flat_places=[places[key] for key in sorted(places)],
        latest_flat=latest,
        latest_places=[places[key] for key in sorted({row["id"] for row in latest})],
        alert_data=alert,
    )
