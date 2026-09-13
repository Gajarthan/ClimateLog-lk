from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from weather_lk.config import Settings
from weather_lk.ingestion.download import fetch_pdf


def test_transient_download_retries_with_backoff(tmp_path):
    calls, delays = [], []

    def opener(request, timeout):
        calls.append(timeout)
        if len(calls) < 3:
            raise URLError("Temporary outage")
        return BytesIO(b"%PDF-example")

    assert (
        fetch_pdf(
            "https://example.invalid/report.pdf",
            Settings(tmp_path),
            opener,
            delays.append,
        )
        == b"%PDF-example"
    )
    assert calls == [60, 60, 60]
    assert delays == [1, 2]


def test_permanent_http_error_is_not_retried(tmp_path):
    def opener(request, timeout):
        raise HTTPError(request.full_url, 404, "Missing", {}, None)

    with pytest.raises(HTTPError):
        fetch_pdf(
            "https://example.invalid/missing.pdf",
            Settings(tmp_path),
            opener,
            lambda delay: pytest.fail("Permanent failure must not retry"),
        )
