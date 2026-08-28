"""Outcome-price parsing tests."""

import math

import pytest

from src.main import _parse_outcome_prices


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('["0", "1"]', [0.0, 1.0]),
        ([0.0, 0.4, 0.6], [0.0, 0.4, 0.6]),
        ([" 0.2 ", "0.8"], [0.2, 0.8]),
        ([], []),
    ],
)
def test_valid_prices_preserve_all_outcomes(raw: object, expected: list[float]) -> None:
    assert _parse_outcome_prices(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        0.5,
        "not-json",
        '{"prices": [0.5, 0.5]}',
        [0.5, None],
        [0.5, ""],
        [0.5, True],
        [0.5, "abc"],
        [0.5, -0.1],
        [0.5, 1.1],
        [0.5, math.nan],
        [0.5, math.inf],
    ],
)
def test_invalid_or_incomplete_prices_are_rejected(raw: object) -> None:
    assert _parse_outcome_prices(raw) is None
