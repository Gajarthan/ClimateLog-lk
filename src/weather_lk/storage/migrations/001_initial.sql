BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS stations (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, lat REAL, lng REAL
);
CREATE TABLE IF NOT EXISTS station_aliases (
    source TEXT NOT NULL, alias TEXT NOT NULL, station_id TEXT NOT NULL REFERENCES stations(id),
    PRIMARY KEY(source, alias)
);
CREATE TABLE IF NOT EXISTS documents (
    hash TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('pdf','legacy_json')),
    raw_path TEXT NOT NULL UNIQUE, sources TEXT NOT NULL, fetched_at REAL NOT NULL,
    report_date TEXT
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id TEXT PRIMARY KEY, source TEXT NOT NULL, started_at REAL NOT NULL, finished_at REAL,
    status TEXT NOT NULL, lease_expires REAL, heartbeat_at REAL, counts TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS parse_attempts (
    id INTEGER PRIMARY KEY, document_hash TEXT NOT NULL REFERENCES documents(hash),
    parser_version TEXT NOT NULL, run_id TEXT REFERENCES pipeline_runs(id), status TEXT NOT NULL,
    started_at REAL NOT NULL, finished_at REAL, error TEXT, diagnostics TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS attempts_document ON parse_attempts(document_hash, parser_version, status);
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY, attempt_id INTEGER NOT NULL REFERENCES parse_attempts(id),
    station_id TEXT NOT NULL REFERENCES stations(id), observed_on TEXT NOT NULL,
    rain REAL CHECK(rain >= 0), min_temp REAL, max_temp REAL, lat REAL, lng REAL,
    trace_rain INTEGER NOT NULL DEFAULT 0, raw TEXT NOT NULL, quality_flags TEXT NOT NULL,
    CHECK(min_temp IS NULL OR max_temp IS NULL OR min_temp <= max_temp),
    UNIQUE(attempt_id, station_id, observed_on), UNIQUE(id, station_id, observed_on)
);
CREATE TABLE IF NOT EXISTS current_observations (
    station_id TEXT NOT NULL, observed_on TEXT NOT NULL, observation_id INTEGER NOT NULL,
    PRIMARY KEY(station_id, observed_on),
    FOREIGN KEY(observation_id, station_id, observed_on) REFERENCES observations(id, station_id, observed_on)
);
CREATE INDEX IF NOT EXISTS observations_date ON current_observations(observed_on, station_id);
PRAGMA user_version=1;
COMMIT;
