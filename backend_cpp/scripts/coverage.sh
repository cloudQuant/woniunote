#!/usr/bin/env bash
#
# Coverage report for the WoniuNote C++ backend (gcov + lcov + genhtml).
#
# Usage:
#   bash backend_cpp/scripts/coverage.sh [extra cmake args...]
#
# Steps:
#   1. configure a dedicated instrumented build dir with
#      -DENABLE_COVERAGE=ON -DBUILD_TESTING=ON (kept separate from the regular
#      Release build in build/ so the normal workflow is untouched)
#   2. build every target and run the ctest suite
#   3. capture counters with lcov and render HTML into
#      backend_cpp/build/coverage-report/
#
# Environment overrides:
#   COVERAGE_BUILD_DIR  instrumented build dir (default: <backend>/build-coverage)
#   COVERAGE_JOBS       parallel build jobs (default: CPU count)
#   COVERAGE_KEEP_GOALS set to 1 to keep previous .gcda counters (default: wipe)
#
# Note: lcov/genhtml are required. The normal build (cmake -DBUILD_TESTING=ON &&
# ctest) does not need them, so this script is purely opt-in.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

BUILD_DIR="${COVERAGE_BUILD_DIR:-${BACKEND_DIR}/build-coverage}"
REPORT_DIR="${BACKEND_DIR}/build/coverage-report"
INFO_RAW="${REPORT_DIR}/coverage.raw.info"
INFO_FILE="${REPORT_DIR}/coverage.info"

# ---------------------------------------------------------------------------
# 1. Tool check (fail fast, before spending minutes on a build)
# ---------------------------------------------------------------------------
missing=""
for tool in lcov genhtml gcov; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
        missing="${missing}${missing:+, }${tool}"
    fi
done

if [ -n "${missing}" ]; then
    cat >&2 <<EOF
ERROR: missing required coverage tool(s): ${missing}

Install them first, e.g.:
  macOS:         brew install lcov
  Debian/Ubuntu: sudo apt-get install -y lcov
  Fedora/RHEL:   sudo dnf install -y lcov
(gcov ships with GCC; on macOS it comes with the Xcode command line tools.)

These tools are only needed for this script -- the regular build and
'ctest' gate do not require them.
EOF
    exit 1
fi

# ---------------------------------------------------------------------------
# 2. Configure
# ---------------------------------------------------------------------------
if [ -n "${COVERAGE_JOBS:-}" ]; then
    JOBS="${COVERAGE_JOBS}"
elif command -v nproc >/dev/null 2>&1; then
    JOBS="$(nproc)"
else
    JOBS="$(sysctl -n hw.ncpu 2>/dev/null || echo 4)"
fi

cmake_args=(
    -S "${BACKEND_DIR}"
    -B "${BUILD_DIR}"
    -DBUILD_TESTING=ON
    -DENABLE_COVERAGE=ON
    -DCMAKE_BUILD_TYPE=Debug
)

# Reuse the vcpkg toolchain of the main build when available (vcpkg mode).
if [ "${USE_SYSTEM_LIBS:-OFF}" != "ON" ]; then
    vcpkg_toolchain="${VCPKG_ROOT:-${HOME}/vcpkg}/scripts/buildsystems/vcpkg.cmake"
    if [ -f "${vcpkg_toolchain}" ]; then
        cmake_args+=("-DCMAKE_TOOLCHAIN_FILE=${vcpkg_toolchain}")
    fi
fi

echo "==> Configuring instrumented build in ${BUILD_DIR}"
cmake "${cmake_args[@]}" "$@"

# Stale counters would skew the report (e.g. after deleting a test).
if [ "${COVERAGE_KEEP_GOALS:-0}" != "1" ]; then
    find "${BUILD_DIR}" -name '*.gcda' -delete 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# 3. Build + test
# ---------------------------------------------------------------------------
echo "==> Building (${JOBS} jobs)"
cmake --build "${BUILD_DIR}" -j"${JOBS}"

echo "==> Running ctest"
( cd "${BUILD_DIR}" && ctest --output-on-failure )

# ---------------------------------------------------------------------------
# 4. Capture + render
# ---------------------------------------------------------------------------
mkdir -p "${REPORT_DIR}"

echo "==> Capturing counters with lcov"
# clang's gcov emulation trips several lcov 2.x consistency checks on
# third-party headers (function begin/end lines, synthesized global ctors,
# gcov version notes). Those files are filtered out below anyway, so the
# related error classes are downgraded to warnings here.
lcov --capture \
    --directory "${BUILD_DIR}" \
    --output-file "${INFO_RAW}" \
    --ignore-errors unsupported,empty,source,mismatch,inconsistent,format,version,range,unused,count,corrupt

echo "==> Filtering out system / dependency / test code"
lcov --remove "${INFO_RAW}" \
    '/usr/*' \
    '*/vcpkg_installed/*' \
    '*/third_party/*' \
    '*/tests/*' \
    '*/build-coverage/*' \
    --output-file "${INFO_FILE}" \
    --ignore-errors unused,empty,source,mismatch,inconsistent,format,version,range

echo "==> Rendering HTML report"
# 'category' covers the UNK marker clang's gcov emulation emits; the rest are
# the same clang-vs-lcov consistency classes downgraded during capture.
genhtml "${INFO_FILE}" \
    --output-directory "${REPORT_DIR}" \
    --title "WoniuNote C++ backend coverage" \
    --legend \
    --show-details \
    --ignore-errors category,inconsistent,format,unused,empty,source,range,version,unsupported,count,corrupt,mismatch

echo
echo "==> Summary (production code only)"
lcov --summary "${INFO_FILE}" --ignore-errors empty,source || true
echo
echo "HTML report: ${REPORT_DIR}/index.html"
