@echo off
REM WoniuNote vcpkg Setup Script for Windows
REM Installs vcpkg to E:\vcpkg and downloads required packages

setlocal enabledelayedexpansion

echo ========================================
echo   vcpkg Setup Script (Windows)
echo ========================================
echo.

REM Set vcpkg installation path - use E: drive to save C: drive space
set "VCPKG_INSTALL_DIR=E:\vcpkg"

REM Check if E: drive exists, fallback to D: or C:
if not exist "E:\" (
    echo [WARN] E: drive not found, trying D: drive...
    set "VCPKG_INSTALL_DIR=D:\vcpkg"
    if not exist "D:\" (
        echo [WARN] D: drive not found, using C: drive...
        set "VCPKG_INSTALL_DIR=C:\vcpkg"
    )
)

echo [INFO] vcpkg will be installed to: %VCPKG_INSTALL_DIR%
echo.

REM Check if vcpkg already exists
if exist "%VCPKG_INSTALL_DIR%\vcpkg.exe" (
    echo [INFO] vcpkg already installed at %VCPKG_INSTALL_DIR%
    goto set_env
)

REM Check for git
where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed. Please install Git first.
    echo Download from: https://git-scm.com/download/win
    exit /b 1
)

REM Create parent directory if needed
if not exist "%VCPKG_INSTALL_DIR%" (
    echo [INFO] Creating directory %VCPKG_INSTALL_DIR%...
    mkdir "%VCPKG_INSTALL_DIR%"
)

REM Clone vcpkg repository
echo [INFO] Cloning vcpkg repository...
cd /d "%VCPKG_INSTALL_DIR%\.."
if exist "%VCPKG_INSTALL_DIR%" rmdir /s /q "%VCPKG_INSTALL_DIR%"
git clone https://github.com/microsoft/vcpkg.git "%VCPKG_INSTALL_DIR%"

if errorlevel 1 (
    echo [ERROR] Failed to clone vcpkg repository.
    exit /b 1
)

REM Bootstrap vcpkg
echo.
echo [INFO] Bootstrapping vcpkg...
cd /d "%VCPKG_INSTALL_DIR%"
call bootstrap-vcpkg.bat -disableMetrics

if errorlevel 1 (
    echo [ERROR] Failed to bootstrap vcpkg.
    exit /b 1
)

:set_env
REM Set VCPKG_ROOT environment variable
echo.
echo [INFO] Setting environment variables...
setx VCPKG_ROOT "%VCPKG_INSTALL_DIR%" >nul 2>&1
set "VCPKG_ROOT=%VCPKG_INSTALL_DIR%"

REM Add vcpkg to PATH if not already there
echo %PATH% | findstr /I "%VCPKG_INSTALL_DIR%" >nul
if errorlevel 1 (
    setx PATH "%PATH%;%VCPKG_INSTALL_DIR%" >nul 2>&1
)

REM Install required packages for woniunote
echo.
echo [INFO] Installing required packages (this may take a while)...
cd /d "%VCPKG_INSTALL_DIR%"

REM Get the vcpkg.json directory
set "MANIFEST_DIR=%~dp0"

echo [INFO] Installing packages from vcpkg.json...
vcpkg install --triplet x64-windows --x-manifest-root="%MANIFEST_DIR%" --x-install-root="%VCPKG_INSTALL_DIR%\installed"

if errorlevel 1 (
    echo [WARN] Some packages may have failed. Trying individual install...
    vcpkg install drogon:x64-windows openssl:x64-windows jsoncpp:x64-windows jwt-cpp:x64-windows picojson:x64-windows hiredis:x64-windows libmariadb:x64-windows
)

echo.
echo ========================================
echo   vcpkg Setup Complete!
echo ========================================
echo   VCPKG_ROOT: %VCPKG_INSTALL_DIR%
echo.
echo   Note: Please restart your terminal or IDE
echo   to apply the new environment variables.
echo ========================================

endlocal
exit /b 0
