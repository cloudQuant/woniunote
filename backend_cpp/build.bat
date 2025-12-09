@echo off
REM WoniuNote C++ Backend Build Script for Windows
REM Requires: CMake 3.20+, Visual Studio 2019+, vcpkg

setlocal enabledelayedexpansion

echo ========================================
echo WoniuNote C++ Backend Builder
echo ========================================

REM Check if VCPKG_ROOT is set
if not defined VCPKG_ROOT (
    echo [ERROR] VCPKG_ROOT environment variable is not set.
    echo Please install vcpkg and set VCPKG_ROOT to its path.
    echo.
    echo Example:
    echo   git clone https://github.com/microsoft/vcpkg.git C:\vcpkg
    echo   C:\vcpkg\bootstrap-vcpkg.bat
    echo   set VCPKG_ROOT=C:\vcpkg
    exit /b 1
)

echo [INFO] Using vcpkg from: %VCPKG_ROOT%

REM Create build directory
if not exist "build" mkdir build
cd build

REM Configure with CMake
echo.
echo [INFO] Configuring with CMake...
cmake .. ^
    -DCMAKE_TOOLCHAIN_FILE=%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake ^
    -DCMAKE_BUILD_TYPE=Release ^
    -G "Visual Studio 17 2022" ^
    -A x64

if errorlevel 1 (
    echo [ERROR] CMake configuration failed!
    exit /b 1
)

REM Build
echo.
echo [INFO] Building...
cmake --build . --config Release --parallel

if errorlevel 1 (
    echo [ERROR] Build failed!
    exit /b 1
)

echo.
echo ========================================
echo [SUCCESS] Build completed!
echo Executable: build\Release\woniunote_backend.exe
echo ========================================

cd ..
