#!/usr/bin/env bash
#
# Static analysis gate for the WoniuNote C++ backend (cppcheck).
#
# Usage:
#   bash backend_cpp/scripts/run_cppcheck.sh
#
# Runs the exact invocation used by the `backend-static-analysis` CI job, so a
# local run and CI cannot drift apart (iteration 20 / Epic 20.1).
#
# Why the -D flag: main.cc and SystemController.cc report the release version
# through the WONIUNOTE_VERSION macro, which CMake injects via
# add_compile_definitions(). cppcheck has no build context, so without the
# define every use is reported as `unknownMacro` — a blocking finding under
# --error-exitcode=1. The value is read from CMakeLists.txt (the single release
# version source) so this script never hardcodes a version.
#
# The baseline is clean, so any newly-introduced warning/style/performance/
# portability issue fails the run. Informational branch-limit notes are
# suppressed (not real findings).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_DIR}"

if ! command -v cppcheck >/dev/null 2>&1; then
  echo "ERROR: cppcheck not found. Install it first (apt-get install cppcheck / brew install cppcheck)." >&2
  exit 1
fi

VERSION="$(sed -n 's/^project([^)]* VERSION \([0-9][0-9.]*\).*/\1/p' CMakeLists.txt | head -1)"
if [ -z "${VERSION}" ]; then
  echo "ERROR: cannot read the project VERSION from backend_cpp/CMakeLists.txt" >&2
  exit 1
fi

echo "==> cppcheck (WONIUNOTE_VERSION=\"${VERSION}\")"
cppcheck --enable=warning,style,performance,portability \
  --std=c++17 --language=c++ --inline-suppr \
  --suppress=missingIncludeSystem \
  --suppress=normalCheckLevelMaxBranches \
  -DWONIUNOTE_VERSION="\"${VERSION}\"" \
  --error-exitcode=1 \
  -I core -I controllers -I filters -I models -I services \
  controllers core filters models services main.cc
echo "==> cppcheck clean"
