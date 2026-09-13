"""Stage a complete README dashboard from a verified current export."""

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from string import Template
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def render_readme(snapshot):
    rows = snapshot["observations"]
    count = len(rows)
    counts = {
        key: sum(r[key] is not None for r in rows)
        for key in ("rain", "min_temp", "max_temp")
    }
    paired = sum(r["min_temp"] is not None and r["max_temp"] is not None for r in rows)
    quality = ["| Measure | Available | Missing |", "| --- | ---: | ---: |"]
    for label, value in [
        ("Rainfall", counts["rain"]),
        ("Minimum temperature", counts["min_temp"]),
        ("Maximum temperature", counts["max_temp"]),
        ("Paired temperatures", paired),
    ]:
        quality.append(f"| {label} | {value} / {count} | {count - value} |")
    table = [
        "| Station | Rain (mm) | Minimum (°C) | Maximum (°C) |",
        "| --- | ---: | ---: | ---: |",
    ]

    def measurement(value):
        return "—" if value is None else f"{value:.1f}"

    for row in sorted(rows, key=lambda r: r["place"]):
        place = (
            row["place"]
            .replace("|", "/")
            .replace("\n", " ")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        rain = "Trace" if row["trace_rain"] else measurement(row["rain"])
        table.append(
            f"| {place} | {rain} | {measurement(row['min_temp'])} | {measurement(row['max_temp'])} |"
        )
    captured = (
        datetime.fromisoformat(snapshot["captured_at"])
        .astimezone(timezone(timedelta(hours=5, minutes=30)))
        .strftime("%d %b %Y · %H:%M SLST")
    )
    template = Template(
        (ROOT / "workflows/dashboard_template.md").read_text(encoding="utf-8")
    )
    return template.substitute(
        report_date=snapshot["report_date"],
        captured=captured,
        count=count,
        rain_count=counts["rain"],
        paired_count=paired,
        quality_table="\n".join(quality),
        station_table="\n".join(table),
        trace_count=sum(bool(r["trace_rain"]) for r in rows),
        unknown_count=sum("unknown_station" in r["quality_flags"] for r in rows),
        coordinate_count=sum(
            "legacy_coordinates_unverified" in r["quality_flags"] for r in rows
        ),
    )


def render_assets(assets):
    spec = importlib.util.spec_from_file_location(
        "dashboard_visuals", ROOT / "workflows/render_dashboard_visuals.py"
    )
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    renderer.render(assets)
    from weather_lk.exports.dashboard_charts import render_station_charts

    snapshot = json.loads((assets / "snapshot.json").read_text(encoding="utf-8"))
    render_station_charts(snapshot, assets)
    from weather_lk.exports.station_map import render_map

    render_map(snapshot, assets)


def confined(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Dashboard source path escapes data directory")
    return path


def update_dashboard(data_dir, repository=ROOT):
    data_dir, repository = Path(data_dir), Path(repository)
    manifest = json.loads(
        (data_dir / "exports/current.json").read_text(encoding="utf-8")
    )
    export = confined(data_dir / "exports", manifest["export_dir"])
    content = (export / "list_all.json").read_bytes()
    if (
        hashlib.sha256(content).hexdigest()
        != manifest["files"]["list_all.json"]["sha256"]
    ):
        raise ValueError("Export checksum mismatch")
    daily = json.loads(content)[-1]
    previous = repository / "docs/dashboard/snapshot.json"
    if (
        previous.exists()
        and json.loads(previous.read_text(encoding="utf-8"))["report_date"]
        > daily["date"]
    ):
        raise ValueError("Refusing to publish an older report")
    rows = daily["weather_list"]
    hashes = {r["document_hash"] for r in rows}
    if len(hashes) != 1 or not daily["pdf_path"]:
        raise ValueError(
            "Dashboard requires one verified PDF source for the selected date"
        )
    raw = confined(data_dir, daily["pdf_path"])
    if hashlib.sha256(raw.read_bytes()).hexdigest() != next(iter(hashes)):
        raise ValueError("Source PDF checksum mismatch")
    fields = (
        "station_id",
        "place",
        "date",
        "rain",
        "min_temp",
        "max_temp",
        "trace_rain",
        "quality_flags",
        "parser_version",
        "document_hash",
    )
    snapshot = dict(
        report_date=daily["date"],
        captured_at=manifest["created_at"],
        source_url=next(iter(rows[0].get("sources", [])), None),
        archived_pdf="report.pdf",
        observations=[{k: r.get(k) for k in fields} for r in rows],
    )
    with TemporaryDirectory(prefix="weather-dashboard-") as directory:
        staging = Path(directory)
        (staging / "snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        shutil.copyfile(raw, staging / "report.pdf")
        render_assets(staging)
        readme = render_readme(snapshot)
        # The workflow publishes all staged files in one Git commit only after success.
        target = repository / "docs/dashboard"
        target.mkdir(parents=True, exist_ok=True)
        for path in staging.iterdir():
            shutil.copyfile(path, target / path.name)
        temporary = repository / ".README.next.md"
        temporary.write_text(readme, encoding="utf-8")
        os.replace(temporary, repository / "README.md")
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    args = parser.parse_args()
    result = update_dashboard(args.data_dir)
    print(
        f"Dashboard updated: {result['report_date']}, {len(result['observations'])} observations"
    )
