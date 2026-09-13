import pytest

from weather_lk.domain.models import Observation, ParseResult
from weather_lk.storage.database import Database
from weather_lk.storage.documents import DocumentStore
from weather_lk.storage.observations import ObservationStore


def setup_store(tmp_path):
    db = Database(tmp_path / "weather.sqlite3")
    documents = DocumentStore(db, tmp_path)
    store = ObservationStore(db)
    document = documents.archive(b"%PDF-test\n", "pdf", "https://example.invalid/a.pdf")
    result = ParseResult(
        "2024-02-23", (Observation("colombo", "Colombo", "2024-02-23", 0, 20, 30),)
    )
    return db, documents, store, document, result


def test_idempotent_ingestion_and_provenance(tmp_path):
    db, documents, store, doc, result = setup_store(tmp_path)
    store.save_result(doc["hash"], "test-v1", result)
    store.save_result(doc["hash"], "test-v1", result)
    rows = store.current()
    assert len(rows) == 1
    assert rows[0]["document_hash"] == doc["hash"]
    assert rows[0]["parser_version"] == "test-v1"
    with db.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
        )


def test_correction_retains_old_value_until_accepted(tmp_path):
    db, documents, store, doc, result = setup_store(tmp_path)
    store.save_result(doc["hash"], "v1", result)
    revised = documents.archive(b"%PDF-corrected\n", "pdf")
    correction = ParseResult(
        "2024-02-23", (Observation("colombo", "Colombo", "2024-02-23", 10, 20, 31),)
    )
    outcome = store.save_result(revised["hash"], "v1", correction)
    assert outcome["status"] == "needs_review"
    assert store.current()[0]["rain"] == 0
    store.accept(outcome["attempt_id"])
    assert store.current()[0]["rain"] == 10
    with db.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 2
        )


def test_invalid_result_never_partially_writes(tmp_path):
    db, documents, store, doc, result = setup_store(tmp_path)
    bad = ParseResult(
        "2024-02-23",
        (*result.observations, Observation("bad", "Bad", "2024-02-23", -10)),
    )
    with pytest.raises(ValueError):
        store.save_result(doc["hash"], "v1", bad)
    assert store.current() == []


def test_duplicate_urls_share_original_bytes(tmp_path):
    db, documents, store, doc, result = setup_store(tmp_path)
    duplicate = documents.archive(
        b"%PDF-test\n", "pdf", "https://example.invalid/b.pdf"
    )
    assert duplicate["hash"] == doc["hash"]
    assert len(duplicate["sources"]) == 2
    assert (tmp_path / duplicate["raw_path"]).read_bytes() == b"%PDF-test\n"


def test_run_lease_blocks_second_writer_and_recovers_expired_run(tmp_path):
    db, documents, store, doc, result = setup_store(tmp_path)
    first = db.start_run("test", lease_seconds=30)
    with pytest.raises(RuntimeError, match="active"):
        db.start_run("test")
    with db.transaction() as connection:
        connection.execute(
            "UPDATE pipeline_runs SET lease_expires=0 WHERE id=?", (first,)
        )
    second = db.start_run("test")
    assert second != first
    db.finish_run(second, "succeeded", {})


def test_database_backup_is_readable(tmp_path):
    db, documents, store, doc, result = setup_store(tmp_path)
    store.save_result(doc["hash"], "v1", result)
    target = tmp_path / "backup.sqlite3"
    db.backup(target)
    restored = ObservationStore(Database(target))
    assert restored.current() == store.current()
