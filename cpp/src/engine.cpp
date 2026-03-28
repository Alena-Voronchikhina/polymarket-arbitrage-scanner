/**
 * @file engine.cpp
 * @brief Mispricing checks used by the C++ backend.
 */

#include "arbitrage/engine.hpp"

#include <algorithm>   // std::ranges::minmax_element
#include <cmath>       // std::abs, std::isfinite
#include <stdexcept>   // std::invalid_argument

namespace polymarket {

// ── Construction ─────────────────────────────────────────────────────────────

ArbitrageEngine::ArbitrageEngine(double threshold)
    : threshold_{threshold}
{
    if (threshold <= 0.0 || threshold >= 1.0) {
        throw std::invalid_argument{
            "ArbitrageEngine: threshold must be in (0, 1), got " +
            std::to_string(threshold)
        };
    }
}

// ── Private helpers ───────────────────────────────────────────────────────────

double ArbitrageEngine::kahan_sum(std::span<const double> values) noexcept
{
    // Kahan summation keeps a compensation term for tiny lost bits,
    // so repeated additions stay steadier near the threshold.
    double sum          = 0.0;
    double compensation = 0.0;

    for (const double v : values) {
        const double y = v - compensation;  // Corrected addend.
        const double t = sum + y;           // sum may be much larger than y.
        compensation   = (t - sum) - y;    // Rounding residue carried forward.
        sum            = t;
    }
    return sum;
}

double ArbitrageEngine::spread_of(std::span<const double> values) noexcept
{
    const auto [lo, hi] = std::ranges::minmax_element(values);
    return *hi - *lo;
}

// ── Public interface ──────────────────────────────────────────────────────────

std::optional<ArbitrageOpportunity>
ArbitrageEngine::evaluate(const Market& market) const noexcept
{
    if (static_cast<int>(market.prices.size()) < kMinOutcomes) {
        return std::nullopt;
    }

    // Reject non-finite prices. NaN or Inf usually means bad upstream data,
    // and we do not want to flag those as real mispricing.
    for (const double p : market.prices) {
        if (!std::isfinite(p)) {
            return std::nullopt;
        }
    }

    const double total = kahan_sum(market.prices);

    if (std::abs(total - 1.0) <= threshold_) {
        return std::nullopt; // Fairly priced within tolerance.
    }

    return ArbitrageOpportunity{
        .question  = market.question,
        .prices    = market.prices,
        .price_sum = total,
        .spread    = spread_of(market.prices),
    };
}

std::vector<ArbitrageOpportunity>
ArbitrageEngine::scan(std::span<const Market> markets) const
{
    std::vector<ArbitrageOpportunity> opportunities;
    opportunities.reserve(markets.size()); // Upper bound: every market may be flagged.

    for (const Market& m : markets) {
        if (auto opp = evaluate(m); opp.has_value()) {
            opportunities.push_back(std::move(*opp));
        }
    }

    opportunities.shrink_to_fit();
    return opportunities;
}

} // namespace polymarket
