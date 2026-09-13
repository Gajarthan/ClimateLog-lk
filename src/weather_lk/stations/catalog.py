"""Resolve names using packaged legacy seeds without guessing ambiguous aliases.

Seed coordinates were historically geocoded and are not verified instrument
locations. The repeated national-centroid fallback is exposed as missing.
"""

import hashlib
import json
import re
import unicodedata
from importlib.resources import files


def _clean_name(value: str) -> str:
    value = " ".join(unicodedata.normalize("NFKC", str(value)).split())
    # In these multilingual reports the English name follows the native-script
    # labels. Preserve a wholly native-script unknown name instead of losing it.
    if re.search(r"[\u0b80-\u0bff\u0d80-\u0dff]", value):
        english_tail = re.split(r"[\u0b80-\u0bff\u0d80-\u0dff]+", value)[-1].strip()
        if re.search(r"[A-Za-z]", english_tail):
            value = english_tail
    return re.sub(r"^Stations?\s+", "", value, flags=re.IGNORECASE).strip()


def _slug(value: str, preserve_identity: bool = False) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if preserve_identity and re.search(r"[^a-z0-9 ]", value.casefold()):
        return (
            (slug or "station")
            + "-"
            + hashlib.sha256(value.casefold().encode()).hexdigest()[:16]
        )
    return (
        slug or "station-" + hashlib.sha256(value.casefold().encode()).hexdigest()[:16]
    )


class StationCatalog:
    def __init__(self):
        resources = files("weather_lk.stations").joinpath("data")
        self._coordinates = json.loads(
            resources.joinpath("coordinates.json").read_text(encoding="utf-8")
        )
        aliases = json.loads(
            resources.joinpath("aliases.json").read_text(encoding="utf-8")
        )
        self._aliases = {key.casefold(): value for key, value in aliases.items()}
        self._names = {}
        for name in self._coordinates:
            key = name.strip().casefold()
            self._names.setdefault(key, []).append(name)

    def resolve(self, name: str) -> dict:
        place = _clean_name(name)
        key = place.casefold()
        flags = []
        # This historical fuzzy alias joins two distinct locations. It requires
        # source-specific station evidence before it can be safely applied.
        if key == "wellawa":
            flags.append("ambiguous_alias")
        elif key in self._aliases:
            place = self._aliases[key]
            key = place.casefold()
        candidates = self._names.get(key, [])
        lat = lng = None
        if candidates:
            place = next(
                (item.strip() for item in candidates if item.strip() == place),
                candidates[0].strip(),
            )
            coordinates = {tuple(self._coordinates[item]) for item in candidates}
            if len(coordinates) > 1:
                flags.append("ambiguous_coordinates")
            else:
                latitude, longitude = next(iter(coordinates))
                if (
                    abs(latitude - 7.873054) < 0.000001
                    and abs(longitude - 80.771797) < 0.000001
                ):
                    flags.append("coordinates_missing")
                else:
                    lat, lng = latitude, longitude
                    flags.append("legacy_coordinates_unverified")
        else:
            flags.append("unknown_station")
        return dict(
            station_id=_slug(place, preserve_identity=not candidates),
            place=place,
            lat=lat,
            lng=lng,
            quality_flags=tuple(flags),
        )
