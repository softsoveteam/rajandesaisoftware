@echo off
echo ========================================
echo Building Signage Player EXE
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Building EXE file...
echo.

REM Build the EXE
REM Note: config.json is NOT bundled - it must be copied separately to target PC
pyinstaller --onefile ^
    --name "SignagePlayer" ^
    --icon=NONE ^
    --console ^
    --hidden-import requests ^
    --hidden-import json ^
    --hidden-import logging ^
    --hidden-import pathlib ^
    --hidden-import subprocess ^
    --hidden-import platform ^
    --hidden-import datetime ^
    --hidden-import sys ^
    --hidden-import os ^
    --hidden-import time ^
    --hidden-import hashlib ^
    player.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo EXE file location: dist\SignagePlayer.exe
echo.
echo Next steps:
echo 1. Copy dist\SignagePlayer.exe to target PC
echo 2. Copy config.json to same folder as EXE
echo 3. On target PC, run install_task_scheduler.bat (as Admin) for auto-start
echo    OR use install_service.bat (requires Python) or install_startup.bat
echo.
pause

