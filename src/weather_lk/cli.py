"""Command-line entry points for the local observation pipeline."""

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone

from weather_lk import __version__
from weather_lk.config import Settings


def status(settings):
    if not settings.database_path.exists():
        return {
            "initialized": False,
            "records": 0,
            "latest_observation_date": None,
            "stale": True,
            "runs": [],
        }
    from weather_lk.storage.database import Database
    from weather_lk.storage.observations import ObservationStore

    database = Database(settings.database_path)
    with database.connect() as connection:
        count, latest = connection.execute(
            "SELECT COUNT(*),MAX(observed_on) FROM current_observations"
        ).fetchone()
    local_zone = timezone(timedelta(hours=5, minutes=30))
    # Date-only reports refer to the period ending at 08:30 local time.
    latest_time = (
        datetime.fromisoformat(latest + "T08:30:00").replace(tzinfo=local_zone)
        if latest
        else None
    )
    age_hours = (
        (datetime.now(timezone.utc) - latest_time).total_seconds() / 3600
        if latest_time
        else None
    )
    return {
        "initialized": True,
        "records": count,
        "latest_observation_date": latest,
        "age_hours": age_hours,
        "stale": age_hours is None or age_hours > settings.stale_hours,
        "runs": database.runs(),
        "attempts": ObservationStore(database).attempts(),
    }


def build_parser():
    parser = argparse.ArgumentParser(
        prog="weather-lk",
        description="Collect, validate and report Sri Lankan weather observations",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--data-dir", help="Durable data directory (or WEATHER_DATA_DIR)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Initialize local storage without cloning")
    commands.add_parser("status", help="Show freshness and recent processing attempts")
    for name in ("ingest", "run"):
        command = commands.add_parser(
            name,
            help="Collect and parse reports"
            if name == "ingest"
            else "Collect, parse and export in order",
        )
        command.add_argument("--source", choices=("meteo", "wayback", "google"))
        command.add_argument(
            "--url", action="append", help="Explicit report URL; repeatable"
        )
        command.add_argument(
            "--file", action="append", help="Local report PDF; repeatable"
        )
        if name == "ingest":
            command.add_argument("--download-only", action="store_true")
        else:
            command.add_argument("--no-charts", action="store_true")
    reprocess = commands.add_parser(
        "reprocess", help="Process archived reports without downloading"
    )
    reprocess.add_argument(
        "--failed", action="store_true", help="Only reports with failed/review attempts"
    )
    legacy = commands.add_parser(
        "import-legacy", help="Import an old JSON/PDF archive without changing it"
    )
    legacy.add_argument("--source", required=True)
    legacy.add_argument("--dry-run", action="store_true")
    export = commands.add_parser(
        "export", help="Generate a complete versioned report snapshot"
    )
    export.add_argument("--no-charts", action="store_true")
    backup = commands.add_parser(
        "backup", help="Back up the database and referenced raw files"
    )
    backup.add_argument("--destination")
    restore = commands.add_parser(
        "restore", help="Restore a verified backup into a new directory"
    )
    restore.add_argument("--source", required=True)
    restore.add_argument("--destination", required=True)
    accept = commands.add_parser(
        "accept", help="Explicitly accept validated correction candidates"
    )
    accept.add_argument("--attempt", required=True, type=int)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.from_env(data_dir=args.data_dir)
        logging.basicConfig(
            level=settings.log_level, format="%(levelname)s %(name)s: %(message)s"
        )
        if args.command == "status":
            output = status(settings)
        elif args.command == "restore":
            from weather_lk.services.backup import restore_backup

            output = {"restored_to": str(restore_backup(args.source, args.destination))}
        elif args.command == "import-legacy":
            from weather_lk.services.legacy_import import import_legacy

            output = import_legacy(settings, args.source, args.dry_run)
        elif args.command == "backup":
            from weather_lk.services.backup import create_backup

            output = {"backup": str(create_backup(settings, args.destination))}
        elif args.command == "export":
            from weather_lk.services.reporting import export_reports

            output = export_reports(settings, charts=not args.no_charts)
        else:
            from weather_lk.services.pipeline import Pipeline

            pipeline = Pipeline(settings)
            if args.command == "init":
                output = {"initialized": True, "data_dir": str(settings.data_dir)}
            elif args.command == "accept":
                pipeline.observations.accept(args.attempt)
                output = {"accepted_attempt": args.attempt}
            elif args.command == "reprocess":
                output = pipeline.reprocess(args.failed)
            else:
                output = pipeline.ingest(
                    args.url,
                    args.file,
                    args.source,
                    getattr(args, "download_only", False),
                )
                if args.command == "run":
                    from weather_lk.services.reporting import export_reports

                    output["export"] = export_reports(
                        settings, pipeline.database, charts=not args.no_charts
                    )
                    output["freshness"] = status(settings)
                    if output["freshness"]["stale"]:
                        output["status"] = "partial"
        print(json.dumps(output, indent=2, default=str, allow_nan=False))
        return 1 if output.get("status") == "partial" else 0
    except Exception as error:
        logging.getLogger(__name__).error("%s", error)
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 2
