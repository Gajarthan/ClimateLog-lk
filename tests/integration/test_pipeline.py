import time

import pytest

from weather_lk.config import Settings
from weather_lk.domain.models import Observation, ParseResult
from weather_lk.services.pipeline import Pipeline
from weather_lk.storage.observations import ObservationStore


def result():
    return ParseResult(
        "2024-02-23", (Observation("colombo", "Colombo", "2024-02-23", 0, 20, 30),)
    )


def test_failure_is_retryable_and_duplicate_ingestion_is_a_noop(tmp_path):
    settings = Settings(tmp_path / "data")
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-test")
    calls = []

    def parser(path):
        calls.append(path)
        if len(calls) == 1:
            raise OSError("Temporary read failure")
        return result()

    pipeline = Pipeline(settings, parser=parser, parser_version="test-v1")
    first = pipeline.ingest(paths=[pdf])
    assert first["failed"] == 1
    second = pipeline.reprocess(failed_only=True)
    assert second["succeeded"] == 1
    assert pipeline.ingest(paths=[pdf])["skipped"] == 1
    assert len(ObservationStore(pipeline.database).current()) == 1


def test_non_pdf_download_is_rejected_before_parsing(tmp_path):
    pipeline = Pipeline(
        Settings(tmp_path / "data"),
        parser=lambda path: pytest.fail("Unexpected parse"),
        fetcher=lambda url, settings: b"<html>Error</html>",
    )
    outcome = pipeline.ingest(urls=["https://example.invalid/report.pdf"])
    assert outcome["failed"] == 1
    assert ObservationStore(pipeline.database).current() == []


def test_run_limit_leaves_pending_reports(tmp_path):
    settings = Settings(tmp_path / "data", max_reports=1)
    pdfs = [tmp_path / f"{i}.pdf" for i in range(2)]
    for i, path in enumerate(pdfs):
        path.write_bytes(f"%PDF-{i}".encode())
    pipeline = Pipeline(settings, parser=lambda path: result(), parser_version="test")
    outcome = pipeline.ingest(paths=pdfs)
    assert outcome["succeeded"] == 1
    assert outcome["pending"] == 1
    assert outcome["status"] == "partial"


def test_parse_validation_failure_keeps_diagnostics(tmp_path):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-test")
    invalid = ParseResult("bad-date", ())
    pipeline = Pipeline(
        Settings(tmp_path / "data"), parser=lambda path: invalid, parser_version="bad"
    )
    assert pipeline.ingest(paths=[pdf])["failed"] == 1
    attempt = ObservationStore(pipeline.database).attempts()[0]
    assert attempt["status"] == "needs_review"
    assert attempt["error"]


def test_reprocessing_rejects_modified_raw_bytes(tmp_path):
    pipeline = Pipeline(
        Settings(tmp_path / "data"), parser=lambda path: result(), parser_version="test"
    )
    document = pipeline.documents.archive(b"%PDF-original", "pdf")
    pipeline.documents.path(document).write_bytes(b"%PDF-changed")
    outcome = pipeline.reprocess()
    assert outcome["failed"] == 1
    assert not pipeline.observations.current()


def test_interrupted_attempt_is_recoverable(tmp_path):
    def interrupted(path):
        raise KeyboardInterrupt()

    pipeline = Pipeline(
        Settings(tmp_path / "data"), parser=interrupted, parser_version="test"
    )
    pipeline.documents.archive(b"%PDF-test", "pdf")
    with pytest.raises(KeyboardInterrupt):
        pipeline.reprocess()
    assert pipeline.documents.pending("test", failed_only=True)


def test_deadline_prevents_late_results_from_being_committed(tmp_path):
    def slow(path):
        time.sleep(0.15)
        return result()

    pipeline = Pipeline(
        Settings(tmp_path / "data", run_timeout_seconds=0.04),
        parser=slow,
        parser_version="test",
    )
    pipeline.documents.archive(b"%PDF-test", "pdf")
    outcome = pipeline.reprocess()
    assert outcome["status"] == "partial"
    assert not pipeline.observations.current()
