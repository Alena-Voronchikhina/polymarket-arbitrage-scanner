"""Edge-case tests for Polymarket outcome-price parsing."""

import math

from src.main import _parse_outcome_prices


def test_json_string_of_numeric_strings() -> None:
    assert _parse_outcome_prices('["0.55", "0.45"]') == [0.55, 0.45]


def test_json_string_of_numbers() -> None:
    assert _parse_outcome_prices("[0.6, 0.4]") == [0.6, 0.4]


def test_native_list_of_floats() -> None:
    assert _parse_outcome_prices([0.25, 0.75]) == [0.25, 0.75]


def test_native_list_of_numeric_strings() -> None:
    assert _parse_outcome_prices(["0.1", "0.2", "0.7"]) == [0.1, 0.2, 0.7]


def test_invalid_json_returns_none() -> None:
    assert _parse_outcome_prices("not-json") is None
    assert _parse_outcome_prices("{]") is None


def test_non_list_json_returns_none() -> None:
    assert _parse_outcome_prices('"0.5"') is None
    assert _parse_outcome_prices('{"a": 1}') is None


def test_unsupported_raw_types_return_none() -> None:
    assert _parse_outcome_prices(None) is None
    assert _parse_outcome_prices(0.5) is None
    assert _parse_outcome_prices({"prices": [0.5, 0.5]}) is None


def test_non_numeric_entry_returns_none() -> None:
    assert _parse_outcome_prices(["0.5", "abc"]) is None
    assert _parse_outcome_prices([0.5, object()]) is None


def test_falsy_entries_are_skipped() -> None:
    # Current parser skips falsy values (including 0 / 0.0 / "").
    assert _parse_outcome_prices([0.5, 0, 0.5]) == [0.5, 0.5]
    assert _parse_outcome_prices(["0.4", "", "0.6"]) == [0.4, 0.6]
    assert _parse_outcome_prices([None, 0.3, 0.7]) == [0.3, 0.7]


def test_empty_list_parses_to_empty_list() -> None:
    assert _parse_outcome_prices([]) == []
    assert _parse_outcome_prices("[]") == []


def test_scientific_notation_accepted() -> None:
    prices = _parse_outcome_prices(["5e-1", "5E-1"])
    assert prices is not None
    assert len(prices) == 2
    assert math.isclose(prices[0], 0.5)
    assert math.isclose(prices[1], 0.5)


def test_whitespace_numeric_strings() -> None:
    assert _parse_outcome_prices([" 0.2 ", "0.8"]) == [0.2, 0.8]
