"""Pure station, value, date and domain regression tests."""

from dataclasses import replace

import pytest

from weather_lk.domain.models import Observation, ParseResult
from weather_lk.domain.validation import ValidationError, validate_result
from weather_lk.parsing.meteo_pdf import parse_tables
from weather_lk.stations.catalog import StationCatalog


def weather_table(rows, date="2024.02.23"):
    return [
        [f"Weather Report {date}", "", "", "", ""],
        ["Meteorological Stations", "Max", "Min", "Rainfall (mm)", ""],
        *rows,
    ]


def test_aliases_and_mixed_script_names_resolve_deterministically():
    catalog = StationCatalog()
    assert catalog.resolve("  hambanthota  ")["station_id"] == "hambantota"
    assert catalog.resolve("தமிழ்Colombo")["place"] == "Colombo"
    assert catalog.resolve("polonnaruwa")["place"] == "Polonnaruwa"
    assert catalog.resolve("Maha Illuppallama")["station_id"] == "maha-illuppallama"


def test_unknown_stations_and_coordinate_ambiguities_are_preserved():
    catalog = StationCatalog()
    unknown = catalog.resolve("New Hill Observatory")
    assert unknown["station_id"] == "new-hill-observatory"
    assert unknown["lat"] is None
    assert "unknown_station" in unknown["quality_flags"]
    assert catalog.resolve("New Colombo")["place"] == "New Colombo"
    ambiguous = catalog.resolve("Wellawa")
    assert ambiguous["station_id"] == "wellawa"
    assert "ambiguous_alias" in ambiguous["quality_flags"]
    assert catalog.resolve("Mediyawa")["lat"] is None
    assert "ambiguous_coordinates" in catalog.resolve("Mediyawa")["quality_flags"]
    assert catalog.resolve("Wevalthalawa")["lat"] is None


def test_accented_unknown_station_names_are_not_truncated():
    station = StationCatalog().resolve("Café Hill")
    assert station["place"] == "Café Hill"
    assert "unknown_station" in station["quality_flags"]


def test_simple_rainfall_tables():
    result = parse_tables(
        [
            [
                ["Weather Report 2024.02.23"],
                ["Station", "Rainfall (mm)"],
                ["Norton", "0"],
            ],
        ]
    )
    assert [(o.place, o.rain) for o in result.observations] == [("Norton", 0)]


@pytest.mark.parametrize(
    "row, expected",
    [
        (["Norton", "1", "Canyon", "2"], [("Norton", 1), ("Canyon", 2)]),
        (["Norton", "1", "Canyon", "", "2"], [("Norton", 1), ("Canyon", 2)]),
        (["Norton", "1", "Canyon", "", "", "2"], [("Norton", 1), ("Canyon", 2)]),
        (
            ["Norton", "1", "Canyon", "2", "Maskeliya", "3"],
            [("Norton", 1), ("Canyon", 2), ("Maskeliya", 3)],
        ),
        (
            ["Norton", "1", "Canyon", "", "Maskeliya", "3"],
            [("Norton", 1), ("Canyon", None), ("Maskeliya", 3)],
        ),
    ],
)
def test_rainfall_layouts_keep_each_value_with_its_station(row, expected):
    result = parse_tables(
        [[["Weather Report 2024.02.23"], ["Rainfall Stations", "Rainfall (mm)"], row]]
    )
    assert [(o.place, o.rain) for o in result.observations] == expected


@pytest.mark.parametrize(
    "row",
    [
        ["Jaffna", "32", "22"],
        ["Jaffna", "32", "22", "0", "", "", ""],
    ],
)
def test_unsupported_weather_rows_reject_partial_report(row):
    with pytest.raises(ValidationError, match="unsupported"):
        parse_tables([weather_table([["Colombo", "30", "20", "0", ""], row])])


@pytest.mark.parametrize(
    "row",
    [
        ["Norton", "1", "Canyon"],
        ["Norton", "1", "Canyon", "2", "3"],
        ["Norton", "1", "Canyon", "", "", "", "3"],
    ],
)
def test_unsupported_rainfall_rows_reject_partial_report(row):
    with pytest.raises(ValidationError, match="unsupported"):
        parse_tables(
            [
                [
                    ["Weather Report 2024.02.23"],
                    ["Rainfall Stations", "Rainfall (mm)"],
                    ["Norton", "0"],
                    row,
                ]
            ]
        )


def test_unknown_names_that_lose_characters_have_distinct_stable_ids():
    catalog = StationCatalog()
    names = ["Café Hill", "Cafè Hill", "Caf Hill", "New.Hill", "New/Hill", "New Hill"]
    identities = [catalog.resolve(name)["station_id"] for name in names]
    assert len(set(identities)) == len(names)
    assert catalog.resolve("Café Hill")["station_id"] == identities[0]
    assert catalog.resolve("Colombo Fort")["station_id"] == "colombo-fort"


