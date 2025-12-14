#!/bin/bash
# WoniuNote vcpkg Setup Script for Linux/macOS
# Installs vcpkg to user home directory and downloads required packages

set -e

echo "========================================"
echo "  vcpkg Setup Script (Linux/macOS)"
echo "========================================"
echo ""

# Detect OS
OS_TYPE="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
fi

echo "[INFO] Detected OS: $OS_TYPE"

# Set vcpkg installation path
VCPKG_INSTALL_DIR="$HOME/vcpkg"

echo "[INFO] vcpkg will be installed to: $VCPKG_INSTALL_DIR"
echo ""

# Check if vcpkg already exists
if [ -f "$VCPKG_INSTALL_DIR/vcpkg" ]; then
    echo "[INFO] vcpkg already installed at $VCPKG_INSTALL_DIR"
else
    # Check for git
    if ! command -v git &> /dev/null; then
        echo "[ERROR] Git is not installed. Please install Git first."
        if [ "$OS_TYPE" == "linux" ]; then
            echo "  Ubuntu/Debian: sudo apt-get install git"
            echo "  CentOS/RHEL:   sudo yum install git"
        elif [ "$OS_TYPE" == "macos" ]; then
            echo "  macOS: xcode-select --install"
        fi
        exit 1
    fi

    # Install required build tools
    echo "[INFO] Checking build dependencies..."
    if [ "$OS_TYPE" == "linux" ]; then
        # Check for required packages
        REQUIRED_PKGS="curl zip unzip tar cmake g++ pkg-config"
        MISSING_PKGS=""
        for pkg in $REQUIRED_PKGS; do
            if ! command -v $pkg &> /dev/null; then
                MISSING_PKGS="$MISSING_PKGS $pkg"
            fi
        done
        if [ -n "$MISSING_PKGS" ]; then
            echo "[INFO] Installing missing packages:$MISSING_PKGS"
            sudo apt-get update && sudo apt-get install -y $MISSING_PKGS
        fi
    elif [ "$OS_TYPE" == "macos" ]; then
        # Check for Homebrew
        if ! command -v brew &> /dev/null; then
            echo "[WARN] Homebrew not found. Some dependencies may be missing."
        else
            echo "[INFO] Checking for cmake..."
            if ! command -v cmake &> /dev/null; then
                brew install cmake
            fi
        fi
    fi

    # Clone vcpkg repository
    echo ""
    echo "[INFO] Cloning vcpkg repository..."
    if [ -d "$VCPKG_INSTALL_DIR" ]; then
        rm -rf "$VCPKG_INSTALL_DIR"
    fi
    git clone https://github.com/microsoft/vcpkg.git "$VCPKG_INSTALL_DIR"

    # Bootstrap vcpkg
    echo ""
    echo "[INFO] Bootstrapping vcpkg..."
    cd "$VCPKG_INSTALL_DIR"
    ./bootstrap-vcpkg.sh -disableMetrics
fi

# Set environment variables
echo ""
echo "[INFO] Setting environment variables..."

# Get shell config file
SHELL_CONFIG=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    if [ "$OS_TYPE" == "macos" ]; then
        SHELL_CONFIG="$HOME/.zprofile"
    else
        SHELL_CONFIG="$HOME/.bashrc"
    fi
fi

# Add VCPKG_ROOT to shell config if not already present
if [ -n "$SHELL_CONFIG" ] && [ -f "$SHELL_CONFIG" ]; then
    if ! grep -q "VCPKG_ROOT" "$SHELL_CONFIG"; then
        echo "" >> "$SHELL_CONFIG"
        echo "# vcpkg configuration" >> "$SHELL_CONFIG"
        echo "export VCPKG_ROOT=\"$VCPKG_INSTALL_DIR\"" >> "$SHELL_CONFIG"
        echo "export PATH=\"\$VCPKG_ROOT:\$PATH\"" >> "$SHELL_CONFIG"
        echo "[INFO] Added VCPKG_ROOT to $SHELL_CONFIG"
    fi
fi

# Export for current session
export VCPKG_ROOT="$VCPKG_INSTALL_DIR"
export PATH="$VCPKG_ROOT:$PATH"

# Install required packages for woniunote
echo ""
echo "[INFO] Installing required packages (this may take a while)..."
cd "$VCPKG_INSTALL_DIR"

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[INFO] Installing packages from vcpkg.json..."

# Determine triplet based on OS
TRIPLET=""
if [ "$OS_TYPE" == "linux" ]; then
    TRIPLET="x64-linux"
elif [ "$OS_TYPE" == "macos" ]; then
    # Check for Apple Silicon
    if [ "$(uname -m)" == "arm64" ]; then
        TRIPLET="arm64-osx"
    else
        TRIPLET="x64-osx"
    fi
fi

if [ -n "$TRIPLET" ]; then
    vcpkg install --triplet "$TRIPLET" --x-manifest-root="$SCRIPT_DIR" --x-install-root="$VCPKG_INSTALL_DIR/installed" || {
        echo "[WARN] Manifest install failed. Trying individual packages..."
        vcpkg install "drogon:$TRIPLET" "openssl:$TRIPLET" "jsoncpp:$TRIPLET" "jwt-cpp:$TRIPLET" "picojson:$TRIPLET" "hiredis:$TRIPLET" "libmariadb:$TRIPLET"
    }
fi

echo ""
echo "========================================"
echo "  vcpkg Setup Complete!"
echo "========================================"
echo "  VCPKG_ROOT: $VCPKG_INSTALL_DIR"
echo ""
echo "  Note: Please restart your terminal or run:"
echo "    source $SHELL_CONFIG"
echo "  to apply the new environment variables."
echo "========================================"
