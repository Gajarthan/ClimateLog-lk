"""Reject results that cannot safely become published observations."""

import math
import re
from datetime import date

from .models import ParseResult


class ValidationError(ValueError):
    """A report contains invalid or contradictory domain values."""


def _validate_date(value: str) -> None:
    try:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"Invalid or absent report date: {value!r}") from exc


def validate_result(result: ParseResult) -> None:
    _validate_date(result.report_date)
    if not result.observations:
        raise ValidationError("Report contains empty observations")
    seen = set()
    for observation in result.observations:
        _validate_date(observation.date)
        if observation.date != result.report_date:
            raise ValidationError("Observation date differs from report date")
        key = (observation.station_id, observation.date)
        if key in seen:
            raise ValidationError(f"Report contains duplicate station/date: {key}")
        seen.add(key)
        if not observation.station_id or not observation.place:
            raise ValidationError("Observation has no station identity")
        for name in ("rain", "min_temp", "max_temp", "lat", "lng"):
            value = getattr(observation, name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValidationError(
                    f"Invalid numeric {name} for {observation.station_id}: {value!r}"
                )
        if observation.rain is not None and observation.rain < 0:
            raise ValidationError(f"Negative rain for {observation.station_id}")
        if (
            observation.min_temp is not None
            and observation.max_temp is not None
            and observation.min_temp > observation.max_temp
        ):
            raise ValidationError(
                f"Minimum exceeds maximum temperature for {observation.station_id}"
            )
