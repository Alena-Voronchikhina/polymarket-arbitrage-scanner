/**
 * @file test_engine.cpp
 * @brief Assertion-based tests for ArbitrageEngine.
 *
 * Small test suite built on plain assert().
 */

#include "arbitrage/engine.hpp"

#include <cassert>
#include <cmath>
#include <iostream>
#include <stdexcept>

using namespace polymarket;

// ── Helpers ───────────────────────────────────────────────────────────────────

static constexpr double kEps = 1e-12;

static bool near(double a, double b) noexcept
{
    return std::abs(a - b) < kEps;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

static void test_fair_market_not_flagged()
{
    // Market sums to 1.0, so it should not be flagged.
    ArbitrageEngine engine;
    const Market m{"Will X happen?", {0.60, 0.40}};
    assert(!engine.evaluate(m).has_value());
}

static void test_mispriced_market_flagged()
{
    // 0.60 + 0.45 = 1.05, so this should cross the default 0.02 threshold.
    ArbitrageEngine engine;
    const Market m{"Will Y happen?", {0.60, 0.45}};
    const auto opp = engine.evaluate(m);
    assert(opp.has_value());
    assert(opp->question == "Will Y happen?");
    assert(near(opp->price_sum, 1.05));
    assert(near(opp->spread, 0.15));
}

static void test_kahan_vs_naive_divergence()
{
    // Simple stress case: sum N copies of (1.0 / N).
    // In exact arithmetic this should equal 1.0.
    // We check that this fair-by-construction market is not flagged.
    constexpr int N = 100;
    std::vector<double> prices(static_cast<std::size_t>(N), 1.0 / N);

    ArbitrageEngine engine;
    const Market m{"Kahan stress test", prices};

    // A fair market should stay inside the default threshold.
    assert(!engine.evaluate(m).has_value());
}

static void test_scan_returns_only_mispriced()
{
    const ArbitrageEngine engine;
    const std::vector<Market> markets = {
        {"Fair binary", {0.50, 0.50}},                    // sum = 1.00 — skip
        {"Mispriced multi", {0.40, 0.40, 0.30}},          // sum = 1.10 — flag
        {"Fair multi",       {0.25, 0.25, 0.25, 0.25}}, // sum = 1.00 — skip
        {"Mispriced binary", {0.60, 0.45}},               // sum = 1.05 — flag
    };

    const auto opps = engine.scan(markets);
    assert(opps.size() == 2);
    assert(opps[0].question == "Mispriced multi");
    assert(opps[1].question == "Mispriced binary");
}

static void test_insufficient_prices_skipped()
{
    ArbitrageEngine engine;
    // Markets with too few outcomes are skipped.
    assert(!engine.evaluate(Market{"Only one price", {0.99}}).has_value());
    assert(!engine.evaluate(Market{"Empty market",   {}    }).has_value());
}

static void test_nonfinite_prices_skipped()
{
    ArbitrageEngine engine;
    // NaN or Inf usually means bad input; these should never be flagged.
    assert(
        !engine
             .evaluate(Market{"NaN price", {0.5, std::numeric_limits<double>::quiet_NaN()}})
             .has_value()
    );
    assert(
        !engine.evaluate(Market{"Inf price", {0.5, std::numeric_limits<double>::infinity()}})
             .has_value()
    );
}

static void test_custom_threshold()
{
    // With a tighter threshold of 0.01, sum=1.015 should be flagged.
    // With the default 0.02, the same market should pass.
    const Market m{"Near miss", {0.50, 0.515}}; // sum = 1.015

    assert(!ArbitrageEngine{0.02}.evaluate(m).has_value());
    assert( ArbitrageEngine{0.01}.evaluate(m).has_value());
}

static void test_invalid_threshold_throws()
{
    bool threw = false;
    try {
        ArbitrageEngine bad{-0.01};
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    assert(threw);

    threw = false;
    try {
        ArbitrageEngine bad{1.5};
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    assert(threw);
}

// ── Entry point ───────────────────────────────────────────────────────────────

int main()
{
    test_fair_market_not_flagged();
    test_mispriced_market_flagged();
    test_kahan_vs_naive_divergence();
    test_scan_returns_only_mispriced();
    test_insufficient_prices_skipped();
    test_nonfinite_prices_skipped();
    test_custom_threshold();
    test_invalid_threshold_throws();

    std::cout << "All ArbitrageEngine tests passed.\n";
    return 0;
}
