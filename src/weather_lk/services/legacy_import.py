"""Non-destructive, repeatable migration of the old JSON/PDF archive."""

import hashlib
import json
import shutil
import sqlite3
from contextlib import closing, contextmanager, nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory

from weather_lk.domain.models import Observation, ParseResult
from weather_lk.domain.validation import validate_result
from weather_lk.services.pipeline import Pipeline
from weather_lk.stations.catalog import StationCatalog

IMPORT_VERSION = "legacy-json-v1"


class _SnapshotChanged(RuntimeError):
    pass


def _file_fingerprint(path):
    try:
        before = path.stat()
    except FileNotFoundError:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    identity = lambda stat: (
        stat.st_dev,
        stat.st_ino,
        stat.st_size,
        stat.st_mtime_ns,
        stat.st_ctime_ns,
    )
    if identity(before) != identity(after):
        raise _SnapshotChanged("Database changed while reading")
    return identity(after), digest.hexdigest()


@contextmanager
def _database_snapshot(database_path):
    """Read a stable private copy, including committed pages still in the WAL.

    Even SQLite mode=ro can create or alter sidecars. Never open the destination
    with SQLite during a preview. The WAL index is rebuilt only in temporary
    storage; source bytes and metadata are checked around copying all files.
    """
    paths = {
        suffix: Path(str(database_path) + suffix) for suffix in ("", "-wal", "-journal")
    }
    for _ in range(3):
        with TemporaryDirectory(prefix="weather-preview-") as directory:
            snapshot = Path(directory) / "snapshot.sqlite3"
            try:
                before = {
                    suffix: _file_fingerprint(path) for suffix, path in paths.items()
                }
                if before[""] is None:
                    raise _SnapshotChanged("Database disappeared while reading")
                for suffix, fingerprint in before.items():
                    if fingerprint is not None:
                        shutil.copyfile(paths[suffix], Path(str(snapshot) + suffix))
                after = {
                    suffix: _file_fingerprint(path) for suffix, path in paths.items()
                }
                if before != after:
                    raise _SnapshotChanged("Database changed while copying")
                for suffix, fingerprint in before.items():
                    if (
                        fingerprint is not None
                        and _file_fingerprint(Path(str(snapshot) + suffix))[1]
                        != fingerprint[1]
                    ):
                        raise _SnapshotChanged("Database copy differs from source")
            except (FileNotFoundError, _SnapshotChanged):
                continue
            with closing(sqlite3.connect(snapshot)) as connection:
                connection.execute("PRAGMA query_only=ON")
                yield connection
            return
    raise RuntimeError(
        "Database changed during dry-run snapshot; retry when ingestion is idle"
    )


