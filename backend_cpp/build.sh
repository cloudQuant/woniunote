#!/bin/bash
# WoniuNote C++ Backend Build Script for Linux/macOS
# Requires: CMake 3.20+, GCC 10+ or Clang 13+, vcpkg

set -e

echo "========================================"
echo "WoniuNote C++ Backend Builder"
echo "========================================"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if VCPKG_ROOT is set, if not try to find vcpkg
if [ -z "$VCPKG_ROOT" ]; then
    echo "[INFO] VCPKG_ROOT not set, searching for vcpkg..."
    
    # Check common locations
    if [ -f "$HOME/vcpkg/vcpkg" ]; then
        export VCPKG_ROOT="$HOME/vcpkg"
    elif [ -f "/opt/vcpkg/vcpkg" ]; then
        export VCPKG_ROOT="/opt/vcpkg"
    elif [ -f "/usr/local/vcpkg/vcpkg" ]; then
        export VCPKG_ROOT="/usr/local/vcpkg"
    else
        echo "[ERROR] vcpkg not found!"
        echo "Please run setup_vcpkg.sh first to install vcpkg."
        echo "Or set VCPKG_ROOT environment variable manually."
        echo ""
        echo "Example:"
        echo "  $SCRIPT_DIR/setup_vcpkg.sh"
        exit 1
    fi
    echo "[INFO] Found vcpkg at: $VCPKG_ROOT"
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
