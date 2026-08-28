#pragma once

#include <optional>
#include <span>
#include <string>
#include <vector>

namespace polymarket {

struct Market {
    std::string question;
    std::vector<double> prices;
};

struct PricingDeviation {
    std::string question;
    std::vector<double> prices;
    double price_sum;
    double sum_deviation;
    double price_range;
};

class PricingEngine {
public:
    static constexpr double kDefaultThreshold = 0.02;
    static constexpr double kComparisonEpsilon = 1e-12;
    static constexpr int kMinOutcomes = 2;

    explicit PricingEngine(double threshold = kDefaultThreshold);

    [[nodiscard]] std::optional<PricingDeviation> evaluate(const Market &market) const;
    [[nodiscard]] std::vector<PricingDeviation> scan(std::span<const Market> markets) const;
    [[nodiscard]] double threshold() const noexcept { return threshold_; }

private:
    double threshold_;

    [[nodiscard]] static double kahan_sum(std::span<const double> values) noexcept;
    [[nodiscard]] static double price_range_of(std::span<const double> values) noexcept;
};

} // namespace polymarket
