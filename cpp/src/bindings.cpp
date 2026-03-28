/**
 * @file bindings.cpp
 * @brief pybind11 bindings that expose the C++ engine to Python.
 *
 * This build produces `arbitrage_engine.so` (Linux/macOS) or
 * `arbitrage_engine.pyd` (Windows), importable directly from Python:
 *
 *   import arbitrage_engine as ae
 *   engine = ae.ArbitrageEngine(threshold=0.02)
 *   opps   = engine.scan([ae.Market("Will X happen?", [0.60, 0.45])])
 */

#include "arbitrage/engine.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>       // Auto-converts std::vector and std::optional.

namespace py = pybind11;

PYBIND11_MODULE(arbitrage_engine, m)
{
    m.doc() = "Python bindings for the C++ mispricing engine.";

    // ── Market ────────────────────────────────────────────────────────────────
    py::class_<polymarket::Market>(m, "Market")
        .def(
            py::init<std::string, std::vector<double>>(),
            py::arg("question"),
            py::arg("prices"),
            "Create a market from a question and outcome prices."
        )
        .def_readwrite("question", &polymarket::Market::question)
        .def_readwrite("prices", &polymarket::Market::prices)
        .def("__repr__", [](const polymarket::Market& mk) {
            return "<Market question=" + mk.question +
                   " prices_len=" + std::to_string(mk.prices.size()) + ">";
        });

    // ── ArbitrageOpportunity ──────────────────────────────────────────────────
    py::class_<polymarket::ArbitrageOpportunity>(m, "ArbitrageOpportunity")
        .def_readonly("question", &polymarket::ArbitrageOpportunity::question)
        .def_readonly("prices", &polymarket::ArbitrageOpportunity::prices)
        .def_readonly("price_sum", &polymarket::ArbitrageOpportunity::price_sum)
        .def_readonly("spread", &polymarket::ArbitrageOpportunity::spread)
        .def("__repr__", [](const polymarket::ArbitrageOpportunity& op) {
            return "<ArbitrageOpportunity question=" + op.question +
                   " price_sum=" + std::to_string(op.price_sum) +
                   " spread=" + std::to_string(op.spread) + ">";
        });

    // ── ArbitrageEngine ───────────────────────────────────────────────────────
    py::class_<polymarket::ArbitrageEngine>(m, "ArbitrageEngine")
        .def(
            py::init<double>(),
            py::arg("threshold") = polymarket::ArbitrageEngine::kDefaultThreshold,
            "Create an engine with a mispricing threshold (default 0.02)."
        )
        .def_property_readonly("threshold", &polymarket::ArbitrageEngine::threshold)
        .def(
            "evaluate",
            &polymarket::ArbitrageEngine::evaluate,
            py::arg("market"),
            "Evaluate one market and return ArbitrageOpportunity or None."
        )
        .def(
            "scan",
            [](const polymarket::ArbitrageEngine& eng,
               const std::vector<polymarket::Market>& markets) {
                // pybind converts Python list to std::vector for this call.
                return eng.scan(markets);
            },
            py::arg("markets"),
            "Evaluate a list of markets and return all opportunities."
        );

    // Mirror core constants at module scope.
    m.attr("DEFAULT_THRESHOLD") = polymarket::ArbitrageEngine::kDefaultThreshold;
    m.attr("MIN_OUTCOMES") = polymarket::ArbitrageEngine::kMinOutcomes;
}
