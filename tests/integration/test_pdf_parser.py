"""Expectations transcribed from the two bundled report tables, not parser output."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from weather_lk.domain.validation import validate_result
from weather_lk.parsing.meteo_pdf import parse_pdf


@pytest.mark.parametrize("stem", ["20240222", "20240223"])
def test_bundled_reports_match_visually_verified_observations(stem):
    fixture_dir = Path(__file__).parents[1] / "data"
    expected = json.loads((fixture_dir / f"{stem}.expected.json").read_text())
    result = parse_pdf(fixture_dir / f"{stem}.pdf")
    validate_result(result)
    assert result.report_date == expected["report_date"]
    assert len(result.observations) == expected["observation_count"]
    observations = {o.station_id: asdict(o) for o in result.observations}
    for item in expected["observations"]:
        actual = observations[item["station_id"]]
        assert {key: actual[key] for key in item} == item
        assert actual["date"] == expected["report_date"]
    assert observations["maskeliya"]["raw"]["rain"] == "NA"
    assert any("period ending" in message for message in result.diagnostics)
    assert not any("malformed" in message for message in result.diagnostics)
    assert "highest-rainfall" not in observations
    if stem == "20240223":
        assert "madampe" not in observations
        assert any(
            "83.0" in message and "Madampe" in message for message in result.diagnostics
        )
