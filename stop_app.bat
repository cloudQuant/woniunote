@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Parse command line arguments
REM Usage: stop_app.bat [python|cpp|all]
REM Default: all (stops any backend on port 8888)

set "BACKEND_TYPE=all"
if /i "%~1"=="python" set "BACKEND_TYPE=python"
if /i "%~1"=="py" set "BACKEND_TYPE=python"
if /i "%~1"=="cpp" set "BACKEND_TYPE=cpp"
if /i "%~1"=="c++" set "BACKEND_TYPE=cpp"
if /i "%~1"=="all" set "BACKEND_TYPE=all"

echo ========================================
echo   WoniuNote stop script (Windows)
if not "%BACKEND_TYPE%"=="all" (
    echo   Backend type: %BACKEND_TYPE%
)
echo ========================================
echo.

REM Stop backend on port 5173
echo [1/2] Stop backend (port 5173)...
set "BACKEND_STOPPED=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo    Killing PID %%P on port 5173 ...
    taskkill /F /PID %%P >nul 2>&1
    set "BACKEND_STOPPED=1"
)
if "!BACKEND_STOPPED!"=="0" (
    echo    No backend running on port 5173.
) else (
    echo    Done.
)

REM Stop frontend on port 8888
echo [2/2] Stop frontend (port 8888)...
set "FRONTEND_STOPPED=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8888" ^| findstr "LISTENING"') do (
    echo    Killing PID %%P on port 8888 ...
    taskkill /F /PID %%P >nul 2>&1
    set "FRONTEND_STOPPED=1"
)
if "!FRONTEND_STOPPED!"=="0" (
    echo    No frontend running on port 8888.
) else (
    echo    Done.
)

echo.
echo ========================================
echo   All services stopped.
echo ========================================
echo.
echo   Usage: stop_app.bat [python^|cpp^|all]
echo   (Note: All backends use port 5173)
echo ========================================

endlocal
exit /b 0
