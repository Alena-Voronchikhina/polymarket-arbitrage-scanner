# Polymarket Arbitrage Scanner

A scanner that polls active Polymarket markets and flags potential mispricing.

It reads event data, parses each market's outcome prices, and flags markets where the implied probabilities drift far enough from 1.0 to be worth a closer look.

## Detection Logic

For each market with prices $p_1, p_2, ..., p_n$:

$$
\left|\sum_{i=1}^{n} p_i - 1.0\right| > 0.02
$$

If this condition holds, the market is logged as an opportunity with:
- `question`
- `prices`
- `price_sum`
- `spread` (`max(prices) - min(prices)`)

The scanner deduplicates entries with a rounded key and appends new opportunities to `opportunities.csv`.

This is a signal generator, not an execution bot. It helps surface markets that deserve manual review.

## How To Run

### 1) Environment setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run the scanner

```bash
python -m src.main
```

The process is continuous (polls every 30 seconds). Stop with `Ctrl+C`.

### Example runtime output

```text
[backend] C++ module not found; using Python fallback.
Loaded 0 prior opportunities from opportunities.csv
New opportunities this cycle: 0
Waiting 30s...
```

When opportunities are found, output includes lines like:

```text
[opportunity] <market question>
    prices=[...]  sum=1.050000  spread=0.150000
```

## Why I Added a C++ Backend

This project started as a Python scanner that polls Polymarket and flags potential mispricing. Once the first version was working, I looked at which step most directly controls whether a market gets flagged. The threshold check stood out because it is the core decision point: when the total price is close to 1.0, small numerical differences can matter.

That led me to dig deeper into floating-point summation and threshold comparisons. I learned that floating-point addition can accumulate rounding error, which matters when a decision depends on whether a total lands just above or below a threshold. To make that step more stable, I added a C++ backend for the pricing check and used Kahan-compensated summation.

The project now combines Python and C++: Python handles API I/O and persistence, while C++ handles the threshold-sensitive pricing check.

## Build And Use The C++ Extension

```bash
cd cpp/build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --parallel
cp arbitrage_engine*.so ../../src/
```

Then run `python -m src.main` again. On startup you should see:

```text
[backend] C++ ArbitrageEngine loaded (Kahan summation active).
```

## Architecture At A Glance

- `src/main.py`: polling loop, API fetch, parsing, opportunity detection, CSV persistence.
- `cpp/include/arbitrage/engine.hpp`: core engine interface.
- `cpp/src/engine.cpp`: Kahan-based evaluation and batch scanning.
- `cpp/src/bindings.cpp`: pybind11 bridge exposing C++ types to Python.
- `cpp/tests/test_engine.cpp`: C++ unit tests for edge cases and threshold behavior.

## Development And Verification

### Python quality gates

```bash
ruff check src tests
ruff format --check src tests
mypy --strict src
python -m pytest
```

### C++ build and tests

```bash
cd cpp/build
cmake .. -DCMAKE_BUILD_TYPE=Debug
cmake --build . --parallel
ctest --output-on-failure
```

### Optional C++ style/static-analysis targets

```bash
cmake --build . --target format-check
cmake --build . --target tidy-check
```

## What This Project Demonstrates

- Market-data ingestion and defensive parsing.
- Threshold-based mispricing screening.
- Deterministic deduplication and CSV persistence.
- Python plus native C++ extension integration.
- Strict linting, formatting, typing, and test gating.

## License

MIT
