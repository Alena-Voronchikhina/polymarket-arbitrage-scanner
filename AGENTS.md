# AGENTS.md

## Cursor Cloud specific instructions

This is the Polymarket Arbitrage Scanner: a Python scanner (`src/main.py`) that polls the
live Polymarket Gamma API for potential mispricing, with an optional C++/pybind11 pricing
engine (`cpp/`). See `README.md` for the full command reference; only non-obvious caveats
are captured here.

### Python (primary service)

- A virtualenv is expected at `.venv` (the update script creates it and installs deps).
  Activate it with `source .venv/bin/activate` before running commands.
- Standard quality gates (from `README.md`): `ruff check src tests`,
  `ruff format --check src tests`, `mypy --strict src`, `python -m pytest`.
- Run the scanner: `python -m src.main`. It polls the live API every 30s and only writes
  `opportunities.csv` when a market's outcome-price sum deviates from 1.0 by more than 0.02.
  Live markets are usually efficiently priced, so a clean run often reports
  `New opportunities this cycle: 0` and creates no CSV — that is expected, not a failure.
- `opportunities.csv` is a runtime output and is intentionally not committed.

### C++ engine (optional backend) — non-obvious gotchas

- Activating the C++ backend: `python -m src.main` on its own uses the Python fallback and
  prints `[backend] C++ module not found`. The compiled module is installed into `src/`, but
  `arbitrage_engine` is imported as a top-level module, so the repo root must be able to see
  it. Run with `PYTHONPATH=src python -m src.main` (or copy the built `.so` to the repo root)
  to load the C++ engine — you should then see
  `[backend] C++ ArbitrageEngine loaded (Kahan-based check active)`. Behavior is identical
  either way; only the summation path differs.
- Compiler: the default `c++` is Clang, and it builds the pybind11 shared module correctly.
  Do NOT force `g++` for the extension — GCC hits a `-fPIC` link error on the shared module
  in this environment.
- Build only the specific target, not all targets:
  - Extension (Release): `cmake .. -DCMAKE_BUILD_TYPE=Release && cmake --build . --target arbitrage_engine`,
    then `cp arbitrage_engine*.so ../../src/`.
  - Tests (Debug): `cmake .. -DCMAKE_BUILD_TYPE=Debug && cmake --build . --target test_engine && ctest --output-on-failure`.
  - Reason: building all targets in Release fails because `cpp/tests/test_engine.cpp` uses
    variables only inside `assert()`, which `NDEBUG` disables in Release, tripping
    `-Werror -Wunused-but-set-variable`. Tests therefore must be built in Debug (asserts
    active). Configuring the extension in Release and the tests in Debug in the same
    `cpp/build` dir is fine; just build the individual target you need.
- Configuring the C++ build fetches `pybind11` from GitHub via CMake `FetchContent`, so the
  first configure needs network access.
