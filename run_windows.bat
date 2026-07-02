@echo off
title Central Lab RFP Generator
echo ============================================
echo  Central Lab RFP Generator
echo ============================================
echo.

REM Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed.
    echo Download Python 3.10+ from https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Create venv if missing
if not exist "venv" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

REM Install deps
echo [2/3] Installing dependencies...
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

REM Launch
echo [3/3] Launching RFP Generator...
echo.
python run.py
pause
