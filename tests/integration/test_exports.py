import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from weather_lk.domain.models import Observation, ParseResult
from weather_lk.services import reporting
from weather_lk.storage.database import Database
from weather_lk.storage.documents import DocumentStore
from weather_lk.storage.observations import ObservationStore


@pytest.fixture
def source(tmp_path):
    settings = SimpleNamespace(
        data_dir=tmp_path,
        database_path=tmp_path / "weather.db",
        public_data_url="https://example.test/data",
        stale_hours=48,
    )
    database = Database(settings.database_path)
    document = DocumentStore(database, tmp_path).archive(
        b"original source", source_url="https://example.test/report.pdf"
    )
    observation = Observation(
        "station-a",
        "Station A",
        "2024-01-01",
        rain=0,
        trace_rain=True,
        raw={"rain": "Trace"},
    )
    ObservationStore(database).save_result(
        document["hash"], "test-v1", ParseResult("2024-01-01", (observation,))
    )
    return settings, database, document


def test_exports_legacy_shapes_sources_and_versioned_links(source):
    settings, database, document = source
    result = reporting.export_reports(settings, database, charts=False)
    output = Path(result["export_dir"])
    required = {
        "list_all.json",
        "idx_by_place.json",
        "idx_by_date.json",
        "date_list.json",
        "latest_flat.json",
        "latest_places.json",
        "flat.json",
        "flat_places.json",
        "alert_data.json",
        "coverage.tsv",
        "README.md",
        "summary.json",
        "summary.md",
    }
    assert required <= {p.name for p in output.iterdir()}
    daily = json.loads((output / "list_all.json").read_text())[0]
    assert daily["date_ut"] == 1704047400
    assert daily["pdf_path"] == document["raw_path"]
    assert daily["pdf_paths"] == [document["raw_path"]]
    assert daily["max_rain"] == {"max_rain": 0, "max_rain_place": "Station A"}
    assert daily["min_temp"] == {"min_temp": None, "min_temp_place": None}
    assert daily["max_temp"] == {"max_temp": None, "max_temp_place": None}
    weather = daily["weather_list"][0]
    assert weather["raw_path"] == document["raw_path"]
    assert weather["sources"] == ["https://example.test/report.pdf"]
    assert weather["parser_version"] == "test-v1"
    assert weather["min_temp"] is None and weather["lat"] is None
    assert json.loads((output / "flat.json").read_text())[0]["temp_min_c"] is None
    assert json.loads((output / "flat_places.json").read_text())[0]["lat_lng"] == [
        None,
        None,
    ]
    manifest = json.loads((settings.data_dir / "exports/current.json").read_text())
    assert manifest == result["manifest"]
    assert manifest["export_dir"] == output.name
    assert manifest["records"] == 1
    assert (output / manifest["stations"]["station-a"]["json"]).exists()
    assert (output / manifest["stations"]["station-a"]["tsv"]).exists()
    alert = json.loads((output / "alert_data.json").read_text())
    assert (
        alert["url_structured"]
        == f"https://example.test/data/exports/{output.name}/flat.json"
    )
    assert list(alert["event_data"]["Station A"]) == ["20240101"]
    with (output / "coverage.tsv").open() as stream:
        coverage = list(csv.DictReader(stream, delimiter="\t"))
    assert coverage == [
        dict(date="2024-01-01", has_data="True", n="1", n_temp="0", n_rain="1")
    ]
    assert (output / "station_coverage.tsv").exists()


def test_failed_render_keeps_previous_manifest(source, monkeypatch):
    settings, database, _ = source
    reporting.export_reports(settings, database, charts=False)
    before = (settings.data_dir / "exports/current.json").read_bytes()

    def fail(*args, **kwargs):
        raise RuntimeError("render failed")

    monkeypatch.setattr(reporting, "render_charts", fail)
    with pytest.raises(RuntimeError, match="render failed"):
        reporting.export_reports(settings, database)
    assert (settings.data_dir / "exports/current.json").read_bytes() == before


def test_empty_database_exports_explicit_empty_data(tmp_path):
    settings = SimpleNamespace(data_dir=tmp_path, database_path=tmp_path / "empty.db")
    result = reporting.export_reports(settings)
    output = Path(result["export_dir"])
    assert result["records"] == 0
    assert json.loads((output / "latest_flat.json").read_text()) == []
    assert json.loads((output / "date_list.json").read_text()) == []
    assert "No observations" in (output / "README.md").read_text()
    assert (
        json.loads((output / "alert_data.json").read_text())["url_structured"]
        == "./flat.json"
    )


