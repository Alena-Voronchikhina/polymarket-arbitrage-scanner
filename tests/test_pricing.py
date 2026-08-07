"""Unit tests for the pricing / mispricing detection core."""

from src.main import _detect_mispricing_python, detect_opportunity


def test_fair_binary_market_not_flagged() -> None:
    assert _detect_mispricing_python("Fair binary", [0.50, 0.50]) is None


def test_fair_multi_outcome_not_flagged() -> None:
    assert _detect_mispricing_python("Fair multi", [0.25, 0.25, 0.25, 0.25]) is None


def test_mispriced_market_flagged_with_expected_fields() -> None:
    opp = _detect_mispricing_python("Mispriced", [0.60, 0.45])
    assert opp is not None
    assert opp["question"] == "Mispriced"
    assert opp["prices"] == [0.60, 0.45]
    assert abs(opp["price_sum"] - 1.05) < 1e-12
    assert abs(opp["spread"] - 0.15) < 1e-12


def test_underpriced_sum_also_flagged() -> None:
    opp = _detect_mispricing_python("Under", [0.30, 0.40])
    assert opp is not None
    assert abs(opp["price_sum"] - 0.70) < 1e-12


def test_within_default_threshold_not_flagged() -> None:
    # |1.015 - 1.0| = 0.015 <= 0.02
    assert _detect_mispricing_python("Near fair", [0.50, 0.515]) is None


def test_custom_threshold_changes_decision() -> None:
    prices = [0.50, 0.515]  # sum = 1.015
    assert _detect_mispricing_python("Near", prices, threshold=0.02) is None
    opp = _detect_mispricing_python("Near", prices, threshold=0.01)
    assert opp is not None


def test_insufficient_outcomes_skipped() -> None:
    assert _detect_mispricing_python("Single", [0.99]) is None
    assert _detect_mispricing_python("Empty", []) is None


def test_detect_opportunity_uses_python_fallback_path() -> None:
    """Without the C++ extension loaded, detect_opportunity mirrors Python logic."""
    assert detect_opportunity("Fair", [0.55, 0.45]) is None
    opp = detect_opportunity("Flag me", [0.70, 0.40])
    assert opp is not None
    assert opp["price_sum"] == 1.1
