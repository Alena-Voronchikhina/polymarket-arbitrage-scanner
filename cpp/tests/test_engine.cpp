#include "arbitrage/engine.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

using namespace polymarket;

namespace {

constexpr double kEpsilon = 1e-12;

void require(bool condition, const std::string &message) {
    if (!condition) {
        throw std::runtime_error{message};
    }
}

bool near(double left, double right) noexcept {
    return std::abs(left - right) < kEpsilon;
}

void test_fair_and_deviating_markets() {
    const PricingEngine engine;
    require(!engine.evaluate(Market{"Fair", {0.60, 0.40}}), "fair market flagged");

    const auto deviation = engine.evaluate(Market{"Deviation", {0.60, 0.45}});
    require(deviation.has_value(), "deviation not flagged");
    require(near(deviation->price_sum, 1.05), "wrong price sum");
    require(near(deviation->sum_deviation, 0.05), "wrong sum deviation");
    require(near(deviation->price_range, 0.15), "wrong price range");
}

void test_zero_price_is_valid() {
    const PricingEngine engine;
    require(!engine.evaluate(Market{"Zero and one", {0.0, 1.0}}), "valid zero was rejected");
    const auto deviation = engine.evaluate(Market{"Zero included", {0.0, 0.40}});
    require(deviation.has_value(), "zero-containing deviation not flagged");
    require(near(deviation->price_range, 0.40), "zero was omitted from price range");
}

void test_invalid_prices_are_rejected() {
    const PricingEngine engine;
    require(!engine.evaluate(Market{"NaN", {0.5, std::numeric_limits<double>::quiet_NaN()}}),
            "NaN accepted");
    require(!engine.evaluate(Market{"Inf", {0.5, std::numeric_limits<double>::infinity()}}),
            "infinity accepted");
    require(!engine.evaluate(Market{"Negative", {-0.1, 0.5}}), "negative price accepted");
    require(!engine.evaluate(Market{"Above one", {0.5, 1.1}}), "price above one accepted");
    require(!engine.evaluate(Market{"Single", {0.5}}), "single outcome accepted");
}

void test_scan_and_threshold() {
    const PricingEngine engine;
    const std::vector<Market> markets{{"Fair", {0.5, 0.5}}, {"High", {0.7, 0.4}},
                                      {"Low", {0.3, 0.4}}};
    const auto deviations = engine.scan(markets);
    require(deviations.size() == 2, "scan returned wrong count");
    require(!PricingEngine{0.02}.evaluate(Market{"Boundary", {0.50, 0.52}}),
            "floating-point boundary was flagged");
    require(!PricingEngine{0.02}.evaluate(Market{"Near", {0.50, 0.515}}),
            "default threshold flagged near value");
    require(PricingEngine{0.01}.evaluate(Market{"Near", {0.50, 0.515}}).has_value(),
            "custom threshold missed deviation");
}

void test_invalid_thresholds_throw() {
    for (const double threshold : {-0.01, 0.0, 1.0, 1.5,
                                   std::numeric_limits<double>::infinity(),
                                   std::numeric_limits<double>::quiet_NaN()}) {
        bool threw = false;
        try {
            const PricingEngine invalid{threshold};
        } catch (const std::invalid_argument &) {
            threw = true;
        }
        require(threw, "invalid threshold accepted");
    }
}

} // namespace

int main() {
    try {
        test_fair_and_deviating_markets();
        test_zero_price_is_valid();
        test_invalid_prices_are_rejected();
        test_scan_and_threshold();
        test_invalid_thresholds_throw();
    } catch (const std::exception &error) {
        std::cerr << "PricingEngine test failure: " << error.what() << '\n';
        return 1;
    }
    std::cout << "PricingEngine tests passed.\n";
    return 0;
}
