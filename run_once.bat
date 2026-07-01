@echo off
REM Central Lab RFP Generator — one-time server launcher
REM Run this once, install the PWA, then you can close this window.

echo.
echo   ====================================================
echo     Central Lab RFP Generator
echo     Starting server on http://localhost:8000
echo.
echo     Open the URL above in your browser.
echo     Click Install when prompted to go offline.
echo     Then close this window — it works offline.
echo   ====================================================
echo.

cd /d "%~dp0"
start "" "http://localhost:8000"
python -m http.server 8000
pause
