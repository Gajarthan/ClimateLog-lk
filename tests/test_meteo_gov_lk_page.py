import pytest


@pytest.mark.live
def test_official_report_url():
    from weather_lk.ingestion.meteo import discover_meteo
    urls = discover_meteo()
    assert urls and urls[0].startswith(("http://", "https://"))