def test_freshness_uses_report_period_ending_at_0830(source, monkeypatch):
    from datetime import datetime, timezone

    settings, database, _ = source
    settings.stale_hours = 24

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2024, 1, 2, 2, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(reporting, "datetime", Clock)
    result = reporting.export_reports(settings, database, charts=False)
    assert result["manifest"]["stale"] is False


def test_chart_outputs_and_no_leaked_figures(source):
    import matplotlib.pyplot as plt

    settings, database, _ = source
    before = plt.get_fignums()
    result = reporting.export_reports(settings, database)
    output = Path(result["export_dir"])
    assert (output / "charts/temperature.png").stat().st_size > 1000
    assert (output / "charts/rainfall.png").stat().st_size > 1000
    assert plt.get_fignums() == before


def test_figure_is_closed_when_saving_fails(source, monkeypatch):
    from matplotlib.figure import Figure
    from matplotlib import pyplot as plt
    from weather_lk.exports.charts import render_charts

    settings, database, _ = source
    before = plt.get_fignums()
    closed = []
    original_close = plt.close

    def track_close(figure):
        closed.append(figure)
        original_close(figure)

    def fail(*args, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(plt, "close", track_close)
    monkeypatch.setattr(Figure, "savefig", fail)
    with pytest.raises(OSError, match="disk unavailable"):
        render_charts(
            ObservationStore(database).current(), settings.data_dir / "failed-charts"
        )
    assert len(closed) == 1
    assert plt.get_fignums() == before


def test_recent_window_is_thirty_calendar_days(source):
    settings, database, _ = source
    result = reporting.export_reports(settings, database, charts=False)
    summary = json.loads((Path(result["export_dir"]) / "summary.json").read_text())
    recent = summary["last_30_calendar_days"]
    assert recent["start"] == "2023-12-03"
    assert recent["statistics"]["coverage"]["calendar_days"] == 30


def test_unsafe_station_id_is_safely_encoded(source):
    settings, database, document = source
    observation = Observation("../escape", "Unsafe Station", "2024-01-02")
    ObservationStore(database).save_result(
        document["hash"], "test-v2", ParseResult("2024-01-02", (observation,))
    )
    result = reporting.export_reports(settings, database, charts=False)
    output = Path(result["export_dir"])
    for item in result["manifest"]["stations"].values():
        assert (output / item["json"]).resolve().is_relative_to(output.resolve())
        assert (output / item["json"]).exists()


@pytest.mark.parametrize("include_pdf", [False, True])
def test_legacy_json_sources_are_not_advertised_as_pdfs(tmp_path, include_pdf):
    settings = SimpleNamespace(data_dir=tmp_path, database_path=tmp_path / "weather.db")
    database = Database(settings.database_path)
    documents = DocumentStore(database, tmp_path)
    legacy = documents.archive(b'{"date":"2024-01-01"}', kind="legacy_json")
    observation = Observation(
        "legacy-station",
        "Legacy Station",
        "2024-01-01",
        rain=1,
        quality_flags=("missing_pdf",),
    )
    store = ObservationStore(database)
    store.save_result(
        legacy["hash"], "legacy-v1", ParseResult("2024-01-01", (observation,))
    )
    expected_sources = [legacy["raw_path"]]
    expected_pdfs = []
    if include_pdf:
        pdf = documents.archive(b"%PDF-1.4 test")
        expected_sources.append(pdf["raw_path"])
        expected_pdfs.append(pdf["raw_path"])
        store.save_result(
            pdf["hash"],
            "pdf-v1",
            ParseResult(
                "2024-01-01",
                (Observation("pdf-station", "PDF Station", "2024-01-01", rain=2),),
            ),
        )
    result = reporting.export_reports(settings, database, charts=False)
    output = Path(result["export_dir"])
    daily = json.loads((output / "list_all.json").read_text())[0]
    assert daily["pdf_paths"] == expected_pdfs
    assert daily["pdf_path"] == (expected_pdfs[0] if expected_pdfs else None)
    assert daily["source_paths"] == sorted(expected_sources)
    legacy_row = next(
        row for row in daily["weather_list"] if row["station_id"] == "legacy-station"
    )
    assert legacy_row["raw_path"] == legacy["raw_path"]
    assert legacy_row["quality_flags"] == ["missing_pdf"]
    assert json.loads((output / "idx_by_date.json").read_text())["2024-01-01"] == daily
