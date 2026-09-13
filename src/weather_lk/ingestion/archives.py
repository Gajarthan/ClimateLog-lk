"""Historical discovery is optional and never runs during package import."""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def discover_wayback(limit=100):
    parameters = urlencode(
        [
            ("url", "meteo.gov.lk/images/mergepdf/"),
            ("matchType", "prefix"),
            ("output", "json"),
            ("filter", "statuscode:200"),
            ("filter", "mimetype:application/pdf"),
            ("collapse", "digest"),
            ("limit", str(limit)),
        ]
    )
    request = Request(
        "https://web.archive.org/cdx/search/cdx?" + parameters,
        headers={"User-Agent": "weather-lk/2.0"},
    )
    with urlopen(request, timeout=60) as response:
        rows = json.load(response)
    if not rows:
        return []
    header, *records = rows
    result = []
    for record in records:
        entry = dict(zip(header, record))
        original = entry.get("original", "")
        if "meteo.gov.lk/" in original and "/images/mergepdf/" in original:
            result.append(
                f"https://web.archive.org/web/{entry['timestamp']}id_/{original}"
            )
    return result


def discover_google():
    try:
        from googlesearch import search
    except ImportError as error:
        raise RuntimeError(
            "Install the archives extra to use Google discovery"
        ) from error
    return [
        url
        for url in search(
            "site:meteo.gov.lk/images/mergepdf filetype:pdf",
            num_results=64,
            sleep_interval=1,
        )
        if "meteo.gov.lk/images/mergepdf" in url
    ]
