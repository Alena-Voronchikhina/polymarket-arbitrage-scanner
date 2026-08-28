"""Poll one Polymarket API page for sum-to-one pricing deviations.

The scanner records observations for manual research. It does not inspect an
order book, model fees or depth, or place trades.
"""

import csv
import importlib
import json
import math
import os
import time
from datetime import datetime, timezone
from typing import Any, Final, TypeAlias, TypedDict

import requests


class PricingDeviation(TypedDict):
    """Fields recorded for one flagged market snapshot."""

    question: str
    prices: list[float]
    price_sum: float
    sum_deviation: float
    price_range: float


LogKey: TypeAlias = tuple[str, tuple[float, ...], float, float, float]
MarketJSON: TypeAlias = dict[str, Any]


_API_URL: Final[str] = "https://gamma-api.polymarket.com/events?active=true&closed=false&limit=100"
_LOG_PATH: Final[str] = "pricing_deviations.csv"
_POLL_PERIOD: Final[int] = 30
_THRESHOLD: Final[float] = 0.02
_COMPARISON_EPSILON: Final[float] = 1e-12

_pe: Any = None
_engine: Any = None
_USE_CPP: bool = False

try:
    _pe = importlib.import_module("pricing_engine")
    _engine = _pe.PricingEngine(threshold=_THRESHOLD)
    _USE_CPP = True
    print("[backend] C++ PricingEngine loaded (Kahan-based check active).")
except (ImportError, OSError):
    print("[backend] C++ module unavailable; using Python fallback.")


def _parse_outcome_prices(raw_prices: Any) -> list[float] | None:
    """Parse a complete list of finite outcome prices in the range [0, 1]."""
    if isinstance(raw_prices, str):
        try:
            raw_values = json.loads(raw_prices)
        except json.JSONDecodeError:
            return None
    elif isinstance(raw_prices, list):
        raw_values = raw_prices
    else:
        return None

    if not isinstance(raw_values, list):
        return None

    parsed: list[float] = []
    for value in raw_values:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, str) and not value.strip():
            return None
        try:
            price = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(price) or not 0.0 <= price <= 1.0:
            return None
        parsed.append(price)
    return parsed


def _kahan_sum(values: list[float]) -> float:
    """Match the C++ backend's compensated summation path."""
    total = 0.0
    compensation = 0.0
    for value in values:
        corrected = value - compensation
        updated = total + corrected
        compensation = (updated - total) - corrected
        total = updated
    return total


def _detect_pricing_deviation_python(
    question: str, prices: list[float], threshold: float = _THRESHOLD
) -> PricingDeviation | None:
    """Return a sum-to-one deviation for already validated prices."""
    if not math.isfinite(threshold) or not 0.0 < threshold < 1.0:
        raise ValueError("threshold must be finite and in (0, 1)")
    if len(prices) < 2 or any(
        not math.isfinite(price) or not 0.0 <= price <= 1.0 for price in prices
    ):
        return None

    total = _kahan_sum(prices)
    sum_deviation = total - 1.0
    if abs(sum_deviation) <= threshold + _COMPARISON_EPSILON:
        return None

    return {
        "question": question,
        "prices": prices,
        "price_sum": total,
        "sum_deviation": sum_deviation,
        "price_range": max(prices) - min(prices),
    }


def detect_deviation(question: str, prices: list[float]) -> PricingDeviation | None:
    """Use C++ when available, otherwise run the equivalent Python check."""
    if _USE_CPP:
        market = _pe.Market(question, prices)
        deviation = _engine.evaluate(market)
        if deviation is None:
            return None

        return {
            "question": deviation.question,
            "prices": deviation.prices,
            "price_sum": deviation.price_sum,
            "sum_deviation": deviation.sum_deviation,
            "price_range": deviation.price_range,
        }

    return _detect_pricing_deviation_python(question, prices)


def _make_log_key(deviation: PricingDeviation) -> LogKey:
    """Build a rounded key for CSV deduplication."""
    return (
        deviation["question"],
        tuple(round(price, 6) for price in deviation["prices"]),
        round(deviation["price_sum"], 6),
        round(deviation["sum_deviation"], 6),
        round(deviation["price_range"], 6),
    )


def load_logged_entries(file_path: str = _LOG_PATH) -> set[LogKey]:
    """Read existing CSV rows and rebuild the deduplication key set."""
    entries: set[LogKey] = set()
    if not os.path.exists(file_path):
        return entries

    try:
        with open(file_path, newline="", encoding="utf-8") as file_handle:
            for row in csv.DictReader(file_handle):
                try:
                    deviation: PricingDeviation = {
                        "question": row.get("question", ""),
                        "prices": [float(price) for price in json.loads(row["prices"])],
                        "price_sum": float(row["price_sum"]),
                        "sum_deviation": float(row["sum_deviation"]),
                        "price_range": float(row["price_range"]),
                    }
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
                entries.add(_make_log_key(deviation))
    except OSError:
        pass

    return entries


def log_deviation(deviation: PricingDeviation, file_path: str = _LOG_PATH) -> None:
    """Append one flagged snapshot and write the header if needed."""
    write_header = not os.path.exists(file_path) or os.path.getsize(file_path) == 0
    with open(file_path, "a", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle)
        if write_header:
            writer.writerow(
                [
                    "timestamp",
                    "question",
                    "prices",
                    "price_sum",
                    "sum_deviation",
                    "price_range",
                ]
            )
        writer.writerow(
            [
                datetime.now(timezone.utc).isoformat(),
                deviation["question"],
                json.dumps(deviation["prices"]),
                f"{deviation['price_sum']:.6f}",
                f"{deviation['sum_deviation']:.6f}",
                f"{deviation['price_range']:.6f}",
            ]
        )


def fetch_active_events() -> list[MarketJSON]:
    """Fetch the first configured page of active events."""
    response = requests.get(_API_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return [event for event in data if isinstance(event, dict)]
    if isinstance(data, dict):
        candidate = data.get("data", data.get("markets", []))
        if isinstance(candidate, list):
            return [event for event in candidate if isinstance(event, dict)]
    return []


def scan_once(logged: set[LogKey]) -> int:
    """Process one API snapshot and return the number of newly logged rows."""
    events = fetch_active_events()
    new_count = 0

    for event in events:
        markets = event.get("markets", [])
        if not isinstance(markets, list):
            continue

        for market in markets:
            if not isinstance(market, dict):
                continue

            question_value = market.get("question", "")
            question = question_value if isinstance(question_value, str) else ""
            prices = _parse_outcome_prices(market.get("outcomePrices", []))
            if prices is None:
                continue

            deviation = detect_deviation(question, prices)
            if deviation is None:
                continue

            key = _make_log_key(deviation)
            if key not in logged:
                log_deviation(deviation)
                logged.add(key)
                new_count += 1
                print(f"[pricing-deviation] {deviation['question']}")
                print(
                    "    prices="
                    f"{deviation['prices']}  sum={deviation['price_sum']:.6f}  "
                    f"sum_deviation={deviation['sum_deviation']:.6f}  "
                    f"price_range={deviation['price_range']:.6f}"
                )

    return new_count


def main() -> None:
    """Run the scanner loop until interrupted."""
    logged = load_logged_entries()
    print(f"Loaded {len(logged)} prior pricing deviations from {_LOG_PATH}")

    while True:
        try:
            count = scan_once(logged)
            print(f"New pricing deviations this cycle: {count}")
        except requests.RequestException as exc:
            print(f"Request error: {exc}")

        print(f"Waiting {_POLL_PERIOD}s...")
        time.sleep(_POLL_PERIOD)


if __name__ == "__main__":
    main()
