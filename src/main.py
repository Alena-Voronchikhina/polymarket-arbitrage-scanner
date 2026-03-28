"""Poll Polymarket every 30 seconds for potential mispricing.

If the C++ extension is available, this module uses it for the pricing check.
If not, it falls back to pure Python.

Build the extension with:
  cd cpp/build && cmake .. -DCMAKE_BUILD_TYPE=Release && cmake --build . --parallel
  cp arbitrage_engine*.so ../../src/
"""

import csv
import importlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Final, TypeAlias, TypedDict

import requests


class Opportunity(TypedDict):
    """Fields recorded for one flagged market."""

    question: str
    prices: list[float]
    price_sum: float
    spread: float


LogKey: TypeAlias = tuple[str, tuple[float, ...], float, float]
MarketJSON: TypeAlias = dict[str, Any]


_API_URL: Final[str] = "https://gamma-api.polymarket.com/events?active=true&closed=false&limit=100"
_LOG_PATH: Final[str] = "opportunities.csv"
_POLL_PERIOD: Final[int] = 30
_THRESHOLD: Final[float] = 0.02

_ae: Any = None
_engine: Any = None
_USE_CPP: bool = False

try:
    _ae = importlib.import_module("arbitrage_engine")
    _engine = _ae.ArbitrageEngine(threshold=_THRESHOLD)
    _USE_CPP = True
    print("[backend] C++ ArbitrageEngine loaded (Kahan-based check active).")
except ModuleNotFoundError:
    print("[backend] C++ module not found; using Python fallback.")


def _parse_outcome_prices(raw_prices: Any) -> list[float] | None:
    """Parse API outcome prices into a clean list of floats."""
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
        if not value:
            continue
        try:
            parsed.append(float(value))
        except (TypeError, ValueError):
            return None
    return parsed


def _detect_mispricing_python(
    question: str, prices: list[float], threshold: float = 0.02
) -> Opportunity | None:
    """Fallback mispricing check using Python sum()."""
    if len(prices) < 2:
        return None

    total = sum(prices)
    if abs(total - 1.0) <= threshold:
        return None

    return {
        "question": question,
        "prices": prices,
        "price_sum": total,
        "spread": max(prices) - min(prices),
    }


def detect_opportunity(question: str, prices: list[float]) -> Opportunity | None:
    """Use C++ when available, otherwise run the Python fallback."""
    if _USE_CPP:
        market = _ae.Market(question, prices)
        opp = _engine.evaluate(market)
        if opp is None:
            return None

        return {
            "question": opp.question,
            "prices": opp.prices,
            "price_sum": opp.price_sum,
            "spread": opp.spread,
        }

    return _detect_mispricing_python(question, prices)


def _make_log_key(question: str, prices: list[float], price_sum: float, spread: float) -> LogKey:
    """Build a rounded key for CSV deduplication."""
    return (
        question,
        tuple(round(p, 6) for p in prices),
        round(price_sum, 6),
        round(spread, 6),
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
                    prices = [float(p) for p in json.loads(row["prices"])]
                    price_sum = float(row["price_sum"])
                    spread = float(row["spread"])
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
                entries.add(_make_log_key(row.get("question", ""), prices, price_sum, spread))
    except OSError:
        pass

    return entries


def log_opportunity(opportunity: Opportunity, file_path: str = _LOG_PATH) -> None:
    """Append one flagged market to CSV and write the header if needed."""
    file_exists = os.path.exists(file_path)
    with open(file_path, "a", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle)
        if not file_exists:
            writer.writerow(["timestamp", "question", "prices", "price_sum", "spread"])
        writer.writerow(
            [
                datetime.now(timezone.utc).isoformat(),
                opportunity["question"],
                json.dumps(opportunity["prices"]),
                f"{opportunity['price_sum']:.6f}",
                f"{opportunity['spread']:.6f}",
            ]
        )


def fetch_active_events() -> list[MarketJSON]:
    """Fetch currently active events from the Polymarket API."""
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
    """Process one API snapshot and return count of newly logged opportunities."""
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

            opp = detect_opportunity(question, prices)
            if opp is None:
                continue

            key = _make_log_key(opp["question"], opp["prices"], opp["price_sum"], opp["spread"])
            if key not in logged:
                log_opportunity(opp)
                logged.add(key)
                new_count += 1
                print(f"[opportunity] {opp['question']}")
                print(
                    "    prices="
                    f"{opp['prices']}  sum={opp['price_sum']:.6f}  spread={opp['spread']:.6f}"
                )

    return new_count


def main() -> None:
    """Run the scanner loop until interrupted."""
    logged = load_logged_entries()
    print(f"Loaded {len(logged)} prior opportunities from {_LOG_PATH}")

    while True:
        try:
            n = scan_once(logged)
            print(f"New opportunities this cycle: {n}")
        except requests.RequestException as exc:
            print(f"Request error: {exc}")

        print(f"Waiting {_POLL_PERIOD}s...")
        time.sleep(_POLL_PERIOD)


if __name__ == "__main__":
    main()
