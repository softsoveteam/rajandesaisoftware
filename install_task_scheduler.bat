@echo off
REM ========================================
REM Install Signage Player via Task Scheduler
REM (No Python required on target PC)
REM ========================================
echo.
echo Installing Signage Player via Task Scheduler...
echo.

REM Check if running as administrator
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check if SignagePlayer.exe exists
if not exist "SignagePlayer.exe" (
    echo ERROR: SignagePlayer.exe not found!
    echo Please build the EXE first using build_exe.bat
    pause
    exit /b 1
)

REM Check if config.json exists
if not exist "config.json" (
    echo ERROR: config.json not found!
    echo Please create config.json before installing
    pause
    exit /b 1
)

REM Create a wrapper script that restarts the player if it crashes or exits
set WRAPPER_BAT=%SCRIPT_DIR%run_player_wrapper.bat
echo @echo off > "%WRAPPER_BAT%"
echo REM Auto-restart wrapper for Signage Player >> "%WRAPPER_BAT%"
echo REM This keeps the player running 24/7, restarting if it crashes or exits >> "%WRAPPER_BAT%"
echo :loop >> "%WRAPPER_BAT%"
echo cd /d "%~dp0" >> "%WRAPPER_BAT%"
echo "%~dp0SignagePlayer.exe" >> "%WRAPPER_BAT%"
echo REM If player exits (for any reason), wait and restart >> "%WRAPPER_BAT%"
echo timeout /t 10 /nobreak ^>nul >> "%WRAPPER_BAT%"
echo goto loop >> "%WRAPPER_BAT%"

REM Delete existing task if it exists
schtasks /Delete /TN "SignagePlayer" /F >nul 2>&1

REM Create new task that runs at startup
echo.
echo Creating scheduled task...
schtasks /Create /TN "SignagePlayer" ^
    /TR "\"%WRAPPER_BAT%\"" ^
    /SC ONSTART ^
    /RU SYSTEM ^
    /RL HIGHEST ^
    /F

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create scheduled task!
    pause
    exit /b 1
)

REM Start the task immediately
echo.
echo Starting task...
schtasks /Run /TN "SignagePlayer"

if errorlevel 1 (
    echo.
    echo WARNING: Task created but failed to start immediately.
    echo It will start automatically on next boot.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Signage Player is now configured to:
echo - Start automatically when Windows boots
echo - Restart automatically if it crashes
echo - Run with highest privileges
echo.
echo Task Management:
echo   Start:   schtasks /Run /TN "SignagePlayer"
echo   Stop:    schtasks /End /TN "SignagePlayer"
echo   Delete:  schtasks /Delete /TN "SignagePlayer" /F
echo.
pause

