import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "workflows/update_dashboard.py"


def module():
    assert SCRIPT.exists(), "Dashboard refresh command is missing"
    spec = importlib.util.spec_from_file_location("update_dashboard", SCRIPT)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_readme_uses_current_snapshot_values():
    snapshot = json.loads((ROOT / "docs/dashboard/snapshot.json").read_text())
    snapshot["report_date"] = "2026-10-01"
    snapshot["captured_at"] = "2026-10-01T04:00:00+00:00"
    snapshot["observations"] = snapshot["observations"][:2]
    for row in snapshot["observations"]:
        row["date"] = "2026-10-01"
    readme = module().render_readme(snapshot)
    assert "2026-10-01" in readme and "2026-09-12" not in readme
    assert "all 2 station readings" in readme
    assert "pipeline" not in readme.lower()


def test_refresh_failure_keeps_published_files(tmp_path, monkeypatch):
    script = module()
    from weather_lk.config import Settings
    from weather_lk.domain.models import Observation, ParseResult
    from weather_lk.services.pipeline import Pipeline
    from weather_lk.services.reporting import export_reports

    settings = Settings(tmp_path / "data")
    pipeline = Pipeline(settings)
    document = pipeline.documents.archive(b"%PDF-valid")
    pipeline.observations.save_result(
        document["hash"],
        "test",
        ParseResult(
            "2026-10-01", (Observation("a", "Station A", "2026-10-01", 1, 20, 30),)
        ),
    )
    export_reports(settings, charts=False)
    target = tmp_path / "repo"
    target.mkdir()
    (target / "README.md").write_text("previous dashboard")

    def fail(*args):
        raise RuntimeError("Render failure")

    monkeypatch.setattr(script, "render_assets", fail)
    with pytest.raises(RuntimeError, match="Render failure"):
        script.update_dashboard(settings.data_dir, target)
    assert (target / "README.md").read_text() == "previous dashboard"
    pipeline.documents.path(document).write_bytes(b"%PDF-modified")
    with pytest.raises(ValueError, match="checksum"):
        script.update_dashboard(settings.data_dir, target)
    assert (target / "README.md").read_text() == "previous dashboard"


def test_rejects_date_regression(tmp_path):
    from weather_lk.config import Settings
    from weather_lk.domain.models import Observation, ParseResult
    from weather_lk.services.pipeline import Pipeline
    from weather_lk.services.reporting import export_reports

    settings = Settings(tmp_path / "data")
    pipeline = Pipeline(settings)
    document = pipeline.documents.archive(b"%PDF-valid")
    pipeline.observations.save_result(
        document["hash"],
        "test",
        ParseResult(
            "2026-01-01", (Observation("a", "Station A", "2026-01-01", 1, 20, 30),)
        ),
    )
    export_reports(settings, charts=False)
    target = tmp_path / "repo"
    (target / "docs/dashboard").mkdir(parents=True)
    (target / "docs/dashboard/snapshot.json").write_text(
        json.dumps({"report_date": "2026-10-01"})
    )
    with pytest.raises(ValueError, match="older"):
        module().update_dashboard(settings.data_dir, target)
