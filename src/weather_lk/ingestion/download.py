import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_PDF_BYTES = 32 * 1024 * 1024


def validate_pdf(content):
    if not content.startswith(b"%PDF-"):
        raise ValueError("Source did not return a PDF document")
    if len(content) > MAX_PDF_BYTES:
        raise ValueError("Source PDF exceeds the 32 MiB size limit")


def fetch_pdf(url, settings, opener=urlopen, sleep=time.sleep):
    if not url.lower().startswith(("https://", "http://")):
        raise ValueError(
            "Downloads require an HTTP or HTTPS URL; use --file for local PDFs"
        )
    for attempt in range(settings.download_retries):
        try:
            request = Request(url, headers={"User-Agent": "weather-lk/2.0"})
            with opener(request, timeout=settings.download_timeout_seconds) as response:
                content = response.read(MAX_PDF_BYTES + 1)
            validate_pdf(content)
            return content
        except (URLError, TimeoutError, OSError) as error:
            if isinstance(error, HTTPError) and error.code not in (
                408,
                429,
                500,
                502,
                503,
                504,
            ):
                raise
            if attempt + 1 == settings.download_retries:
                raise
            sleep(min(2**attempt, 8))
