# Polymarket Pricing-Deviation Scanner

A Python polling tool with an optional C++20/pybind11 backend. It reads outcome
price snapshots from the Polymarket Gamma API and records markets whose listed
prices deviate from a sum of 1.0 by more than a configurable threshold.

This is a research scanner, not an execution or arbitrage system.

## What it measures

For validated prices `p1 ... pn`, the default rule is:

```text
abs(sum(prices) - 1.0) > 0.02
```

Each recorded row contains:

- `price_sum`: compensated sum of the outcome prices
- `sum_deviation`: signed `price_sum - 1.0`
- `price_range`: `max(prices) - min(prices)`

`price_range` is descriptive. It is not a bid/ask spread or profit estimate.

## Data validation

The parser preserves numeric zero and rejects incomplete or malformed lists,
booleans, non-numeric values, NaN/infinity, negative prices, and prices above 1.
Both Python and C++ paths apply the same finite `[0, 1]` contract and require at
least two outcomes.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

The process polls every 30 seconds and appends new observations to
`pricing_deviations.csv`.

## Optional C++ backend

Python owns HTTP I/O, parsing, deduplication, and CSV persistence. The C++20
backend implements the same threshold check with Kahan-compensated summation and
is exposed through pybind11. It is an integration and numerical-consistency
exercise; this repository does not claim a measured speedup for the small price
vectors involved.

```bash
cmake -S cpp -B cpp/build-release -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build-release --parallel
PYTHONPATH=cpp/build-release python -m src.main
```

On startup, the selected backend is printed.

## Verify

```bash
ruff check src tests
ruff format --check src tests
mypy --strict src
pytest -q

cmake -S cpp -B cpp/build-debug -DCMAKE_BUILD_TYPE=Debug -DENABLE_SANITIZERS=ON
cmake --build cpp/build-debug --parallel
ctest --test-dir cpp/build-debug --output-on-failure
```

GitHub Actions runs the Python gates plus Debug/sanitizer and Release C++
builds, CTest, and native-extension import checks.

## Scope and limitations

- The current URL requests only the first page of up to 100 active events; the
  scanner does not claim complete market coverage.
- Polling is 30-second HTTP snapshotting, not websocket or order-book data.
- The rule does not model bids/asks, depth, partial fills, fees, slippage,
  inventory, settlement, latency, or whether short/sell legs are available.
- A flagged row is a pricing-deviation observation for manual analysis, not an
  executable trade, risk-free arbitrage, financial advice, or profitability
  evidence.
- API availability, response shape, access, and platform/jurisdiction rules can
  change; operators are responsible for current compliance.

## Project layout

- `src/main.py` — polling, validation, Python check, deduplication, CSV output
- `cpp/` — C++20 engine, pybind11 module, and Release-safe CTest executable
- `tests/` — parser, pricing, boundary, and CSV tests
- `.github/workflows/ci.yml` — Python and C++ verification gates

## License

[MIT](LICENSE)
