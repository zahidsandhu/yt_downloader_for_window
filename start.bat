@echo off
cd /d "%~dp0"

python -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo Python nahi mila. Install ho raha hai, thora intezar karein...
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    echo.
    echo Python install ho gaya. Ab is window ko band karein aur start.bat dobara chalayen.
    pause
    exit /b
)

python auto_start.py
if errorlevel 1 pause
