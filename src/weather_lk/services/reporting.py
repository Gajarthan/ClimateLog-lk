"""Publish complete immutable export snapshots by switching one manifest."""

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from weather_lk.analytics.statistics import month_statistics, summarize
from weather_lk.exports.charts import render_charts
from weather_lk.exports.json_tsv import (
    build_legacy_data,
    date_epoch,
    station_slug,
    write_json,
    write_tsv,
)
from weather_lk.storage.database import Database
from weather_lk.storage.observations import ObservationStore


def _display(value):
    return "—" if value is None else f"{value:.2f}"


def _summary_markdown(summary):
    lines = [
        "# Weather statistics",
        "",
        "Each mean uses valid station-day measurements. Missing values are excluded; zero is valid.",
        "Paired temperature means require both daily minimum and maximum. Trace rainfall counts as rainy.",
        "Rain totals sum station-day values and are not regional rainfall totals.",
        "Monthly coverage uses complete calendar months and all stations in this snapshot.",
        "",
        "| Period | Records | Rain n | Rain mean (mm) | Minimum n | Minimum mean (°C) | Maximum n | Maximum mean (°C) | Paired n | Paired mean (°C) | Coverage |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for period, stats in [
        ("All observations", summary["all_period"]),
        *summary["months"].items(),
    ]:
        fields = [period, str(stats["records"])]
        for key in ("rain", "min_temp", "max_temp", "paired_temp"):
            fields.extend([str(stats[key]["count"]), _display(stats[key]["mean"])])
        fraction = stats["coverage"]["fraction"]
        fields.append("—" if fraction is None else f"{fraction:.1%}")
        lines.append("| " + " | ".join(fields) + " |")
    return "\n".join(lines) + "\n"


def _readme(rows, summary, station_files, chart_paths, stale):
    lines = [
        "# Weather observation reports",
        "",
        f"Accepted station observations: **{len(rows)}**. Stations: **{len(station_files)}**.",
        "",
        "No observations are available."
        if not rows
        else f"Dates: {summary['all_period']['coverage']['start']} to {summary['all_period']['coverage']['end']}.",
        "Freshness: no observations."
        if stale is None
        else (
            "Freshness: latest observation is stale."
            if stale
            else "Freshness: within the configured threshold."
        ),
        "",
        "[Statistics](summary.md) · [Statistics JSON](summary.json) · [Daily coverage](coverage.tsv) · [Station coverage](station_coverage.tsv)",
        "[All reports](list_all.json) · [Flat observations](flat.json) · [Latest observations](latest_flat.json)",
        "",
        "Null means unavailable, never zero. Coverage counts observed station-days against calendar days times the stations in the snapshot; station operating periods are unknown.",
        "Charts show up to the latest 90 calendar days. Daily curves average only stations reporting each measure; gaps remain missing and station coverage can change.",
        "Source paths are relative to the data directory. JSON records retain original fields, document hashes, parser versions, source URLs, and quality flags.",
        "",
        "| Station | JSON | TSV |",
        "| --- | --- | --- |",
    ]
    for station, metadata in sorted(station_files.items()):
        label = metadata["place"].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {label} | [JSON]({metadata['json']}) | [TSV]({metadata['tsv']}) |"
        )
    for path in chart_paths:
        lines.extend(
            ["", f"![{path.stem.replace('_', ' ').title()}](charts/{path.name})"]
        )
    sources = sorted({row["raw_path"] for row in rows if row.get("raw_path")})
    if sources:
        lines.extend(["", "## Archived source documents", ""])
        for raw_path in sources:
            # Only link paths confined to the data directory; preserve all values in JSON.
            path = Path(raw_path)
            if not path.is_absolute() and ".." not in path.parts:
                lines.append(f"- [{path.name}](../../{path.as_posix()})")
    return "\n".join(lines) + "\n"


