/**
 * @file test_framework.h
 * @brief Minimal dependency-free test harness.
 *
 * Provides TEST_CASE registration, CHECK/CHECK_EQ assertions and a runner.
 * No external test library required — keeps the suite buildable anywhere the
 * main project builds.
 */

#ifndef WONIUNOTE_TESTS_TEST_FRAMEWORK_H
#define WONIUNOTE_TESTS_TEST_FRAMEWORK_H

#include <functional>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace woniutest {

struct TestCase {
    std::string name;
    std::function<void()> fn;
};

inline std::vector<TestCase>& registry() {
    static std::vector<TestCase> cases;
    return cases;
}

// Per-run counters.
inline int& failureCount() { static int f = 0; return f; }
inline int& checkCount()   { static int c = 0; return c; }

struct Registrar {
    Registrar(const std::string& name, std::function<void()> fn) {
        registry().push_back({name, std::move(fn)});
    }
};

inline void reportFailure(const std::string& expr,
                          const char* file, int line,
                          const std::string& detail = "") {
    failureCount()++;
    std::cerr << "  [FAIL] " << file << ":" << line << "  " << expr;
    if (!detail.empty()) std::cerr << "  (" << detail << ")";
    std::cerr << "\n";
}

inline int runAll() {
    int passed = 0;
    for (auto& tc : registry()) {
        int before = failureCount();
        std::cout << "[ RUN  ] " << tc.name << "\n";
        try {
            tc.fn();
        } catch (const std::exception& e) {
            reportFailure("exception thrown", __FILE__, __LINE__, e.what());
        } catch (...) {
            reportFailure("unknown exception thrown", __FILE__, __LINE__);
        }
        if (failureCount() == before) {
            std::cout << "[  OK  ] " << tc.name << "\n";
            passed++;
        } else {
            std::cout << "[ FAIL ] " << tc.name << "\n";
        }
    }
    std::cout << "\n==== " << passed << "/" << registry().size()
              << " test cases passed, " << checkCount() << " checks, "
              << failureCount() << " failures ====\n";
    return failureCount() == 0 ? 0 : 1;
}

} // namespace woniutest

#define TEST_CASE(name)                                                        \
    static void name();                                                        \
    static woniutest::Registrar registrar_##name(#name, name);                 \
    static void name()

#define CHECK(cond)                                                            \
    do {                                                                       \
        woniutest::checkCount()++;                                             \
        if (!(cond)) {                                                         \
            woniutest::reportFailure(#cond, __FILE__, __LINE__);               \
        }                                                                      \
    } while (0)

#define CHECK_EQ(a, b)                                                         \
    do {                                                                       \
        woniutest::checkCount()++;                                             \
        auto _va = (a);                                                        \
        auto _vb = (b);                                                        \
        if (!(_va == _vb)) {                                                   \
            std::ostringstream _oss;                                           \
            _oss << "got '" << _va << "' expected '" << _vb << "'";            \
            woniutest::reportFailure(#a " == " #b, __FILE__, __LINE__, _oss.str()); \
        }                                                                      \
    } while (0)

#endif // WONIUNOTE_TESTS_TEST_FRAMEWORK_H
