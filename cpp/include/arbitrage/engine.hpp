/**
 * @file engine.hpp
 * @brief C++ backend for threshold-based mispricing checks.
 *
 * This header defines the market types and engine used for the
 * threshold-sensitive pricing check.
 *
 * It uses Kahan-compensated summation to keep totals more stable near
 * the threshold when floating-point rounding is involved.
 */

#pragma once

#include <optional>
#include <span>
#include <string>
#include <vector>

namespace polymarket {

// ── Public data types ────────────────────────────────────────────────────────

/**
 * @brief One Polymarket sub-market: a question and its outcome probabilities.
 *
 * Each price represents one outcome's implied probability.
 * In a well-priced market, outcome prices should add up to about 1.0.
 */
struct Market {
    std::string          question; ///< Human-readable market question.
    std::vector<double>  prices;   ///< Outcome prices, one per outcome.
};

/**
 * @brief An identified arbitrage opportunity.
 *
 * Produced by ArbitrageEngine::evaluate() when the price total falls
 * outside the configured mispricing threshold.
 */
struct ArbitrageOpportunity {
    std::string         question;   ///< Market question (copied from Market).
    std::vector<double> prices;     ///< Outcome prices at detection time.
    double              price_sum;  ///< Kahan-compensated sum of prices.
    double              spread;     ///< max(prices) − min(prices).
};

// ── Engine ───────────────────────────────────────────────────────────────────

/**
 * @brief Stateless engine that evaluates markets for potential mispricing.
 *
 * The engine object itself is safe to call from multiple threads after
 * construction because public methods do not mutate internal state.
 *
 * ### Why Kahan summation?
 * Plain floating-point addition can drift as values are accumulated.
 * Kahan keeps a small compensation term for lost low-order bits, which
 * makes threshold checks more stable when totals are close to 1.0.
 */
class ArbitrageEngine {
public:
    /// Default mispricing threshold (|Σ prices − 1| must exceed this).
    static constexpr double kDefaultThreshold = 0.02;

    /// Minimum number of outcomes required to evaluate a market.
    static constexpr int kMinOutcomes = 2;

    /**
     * @brief Construct an engine with the given mispricing threshold.
     * @param threshold  Must be positive and less than 1.0.
     * @throws std::invalid_argument if threshold is out of range.
     */
    explicit ArbitrageEngine(double threshold = kDefaultThreshold);

    // Copyable and movable — all state is a single double.
    ArbitrageEngine(const ArbitrageEngine&)            = default;
    ArbitrageEngine& operator=(const ArbitrageEngine&) = default;
    ArbitrageEngine(ArbitrageEngine&&)                 = default;
    ArbitrageEngine& operator=(ArbitrageEngine&&)      = default;
    ~ArbitrageEngine()                                 = default;

    /**
     * @brief Evaluate a single market for mispricing.
     *
     * @param market  The market to evaluate. Must have at least
     *                kMinOutcomes prices; returns std::nullopt otherwise.
     * @return  ArbitrageOpportunity when the total price differs from 1.0
     *          by more than the configured threshold; std::nullopt if the
     *          market appears fairly priced or has insufficient data.
     */
    [[nodiscard]] std::optional<ArbitrageOpportunity>
    evaluate(const Market& market) const noexcept;

    /**
     * @brief Scan a batch of markets and return all opportunities found.
     *
     * Evaluates each market in the span. Markets that are fairly priced
     * or missing enough data are skipped.
     *
     * @param markets  View over a contiguous range of Market objects.
     * @return  Vector of all detected ArbitrageOpportunity values.
     */
    [[nodiscard]] std::vector<ArbitrageOpportunity>
    scan(std::span<const Market> markets) const;

    /// Returns the configured mispricing threshold.
    [[nodiscard]] double threshold() const noexcept { return threshold_; }

private:
    double threshold_;

    /**
     * @brief Kahan-compensated sum over a span of doubles.
     *
     * Keeps a compensation value for low-order bits that would otherwise
     * be lost to rounding during repeated addition.
     *
     * @param values  Non-empty span of finite doubles.
     * @return  Sum that is typically more stable than plain accumulation.
     */
    [[nodiscard]] static double
    kahan_sum(std::span<const double> values) noexcept;

    /**
     * @brief Compute spread = max − min over a span of doubles.
     * @param values  Non-empty span.
     */
    [[nodiscard]] static double
    spread_of(std::span<const double> values) noexcept;
};

} // namespace polymarket
