import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

import weather_lk.services.legacy_import as legacy_import

from weather_lk.config import Settings
from weather_lk.services.legacy_import import import_legacy
from weather_lk.storage.database import Database
from weather_lk.storage.observations import ObservationStore


def file_snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): (
            path.read_bytes(),
            path.stat().st_mtime_ns,
        )
        for path in directory.rglob("*")
        if path.is_file()
    }


def archive(tmp_path):
    source = tmp_path / "old"
    (source / "json_parsed").mkdir(parents=True)
    document = {
        "date": "2024-02-23",
        "weather_list": [
            {"place": "Colombo", "rain": 0, "min_temp": 20, "max_temp": 30},
            {"place": "Galle", "rain": None, "min_temp": 21, "max_temp": 31},
        ],
    }
    (source / "json_parsed" / "2024-02-23.json").write_text(json.dumps(document))
    return source


def test_dry_run_does_not_create_destination(tmp_path):
    source = archive(tmp_path)
    settings = Settings(tmp_path / "new")
    result = import_legacy(settings, source, dry_run=True)
    assert result["rows"] == 2
    assert result["missing_pdf"] == 1
    assert not settings.data_dir.exists()


def test_archive_import_is_idempotent_and_preserves_missing_provenance(tmp_path):
    source = archive(tmp_path)
    settings = Settings(tmp_path / "new")
    first = import_legacy(settings, source)
    second = import_legacy(settings, source)
    assert first["accepted"] == 2
    assert second["duplicates"] == 2
    rows = ObservationStore(Database(settings.database_path)).current()
    assert len(rows) == 2
    assert "missing_pdf" in rows[0]["quality_flags"]
    assert (settings.data_dir / rows[0]["raw_path"]).suffix == ".json"
    assert (source / "json_parsed" / "2024-02-23.json").exists()


def test_invalid_report_is_accounted_for_without_stopping_import(tmp_path):
    source = archive(tmp_path)
    (source / "json_parsed" / "bad.json").write_text("{broken")
    result = import_legacy(Settings(tmp_path / "new"), source)
    assert result["accepted"] == 2
    assert result["rejected_files"] == 1
    assert result["errors"]


def test_dry_run_reconciles_conflicting_rows_like_real_import(tmp_path):
    source = archive(tmp_path)
    first = source / "json_parsed" / "2024-02-23.json"
    revised = json.loads(first.read_text())
    revised["weather_list"][0]["rain"] = 99
    (source / "json_parsed" / "revision.json").write_text(json.dumps(revised))
    settings = Settings(tmp_path / "new")
    preview = import_legacy(settings, source, dry_run=True)
    actual = import_legacy(settings, source)
    for key in ("accepted", "duplicates", "conflicts", "status"):
        assert preview[key] == actual[key]


def test_dry_run_leaves_every_existing_destination_file_unchanged(tmp_path):
    source = archive(tmp_path)
    settings = Settings(tmp_path / "new")
    import_legacy(settings, source)
    before = file_snapshot(settings.data_dir)
    preview = import_legacy(settings, source, dry_run=True)
    assert file_snapshot(settings.data_dir) == before
    actual = import_legacy(settings, source)
    for key in ("accepted", "duplicates", "conflicts", "status"):
        assert preview[key] == actual[key]


def test_dry_run_reads_committed_active_wal_without_mutating_destination(tmp_path):
    source = archive(tmp_path)
    settings = Settings(tmp_path / "new")
    Database(settings.database_path)
    with closing(sqlite3.connect(settings.database_path)) as keeper:
        keeper.execute("PRAGMA wal_autocheckpoint=0")
        keeper.execute("SELECT COUNT(*) FROM current_observations").fetchone()
        import_legacy(settings, source)
        assert (
            settings.database_path.with_name("weather.sqlite3-wal").stat().st_size > 0
        )
        base_copy = tmp_path / "base_only.sqlite3"
        shutil.copyfile(settings.database_path, base_copy)
        with closing(sqlite3.connect(base_copy)) as base:
            assert (
                base.execute("SELECT COUNT(*) FROM current_observations").fetchone()[0]
                == 0
            )
        revised = source / "json_parsed" / "revision.json"
        data = json.loads((source / "json_parsed" / "2024-02-23.json").read_text())
        data["weather_list"][0]["rain"] = 99
        revised.write_text(json.dumps(data))
        before = file_snapshot(settings.data_dir)
        preview = import_legacy(settings, source, dry_run=True)
        assert file_snapshot(settings.data_dir) == before
        assert preview["accepted"] == 0
        assert preview["duplicates"] == 3
        assert preview["conflicts"] == 1
        actual = import_legacy(settings, source)
        for key in ("accepted", "duplicates", "conflicts", "status"):
            assert preview[key] == actual[key]


@pytest.mark.parametrize("keep_changing", [False, True])
def test_dry_run_retries_or_rejects_concurrent_database_changes(
    tmp_path, monkeypatch, keep_changing
):
    source = archive(tmp_path)
    settings = Settings(tmp_path / "new")
    import_legacy(settings, source)
    original_copy = shutil.copyfile
    copy_count = 0
    with closing(sqlite3.connect(settings.database_path)) as writer:
        writer.execute("CREATE TABLE concurrent_writer_probe (value INTEGER)")
        writer.commit()

        def copy_during_write(source_path, destination_path, *args, **kwargs):
            nonlocal copy_count
            result = original_copy(source_path, destination_path, *args, **kwargs)
            if Path(source_path) == settings.database_path:
                copy_count += 1
                if keep_changing or copy_count == 1:
                    writer.execute(
                        "INSERT INTO concurrent_writer_probe VALUES (?)", (copy_count,)
                    )
                    writer.commit()
            return result

        monkeypatch.setattr(legacy_import.shutil, "copyfile", copy_during_write)
        if keep_changing:
            with pytest.raises(RuntimeError, match="Database changed"):
                import_legacy(settings, source, dry_run=True)
            assert copy_count == 3
        else:
            preview = import_legacy(settings, source, dry_run=True)
            assert preview["duplicates"] == 2
            assert preview["accepted"] == 0
            assert copy_count == 2
