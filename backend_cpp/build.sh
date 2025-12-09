#!/bin/bash
# WoniuNote C++ Backend Build Script for Linux/macOS
# Requires: CMake 3.20+, GCC 10+ or Clang 13+, vcpkg

set -e

echo "========================================"
echo "WoniuNote C++ Backend Builder"
echo "========================================"

# Check if VCPKG_ROOT is set
if [ -z "$VCPKG_ROOT" ]; then
    echo "[ERROR] VCPKG_ROOT environment variable is not set."
    echo "Please install vcpkg and set VCPKG_ROOT to its path."
    echo ""
    echo "Example:"
    echo "  git clone https://github.com/microsoft/vcpkg.git ~/vcpkg"
    echo "  ~/vcpkg/bootstrap-vcpkg.sh"
    echo "  export VCPKG_ROOT=~/vcpkg"
    exit 1
fi

echo "[INFO] Using vcpkg from: $VCPKG_ROOT"

# Determine number of parallel jobs
JOBS=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

# Create build directory
mkdir -p build
cd build

# Configure with CMake
echo ""
echo "[INFO] Configuring with CMake..."
cmake .. \
    -DCMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" \
    -DCMAKE_BUILD_TYPE=Release

# Build
echo ""
echo "[INFO] Building with $JOBS parallel jobs..."
cmake --build . --config Release --parallel "$JOBS"

echo ""
echo "========================================"
echo "[SUCCESS] Build completed!"
echo "Executable: build/woniunote_backend"
echo "========================================"

cd ..
