"""Observation versions are immutable; accepted selections can be changed explicitly."""

import json
import time

from weather_lk.domain.validation import validate_result


class ObservationStore:
    def __init__(self, database):
        self.database = database

    def has_result(self, digest, version):
        with self.database.connect() as connection:
            return (
                connection.execute(
                    "SELECT id FROM parse_attempts WHERE document_hash=? AND parser_version=? AND status IN ('succeeded','needs_review') AND EXISTS (SELECT 1 FROM observations o WHERE o.attempt_id=parse_attempts.id) LIMIT 1",
                    (digest, version),
                ).fetchone()
                is not None
            )

    def start_attempt(self, digest, version, run_id=None):
        with self.database.transaction() as connection:
            return connection.execute(
                "INSERT INTO parse_attempts(document_hash,parser_version,run_id,status,started_at) VALUES(?,?,?,'processing',?)",
                (digest, version, run_id, time.time()),
            ).lastrowid

    def fail_attempt(self, attempt_id, error, retryable=True):
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE parse_attempts SET status=?,error=?,finished_at=? WHERE id=? AND status='processing'",
                (
                    "retryable_failure" if retryable else "needs_review",
                    str(error),
                    time.time(),
                    attempt_id,
                ),
            )

    def save_result(self, digest, version, result, run_id=None):
        if self.has_result(digest, version):
            return {"status": "skipped", "accepted": 0, "conflicts": 0}
        validate_result(result)
        attempt = self.start_attempt(digest, version, run_id)
        try:
            return self.complete_attempt(attempt, result)
        except Exception as error:
            self.fail_attempt(attempt, error)
            raise

    def complete_attempt(self, attempt_id, result):
        validate_result(result)
        accepted = conflicts = 0
        with self.database.transaction() as connection:
            attempt = connection.execute(
                "SELECT * FROM parse_attempts WHERE id=?", (attempt_id,)
            ).fetchone()
            if attempt is None or attempt["status"] != "processing":
                raise RuntimeError("Attempt is not processing")
            if attempt["run_id"]:
                owner = connection.execute(
                    "SELECT id FROM pipeline_runs WHERE id=? AND status='running' AND lease_expires>?",
                    (attempt["run_id"], time.time()),
                ).fetchone()
                if owner is None:
                    raise RuntimeError("Ingestion lease was lost")
            # Recheck inside the write transaction to avoid duplicate concurrent completions.
            done = connection.execute(
                "SELECT id FROM parse_attempts WHERE document_hash=? AND parser_version=? AND status IN ('succeeded','needs_review') AND EXISTS (SELECT 1 FROM observations o WHERE o.attempt_id=parse_attempts.id) AND id<>?",
                (attempt["document_hash"], attempt["parser_version"], attempt_id),
            ).fetchone()
            if done:
                connection.execute(
                    "UPDATE parse_attempts SET status='skipped',finished_at=? WHERE id=?",
                    (time.time(), attempt_id),
                )
                return {
                    "status": "skipped",
                    "accepted": 0,
                    "conflicts": 0,
                    "attempt_id": attempt_id,
                }
            for observation in result.observations:
                connection.execute(
                    "INSERT INTO stations(id,name,lat,lng) VALUES(?,?,?,?) ON CONFLICT(id) DO NOTHING",
                    (
                        observation.station_id,
                        observation.place,
                        observation.lat,
                        observation.lng,
                    ),
                )
                source_name = observation.raw.get("place", observation.place)
                if isinstance(source_name, str):
                    connection.execute(
                        "INSERT OR IGNORE INTO station_aliases(source,alias,station_id) VALUES('report',?,?)",
                        (source_name, observation.station_id),
                    )
                current = connection.execute(
                    "SELECT o.* FROM current_observations c JOIN observations o ON o.id=c.observation_id WHERE c.station_id=? AND c.observed_on=?",
                    (observation.station_id, observation.date),
                ).fetchone()
                values = (
                    observation.rain,
                    observation.min_temp,
                    observation.max_temp,
                    int(observation.trace_rain),
                )
                row_id = connection.execute(
                    "INSERT INTO observations(attempt_id,station_id,observed_on,rain,min_temp,max_temp,lat,lng,trace_rain,raw,quality_flags) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        attempt_id,
                        observation.station_id,
                        observation.date,
                        *values[:3],
                        observation.lat,
                        observation.lng,
                        values[3],
                        json.dumps(observation.raw),
                        json.dumps(observation.quality_flags),
                    ),
                ).lastrowid
                if current is None:
                    connection.execute(
                        "INSERT INTO current_observations(station_id,observed_on,observation_id) VALUES(?,?,?)",
                        (observation.station_id, observation.date, row_id),
                    )
                    accepted += 1
                elif (
                    tuple(
                        current[name]
                        for name in ("rain", "min_temp", "max_temp", "trace_rain")
                    )
                    != values
                ):
                    conflicts += 1
            status = "needs_review" if conflicts else "succeeded"
            connection.execute(
                "UPDATE documents SET report_date=? WHERE hash=?",
                (result.report_date, attempt["document_hash"]),
            )
            connection.execute(
                "UPDATE parse_attempts SET status=?,finished_at=?,diagnostics=? WHERE id=?",
                (status, time.time(), json.dumps(result.diagnostics), attempt_id),
            )
        return {
            "status": status,
            "accepted": accepted,
            "conflicts": conflicts,
            "attempt_id": attempt_id,
        }

    def current(self, start=None, end=None):
        query = "SELECT o.*,s.name AS place,a.document_hash,a.parser_version,d.sources,d.raw_path FROM current_observations c JOIN observations o ON o.id=c.observation_id JOIN stations s ON s.id=o.station_id JOIN parse_attempts a ON a.id=o.attempt_id JOIN documents d ON d.hash=a.document_hash WHERE 1=1"
        values = []
        for operator, value in [(">=", start), ("<=", end)]:
            if value:
                query += f" AND o.observed_on{operator}?"
                values.append(value)
        with self.database.connect() as connection:
            rows = connection.execute(
                query + " ORDER BY o.observed_on,o.station_id", values
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["date"] = item.pop("observed_on")
            item["trace_rain"] = bool(item["trace_rain"])
            for key in ("raw", "quality_flags", "sources"):
                item[key] = json.loads(item[key])
            result.append(item)
        return result

    def attempts(self):
        with self.database.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM parse_attempts ORDER BY id DESC LIMIT 100"
                )
            ]

    def accept(self, attempt_id):
        with self.database.transaction() as connection:
            attempt = connection.execute(
                "SELECT id FROM parse_attempts WHERE id=? AND status IN ('succeeded','needs_review')",
                (attempt_id,),
            ).fetchone()
            rows = connection.execute(
                "SELECT * FROM observations WHERE attempt_id=?", (attempt_id,)
            ).fetchall()
            if not attempt or not rows:
                raise ValueError("Attempt has no validated observations to accept")
            for row in rows:
                connection.execute(
                    "INSERT INTO current_observations(station_id,observed_on,observation_id) VALUES(?,?,?) ON CONFLICT(station_id,observed_on) DO UPDATE SET observation_id=excluded.observation_id",
                    (row["station_id"], row["observed_on"], row["id"]),
                )
            connection.execute(
                "UPDATE parse_attempts SET status='succeeded' WHERE id=?", (attempt_id,)
            )
