# Sri Lanka Weather

A local data collection and reporting pipeline. Original reports are archived by
SHA-256; SQLite records processing attempts, observation versions, and explicitly
selected corrections. JSON, TSV, charts, and Markdown reports are produced from
one consistent observation snapshot.

## Install

Python 3.11 is the tested baseline. From this directory:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pytest -q
```

On Linux use `.venv/bin/python` in place of `.venv/Scripts/python.exe`.
`requirements.lock` pins the runtime and offline test dependencies tested on
Windows. The CI matrix also defines Linux validation; it has not been run here.
An installed package works outside the source directory without `PYTHONPATH`.

The core package uses only the standard library. For a minimal installation use
`python -m pip install .`; add `.[pdf]` for PDFs, `.[charts]` for charts, and
`.[browser]` for official-site discovery. The pinned setup above includes all
three and pytest. Discovery needs Firefox and an available geckodriver; Selenium
may download a driver on its first run. Camelot uses its bundled PDFium backend.
Optional historical Google discovery uses `.[archives]`. Old geocoding maintenance
scripts use `.[maintenance]` and `GMAPS_API_KEY`.

## Run

After activating the virtual environment, use:

```powershell
python -m weather_lk init
python -m weather_lk ingest --file tests/data/20240222.pdf
python -m weather_lk export
python -m weather_lk status
python -m weather_lk run
```

`run` discovers the official report, downloads, parses, and exports in order.
`ingest --url URL` accepts an explicit report URL; repeat `--file` or `--url` to
process multiple reports. `--download-only` archives PDFs for later processing.
Use `export --no-charts` or `run --no-charts` when charts are unnecessary.
Historical discovery is explicit: `ingest --source wayback` or `--source google`.

The default data root is `var/weather_lk` under the current working directory.
For repeatable operation, set `WEATHER_DATA_DIR` to an absolute directory on
persistent local disk, or pass `--data-dir PATH` **before** the command:

```powershell
python -m weather_lk --data-dir D:/weather-data run
```

The manual wrapper uses the project-local data root unless configured:

```powershell
.\workflows\_pipeline_manual.ps1 -DataDirectory D:/weather-data
```

Command results are JSON on stdout; diagnostic logs go to stderr. Exit codes:
`0` completed, `1` partial success/review needed or stale data after `run`,
`2` fatal error. `status` is a readout, so inspect its `stale` field when monitoring.
A successful offline ingest of an old report does not mean the data is fresh.
The ingestion run history records collection/parse outcomes; the `run` response
also includes export and freshness results. Export failures return exit code 2.

## Storage and corrections

```text
weather.sqlite3           observations, attempts, leases, and source metadata
raw/<hash-prefix>/       original PDF or legacy JSON bytes
exports/<export-id>/     complete reports and per-station files
exports/current.json     manifest pointing to the last completed export
backups/<backup-id>/     database snapshot, referenced sources, backup manifest
```

Raw files are checked against their hashes before parsing and during backup or
restore. Never edit them in place. Repeated successful processing of the same
bytes with the same parser version is a no-op. Failed attempts remain visible:

```powershell
python -m weather_lk reprocess --failed
python -m weather_lk status
python -m weather_lk accept --attempt 12
python -m weather_lk export
```

The attempt number is an example: inspect candidates before accepting one.
Different values for an existing station/date are preserved for review and do
not automatically replace selected values. `accept` selects all validated rows
from that attempt. A single ingestion lease prevents concurrent collection;
expired leases and interrupted attempts recover on later runs. Production
collection/parsing workers have a deadline and their process trees are terminated
on timeout. Cleanup can take a short grace period after the deadline. Export
rendering runs after ingestion and is bounded by the scheduler's execution limit.

## Import an existing archive

Keep the old archive and use a separate destination directory:

```powershell
python -m weather_lk --data-dir D:/weather-new import-legacy --source D:/weather-old --dry-run
python -m weather_lk --data-dir D:/weather-new import-legacy --source D:/weather-old
```

The preview reports accepted, duplicate, conflicting, rejected, and missing-PDF
counts without changing either archive. Against an existing database it reads a
verified temporary snapshot, including committed WAL data, and retries or fails
if the source changes during copying. The import preserves original JSON bytes,
flags unverified legacy provenance and missing PDFs, and is repeatable. Unknown
legacy placeholders become retryable attempts when their PDFs are available.
Source archives are never deleted. A production archive has not been supplied,
so production migration and multi-day comparison remain deployment tasks.

## Reports and interpretation

Readers should resolve `exports/current.json` once, then use its `export_dir` for
all files. The manifest lists file sizes, SHA-256 hashes, record counts, freshness,
and per-station filenames. A failed generation leaves the previous manifest
intact; an unreferenced partial directory may remain for inspection.

Legacy daily/flat JSON fields and `coverage.tsv` are retained. Additive fields
include station IDs, source paths, document hashes, parser versions, trace rain,
and quality flags. Generic `source_paths` can contain JSON; `pdf_paths` contains
PDFs only. Source paths are relative to the data root. Per-station filenames use
safe stable slugs listed in the manifest. New `summary.json`, `summary.md`, and
`station_coverage.tsv` expose sample counts and calendar coverage.

Intentional numeric corrections: each measure uses its own valid sample count;
missing values remain null, zero is valid, trace rain is explicit, and paired
temperatures require both minimum and maximum. Date windows use calendar days.
Rain totals sum station measurements and are not regional rainfall totals.
Coverage assumes the stations in the snapshot; station operating periods are
unknown. Reports use the printed date for the period ending at 08:30 Sri Lanka
time. Unverified historical station coordinates are flagged; ambiguous or missing
coordinates remain null. Unsupported layouts fail visibly for review.

To publish, copy a completed export plus its referenced raw files while preserving
the data-root layout, then update the remote current manifest last. Set
`WEATHER_PUBLIC_DATA_URL` to that data root's public URL before exporting.
Publication credentials and upload transport belong to deployment configuration.
The pipeline does not clone a data branch or push generated data.

## Backup and operation

```powershell
python -m weather_lk backup --destination D:/weather-backups/snapshot-001
python -m weather_lk restore --source D:/weather-backups/snapshot-001 --destination D:/weather-restored
python -m weather_lk --data-dir D:/weather-restored export
```

Backup uses SQLite's consistent backup API and copies every referenced raw source.
Restore verifies database integrity, foreign keys, and source checksums, and
requires a new destination. Exports are regenerated after restoring. Keep an
off-host backup copy and choose retention before enabling regular collection;
there is no automatic pruning. Do not put an active WAL database on a shared
network filesystem.

No scheduler has been registered. To register a daily Windows task explicitly,
after confirming report availability and backup arrangements:

```powershell
.\workflows\register_schedule.ps1 -DataDirectory D:/weather-data -At '10:00'
```

The time is an example, not a verified publication schedule. This registers for
the current interactive account; unattended operation requires host-specific task
credentials/configuration. The script does not overwrite an existing task.
Configure a separate backup task and monitor nonzero exit codes and freshness.
On Linux, use the same installed CLI with a systemd timer and absolute data path.

The six independent CI schedules have been replaced by offline CI and one manual
pipeline workflow. The latter requires a self-hosted runner labelled
`weather-pipeline`, Firefox, and an absolute `WEATHER_DATA_DIR` repository variable
outside its checkout. It makes a local backup after the run. No workflow has been
run or deployed from this checkout. Select one production scheduler.

| Setting | Default / purpose |
| --- | --- |
| `WEATHER_DATA_DIR` | Current-directory `var/weather_lk`; set an absolute durable path for jobs |
| `WEATHER_SOURCE` | `meteo` |
| `WEATHER_RUN_TIMEOUT_SECONDS` | `600`, ingestion deadline |
| `WEATHER_MAX_REPORTS` | Unlimited, subject to deadline; optional processing limit |
| `WEATHER_DOWNLOAD_TIMEOUT_SECONDS` | `60` per request |
| `WEATHER_DOWNLOAD_RETRIES` | `3` total attempts with bounded backoff |
| `WEATHER_STALE_HOURS` | `48` since the latest report period ending |
| `WEATHER_LOG_LEVEL` | `INFO` |
| `WEATHER_PUBLIC_DATA_URL` | Relative local links |

Verification: 95 offline tests pass on Windows, including both bundled PDFs,
interrupted processing, descendant cleanup, migration previews, and backup restore.
The fixture CLI run produced 120 observations and 149 verified export files.
Wheel imports and packaged resources were checked outside the source directory.
Normal tests are offline, including both bundled PDFs. Live discovery is opt-in:
`python -m pytest -m live`. A bounded live run on 2026-09-13 successfully discovered, downloaded, parsed,
and exported the 2026-09-12 official report: 60 observations, within the freshness
threshold. Linux CI and sustained production freshness remain deployment checks. Older internal parser/summary classes
remain for migration compatibility; supported workflow scripts delegate to the
new CLI. Do not use the old internal classes for production processing.

See the [architecture and migration plan](docs/superpowers/plans/2026-09-12-weather-architecture.md)
and [LICENSE](LICENSE).
