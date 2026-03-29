@echo off
title Stock Screener

echo ============================================
echo   Stock Screener - Starting
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

if not exist "%~dp0frontend\node_modules" (
    echo Installing frontend dependencies...
    cd /d "%~dp0frontend"
    call npm install
)

echo Starting backend: http://localhost:8000
echo Starting frontend: http://localhost:5173
echo.

start "Backend" cmd /k "cd /d %~dp0backend && python main.py"

timeout /t 3 /nobreak >nul

start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Open http://localhost:5173 in browser
echo.
pause