def test_all_weather_tables_are_read_and_unrelated_tables_are_ignored():
    result = parse_tables(
        [
            [["Accounts", "Credit", "Debit", "", ""], ["Office", "1", "2", "3", ""]],
            weather_table([["Colombo", "31", "0", "0", ""]]),
            [
                [
                    "Rainfall Stations",
                    "Rainfall (mm)",
                    "Rainfall Stations",
                    "",
                    "Rainfall (mm)",
                ],
                ["New Hill Observatory", "TR", "Maskeliya", "", "NA"],
            ],
        ]
    )
    assert result.report_date == "2024-02-23"
    assert [o.place for o in result.observations] == [
        "Colombo",
        "New Hill Observatory",
        "Maskeliya",
    ]
    assert result.observations[0].min_temp == 0
    assert result.observations[0].rain == 0
    assert result.observations[1].trace_rain is True
    assert result.observations[1].rain == 0
    assert result.observations[2].rain is None
    assert result.observations[1].min_temp is None
    assert result.observations[1].raw["rain"] == "TR"
    validate_result(result)


def test_missing_and_malformed_numbers_are_distinguished():
    result = parse_tables([weather_table([["Colombo", "bad", "NA", "1O.2mm", ""]])])
    observation = result.observations[0]
    assert observation.max_temp is None
    assert observation.min_temp is None
    assert observation.rain is None
    assert "malformed_rain" in observation.quality_flags
    assert "malformed_max_temp" in observation.quality_flags
    assert "missing_min_temp" in observation.quality_flags
    assert any("1O.2mm" in message for message in result.diagnostics)
    assert observation.raw["rain"] == "1O.2mm"


@pytest.mark.parametrize("date", ["", "2024.02.31"])
def test_missing_or_invalid_date_never_becomes_today(date):
    with pytest.raises(ValidationError, match="date"):
        parse_tables([weather_table([["Colombo", "30", "20", "0", ""]], date)])


def test_conflicting_report_dates_are_rejected():
    with pytest.raises(ValidationError, match="date"):
        parse_tables(
            [
                weather_table([["Colombo", "30", "20", "0", ""]]),
                weather_table([["Jaffna", "30", "20", "0", ""]], "2024.02.24"),
            ]
        )


def test_four_column_weather_and_rainfall_tables():
    result = parse_tables(
        [
            [
                ["Weather Report 2024.02.23"],
                ["Station", "Maximum", "Minimum", "Rainfall"],
                ["Colombo", "30.5 C", "20.1", "0 mm"],
            ],
            [
                ["Rainfall Stations", "Rainfall", "Rainfall Stations", "Rainfall"],
                ["Norton", "2.4", "Canyon", "-"],
            ],
        ]
    )
    assert [(o.place, o.rain) for o in result.observations] == [
        ("Colombo", 0),
        ("Norton", 2.4),
        ("Canyon", None),
    ]
    assert result.observations[0].max_temp == 30.5


@pytest.mark.parametrize(
    "header, row",
    [
        (["Station", "Minimum", "Maximum", "Rainfall"], ["Colombo", "20", "", "0"]),
        (["Rainfall", "Station", "Minimum", "Maximum"], ["0", "Colombo", "20", ""]),
    ],
)
def test_weather_column_meanings_follow_the_printed_header(header, row):
    result = parse_tables([[["Weather Report 2024.02.23"], header, row]])
    observation = result.observations[0]
    assert observation.place == "Colombo"
    assert observation.min_temp == 20
    assert observation.max_temp is None
    assert observation.rain == 0
    assert observation.raw["min_temp"] == "20"
    assert observation.raw["max_temp"] == ""


def test_validation_rejects_unusable_and_contradictory_results():
    base = Observation(
        "colombo", "Colombo", "2024-02-23", rain=0, min_temp=20, max_temp=30
    )
    validate_result(ParseResult(base.date, (base,)))
    invalid = [
        replace(base, rain=-1),
        replace(base, rain=float("nan")),
        replace(base, min_temp=40),
        replace(base, max_temp=float("inf")),
        replace(base, date="2024-02-31"),
    ]
    for observation in invalid:
        with pytest.raises(ValidationError):
            validate_result(ParseResult(base.date, (observation,)))
    with pytest.raises(ValidationError, match="duplicate"):
        validate_result(ParseResult(base.date, (base, base)))
    with pytest.raises(ValidationError, match="empty"):
        validate_result(ParseResult(base.date, ()))
