@echo off
setlocal ENABLEDELAYEDEXPANSION

echo ========================================
echo   WoniuNote start script (Windows)
echo ========================================
echo.

REM Step 1: kill processes on port 8000 (backend)
echo [1/4] Check backend port 8000 ...
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo       Found PID %%P on port 8000, killing ...
    taskkill /F /PID %%P >nul 2>&1
)
echo       Port 8000 cleared.

REM Step 2: kill processes on port 5173 (frontend)
echo [2/4] Check frontend port 5173 ...
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo       Found PID %%P on port 5173, killing ...
    taskkill /F /PID %%P >nul 2>&1
)
echo       Port 5173 cleared.

REM small delay
timeout /t 2 /nobreak >nul

REM Step 3: start backend
echo [3/4] Start backend ...
cd /d "%~dp0backend" || goto error
if not exist "app\main.py" (
    echo [ERROR] backend\app\main.py not found.
    goto error
)

start "" /b cmd /c "uvicorn app.main:app --host 0.0.0.0 --port 8000 > ..\backend.log 2>&1"
echo       Backend starting, waiting 3s ...
timeout /t 3 /nobreak >nul

REM verify backend
netstat -ano ^| findstr ":8000" ^| findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Backend may NOT be running, please check backend.log
)

REM Step 4: start frontend
echo [4/4] Start frontend ...
cd /d "%~dp0frontend" || goto error
if not exist "package.json" (
    echo [ERROR] frontend\package.json not found.
    goto error
)

start "" /b cmd /c "npm run dev > ..\frontend.log 2>&1"
echo       Frontend starting, waiting 5s ...
timeout /t 5 /nobreak >nul

REM verify frontend
netstat -ano ^| findstr ":5173" ^| findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Frontend may NOT be running, please check frontend.log
)

echo.
echo ========================================
echo   Start OK
echo ========================================
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:5173
echo   Docs:    http://localhost:8000/docs
echo   Logs: backend.log / frontend.log
echo ========================================
goto end

:error
echo.
echo ========================================
echo   Start FAILED, please check logs.
echo ========================================
cd /d "%~dp0"
endlocal
exit /b 1

:end
cd /d "%~dp0"
endlocal
exit /b 0
