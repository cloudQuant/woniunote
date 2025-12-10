@echo off
REM WoniuNote C++ Backend Build Script for Windows
REM Requires: CMake 3.20+, Visual Studio 2019+, vcpkg

setlocal enabledelayedexpansion

echo ========================================
echo WoniuNote C++ Backend Builder
echo ========================================

REM Get script directory
set "SCRIPT_DIR=%~dp0"

REM Check if VCPKG_ROOT is set, if not try to find vcpkg
if not defined VCPKG_ROOT (
    echo [INFO] VCPKG_ROOT not set, searching for vcpkg...
    
    REM Check common locations in order: E:, D:, C:, user home
    if exist "E:\vcpkg\vcpkg.exe" (
        set "VCPKG_ROOT=E:\vcpkg"
    ) else if exist "D:\vcpkg\vcpkg.exe" (
        set "VCPKG_ROOT=D:\vcpkg"
    ) else if exist "C:\vcpkg\vcpkg.exe" (
        set "VCPKG_ROOT=C:\vcpkg"
    ) else if exist "%USERPROFILE%\vcpkg\vcpkg.exe" (
        set "VCPKG_ROOT=%USERPROFILE%\vcpkg"
    ) else (
        echo [ERROR] vcpkg not found!
        echo Please run setup_vcpkg.bat first to install vcpkg.
        echo Or set VCPKG_ROOT environment variable manually.
        echo.
        echo Example:
        echo   %SCRIPT_DIR%setup_vcpkg.bat
        exit /b 1
    )
    echo [INFO] Found vcpkg at: !VCPKG_ROOT!
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
