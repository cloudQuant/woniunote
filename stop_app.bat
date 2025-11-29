@echo off
setlocal

echo ========================================
echo   WoniuNote stop script (Windows)
echo ========================================
echo.

REM Stop backend on port 8000
echo [1/2] Stop backend (port 8000)...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo    Killing PID %%P on port 8000 ...
    taskkill /F /PID %%P >nul 2>&1
)
echo    Done.

REM Stop frontend on port 5173
echo [2/2] Stop frontend (port 5173)...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo    Killing PID %%P on port 5173 ...
    taskkill /F /PID %%P >nul 2>&1
)
echo    Done.

echo.
echo All services stopped.
echo ========================================

endlocal
exit /b 0
