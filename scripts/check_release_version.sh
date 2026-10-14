#!/usr/bin/env bash
#
# Release version consistency check (iteration 20 / Epic 20.5).
#
# The release version is declared once, in backend_cpp/CMakeLists.txt
# (`project(woniunote_backend VERSION X.Y.Z ...)`). Every other place that
# carries the version must agree with it:
#   - frontend/package.json
#   - backend_cpp/vcpkg.json
# The C++ sources use the WONIUNOTE_VERSION macro (injected by CMake) and must
# not contain version literals, so a bump touches exactly one line plus the two
# manifests.
#
# Run from anywhere:  bash scripts/check_release_version.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

cmake_version="$(sed -n 's/^project([^)]* VERSION \([0-9][0-9.]*\).*/\1/p' backend_cpp/CMakeLists.txt | head -1)"
if [ -z "$cmake_version" ]; then
  echo "ERROR: cannot read the project VERSION from backend_cpp/CMakeLists.txt" >&2
  exit 1
fi

pkg_version="$(python3 -c "import json; print(json.load(open('frontend/package.json'))['version'])")"
manifest_version="$(python3 -c "import json; print(json.load(open('backend_cpp/vcpkg.json'))['version'])")"

fail=0
check() { # <label> <value>
  if [ "$2" != "$cmake_version" ]; then
    echo "ERROR: $1 version '$2' != CMakeLists project VERSION '$cmake_version'" >&2
    fail=1
  fi
}
check "frontend/package.json" "$pkg_version"
check "backend_cpp/vcpkg.json" "$manifest_version"

# Guard against re-introducing hardcoded versions in the C++ sources.
literal_hits="$(grep -nE '"[0-9]+\.[0-9]+\.[0-9]+(-cpp)?"' \
  backend_cpp/main.cc backend_cpp/controllers/SystemController.cc || true)"
if [ -n "$literal_hits" ]; then
  echo "ERROR: hardcoded version literal in C++ sources; use the WONIUNOTE_VERSION macro:" >&2
  echo "$literal_hits" >&2
  fail=1
fi

if [ "$fail" != "0" ]; then
  exit 1
fi
echo "Release version OK: ${cmake_version} (CMakeLists == package.json == vcpkg.json; no C++ literals)"
