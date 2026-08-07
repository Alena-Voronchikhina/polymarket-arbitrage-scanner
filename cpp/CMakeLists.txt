cmake_minimum_required(VERSION 3.25)
project(polymarket_arbitrage_engine
    VERSION     1.0.0
    DESCRIPTION "C++ backend for Polymarket mispricing checks"
    LANGUAGES   CXX
)

# ── Language standard ─────────────────────────────────────────────────────────
set(CMAKE_CXX_STANDARD          20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS        OFF)   # Keep builds on strict ISO C++20.

# ── Compiler warning flags ────────────────────────────────────────────────────
add_compile_options(
    -Wall
    -Wextra
    -Wpedantic
    -Wconversion
    -Wshadow
    -Wnon-virtual-dtor
    -Wold-style-cast
    -Woverloaded-virtual
    -Werror          # Treat all warnings as errors.
)

# ── Optional: Address/UB sanitizers in Debug builds ──────────────────────────
option(ENABLE_SANITIZERS "Enable ASan + UBSan (Debug only)" ON)
if(ENABLE_SANITIZERS AND CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
    add_link_options(   -fsanitize=address,undefined)
endif()

# ── Core library (no direct Python dependency) ───────────────────────────────
add_library(arbitrage_core STATIC
    src/engine.cpp
)
# Required so the static archive can link into the pybind11 shared module.
set_property(TARGET arbitrage_core PROPERTY POSITION_INDEPENDENT_CODE ON)
target_include_directories(arbitrage_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

# ── pybind11 (fetched during configure) ──────────────────────────────────────
include(FetchContent)
FetchContent_Declare(
    pybind11
    GIT_REPOSITORY https://github.com/pybind/pybind11.git
    GIT_TAG        v2.13.1
)
FetchContent_MakeAvailable(pybind11)

# ── Python extension module ───────────────────────────────────────────────────
pybind11_add_module(arbitrage_engine src/bindings.cpp)
target_link_libraries(arbitrage_engine PRIVATE arbitrage_core)

# ── Tests ─────────────────────────────────────────────────────────────────────
enable_testing()

add_executable(test_engine tests/test_engine.cpp)
target_link_libraries(test_engine PRIVATE arbitrage_core)

add_test(NAME ArbitrageEngineTests COMMAND test_engine)

# Optional style/static analysis targets.
find_program(CLANG_FORMAT_BIN clang-format)
if(CLANG_FORMAT_BIN)
    set(CPP_STYLE_FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/include/arbitrage/engine.hpp
        ${CMAKE_CURRENT_SOURCE_DIR}/src/engine.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/src/bindings.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_engine.cpp
    )

    add_custom_target(format-check
        COMMAND ${CLANG_FORMAT_BIN} --dry-run --Werror ${CPP_STYLE_FILES}
        COMMENT "Running clang-format style check"
        VERBATIM
    )
endif()

find_program(CLANG_TIDY_BIN clang-tidy)
if(CLANG_TIDY_BIN)
    add_custom_target(tidy-check
        COMMAND ${CLANG_TIDY_BIN}
                -p ${CMAKE_BINARY_DIR}
                ${CMAKE_CURRENT_SOURCE_DIR}/src/engine.cpp
                ${CMAKE_CURRENT_SOURCE_DIR}/src/bindings.cpp
                ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_engine.cpp
        COMMENT "Running clang-tidy static analysis"
        VERBATIM
    )
endif()