def import_legacy(settings, source, dry_run=False):
    source = Path(source).resolve()
    if not source.is_dir():
        raise ValueError("Legacy source must be an existing archive directory")
    if settings.data_dir.resolve().is_relative_to(source):
        raise ValueError("Migration destination must be outside the source archive")
    catalog = StationCatalog()
    pipeline = None if dry_run else Pipeline(settings)
    selected, completed = {}, set()
    if dry_run and settings.database_path.exists():
        with _database_snapshot(settings.database_path) as connection:
            for row in connection.execute(
                "SELECT o.station_id,o.observed_on,o.rain,o.min_temp,o.max_temp,o.trace_rain FROM current_observations c JOIN observations o ON o.id=c.observation_id"
            ):
                selected[row[:2]] = row[2:]
            completed = {
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT a.document_hash FROM parse_attempts a JOIN observations o ON o.attempt_id=a.id WHERE a.parser_version=? AND a.status IN ('succeeded','needs_review')",
                    (IMPORT_VERSION,),
                )
            }
    counts = dict(
        dry_run=dry_run,
        files=0,
        rows=0,
        accepted=0,
        duplicates=0,
        conflicts=0,
        rejected_files=0,
        rejected_rows=0,
        missing_pdf=0,
        pdfs=0,
        failed_placeholders=0,
        orphan_placeholders=0,
        errors=[],
    )
    pdf_by_name = {}
    pdf_documents = {}
    json_root = source / "json_parsed" if (source / "json_parsed").is_dir() else source
    manager = nullcontext(None) if dry_run else pipeline.run_context("legacy-import")
    with manager as run:
        for pdf in sorted(source.rglob("*.pdf")):
            if not pdf.resolve().is_relative_to(source):
                continue
            pdf_by_name.setdefault(pdf.name, []).append(pdf)
            counts["pdfs"] += 1
            try:
                content = pdf.read_bytes()
                if not content.startswith(b"%PDF-"):
                    raise ValueError("File is not a PDF")
                if pipeline:
                    pdf_documents[pdf.stem] = pipeline.documents.archive(
                        content, "pdf", "legacy:" + pdf.relative_to(source).as_posix()
                    )
            except (OSError, ValueError) as error:
                counts["errors"].append(f"{pdf.relative_to(source)}: {error}")
                if run is not None:
                    run["failed"] += 1
        for path in sorted(json_root.glob("*.json")):
            if not path.resolve().is_relative_to(source):
                continue
            counts["files"] += 1
            row_count = 0
            try:
                content = path.read_bytes()
                data = json.loads(content)
                weather = data["weather_list"]
                row_count = len(weather)
                counts["rows"] += row_count
                filename = (
                    str(data.get("pdf_path", "")).replace("\\", "/").rsplit("/", 1)[-1]
                )
                missing_pdf = len(pdf_by_name.get(filename, [])) != 1
                if missing_pdf:
                    counts["missing_pdf"] += 1
                observations = []
                for item in weather:
                    station = catalog.resolve(item["place"])
                    flags = (*station.pop("quality_flags"), "legacy_provenance")
                    if missing_pdf:
                        flags += ("missing_pdf",)
                    observations.append(
                        Observation(
                            **station,
                            date=data["date"],
                            rain=item.get("rain"),
                            min_temp=item.get("min_temp"),
                            max_temp=item.get("max_temp"),
                            trace_rain=bool(item.get("trace_rain", False)),
                            raw=dict(item),
                            quality_flags=flags,
                        )
                    )
                result = ParseResult(
                    data["date"],
                    tuple(observations),
                    (
                        "Imported original JSON; PDF extraction not independently verified",
                    ),
                )
                validate_result(result)
                if dry_run:
                    digest = hashlib.sha256(content).hexdigest()
                    if digest in completed:
                        counts["duplicates"] += row_count
                        continue
                    for item in observations:
                        key = (item.station_id, item.date)
                        values = (
                            item.rain,
                            item.min_temp,
                            item.max_temp,
                            item.trace_rain,
                        )
                        if key not in selected:
                            selected[key] = values
                            counts["accepted"] += 1
                        elif selected[key] == values:
                            counts["duplicates"] += 1
                        else:
                            counts["conflicts"] += 1
                    completed.add(digest)
                    continue
                document = pipeline.documents.archive(
                    content,
                    "legacy_json",
                    "legacy:" + path.relative_to(source).as_posix(),
                )
                outcome = pipeline.observations.save_result(
                    document["hash"], IMPORT_VERSION, result, run["run_id"]
                )
                counts["accepted"] += outcome["accepted"]
                counts["conflicts"] += outcome["conflicts"]
                counts["duplicates"] += (
                    row_count - outcome["accepted"] - outcome["conflicts"]
                )
                run[outcome["status"]] += 1
            except (ValueError, OSError, KeyError, TypeError) as error:
                counts["rejected_files"] += 1
                counts["rejected_rows"] += row_count
                counts["errors"].append(f"{path.relative_to(source)}: {error}")
                if run is not None:
                    run["failed"] += 1
        for path in sorted((source / "json_placeholder").glob("*.json")):
            if not path.resolve().is_relative_to(source):
                continue
            try:
                if json.loads(path.read_bytes()).get("date") != "unknown":
                    continue
                counts["failed_placeholders"] += 1
                document = pdf_documents.get(path.stem)
                if document and pipeline:
                    with pipeline.database.connect() as connection:
                        existing = connection.execute(
                            "SELECT id FROM parse_attempts WHERE document_hash=? AND parser_version='legacy-placeholder-v1'",
                            (document["hash"],),
                        ).fetchone()
                    if not existing:
                        attempt = pipeline.observations.start_attempt(
                            document["hash"], "legacy-placeholder-v1", run["run_id"]
                        )
                        pipeline.observations.fail_attempt(
                            attempt, "Imported failed legacy placeholder"
                        )
                elif path.stem not in {
                    p.stem for paths in pdf_by_name.values() for p in paths
                }:
                    counts["orphan_placeholders"] += 1
            except (ValueError, OSError) as error:
                counts["errors"].append(f"{path.relative_to(source)}: {error}")
    counts["status"] = (
        "partial" if counts["errors"] or counts["conflicts"] else "succeeded"
    )
    return counts
