@echo off
title Stock Screener - Backend

echo Starting backend: http://localhost:8000
echo Press Ctrl+C to stop
echo.

cd /d %~dp0backend
python main.py
