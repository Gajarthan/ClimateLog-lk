"""Consistent database snapshots with verified immutable source bytes."""

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from weather_lk.storage.database import Database


def _copy_sources(database_path, source_root, destination_root):
    with closing(sqlite3.connect(database_path)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Backup database failed integrity validation")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Backup database has broken source references")
        rows = connection.execute("SELECT hash,raw_path FROM documents").fetchall()
    source_root = Path(source_root).resolve()
    destination_root = Path(destination_root).resolve()
    for digest, relative in rows:
        source = (source_root / relative).resolve()
        target = (destination_root / relative).resolve()
        if not source.is_relative_to(source_root) or not target.is_relative_to(
            destination_root
        ):
            raise ValueError("Backup contains an invalid source path")
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Original source checksum mismatch: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return len(rows)


def create_backup(settings, destination=None):
    if not settings.database_path.exists():
        raise ValueError("No initialized database to back up")
    identity = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    destination = Path(
        destination or settings.data_dir / "backups" / identity
    ).resolve()
    if destination.exists():
        raise FileExistsError("Backup destination already exists")
    staging = destination.with_name(destination.name + ".partial")
    staging.mkdir(parents=True)
    Database(settings.database_path).backup(staging / "weather.sqlite3")
    count = _copy_sources(staging / "weather.sqlite3", settings.data_dir, staging)
    (staging / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_documents": count,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    os.replace(staging, destination)
    return destination


def restore_backup(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("Restore requires a new destination directory")
    if not (source / "manifest.json").is_file():
        raise ValueError("Backup manifest is missing; refusing an incomplete backup")
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported backup schema")
    staging = destination.with_name(destination.name + ".partial")
    staging.mkdir(parents=True)
    shutil.copyfile(source / "weather.sqlite3", staging / "weather.sqlite3")
    count = _copy_sources(staging / "weather.sqlite3", source, staging)
    if count != manifest["source_documents"]:
        raise ValueError("Backup manifest source count mismatch")
    os.replace(staging, destination)
    return destination
