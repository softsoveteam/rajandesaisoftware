@echo off
REM ========================================
REM Install Signage Player to Windows Startup (Simple Method)
REM ========================================
echo.
echo Installing Signage Player to Windows Startup...
echo.

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

REM Get the startup folder path
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

REM Create a VBS script to run the player in background
set VBS_FILE=%STARTUP_FOLDER%\SignagePlayer.vbs
echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_FILE%"
echo WshShell.Run chr(34) ^& "%SCRIPT_DIR%SignagePlayer.exe" ^& chr(34), 0 >> "%VBS_FILE%"
echo Set WshShell = Nothing >> "%VBS_FILE%"

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Signage Player will now start automatically when Windows boots.
echo.
echo The startup script has been created at:
echo %VBS_FILE%
echo.
echo To remove auto-start, delete the file above.
echo.
pause

