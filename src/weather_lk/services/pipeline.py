import hashlib
import logging
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from weather_lk.ingestion.download import fetch_pdf, validate_pdf
from weather_lk.parsing.meteo_pdf import PARSER_VERSION, parse_pdf
from weather_lk.storage.database import Database
from weather_lk.storage.documents import DocumentStore
from weather_lk.storage.observations import ObservationStore
from weather_lk.services.deadline import bounded_call

log = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        settings,
        parser=parse_pdf,
        parser_version=PARSER_VERSION,
        fetcher=fetch_pdf,
    ):
        self.settings = settings
        self.parser = parser
        self.parser_version = parser_version
        self.fetcher = fetcher
        self.database = Database(settings.database_path)
        self.documents = DocumentStore(self.database, settings.data_dir)
        self.observations = ObservationStore(self.database)

    @contextmanager
    def run_context(self, source, allow_pending=False):
        run_id = self.database.start_run(source)
        stop = threading.Event()
        lease_errors = []

        def heartbeat():
            while not stop.wait(10):
                try:
                    self.database.heartbeat(run_id)
                except Exception as error:
                    lease_errors.append(error)
                    return

        worker = threading.Thread(target=heartbeat, daemon=True)
        counts = dict(
            run_id=run_id,
            archived=0,
            succeeded=0,
            skipped=0,
            failed=0,
            needs_review=0,
            pending=0,
            errors=[],
        )
        worker.start()
        try:
            yield counts
            if lease_errors:
                raise RuntimeError("Ingestion lease was lost") from lease_errors[0]
        except BaseException:
            self.database.finish_run(run_id, "failed", counts)
            raise
        else:
            counts["status"] = (
                "partial"
                if (
                    counts["failed"]
                    or counts["needs_review"]
                    or (counts["pending"] and not allow_pending)
                )
                else "succeeded"
            )
            self.database.finish_run(run_id, counts["status"], counts)
        finally:
            stop.set()
            worker.join(timeout=15)

    def _failure(self, counts, error):
        counts["failed"] += 1
        counts["errors"].append(str(error))
        log.error("run=%s error=%s", counts["run_id"], error)

    def _process(self, counts, deadline, failed_only=False):
        pending = self.documents.pending(self.parser_version, failed_only)
        for index, document in enumerate(pending):
            if time.monotonic() >= deadline or (
                self.settings.max_reports is not None
                and index >= self.settings.max_reports
            ):
                break
            attempt = self.observations.start_attempt(
                document["hash"], self.parser_version, counts["run_id"]
            )
            try:
                path = self.documents.path(document)
                if hashlib.sha256(path.read_bytes()).hexdigest() != document["hash"]:
                    raise ValueError("Archived document checksum mismatch")
                parsed = bounded_call(
                    self.parser, (path,), deadline, isolated=self.parser is parse_pdf
                )
                if time.monotonic() >= deadline:
                    raise TimeoutError("Run deadline reached before storing results")
                outcome = self.observations.complete_attempt(attempt, parsed)
                counts[outcome["status"]] += 1
                log.info(
                    "run=%s document=%s status=%s rows=%s",
                    counts["run_id"],
                    document["hash"],
                    outcome["status"],
                    len(parsed.observations),
                )
            except Exception as error:
                self.observations.fail_attempt(
                    attempt, error, retryable=not isinstance(error, ValueError)
                )
                self._failure(counts, error)
        counts["pending"] = len(self.documents.pending(self.parser_version))

    def ingest(self, urls=None, paths=None, source=None, download_only=False):
        source = source or self.settings.source
        deadline = time.monotonic() + self.settings.run_timeout_seconds
        with self.run_context(source, allow_pending=download_only) as counts:
            if urls is None and paths is None:
                try:
                    if source == "meteo":
                        from weather_lk.ingestion.meteo import discover_meteo

                        urls = bounded_call(discover_meteo, (), deadline)
                    elif source == "wayback":
                        from weather_lk.ingestion.archives import discover_wayback

                        urls = bounded_call(discover_wayback, (), deadline)
                    elif source == "google":
                        from weather_lk.ingestion.archives import discover_google

                        urls = bounded_call(discover_google, (), deadline)
                    else:
                        raise ValueError(f"Unknown source: {source}")
                except Exception as error:
                    self._failure(counts, error)
            for location, is_url in [
                *((str(path), False) for path in paths or []),
                *((url, True) for url in urls or []),
            ]:
                if time.monotonic() >= deadline:
                    self._failure(
                        counts, TimeoutError("Run deadline reached during collection")
                    )
                    break
                try:
                    content = (
                        bounded_call(
                            self.fetcher,
                            (location, self.settings),
                            deadline,
                            isolated=self.fetcher is fetch_pdf,
                        )
                        if is_url
                        else Path(location).read_bytes()
                    )
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Run deadline reached during collection")
                    validate_pdf(content)
                    document = self.documents.archive(
                        content, "pdf", location if is_url else None
                    )
                    counts["archived"] += 1
                    if self.observations.has_result(
                        document["hash"], self.parser_version
                    ):
                        counts["skipped"] += 1
                except Exception as error:
                    self._failure(counts, error)
            if not download_only:
                self._process(counts, deadline)
            else:
                counts["pending"] = len(self.documents.pending(self.parser_version))
        return counts

    def reprocess(self, failed_only=False):
        with self.run_context("reprocess") as counts:
            self._process(
                counts,
                time.monotonic() + self.settings.run_timeout_seconds,
                failed_only,
            )
        return counts
