# Backend Unit Tests

Lightweight, dependency-free unit tests for the WoniuNote C++ backend. No
external test library (gtest/catch2) is required — a minimal header-only
harness lives in `test_framework.h`, so the suite builds anywhere the main
project builds.

## What is covered

- `test_security.cc` — `woniunote::Security`:
  - bcrypt-style password hash + verify round-trip
  - wrong password / garbage hash rejection
  - legacy MD5 detection and verification (migration compatibility)
  - JWT access/refresh token round-trip, tampered/garbage token rejection

These tests exercise pure logic and do **not** require a running MySQL/Redis.

## Structure

```
tests/
├── CMakeLists.txt        # test target (linked against core/ sources)
├── test_framework.h      # minimal TEST_CASE / CHECK / CHECK_EQ harness
├── test_main.cc          # runner entry point
└── test_security.cc      # Security unit tests
```

## Build & run

```bash
cd backend_cpp
cmake -S . -B build -DBUILD_TESTING=ON \
  -DCMAKE_TOOLCHAIN_FILE=~/vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build build --target woniunote_tests -j8

# Run directly
./build/tests/woniunote_tests

# Or via ctest
cd build && ctest --output-on-failure
```

## Adding tests

1. Create `test_<area>.cc` and `#include "test_framework.h"`.
2. Write cases with `TEST_CASE(name) { CHECK(...); CHECK_EQ(a, b); }`.
3. Add the file (and any required `core/` sources) to `tests/CMakeLists.txt`.

Controller/endpoint tests that need a database should use a dedicated test
schema and Drogon's async DB client; keep DB-dependent suites separate from
this pure-logic suite so the latter always runs.
