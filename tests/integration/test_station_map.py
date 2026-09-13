import importlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def maps():
    assert importlib.util.find_spec("weather_lk.exports.station_map"), (
        "Station map renderer missing"
    )
    return importlib.import_module("weather_lk.exports.station_map")


def test_map_uses_only_reference_matches():
    rows = [
        {
            "station_id": "colombo",
            "place": "Colombo",
            "rain": 0,
            "max_temp": 30,
            "trace_rain": False,
        },
        {
            "station_id": "unknown-site",
            "place": "Unknown",
            "rain": 100,
            "max_temp": 40,
            "trace_rain": False,
            "lat": 6.9,
            "lng": 79.8,
        },
    ]
    points = maps().map_points(rows)
    assert len(points) == 1
    assert points[0]["station_id"] == "colombo"
    assert points[0]["latitude"] == 6.9 and points[0]["longitude"] == 79.867
    assert points[0]["rain"] == 0


def test_snapshot_map_count_and_output(tmp_path):
    snapshot = json.loads((ROOT / "docs/dashboard/snapshot.json").read_text())
    module = maps()
    points = module.map_points(snapshot["observations"])
    assert len(points) == 16
    assert all(5.8 < p["latitude"] < 10 and 79 < p["longitude"] < 82.2 for p in points)
    result = module.render_map(snapshot, tmp_path)
    assert result.name == "sri-lanka-map.png"
    assert result.stat().st_size > 10000