def export_reports(settings, database=None, charts=True):
    """Read current observations once; publish current.json only after every output succeeds.

    Failed generations may remain as unreferenced directories for inspection.
    Readers resolve current.json once and use that immutable directory throughout.
    """
    database = database if database is not None else Database(settings.database_path)
    rows = ObservationStore(database).current()
    now = datetime.now(timezone.utc)
    export_id = now.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex
    exports_dir = Path(settings.data_dir) / "exports"
    output = exports_dir / export_id
    output.mkdir(parents=True, exist_ok=False)
    public_base = getattr(settings, "public_data_url", ".").rstrip("/")
    public_url = (
        "." if public_base in ("", ".") else f"{public_base}/exports/{export_id}"
    )
    legacy = build_legacy_data(rows, public_url)
    for name, value in legacy.items():
        write_json(output / f"{name}.json", value)

    by_station = {}
    for row in rows:
        by_station.setdefault(row["station_id"], []).append(row)
    station_files, coverage = {}, []
    fields = [
        "date",
        "station_id",
        "place",
        "rain",
        "min_temp",
        "max_temp",
        "lat",
        "lng",
        "trace_rain",
        "raw_path",
        "document_hash",
        "parser_version",
        "sources",
        "quality_flags",
        "raw",
    ]
    summary = dict(
        all_period=summarize(rows), months=month_statistics(rows), stations={}
    )
    if rows:
        end = max(row["date"] for row in rows)
        start = (datetime.fromisoformat(end).date() - timedelta(days=29)).isoformat()
        summary["last_30_calendar_days"] = dict(
            start=start, end=end, statistics=summarize(rows, start=start, end=end)
        )
    else:
        summary["last_30_calendar_days"] = dict(
            start=None, end=None, statistics=summarize([])
        )
    for station, station_rows in sorted(by_station.items()):
        stem = station_slug(station)
        metadata = dict(
            place=station_rows[-1]["place"],
            json=f"data_by_place/{stem}.json",
            tsv=f"data_by_place/{stem}.tsv",
        )
        station_files[station] = metadata
        write_json(output / metadata["json"], station_rows)
        write_tsv(output / metadata["tsv"], station_rows, fields)
        stats = summarize(station_rows)
        summary["stations"][station] = dict(
            place=metadata["place"],
            all_period=stats,
            months=month_statistics(station_rows),
        )
        coverage.append(
            dict(
                station_id=station,
                place=metadata["place"],
                **stats["coverage"],
                rain_count=stats["rain"]["count"],
                min_temp_count=stats["min_temp"]["count"],
                max_temp_count=stats["max_temp"]["count"],
                paired_temp_count=stats["paired_temp"]["count"],
            )
        )
    write_tsv(
        output / "station_coverage.tsv",
        coverage,
        [
            "station_id",
            "place",
            "start",
            "end",
            "calendar_days",
            "observed_days",
            "observed_station_days",
            "expected_station_days",
            "fraction",
            "rain_count",
            "min_temp_count",
            "max_temp_count",
            "paired_temp_count",
        ],
    )
    daily_coverage = []
    if rows:
        first = datetime.fromisoformat(min(row["date"] for row in rows)).date()
        last = datetime.fromisoformat(max(row["date"] for row in rows)).date()
        for offset in range((last - first).days + 1):
            day = (first + timedelta(days=offset)).isoformat()
            weather = legacy["idx_by_date"].get(day, {}).get("weather_list", [])
            daily_coverage.append(
                dict(
                    date=day,
                    has_data=bool(weather),
                    n=len(weather),
                    n_temp=sum(row.get("max_temp") is not None for row in weather),
                    n_rain=sum(row.get("rain") is not None for row in weather),
                )
            )
    write_tsv(
        output / "coverage.tsv",
        daily_coverage,
        ["date", "has_data", "n", "n_temp", "n_rain"],
    )
    write_json(output / "summary.json", summary)
    (output / "summary.md").write_text(_summary_markdown(summary), encoding="utf-8")
    chart_paths = render_charts(rows, output / "charts") if charts else []
    latest = max((row["date"] for row in rows), default=None)
    # Date-only source reports describe the period ending at 08:30 local time.
    report_end = date_epoch(latest) + 8.5 * 3600 if latest else None
    stale = (
        (now.timestamp() - report_end) > getattr(settings, "stale_hours", 48) * 3600
        if latest
        else None
    )
    (output / "README.md").write_text(
        _readme(rows, summary, station_files, chart_paths, stale), encoding="utf-8"
    )
    files = {}
    for path in sorted(output.rglob("*")):
        if path.is_file():
            content = path.read_bytes()
            files[path.relative_to(output).as_posix()] = dict(
                bytes=len(content), sha256=hashlib.sha256(content).hexdigest()
            )
    manifest = dict(
        schema_version=1,
        export_dir=export_id,
        created_at=now.isoformat(),
        records=len(rows),
        latest_date=latest,
        stale=stale,
        stations=station_files,
        files=files,
    )
    temporary = exports_dir / f".current-{uuid.uuid4().hex}.json"
    try:
        write_json(temporary, manifest)
        os.replace(temporary, exports_dir / "current.json")
    finally:
        temporary.unlink(missing_ok=True)
    return dict(export_dir=str(output), manifest=manifest, records=len(rows))
