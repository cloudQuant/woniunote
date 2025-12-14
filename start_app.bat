@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Parse command line arguments
REM Usage: start_app.bat [python|cpp]
REM Default: cpp

set "BACKEND_TYPE=cpp"
if /i "%~1"=="python" set "BACKEND_TYPE=python"
if /i "%~1"=="py" set "BACKEND_TYPE=python"
if /i "%~1"=="cpp" set "BACKEND_TYPE=cpp"
if /i "%~1"=="c++" set "BACKEND_TYPE=cpp"

echo ========================================
echo   WoniuNote start script (Windows)
echo   Backend: %BACKEND_TYPE%
echo ========================================
echo.

REM Step 1: kill processes on port 8888 (backend)
echo [1/4] Check backend port 8888 ...
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":8888" ^| findstr "LISTENING"') do (
    echo       Found PID %%P on port 8888, killing ...
    taskkill /F /PID %%P >nul 2>&1
)
echo       Port 8888 cleared.

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
echo [3/4] Start backend (%BACKEND_TYPE%) ...

if "%BACKEND_TYPE%"=="cpp" (
    REM Start C++ backend
    REM Check if executable exists
    if exist "%~dp0backend_cpp\build\Release\woniunote_backend.exe" (
        set "CPP_DIR=%~dp0backend_cpp\build\Release"
        set "CPP_EXE=woniunote_backend.exe"
    ) else if exist "%~dp0backend_cpp\build\woniunote_backend.exe" (
        set "CPP_DIR=%~dp0backend_cpp\build"
        set "CPP_EXE=woniunote_backend.exe"
    ) else (
        echo [ERROR] C++ backend not built. Please run:
        echo         cd backend_cpp ^&^& build.bat
        goto error
    )
    
    echo       Starting C++ backend from: !CPP_DIR!
    REM Copy config.json to build directory
    if exist "%~dp0backend_cpp\config.json" (
        copy /y "%~dp0backend_cpp\config.json" "!CPP_DIR!\config.json" >nul 2>&1
        echo       Copied config.json to build directory
    )
    REM Run from the executable directory so it can find config.json
    cd /d "!CPP_DIR!" || goto error
    start "" /b cmd /c ""!CPP_EXE! >> "%~dp0backend.log" 2>&1""
) else (
    REM Start Python backend
    cd /d "%~dp0backend" || goto error
    if not exist "app\main.py" (
        echo [ERROR] backend\app\main.py not found.
        goto error
    )
    
    start "" /b cmd /c "uvicorn app.main:app --host 0.0.0.0 --port 8888 >> ..\backend.log 2>&1"
)

echo       Backend starting, waiting 3s ...
timeout /t 3 /nobreak >nul

REM verify backend
netstat -ano ^| findstr ":8888" ^| findstr "LISTENING" >nul 2>&1
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

start "" /b cmd /c "npm run dev >> ..\frontend.log 2>&1"
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
echo   Backend (%BACKEND_TYPE%): http://localhost:8888
echo   Frontend: http://localhost:5173
echo   Docs:    http://localhost:8888/docs
echo   Logs: backend.log / frontend.log
echo ========================================
echo.
echo   Usage: start_app.bat [python^|cpp]
echo   Default backend: cpp
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
