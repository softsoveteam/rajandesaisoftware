# Signage Player Deployment Guide

This guide explains how to build the EXE and deploy it to target PCs with auto-start functionality.

## Prerequisites

1. **Python 3.8+** installed on the build machine
2. **VLC Media Player** installed on target PC at: `C:\Program Files\VideoLAN\VLC\vlc.exe`
3. **Administrator access** on target PC (for service installation)

## Step 1: Build the EXE

1. Open Command Prompt in the `signage_player_v2` folder
2. Run:
   ```batch
   build_exe.bat
   ```
3. The EXE will be created in `dist\SignagePlayer.exe`

## Step 2: Prepare for Deployment

1. Copy these files to target PC:
   - `dist\SignagePlayer.exe`
   - `config.json` (with correct settings for target PC)

2. Place both files in the same folder (e.g., `C:\SignagePlayer\`)

## Step 3: Install Auto-Start (Choose One Method)

### Method 1: Task Scheduler (Recommended - No Python Required)

**Advantages:**
- No Python needed on target PC
- Automatically restarts if it crashes
- Runs at system startup
- Easy to manage via Windows Task Scheduler

**Steps:**
1. Right-click `install_task_scheduler.bat` → **Run as Administrator**
2. The player will start immediately and on every boot

**Task Management:**
```batch
# Start task
schtasks /Run /TN "SignagePlayer"

# Stop task
schtasks /End /TN "SignagePlayer"

# Delete task
schtasks /Delete /TN "SignagePlayer" /F
```

### Method 2: Windows Service (Requires Python on Target PC)

**Advantages:**
- Runs as a system service
- Automatically restarts if it crashes
- Runs even when no user is logged in
- Better for production environments

**Steps:**
1. Copy `service_wrapper.py` to target PC (same folder as EXE)
2. Install Python and pywin32 on target PC:
   ```batch
   pip install pywin32
   ```
3. Right-click `install_service.bat` → **Run as Administrator**
4. The service will be installed and started automatically

**Service Management:**
```batch
# Start service
python service_wrapper.py start

# Stop service
python service_wrapper.py stop

# Restart service
python service_wrapper.py restart

# Remove service
python service_wrapper.py remove
```

### Method 3: Windows Startup Folder (Simple - No Python Required)

**Advantages:**
- Simple, no Python needed on target PC
- Easy to remove
- Good for testing

**Steps:**
1. Right-click `install_startup.bat` → **Run as Administrator**
2. The player will start automatically on next boot

**To Remove:**
- Delete: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SignagePlayer.vbs`

## Step 4: Verify Installation

1. Restart the target PC
2. Check that VLC is playing videos
3. Check logs in `player.log` (in same folder as EXE)

## Troubleshooting

### EXE won't start
- Check that `config.json` is in the same folder as EXE
- Check that VLC is installed at the path specified in config.json
- Check `player.log` for errors

### Service won't start
- Make sure you ran `install_service.bat` as Administrator
- Check Windows Event Viewer → Windows Logs → Application
- Verify Python and pywin32 are installed

### VLC not playing
- Verify VLC path in config.json is correct
- Check that video files are downloading (check `C:\signage\videos\`)
- Check API connection (server_url and api_key in config.json)

### Player keeps restarting
- Check `player.log` for errors
- Verify API is accessible from target PC
- Check that video files are valid MP4 files

## Configuration

Edit `config.json` before deployment:

```json
{
  "server_url": "https://api-led.dhruvik.in",
  "screen_id": 1,
  "api_key": "your-api-key-here",
  "video_dir": "C:\\signage\\videos",
  "vlc_path": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
  "poll_interval_seconds": 60,
  "heartbeat_interval_seconds": 60
}
```

## Logs

- **Player logs:** `player.log` (in same folder as EXE)
- **Service logs:** Windows Event Viewer → Windows Logs → Application (filter by "Signage Player")

## Uninstallation

### If installed as Service:
```batch
python service_wrapper.py stop
python service_wrapper.py remove
```

### If installed via Startup Folder:
- Delete `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SignagePlayer.vbs`

Then delete the SignagePlayer folder.

