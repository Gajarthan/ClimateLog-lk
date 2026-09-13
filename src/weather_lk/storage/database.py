"""Short SQLite transactions, run leases, and consistent backups."""

import json
import sqlite3
import time
import uuid
from contextlib import closing, contextmanager
from importlib.resources import files
from pathlib import Path


class Database:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise RuntimeError("Database schema is newer than this application")
            connection.execute("PRAGMA journal_mode=WAL")
            if version == 0:
                connection.executescript(
                    files("weather_lk.storage")
                    .joinpath("migrations/001_initial.sql")
                    .read_text()
                )

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def start_run(self, source, lease_seconds=60):
        now = time.time()
        run_id = uuid.uuid4().hex
        with self.transaction() as connection:
            active = connection.execute(
                "SELECT id FROM pipeline_runs WHERE status='running' AND lease_expires>?",
                (now,),
            ).fetchone()
            if active:
                raise RuntimeError("Another ingestion run is active")
            connection.execute(
                "UPDATE parse_attempts SET status='retryable_failure',error='Interrupted run',finished_at=? WHERE status='processing' AND run_id IN (SELECT id FROM pipeline_runs WHERE status='running' AND lease_expires<=?)",
                (now, now),
            )
            connection.execute(
                "UPDATE pipeline_runs SET status='abandoned',finished_at=? WHERE status='running' AND lease_expires<=?",
                (now, now),
            )
            connection.execute(
                "INSERT INTO pipeline_runs(id,source,started_at,status,lease_expires,heartbeat_at) VALUES(?,?,?,'running',?,?)",
                (run_id, source, now, now + lease_seconds, now),
            )
        return run_id

    def heartbeat(self, run_id, lease_seconds=60):
        now = time.time()
        with self.transaction() as connection:
            updated = connection.execute(
                "UPDATE pipeline_runs SET heartbeat_at=?,lease_expires=? WHERE id=? AND status='running' AND lease_expires>?",
                (now, now + lease_seconds, run_id, now),
            ).rowcount
            if not updated:
                raise RuntimeError("Ingestion lease was lost")

    def finish_run(self, run_id, status, counts):
        with self.transaction() as connection:
            connection.execute(
                "UPDATE parse_attempts SET status='retryable_failure',error='Interrupted run',finished_at=? WHERE run_id=? AND status='processing'",
                (time.time(), run_id),
            )
            connection.execute(
                "UPDATE pipeline_runs SET status=?,counts=?,finished_at=?,lease_expires=NULL WHERE id=? AND status='running'",
                (status, json.dumps(counts), time.time(), run_id),
            )

    def runs(self):
        with self.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 20"
                )
            ]

    def backup(self, destination):
        destination = Path(destination).resolve()
        if destination == self.path.resolve():
            raise ValueError("Backup destination must differ from the active database")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        with self.connect() as source:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target)
        return destination
