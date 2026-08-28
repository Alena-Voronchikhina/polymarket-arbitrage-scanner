#include "arbitrage/engine.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace polymarket {

PricingEngine::PricingEngine(double threshold) : threshold_{threshold} {
    if (!std::isfinite(threshold) || threshold <= 0.0 || threshold >= 1.0) {
        throw std::invalid_argument{"PricingEngine threshold must be finite and in (0, 1)"};
    }
}

double PricingEngine::kahan_sum(std::span<const double> values) noexcept {
    double sum = 0.0;
    double compensation = 0.0;
    for (const double value : values) {
        const double corrected = value - compensation;
        const double updated = sum + corrected;
        compensation = (updated - sum) - corrected;
        sum = updated;
    }
    return sum;
}

double PricingEngine::price_range_of(std::span<const double> values) noexcept {
    const auto [low, high] = std::ranges::minmax_element(values);
    return *high - *low;
}

std::optional<PricingDeviation> PricingEngine::evaluate(const Market &market) const {
    if (static_cast<int>(market.prices.size()) < kMinOutcomes) {
        return std::nullopt;
    }
    for (const double price : market.prices) {
        if (!std::isfinite(price) || price < 0.0 || price > 1.0) {
            return std::nullopt;
        }
    }

    const double total = kahan_sum(market.prices);
    const double sum_deviation = total - 1.0;
    if (std::abs(sum_deviation) <= threshold_ + kComparisonEpsilon) {
        return std::nullopt;
    }

    return PricingDeviation{
        .question = market.question,
        .prices = market.prices,
        .price_sum = total,
        .sum_deviation = sum_deviation,
        .price_range = price_range_of(market.prices),
    };
}

std::vector<PricingDeviation> PricingEngine::scan(std::span<const Market> markets) const {
    std::vector<PricingDeviation> deviations;
    deviations.reserve(markets.size());
    for (const Market &market : markets) {
        if (auto deviation = evaluate(market); deviation.has_value()) {
            deviations.push_back(std::move(*deviation));
        }
    }
    return deviations;
}

} // namespace polymarket
