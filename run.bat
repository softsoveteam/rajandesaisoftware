@echo off
echo Starting Signage Player V2...
echo.

REM Check if config.json exists
if not exist config.json (
    echo ERROR: config.json not found!
    echo Please copy config.json.example to config.json and fill in your details.
    pause
    exit /b 1
)

REM Run the player
python player.py

pause

