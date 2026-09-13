import pytest

from weather_lk.analytics.statistics import month_statistics, summarize


def row(day, rain=None, minimum=None, maximum=None, trace=False):
    return dict(
        date=day,
        station_id="station",
        rain=rain,
        min_temp=minimum,
        max_temp=maximum,
        trace_rain=trace,
    )


def test_valid_measure_denominators_and_paired_temperature():
    stats = summarize(
        [
            row("2024-01-01", 0, 0, 10),
            row("2024-01-02", 10, None, 30),
            row("2024-01-03", None, 20, None),
        ]
    )
    assert stats["rain"] == dict(count=2, mean=5, total=10, min=0, max=10)
    assert stats["min_temp"]["mean"] == 10
    assert stats["max_temp"]["mean"] == 20
    assert stats["paired_temp"]["count"] == 1
    assert stats["paired_temp"]["mean"] == 5
    assert stats["rainy_fraction"] == 0.5


def test_trace_and_empty_observations_are_explicit():
    stats = summarize([row("2024-01-01", 0, trace=True), row("2024-01-02")])
    assert stats["records"] == 2
    assert stats["rainy_days"] == 1
    assert stats["rainy_fraction"] == 1
    assert stats["rain"]["mean"] == 0
    empty = summarize([])
    assert empty["rain"]["mean"] is None
    assert empty["rain"]["total"] is None
    assert empty["rainy_fraction"] is None
    assert month_statistics([]) == {}


def test_all_period_mean_weights_daily_values_not_month_means():
    rows = [row("2024-01-01", 3), row("2024-01-02", 3), row("2024-02-01", 30)]
    assert summarize(rows)["rain"]["mean"] == 12
    months = month_statistics(rows)
    assert months["2024-01"]["rain"]["count"] == 2
    assert months["2024-02"]["rain"]["count"] == 1


def test_calendar_gaps_and_empty_months():
    rows = [row("2024-01-31", 1), row("2024-03-01", 2)]
    months = month_statistics(rows)
    assert list(months) == ["2024-01", "2024-02", "2024-03"]
    assert months["2024-02"]["rain"]["count"] == 0
    assert months["2024-02"]["coverage"]["calendar_days"] == 29
    assert months["2024-02"]["coverage"]["fraction"] == 0
    assert summarize(rows)["coverage"]["calendar_days"] == 31
    assert summarize(rows)["coverage"]["fraction"] == pytest.approx(2 / 31)


def test_window_coverage_includes_missing_edges():
    stats = summarize([row("2024-01-30", 0)], start="2024-01-01", end="2024-01-30")
    assert stats["coverage"]["calendar_days"] == 30
    assert stats["coverage"]["fraction"] == pytest.approx(1 / 30)


def test_nonfinite_samples_do_not_contaminate_statistics():
    stats = summarize(
        [
            row("2024-01-01", float("nan"), float("inf"), 20),
            row("2024-01-02", 4, 10, 30),
        ]
    )
    assert stats["rain"]["mean"] == 4
    assert stats["min_temp"]["mean"] == 10
    assert stats["paired_temp"]["mean"] == 20
