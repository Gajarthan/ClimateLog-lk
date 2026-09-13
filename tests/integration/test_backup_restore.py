from weather_lk.config import Settings
from weather_lk.domain.models import Observation, ParseResult
from weather_lk.services.backup import create_backup, restore_backup
from weather_lk.storage.database import Database
from weather_lk.storage.documents import DocumentStore
from weather_lk.storage.observations import ObservationStore


def test_backup_restore_includes_original_sources(tmp_path):
    settings = Settings(tmp_path / "active")
    db = Database(settings.database_path)
    doc = DocumentStore(db, settings.data_dir).archive(b"%PDF-test", "pdf")
    store = ObservationStore(db)
    store.save_result(
        doc["hash"],
        "test",
        ParseResult(
            "2024-02-23", (Observation("colombo", "Colombo", "2024-02-23", 0),)
        ),
    )
    backup = create_backup(settings)
    restored = tmp_path / "restored"
    restore_backup(backup, restored)
    assert (
        ObservationStore(Database(restored / "weather.sqlite3")).current()
        == store.current()
    )
    assert (restored / doc["raw_path"]).read_bytes() == b"%PDF-test"
