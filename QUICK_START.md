# Quick Start Guide

## Build EXE (On Development Machine)

1. Open Command Prompt in `signage_player_v2` folder
2. Run: `build_exe.bat`
3. EXE will be in `dist\SignagePlayer.exe`

## Deploy to Target PC

1. Copy to target PC:
   - `dist\SignagePlayer.exe`
   - `config.json` (edit with correct settings)
   - `install_task_scheduler.bat` (optional - for auto-start)

2. Place all files in same folder (e.g., `C:\SignagePlayer\`)

3. **Set up auto-start:**
   - Right-click `install_task_scheduler.bat` → **Run as Administrator**
   - Player will start on boot and restart if it crashes

## Verify It's Working

- Check `player.log` in the same folder as EXE
- VLC should be playing videos automatically
- Restart PC to test auto-start

## That's It!

The player will:
- ✅ Start automatically on boot
- ✅ Restart automatically if it crashes
- ✅ Run 24/7 without stopping
- ✅ Only restart VLC when schedule changes

For detailed instructions, see `DEPLOYMENT.md`

