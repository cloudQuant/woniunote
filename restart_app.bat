@echo off
setlocal ENABLEDELAYEDEXPANSION

set "BACKEND_TYPE=cpp"
if /i "%~1"=="python" set "BACKEND_TYPE=python"
if /i "%~1"=="py" set "BACKEND_TYPE=python"
if /i "%~1"=="cpp" set "BACKEND_TYPE=cpp"
if /i "%~1"=="c++" set "BACKEND_TYPE=cpp"

echo ========================================
echo   WoniuNote restart script (Windows)
echo   Backend: %BACKEND_TYPE%
echo ========================================
echo.

echo [1/3] Stop backend/frontend ...
call "%~dp0stop_app.bat" all

echo [2/3] Clear logs ...
> "%~dp0backend.log" echo.
> "%~dp0frontend.log" echo.
if exist "%~dp0route_debug.log" > "%~dp0route_debug.log" echo.

if exist "%~dp0backend\logs" del /q "%~dp0backend\logs\*.log" 2>nul
if exist "%~dp0backend_cpp\build\logs" del /q "%~dp0backend_cpp\build\logs\*.log" 2>nul
if exist "%~dp0backend_cpp\build\Release\logs" del /q "%~dp0backend_cpp\build\Release\logs\*.log" 2>nul

echo       Logs cleared.

echo [3/3] Start backend/frontend ...
call "%~dp0start_app.bat" %BACKEND_TYPE%

echo.
endlocal
exit /b 0
