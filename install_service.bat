@echo off
REM ========================================
REM Install Signage Player as Windows Service
REM ========================================
echo.
echo Installing Signage Player Service...
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

REM Check if pywin32 is installed
python -c "import win32service" >nul 2>&1
if errorlevel 1 (
    echo Installing pywin32...
    pip install pywin32
    if errorlevel 1 (
        echo ERROR: Failed to install pywin32
        pause
        exit /b 1
    )
)

REM Check if service_wrapper.py exists
if not exist "service_wrapper.py" (
    echo ERROR: service_wrapper.py not found!
    echo Make sure you're running this from the signage_player_v2 folder
    pause
    exit /b 1
)

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
    echo Please create config.json before installing the service
    pause
    exit /b 1
)

echo.
echo Installing service...
python service_wrapper.py install

if errorlevel 1 (
    echo.
    echo ERROR: Service installation failed!
    pause
    exit /b 1
)

echo.
echo Starting service...
python service_wrapper.py start

if errorlevel 1 (
    echo.
    echo WARNING: Service installation succeeded but starting failed.
    echo You can start it manually later using: python service_wrapper.py start
    pause
    exit /b 1
)

echo.
echo ========================================
echo Service Installed Successfully!
echo ========================================
echo.
echo The Signage Player will now:
echo - Start automatically when Windows boots
echo - Restart automatically if it crashes
echo - Run in the background
echo.
echo Service commands:
echo   Start:   python service_wrapper.py start
echo   Stop:    python service_wrapper.py stop
echo   Restart: python service_wrapper.py restart
echo   Remove:  python service_wrapper.py remove
echo.
pause

