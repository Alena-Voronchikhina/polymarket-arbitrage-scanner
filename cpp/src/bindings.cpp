#include "arbitrage/engine.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

PYBIND11_MODULE(pricing_engine, module) {
    module.doc() = "Python bindings for sum-to-one pricing-deviation checks.";

    py::class_<polymarket::Market>(module, "Market")
        .def(py::init<std::string, std::vector<double>>(), py::arg("question"),
             py::arg("prices"))
        .def_readwrite("question", &polymarket::Market::question)
        .def_readwrite("prices", &polymarket::Market::prices);

    py::class_<polymarket::PricingDeviation>(module, "PricingDeviation")
        .def_readonly("question", &polymarket::PricingDeviation::question)
        .def_readonly("prices", &polymarket::PricingDeviation::prices)
        .def_readonly("price_sum", &polymarket::PricingDeviation::price_sum)
        .def_readonly("sum_deviation", &polymarket::PricingDeviation::sum_deviation)
        .def_readonly("price_range", &polymarket::PricingDeviation::price_range);

    py::class_<polymarket::PricingEngine>(module, "PricingEngine")
        .def(py::init<double>(), py::arg("threshold") = polymarket::PricingEngine::kDefaultThreshold)
        .def_property_readonly("threshold", &polymarket::PricingEngine::threshold)
        .def("evaluate", &polymarket::PricingEngine::evaluate, py::arg("market"))
        .def("scan", [](const polymarket::PricingEngine &engine,
                        const std::vector<polymarket::Market> &markets) {
            return engine.scan(markets);
        });

    module.attr("DEFAULT_THRESHOLD") = polymarket::PricingEngine::kDefaultThreshold;
    module.attr("MIN_OUTCOMES") = polymarket::PricingEngine::kMinOutcomes;
}
