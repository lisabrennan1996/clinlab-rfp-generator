@echo off
REM Central Lab RFP Generator — one-time server launcher
echo.
echo   ====================================================
echo     Central Lab RFP Generator
echo.
echo     Step 1: Open http://localhost:8000 in your browser
echo     Step 2: Upload PDFs - they parse instantly
echo     Step 3: Click "Next" - Generate RFP
echo.
echo     Close this window when done.
echo   ====================================================
echo.

cd /d "%~dp0"
start "" "http://localhost:8000"
python -m http.server 8000
pause
