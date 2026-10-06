@echo off
title UNR Tool v1 - Lineage 2 Map Dependency & Downporting Toolkit
cd /d "%~dp0"
python gui.py
if errorlevel 1 (
    echo.
    echo [ERROR] Could not start UNR Tool GUI. Ensure Python is installed and added to PATH.
    pause
)
