"""Pricing-deviation and persistence tests."""

from pathlib import Path

import pytest

from src.main import (
    _detect_pricing_deviation_python,
    _make_log_key,
    load_logged_entries,
    log_deviation,
)


def test_fair_market_is_not_flagged() -> None:
    assert _detect_pricing_deviation_python("Fair", [0.5, 0.5]) is None


@pytest.mark.parametrize(
    ("prices", "expected_deviation"),
    [([0.6, 0.45], 0.05), ([0.3, 0.4], -0.3), ([0.0, 0.4], -0.6)],
)
def test_sum_to_one_deviation_is_flagged(prices: list[float], expected_deviation: float) -> None:
    result = _detect_pricing_deviation_python("Snapshot", prices)
    assert result is not None
    assert result["sum_deviation"] == pytest.approx(expected_deviation)
    assert result["price_range"] == pytest.approx(max(prices) - min(prices))


@pytest.mark.parametrize("prices", [[], [0.5], [0.5, float("nan")], [-0.1, 0.5]])
def test_invalid_prices_are_not_flagged(prices: list[float]) -> None:
    assert _detect_pricing_deviation_python("Invalid", prices) is None


def test_threshold_boundary_is_not_flagged() -> None:
    assert _detect_pricing_deviation_python("Boundary", [0.5, 0.52]) is None


@pytest.mark.parametrize("threshold", [-0.01, 0.0, 1.0, float("inf"), float("nan")])
def test_invalid_threshold_is_rejected(threshold: float) -> None:
    with pytest.raises(ValueError, match="threshold"):
        _detect_pricing_deviation_python("Invalid threshold", [0.5, 0.5], threshold)


def test_csv_roundtrip_uses_unambiguous_fields(tmp_path: Path) -> None:
    result = _detect_pricing_deviation_python("Persisted", [0.6, 0.45])
    assert result is not None
    output = tmp_path / "deviations.csv"
    log_deviation(result, str(output))
    assert load_logged_entries(str(output)) == {_make_log_key(result)}


def test_empty_existing_csv_receives_header(tmp_path: Path) -> None:
    result = _detect_pricing_deviation_python("Persisted", [0.6, 0.45])
    assert result is not None
    output = tmp_path / "deviations.csv"
    output.touch()

    log_deviation(result, str(output))

    assert output.read_text(encoding="utf-8").startswith("timestamp,question,prices,")
    assert load_logged_entries(str(output)) == {_make_log_key(result)}
